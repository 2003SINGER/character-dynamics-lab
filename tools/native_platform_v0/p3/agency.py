"""Local observation, explicit goal arbitration, and bounded actor-step control.

Evennia remains the only world and receipt authority. This module never queries
ObjectDB or accepts the world object as a planner input.
"""

from copy import deepcopy
from datetime import datetime, timezone
import threading

from .planning import freeze, plan_next, thaw

CATEGORY = "native_p3"
_SOCIAL_CLIENTS = {}
_SOCIAL_CLIENTS_LOCK = threading.RLock()


def _get(obj, key, default=None):
    return obj.attributes.get(key, category=CATEGORY, default=default)


def _set(obj, key, value):
    obj.attributes.add(key, value, category=CATEGORY)


def _append(actor, event):
    log = list(_get(actor, "log", []))
    log.append(event)
    _set(actor, "log", log)


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _obj_ref(obj):
    return {"id": obj.id, "dbref": obj.dbref, "key": obj.key}


def observe_actor(actor):
    """Build O from own inventory, current room, visible exits/items, and memory.

    The assigned task identifiers are authored task metadata. Item location is
    refreshed only when the assigned item is visible locally or in own inventory.
    """
    room = actor.location
    if room is None:
        raise ValueError("actor has no current room")

    item_id = _get(actor, "task_item_id")
    destination_id = _get(actor, "task_destination_id")
    inventory = [_obj_ref(obj) for obj in actor.contents]
    visible_items = []
    current_exit_rows = []
    for obj in room.contents:
        if obj.id == actor.id:
            continue
        if obj.access(actor, "view", default=True):
            visible_items.append({**_obj_ref(obj), "room_id": room.id})
    for edge in room.exits:
        destination = getattr(edge, "destination", None)
        if destination is not None and edge.access(actor, "view", default=True):
            current_exit_rows.append({"key": edge.key, "destination_id": destination.id,
                                      "destination_dbref": destination.dbref})

    # Retain only observed edges and sightings. No global world lookup occurs here.
    knowledge = deepcopy(_get(actor, "witnessed", {"edges": {}, "objects": {}}))
    room_edges = knowledge["edges"].setdefault(str(room.id), {})
    for edge in current_exit_rows:
        room_edges[str(edge["destination_id"])] = edge["key"]
    observed_item = next((row for row in visible_items if row["id"] == item_id), None)
    held_item = next((row for row in inventory if row["id"] == item_id), None)
    if observed_item:
        old = knowledge["objects"].get(str(item_id), {})
        if old.get("room_id") != room.id or old.get("key") != observed_item["key"] or old.get("status") != "seen":
            knowledge["objects"][str(item_id)] = {"room_id": room.id, "key": observed_item["key"],
                                                 "last_seen_at": _stamp(), "status": "seen"}
    elif held_item:
        old = knowledge["objects"].get(str(item_id), {})
        if old.get("room_id") != "inventory" or old.get("key") != held_item["key"] or old.get("status") != "held":
            knowledge["objects"][str(item_id)] = {"room_id": "inventory", "key": held_item["key"],
                                                 "last_seen_at": _stamp(), "status": "held"}
    elif item_knowledge := knowledge["objects"].get(str(item_id)):
        if item_knowledge.get("room_id") == room.id:
            item_knowledge.update({"room_id": None, "status": "not_visible_in_last_seen_room",
                                   "absence_observed_at": _stamp()})

    item_knowledge = knowledge["objects"].get(str(item_id), {})
    item_location = (room.id if observed_item else None if held_item else
                     item_knowledge.get("room_id") if isinstance(item_knowledge.get("room_id"), int) else None)
    exits = list(current_exit_rows)
    known_exits = {int(source): tuple(int(destination) for destination in rows)
                   for source, rows in knowledge["edges"].items()}
    task_item = {"id": item_id, "key": (observed_item or held_item or {}).get("key", _get(actor, "task_item_key"))}
    delivered = bool(observed_item and room.id == destination_id)
    own_delivery_receipts = list(_get(actor, "native_receipts", []))
    view = {
        "actor_id": actor.id,
        "goal_contract": {"goal": _get(actor, "goal", "deliver_supply"), "item_id": item_id,
                           "destination_id": destination_id, "source": "scenario-authored-task"},
        "observation": {
            "room_id": room.id,
            "inventory": inventory,
            "visible_items": visible_items,
            "task_item": task_item,
            "task_destination": destination_id,
            "item_location": item_location,
            "item_held": held_item is not None,
            "delivered": delivered,
            "own_delivery_receipts": own_delivery_receipts,
            "known_exits": known_exits,
            "exits": exits,
            "witnessed": [{"room_id": room.id, "kind": "current_room", "dbref": room.dbref}],
            "retained_witnesses": list(knowledge["objects"].values()),
        },
    }
    _set(actor, "witnessed", knowledge)
    previous = _get(actor, "last_observation")
    _set(actor, "last_observation", deepcopy(view))
    if previous != view:
        _append(actor, {"at": _stamp(), "kind": "observation", "room": room.dbref,
                        "visible_item_ids": [row["id"] for row in visible_items],
                        "inventory_ids": [row["id"] for row in inventory],
                        "visible_exit_keys": [row["key"] for row in exits]})
    return freeze(view)


def choose_goal(local_view):
    """A versioned authored objective rule; it is not a learned utility/personality."""
    view = local_view
    goal = view["goal_contract"]["goal"]
    if goal != "deliver_supply":
        return {"goal": None, "reason": "no supported authored task", "rule": "p3-authored-goal-v0"}
    observation = view["observation"]
    own_receipt = any(row.get("kind") == "drop" and row.get("settled") and
                      str(row.get("item_id")) == str(observation["task_item"]["id"]) and
                      row.get("after_item_room_id") == observation["task_destination"]
                      for row in observation["own_delivery_receipts"])
    if own_receipt:
        return {"goal": None, "reason": "this actor has a settled drop receipt for the assigned item and destination",
                "rule": "p3-authored-goal-v0", "status": "ACTOR_DELIVERY_SETTLED"}
    if observation["delivered"]:
        return {"goal": None, "reason": "world goal is visibly satisfied, but no actor drop receipt proves who delivered it",
                "rule": "p3-authored-goal-v0", "status": "WORLD_GOAL_SATISFIED_EXTERNAL"}
    return {"goal": goal, "reason": "continue the scenario-authored delivery objective",
            "rule": "p3-authored-goal-v0", "status": "ACTIVE"}


def make_decision(actor):
    """Observe, arbitrate, and propose at most one HTN primitive."""
    view = observe_actor(actor)
    choice = choose_goal(view)
    if choice["goal"] is None:
        return {"view": view, "goal": choice, "planner": None, "intent": None}
    planned = plan_next(view, choice["goal"])
    return {"view": view, "goal": choice, "planner": planned, "intent": planned.get("intent")}


def record(actor, event):
    _append(actor, {"at": _stamp(), **event})


def set_value(actor, key, value):
    _set(actor, key, value)


def get_value(actor, key, default=None):
    return _get(actor, key, default)


def _visible_item_in_room(actor, item_id):
    room = actor.location
    if not room:
        return None
    return next((obj for obj in room.contents
                 if obj.id == item_id and obj.access(actor, "view", default=True)), None)


def _dispatch_pending(actor, pending):
    """Run one native command and settle only from the resulting Evennia state."""
    operation = pending["intent"]
    view = thaw(pending["view"])
    item_id = view["goal_contract"]["item_id"]
    before_room = actor.location.id if actor.location else None
    before_inventory = [obj.id for obj in actor.contents]
    before_item_room = before_room if _visible_item_in_room(actor, item_id) else None
    command = None
    rejection = None
    if operation["operator"] == "move":
        edge = next((ex for ex in actor.location.exits if ex.key == operation["exit_key"]
                     and ex.destination and ex.destination.id == operation["destination_id"]), None) if actor.location else None
        if edge is None:
            rejection = "observed exit is no longer available"
        else:
            command = edge.key
    elif operation["operator"] == "get":
        target = _visible_item_in_room(actor, item_id)
        if target is None:
            rejection = "assigned item is not visible in the actor's current room"
        else:
            command = f"get {target.key}"
    elif operation["operator"] == "drop":
        target = next((obj for obj in actor.contents if obj.id == item_id), None)
        if target is None:
            rejection = "assigned item is not in the actor's inventory"
        elif actor.location.id != operation["room_id"]:
            rejection = "actor is not at the observed destination room"
        else:
            command = f"drop {target.key}"
    else:
        rejection = "unsupported primitive"

    if rejection:
        _settle_pending(actor, pending, before_room, before_inventory, before_item_room,
                        "WORLD_VALIDATION_REJECTED", rejection, dispatch_succeeded=False)
        return

    set_value(actor, "pending_action", {**pending, "status": "executing"})
    operation_id = pending.get("operation_id")
    actor.ndb.p3_pending_operation_id = operation_id
    try:
        deferred = actor.execute_cmd(command)
    except Exception as exc:  # command dispatch errors are recorded, never treated as success
        _settle_pending(actor, pending, before_room, before_inventory, before_item_room,
                        "COMMAND_ERROR", f"{type(exc).__name__}: {exc}", dispatch_succeeded=False)
        return

    def completed(result):
        if hasattr(result, "getErrorMessage"):
            _settle_pending(actor, pending, before_room, before_inventory, before_item_room,
                            "COMMAND_ERROR", result.getErrorMessage(), dispatch_succeeded=False)
        else:
            _settle_pending(actor, pending, before_room, before_inventory, before_item_room,
                            None, None, dispatch_succeeded=True)
        return result

    if hasattr(deferred, "addBoth"):
        deferred.addBoth(completed)
    else:
        completed(deferred)
    return deferred


def _settle_pending(actor, pending, before_room, before_inventory, before_item_room, failure, detail,
                    dispatch_succeeded):
    intent = pending["intent"]
    item_id = pending["view"]["goal_contract"]["item_id"]
    after_room = actor.location.id if actor.location else None
    after_inventory = [obj.id for obj in actor.contents]
    after_item_room = after_room if _visible_item_in_room(actor, item_id) else None
    if intent["operator"] == "move":
        settled = bool(dispatch_succeeded and after_room == intent["destination_id"] and before_room != after_room)
    elif intent["operator"] == "get":
        settled = bool(dispatch_succeeded and item_id in after_inventory and item_id not in before_inventory)
    else:
        settled = bool(dispatch_succeeded and item_id in before_inventory and
                       after_item_room == intent["room_id"] and item_id not in after_inventory)
    status = "SETTLED" if settled else failure or "WORLD_VALIDATION_REJECTED"
    event_id = f"p3:{actor.id}:{get_value(actor, 'tick_count', 0)}:{len(get_value(actor, 'log', []))}"
    receipt = {"receipt_id": event_id, "kind": intent["operator"], "actor_dbref": actor.dbref,
               "item_id": item_id, "before_room_id": before_room, "after_room_id": after_room,
               "before_item_room_id": before_item_room, "after_item_room_id": after_item_room,
               "before_inventory_ids": before_inventory, "after_inventory_ids": after_inventory,
               "dispatch_succeeded": dispatch_succeeded, "settled": settled}
    set_value(actor, "last_outcome", {"status": status, "intent": intent, "detail": detail,
                                     "receipt": receipt})
    set_value(actor, "pending_action", None)
    if getattr(actor, "ndb", None) is not None:
        actor.ndb.p3_pending_operation_id = None
    if intent["operator"] == "get" and not settled and after_room == before_room:
        knowledge = get_value(actor, "witnessed", {"edges": {}, "objects": {}})
        fact = knowledge.get("objects", {}).get(str(item_id))
        if fact and fact.get("room_id") == after_room:
            fact.update({"room_id": None, "status": "not_visible_after_rejected_get",
                         "absence_observed_at": _stamp()})
            set_value(actor, "witnessed", knowledge)
    if settled:
        native_receipts = list(get_value(actor, "native_receipts", []))
        native_receipts.append(receipt)
        set_value(actor, "native_receipts", native_receipts)
    record(actor, {"kind": "execution_settlement", "status": status, "intent": intent,
                   "receipt": receipt, "detail": detail})


def _maybe_social_after_delivery(actor, local_view):
    """Propose P3-B social action; native world settlement is a later script tick."""
    if get_value(actor, "mode") != "b" or get_value(actor, "social_attempted", False):
        return
    target_id = get_value(actor, "p3_social_target_id")
    visible_ids = {row["id"] for row in local_view["observation"]["visible_items"]}
    if target_id not in visible_ids or not actor.location:
        return
    target = next((obj for obj in actor.location.contents if obj.id == target_id and
                   obj.access(actor, "view", default=True)), None)
    if target is None:
        return
    record(actor, {"kind": "goal_choice", "goal": "native_ensemble_interaction",
                   "reason": "P3-B authored social objective; assigned parcel already settled",
                   "target_id": target.id, "room_id": actor.location.id})
    try:
        from tools.native_platform_v0.bridge import evennia_bridge
        from tools.native_platform_v0.bridge.social import execute_social, propose_social
        scene_id = get_value(actor, "scene_id")
        with _SOCIAL_CLIENTS_LOCK:
            client = _SOCIAL_CLIENTS.get(scene_id)
            if client is None or client.proc.poll() is not None:
                client = evennia_bridge.EnsembleProcess()
                _SOCIAL_CLIENTS[scene_id] = client
        attempt = get_value(actor, "social_attempt_count", 0) + 1
        set_value(actor, "social_attempt_count", attempt)
        role = actor.attributes.get("ensemble_character_id", category="ensemble_bridge")
        scenario_seed = get_value(actor, "scenario_seed", 0)
        social_view = {"target": target, "target_visible": True, "room_id": actor.location.id,
                       "source_event_id": f"native-p3b:{scenario_seed}:{role}:social-after-delivery:attempt:{attempt}"}
        proposal = propose_social(actor, social_view, {"ensemble_client": client},
                                  seed=f"p3b-seed-v0:{scenario_seed}:{role}:social-after-delivery")
        record(actor, {"kind": "social_proposal", "proposal": proposal})
        if not proposal.get("ok"):
            set_value(actor, "social_attempted", True)
            record(actor, {"kind": "social_outcome", "result": proposal})
            return
        set_value(actor, "pending_social", {"status": "planned", "proposal": proposal,
                                             "target_id": target.id, "scene_id": scene_id,
                                             "attempt": attempt})
    except Exception as exc:
        result = {"ok": False, "status": "SOCIAL_ADAPTER_ERROR",
                  "error": f"{type(exc).__name__}: {exc}"}
        set_value(actor, "social_attempted", True)
        set_value(actor, "social_result", result)
        record(actor, {"kind": "social_outcome", "result": result})


def _settle_social_pending(actor, pending):
    """Revalidate current-room visibility before one native social settlement."""
    from tools.native_platform_v0.bridge import evennia_bridge
    from tools.native_platform_v0.bridge.social import execute_social

    scene_id = pending["scene_id"]
    client = _SOCIAL_CLIENTS.get(scene_id)
    if client is None or client.proc.poll() is not None:
        set_value(actor, "pending_social", None)
        result = {"ok": False, "status": "SOCIAL_PROPOSAL_INTERRUPTED",
                  "error": "scene-local Ensemble process is unavailable; no world receipt inferred"}
        set_value(actor, "social_result", result)
        set_value(actor, "social_attempted", False)
        record(actor, {"kind": "social_outcome", "result": result})
        return
    target = None
    if actor.location:
        target = next((obj for obj in actor.location.contents
                       if obj.id == pending["target_id"] and obj.access(actor, "view", default=True)), None)
    result = execute_social(client, pending["proposal"], {
        "actor": actor, "target": target, "target_visible": target is not None,
    })
    set_value(actor, "pending_social", None)
    set_value(actor, "social_result", result)
    set_value(actor, "social_attempted", result.get("status") != "WORLD_VALIDATION_REJECTED")
    record(actor, {"kind": "social_outcome", "result": result})


try:
    from evennia import DefaultScript
except Exception:  # permits pure unit tests without a configured Evennia/Django server
    DefaultScript = object
if not isinstance(DefaultScript, type):
    DefaultScript = object


class P3AutonomyScript(DefaultScript):
    """Persistent, independent scheduler loop; each tick observes or settles one primitive."""

    def at_script_creation(self):
        self.key = self.key or "native-p3-autonomy"
        self.desc = "Persistent actor-local HTN courier loop with native command settlement."
        actor = getattr(self, "obj", None)
        drive = _get(actor, "drive_mode", "timer") if actor else "timer"
        interval = _get(actor, "interval_seconds", 4) if actor else 4
        # Evennia 6.0.0 stores db_interval as a non-null integer; zero disables timing.
        self.interval = interval if drive == "timer" else 0
        self.persistent = True

    def at_repeat(self):
        actor = self.obj
        if actor is None:
            self.stop()
            return
        status = get_value(actor, "status", "RUNNING")
        if status == "PAUSED":
            return
        tick = get_value(actor, "tick_count", 0) + 1
        set_value(actor, "tick_count", tick)
        record(actor, {"kind": "timer_tick", "tick": tick, "status_before": status})
        pending = get_value(actor, "pending_action")
        if pending:
            if pending.get("status") == "planned":
                return _dispatch_pending(actor, pending)
            elif pending.get("status") == "executing" and not getattr(actor.ndb, "p3_pending_operation_id", None):
                # A persisted in-flight command may have been interrupted by a server restart.
                # Never infer settlement from the coincidental current state; clear and reobserve.
                set_value(actor, "pending_action", None)
                set_value(actor, "last_outcome", {"status": "INTERRUPTED_IN_DOUBT",
                                                   "intent": pending["intent"], "receipt": None})
                record(actor, {"kind": "execution_interrupted", "intent": pending["intent"],
                               "reason": "server restart or lost in-process Deferred; no receipt inferred"})
            return
        pending_social = get_value(actor, "pending_social")
        if pending_social:
            _settle_social_pending(actor, pending_social)
            return
        try:
            decision = make_decision(actor)
        except Exception as exc:
            set_value(actor, "status", "ERROR")
            record(actor, {"kind": "loop_error", "error": f"{type(exc).__name__}: {exc}"})
            return
        record(actor, {"kind": "goal_choice", "goal": decision["goal"],
                       "view": thaw(decision["view"]), "planner": decision["planner"]})
        if decision["goal"].get("status") in ("ACTOR_DELIVERY_SETTLED", "WORLD_GOAL_SATISFIED_EXTERNAL"):
            outcome = decision["goal"]["status"]
            if status != outcome:
                set_value(actor, "status", outcome)
                record(actor, {"kind": "goal_satisfied_by_local_observation", "status": outcome,
                               "evidence": decision["goal"]["reason"],
                               "native_actor_receipts": decision["view"]["observation"]["own_delivery_receipts"]})
            if outcome == "ACTOR_DELIVERY_SETTLED":
                _maybe_social_after_delivery(actor, thaw(decision["view"]))
            return
        if decision["intent"] is None:
            set_value(actor, "status", "BLOCKED")
            record(actor, {"kind": "blocked", "reason": decision["planner"].get("reason")})
            return
        set_value(actor, "status", "RUNNING")
        pending = {"status": "planned", "planned_at_tick": tick,
                   "operation_id": f"p3:{actor.id}:{tick}",
                   "goal": decision["goal"], "planner": decision["planner"],
                   "intent": decision["intent"], "view": thaw(decision["view"])}
        set_value(actor, "pending_action", pending)
        record(actor, {"kind": "primitive_intent", "pending_action": pending})


def step_actor(actor):
    """Run one real script callback only in the explicit manual test fixture."""
    from evennia.scripts.models import ScriptDB

    if get_value(actor, "drive_mode") != "manual":
        raise ValueError("step_actor is available only for the explicit manual test fixture")
    script = ScriptDB.objects.filter(id=get_value(actor, "script_id")).first()
    if script is None:
        raise RuntimeError("persistent P3 actor script is missing")
    return script.at_repeat()
