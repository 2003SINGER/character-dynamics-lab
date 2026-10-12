"""Sealed-evidence progression for the P5 mature-method application layer."""
from __future__ import annotations

from typing import Any, Mapping

from .method_adapters import MatureSnapshot


def _actor_map(snapshot: MatureSnapshot) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("actor_alias")): row for row in snapshot.actor_evidence}


def _pending_identity(actor: Mapping[str, Any]) -> Any:
    pending = actor.get("pending_action")
    if not isinstance(pending, Mapping):
        return None
    return {key: pending.get(key) for key in ("operation_id", "status", "planned_at_tick", "intent")
            if key in pending}


def _receipt_ids(actor: Mapping[str, Any]) -> set[str]:
    return {str(row.get("receipt_id")) for row in actor.get("native_receipts", ())
            if isinstance(row, Mapping) and row.get("receipt_id")}


def _verdict_map(snapshot: MatureSnapshot) -> dict[str, Mapping[str, Any]]:
    return {str(row["constraint_id"]): row for row in snapshot.verdicts}


def _author_event_ids(snapshot: MatureSnapshot) -> set[str]:
    return {str(row.get("event_id")) for row in snapshot.typed_trace.get("events", ())
            if isinstance(row, Mapping) and row.get("event_type") in
            {"p5_delivery_settled", "p5_note_response"}}


def advance_from_sealed(prior_plan: Mapping[str, Any], before: MatureSnapshot,
                        after: MatureSnapshot) -> dict[str, Any]:
    """Decide whether sealed native evidence changed a high-level dependency.

    This is not a second monitor. It compares the already-validated P5
    projection and preserves obligations for actors unaffected by the change.
    Position/log-only changes and ordinary clock increments do not trigger a
    root replan; deadlines are reconsidered at their boundary.
    """
    if not isinstance(prior_plan, Mapping) or prior_plan.get("schema") != "p5-mature-method-plan-v1":
        raise ValueError("prior_plan is not a mature-method decision record")
    if not isinstance(before, MatureSnapshot) or not isinstance(after, MatureSnapshot):
        raise TypeError("advance_from_sealed requires validated before/after snapshots")
    if before.scene_id != after.scene_id or before.bundle_id != after.bundle_id:
        raise ValueError("cannot advance across scenes or author bundles")
    if after.now < before.now:
        raise ValueError("sealed prefix minute cannot move backwards")
    if (prior_plan.get("scene_id") != before.scene_id
            or prior_plan.get("bundle_id") != before.bundle_id
            or prior_plan.get("bundle_version") != before.bundle_version):
        raise ValueError("prior plan does not match its before snapshot")

    reasons: list[dict[str, Any]] = []
    changed_actors: set[str] = set()
    affected_goals: set[str] = set()
    if before.bundle_version != after.bundle_version or before.bundle_sha256 != after.bundle_sha256:
        reasons.append({"kind": "AUTHOR_VERSION_CHANGED", "from": before.bundle_version,
                        "to": after.bundle_version})
        affected_goals.update(row.get("constraint_id") for row in prior_plan.get("obligations", ())
                              if row.get("constraint_id"))

    old_verdicts, new_verdicts = _verdict_map(before), _verdict_map(after)
    for constraint_id in sorted(set(old_verdicts) | set(new_verdicts)):
        old, new = old_verdicts.get(constraint_id), new_verdicts.get(constraint_id)
        if old != new:
            reasons.append({"kind": "TYPEDIR_VERDICT_CHANGED", "constraint_id": constraint_id,
                            "from": None if old is None else old.get("status"),
                            "to": None if new is None else new.get("status")})
            affected_goals.add(constraint_id)

    old_actors, new_actors = _actor_map(before), _actor_map(after)
    pending_telemetry = {}
    for actor_alias in ("A", "B"):
        old, new = old_actors.get(actor_alias, {}), new_actors.get(actor_alias, {})
        old_pending, new_pending = _pending_identity(old), _pending_identity(new)
        if old_pending != new_pending:
            pending_telemetry[actor_alias] = {"from": old_pending, "to": new_pending,
                                               "replan_trigger": False}
        new_receipts = _receipt_ids(new) - _receipt_ids(old)
        if new_receipts:
            pending_telemetry.setdefault(actor_alias, {})["new_receipt_ids"] = sorted(new_receipts)

    before_events, after_events = _author_event_ids(before), _author_event_ids(after)
    added_author_events = sorted(after_events - before_events)
    if added_author_events:
        reasons.append({"kind": "AUTHOR_EVENT_RECEIPT_ADDED", "event_ids": added_author_events})
        affected_goals.update(row.get("constraint_id") for row in prior_plan.get("obligations", ())
                              if row.get("kind") in {"delivery", "social_response"})

    from .narrative_methods import _delivery_availability
    old_items = _delivery_availability(before)
    new_items = _delivery_availability(after)
    for key in sorted(set(old_items) | set(new_items)):
        old_item, new_item = old_items.get(key), new_items.get(key)
        old_status = None if old_item is None else old_item.get("status")
        new_status = None if new_item is None else new_item.get("status")
        if old_status != new_status:
            actor_alias, item_alias = key
            reasons.append({"kind": "BOUND_TASK_ITEM_AVAILABILITY_CHANGED", "actor": actor_alias,
                            "item": item_alias, "from": old_item, "to": new_item})
            changed_actors.add(actor_alias)
            affected_goals.update(row.get("constraint_id") for row in prior_plan.get("obligations", ())
                                  if row.get("kind") == "delivery" and row.get("actor") == actor_alias
                                  and row.get("item") == item_alias)

    old_routes = {row.get("id"): row for row in before.director_state.get("routes", ())}
    new_routes = {row.get("id"): row for row in after.director_state.get("routes", ())}
    for route_id in sorted(set(old_routes) | set(new_routes)):
        if old_routes.get(route_id) != new_routes.get(route_id):
            reasons.append({"kind": "WORLD_SUPPORT_CHANGED", "route_id": route_id,
                            "from": old_routes.get(route_id), "to": new_routes.get(route_id)})
            changed_actors.update(("A", "B"))

    if before.director_state.get("spent_cost") != after.director_state.get("spent_cost") or \
            before.director_state.get("opportunities_used") != after.director_state.get("opportunities_used"):
        reasons.append({"kind": "WORLD_RESOURCE_CHANGED"})
        changed_actors.update(("A", "B"))

    if after.now > before.now:
        for obligation in prior_plan.get("obligations", ()):
            deadline = obligation.get("deadline")
            if type(deadline) is int and before.now < deadline <= after.now:
                reasons.append({"kind": "DEADLINE_CHECKPOINT", "constraint_id": obligation.get("constraint_id"),
                                "deadline": deadline})
                affected_goals.add(obligation.get("constraint_id"))

    obligations = [dict(row) for row in prior_plan.get("obligations", ())]
    for row in obligations:
        constraint_id, actor_alias = row.get("constraint_id"), row.get("actor")
        if (constraint_id in affected_goals or actor_alias in changed_actors) and row.get("status", "").startswith("WAITING"):
            row["reconsider_on_next_plan"] = True
        else:
            row["preserved_unaffected"] = True
    return {"schema": "p5-mature-method-advance-v1",
            "status": "REPLAN_REQUIRED" if reasons else "WAITING_NO_RELEVANT_CHANGE",
            "scene_id": after.scene_id, "bundle_id": after.bundle_id,
            "bundle_version": after.bundle_version, "from_minute": before.now,
            "through_minute": after.now, "reasons": reasons,
            "affected_constraint_ids": sorted(x for x in affected_goals if x),
            "changed_actor_aliases": sorted(changed_actors),
            "pending_progress_telemetry": pending_telemetry,
            "retained_obligations": obligations,
            "before_trace_identity": dict(before.trace_identity),
            "after_trace_identity": dict(after.trace_identity),
            "replan_count_triggered": bool(reasons)}


__all__ = ["advance_from_sealed"]
