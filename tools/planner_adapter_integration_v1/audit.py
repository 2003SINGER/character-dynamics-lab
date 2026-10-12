"""Auditable joins between conditional Sabre steps and native P5 evidence.

This is an evidence correlator, not a task dispatcher or planner. A candidate
actor step is never upgraded to an assignment or execution claim.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _native_actor_evidence(step: Mapping[str, Any], before: Mapping[str, Any],
                           after: Mapping[str, Any]) -> dict[str, Any]:
    result = {}
    bindings = before.get("world_capability_projection", {}).get("task_bindings", {})
    rounds = step.get("rounds", [])
    actor_steps = rounds[0].get("actor_steps", []) if rounds and isinstance(rounds[0], Mapping) else []
    before_actors = {row.get("actor_alias"): row for row in before.get("actor_evidence", [])
                     if isinstance(row, Mapping)}
    after_actors = {row.get("actor_alias"): row for row in after.get("actor_evidence", [])
                    if isinstance(row, Mapping)}
    for alias in ("A", "B"):
        binding = bindings.get(alias, {}) if isinstance(bindings, Mapping) else {}
        row = next((item for item in actor_steps if isinstance(item, Mapping)
                    and item.get("actor_alias") == alias), {})
        decisions = row.get("local_decisions", []) if isinstance(row, Mapping) else []
        old_log = before_actors.get(alias, {}).get("log", [])
        new_log = after_actors.get(alias, {}).get("log", [])
        log_rows = [entry for entry in [*old_log, *new_log, *decisions]
                    if isinstance(entry, Mapping)]
        choices = [entry for entry in log_rows if entry.get("kind") == "p5_goal_choice"]
        intent_rows = [entry for entry in log_rows if entry.get("kind") == "p5_primitive_intent"]
        intents = [entry.get("pending_action", {}) for entry in intent_rows
                   if isinstance(entry.get("pending_action"), Mapping)]
        settlements = [entry for entry in log_rows if entry.get("kind") == "execution_settlement"]
        raw_receipts = [entry for entry in [*(row.get("native_receipts", []) if isinstance(row, Mapping) else []),
                                              *after_actors.get(alias, {}).get("native_receipts", [])]
                        if isinstance(entry, Mapping)]
        receipts = list({str(entry.get("receipt_id", _digest(entry))): entry
                         for entry in raw_receipts}.values())
        item_id = binding.get("item_id") if isinstance(binding, Mapping) else None
        destination_id = binding.get("destination_id") if isinstance(binding, Mapping) else None
        binding_match = []
        for choice in choices:
            observation = choice.get("view", {}).get("observation", {})
            task_item = observation.get("task_item", {}) if isinstance(observation, Mapping) else {}
            observed_item = isinstance(task_item, Mapping) and str(task_item.get("id")) == str(item_id)
            observed_destination = (isinstance(observation, Mapping)
                                    and str(observation.get("task_destination")) == str(destination_id))
            binding_match.append({"goal_choice": choice.get("choice"),
                                  "item_id_observed": observed_item,
                                  "destination_id_observed": observed_destination,
                                  "exact_existing_task_binding": bool(item_id is not None
                                      and destination_id is not None and observed_item
                                      and observed_destination)})
        operation_ids = [pending["operation_id"] for pending in intents
                         if pending.get("operation_id")]
        receipt_ids = [receipt.get("operation_id") for receipt in receipts
                       if isinstance(receipt, Mapping) and receipt.get("operation_id")]
        semantic_joins = []
        for intent_row in intent_rows:
            pending = intent_row.get("pending_action", {})
            if not isinstance(pending, Mapping) or not pending.get("operation_id"):
                continue
            operation_id = pending["operation_id"]
            current_before_pending = before_actors.get(alias, {}).get("pending_action")
            if (not isinstance(current_before_pending, Mapping)
                    or current_before_pending.get("operation_id") != operation_id):
                continue
            intent_contract = pending.get("intent", {})
            goal_view = pending.get("view", {}).get("goal_contract", {})
            expected_item = goal_view.get("item_id") if isinstance(goal_view, Mapping) else None
            expected_kind = intent_contract.get("operator") if isinstance(intent_contract, Mapping) else None
            observation = pending.get("view", {}).get("observation", {})
            source_room = observation.get("room_id") if isinstance(observation, Mapping) else None
            intent_minute = intent_row.get("sim_minute")
            matches = [entry for entry in settlements
                       if type(intent_minute) is int and type(entry.get("sim_minute")) is int
                       and entry["sim_minute"] > intent_minute
                       and entry.get("intent") == intent_contract
                       and isinstance(entry.get("receipt"), Mapping)
                       and entry["receipt"].get("kind") == expected_kind
                       and str(entry["receipt"].get("item_id")) == str(expected_item)
                       and entry["receipt"].get("before_room_id") == source_room]
            if matches:
                matches.sort(key=lambda entry: entry["sim_minute"])
                settlement = matches[0]
                receipt = settlement["receipt"]
                stored_ids = {row.get("receipt_id") for row in receipts
                              if isinstance(row, Mapping)}
                inventory_after = {str(value) for value in receipt.get("after_inventory_ids", [])}
                if expected_kind == "move":
                    transition_observed = receipt.get("after_room_id") == intent_contract.get("destination_id")
                elif expected_kind == "get":
                    transition_observed = str(expected_item) in inventory_after
                else:
                    transition_observed = (receipt.get("after_item_room_id") == intent_contract.get("room_id")
                                           and str(expected_item) not in inventory_after)
                semantic_joins.append({"intent_operation_id": operation_id,
                                       "receipt_id": receipt.get("receipt_id"),
                                       "status": settlement.get("status"),
                                       "receipt_settled": receipt.get("settled"),
                                       "expected_transition_observed": transition_observed,
                                       "actual_before_room_id": receipt.get("before_room_id"),
                                       "actual_after_room_id": receipt.get("after_room_id"),
                                       "actual_after_item_room_id": receipt.get("after_item_room_id"),
                                       "settled_receipt_stored": receipt.get("receipt_id") in stored_ids,
                                       "item_id": expected_item,
                                       "destination_id": (intent_contract.get("destination_id")
                                           if expected_kind == "move" else
                                           intent_contract.get("room_id") if expected_kind == "drop"
                                           else source_room),
                                       "primitive": expected_kind,
                                       "join_method": "sequenced_single_pending_callback_semantic",
                                       "join_basis": "same actor + next later exact intent + item + primitive + destination; native receipt omits operation_id"})
        pending_before = before_actors.get(alias, {}).get("pending_action")
        pending_after = after_actors.get(alias, {}).get("pending_action")
        result[alias] = {"existing_task_binding": dict(binding) if isinstance(binding, Mapping) else {},
                         "goal_choice_count": len(choices), "primitive_intent_count": len(intents),
                         "intent_operation_ids": operation_ids,
                         "receipt_operation_ids": receipt_ids,
                         "intent_receipt_operation_id_matches": sorted(set(operation_ids)
                             & set(receipt_ids)), "task_binding_matches": binding_match,
                         "intent_receipt_semantic_joins": semantic_joins,
                         "operation_id_receipt_join_status": ("JOINED" if set(operation_ids)
                             & set(receipt_ids) else "UNAVAILABLE_NATIVE_RECEIPT_SCHEMA"
                             if operation_ids and receipts and not receipt_ids else "NO_MATCHING_EVIDENCE"),
                         "execution_settlements": [{"sim_minute": row.get("sim_minute"),
                             "status": row.get("status"), "intent": row.get("intent"),
                             "receipt": row.get("receipt"), "detail": row.get("detail")}
                             for row in settlements],
                         "pending_before": pending_before, "pending_after": pending_after,
                         "pending_operation_id_retained": bool(isinstance(pending_before, Mapping)
                             and isinstance(pending_after, Mapping)
                             and pending_before.get("operation_id")
                             and pending_before.get("operation_id") == pending_after.get("operation_id")),
                         "receipt_statuses": [receipt.get("status") for receipt in receipts
                                              if isinstance(receipt, Mapping)]}
    return result


def build_step_audit(*, decoded_plan: Mapping[str, Any], native_step: Mapping[str, Any],
                     before_trace: Mapping[str, Any], after_trace: Mapping[str, Any],
                     candidate_bundle_version: int,
                     hard_requirements: tuple[tuple[str, str, int, int, str], ...] = (),
                     candidate_constraint_statuses: tuple[tuple[str, str], ...] = ()) -> dict[str, Any]:
    """Join one Sabre prediction with the subsequent sealed native step."""
    actions = decoded_plan.get("ordered_actions", decoded_plan.get("prediction_only_actions", []))
    actions = actions if isinstance(actions, list) else []
    old_ledger = before_trace.get("ledger", [])
    new_ledger = after_trace.get("ledger", [])
    old_rows = [row for row in old_ledger if isinstance(row, Mapping)]
    new_rows = [row for row in new_ledger if isinstance(row, Mapping)]
    prefix_preserved = (len(new_rows) >= len(old_rows)
                        and [_digest(row) for row in new_rows[:len(old_rows)]]
                        == [_digest(row) for row in old_rows])
    before_minute, after_minute = before_trace.get("now"), after_trace.get("now")
    before_world = before_trace.get("world_snapshots", [])
    after_world = after_trace.get("world_snapshots", [])
    old_snapshot = next((row for row in before_world if isinstance(row, Mapping)
                         and row.get("minute") == before_minute), {})
    new_snapshot = next((row for row in after_world if isinstance(row, Mapping)
                         and row.get("minute") == after_minute), {})
    before_actors = {row.get("actor_alias"): row for row in before_trace.get("actor_evidence", [])
                     if isinstance(row, Mapping)}
    after_actors = {row.get("actor_alias"): row for row in after_trace.get("actor_evidence", [])
                    if isinstance(row, Mapping)}
    old_pending = {actor: before_actors.get(actor, {}).get("pending_action") for actor in ("A", "B")}
    new_pending = {actor: after_actors.get(actor, {}).get("pending_action") for actor in ("A", "B")}
    assumptions = [action for action in actions if isinstance(action, str)
                   and (action.startswith("respond_note(") or action.startswith("request_note("))]
    binding_rows = before_trace.get("world_capability_projection", {}).get("task_bindings", {})
    candidate_actor_steps = decoded_plan.get("actor_task_steps", [])
    candidate_binding_join = []
    for candidate in candidate_actor_steps if isinstance(candidate_actor_steps, list) else []:
        if not isinstance(candidate, Mapping) or candidate.get("actor") not in {"A", "B"}:
            continue
        actor = candidate["actor"]
        binding = binding_rows.get(actor, {}) if isinstance(binding_rows, Mapping) else {}
        expected_item = "Supply" if actor == "A" else "Parcel"
        candidate_binding_join.append({"candidate_step": dict(candidate),
            "native_actor": actor, "native_task_binding": dict(binding) if isinstance(binding, Mapping) else {},
            "actor_has_registered_existing_task_binding": (isinstance(binding, Mapping)
                and binding.get("item_alias") == ("courier_supply" if actor == "A" else "resident_parcel")
                and binding.get("destination_id") is not None),
            "candidate_item_matches_existing_task": (None if candidate.get("item") is None else
                candidate.get("item") == expected_item and isinstance(binding, Mapping)
                and binding.get("item_alias") == ("courier_supply" if actor == "A" else "resident_parcel")),
            "handoff": "PREDICTION_ONLY_NOT_DISPATCHED"})
    response_rows = [row for row in new_rows if row.get("event_type") == "P5_NOTE_RESPONSE"
                     or (isinstance(row.get("typed_args"), Mapping)
                         and row["typed_args"].get("event_type") == "p5_note_response")]
    active_identity = after_trace.get("bundle_identity", {})
    after_verdicts = after_trace.get("verdicts", [])
    after_statuses = {row.get("constraint_id"): row.get("status") for row in after_verdicts
                      if isinstance(row, Mapping)}
    before_statuses = dict(candidate_constraint_statuses)
    deadlines = [{"constraint_id": row[0], "absolute_start_minute": row[2],
                  "absolute_deadline_minute": row[3],
                  "candidate_status": before_statuses.get(row[0]),
                  "native_status_after_step": after_statuses.get(row[0]),
                  "still_in_window_after_step": (type(after_minute) is int and after_minute <= row[3])}
                 for row in hard_requirements]
    return {"schema": "planner-adapter-native-join-audit-v1",
            "candidate_bundle_version": candidate_bundle_version,
            "native_bundle_identity_after_step": active_identity,
            "bundle_version_changed": (isinstance(active_identity, Mapping)
                and active_identity.get("version") != candidate_bundle_version),
            "candidate_actions_prediction_only": actions,
            "candidate_actor_task_binding_join": candidate_binding_join,
            "handoff_status": decoded_plan.get("handoff_status", "PREDICTION_ONLY_NOT_DISPATCHED"),
            "native_dynamic_task_dispatch_supported": False,
            "actor_evidence_join": _native_actor_evidence(native_step, before_trace, after_trace),
            "feedback": {"minute_before": before_minute, "minute_after": after_minute,
                         "time_monotonic": (type(before_minute) is int and type(after_minute) is int
                                             and after_minute >= before_minute),
                         "sealed_historical_ledger_prefix_preserved": prefix_preserved,
                         "ledger_rows_before": len(old_rows), "ledger_rows_after": len(new_rows),
                         "route_state_before": old_snapshot.get("routes"),
                         "route_state_after": new_snapshot.get("routes"),
                         "route_state_changed": old_snapshot.get("routes") != new_snapshot.get("routes"),
                         "item_locations_before": old_snapshot.get("item_locations"),
                         "item_locations_after": new_snapshot.get("item_locations"),
                         "item_support_changed": old_snapshot.get("item_locations")
                                                != new_snapshot.get("item_locations"),
                         "absolute_deadline_status": deadlines,
                         "pending_before": old_pending, "pending_after": new_pending,
                         "pending_identity_retained": any(
                             isinstance(old_pending.get(actor), Mapping)
                             and isinstance(new_pending.get(actor), Mapping)
                             and old_pending[actor].get("operation_id")
                             and old_pending[actor].get("operation_id")
                             == new_pending[actor].get("operation_id")
                             for actor in ("A", "B")),
                         "candidate_response_assumptions": assumptions,
                         "native_response_ledger_rows": response_rows,
                         "response_assumption_replaced_by_native_event": bool(assumptions
                             and response_rows),
                         "edit_or_intervention_receipts": [row for round_row in native_step.get("rounds", [])
                             if isinstance(round_row, Mapping)
                             for row in [*round_row.get("edits", []), *round_row.get("interventions", [])]]}}


__all__ = ["build_step_audit"]
