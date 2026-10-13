"""Actor-local HTN planning for the bounded native courier scene.

The planner accepts only a local view and never imports Evennia or reads world state.
Its symbolic actions are forecasts; the native game must validate every primitive.
"""

from collections import deque
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import os
import threading
import time
from types import MappingProxyType

_LOCK = threading.RLock()


def freeze(value):
    """Recursively freeze a JSON-like local observation."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(freeze(item) for item in value)
    return value


def thaw(value):
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [thaw(item) for item in value]
    return value


def _path(graph, start, target):
    if start == target:
        return []
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        room, prefix = queue.popleft()
        for neighbor in graph.get(room, ()):
            if neighbor in visited:
                continue
            path = prefix + [neighbor]
            if neighbor == target:
                return path
            visited.add(neighbor)
            queue.append((neighbor, path))
    return None


def plan_next(local_view, goal, max_visits=500, wall_seconds=0.25,
              respect_local_traversability=False):
    """Return only the first HTN primitive for `deliver_supply`.

    GTPyhop methods recursively decompose delivery using observed topology and
    observed item location. This is a small authored domain, not a learned policy.
    """
    if goal != "deliver_supply":
        return {"status": "NO_PLAN", "reason": "unsupported goal", "intent": None, "plan": []}
    view = thaw(local_view)
    observation = view["observation"]
    item = observation.get("task_item")
    destination = observation.get("task_destination")
    if not item or destination is None:
        return {"status": "BLOCKED", "reason": "task binding is not available in actor view", "intent": None, "plan": []}
    graph = {int(room): tuple(int(n) for n in neighbors)
             for room, neighbors in observation.get("known_exits", {}).items()}
    if respect_local_traversability:
        known_traversability = observation.get("known_traversability", {})
        graph = {
            room: tuple(neighbor for neighbor in neighbors
                        if known_traversability.get(room, {}).get(neighbor) is True)
            for room, neighbors in graph.items()
        }
    item_location = observation.get("item_location")
    state = None
    start = time.monotonic()
    visits = 0
    exhausted = False

    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("P3 requires the pinned gtpyhop-core==2.0.2 dependency") from exc

    def budget():
        nonlocal visits, exhausted
        visits += 1
        if visits > max_visits or time.monotonic() - start >= wall_seconds:
            exhausted = True
            return False
        return True

    def move_to(world, room_id):
        if not budget() or room_id not in graph.get(world.room, ()):
            return False
        world.room = room_id
        return world

    def get_item(world, item_id):
        if not budget() or world.item != item_id or world.item_room != world.room or world.held:
            return False
        world.held = True
        world.item_room = None
        return world

    def drop_item(world, item_id, room_id):
        if not budget() or not world.held or item_id != world.item or world.room != room_id:
            return False
        world.held = False
        world.item_room = room_id
        world.delivered = True
        return world

    def travel(world, room_id):
        if not budget():
            return False
        path = _path(graph, world.room, room_id)
        if path is None:
            return None
        return [] if not path else [("move_to", path[0]), ("travel_to", room_id)]

    def deliver(world, item_id, room_id):
        if not budget():
            return False
        if world.delivered:
            return []
        if world.held:
            path = _path(graph, world.room, room_id)
            if path is None:
                return None
            return ([] if not path else [("move_to", path[0]), ("deliver_supply", item_id, room_id)]) \
                if world.room != room_id else [("drop_item", item_id, room_id)]
        if world.item_room is None:
            return None
        path = _path(graph, world.room, world.item_room)
        if path is None:
            return None
        if world.room != world.item_room:
            return [("move_to", path[0]), ("deliver_supply", item_id, room_id)]
        return [("get_item", item_id), ("deliver_supply", item_id, room_id)]

    state = g.State("p3-actor-local")
    state.room = int(observation["room_id"])
    state.item = str(item["id"])
    state.item_room = int(item_location) if item_location is not None else None
    state.destination = int(destination)
    state.held = bool(observation.get("item_held", False))
    state.delivered = bool(observation.get("delivered", False))
    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("p3-courier-local")
            g.declare_actions(move_to, get_item, drop_item)
            g.declare_task_methods("travel_to", travel)
            g.declare_task_methods("deliver_supply", deliver)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking", verbose=0,
                                  structured_logging=False) as session:
                result = session.find_plan(state, [("deliver_supply", state.item, state.destination)],
                                           timeout_ms=max(1, int(wall_seconds * 1000)))
        finally:
            main.current_domain = previous
    if exhausted or time.monotonic() - start >= wall_seconds:
        return {"status": "BUDGET", "reason": "method/action cap or wall watchdog", "intent": None, "plan": [],
                "method_action_visits": visits}
    if not result.success:
        return {"status": "NO_PLAN", "reason": "no route or required item is absent under current local view",
                "intent": None, "plan": [], "method_action_visits": visits}
    steps = []
    for step in result.plan:
        op = step[0]
        if op == "move_to":
            matching = next((edge for edge in observation.get("exits", [])
                             if int(edge["destination_id"]) == int(step[1])), None)
            if matching is None:
                # The destination remains locally known, but native traversal is
                # dispatched by the observed exit key only.
                matching = {"key": None, "destination_id": int(step[1])}
            steps.append({"operator": "move", "exit_key": matching["key"],
                          "destination_id": int(step[1])})
        elif op == "get_item":
            steps.append({"operator": "get", "item_id": state.item})
        elif op == "drop_item":
            steps.append({"operator": "drop", "item_id": state.item, "room_id": int(step[2])})
    return {"status": "SOLVED", "reason": "actor-local HTN proposal", "intent": steps[0] if steps else None,
            "plan": steps, "method_action_visits": visits,
            "implementation": "gtpyhop-core-2.0.2", "prediction_only": True}


def plan_patrol(local_view, rejected_exits=()):
    """Propose one move using only currently observed, visible exits.

    This is deliberately a thin application adapter inspired by EvAdventure's
    roaming action, not a port of its NPC FSM or random roaming policy.
    """
    observation = thaw(local_view)["observation"]
    exits = sorted(
        (edge for edge in observation.get("exits", ())
         if edge.get("key") and edge.get("destination_id") is not None),
        key=lambda edge: (str(edge["key"]).casefold(), int(edge["destination_id"])),
    )
    if not exits:
        return {"status": "WAIT", "reason": "no currently visible exits",
                "intent": None, "candidate_exits": []}
    rejected = {(str(row[0]), int(row[1])) for row in rejected_exits}
    candidates = [edge for edge in exits
                  if (str(edge["key"]), int(edge["destination_id"])) not in rejected]
    if not candidates:
        return {"status": "WAIT", "reason": "all currently visible exits were rejected; wait for local change",
                "intent": None,
                "candidate_exits": [{"key": edge["key"], "destination_id": edge["destination_id"]}
                                    for edge in exits]}
    selected = candidates[0]
    return {"status": "SOLVED", "reason": "first un-rejected locally visible exit by stable key order",
            "intent": {"operator": "move", "exit_key": selected["key"],
                       "destination_id": int(selected["destination_id"])},
            "candidate_exits": [{"key": edge["key"], "destination_id": edge["destination_id"]}
                                for edge in exits],
            "selection_rule": "local_visible_exit_stable_order_v0"}


def plan_actor_task(local_view, task, max_visits=500, wall_seconds=0.25):
    """Plan one primitive for an opt-in ongoing-station task using P3 HTN routes.

    The task is an authorized actor-local binding, not world state. Navigation and
    item acquisition use the same P3 delivery HTN and ``_path`` implementation;
    only task-specific terminal operators (give/return leg) are added here.
    This function is prediction-only and never dispatches a world action.
    """
    if not isinstance(task, Mapping):
        return {"status": "BLOCKED", "reason": "task binding must be a mapping", "intent": None, "plan": []}
    kind = task.get("task_kind")
    allowed = {"deliver_supply", "archive_note", "handover_note", "routine_route",
               "return_stock", "inspect_supply", "repair_passage", "store_item",
               "lend_tool", "return_tool"}
    if kind not in allowed:
        return {"status": "NO_PLAN", "reason": "unsupported actor task kind",
                "intent": None, "plan": [], "task_kind": kind}
    view = thaw(local_view)
    observation = view.get("observation", {})
    item_id, destination_id = task.get("item_id"), task.get("destination_id")
    tool_task = kind in {"inspect_supply", "repair_passage"}
    store_task = kind == "store_item"
    transfer_task = kind in {"lend_tool", "return_tool"}
    tool_id = task.get("tool_id") if tool_task else None
    target_room_id = task.get("target_room_id") if tool_task else None
    storage_destination_id = task.get("storage_destination_id") if tool_task or store_task else None
    storage_room_id = task.get("storage_room_id") if store_task else None
    phase = task.get("phase", "work") if tool_task else None
    route_waypoints = task.get("route_waypoints") if kind == "routine_route" else None
    waypoint_receipts = task.get("waypoint_receipts", []) if kind == "routine_route" else []
    if route_waypoints is not None:
        if not isinstance(route_waypoints, (list, tuple)) or not route_waypoints:
            return {"status": "BLOCKED", "reason": "route waypoints must be a non-empty sequence",
                    "intent": None, "plan": []}
        if len(waypoint_receipts) != len(route_waypoints):
            return {"status": "BLOCKED", "reason": "route receipt progress does not match waypoint sequence",
                    "intent": None, "plan": []}
        next_waypoint = next((index for index, receipt_id in enumerate(waypoint_receipts)
                              if receipt_id is None), None)
        if next_waypoint is None:
            return {"status": "SOLVED", "reason": "all route waypoints have settled receipts",
                    "intent": None, "plan": [], "task_kind": kind,
                    "task_id": task.get("goal_id"), "prediction_only": True}
        destination_id = route_waypoints[next_waypoint]
    if destination_id is None and not tool_task and not transfer_task and not store_task:
        return {"status": "BLOCKED", "reason": "task destination is unbound", "intent": None, "plan": []}
    if kind != "routine_route" and not tool_task and not transfer_task and item_id is None:
        return {"status": "BLOCKED", "reason": "task item is unbound", "intent": None, "plan": []}
    if kind == "handover_note" and task.get("recipient_id") is None:
        return {"status": "BLOCKED", "reason": "handover recipient is unbound", "intent": None, "plan": []}

    tool_row = None
    tool_held = False
    tool_room = None
    held = False
    item_room = None
    conditional_workbench_reobservation = False
    if tool_task:
        if (type(tool_id) is not int or tool_id <= 0
                or type(target_room_id) is not int or target_room_id <= 0
                or (kind == "inspect_supply" and
                    (type(storage_destination_id) is not int or storage_destination_id <= 0
                     or type(item_id) is not int or item_id <= 0
                     or str(task.get("target_id")) != str(item_id)))
                or (kind == "repair_passage" and not isinstance(task.get("target_id"), (int, str)))
                or phase != "work"):
            return {"status": "BLOCKED", "reason": "station work requires exact local tool, target, and phase bindings",
                    "intent": None, "plan": [], "task_kind": kind}
        at_workbench = observation.get("room_id") == target_room_id
        tool_row = next((row for row in observation.get("station_tools", ())
                         if str(row.get("id")) == str(tool_id)
                         and (row.get("visible") is True
                              or row.get("held_by_actor_id") == view.get("actor_id"))), None)
        if tool_row is None and at_workbench:
            return {"status": "BLOCKED", "reason": "exact tool is not locally visible or held",
                    "intent": None, "plan": [], "task_kind": kind}
        if tool_row is None and not at_workbench:
            # The authored/native task names a registered workbench, but a
            # remote actor cannot infer whether its tool is still there or
            # available. Plan only the locally known route; the actor must
            # re-observe the tool before any terminal work primitive.
            conditional_workbench_reobservation = True
        if tool_row is not None and (tool_row.get("lease_status") not in {"FREE"}
                or tool_row.get("visible") is not True
                or tool_row.get("held_by_actor_id") is not None):
            return {"status": "BLOCKED", "reason": "locally observed tool is leased or unavailable",
                    "intent": None, "plan": [], "task_kind": kind}
        tool_held = False
        tool_room = tool_row.get("room_id") if tool_row is not None else target_room_id
        if type(tool_room) is not int or tool_room <= 0:
            return {"status": "BLOCKED", "reason": "tool location is not actor-locally known",
                    "intent": None, "plan": [], "task_kind": kind}
        if tool_row is not None and tool_room != target_room_id:
            return {"status": "BLOCKED", "reason": "tool is not at the task's registered workbench",
                    "intent": None, "plan": [], "task_kind": kind}
        if kind == "inspect_supply" and at_workbench:
            supply_row = next((row for row in observation.get("station_supplies", ())
                               if str(row.get("id")) == str(item_id)
                               and row.get("visible") is True
                               and row.get("room_id") == target_room_id), None)
            if supply_row is None:
                return {"status": "BLOCKED", "reason": "registered supply is not locally observed at the workbench",
                        "intent": None, "plan": [], "task_kind": kind}
            if supply_row.get("inspection_status") == "APPROVED":
                return {"status": "BLOCKED", "reason": "supply already has a completed inspection receipt",
                        "intent": None, "plan": [], "task_kind": kind}
            item_row = next((row for row in observation.get("inventory", ())
                             if str(row.get("id")) == str(item_id)), None)
            visible_item = next((row for row in observation.get("visible_items", ())
                                 if str(row.get("id")) == str(item_id)), None)
            if item_row is None and visible_item is None:
                return {"status": "BLOCKED", "reason": "exact supply is not locally visible or held",
                        "intent": None, "plan": [], "task_kind": kind}
            if item_row is not None:
                return {"status": "BLOCKED", "reason": "inspection requires the exact supply grounded at the registered workbench",
                        "intent": None, "plan": [], "task_kind": kind}
            held = False
            item_room = visible_item.get("room_id", observation.get("room_id"))
            if type(item_room) is not int or item_room != target_room_id:
                return {"status": "BLOCKED", "reason": "supply must be locally observed at the registered workbench",
                        "intent": None, "plan": [], "task_kind": kind}
        elif kind == "repair_passage" and at_workbench:
            repair_row = next((row for row in observation.get("station_repair_targets", ())
                               if str(row.get("id")) == str(task.get("target_id"))
                               and row.get("room_id") == target_room_id), None)
            if repair_row is None or repair_row.get("traversable") is not False:
                return {"status": "BLOCKED", "reason": "exact closed repair exit is not locally observed at the workbench",
                        "intent": None, "plan": [], "task_kind": kind}
            item_id, held, item_room = None, False, None
        destination_id = target_room_id

    if store_task:
        if (type(item_id) is not int or item_id <= 0
                or type(storage_destination_id) is not int or storage_destination_id <= 0
                or type(storage_room_id) is not int or storage_room_id <= 0):
            return {"status": "BLOCKED", "reason": "storage phase requires exact item, container, and room bindings",
                    "intent": None, "plan": [], "task_kind": kind}
        held = any(str(row.get("id")) == str(item_id) for row in observation.get("inventory", ()))
        supply_row = next((row for row in observation.get("station_supplies", ())
                           if str(row.get("id")) == str(item_id)), None)
        storage_row = next((row for row in observation.get("station_storages", ())
                            if str(row.get("id")) == str(storage_destination_id)
                            ), None)
        if supply_row is None or supply_row.get("inspection_status") != "APPROVED":
            return {"status": "BLOCKED", "reason": "exact supply lacks a locally visible completed inspection",
                    "intent": None, "plan": [], "task_kind": kind}
        if storage_row is not None and (storage_row.get("visible") is not True
                                        or storage_row.get("room_id") != storage_room_id):
            return {"status": "BLOCKED", "reason": "locally observed storage binding conflicts with the assigned exact container",
                    "intent": None, "plan": [], "task_kind": kind}
        visible_item = next((row for row in observation.get("visible_items", ())
                             if str(row.get("id")) == str(item_id)), None)
        item_room = None if held else (visible_item.get("room_id", observation.get("room_id"))
                                       if visible_item is not None else task.get("last_known_item_room"))
        if not held and (type(item_room) is not int or item_room <= 0):
            return {"status": "BLOCKED", "reason": "exact inspected supply is not locally available",
                    "intent": None, "plan": [], "task_kind": kind}
        destination_id = storage_room_id

    if transfer_task:
        tool_id = task.get("tool_id", item_id)
        recipient_room_id = task.get("recipient_room_id")
        if (type(tool_id) is not int or tool_id <= 0
                or type(task.get("recipient_id")) is not int
                or type(recipient_room_id) is not int or recipient_room_id <= 0):
            return {"status": "BLOCKED", "reason": "tool transfer requires exact tool, recipient, and locally known recipient room",
                    "intent": None, "plan": [], "task_kind": kind}
        tool_row = next((row for row in observation.get("station_tools", ())
                         if str(row.get("id")) == str(tool_id)
                         and (row.get("visible") is True
                              or row.get("held_by_actor_id") == view.get("actor_id"))), None)
        if tool_row is None:
            return {"status": "BLOCKED", "reason": "exact transfer tool is not locally visible or held",
                    "intent": None, "plan": [], "task_kind": kind}
        if tool_row.get("lease_status") not in {None, "FREE", "AVAILABLE", "HELD_BY_ACTOR", "COMPLETED"}:
            return {"status": "BLOCKED", "reason": "transfer tool is locally observed but unavailable",
                    "intent": None, "plan": [], "task_kind": kind}
        held = tool_row.get("held_by_actor_id") == view.get("actor_id")
        item_room = observation.get("room_id") if held else tool_row.get("room_id")
        if type(item_room) is not int or item_room <= 0:
            return {"status": "BLOCKED", "reason": "transfer tool location is not locally known",
                    "intent": None, "plan": [], "task_kind": kind}
        item_id = tool_id
        destination_id = recipient_room_id

    graph = {int(room): tuple(int(n) for n in neighbors)
             for room, neighbors in observation.get("known_exits", {}).items()}
    known_traversability = observation.get("known_traversability", {})
    if known_traversability:
        # Preserve an initial attempt from stale/unknown topology, but never
        # schedule a locally witnessed blocked edge again until observation
        # changes. This is actor-local evidence, not global route knowledge.
        graph = {room: tuple(neighbor for neighbor in neighbors
                             if known_traversability.get(room, {}).get(neighbor) is not False)
                 for room, neighbors in graph.items()}
    if not (tool_task or transfer_task) and not store_task:
        held = any(str(row.get("id")) == str(item_id) for row in observation.get("inventory", ()))
        item_room = (observation.get("room_id") if any(
            str(row.get("id")) == str(item_id) for row in observation.get("visible_items", ()))
            else None if held else task.get("last_known_item_room"))
    if kind not in {"routine_route", "repair_passage", "inspect_supply"} and not held and item_room is None:
        return {"status": "BLOCKED", "reason": "item is unavailable in actor-local observation/history",
                "intent": None, "plan": [], "task_kind": kind}

    started = time.monotonic()
    visits = 0
    exhausted = False
    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("P3 requires the pinned gtpyhop-core==2.0.2 dependency") from exc

    def budget():
        nonlocal visits, exhausted
        visits += 1
        if visits > max_visits or time.monotonic() - started >= wall_seconds:
            exhausted = True
            return False
        return True

    def move_to(world, room_id):
        if not budget() or room_id not in graph.get(world.room, ()):
            return False
        world.room = room_id
        return world

    def get_item(world, exact_item):
        if not budget() or world.item != exact_item or world.item_room != world.room or world.held:
            return False
        world.held, world.item_room = True, None
        return world

    def drop_item(world, exact_item, room_id):
        if not budget() or not world.held or world.item != exact_item or world.room != room_id:
            return False
        world.held, world.item_room, world.delivered = False, room_id, True
        return world

    def give_item(world, exact_item, recipient_id, room_id):
        if not budget() or not world.held or world.item != exact_item or world.room != room_id:
            return False
        world.held, world.handed_over = False, True
        world.recipient = recipient_id
        return world

    def travel_to(world, room_id):
        if not budget():
            return False
        path = _path(graph, world.room, room_id)
        if path is None:
            return None
        return [] if not path else [("move_to", path[0]), ("travel_to", room_id)]

    def perform_delivery(world, task_kind, exact_item, room_id):
        if not budget():
            return False
        if world.delivered:
            return []
        if world.held:
            if world.room != room_id:
                return [("travel_to", room_id), ("perform_delivery", task_kind, exact_item, room_id)]
            return [("drop_item", exact_item, room_id)]
        if world.item_room is None:
            return None
        path = _path(graph, world.room, world.item_room)
        if path is None:
            return None
        if world.room != world.item_room:
            return [("travel_to", world.item_room), ("perform_delivery", task_kind, exact_item, room_id)]
        return [("get_item", exact_item), ("perform_delivery", task_kind, exact_item, room_id)]

    def perform_handover(world, exact_item, recipient_id, room_id):
        if not budget():
            return False
        if world.handed_over:
            return []
        if world.held:
            if world.room != room_id:
                return [("travel_to", room_id),
                        ("perform_handover", exact_item, recipient_id, room_id)]
            return [("give_item", exact_item, recipient_id, room_id)]
        if world.item_room is None:
            return None
        path = _path(graph, world.room, world.item_room)
        if path is None:
            return None
        if world.room != world.item_room:
            return [("travel_to", world.item_room),
                    ("perform_handover", exact_item, recipient_id, room_id)]
        return [("get_item", exact_item),
                ("perform_handover", exact_item, recipient_id, room_id)]

    def perform_route(world, room_id):
        if not budget():
            return False
        if world.room == room_id:
            world.arrived = True
            return []
        return [("travel_to", room_id)]

    def use_tool(world, exact_tool, work_kind, target_id, room_id):
        if not budget() or world.room != room_id:
            return False
        world.work_started = True
        return world

    def store_item(world, exact_item, storage_id):
        if not budget() or not world.held or world.item != str(exact_item):
            return False
        world.stored = True
        return world

    def perform_tool_work(world, exact_tool, work_kind, target_id, room_id):
        if not budget():
            return False
        if world.work_started:
            return []
        if world.room != room_id:
            return [("travel_to", room_id),
                    ("perform_tool_work", exact_tool, work_kind, target_id, room_id)]
        return [("use_tool", exact_tool, work_kind, target_id, room_id)]

    def store_supply(world, exact_item, storage_id, room_id):
        if not budget():
            return False
        if world.stored:
            return []
        if not world.held:
            if world.item_room is None:
                return None
            if world.room != world.item_room:
                return [("travel_to", world.item_room),
                        ("store_supply", exact_item, storage_id, room_id)]
            return [("get_item", exact_item), ("store_supply", exact_item, storage_id, room_id)]
        if world.room != room_id:
            return [("travel_to", room_id), ("store_supply", exact_item, storage_id, room_id)]
        return [("store_item", exact_item, storage_id)]

    def perform_tool_transfer(world, exact_tool, recipient_id, room_id):
        if not budget():
            return False
        if world.transferred:
            return []
        if world.held:
            if world.room != room_id:
                return [("travel_to", room_id),
                        ("perform_tool_transfer", exact_tool, recipient_id, room_id)]
            return [("give_item", exact_tool, recipient_id, room_id)]
        if world.item_room is None:
            return None
        if world.room != world.item_room:
            return [("travel_to", world.item_room),
                    ("perform_tool_transfer", exact_tool, recipient_id, room_id)]
        return [("get_item", exact_tool),
                ("perform_tool_transfer", exact_tool, recipient_id, room_id)]

    state = g.State("p3-ongoing-actor-local")
    state.room = int(observation["room_id"])
    state.item = str(item_id) if item_id is not None else None
    state.item_room = int(item_room) if item_room is not None else None
    state.destination = int(destination_id)
    state.held = held
    state.delivered = False
    state.handed_over = False
    state.recipient = None
    state.arrived = False
    state.work_started = False
    state.transferred = False
    state.stored = False
    if tool_task:
        task_args = (tool_id, kind, task.get("target_id"), target_room_id)
        task_name = "perform_tool_work"
    elif store_task:
        task_args = (state.item, storage_destination_id, storage_room_id)
        task_name = "store_supply"
    elif transfer_task:
        task_args = (item_id, task["recipient_id"], destination_id)
        task_name = "perform_tool_transfer"
    else:
        task_args = ((kind, state.item, state.destination)
                 if kind in {"deliver_supply", "archive_note", "return_stock"}
                 else (state.item, task.get("recipient_id"), state.destination)
                 if kind == "handover_note" else (state.destination,))
        task_name = "perform_route" if kind == "routine_route" else \
            "perform_handover" if kind == "handover_note" else "perform_delivery"
    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("p3-ongoing-actor-local")
            g.declare_actions(move_to, get_item, drop_item, give_item, use_tool, store_item)
            g.declare_task_methods("travel_to", travel_to)
            g.declare_task_methods("perform_delivery", perform_delivery)
            g.declare_task_methods("perform_handover", perform_handover)
            g.declare_task_methods("perform_route", perform_route)
            g.declare_task_methods("perform_tool_work", perform_tool_work)
            g.declare_task_methods("perform_tool_transfer", perform_tool_transfer)
            g.declare_task_methods("store_supply", store_supply)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking", verbose=0,
                                  structured_logging=False) as session:
                result = session.find_plan(state, [(task_name, *task_args)],
                                           timeout_ms=max(1, int(wall_seconds * 1000)))
        finally:
            main.current_domain = previous
    if exhausted or time.monotonic() - started >= wall_seconds:
        return {"status": "BUDGET", "reason": "method/action cap or wall watchdog", "intent": None,
                "plan": [], "method_action_visits": visits, "task_kind": kind}
    if not result.success:
        return {"status": "NO_PLAN", "reason": "no locally known route or required item is available",
                "intent": None, "plan": [], "method_action_visits": visits, "task_kind": kind}
    steps = []
    for step in result.plan:
        op = step[0]
        if op == "move_to":
            edge = next((row for row in observation.get("exits", ())
                         if int(row.get("destination_id", -1)) == int(step[1])), None)
            steps.append({"operator": "move", "exit_key": edge.get("key") if edge else None,
                          "destination_id": int(step[1])})
        elif op == "get_item":
            steps.append({"operator": "get", "item_id": item_id})
        elif op == "drop_item":
            steps.append({"operator": "drop", "item_id": item_id, "room_id": int(step[2])})
        elif op == "give_item":
            steps.append({"operator": "give", "item_id": item_id,
                          "recipient_id": task.get("recipient_id")})
        elif op == "use_tool":
            steps.append({"operator": "use_tool", "tool_id": tool_id,
                          "task_kind": kind, "target_id": task.get("target_id")})
        elif op == "store_item":
            steps.append({"operator": "store_item", "item_id": item_id,
                          "storage_id": storage_destination_id})
    if conditional_workbench_reobservation:
        steps = [step for step in steps if step["operator"] == "move"]
        if not steps:
            return {"status": "NO_PLAN", "reason": "no locally known route to registered workbench",
                    "intent": None, "plan": [], "method_action_visits": visits,
                    "task_kind": kind}
        return {"status": "CONDITIONAL_ROUTE",
                "reason": "route only; re-observe exact workbench tool before starting work",
                "intent": steps[0], "plan": steps,
                "method_action_visits": visits, "implementation": "gtpyhop-core-2.0.2",
                "prediction_only": True, "conditional_terminal_reobservation": True,
                "task_kind": kind, "task_id": task.get("goal_id"),
                "shared_method_domain": "p3-ongoing-actor-local",
                "phase": phase}
    return {"status": "SOLVED", "reason": "shared actor-local GTPyhop task method",
            "intent": steps[0] if steps else None, "plan": steps,
            "method_action_visits": visits, "implementation": "gtpyhop-core-2.0.2",
            "prediction_only": True, "task_kind": kind, "task_id": task.get("goal_id"),
            "shared_method_domain": "p3-ongoing-actor-local",
            "phase": phase if tool_task else ("store" if store_task else None),
            "route_waypoint_index": (next_waypoint if route_waypoints is not None else None)}
