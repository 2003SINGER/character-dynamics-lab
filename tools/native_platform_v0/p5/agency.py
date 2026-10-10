"""P5 actor callback: local observation, native HTN, one real primitive."""

from . import world
from copy import deepcopy
from tools.native_platform_v0.p3.agency import (
    _dispatch_pending, get_value, record, set_value,
)
from tools.native_platform_v0.p3.planning import plan_patrol, thaw


def step_actor(actor):
    """Run one actor-owned P5 callback; callers supply no world observation."""
    scene_id = world.assert_p5_actor(actor)
    status = get_value(actor, "status", "RUNNING")
    if status == "PAUSED":
        return None
    from tools.native_platform_v0.p3.p4_world import clock_for_actor

    clock = clock_for_actor(actor)
    clock_fields = {"sim_minute": clock["now"], "deadline": clock["deadline"],
                    "time_unit": clock.get("unit", "simulated-minute")}
    tick = get_value(actor, "tick_count", 0) + 1
    set_value(actor, "tick_count", tick)
    record(actor, {**clock_fields, "kind": "timer_tick", "tick": tick,
                    "status_before": status, "activity_profile": "p5_story_v0"})

    pending = get_value(actor, "pending_action")
    if pending:
        if pending.get("status") == "planned":
            return _dispatch_pending(actor, pending)
        if pending.get("status") == "executing" and not getattr(actor.ndb, "p3_pending_operation_id", None):
            set_value(actor, "pending_action", None)
            set_value(actor, "last_outcome", {"status": "INTERRUPTED_IN_DOUBT",
                                               "intent": pending["intent"], "receipt": None})
            record(actor, {**clock_fields, "kind": "execution_interrupted",
                           "intent": pending["intent"],
                           "reason": "lost in-process command; no receipt inferred"})
        return None

    try:
        from tools.native_platform_v0.p3.p4_social import step_social

        if step_social(actor) is True:
            record(actor, {**clock_fields, "kind": "p5_social_callback_consumed"})
            return None
    except Exception as exc:
        set_value(actor, "status", "ERROR")
        record(actor, {**clock_fields, "kind": "p5_social_error",
                       "error": f"{type(exc).__name__}: {exc}",
                       "reason": "native social outcome uncertain; no other primitive dispatched"})
        return None

    try:
        from tools.native_platform_v0.p3.p4_agency import make_decision

        decision = make_decision(actor)
    except Exception as exc:
        set_value(actor, "status", "ERROR")
        record(actor, {**clock_fields, "kind": "p5_loop_error",
                       "error": f"{type(exc).__name__}: {exc}"})
        return None

    # Preserve delivery as the selected task. If the HTN has no route in its
    # actor-local graph, permit one locally visible traversal as route discovery;
    # this is not a side-route script or a claim of global unreachability.
    goal = decision["goal"]
    observation = decision["view"]["observation"]
    task = observation.get("task_item") or {}
    item_id = task.get("id")
    retained = observation.get("item_location")
    own_receipt = goal.get("delivery_status") == "SETTLED"
    item_locally_available = (observation.get("item_held") is True
                              or any(str(row.get("id")) == str(item_id)
                                     for row in observation.get("visible_items", ()))
                              or retained is not None)
    if (goal.get("choice") == "deliver_supply" and not own_receipt
            and item_locally_available and decision["intent"] is None
            and (decision["planner"] or {}).get("status") == "NO_PLAN"):
        local_patrol_view = deepcopy(thaw(decision["view"]))
        local_patrol_view["observation"]["exits"] = [
            edge for edge in local_patrol_view["observation"].get("exits", ())
            if edge.get("traversable") is True
        ]
        signature = sorted((str(row["key"]), int(row["destination_id"]), row.get("traversable") is True)
                           for row in observation.get("exits", ()))
        rejected_state = get_value(actor, "patrol_rejected_state")
        old_signature = (sorted(tuple(row) for row in rejected_state.get("exits", ()))
                         if rejected_state else None)
        if (not rejected_state or rejected_state.get("room_id") != observation["room_id"]
                or old_signature != signature):
            rejected_state = {"room_id": observation["room_id"], "exits": signature, "rejected": []}
            set_value(actor, "patrol_rejected_state", rejected_state)
        rejected = [(str(row[0]), int(row[1])) for row in rejected_state.get("rejected", ())]
        exploration = plan_patrol(local_patrol_view, rejected)
        goal = dict(goal)
        goal.update({"choice": "patrol", "delivery_status": "UNKNOWN_LOCAL_ROUTE",
                     "delivery_reason": (decision["planner"] or {}).get("reason"),
                     "fallback_reason": "local NO_PLAN permits trying only currently visible traversable exits",
                     "reason": "retain assigned delivery and explore one locally visible route edge",
                     "activity": "local_route_discovery",
                     "local_route_planner": decision["planner"],
                     "exploration_planner": exploration})
        decision = {**decision, "goal": goal, "planner": exploration,
                    "intent": exploration.get("intent")}

    selection = decision["goal"]
    record(actor, {**clock_fields, "kind": "p5_goal_choice",
                   "inputs": selection.get("inputs"), "candidates": selection.get("candidates", []),
                   "rule": selection.get("rule"), "choice": selection.get("choice"),
                   "reason": selection.get("reason"),
                   "delivery_status": selection.get("delivery_status"),
                   "delivery_reason": selection.get("delivery_reason"),
                   "goal": selection, "activity_profile": "p5_story_v0",
                   "view": thaw(decision["view"]), "planner": decision["planner"]})
    if selection.get("status") == "NO_TASK":
        set_value(actor, "status", "IDLE")
        return None
    if decision["intent"] is None:
        planner = decision["planner"] or {}
        if selection.get("choice") == "patrol":
            set_value(actor, "status", "PATROL_WAITING")
            record(actor, {**clock_fields, "kind": "activity_wait", "activity": "patrol",
                           "status": planner.get("status"), "reason": planner.get("reason"),
                           "candidate_exits": planner.get("candidate_exits", [])})
        else:
            set_value(actor, "status", "BLOCKED")
            record(actor, {**clock_fields, "kind": "blocked", "reason": planner.get("reason"),
                           "planner_status": planner.get("status")})
        return None

    set_value(actor, "status", "RUNNING")
    pending = {"status": "planned", "planned_at_tick": tick,
               "operation_id": f"p5:{scene_id}:{actor.id}:{tick}",
               "goal": decision["goal"], "planner": decision["planner"],
               "intent": decision["intent"], "view": thaw(decision["view"])}
    set_value(actor, "pending_action", pending)
    record(actor, {**clock_fields, "kind": "p5_primitive_intent", "pending_action": pending})
    return pending


__all__ = ["step_actor"]
