"""Evidence-only checks for the first no-author ongoing-station case."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from typing import Any


def _rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _scene_db(db: Mapping[str, Any], scene_id: str) -> Mapping[str, Any] | None:
    scenes = db.get("scenes", [])
    if not isinstance(scenes, list):
        return None
    return next((row for row in scenes if isinstance(row, Mapping)
                 and row.get("scene_id") == scene_id), None)


def _actor_native_state(db: Mapping[str, Any], actor_id: int,
                        scene_id: str) -> tuple[list[dict[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
    scene = _scene_db(db, scene_id)
    objects = scene.get("objects", []) if isinstance(scene, Mapping) else []
    for obj in objects if isinstance(objects, list) else []:
        if not isinstance(obj, Mapping) or obj.get("id") != actor_id:
            continue
        attrs = obj.get("attributes", {})
        if not isinstance(attrs, Mapping):
            return [], {}, {}
        native = attrs.get("native_p3", {})
        if not isinstance(native, Mapping):
            native = {}
        station = attrs.get("native_p5", {})
        if not isinstance(station, Mapping):
            station = {}
        return _rows(native.get("native_receipts", [])), native, station
    return [], {}, {}


def _no_author_profile(db: Mapping[str, Any], scene_id: str,
                       scene_identity: Mapping[str, Any]) -> bool:
    scene = _scene_db(db, scene_id)
    rooms = scene_identity.get("rooms", {})
    origin_id = rooms.get("origin") if isinstance(rooms, Mapping) else None
    objects = scene.get("objects", []) if isinstance(scene, Mapping) else []
    pickup = next((row for row in objects if isinstance(row, Mapping)
                   and row.get("id") == origin_id), None)
    attrs = pickup.get("attributes", {}) if isinstance(pickup, Mapping) else {}
    station = attrs.get("native_p5", {}) if isinstance(attrs, Mapping) else {}
    if not isinstance(station, Mapping):
        return False
    profile = station.get("p5_ongoing_station_profile")
    meta = station.get("p5_ongoing_station_meta")
    return (isinstance(profile, Mapping) and profile.get("author", "missing") is None
            and isinstance(meta, Mapping) and meta.get("author_status") == "ABSENT"
            and station.get("p5_ongoing_station_author") is None
            and station.get("p5_ongoing_station_staged_author") is None)


def audit_t1(trace: Mapping[str, Any], scene: Mapping[str, Any],
             db: Mapping[str, Any]) -> dict[str, Any]:
    """Check author-free self-goal -> physical settlement -> next self-goal.

    Missing or schema-drifted evidence is NOT_CERTIFIED, never inferred from a
    planner proposal or the episode's final status.
    """
    station = trace.get("ongoing_station")
    if not isinstance(station, Mapping):
        return {"schema": "ongoing-station-t1-audit-v1", "status": "NOT_CERTIFIED",
                "pass": False, "reason": "final trace omitted ongoing_station evidence"}
    decisions = _rows(station.get("actor_goal_decisions", station.get("actor_decisions")))
    if not decisions:
        for actor_row in _rows(trace.get("actor_evidence")):
            for log_row in _rows(actor_row.get("log")):
                if log_row.get("kind") == "ongoing_station_decision":
                    decisions.append(log_row)
    commitments = _rows(station.get("commitments", station.get("actor_commitments")))
    scene_id = trace.get("scene_id")
    scene_actors = scene.get("actors", {})
    aliases = {alias: row.get("id") for alias, row in scene_actors.items()
               if isinstance(scene_actors, Mapping) and isinstance(row, Mapping)}
    activation_events = station.get("activation_events", [])
    activation_ids = station.get("activation_event_ids", [])
    has_author_activation = bool(activation_events or activation_ids)
    db_has_null_author_profile = (isinstance(scene_id, str)
                                  and _no_author_profile(db, scene_id, scene))
    author_sources = [row for row in decisions
                      if row.get("source") == "AUTHOR"
                      or (isinstance(row.get("commitment"), Mapping)
                          and row["commitment"].get("source") == "AUTHOR")]
    per_actor: dict[str, Any] = {}
    for alias in ("A", "B"):
        actor_id = aliases.get(alias)
        actor_decisions = [row for row in decisions if row.get("actor_id") == actor_id]
        self_decisions = [row for row in actor_decisions
                          if (isinstance(row.get("commitment"), Mapping)
                              and row["commitment"].get("source") == "SELF")]
        actor_commitments = [row for row in commitments
                             if (row.get("actor_id") == actor_id or row.get("actor_alias") == alias)
                             and row.get("source") == "SELF"]
        settled = [row for row in actor_commitments
                   if row.get("status") == "SETTLED" and row.get("receipt_ids")]
        physical_receipts, native_actor, station_actor = (_actor_native_state(db, actor_id, scene_id)
                                                          if type(actor_id) is int and isinstance(scene_id, str)
                                                          else ([], {}, {}))
        persisted_commitments = _rows(station_actor.get("ongoing_commitments", []))
        if persisted_commitments:
            actor_commitments = persisted_commitments
        receipt_rows = {row.get("receipt_id"): row for row in physical_receipts
                        if row.get("settled") is True and row.get("receipt_id")}
        receipt_ids = set(receipt_rows)
        witnessed_settled = [row for row in settled
                             if any(receipt_id in receipt_ids
                                    and receipt_rows[receipt_id].get("ongoing_commitment_id") == row.get("commitment_id")
                                    for receipt_id in row.get("receipt_ids", []))]
        later_self_choice = False
        for commitment in witnessed_settled:
            settled_at = commitment.get("updated_minute")
            goal_id = commitment.get("goal_id")
            if type(settled_at) is not int:
                continue
            for selected in actor_decisions:
                later = selected.get("commitment")
                if (not isinstance(later, Mapping) or later.get("source") != "SELF"
                        or later.get("goal_id") == goal_id
                        or not later.get("commitment_id")
                        or later.get("commitment_id") == commitment.get("commitment_id")
                        or type(selected.get("minute")) is not int
                        or selected["minute"] <= settled_at):
                    continue
                later_row = next((row for row in actor_commitments
                                  if row.get("commitment_id") == later.get("commitment_id")
                                  and row.get("source") == "SELF"), None)
                later_receipt = bool(later_row and any(
                    receipt_id in receipt_ids
                    and receipt_rows[receipt_id].get("ongoing_commitment_id") == later_row.get("commitment_id")
                    for receipt_id in later_row.get("receipt_ids", [])))
                pending = native_actor.get("pending_action")
                pending_task = pending.get("ongoing_task") if isinstance(pending, Mapping) else None
                pending_for_later = (isinstance(pending_task, Mapping)
                                     and pending_task.get("commitment_id") == later.get("commitment_id"))
                if later_row and later_row.get("status") in {"ACCEPTED", "IN_PROGRESS", "SETTLED"} \
                        and (later_receipt or pending_for_later):
                    later_self_choice = True
                    break
            if later_self_choice:
                break
        per_actor[alias] = {
            "actor_id": actor_id,
            "self_goal_decision_count": len(self_decisions),
            "self_commitment_count": len(actor_commitments),
            "settled_self_commitments_with_native_db_receipt": len(witnessed_settled),
            "later_distinct_self_goal_selected_and_dispatched_or_pending": later_self_choice,
            "pass": bool(witnessed_settled and later_self_choice),
        }
    passed = (all(row.get("pass") is True for row in per_actor.values())
              and not has_author_activation and not author_sources
              and isinstance(_scene_db(db, scene_id), Mapping)
              and db_has_null_author_profile)
    return {"schema": "ongoing-station-t1-audit-v1",
            "status": "PASS" if passed else "NOT_CERTIFIED",
            "pass": passed,
            "criteria": {
                "zero_author_activation": not has_author_activation and not author_sources,
                "independent_db_confirms_author_null": db_has_null_author_profile,
                "both_roles_self_goal_settle_then_reselect": all(
                    row.get("pass") is True for row in per_actor.values()),
                "trace_db_scene_identity_matches": isinstance(_scene_db(db, scene_id), Mapping)},
            "actors": per_actor,
            "evidence_source": "native actor decisions + persisted Evennia commitments + independent Evennia DB receipts",
            "limits": ["Does not establish psychological realism or algorithmic advantage."]}


def _source_digest(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _event_rows(trace: Mapping[str, Any], kind: str) -> list[dict[str, Any]]:
    return [row for row in _rows(trace.get("ledger")) if row.get("event_type") == kind]


def _published_controller_tasks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project only tasks named by the controller's persisted published-ID set."""
    result: list[dict[str, Any]] = []
    for row in rows:
        decision = row.get("decision", {})
        if not isinstance(decision, Mapping):
            continue
        explicit = _rows(decision.get("task_requests"))
        if explicit:
            for task in explicit:
                result.append({**task,
                    "offer_id": task.get("offer_id", task.get("request_id")),
                    "constraint_id": task.get("constraint_id", row.get("constraint_id")),
                    "source_version": task.get("source_version", row.get("source_version")),
                    "deadline_minute": task.get("deadline_minute",
                        decision.get("guards", {}).get("absolute_deadline_minute")
                        if isinstance(decision.get("guards"), Mapping) else None)})
            continue
        raw_ids = row.get("offer_ids", [])
        published_ids = {str(value) for value in raw_ids
                         if isinstance(raw_ids, list) and value is not None}
        for task in _rows(decision.get("decomposition")):
            request_id = task.get("request_id")
            if request_id is None or str(request_id) not in published_ids:
                continue
            result.append({**task, "offer_id": str(request_id),
                "constraint_id": row.get("constraint_id"),
                "source_version": row.get("source_version"),
                "deadline_minute": task.get("deadline_minute",
                    decision.get("guards", {}).get("absolute_deadline_minute")
                    if isinstance(decision.get("guards"), Mapping) else None)})
    return result


def audit_author_pair(trace: Mapping[str, Any], scene: Mapping[str, Any],
                      db: Mapping[str, Any], expected_author: Mapping[str, Any],
                      *, edit_author: Mapping[str, Any] | None = None,
                      activation_minute: int = 5) -> dict[str, Any]:
    """Certify the mixed result/locked-source edit from trace and DB evidence."""
    station = trace.get("ongoing_station")
    station = station if isinstance(station, Mapping) else {}
    scene_id = trace.get("scene_id")
    db_scene = _scene_db(db, scene_id) if isinstance(scene_id, str) else None
    objects = db_scene.get("objects", []) if isinstance(db_scene, Mapping) else []
    origin_id = scene.get("rooms", {}).get("origin") if isinstance(scene.get("rooms"), Mapping) else None
    pickup = next((row for row in objects if isinstance(row, Mapping) and row.get("id") == origin_id), None)
    pickup_attrs = pickup.get("attributes", {}) if isinstance(pickup, Mapping) else {}
    pickup_p5 = pickup_attrs.get("native_p5", {}) if isinstance(pickup_attrs, Mapping) else {}
    pickup_p5 = pickup_p5 if isinstance(pickup_p5, Mapping) else {}
    raw_profile = pickup_p5.get("p5_ongoing_station_profile")
    meta = pickup_p5.get("p5_ongoing_station_meta", {})
    stored_author = pickup_p5.get("p5_ongoing_station_author")
    expected_final = edit_author or expected_author
    activation_rows = _rows(station.get("activation_events"))
    activation = next((row for row in activation_rows
                       if row.get("event_type") == "P5_ONGOING_STATION_ACTIVATION"
                       and row.get("minute") == activation_minute
                       and row.get("typed_args", {}).get("result", {}).get("status") == "ACTIVATED"), None)
    controller = [row for row in _rows(station.get("controller_decisions"))
                  if row.get("source_version") == 1 and row.get("minute", 0) >= activation_minute]
    offers = _published_controller_tasks(controller)
    # Evidence API also preserves the exact last-published offer set.
    offers.extend(_rows(station.get("pending_offers")))
    expected_sha = _source_digest(expected_author)
    final_sha = _source_digest(expected_final)
    typed = _rows(station.get("typed_events"))
    note_id = station.get("bound_note_id")
    responses = [row for row in typed if row.get("event_type") == "p5_note_response"
                 and row.get("args", {}).get("item", {}).get("stable_id") == str(note_id)]
    archives = [row for row in typed if row.get("event_type") == "p5_note_archived"
                and row.get("args", {}).get("item", {}).get("stable_id") == str(note_id)]
    response = next((row for row in responses for archive in archives
                     if (row.get("time", 2**63) < archive.get("time", -1)
                         or (row.get("time") == archive.get("time")
                             and row.get("sequence", 2**63) < archive.get("sequence", -1)))), None)
    archive = next((row for row in archives if response and
                    (row.get("time", -1) > response.get("time", 2**63)
                     or (row.get("time") == response.get("time")
                         and row.get("sequence", -1) > response.get("sequence", 2**63)))), None)
    commitments = _rows(station.get("commitments"))
    actor_rows = {alias: scene.get("actors", {}).get(alias, {}).get("id")
                  for alias in ("A", "B")}
    db_receipts: dict[int, list[dict[str, Any]]] = {}
    for actor_id in actor_rows.values():
        if type(actor_id) is int:
            db_receipts[actor_id] = _actor_native_state(db, actor_id, scene_id)[0]
    locked_hash = next((row.get("locked_fragment", {}).get("sequence_sha256")
                        for row in expected_author.get("bindings", [])
                        if isinstance(row.get("locked_fragment"), Mapping)), None)
    archive_binding = next((row for row in expected_author.get("bindings", [])
                            if row.get("constraint_id") == "archive-note-by-horizon"), {})
    order_binding = next((row for row in expected_author.get("bindings", [])
                          if row.get("constraint_id") == "respond-before-archive"), {})
    edit_events = [row for row in _event_rows(trace, "P5_INTERVENTION")
                   if row.get("typed_args", {}).get("kind") == "ongoing_station_author_edit"]
    edit_row = next((row for row in edit_events
                     if row.get("typed_args", {}).get("settlement", {}).get("status") == "UPDATED"
                     and row.get("minute") == activation_minute + 1), None)
    edit_result = edit_row.get("typed_args", {}).get("settlement", {}) if edit_row else {}
    projection_history = _rows(station.get("projection_history"))
    version_one_projection = next((row for row in projection_history if row.get("version") == 1), {})
    version_two_projection = next((row for row in projection_history if row.get("version") == 2), {})
    stale_projection_ids = set(station.get("stale_projection_ids", []))
    controller = _rows(station.get("controller_decisions"))
    conflict = next((row for row in controller
                     if row.get("source_version") == 1
                     and row.get("constraint_id") == "archive-note-by-horizon"
                     and row.get("decision", {}).get("status") == "LOCKED_CONSTRAINT_CONFLICT"), {})
    conflict_decision = conflict.get("decision", {})
    conflict_result_method = next((task.get("source_method_id")
        for task in _rows(conflict_decision.get("decomposition"))
        if task.get("source_method_id") is not None), None)
    conflict_method_was_feasible = any(method.get("method_id") == conflict_result_method
        and method.get("feasible") is True
        for method in _rows(conflict_decision.get("attempted_methods")))
    combined_lock = conflict_decision.get("combined_locked_core", {})
    v2_archive = next((row for row in controller
                       if row.get("source_version") == 2
                       and row.get("constraint_id") == "archive-note-by-horizon"
                       and row.get("decision", {}).get("selected_method") == "return_then_file_by_A"), {})
    lock_offers = [offer for offer in _published_controller_tasks(_rows(station.get("controller_decisions")))
                   if offer.get("source_version") == 2
                   and offer.get("constraint_id") == "respond-before-archive"]
    locked_commitments = [row for row in commitments
                          if row.get("source") == "AUTHOR"
                          and row.get("constraint_id") == "respond-before-archive"
                          and row.get("source_method_id") == "locked_fragment"
                          and row.get("locked_fragment_hash") == locked_hash
                          and row.get("status") == "SETTLED"]
    give_commitment = next((row for row in locked_commitments
                            if row.get("task_kind") == "handover_note"
                            and row.get("actor_alias") == "B"
                            and row.get("locked_sequence_index") == 0), None)
    archive_commitment = next((row for row in locked_commitments
                               if row.get("task_kind") == "archive_note"
                               and row.get("actor_alias") == "A"
                               and row.get("locked_sequence_index") == 1), None)
    locked_typed = [row for row in typed
                    if row.get("native_constraint_id") == "respond-before-archive"
                    and row.get("native_control_source") == "LOCKED_FRAGMENT"
                    and row.get("native_source_method_id") == "locked_fragment"
                    and row.get("native_grant_id")
                    and row.get("native_locked_fragment_hash") == locked_hash]
    give_event = next((row for row in locked_typed
                       if row.get("event_type") == "p5_note_handed_over"
                       and row.get("native_locked_sequence_index") == 0), None)
    locked_archive_event = next((row for row in locked_typed
                                 if row.get("event_type") == "p5_note_archived"
                                 and row.get("native_locked_sequence_index") == 1), None)
    locked_receipts = []
    for commitment in (give_commitment, archive_commitment):
        if not commitment:
            continue
        actor_id = commitment.get("actor_id")
        locked_receipts.extend(receipt for receipt in db_receipts.get(actor_id, [])
                               if receipt.get("settled") is True
                               and receipt.get("receipt_id") in commitment.get("receipt_ids", [])
                               and receipt.get("ongoing_commitment_id") == commitment.get("commitment_id")
                               and receipt.get("ongoing_task_kind") == commitment.get("task_kind")
                               and receipt.get("item_id") == note_id)
    verdicts = _rows(station.get("real_verdicts", {}).get("constraints")
                     if isinstance(station.get("real_verdicts"), Mapping) else [])
    archive_verdict = next((row for row in verdicts
                            if row.get("constraint_id") == "archive-note-by-horizon"), {})
    order_verdict = next((row for row in verdicts
                          if row.get("constraint_id") == "respond-before-archive"), {})
    criteria = {
        "exact_scene_database_readback": isinstance(db_scene, Mapping),
        "stored_author_matches_final_fixed_input": stored_author == expected_final,
        "activation_at_fixed_minute": bool(activation),
        "version_two_source_and_hash_match": (station.get("author_status") == "ACTIVE"
                                              and station.get("active_author_version") == 2
                                              and station.get("active_author_sha256") == final_sha
                                              and isinstance(meta, Mapping)
                                              and meta.get("active_author_version") == 2
                                              and isinstance(raw_profile, Mapping)
                                              and raw_profile.get("author") == expected_author),
        "future_edit_was_a_successful_cas": bool(edit_row and edit_result.get("version") == 2
                                                 and edit_result.get("source_sha256") == final_sha),
        "v1_method_search_and_locked_conflict": (
            conflict_decision.get("status") == "LOCKED_CONSTRAINT_CONFLICT"
            and conflict_result_method == "file_by_B" and conflict_method_was_feasible
            and conflict_decision.get("selected_method") in {None, ""}
            and combined_lock.get("constraint_id") == "respond-before-archive"
            and combined_lock.get("required_method") == "return_then_file_by_A"
            and combined_lock.get("compatible_method_feasible") is False),
        "v1_conflict_did_not_publish_an_actor_offer": bool(conflict)
            and not conflict.get("offer_ids"),
        "v2_result_search_selects_compatible_method": bool(v2_archive)
            and v2_archive["decision"].get("search_selected_method") == "return_then_file_by_A",
        "old_projection_marked_stale_and_new_projection_active": (
            bool(version_one_projection.get("projection_id"))
            and version_one_projection.get("projection_id") in stale_projection_ids
            and version_two_projection.get("projection_id")
            and version_two_projection.get("source_sha256") == final_sha),
        "locked_sequence_unchanged_across_versions": (
            bool(locked_hash) and locked_hash == next((row.get("locked_fragment", {}).get("sequence_sha256")
                for row in expected_final.get("bindings", [])
                if isinstance(row.get("locked_fragment"), Mapping)), None)
            and expected_author.get("bundle", {}).get("constraints")
                == expected_final.get("bundle", {}).get("constraints")),
        "v2_locked_offers_are_registered": bool(lock_offers)
            and all(row.get("source_method_id") == "locked_fragment"
                    and row.get("constraint_id") == "respond-before-archive"
                    for row in lock_offers),
        "locked_tasks_settle_in_exact_order": bool(give_commitment and archive_commitment
            and give_event and locked_archive_event
            and give_event.get("time", 2**63) < locked_archive_event.get("time", -1)
            and give_event.get("native_grant_id") == locked_archive_event.get("native_grant_id")
            and give_commitment.get("grant_id") == archive_commitment.get("grant_id")
            and any(row.get("kind") == "give" for row in locked_receipts)
            and any(row.get("kind") == "drop" for row in locked_receipts)),
        "same_note_response_then_archive": bool(response and archive and archive.get("time", 2**63) <= 24),
        "archive_has_exact_native_db_receipt": bool(archive_commitment and any(
            receipt.get("kind") == "drop" and receipt.get("item_id") == note_id
            and receipt.get("after_item_room_id") == archive_commitment.get("destination_id")
            for receipt in locked_receipts)),
        "native_goal_verdict_satisfied": archive_verdict.get("status") == "SATISFIED",
        "native_order_verdict_satisfied": order_verdict.get("status") == "SATISFIED",
    }
    passed = all(criteria.values())
    return {"schema": "ongoing-station-author-pair-audit-v1",
            "status": "PASS" if passed else "NOT_CERTIFIED", "pass": passed,
            "criteria": criteria, "note_id": note_id,
            "response_event_id": response.get("event_id") if response else None,
            "archive_event_id": archive.get("event_id") if archive else None,
            "v1_controller_decision_id": conflict.get("decision_id"),
            "v1_controller_decision_source_path": (
                f"ongoing_station.controller_decisions[{controller.index(conflict)}]"
                if conflict else None),
            "v2_projection_id": version_two_projection.get("projection_id"),
            "stale_projection_ids": sorted(stale_projection_ids),
            "locked_receipt_ids": [row.get("receipt_id") for row in locked_receipts],
            "limits": ["A successful matched arm is not evidence of GT superiority.",
                       "Actor autonomy is evidenced only through native decisions and receipts."]}


def audit_actor_deferral(trace: Mapping[str, Any], scene: Mapping[str, Any],
                         db: Mapping[str, Any], *, expected_author: Mapping[str, Any],
                         edit_author: Mapping[str, Any] | None = None,
                         activation_minute: int = 5, edit_minute: int = 8) -> dict[str, Any]:
    station = trace.get("ongoing_station", {})
    station = station if isinstance(station, Mapping) else {}
    decisions = _rows(station.get("controller_decisions"))
    offers = [offer for offer in _published_controller_tasks(decisions)
              if offer.get("source_version") == 1]
    history = station.get("actor_goal_history", {})
    history_rows = [entry for values in history.values() for entry in _rows(values)] \
        if isinstance(history, Mapping) else []
    deferred = next((row for row in history_rows
                     if row.get("event") == "AUTHOR_OFFER_DEFERRED"
                     and row.get("blocking_commitment_id")
                     and row.get("blocking_commitment_status") in {"ACCEPTED", "IN_PROGRESS"}), None)
    commitments = _rows(station.get("commitments"))
    blocker = next((row for row in commitments
                    if row.get("commitment_id") == (deferred or {}).get("blocking_commitment_id")
                    and row.get("source") == "SELF" and row.get("task_kind") == "routine_route"), None)
    offered = next((row for row in offers if row.get("offer_id") == (deferred or {}).get("offer_id")), None)
    activated = any(row.get("minute") == activation_minute
                    and row.get("typed_args", {}).get("result", {}).get("status") == "ACTIVATED"
                    for row in _rows(station.get("activation_events")))
    decisions_by_actor = _rows(station.get("actor_goal_decisions"))
    preserved_prefix = any(row.get("minute", activation_minute + 1) <= activation_minute
        and isinstance(row.get("commitment"), Mapping)
        and row["commitment"].get("source") == "SELF"
        and row["commitment"].get("task_kind") == "routine_route"
        for row in decisions_by_actor)
    old_offer_ids = {str(row.get("offer_id")) for row in offers if row.get("offer_id")}
    stale_offer_ids = {str(value) for value in station.get("stale_offer_ids", [])}
    cancelled = next((row for row in commitments
                      if row.get("source") == "AUTHOR"
                      and row.get("source_method_id") == "return_then_file_by_A"
                      and row.get("task_kind") == "handover_note"
                      and row.get("actor_alias") == "B"
                      and row.get("status") == "CANCELLED_STALE"
                      and str(row.get("source_offer_id")) in old_offer_ids), None)
    cancellation_rows = [entry for values in history.values() for entry in _rows(values)
                         if isinstance(history, Mapping)] if isinstance(history, Mapping) else []
    cancellation = next((row for row in cancellation_rows
                         if row.get("event") == "COMMITMENT_CANCELLED_STALE"
                         and row.get("commitment_id") == (cancelled or {}).get("commitment_id")), None)
    edit_events = [row for row in _event_rows(trace, "P5_INTERVENTION")
                   if row.get("typed_args", {}).get("kind") == "ongoing_station_author_edit"]
    edit = next((row for row in edit_events if row.get("minute") == edit_minute
                 and row.get("typed_args", {}).get("settlement", {}).get("status") == "UPDATED"), None)
    edit_result = edit.get("typed_args", {}).get("settlement", {}) if edit else {}
    invalidated_offer_ids = {str(value) for value in edit_result.get("invalidated_offer_ids", [])}
    final_author = edit_author or expected_author
    final_sha = _source_digest(final_author)
    v2_file = next((row for row in decisions if row.get("source_version") == 2
                    and row.get("constraint_id") == "archive-note-by-horizon"
                    and (row.get("decision", {}).get("selected_method") == "file_by_B"
                         or row.get("decision", {}).get("search_selected_method") == "file_by_B")), None)
    actor_ids = {alias: row.get("id") for alias, row in scene.get("actors", {}).items()
                 if isinstance(scene.get("actors"), Mapping) and isinstance(row, Mapping)}
    old_task_alias = cancelled.get("actor_alias") if cancelled else None
    old_task_actor = actor_ids.get(old_task_alias)
    old_actor_receipts, old_actor_native, _ = _actor_native_state(
        db, old_task_actor, trace.get("scene_id")) if type(old_task_actor) is int \
        else ([], {}, {})
    pre_edit_move = any(row.get("kind") == "move" and row.get("settled") is True
                        and row.get("sim_minute") == edit_minute - 2
                        and row.get("ongoing_commitment_id")
                            == (deferred or {}).get("blocking_commitment_id")
                        for row in old_actor_receipts)
    old_action_still_pending = False
    pending = old_actor_native.get("pending_action")
    pending_task = pending.get("ongoing_task") if isinstance(pending, Mapping) else None
    if isinstance(pending_task, Mapping):
        old_action_still_pending = str(pending_task.get("source_offer_id")) in old_offer_ids
    db_scene = _scene_db(db, trace.get("scene_id"))
    db_objects = db_scene.get("objects", []) if isinstance(db_scene, Mapping) else []
    origin_id = scene.get("rooms", {}).get("origin") if isinstance(scene.get("rooms"), Mapping) else None
    pickup = next((row for row in db_objects if isinstance(row, Mapping) and row.get("id") == origin_id), None)
    pickup_attrs = pickup.get("attributes", {}) if isinstance(pickup, Mapping) else {}
    pickup_station = pickup_attrs.get("native_p5", {}) if isinstance(pickup_attrs, Mapping) else {}
    pickup_station = pickup_station if isinstance(pickup_station, Mapping) else {}
    stored_author = pickup_station.get("p5_ongoing_station_author")
    criteria = {
        "exact_scene_database_readback": isinstance(db_scene, Mapping),
        "fixed_author_source_activated": activated,
        "controller_published_native_author_offer": bool(offered),
        "v1_return_method_offered_B_handover": bool(offered
            and offered.get("source_method_id") == "return_then_file_by_A"
            and offered.get("task_kind") == "handover_note"
            and offered.get("actor_alias") == "B"
            and expected_author.get("bindings", [{}])[0].get("control", {}).get("file_actor") == "A"),
        "actor_history_records_real_deferral": bool(deferred),
        "deferral_names_live_self_route_commitment": bool(deferred and blocker
            and deferred.get("blocking_task_kind") == "routine_route"
            and blocker.get("status") in {"ACCEPTED", "IN_PROGRESS", "SETTLED"}),
        "offer_is_the_deferred_offer": bool(offered and deferred
            and offered.get("offer_id") == deferred.get("offer_id")),
        "prefix_decisions_preserved": preserved_prefix,
        "author_deadline_is_fixed": all(row.get("deadline_minute") == 24 for row in offers),
        "future_edit_switches_compatible_filer": bool(edit and edit_result.get("version") == 2
            and edit_result.get("source_sha256") == final_sha
            and final_author.get("bundle", {}).get("constraints")
                == expected_author.get("bundle", {}).get("constraints")),
        "final_author_version_persisted_in_db": (stored_author == final_author
            and station.get("author_status") == "ACTIVE"
            and station.get("active_author_version") == 2
            and station.get("active_author_sha256") == final_sha
            and pickup_station.get("p5_ongoing_station_author") == final_author),
        "v2_replans_to_file_by_B": bool(v2_file),
        "v2_input_changes_only_filer_to_B": bool(expected_author.get("bundle", {}).get("constraints")
            == final_author.get("bundle", {}).get("constraints")
            and expected_author.get("bundle", {}).get("bundle_id")
            == final_author.get("bundle", {}).get("bundle_id")
            and expected_author.get("bindings", [{}])[0].get("control", {}).get("file_actor") == "A"
            and final_author.get("bindings", [{}])[0].get("control", {}).get("file_actor") == "B"),
        "old_undispatched_suffix_cancelled": bool(cancelled and cancellation
            and str(cancelled.get("source_offer_id")) in invalidated_offer_ids
            and not old_action_still_pending),
        "pre_edit_self_route_prefix_receipt_preserved": pre_edit_move,
    }
    passed = all(criteria.values())
    return {"schema": "ongoing-station-actor-deferral-audit-v1",
            "status": "PASS" if passed else "NOT_CERTIFIED", "pass": passed,
            "criteria": criteria, "deferred_event": deferred,
            "blocking_commitment": blocker, "native_offer": offered,
            "cancelled_old_commitment": cancelled,
            "source_offer_stale_ids": sorted(stale_offer_ids),
            "edit_invalidated_offer_ids": sorted(invalidated_offer_ids),
            "limits": ["A recorded deferral is not a first-rejection rule or a general preference model."]}


def audit_resource_negative(trace: Mapping[str, Any], scene: Mapping[str, Any],
                            db: Mapping[str, Any], *,
                            expected_intervention: Mapping[str, Any]) -> dict[str, Any]:
    station = trace.get("ongoing_station", {})
    station = station if isinstance(station, Mapping) else {}
    event = next((row for row in _event_rows(trace, "P5_INTERVENTION")
                  if row.get("minute") == expected_intervention.get("at")
                  and row.get("typed_args", {}).get("kind") == "player_native_command"), None)
    args = event.get("typed_args", {}) if event else {}
    receipt = args.get("command_receipt", {}) if isinstance(args, Mapping) else {}
    db_scene = _scene_db(db, trace.get("scene_id"))
    objects = db_scene.get("objects", []) if isinstance(db_scene, Mapping) else []
    actor_ids = {alias: row.get("id") for alias, row in scene.get("actors", {}).items()
                 if isinstance(scene.get("actors"), Mapping) and isinstance(row, Mapping)}
    item = next((row for row in objects if isinstance(row, Mapping)
                 and row.get("attributes", {}).get("native_p5", {}).get("p5_item_alias") == "courier_supply"), None)
    player = next((row for row in objects if isinstance(row, Mapping)
                   and row.get("attributes", {}).get("native_p3", {}).get("p3_control_role") == "player"), None)
    commitments = _rows(station.get("commitments"))
    a_goal = next((row for row in commitments if row.get("actor_id") == actor_ids.get("A")
                   and row.get("source") == "SELF" and row.get("task_kind") == "deliver_supply"), None)
    b_commits = [row for row in commitments if row.get("actor_id") == actor_ids.get("B")
                 and row.get("source") == "SELF"]
    b_receipts, _, _ = _actor_native_state(db, actor_ids.get("B"), trace.get("scene_id")) \
        if type(actor_ids.get("B")) is int else ([], {}, {})
    b_settled_ids = {row.get("ongoing_commitment_id") for row in b_receipts
                     if row.get("settled") is True and row.get("sim_minute", 0) > 1}
    b_route = next((row for row in b_commits if row.get("task_kind") == "routine_route"), None)
    route_receipts = [row for row in b_receipts if row.get("ongoing_commitment_id") ==
                      (b_route or {}).get("commitment_id") and row.get("settled") is True
                      and row.get("kind") == "move"]
    route_by_id = {row.get("receipt_id"): row for row in route_receipts}
    route_waypoint_ids = list((b_route or {}).get("waypoint_receipts", []))
    route_waypoints = list((b_route or {}).get("route_waypoints", []))
    ordered_route_receipts = [route_by_id.get(receipt_id) for receipt_id in route_waypoint_ids]
    a_receipts, a_native, a_station = _actor_native_state(db, actor_ids.get("A"), trace.get("scene_id")) \
        if type(actor_ids.get("A")) is int else ([], {}, {})
    a_supply_delivery = any(row.get("settled") is True and row.get("kind") == "drop"
                            and item is not None and row.get("item_id") == item.get("id")
                            for row in a_receipts)
    criteria = {
        "exact_scene_database_readback": isinstance(db_scene, Mapping),
        "scheduled_player_get_settled": bool(event and receipt.get("settled") is True
            and receipt.get("operation") == "get" and receipt.get("provenance") == "native_player_command"
            and expected_intervention.get("operation") == "get"
            and expected_intervention.get("item_alias") == "courier_supply"),
        "player_holds_supply_in_final_db": bool(item and player
            and item.get("location", {}).get("id") == player.get("id")
            and receipt.get("item_id") == item.get("id")
            and item.get("id") in receipt.get("after_inventory_ids", [])),
        "A_target_remains_configured_and_unfulfilled": bool(item
            and a_station.get("p5_task_item_alias") == "courier_supply"
            and a_native.get("task_item_id") == item.get("id")
            and (a_goal is None or a_goal.get("status") != "SETTLED")
            and not a_supply_delivery),
        "B_independent_goal_has_later_native_receipt": bool(b_settled_ids),
        "B_routine_route_has_settled_native_move": bool(b_route
            and b_route.get("status") == "SETTLED"
            and len(route_waypoint_ids) == 2 and len(route_waypoints) == 2
            and all(row is not None for row in ordered_route_receipts)
            and [row.get("after_room_id") for row in ordered_route_receipts] == route_waypoints),
    }
    passed = all(criteria.values())
    return {"schema": "ongoing-station-resource-negative-audit-v1",
            "status": "PASS" if passed else "NOT_CERTIFIED", "pass": passed,
            "criteria": criteria, "player_receipt": receipt,
            "A_delivery_commitment": a_goal, "B_route_commitment": b_route,
            "B_route_receipt_ids": [row.get("receipt_id") for row in route_receipts],
            "limits": ["The get occurs before NPC callbacks at minute 1; this is not a midstream interruption."]}
