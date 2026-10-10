"""Opt-in P4 actor callback adapter over the existing native P3 loop.

P4 keeps both NPCs on independent actor-local observations and callbacks. It
adds only local door-traversability filtering and the narrow social hook; the
old P3 profiles continue through their original callback path.
"""

from copy import deepcopy

from .agency import (
    _dispatch_pending,
    get_value,
    record,
    set_value,
)
from .planning import plan_next, plan_patrol, thaw


def _clock_fields(actor):
    """Return only the public P4 scene clock fields for actor trace timestamps."""
    from .p4_world import clock_for_actor

    clock = clock_for_actor(actor)
    if not isinstance(clock, dict) or "now" not in clock or "deadline" not in clock:
        raise ValueError("p4_world.clock_for_actor must return now and deadline")
    return {"sim_minute": clock["now"], "deadline": clock["deadline"],
            "time_unit": clock.get("unit", "simulated-minute")}


def _own_delivery_receipt(observation):
    item = observation.get("task_item") or {}
    item_id = item.get("id")
    destination = observation.get("task_destination")
    return item_id is not None and destination is not None and any(
        row.get("kind") == "drop" and row.get("settled") is True and
        str(row.get("item_id")) == str(item_id) and
        row.get("after_item_room_id") == destination
        for row in observation.get("own_delivery_receipts", ())
    )


def choose_goal(local_view):
    """P4's narrow priority: own delivery, or patrol when locally unavailable/settled."""
    observation = local_view["observation"]
    contract = local_view.get("activity_contract", {})
    goal = local_view.get("goal_contract", {}).get("goal")
    item = observation.get("task_item") or {}
    item_id = item.get("id")
    destination = observation.get("task_destination")
    held = observation.get("item_held") is True
    visible = item_id is not None and any(
        str(row.get("id")) == str(item_id) for row in observation.get("visible_items", ())
    )
    retained_location = observation.get("item_location")
    own_receipt = _own_delivery_receipt(observation)
    valid_binding = item_id is not None and destination is not None
    available_locally = held or visible or retained_location is not None
    evidence = {
        "assigned_item_id": item_id,
        "destination_id": destination,
        "item_held": held,
        "item_currently_visible": visible,
        "retained_item_location": retained_location,
        "binding_valid": valid_binding,
        "own_delivery_receipt": own_receipt,
    }
    candidates = ["deliver_supply", "patrol"]
    if goal != "deliver_supply":
        return {"goal": None, "choice": None, "status": "NO_TASK",
                "reason": "P4 supports only the scenario-authored delivery task",
                "rule": "p4_delivery_before_patrol_v0", "candidates": [],
                "inputs": {"profile": "p4_story_v0", "local_evidence": evidence}}
    if own_receipt:
        return {"goal": "patrol", "choice": "patrol", "status": "ACTIVE",
                "reason": "this actor's matching settled drop receipt permanently completes delivery",
                "delivery_status": "SETTLED", "delivery_reason": "own receipt evidence",
                "rule": "p4_delivery_before_patrol_v0", "candidates": candidates,
                "inputs": {"profile": "p4_story_v0", "local_evidence": evidence}}
    if not valid_binding:
        return {"goal": "deliver_supply", "choice": "deliver_supply", "status": "ACTIVE",
                "reason": "invalid task binding remains a delivery-planner concern",
                "delivery_status": "INVALID_BINDING", "delivery_reason": "missing local task item or destination",
                "rule": "p4_delivery_before_patrol_v0", "candidates": candidates,
                "inputs": {"profile": "p4_story_v0", "local_evidence": evidence}}
    if not available_locally:
        return {"goal": "patrol", "choice": "patrol", "status": "ACTIVE",
                "reason": "assigned item is absent from local observation and retained witnessed location",
                "delivery_status": "SUSPENDED_LOCAL_ITEM_UNAVAILABLE",
                "delivery_reason": "reobserve through the actor's own patrol; no global location query",
                "rule": "p4_delivery_before_patrol_v0", "candidates": candidates,
                "inputs": {"profile": "p4_story_v0", "local_evidence": evidence}}
    return {"goal": "deliver_supply", "choice": "deliver_supply", "status": "ACTIVE",
            "reason": "local observation supports continuing the assigned delivery through GTPyhop",
            "delivery_status": "ACTIVE", "delivery_reason": "item is held, visible, or retained at a witnessed room",
            "rule": "p4_delivery_before_patrol_v0", "candidates": candidates,
            "inputs": {"profile": "p4_story_v0", "local_evidence": evidence}}


def make_decision(actor):
    """Observe locally and return one HTN or patrol primitive, never a command sequence."""
    view = make_decision_view(actor)
    selection = choose_goal(view)
    if selection["goal"] is None:
        return {"view": view, "goal": selection, "planner": None, "intent": None}
    observation = view["observation"]
    if selection["goal"] == "deliver_supply":
        planner = plan_next(view, "deliver_supply", respect_local_traversability=True)
    else:
        # Patrol may use only currently visible exits whose native traverse lock
        # was locally observed as open. Keep the unfiltered observation in trace.
        patrol_view = deepcopy(thaw(view))
        patrol_view["observation"]["exits"] = [
            row for row in observation.get("exits", ()) if row.get("traversable") is True
        ]
        signature = sorted(
            (str(row["key"]), int(row["destination_id"]), row.get("traversable") is True)
            for row in observation.get("exits", ())
        )
        state = get_value(actor, "patrol_rejected_state")
        saved_signature = sorted(tuple(row) for row in state.get("exits", ())) if state else None
        if not state or state.get("room_id") != observation["room_id"] or saved_signature != signature:
            state = {"room_id": observation["room_id"], "exits": signature, "rejected": []}
            set_value(actor, "patrol_rejected_state", state)
        rejected = [(str(row[0]), int(row[1])) for row in state.get("rejected", ())]
        planner = plan_patrol(patrol_view, rejected)
    return {"view": view, "goal": selection, "planner": planner,
            "intent": planner.get("intent")}


def make_decision_view(actor):
    """Get P3's actor-local O; P4-specific traversal is added by its profile branch."""
    from .agency import observe_actor

    view = observe_actor(actor)
    observation = view["observation"]
    if view["activity_contract"].get("profile") not in {"p4_story_v0", "p5_story_v0"}:
        raise ValueError("P4/P5 HTN adapter received an actor outside its native scene profiles")
    if any("traversable" not in row for row in observation.get("exits", ())):
        raise ValueError("P4 local observation is missing native exit traversability")
    return view


def _record_clocked(actor, event, clock_fields):
    record(actor, {**clock_fields, **event})


def step_actor(actor):
    """Run exactly one callback for one P4 actor; no controller-supplied world view."""
    status = get_value(actor, "status", "RUNNING")
    if status == "PAUSED":
        return
    clock_fields = _clock_fields(actor)
    tick = get_value(actor, "tick_count", 0) + 1
    set_value(actor, "tick_count", tick)
    _record_clocked(actor, {"kind": "timer_tick", "tick": tick, "status_before": status,
                            "activity_profile": get_value(actor, "activity_profile")}, clock_fields)

    pending = get_value(actor, "pending_action")
    if pending:
        if pending.get("status") == "planned":
            return _dispatch_pending(actor, pending)
        if pending.get("status") == "executing" and not getattr(actor.ndb, "p3_pending_operation_id", None):
            set_value(actor, "pending_action", None)
            set_value(actor, "last_outcome", {"status": "INTERRUPTED_IN_DOUBT",
                                               "intent": pending["intent"], "receipt": None})
            _record_clocked(actor, {"kind": "execution_interrupted", "intent": pending["intent"],
                                    "reason": "lost in-process command; no receipt inferred"}, clock_fields)
        return

    try:
        from .p4_social import step_social

        if step_social(actor) is True:
            _record_clocked(actor, {"kind": "p4_social_callback_consumed"}, clock_fields)
            return
    except Exception as exc:
        set_value(actor, "status", "ERROR")
        _record_clocked(actor, {"kind": "p4_social_error",
                                "error": f"{type(exc).__name__}: {exc}",
                                "reason": "social outcome uncertain; no delivery/patrol primitive dispatched"},
                        clock_fields)
        return

    try:
        decision = make_decision(actor)
    except Exception as exc:
        set_value(actor, "status", "ERROR")
        _record_clocked(actor, {"kind": "loop_error", "error": f"{type(exc).__name__}: {exc}"},
                        clock_fields)
        return

    selection = decision["goal"]
    _record_clocked(actor, {
        "kind": "goal_choice",
        "inputs": selection.get("inputs"),
        "candidates": selection.get("candidates", []),
        "rule": selection.get("rule"),
        "choice": selection.get("choice"),
        "reason": selection.get("reason"),
        "delivery_status": selection.get("delivery_status"),
        "delivery_reason": selection.get("delivery_reason"),
        "goal": selection,
        "activity_profile": decision["view"]["activity_contract"],
        "view": thaw(decision["view"]),
        "planner": decision["planner"],
    }, clock_fields)
    if selection.get("status") == "NO_TASK":
        set_value(actor, "status", "IDLE")
        return
    if decision["intent"] is None:
        planner = decision["planner"] or {}
        if selection.get("choice") == "patrol":
            set_value(actor, "status", "PATROL_WAITING")
            _record_clocked(actor, {"kind": "activity_wait", "activity": "patrol",
                                    "status": planner.get("status"), "reason": planner.get("reason"),
                                    "candidate_exits": planner.get("candidate_exits", [])}, clock_fields)
        else:
            set_value(actor, "status", "BLOCKED")
            _record_clocked(actor, {"kind": "blocked", "reason": planner.get("reason"),
                                    "planner_status": planner.get("status")}, clock_fields)
        return

    set_value(actor, "status", "RUNNING")
    pending = {"status": "planned", "planned_at_tick": tick,
               "operation_id": f"p4:{actor.id}:{tick}",
               "goal": decision["goal"], "planner": decision["planner"],
               "intent": decision["intent"], "view": thaw(decision["view"])}
    set_value(actor, "pending_action", pending)
    _record_clocked(actor, {"kind": "primitive_intent", "pending_action": pending}, clock_fields)
