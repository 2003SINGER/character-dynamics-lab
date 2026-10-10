"""Independent structural audit for P5 runner artifacts.

This re-joins native ledger rows, actor receipts, the TypedIR projection, and a
separate persisted Evennia DB export. Monitor verdicts are evidence, not proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .bundle import load_bundle

LEDGER_PRODUCER = "native-p4-ledger-v1"


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> list[dict]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _attrs(obj: dict, category: str) -> dict:
    return _mapping(_mapping(obj.get("attributes")).get(category))


def _failure(findings: list[dict], code: str, detail: str):
    findings.append({"status": "FAIL", "code": code, "detail": detail})


def _unknown(findings: list[dict], code: str, detail: str):
    findings.append({"status": "INDETERMINATE", "code": code, "detail": detail})


def _event_key(row: dict) -> tuple:
    return (int(row.get("minute", -1)), int(row.get("sequence", -1)))


def _find_db_scene(evidence: dict, scene_id: str) -> dict | None:
    return next((scene for scene in _rows(evidence.get("scenes"))
                 if scene.get("scene_id") == scene_id), None)


def _db_objects(scene: dict | None) -> dict[int, dict]:
    if not isinstance(scene, dict):
        return {}
    result = {}
    for obj in _rows(scene.get("objects")):
        try:
            result[int(obj["id"])] = obj
        except (KeyError, TypeError, ValueError):
            continue
    return result


def _check_ledger(final: dict, horizon: int, findings: list[dict]) -> list[dict]:
    ledger = _rows(final.get("ledger"))
    if not ledger:
        _unknown(findings, "LEDGER_MISSING", "final raw P4/P5 scene ledger is absent")
        return []
    sequences, event_ids = [], set()
    for row in ledger:
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            _failure(findings, "LEDGER_EVENT_ID", "ledger event IDs are missing or duplicated")
        event_ids.add(event_id)
        if row.get("sealed") is not True:
            _failure(findings, "UNSEALED_LEDGER_ROW", f"ledger row {event_id!r} is not sealed")
        if row.get("producer_version") != LEDGER_PRODUCER:
            _failure(findings, "LEDGER_PRODUCER", f"ledger row {event_id!r} has unexpected producer")
        try:
            sequences.append(int(row["sequence"]))
            if int(row["minute"]) < 0 or int(row["minute"]) > horizon:
                _failure(findings, "LEDGER_TIME_RANGE", f"ledger row {event_id!r} is outside run horizon")
        except (KeyError, TypeError, ValueError):
            _failure(findings, "LEDGER_ORDER_FIELDS", f"ledger row {event_id!r} lacks minute/sequence")
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        _failure(findings, "LEDGER_SEQUENCE", "ledger sequence is not strictly increasing")
    coverage = _mapping(final.get("complete_through"))
    if coverage.get("events") != horizon or coverage.get("values") != horizon:
        _failure(findings, "INCOMPLETE_PREFIX", "event and world snapshot seals do not reach the fixed horizon")
    trace = _mapping(final.get("typed_trace"))
    if trace.get("events_sealed_through") not in (str(horizon), horizon):
        _failure(findings, "TRACE_EVENT_SEAL", "TypedIR event completeness frontier misses the run horizon")
    return ledger


def _note_join(ledger: list[dict], trace: dict, scene: dict,
               db_objects: dict[int, dict], findings: list[dict],
               expected_decisions: list[str] | None) -> list[dict]:
    rows_by_type: dict[str, list[dict]] = {}
    for row in ledger:
        rows_by_type.setdefault(str(row.get("event_type")), []).append(row)
    requests = {row.get("typed_args", {}).get("request_id"): row
                for row in rows_by_type.get("SOCIAL_REQUEST", []) if row.get("sealed") is True}
    commits = {row.get("typed_args", {}).get("request_id"): row
               for row in rows_by_type.get("SOCIAL_COMMIT", []) if row.get("sealed") is True}
    responses = [row for row in rows_by_type.get("SOCIAL_RESPONSE", [])
                 if row.get("sealed") is True]
    typed_events = {row.get("event_id"): row for row in _rows(_mapping(trace).get("events"))
                    if row.get("event_type") == "p5_note_response"
                    and row.get("version") == "1"
                    and row.get("provenance") == "committed_ledger"}
    ids = _mapping(scene.get("actors"))
    actor_a, actor_b = _mapping(ids.get("A")).get("id"), _mapping(ids.get("B")).get("id")
    response_counts: dict[str, int] = {}
    commit_counts: dict[str, int] = {}
    for event in rows_by_type.get("SOCIAL_RESPONSE", []):
        key = event.get("typed_args", {}).get("request_id")
        response_counts[str(key)] = response_counts.get(str(key), 0) + 1
    for event in rows_by_type.get("SOCIAL_COMMIT", []):
        key = event.get("typed_args", {}).get("request_id")
        commit_counts[str(key)] = commit_counts.get(str(key), 0) + 1
    valid = []
    for row in responses:
        args = _mapping(row.get("typed_args"))
        request_id, note_id = args.get("request_id"), args.get("note_id")
        request, commit = requests.get(request_id), commits.get(request_id)
        request_args = _mapping(request.get("typed_args")) if request else {}
        commit_args = _mapping(commit.get("typed_args")) if commit else {}
        physical = _mapping(args.get("physical_receipt"))
        expected_action = ("writeLoveNoteAccept" if args.get("decision") == "accepted"
                           else "writeLoveNoteReject")
        if (args.get("decision") not in {"accepted", "rejected"}
                or args.get("selected_action") != expected_action
                or args.get("native_commit_status") != "settled"
                or request is None or commit is None
                or request_args.get("note_id") != note_id
                or commit_args.get("note_id") != note_id
                or request_args.get("initiator_actor_id") != actor_a
                or request_args.get("recipient_actor_id") != actor_b
                or args.get("initiator_actor_id") != actor_a
                or args.get("responder_actor_id") != actor_b
                or physical.get("status") != "settled"
                or physical.get("same_note_id") != note_id
                or commit_args.get("settlement_receipt_id") != physical.get("receipt_id")
                or args.get("native_commit_receipt_id") != commit.get("event_id")
                or commit_args.get("action_name") != expected_action
                or response_counts.get(str(request_id)) != 1
                or commit_counts.get(str(request_id)) != 1
                or not (_event_key(request) < _event_key(row) < _event_key(commit))):
            _failure(findings, "SOCIAL_CHAIN", "SOCIAL_REQUEST/RESPONSE/COMMIT do not join one same-note settled chain")
            continue
        trace_event = typed_events.get(row.get("event_id"))
        trace_args = _mapping(trace_event.get("args")) if trace_event else {}
        if (trace_event is None or trace_args.get("response") != args.get("decision")
                or trace_args.get("actor") != {"entity_type": "Actor", "stable_id": "A"}
                or trace_args.get("recipient") != {"entity_type": "Actor", "stable_id": "B"}
                or trace_args.get("item") != {"entity_type": "Item", "stable_id": "note"}):
            _failure(findings, "SOCIAL_TRACE_WITNESS", "TypedIR response is not the committed native response event")
            continue
        try:
            note = db_objects[int(note_id)]
        except (KeyError, TypeError, ValueError):
            _failure(findings, "SOCIAL_NOTE_DB_MISSING", "same physical note is absent from persisted scene export")
            continue
        note_native, note_p5 = _attrs(note, "native_p3"), _attrs(note, "native_p5")
        location_id = _mapping(note.get("location")).get("id")
        if (note_native.get("p4_note_request_id") != request_id
                or note_native.get("p4_note_response_event_id") != row.get("event_id")
                or note_native.get("p4_note_action") != args.get("selected_action")
                or note_native.get("p4_native_commit_status") != "settled"
                or note_p5.get("p5_item_alias") != "note"
                or location_id != actor_b):
            _failure(findings, "SOCIAL_NOTE_DB_STATE", "persisted note/request/response/recipient inventory state differs from the settled chain")
            continue
        valid.append(row)
    if set(typed_events) != {row.get("event_id") for row in valid}:
        _failure(findings, "TRACE_UNJOINED_RESPONSE", "TypedIR includes a note response without exactly one valid same-note native chain")
    if expected_decisions is not None and sorted(row["typed_args"]["decision"] for row in valid) != sorted(expected_decisions):
        _failure(findings, "SOCIAL_DECISION_EXPECTATION", "settled native response decisions differ from explicit expectations")
    return valid


def _check_actor_and_db(final: dict, scene: dict, db_objects: dict[int, dict],
                        findings: list[dict], expected_deliveries: list[str],
                        expected_route: str | None, shared_supply: bool) -> None:
    actor_rows = _rows(final.get("actor_evidence"))
    by_alias = {row.get("actor_alias"): row for row in actor_rows}
    scene_actors, rooms = _mapping(scene.get("actors")), _mapping(scene.get("rooms"))
    for alias in ("A", "B"):
        actor_scene = _mapping(scene_actors.get(alias))
        actor_id = actor_scene.get("id")
        actor = by_alias.get(alias)
        if not isinstance(actor, dict) or actor.get("actor_id") != actor_id:
            _failure(findings, "ACTOR_EVIDENCE", f"scene actor {alias} lacks matching final evidence")
            continue
        try:
            db_actor = db_objects[int(actor_id)]
        except (KeyError, TypeError, ValueError):
            _failure(findings, "ACTOR_DB_MISSING", f"scene actor {alias} is absent from independent DB export")
            continue
        native = _attrs(db_actor, "native_p3")
        p5 = _attrs(db_actor, "native_p5")
        if p5.get("p5_actor_alias") != alias or native.get("activity_profile") != "p5_story_v0":
            _failure(findings, "ACTOR_DB_ROLE", f"persisted actor {alias} lacks P5 role/profile binding")
        task_id = actor.get("task_item_id")
        if task_id != native.get("task_item_id"):
            _failure(findings, "TASK_DB_BINDING", f"actor {alias} task item differs from persisted assignment")
        receipts, logs = native.get("native_receipts", []), native.get("log", [])
        if actor.get("native_receipts") != receipts or actor.get("log") != logs:
            _failure(findings, "ACTOR_LOG_DB_MISMATCH", f"actor {alias} runtime evidence differs from persisted logs/receipts")
        if task_id is None:
            _failure(findings, "TASK_MISSING", f"actor {alias} has no assigned task item")
            continue
        task_obj = db_objects.get(int(task_id))
        if task_obj is None:
            _failure(findings, "TASK_OBJECT_MISSING", f"actor {alias} assigned item is absent from generated-scene export")
            continue
        settled = [receipt for receipt in _rows(receipts)
                   if receipt.get("kind") == "drop" and receipt.get("settled") is True
                   and str(receipt.get("item_id")) == str(task_id)
                   and receipt.get("after_item_room_id") == actor.get("task_destination_id")]
        if alias in expected_deliveries:
            location_id = _mapping(task_obj.get("location")).get("id")
            if not settled or location_id != actor.get("task_destination_id"):
                _failure(findings, "DELIVERY_NOT_SETTLED", f"actor {alias} lacks native task-drop receipt plus matching persisted location")
        if expected_route:
            move_pairs = [(row.get("before_room_id"), row.get("after_room_id"))
                          for row in _rows(receipts)
                          if row.get("kind") == "move" and row.get("settled") is True]
            origin, side, destination = rooms.get("origin"), rooms.get("side"), rooms.get("destination")
            required = ([(origin, destination)] if expected_route == "main_passage"
                        else [(origin, side), (side, destination)] if expected_route == "side_passage" else [])
            cursor = 0
            for pair in required:
                try:
                    cursor = move_pairs.index(pair, cursor) + 1
                except ValueError:
                    _failure(findings, "ROUTE_NOT_TRAVERSED", f"actor {alias} lacks ordered settled native moves for {expected_route}")
                    break
    if shared_supply:
        task_ids = [_mapping(by_alias.get(alias)).get("task_item_id") for alias in ("A", "B")]
        if None in task_ids or len(set(map(str, task_ids))) != 1:
            _failure(findings, "SHARED_ITEM_BINDING", "shared-supply run did not bind both actors to one physical task item")


def _check_world_and_edits(document: dict, findings: list[dict]) -> None:
    config = _mapping(document.get("configuration"))
    response = _mapping(document.get("response"))
    rounds = _rows(response.get("rounds"))
    final = _mapping(response.get("final"))
    ledger = _rows(final.get("ledger"))
    expectations = _mapping(config.get("expect"))
    expected_route = expectations.get("route_traversed")
    no_route_opportunity = expectations.get("no_route_opportunity") is True
    expected_opportunity_route = expectations.get("opportunity_route")
    if expected_opportunity_route is None and not no_route_opportunity:
        expected_opportunity_route = expected_route
    opportunity_rows = [row for row in ledger if row.get("event_type") == "P5_OPPORTUNITY_SETTLED"]
    route_settlements = [row for row in ledger if row.get("event_type") in {
        "P5_OPPORTUNITY_SETTLED", "P5_OPPORTUNITY_ATTEMPT"} and row.get("typed_args", {}).get("settled") is True]
    if expected_opportunity_route:
        matching = [row for row in opportunity_rows
                    if row.get("typed_args", {}).get("route_id") == expected_opportunity_route]
        if len(matching) != 1:
            _failure(findings, "ROUTE_OPPORTUNITY", "expected exactly one settled author opportunity for the selected route")
        elif matching[0].get("typed_args", {}).get("cost") != (
                1 if expected_opportunity_route == "side_passage" else 2):
            _failure(findings, "ROUTE_COST", "settled route opportunity cost differs from the registered route cost")
        if len(opportunity_rows) > 1:
            _failure(findings, "OPPORTUNITY_QUOTA", "more than one physical passage opportunity settled")
    scene = _mapping(response.get("scene"))
    db_evidence = document.get("db_evidence")
    db_scene = _find_db_scene(db_evidence, scene.get("scene_id")) if isinstance(db_evidence, dict) else None
    db_objects = _db_objects(db_scene)
    pickup_id = _mapping(scene.get("rooms")).get("origin")
    pickup = db_objects.get(int(pickup_id)) if isinstance(pickup_id, int) else None
    if pickup is not None and expected_opportunity_route:
        attrs = _attrs(pickup, "native_p5")
        if attrs.get("p5_spent_cost") != (1 if expected_opportunity_route == "side_passage" else 2):
            _failure(findings, "PERSISTED_ROUTE_COST", "persisted opportunity cost does not match the settled route")
        if attrs.get("p5_opportunities_used") != 1:
            _failure(findings, "PERSISTED_OPPORTUNITY_QUOTA", "persisted opportunity count is not exactly one")
    elif expected_opportunity_route:
        _unknown(findings, "PERSISTED_ROUTE_COST_UNKNOWN", "persisted pickup P5 opportunity budget is unavailable")
    if no_route_opportunity:
        # P5_OPPORTUNITY_SETTLED is a receipt-backed success event; unlike an
        # attempted intervention it need not duplicate `settled: true` in args.
        if opportunity_rows or route_settlements:
            _failure(findings, "UNEXPECTED_ROUTE_OPPORTUNITY", "a physical route opportunity settled in a no-opportunity control")
    for operation in expectations.get("denied_author_opportunities", []):
        rejected = [row for row in ledger if row.get("event_type") == "P5_INTERVENTION"
                    and row.get("typed_args", {}).get("kind") == "author_opportunity"
                    and row.get("typed_args", {}).get("intervention", {}).get("opportunity_id") == operation
                    and row.get("typed_args", {}).get("settlement", {}).get("status") == "PERMISSION_DENIED"]
        if len(rejected) != 1:
            _failure(findings, "AUTHORITY_NEGATIVE", f"unauthorized opportunity {operation!r} lacks one real permission rejection")
    expected_player = expectations.get("player_interventions", [])
    if expected_player:
        rows = [row for row in ledger if row.get("event_type") == "P5_INTERVENTION"
                and row.get("typed_args", {}).get("kind") == "player_native_command"]
        observed = []
        for row in rows:
            args = _mapping(row.get("typed_args"))
            receipt = _mapping(args.get("command_receipt"))
            intervention = _mapping(args.get("intervention"))
            if (args.get("settlement", {}).get("settled") is True
                    and receipt.get("actor_alias") == "player"
                    and receipt.get("provenance") == "native_player_command"):
                observed.append({"operation": intervention.get("operation"),
                                 "item_alias": intervention.get("item_alias"),
                                 "receipt": receipt})
        if len(observed) != len(expected_player):
            _failure(findings, "PLAYER_INTERVENTION_COUNT", "recorded settled native player interventions differ from expectations")
        for wanted, actual in zip(expected_player, observed):
            if actual["operation"] != wanted.get("operation") or actual["item_alias"] != wanted.get("item_alias"):
                _failure(findings, "PLAYER_INTERVENTION_BINDING", "player intervention operation/item does not match configured test")
                continue
            receipt = actual["receipt"]
            if wanted.get("operation") == "get":
                player_id = _mapping(scene.get("player")).get("id")
                settled = (receipt.get("before_location_id") == _mapping(scene.get("rooms")).get("origin")
                           and receipt.get("after_location_id") == player_id
                           and receipt.get("item_id") in receipt.get("after_inventory_ids", []))
            else:
                settled = (receipt.get("after_location_id") == _mapping(scene.get("rooms")).get("origin")
                           and receipt.get("item_id") not in receipt.get("after_inventory_ids", []))
            if not settled:
                _failure(findings, "PLAYER_INTERVENTION_PHYSICAL", "native player command receipt does not show the expected location/inventory transition")

    verdicts = _mapping(final.get("verdicts"))
    if expectations.get("hard_status") is not None and verdicts.get("hard_status") != expectations["hard_status"]:
        _failure(findings, "HARD_VERDICT", "author bundle hard status differs from explicit run expectation")
    goal_expectations = _mapping(expectations.get("goal_statuses"))
    actual_goals = {row.get("constraint_id"): row.get("status")
                    for row in _rows(verdicts.get("constraints"))}
    for goal_id, expected in goal_expectations.items():
        if actual_goals.get(goal_id) != expected:
            _failure(findings, "GOAL_VERDICT", f"constraint {goal_id!r} status differs from explicit expectation")
    branches = _rows(verdicts.get("branches"))
    if expectations.get("note_response") is True:
        accepted = [row for row in branches if row.get("status") == "ELIGIBLE"]
        expected_responses = set(expectations.get("note_decisions", []))
        actual_responses = {row.get("response") for row in accepted}
        if actual_responses != expected_responses:
            _failure(findings, "STORYLET_BRANCH", "eligible content branch does not match the actual sealed native response")
        if verdicts.get("storylets_execute_world_effects") is not False:
            _failure(findings, "STORYLET_EFFECT_SCOPE", "storylet monitor output does not declare content-only effects")
        response_ids = {row.get("event_id") for row in accepted}
        typed_ids = {row.get("event_id") for row in _rows(_mapping(final.get("typed_trace")).get("events"))
                     if row.get("event_type") == "p5_note_response"}
        if not response_ids or not response_ids.issubset(typed_ids):
            _failure(findings, "STORYLET_EVENT_JOIN", "eligible storylet is not joined to a projected native response event")

    expected_edit_rows = _rows(config.get("edits"))
    actual_edit_rows = [(minute_row.get("minute"), edit) for minute_row in rounds
                        for edit in _rows(minute_row.get("edits"))]
    if len(actual_edit_rows) != len(expected_edit_rows):
        _failure(findings, "EDIT_COUNT", "recorded edit attempts do not match the external schedule")
    for scheduled, recorded in zip(expected_edit_rows, actual_edit_rows):
        if recorded[0] != scheduled.get("at"):
            _failure(findings, "EDIT_MINUTE", "edit result was recorded at a different minute from its schedule")
        result = _mapping(recorded[1])
        if result.get("ok") is True:
            before = _mapping(result.get("pending_actions_before"))
            after = _mapping(result.get("pending_actions_after"))
            identities = [value for value in before.values() if isinstance(value, dict)]
            if (not identities or not any(value.get("operation_id") for value in identities)
                    or before != after or result.get("pending_identity_preserved") is not True):
                _failure(findings, "EDIT_PENDING_IDENTITY", "accepted edit did not preserve a nonempty pending action identity")
            archive = _mapping(result.get("archive"))
            active = _mapping(result.get("active_bundle"))
            if (archive.get("prior_version") != scheduled.get("expected_version")
                    or active.get("version") != scheduled.get("expected_version", -1) + 1
                    or not isinstance(archive.get("prior_verdicts"), dict)):
                _failure(findings, "EDIT_ARCHIVE_VERSION", "accepted edit lacks a matching prior-version verdict archive")
            if result.get("ledger_prefix_before") != result.get("ledger_prefix_after"):
                _failure(findings, "EDIT_LEDGER_PREFIX", "accepted edit changed the already-committed ledger prefix")
        elif result.get("ok") is False:
            error = _mapping(result.get("error"))
            if error.get("code") != "VERSION_CONFLICT":
                _failure(findings, "EDIT_REJECTION_KIND", "rejected edit was not a stale-version conflict")
            if result.get("ledger_prefix_before") != result.get("ledger_prefix_after"):
                _failure(findings, "REJECTED_EDIT_MUTATION", "stale edit changed the committed ledger prefix")
        else:
            _failure(findings, "EDIT_RESULT", "scheduled edit has no explicit accepted or rejected CAS result")

    # A controller can submit only scene-player commands or licensed author
    # opportunity rows. Actor callbacks must remain native-owned and local.
    for round_row in rounds:
        for intervention in _rows(round_row.get("interventions")):
            receipt = _mapping(intervention.get("receipt"))
            if intervention.get("status") == "SETTLED" and receipt:
                if receipt.get("actor_alias") != "player" or receipt.get("provenance") != "native_player_command":
                    _failure(findings, "INTERVENTION_ACTOR", "settled player intervention was not executed by the generated player")
        for actor_step in _rows(round_row.get("actor_steps")):
            for decision in _rows(actor_step.get("local_decisions")):
                if decision.get("source") in {"controller", "author"} or decision.get("controller_authored") is True:
                    _failure(findings, "NPC_DECISION_PROVENANCE", "NPC action intent is marked as controller/author supplied")


def audit_document(document: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict] = []
    if not isinstance(document, dict) or document.get("schema") != "native-p5-run-artifact-v1":
        return {"schema": "native-p5-audit-v1", "status": "FAIL",
                "findings": [{"status": "FAIL", "code": "ARTIFACT_SCHEMA", "detail": "unsupported P5 artifact schema"}]}
    config, manifest = _mapping(document.get("configuration")), _mapping(document.get("manifest"))
    response = _mapping(document.get("response"))
    scene, final = _mapping(response.get("scene")), _mapping(response.get("final"))
    horizon = config.get("horizon")
    if type(horizon) is not int:
        _failure(findings, "HORIZON_MISSING", "run configuration has no integer fixed horizon")
        horizon = 0
    bundle_raw = manifest.get("bundle")
    if not isinstance(bundle_raw, dict):
        _failure(findings, "RAW_BUNDLE_MISSING", "artifact does not preserve the external raw author bundle")
    else:
        try:
            parsed = load_bundle(bundle_raw)
            if scene.get("active_bundle") != {"bundle_id": parsed.bundle_id, "version": parsed.version}:
                _failure(findings, "BUNDLE_BINDING", "scene active bundle does not match preserved author package")
        except Exception as exc:
            _failure(findings, "BUNDLE_INVALID", f"preserved bundle failed closed parser: {type(exc).__name__}")
    if response.get("ok") is not True:
        _failure(findings, "RUN_RESPONSE", "P5 service did not return an accepted run")
    if response.get("run_status") != "COMPLETE":
        _unknown(findings, "RUN_INCOMPLETE", "P5 server run status is not COMPLETE")
    if response.get("controller_authored_npc_commands") != 0:
        _failure(findings, "CONTROLLER_NPC_COMMAND", "response does not attest zero controller-authored NPC commands")
    rounds = _rows(response.get("rounds"))
    if [row.get("minute") for row in rounds] != list(range(1, horizon + 1)):
        _failure(findings, "ROUND_SEQUENCE", "rounds are not a contiguous fixed-horizon sequence")
    for row in rounds:
        if row.get("minute_complete") is not True:
            _failure(findings, "ROUND_UNSEALED", f"minute {row.get('minute')} lacks director/A/B completion seal")
        aliases = {item.get("actor_alias") for item in _rows(row.get("actor_steps"))}
        if aliases != {"A", "B"}:
            _failure(findings, "CALLBACK_COVERAGE", f"minute {row.get('minute')} lacks both native actor callbacks")
    ledger = _check_ledger(final, horizon, findings)
    db_evidence = document.get("db_evidence")
    db_scene, db_objects = None, {}
    if not isinstance(db_evidence, dict):
        _unknown(findings, "DB_READBACK_MISSING", "no separate read-only persisted DB export is embedded")
    else:
        db_scene = _find_db_scene(db_evidence, scene.get("scene_id"))
        if db_scene is None:
            _failure(findings, "DB_SCENE_MISSING", "independent DB evidence omits the exact generated scene")
        db_objects = _db_objects(db_scene)
        if not db_objects:
            _failure(findings, "DB_OBJECTS_MISSING", "independent DB scene export contains no object rows")
        origin_id = _mapping(scene.get("rooms")).get("origin")
        pickup = db_objects.get(int(origin_id)) if isinstance(origin_id, int) else None
        db_ledger = _attrs(pickup, "native_p3").get("p4_ledger") if pickup else None
        if not isinstance(db_ledger, list):
            _failure(findings, "DB_LEDGER_MISSING", "persisted pickup lacks its authoritative raw P4/P5 ledger")
        elif [(r.get("event_id"), r.get("sequence"), r.get("event_type")) for r in _rows(db_ledger)] != [
                (r.get("event_id"), r.get("sequence"), r.get("event_type")) for r in ledger]:
            _failure(findings, "DB_LEDGER_MISMATCH", "service ledger differs from independently persisted ledger")
    expectations = _mapping(config.get("expect"))
    expected_decisions = expectations.get("note_decisions")
    if expected_decisions is not None and (not isinstance(expected_decisions, list)
                                           or any(value not in {"accepted", "rejected"} for value in expected_decisions)):
        _failure(findings, "EXPECTATION_SCHEMA", "note_decisions must list accepted/rejected")
        expected_decisions = None
    if db_scene is not None:
        responses = _note_join(ledger, _mapping(final.get("typed_trace")), scene,
                               db_objects, findings, expected_decisions)
        _check_actor_and_db(final, scene, db_objects, findings,
                            expectations.get("delivery_actors", []),
                            expectations.get("route_traversed"),
                            config.get("shared_supply") is True)
        if expectations.get("note_response") is True and not responses:
            _failure(findings, "NOTE_RESPONSE_MISSING", "expected a same-note native response/commit chain")
        elif expectations.get("note_response") is False and responses:
            _failure(findings, "NOTE_RESPONSE_UNEXPECTED", "native response exists despite explicit no-response expectation")
    _check_world_and_edits(document, findings)
    verdicts = _mapping(final.get("verdicts"))
    if verdicts:
        findings.append({"status": "INFO", "code": "MONITOR_RESULT_RECORDED",
                         "detail": f"monitor hard_status={verdicts.get('hard_status')}; raw evidence independently checked"})
    failed = any(row["status"] == "FAIL" for row in findings)
    unknown = any(row["status"] == "INDETERMINATE" for row in findings)
    status = "FAIL" if failed else "INDETERMINATE" if unknown else "PASS"
    return {"schema": "native-p5-audit-v1", "status": status,
            "scene_id": scene.get("scene_id"),
            "bundle_id": _mapping(bundle_raw).get("bundle_id"),
            "bundle_version": _mapping(bundle_raw).get("version"),
            "checks": len(findings), "findings": findings,
            "claim_boundary": "structural evidence audit only; not a research-effectiveness or psychological-validity claim"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.artifact.read_text(encoding="utf-8"))
        result = audit_document(document)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        print(rendered, end="")
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        parser.error(f"P5 audit could not complete: {type(exc).__name__}: {exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
