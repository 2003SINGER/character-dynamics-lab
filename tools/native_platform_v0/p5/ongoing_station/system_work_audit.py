"""Receipt- and world-readback audits for the station-work integration slice.

These checks certify evidence consistency, not algorithmic quality. They only
accept work outcomes backed by the native P4 ledger and independent scoped
Evennia export; plans, offers, and controller decisions are not completion evidence.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def _rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _scene_db(db: Mapping[str, Any], scene_id: Any) -> Mapping[str, Any] | None:
    scenes = db.get("scenes", [])
    return next((row for row in scenes if isinstance(row, Mapping)
                 and row.get("scene_id") == scene_id), None) if isinstance(scenes, list) else None


def _objects(scene: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [row for row in scene.get("objects", []) if isinstance(row, Mapping)]


def _native_p5(obj: Mapping[str, Any]) -> Mapping[str, Any]:
    attrs = obj.get("attributes", {})
    category = attrs.get("native_p5", {}) if isinstance(attrs, Mapping) else {}
    return category if isinstance(category, Mapping) else {}


def _p4_ledger(scene: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for obj in _objects(scene):
        attrs = obj.get("attributes", {})
        p3 = attrs.get("native_p3", {}) if isinstance(attrs, Mapping) else {}
        ledger = p3.get("p4_ledger", []) if isinstance(p3, Mapping) else []
        if isinstance(ledger, list):
            result.extend(dict(row) for row in ledger if isinstance(row, Mapping))
    unique: dict[str, dict[str, Any]] = {}
    for row in result:
        key = str(row.get("event_id", row.get("receipt_id", "")))
        if key:
            unique.setdefault(key, row)
    return list(unique.values())


def _receipt_rows(station: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for field in ("station_work_receipts", "station_store_receipts"):
        value = station.get(field, {})
        if isinstance(value, Mapping):
            for actor_alias, receipts in value.items():
                for row in _rows(receipts):
                    normalized = {"actor_alias": actor_alias, **row}
                    if not normalized.get("task_kind"):
                        normalized["task_kind"] = normalized.get("operator")
                    result.append(normalized)
    return result


def audit_station_work(trace: Mapping[str, Any], db: Mapping[str, Any], *,
                       required_outcomes: tuple[str, ...] = (),
                       require_tool_released: bool = True) -> dict[str, Any]:
    """Check physical work, shared capacity, storage, and receipt provenance.

    required_outcomes uses registered task names (inspect_supply,
    repair_passage, store_item). Physical outcomes remain distinct from
    controller acceptance and author-goal verdicts.
    """
    station = trace.get("ongoing_station", {})
    station = station if isinstance(station, Mapping) else {}
    state = station.get("station_work", {})
    state = state if isinstance(state, Mapping) else {}
    scene = _scene_db(db, trace.get("scene_id"))
    receipts = _receipt_rows(station)
    ledger = _p4_ledger(scene) if isinstance(scene, Mapping) else []
    ledger_by_receipt = {str(row.get("receipt_id")): row for row in ledger
                         if row.get("receipt_id") is not None and row.get("sealed") is True}
    registered_task_kinds = {"inspect_supply", "repair_passage", "store_item"}
    receipt_checks = []
    for receipt in receipts:
        receipt_id = receipt.get("receipt_id")
        event = ledger_by_receipt.get(str(receipt_id))
        # Native store receipts may carry task_kind=None while operator is the
        # authoritative registered operation. Resolve that shape explicitly;
        # unknown rows remain visible and fail the audit rather than crashing
        # later when task kinds are sorted.
        task_kind = receipt.get("task_kind") or receipt.get("operator")
        settled = receipt.get("settled") is True and receipt.get("outcome", "SETTLED") == "SETTLED"
        expected_event = {"inspect_supply": "P5_STATION_SUPPLY_INSPECTED",
                          "repair_passage": "P5_STATION_PASSAGE_REPAIRED",
                          "store_item": "P5_STATION_SUPPLY_STORED"}.get(task_kind)
        if receipt.get("outcome") == "ABORTED":
            expected_event = "P5_STATION_WORK_ABORTED"
        start_event_id = (f"station-work:{trace.get('scene_id')}:{receipt.get('action_id')}:start"
                          if receipt.get("action_id") else None)
        start_event = ledger_by_receipt.get(str(start_event_id)) if start_event_id else None
        args = event.get("typed_args", {}) if isinstance(event, Mapping) else {}
        expected_args = {
            "receipt_id": receipt_id, "commitment_id": receipt.get("commitment_id"),
            "actor_id": receipt.get("actor_id"), "actor_alias": receipt.get("actor_alias"),
        }
        if task_kind == "store_item":
            expected_args.update({"operator": "store_item", "kind": "store_item"})
        else:
            expected_args["task_kind"] = task_kind
        for field in ("action_id", "tool_id", "target_id", "item_id", "storage_id",
                      "after_container_id", "started_minute", "due_minute",
                      "completed_minute", "sim_minute", "outcome"):
            if field in receipt:
                # Store rows use sim_minute and outcome; work rows use
                # completed_minute and outcome. Compare only source fields
                # actually present on the native receipt.
                expected_args[field] = receipt[field]
        event_args_match = bool(event and all(args.get(key) == value
                                              for key, value in expected_args.items()))
        receipt_checks.append({"receipt_id": receipt_id, "task_kind": task_kind,
            "settled": settled, "ledger_event_id": event.get("event_id") if event else None,
            "ledger_event_type": event.get("event_type") if event else None,
            "ledger_witness_matches": bool(event and event.get("event_id") == receipt_id
                and event.get("event_type") == expected_event
                and event.get("typed_args", {}).get("receipt_id") == receipt_id
                and event.get("sealed") is True and event_args_match
                and event.get("minute") == receipt.get("completed_minute",
                    receipt.get("sim_minute"))),
            "start_event_witness_matches": (bool(start_event
                and start_event.get("event_type") == "P5_STATION_WORK_STARTED"
                and start_event.get("typed_args", {}).get("action_id") == receipt.get("action_id")
                and start_event.get("typed_args", {}).get("commitment_id") == receipt.get("commitment_id")
                and start_event.get("minute") == receipt.get("started_minute")
                and start_event.get("typed_args", {}).get("tool_id") == receipt.get("tool_id")
                and start_event.get("typed_args", {}).get("target_id") == receipt.get("target_id"))
                if task_kind in {"inspect_supply", "repair_passage"} else None)})

    tool = state.get("tool", {})
    tool = tool if isinstance(tool, Mapping) else {}
    lease = tool.get("lease", {})
    lease = lease if isinstance(lease, Mapping) else {}
    work_receipts = [row for row in receipts if row.get("task_kind") in {"inspect_supply", "repair_passage"}]
    intervals, invalid_intervals = [], []
    expected_duration = {"inspect_supply": 2, "repair_passage": 3}
    for receipt in work_receipts:
        start, due, completed = (receipt.get("started_minute"), receipt.get("due_minute"),
                                 receipt.get("completed_minute"))
        kind = receipt.get("task_kind")
        well_formed = (type(start) is int and type(due) is int and type(completed) is int
            and due >= start and completed >= start
            and receipt.get("duration_minutes") == expected_duration.get(kind)
            and due == start + expected_duration.get(kind, -100))
        if well_formed and receipt.get("outcome") == "SETTLED":
            well_formed = completed >= due
        if well_formed and receipt.get("outcome") == "ABORTED":
            well_formed = completed <= due
        if well_formed:
            intervals.append((start, completed, receipt.get("receipt_id")))
        else:
            invalid_intervals.append(receipt.get("receipt_id"))
    overlapping = []
    for index, left in enumerate(intervals):
        for right in intervals[index + 1:]:
            if left[2] != right[2] and max(left[0], right[0]) < min(left[1], right[1]):
                overlapping.append([left[2], right[2]])

    settled_work = [row for row in work_receipts if row.get("settled") is True
                    and row.get("outcome") == "SETTLED"]
    supply = state.get("supply", {})
    supply = supply if isinstance(supply, Mapping) else {}
    storage = state.get("storage", {})
    storage = storage if isinstance(storage, Mapping) else {}
    repair_exit = state.get("repair_exit", {})
    repair_exit = repair_exit if isinstance(repair_exit, Mapping) else {}
    objects_by_id = {row.get("id"): row for row in _objects(scene)} if isinstance(scene, Mapping) else {}
    registered = state.get("registered_ids", {})
    registered = dict(registered) if isinstance(registered, Mapping) else {}
    for state_key, id_key in (("tool", "tool_id"), ("storage", "storage_id"),
                              ("supply", "supply_id"), ("repair_exit", "repair_exit_id")):
        entity_state = state.get(state_key, {})
        if id_key not in registered and isinstance(entity_state, Mapping):
            registered[id_key] = entity_state.get("id")
    tool_db = objects_by_id.get(registered.get("tool_id"), {})
    storage_db = objects_by_id.get(registered.get("storage_id"), {})
    supply_db = objects_by_id.get(registered.get("supply_id"), {})
    exit_db = objects_by_id.get(registered.get("repair_exit_id"), {})
    def location_id(row):
        location = row.get("location") if isinstance(row, Mapping) else None
        return location.get("id") if isinstance(location, Mapping) else None
    tool_attr, storage_attr = _native_p5(tool_db), _native_p5(storage_db)
    supply_attr, exit_attr = _native_p5(supply_db), _native_p5(exit_db)
    inspect_receipts = [row for row in settled_work if row.get("task_kind") == "inspect_supply"]
    repair_receipts = [row for row in settled_work if row.get("task_kind") == "repair_passage"]
    store_receipts = [row for row in receipts if row.get("task_kind") == "store_item"
                      and row.get("settled") is True and row.get("outcome") == "SETTLED"]
    successful = {row.get("task_kind") for row in receipts
                  if row.get("task_kind") in registered_task_kinds
                  and row.get("settled") is True and row.get("outcome", "SETTLED") == "SETTLED"}
    unknown_task_receipts = [row.get("receipt_id") for row in receipt_checks
                             if row.get("task_kind") not in registered_task_kinds]
    exact_supply_stored = bool(store_receipts and supply.get("id") is not None
        and supply.get("id") in storage.get("stored_item_ids", [])
        and supply.get("location_id") == storage.get("id")
        and any(row.get("item_id") == supply.get("id")
                and row.get("storage_id") == storage.get("id")
                and row.get("after_container_id") == storage.get("id") for row in store_receipts))
    supply_db_row = objects_by_id.get(supply.get("id"), {})
    storage_db_row = objects_by_id.get(storage.get("id"), {})
    def db_location_id(row):
        location = row.get("location") if isinstance(row, Mapping) else None
        return location.get("id") if isinstance(location, Mapping) else None
    supply_db_attrs = _native_p5(supply_db_row)
    storage_db_attrs = _native_p5(storage_db_row)
    tool_db_attrs = _native_p5(tool_db)
    exit_lock = exit_db.get("exit_traverse_lock") if isinstance(exit_db, Mapping) else None
    physical = {
        "inspection_approved_by_settled_receipt": bool(inspect_receipts
            and supply.get("inspection_status") == "APPROVED"
            and any(row.get("effect", {}).get("after_status") == "APPROVED"
                    and row.get("item_id") == supply.get("id") for row in inspect_receipts)),
        "supply_stored_in_registered_container": exact_supply_stored,
        "registered_storage_contains_exact_supply_in_db": bool(store_receipts
            and storage_db_attrs.get("p5_station_storage") is True
            and supply.get("id") in storage_db_row.get("contents_ids", [])
            and db_location_id(supply_db_row) == storage.get("id")),
        "supply_inspection_attribute_matches_independent_db": bool(supply_db_row
            and supply_db_attrs.get("p5_supply_inspection_status") == supply.get("inspection_status")),
        "registered_passage_repaired": bool(repair_receipts
            and repair_exit.get("traversable") is True
            and any(row.get("target_id") == repair_exit.get("id")
                    and row.get("effect", {}).get("after_traversable") is True
                    for row in repair_receipts)),
        "registered_exit_identity_and_persisted_traverse_lock_match_db": (
            not repair_receipts or bool(exit_db
                and _native_p5(exit_db).get("p5_repair_target") is True
                and db_location_id(exit_db) == repair_exit.get("source_room_id")
                and (exit_db.get("exit_destination") or {}).get("id") == repair_exit.get("destination_room_id")
                and exit_db.get("key") == repair_exit.get("key")
                and exit_lock == "traverse:true()")),
        "tool_is_registered_evennia_object_and_state_matches_db": bool(tool_db
            and tool_attr.get("p5_station_tool") is True
            and tool_attr.get("p5_station_tool_lease") == lease
            and (location_id(tool_db) == tool.get("room_id")
                 or tool.get("held_by_actor_id") == location_id(tool_db))),
        "storage_is_registered_evennia_object": bool(storage_db
            and storage_attr.get("p5_station_storage") is True
            and location_id(storage_db) == storage.get("room_id")),
        "supply_evennia_location_and_inspection_match_trace": bool(supply_db
            and location_id(supply_db) == supply.get("location_id")
            and supply_attr.get("p5_supply_inspection_status") == supply.get("inspection_status")),
        "repair_exit_evennia_identity_matches_trace": bool(exit_db
            and exit_attr.get("p5_repair_target") is True
            and location_id(exit_db) == repair_exit.get("source_room_id")
            and (exit_db.get("exit_destination") or {}).get("id") == repair_exit.get("destination_room_id")
            and exit_db.get("key") == repair_exit.get("key")),
        "repair_exit_exact_lock_readback_available": bool(exit_db and "exit_traverse_lock" in exit_db),
    }
    expected_receipts_present = all(name in successful for name in required_outcomes)
    criteria = {
        "independent_scene_database_readback_present": isinstance(scene, Mapping),
        "every_work_or_store_receipt_has_sealed_exact_p4_event": all(
            row["ledger_witness_matches"] and (row["settled"] is False
                or row["start_event_witness_matches"] is not False)
            for row in receipt_checks
            if row["settled"] or row["task_kind"] in {"inspect_supply", "repair_passage"}),
        "work_receipt_intervals_are_well_formed_and_duration_bounded": not invalid_intervals,
        "all_receipts_have_registered_task_kind": not unknown_task_receipts,
        "single_shared_tool_has_no_overlapping_work_leases": not overlapping,
        "tool_lease_released_at_horizon": lease.get("status") == "FREE" if require_tool_released else True,
        "required_registered_outcomes_have_receipts": expected_receipts_present,
        **physical,
    }
    return {"schema": "ongoing-station-physical-work-audit-v1",
        "status": "PASS" if all(criteria.values()) else "NOT_CERTIFIED",
        "pass": all(criteria.values()), "criteria": criteria,
        "required_outcomes": list(required_outcomes),
        "receipt_checks": receipt_checks, "overlapping_work_intervals": overlapping,
        "unknown_task_kind_receipt_ids": unknown_task_receipts,
        "invalid_work_interval_receipt_ids": invalid_intervals,
        "tool_state": tool, "supply_state": supply, "storage_state": storage,
        "repair_exit_state": repair_exit,
        "settled_task_kinds": sorted(successful),
        "author_verdicts": station.get("real_verdicts"),
        "physical_outcomes_are_not_author_verdicts": True}


def audit_station_episode(trace: Mapping[str, Any], db: Mapping[str, Any], *,
                          expected_constraint_statuses: Mapping[str, str],
                          required_outcomes: tuple[str, ...] = ()) -> dict[str, Any]:
    """Audit both physical work evidence and explicit author-goal verdicts.

    A VERIFIED_NEGATIVE status means the expected violated goal and independent
    work were correctly evidenced; it does not mean the authored goal succeeded.
    """
    physical = audit_station_work(trace, db, required_outcomes=required_outcomes)
    station = trace.get("ongoing_station", {})
    station = station if isinstance(station, Mapping) else {}
    verdicts = station.get("real_verdicts", {})
    verdicts = verdicts if isinstance(verdicts, Mapping) else {}
    constraints = _rows(verdicts.get("constraints"))
    actual = {row.get("constraint_id", row.get("id")): row.get("status")
              for row in constraints if row.get("constraint_id", row.get("id")) is not None}
    expected = dict(expected_constraint_statuses)
    verdicts_match = bool(expected) and actual == expected
    negative = any(value == "VIOLATED" for value in expected.values())
    physical_criteria = physical.get("criteria", {})
    base_physical_checks = (
        "independent_scene_database_readback_present",
        "every_work_or_store_receipt_has_sealed_exact_p4_event",
        "work_receipt_intervals_are_well_formed_and_duration_bounded",
        "all_receipts_have_registered_task_kind",
        "single_shared_tool_has_no_overlapping_work_leases",
        "required_registered_outcomes_have_receipts",
        "tool_is_registered_evennia_object_and_state_matches_db",
        "storage_is_registered_evennia_object",
        "supply_evennia_location_and_inspection_match_trace",
        "repair_exit_evennia_identity_matches_trace",
    )
    outcome_checks = {
        "inspect_supply": ("inspection_approved_by_settled_receipt",
                           "supply_inspection_attribute_matches_independent_db"),
        "repair_passage": ("registered_passage_repaired",
                           "registered_exit_identity_and_persisted_traverse_lock_match_db"),
        "store_item": ("supply_stored_in_registered_container",
                       "registered_storage_contains_exact_supply_in_db"),
    }
    selected_checks = list(base_physical_checks)
    for outcome in required_outcomes:
        selected_checks.extend(outcome_checks.get(outcome, ()))
    selected_checks = tuple(dict.fromkeys(selected_checks))
    # A successful author episode must satisfy the complete physical audit.
    # A deliberate negative may omit the failed objective's physical effect,
    # but must still prove every declared independent result and all DB/receipt
    # identity checks above.
    physical_evidence_complete = (
        physical.get("pass") is True if not negative else
        all(physical_criteria.get(name) is True for name in selected_checks))
    evidence_complete = verdicts_match and physical_evidence_complete
    return {"schema": "ongoing-station-episode-evidence-audit-v1",
        "status": ("PASS" if evidence_complete and not negative else
                   "VERIFIED_NEGATIVE" if evidence_complete and negative else "NOT_CERTIFIED"),
        "pass": evidence_complete and not negative,
        "evidence_complete": evidence_complete,
        "objective_outcome_by_deadline": ("VIOLATED" if negative and verdicts_match
                                           else "SATISFIED" if verdicts_match
                                           else "UNVERIFIED"),
        "expected_constraint_statuses": expected,
        "actual_constraint_statuses": actual,
        "criteria": {"exact_author_verdicts_match": verdicts_match,
                     "independent_physical_evidence_complete": physical_evidence_complete,
                     "selected_physical_evidence_checks": list(selected_checks)},
        "physical_work_audit": physical}


def compare_history_frontiers(left: Mapping[str, Any], right: Mapping[str, Any], *,
                              allowed_observation_differences: tuple[str, ...] = ("known_tool_events",),
                              left_entity_aliases: Mapping[str, Any] | None = None,
                              right_entity_aliases: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Compare matched current frontiers and separately validate a history treatment.

    Scene-local numeric ids are normalized only when the caller supplies the
    stable entity alias map captured from each reset. History is never treated
    as a causal treatment merely because it is the only differing field: each
    arm must expose a real, sealed, witness-linked loan/return pair and a later
    actor decision for the same offer with different dispositions.
    """
    def id_map(trace: Mapping[str, Any], supplied: Mapping[str, Any] | None) -> dict[str, str]:
        aliases = dict(supplied or {})
        # Actor aliases are stable across scenes and safe to infer from the trace.
        for row in _rows(trace.get("actor_evidence")):
            if row.get("actor_id") is not None and row.get("actor_alias") in {"A", "B"}:
                aliases.setdefault(str(row["actor_id"]), str(row["actor_alias"]))
        station = trace.get("ongoing_station", {})
        state = station.get("station_work", {}) if isinstance(station, Mapping) else {}
        if isinstance(state, Mapping):
            for key, alias in (("tool", "station_tool"), ("storage", "station_storage"),
                               ("supply", "courier_supply"), ("repair_exit", "pickup_to_side_south")):
                value = state.get(key)
                if isinstance(value, Mapping) and value.get("id") is not None:
                    aliases.setdefault(str(value["id"]), alias)
                if isinstance(value, Mapping):
                    for field, room_alias in (("room_id", "pickup"), ("source_room_id", "pickup"),
                                              ("destination_room_id", "side")):
                        if value.get(field) is not None:
                            aliases.setdefault(str(value[field]), room_alias)
        return {str(identifier): str(alias) for identifier, alias in aliases.items()}

    def normalize(value: Any, aliases: Mapping[str, str], key: str = "") -> Any:
        if isinstance(value, Mapping):
            return {str(k): normalize(v, aliases, str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(item, aliases, key[:-1] if key.endswith("s") else key) for item in value]
        if (key == "id" or key.endswith("_id") or key.endswith("_ids")) and value is not None:
            if isinstance(value, list):
                return [aliases.get(str(item), item) for item in value]
            return aliases.get(str(value), value)
        return value

    def snapshot(trace: Mapping[str, Any], aliases: Mapping[str, str]) -> dict[str, Any]:
        station = trace.get("ongoing_station", {})
        station = station if isinstance(station, Mapping) else {}
        state = station.get("station_work", {})
        state = state if isinstance(state, Mapping) else {}
        actors = {}
        for actor in _rows(trace.get("actor_evidence")):
            alias = actor.get("actor_alias")
            if alias not in {"A", "B"}:
                continue
            decisions = [row for row in _rows(actor.get("log"))
                         if row.get("kind") == "ongoing_station_decision"]
            latest = deepcopy(decisions[-1]) if decisions else {}
            actors[alias] = normalize({"room_id": actor.get("room_id"),
                "inventory_ids": actor.get("inventory_ids"),
                "active_commitments": [row for row in _rows(station.get("commitments"))
                    if row.get("actor_alias") == alias
                    and row.get("status") in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}],
                "pending_action": actor.get("pending_action"),
                "view": latest.get("view", {}) if isinstance(latest, Mapping) else {}}, aliases)
        # Do not include whole actor/controller histories in the current-state
        # comparison; only physical work state, current commitments, O, and offers.
        return normalize({"minute": trace.get("complete_through"), "actors": actors,
            "station_work": state, "pending_offers": _rows(station.get("pending_offers"))}, aliases)

    def witnessed_history(trace: Mapping[str, Any], actor_alias: str = "A",
                         lender_alias: str = "A", borrower_alias: str = "B") -> dict[str, Any]:
        actor = next((row for row in _rows(trace.get("actor_evidence"))
                      if row.get("actor_alias") == actor_alias), None)
        decisions = [row for row in _rows(actor.get("log"))
                     if row.get("kind") == "ongoing_station_decision"] if actor else []
        latest = decisions[-1] if decisions else {}
        view = latest.get("view", {}) if isinstance(latest, Mapping) else {}
        observation = view.get("observation", {}) if isinstance(view, Mapping) else {}
        known = _rows(observation.get("known_tool_events")) if isinstance(observation, Mapping) else []
        ledger = {str(row.get("event_id")): row for row in _rows(trace.get("ledger"))
                  if row.get("sealed") is True and row.get("event_id") is not None}
        # Actor-local observation rows use the stable lowercase registry names;
        # the sealed P4 ledger uses uppercase event names.
        loans = [row for row in known if row.get("event_type") in {
                     "p5_station_tool_loaned", "P5_STATION_TOOL_LOANED"}
                 and row.get("witnessed_by_alias") == actor_alias
                 and row.get("lender_alias") == lender_alias
                 and row.get("borrower_alias") == borrower_alias]
        returns = [row for row in known if row.get("event_type") in {
                       "p5_station_tool_returned", "P5_STATION_TOOL_RETURNED"}
                   and row.get("witnessed_by_alias") == actor_alias
                   and row.get("lender_alias") == lender_alias
                   and row.get("borrower_alias") == borrower_alias]
        valid_pairs = []
        for loan in loans:
            for returned in returns:
                loan_id = loan.get("loan_id")
                if (not loan_id or returned.get("loan_id") != loan_id
                        or loan.get("tool_id") != returned.get("tool_id")
                        or loan.get("lender_alias") != returned.get("lender_alias")
                        or loan.get("borrower_alias") != returned.get("borrower_alias")
                        or returned.get("lender_alias") != lender_alias
                        or returned.get("borrower_alias") != borrower_alias):
                    continue
                loan_event = ledger.get(str(loan.get("event_id")))
                return_event = ledger.get(str(returned.get("event_id")))
                def event_matches(event, known_row, expected_type):
                    args = event.get("typed_args", {}) if isinstance(event, Mapping) else {}
                    return bool(event and event.get("event_type") == expected_type
                        and event.get("receipt_id") == known_row.get("receipt_id")
                        and event.get("minute") == known_row.get("witnessed_minute")
                        and args.get("receipt_id") == known_row.get("receipt_id")
                        and args.get("loan_id") == known_row.get("loan_id")
                        and args.get("tool_id") == known_row.get("tool_id")
                        and args.get("lender_alias") == known_row.get("lender_alias")
                        and args.get("borrower_alias") == known_row.get("borrower_alias")
                        and args.get("due_minute") == known_row.get("due_minute"))
                if not event_matches(loan_event, loan, "P5_STATION_TOOL_LOANED"):
                    continue
                if not event_matches(return_event, returned, "P5_STATION_TOOL_RETURNED"):
                    continue
                loan_args = loan_event.get("typed_args", {})
                return_args = return_event.get("typed_args", {})
                if (loan_args.get("outcome") != "SETTLED"
                        or return_args.get("returned_minute") != returned.get("returned_minute")
                        or return_args.get("outcome") != returned.get("outcome")):
                    continue
                due, returned_minute = returned.get("due_minute"), returned.get("returned_minute")
                outcome = returned.get("outcome")
                if (type(due) is not int or type(returned_minute) is not int
                        or loan.get("due_minute") != due
                        or type(loan_event.get("minute")) is not int
                        or type(return_event.get("minute")) is not int
                        or loan_event.get("minute") >= return_event.get("minute")
                        or returned.get("witnessed_minute") != returned_minute
                        or outcome not in {"ON_TIME", "LATE"}
                        or (outcome == "ON_TIME") != (returned_minute <= due)):
                    continue
                valid_pairs.append({"loan_id": loan_id, "tool_id": loan.get("tool_id"),
                    "lender_alias": loan.get("lender_alias"),
                    "borrower_alias": loan.get("borrower_alias"),
                    "due_minute": due, "returned_minute": returned_minute,
                    "outcome": outcome, "loan_event_id": loan.get("event_id"),
                    "return_event_id": returned.get("event_id"),
                    "receipt_ids": [loan.get("receipt_id"), returned.get("receipt_id")]})
        return {"valid_pairs": valid_pairs, "latest_decision": deepcopy(latest),
                "decision_minute": latest.get("minute") if isinstance(latest, Mapping) else None}

    left_ids, right_ids = id_map(left, left_entity_aliases), id_map(right, right_entity_aliases)
    a, b = snapshot(left, left_ids), snapshot(right, right_ids)
    treatment = {}
    for alias in ("A", "B"):
        for side, snap in (("left", a), ("right", b)):
            view = snap["actors"].get(alias, {}).get("view", {})
            observation = view.get("observation", {}) if isinstance(view, Mapping) else {}
            if isinstance(observation, Mapping):
                treatment[f"{side}.{alias}"] = {
                    key: deepcopy(observation.get(key)) for key in allowed_observation_differences
                    if key in observation}
                # Mutate only our private snapshot, never caller-owned traces.
                for key in allowed_observation_differences:
                    observation.pop(key, None)
    mismatches = []
    def walk(x, y, path="$"):
        if isinstance(x, Mapping) and isinstance(y, Mapping):
            for key in sorted(set(x) | set(y)):
                if key not in x or key not in y:
                    mismatches.append(f"{path}.{key}")
                else:
                    walk(x[key], y[key], f"{path}.{key}")
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                mismatches.append(f"{path}.length")
            for index, (lx, ry) in enumerate(zip(x, y)):
                walk(lx, ry, f"{path}[{index}]")
        elif x != y:
            mismatches.append(path)
    walk(a, b)
    aliases_supplied = bool(left_entity_aliases and right_entity_aliases)
    if left.get("scene_id") != right.get("scene_id") and not aliases_supplied:
        mismatches.append("$.stable_entity_alias_maps")
    # The local decision under test is the lender's decision to accept or
    # defer the borrower's request, so inspect A's witnessed history and later
    # A-owned lend_tool candidate (not B's borrower-side view).
    left_history = witnessed_history(left, actor_alias="A")
    right_history = witnessed_history(right, actor_alias="A")
    left_latest, right_latest = left_history["latest_decision"], right_history["latest_decision"]
    left_candidates = _rows(left_latest.get("goal_candidates"))
    right_candidates = _rows(right_latest.get("goal_candidates"))
    def candidate_signature(row, aliases):
        return normalize({key: row.get(key) for key in
            ("source", "task_kind", "goal_id", "actor_alias", "recipient_alias",
             "item_alias", "tool_alias", "due_minute", "deadline_minute", "prerequisites")}, aliases)
    left_requests = [candidate_signature(row, left_ids) for row in left_candidates
        if row.get("task_kind") == "lend_tool" and row.get("actor_alias") == "A"]
    right_requests = [candidate_signature(row, right_ids) for row in right_candidates
                      if row.get("task_kind") == "lend_tool" and row.get("actor_alias") == "A"]
    same_request = bool(left_requests and right_requests and left_requests == right_requests)
    left_decision = {key: left_latest.get(key) for key in ("disposition", "selected_goal", "rationale")}
    right_decision = {key: right_latest.get(key) for key in ("disposition", "selected_goal", "rationale")}
    histories_valid = bool(left_history["valid_pairs"] and right_history["valid_pairs"])
    decisions_follow_history = bool(
        histories_valid
        and type(left_history.get("decision_minute")) is int
        and type(right_history.get("decision_minute")) is int
        and left_history["decision_minute"] > max(
            row["returned_minute"] for row in left_history["valid_pairs"])
        and right_history["decision_minute"] > max(
            row["returned_minute"] for row in right_history["valid_pairs"]))
    outcomes_differ = (histories_valid and
        {row["outcome"] for row in left_history["valid_pairs"]}
        != {row["outcome"] for row in right_history["valid_pairs"]})
    decision_differs = bool(left_latest and right_latest and left_decision != right_decision)
    causal_allowed = bool(not mismatches and histories_valid and decisions_follow_history and outcomes_differ
                          and same_request and decision_differs)
    return {"schema": "ongoing-station-history-frontier-comparison-v2",
        "status": ("MATCHED_EXCEPT_DECLARED_HISTORY" if not mismatches else "CONFOUNDED"),
        "strict_physical_and_observation_match": not mismatches,
        "mismatch_paths": mismatches,
        "declared_history_fields": list(allowed_observation_differences),
        "history_treatment_values": treatment,
        "left_history_witnesses": left_history["valid_pairs"],
        "right_history_witnesses": right_history["valid_pairs"],
        "same_later_request": same_request,
        "left_later_decision": left_decision,
        "right_later_decision": right_decision,
        "history_outcomes_differ": bool(outcomes_differ),
        "later_decisions_follow_witnessed_history": decisions_follow_history,
        "subsequent_actor_decisions_differ": decision_differs,
        "history_causal_claim_allowed": causal_allowed,
        "causal_claim_blockers": [name for name, ok in (
            ("current_frontiers_not_matched", not mismatches),
            ("missing_receipt_backed_actor_local_history", histories_valid),
            ("history_outcomes_not_distinct", outcomes_differ),
            ("later_decision_not_after_history", decisions_follow_history),
            ("later_request_not_matched", same_request),
            ("later_actor_decisions_not_distinct", decision_differs)) if not ok],
        "left_scene_id": left.get("scene_id"), "right_scene_id": right.get("scene_id"),
        "entity_aliases_supplied": aliases_supplied}
