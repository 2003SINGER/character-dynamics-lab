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
