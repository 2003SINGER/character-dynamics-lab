"""P4-only simulated clock and append-only typed scene ledger.

Evennia objects remain authoritative. The clock and ledger live on the unique
generated pickup room; actor callbacks can read only the public clock through
``clock_for_actor`` and cannot write author/world events.
"""

from __future__ import annotations

from collections.abc import Mapping


PRODUCER_VERSION = "native-p4-ledger-v1"
P4_PROFILE = "p4_story_v0"


def _attr(obj, key, default=None):
    return obj.attributes.get(key, category="native_p3", default=default)


def _scene_rows(scene_id):
    from evennia.objects.models import ObjectDB

    rows = ObjectDB.objects.get_by_attribute(key="p3_scene_id", category="native_p3", value=scene_id)
    return [obj for obj in rows.distinct().order_by("id")
            if _attr(obj, "p3_scene_id") == scene_id]


def pickup_for_scene(scene_id):
    rows = _scene_rows(scene_id)
    pickup_id = next((obj.attributes.get("p4_pickup_id", category="native_p3", default=None)
                      for obj in rows if _attr(obj, "p4_pickup_id") is not None), None)
    pickup = next((obj for obj in rows if obj.id == pickup_id), None)
    if pickup is None or not isinstance(pickup.attributes.get("p4_clock", category="native_p3", default=None), Mapping):
        raise ValueError("P4 scene clock owner is missing or invalid")
    return pickup, rows


def clock_for_actor(actor):
    """Return a copy of the current scene clock; expose no peer state."""
    if _attr(actor, "activity_profile") != P4_PROFILE:
        raise ValueError("P4 clock is available only to p4_story_v0 actors")
    scene_id = _attr(actor, "scene_id")
    pickup, _ = pickup_for_scene(scene_id)
    clock = pickup.attributes.get("p4_clock", category="native_p3")
    return {"now": int(clock["now"]), "unit": str(clock["unit"]),
            "step_minutes": int(clock["step_minutes"]), "deadline": int(clock["deadline"])}


def append_event(actor_or_scene, event):
    """Append one server-produced event to the scene's ledger and timeline.

    Callers supply only event type, deterministic ID, typed arguments, seal
    state, and optional receipt identity. Ordering/time are assigned here.
    """
    if isinstance(actor_or_scene, str):
        scene_id = actor_or_scene
    else:
        scene_id = _attr(actor_or_scene, "scene_id")
        if scene_id is None:
            scene_id = _attr(actor_or_scene, "p3_scene_id")
    if not isinstance(scene_id, str) or not isinstance(event, Mapping):
        raise TypeError("append_event requires a P4 actor/scene and event mapping")
    required = {"event_type", "event_id", "typed_args"}
    if not required.issubset(event):
        raise ValueError("P4 event requires event_type, event_id, and typed_args")
    if not isinstance(event["event_type"], str) or not event["event_type"]:
        raise ValueError("event_type must be a nonempty string")
    if not isinstance(event["event_id"], str) or not event["event_id"]:
        raise ValueError("event_id must be a nonempty string")
    if not isinstance(event["typed_args"], Mapping):
        raise TypeError("typed_args must be a mapping")
    pickup, _ = pickup_for_scene(scene_id)
    clock = dict(pickup.attributes.get("p4_clock", category="native_p3"))
    ledger = list(pickup.attributes.get("p4_ledger", category="native_p3", default=[]))
    timeline = list(pickup.attributes.get("p4_timeline", category="native_p3", default=[]))
    if any(row.get("event_id") == event["event_id"] for row in ledger):
        existing = next(row for row in ledger if row.get("event_id") == event["event_id"])
        if existing.get("event_type") == event["event_type"] and existing.get("typed_args") == dict(event["typed_args"]):
            return dict(existing)
        raise ValueError("P4 event_id reuse with different content is forbidden")
    sequence = int(pickup.attributes.get("p4_ledger_sequence", category="native_p3", default=0)) + 1
    row = {
        "event_type": event["event_type"], "event_version": 1,
        "event_id": event["event_id"], "minute": int(clock["now"]),
        "sequence": sequence, "producer_version": PRODUCER_VERSION,
        "typed_args": dict(event["typed_args"]),
        "sealed": event.get("sealed", True) is True,
    }
    if event.get("receipt_id") is not None:
        row["receipt_id"] = str(event["receipt_id"])
    pickup.attributes.add("p4_ledger_sequence", sequence, category="native_p3")
    ledger.append(row)
    timeline.append(dict(row))
    pickup.attributes.add("p4_ledger", ledger, category="native_p3")
    pickup.attributes.add("p4_timeline", timeline, category="native_p3")
    return dict(row)


def advance_clock(scene_id):
    """Advance exactly one server-owned simulated minute without wall-time claims."""
    pickup, _ = pickup_for_scene(scene_id)
    clock = dict(pickup.attributes.get("p4_clock", category="native_p3"))
    if int(clock["now"]) >= int(clock["deadline"]):
        raise ValueError("P4 scenario is already at its fixed deadline")
    before = int(clock["now"])
    clock["now"] = before + int(clock["step_minutes"])
    pickup.attributes.add("p4_clock", clock, category="native_p3")
    append_event(scene_id, {
        "event_type": "TIME_ADVANCED",
        "event_id": f"p4:{pickup.attributes.get('scenario_seed', category='native_p3', default=0)}:{clock['now']}:time",
        "typed_args": {"before_minute": before, "after_minute": clock["now"],
                       "step_minutes": clock["step_minutes"], "unit": clock["unit"],
                       "source": "server_owned_p4_clock"},
        "sealed": True,
    })
    return {"before": before, **clock}


def director_view(scene_id):
    """Build only the five frozen fields authorized for the fixed director."""
    pickup, objects = pickup_for_scene(scene_id)
    clock = pickup.attributes.get("p4_clock", category="native_p3")
    actors = [obj for obj in objects if _attr(obj, "p3_control_role") in ("courier", "resident")]
    east = next((edge for edge in pickup.exits if edge.key == "east" and _attr(edge, "p3_scene_id") == scene_id), None)
    if east is None:
        raise ValueError("P4 generated east passage is missing")
    actor = actors[0] if actors else None
    door_closed = not bool(east.access(actor, "traverse", default=True))
    opportunity_used = pickup.attributes.get("p4_opportunity_used", category="native_p3", default=False) is True
    ledger = pickup.attributes.get("p4_ledger", category="native_p3", default=[])
    goal_witness_present = any(
        row.get("event_type") == "SOCIAL_RESPONSE" and row.get("sealed") is True
        and row.get("typed_args", {}).get("decision") in ("accepted", "rejected")
        and row.get("typed_args", {}).get("physical_receipt", {}).get("status") == "settled"
        and row.get("typed_args", {}).get("native_commit_status") == "settled"
        for row in ledger
    )
    return {"now": int(clock["now"]), "deadline": int(clock["deadline"]),
            "door_closed": door_closed, "opportunity_used": opportunity_used,
            "goal_witness_present": goal_witness_present}


def open_east_passage(scene_id):
    """Perform the sole licensed author action and verify the lock transition."""
    pickup, _ = pickup_for_scene(scene_id)
    east = next((edge for edge in pickup.exits if edge.key == "east" and _attr(edge, "p3_scene_id") == scene_id), None)
    if east is None:
        raise ValueError("P4 generated east passage is missing")
    actors = [obj for obj in _scene_rows(scene_id) if _attr(obj, "p3_control_role") in ("courier", "resident")]
    actor = actors[0] if actors else None
    before = not bool(east.access(actor, "traverse", default=True))
    destination = east.destination
    west = next((edge for edge in destination.exits if edge.key == "west" and _attr(edge, "p3_scene_id") == scene_id), None)
    west_actor = next((obj for obj in actors if obj.location and obj.location.id == destination.id), actor)
    west_before = bool(west and west.access(west_actor, "traverse", default=True))
    if not before or pickup.attributes.get("p4_opportunity_used", category="native_p3", default=False):
        return {"settled": False, "before_closed": before,
                "after_closed": not bool(east.access(actor, "traverse", default=True)),
                "reason": "passage already open or opportunity already used"}
    east.locks.add("traverse:true()")
    after = not bool(east.access(actor, "traverse", default=True))
    west_after = bool(west and west.access(west_actor, "traverse", default=True))
    west_unchanged = west_before == west_after
    settled = before is True and after is False and west_unchanged
    if settled:
        pickup.attributes.add("p4_opportunity_used", True, category="native_p3")
    return {"settled": settled, "before_closed": before, "after_closed": after,
            "east_exit_id": int(east.id), "west_unchanged": west_unchanged,
            "west_before_traversable": west_before, "west_after_traversable": west_after,
            "opportunity_used": bool(pickup.attributes.get("p4_opportunity_used", category="native_p3", default=False))}


def seal_ledger(scene_id):
    pickup, objects = pickup_for_scene(scene_id)
    clock = dict(pickup.attributes.get("p4_clock", category="native_p3"))
    if int(clock["now"]) != int(clock["deadline"]):
        raise ValueError("P4 ledger cannot be closed before the fixed deadline")
    ledger = list(pickup.attributes.get("p4_ledger", category="native_p3", default=[]))
    sequence = int(pickup.attributes.get("p4_ledger_sequence", category="native_p3", default=0))
    unsealed_ids = [row.get("event_id") for row in ledger if row.get("sealed") is not True]
    missing_records = []
    for minute in range(1, int(clock["deadline"]) + 1):
        minute_rows = [row for row in ledger if row.get("minute") == minute]
        if not any(row.get("event_type") == "TIME_ADVANCED" for row in minute_rows):
            missing_records.append(f"minute:{minute}:time")
        if not any(row.get("event_type") == "DIRECTOR_DECISION" for row in minute_rows):
            missing_records.append(f"minute:{minute}:director")
        callback_roles = {row.get("typed_args", {}).get("role") for row in minute_rows
                          if row.get("event_type") == "NPC_CALLBACK"}
        if callback_roles != {"courier", "resident"}:
            missing_records.append(f"minute:{minute}:callbacks")
    actor_failures = []
    for actor in objects:
        if _attr(actor, "p3_control_role") not in ("courier", "resident"):
            continue
        if _attr(actor, "status") == "ERROR":
            actor_failures.append(f"actor:{actor.id}:ERROR")
        social_status = _attr(actor, "p4_social_status")
        if social_status in {"UNAVAILABLE", "SOCIAL_SETTLEMENT_PENDING", "WORLD_SETTLEMENT_PENDING",
                             "UNSUPPORTED_NATIVE_ACTION", "STALE_NATIVE_PROPOSAL",
                             "WORLD_VALIDATION_REJECTED"}:
            actor_failures.append(f"actor:{actor.id}:{social_status}")
    closed = not unsealed_ids and not missing_records and not actor_failures
    seal = {"minute": int(clock["now"]), "sequence": sequence, "closed": closed,
            "unsealed_event_ids": unsealed_ids, "missing_records": missing_records,
            "actor_failures": actor_failures}
    pickup.attributes.add("p4_ledger_seal", seal, category="native_p3")
    return seal
