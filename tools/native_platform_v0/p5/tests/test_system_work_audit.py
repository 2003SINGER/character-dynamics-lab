import unittest

from tools.native_platform_v0.p5.ongoing_station.system_work_audit import (
    audit_station_episode, audit_station_work, compare_history_frontiers,
)


class SystemWorkAuditTests(unittest.TestCase):
    def _evidence(self):
        receipts = [
            {"receipt_id": "inspect-1", "action_id": "a1", "commitment_id": "c1",
             "actor_id": 10, "actor_alias": "A",
             "task_kind": "inspect_supply", "item_id": 3,
             "tool_id": 4, "started_minute": 2, "due_minute": 4,
             "completed_minute": 4, "duration_minutes": 2, "settled": True, "outcome": "SETTLED",
             "effect": {"after_status": "APPROVED"}},
            {"receipt_id": "repair-1", "action_id": "a2", "commitment_id": "c2",
             "actor_id": 10, "actor_alias": "A",
             "task_kind": "repair_passage", "target_id": 8,
             "tool_id": 4, "started_minute": 5, "due_minute": 8,
             "completed_minute": 8, "duration_minutes": 3, "settled": True, "outcome": "SETTLED",
             "effect": {"after_traversable": True}},
            {"receipt_id": "store-1", "task_kind": "store_item", "item_id": 3,
             "actor_id": 10, "actor_alias": "A", "tool_id": 4, "sim_minute": 9,
             "operator": "store_item", "kind": "store_item",
             "storage_id": 5, "after_container_id": 5, "settled": True,
             "outcome": "SETTLED"},
        ]
        events = [{"event_id": row["receipt_id"], "receipt_id": row["receipt_id"],
                   "minute": row.get("completed_minute", row.get("sim_minute")),
                   "event_type": {"inspect_supply": "P5_STATION_SUPPLY_INSPECTED",
                       "repair_passage": "P5_STATION_PASSAGE_REPAIRED",
                       "store_item": "P5_STATION_SUPPLY_STORED"}[row["task_kind"]],
                   "typed_args": {key: value for key, value in {
                       "receipt_id": row["receipt_id"], "commitment_id": row.get("commitment_id"),
                       "action_id": row.get("action_id"),
                       "operator": row.get("operator"), "kind": row.get("kind"),
                       "actor_id": row.get("actor_id"), "actor_alias": row.get("actor_alias"),
                       "task_kind": row["task_kind"], "tool_id": row.get("tool_id"),
                       "target_id": row.get("target_id"), "item_id": row.get("item_id"),
                       "storage_id": row.get("storage_id"),
                       "after_container_id": row.get("after_container_id"),
                       "started_minute": row.get("started_minute"), "due_minute": row.get("due_minute"),
                       "completed_minute": row.get("completed_minute"),
                       "sim_minute": row.get("sim_minute"), "outcome": row.get("outcome")
                   }.items() if value is not None}, "sealed": True}
                  for row in receipts]
        events.extend({"event_id": f"station-work:scene-x:{row['action_id']}:start",
            "receipt_id": f"station-work:scene-x:{row['action_id']}:start",
            "event_type": "P5_STATION_WORK_STARTED",
            "minute": row["started_minute"],
            "typed_args": {"action_id": row["action_id"], "commitment_id": row["commitment_id"]},
            "sealed": True} for row in receipts[:2])
        for row, event in zip(receipts[:2], events[3:5]):
            event["typed_args"].update({"tool_id": row["tool_id"], "target_id": row.get("target_id")})
        return ({"scene_id": "scene-x", "ongoing_station": {
            "station_work_receipts": {"A": receipts[:2]},
            "station_store_receipts": {"A": receipts[2:]},
            "station_work": {"tool": {"id": 4, "room_id": 1,
                                      "lease": {"status": "FREE"}},
                "supply": {"id": 3, "inspection_status": "APPROVED",
                           "location_id": 5},
                "storage": {"id": 5, "room_id": 2, "stored_item_ids": [3]},
                "repair_exit": {"id": 8, "source_room_id": 1,
                    "destination_room_id": 9, "key": "south", "traversable": True},
                "registered_ids": {"tool_id": 4, "storage_id": 5, "supply_id": 3,
                                   "repair_exit_id": 8}},
            "real_verdicts": {"constraints": [{"id": "goal", "status": "SATISFIED"}]}}},
            {"scenes": [{"scene_id": "scene-x", "objects": [
                {"id": 1, "location": None, "key": "Pickup",
                 "attributes": {"native_p3": {"p4_ledger": events}}},
                {"id": 2, "location": {"id": 20}, "key": "Destination",
                 "attributes": {"native_p5": {}}},
                {"id": 3, "location": {"id": 5}, "key": "Supply",
                 "attributes": {"native_p5": {"p5_supply_inspection_status": "APPROVED"}}},
                {"id": 4, "location": {"id": 1}, "key": "Tool",
                 "attributes": {"native_p5": {"p5_station_tool": True,
                    "p5_station_tool_lease": {"status": "FREE"}}}},
                {"id": 5, "location": {"id": 2}, "key": "Storage",
                 "contents_ids": [3],
                 "attributes": {"native_p5": {"p5_station_storage": True}}},
                {"id": 8, "location": {"id": 1}, "key": "south",
                 "exit_destination": {"id": 9}, "exit_traverse_lock": "traverse:true()",
                 "attributes": {"native_p5": {"p5_repair_target": True}}},
                {"id": 9, "location": None, "key": "Side",
                 "attributes": {"native_p5": {}}},
            ]}]})

    def test_work_pass_requires_real_receipt_ledger_and_world_witnesses(self):
        trace, db = self._evidence()
        audit = audit_station_work(trace, db,
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertTrue(audit["pass"])
        self.assertTrue(audit["physical_outcomes_are_not_author_verdicts"])
        self.assertTrue(audit["criteria"]["registered_exit_identity_and_persisted_traverse_lock_match_db"])
        self.assertEqual(audit["settled_task_kinds"],
                         ["inspect_supply", "repair_passage", "store_item"])

    def test_store_receipt_with_null_task_kind_uses_registered_operator(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["station_store_receipts"]["A"][0]["task_kind"] = None
        audit = audit_station_work(trace, db,
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertTrue(audit["pass"])
        store = next(row for row in audit["receipt_checks"]
                     if row["receipt_id"] == "store-1")
        self.assertEqual(store["task_kind"], "store_item")

    def test_unknown_receipt_kind_is_rejected_without_sorting_crash(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["station_store_receipts"]["A"].append({
            "receipt_id": "unknown-kind", "task_kind": None, "operator": None,
            "settled": False, "outcome": "ABORTED"})
        audit = audit_station_work(trace, db,
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertFalse(audit["pass"])
        self.assertEqual(audit["unknown_task_kind_receipt_ids"], ["unknown-kind"])

    def test_plan_or_offer_without_receipt_does_not_certify_physical_work(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["station_work_receipts"]["A"].clear()
        trace["ongoing_station"]["station_store_receipts"]["A"].clear()
        trace["ongoing_station"]["pending_offers"] = [
            {"task_kind": "inspect_supply", "status": "ACCEPTED"}]
        audit = audit_station_work(trace, db,
            required_outcomes=("inspect_supply", "store_item"))
        self.assertFalse(audit["pass"])
        self.assertFalse(audit["criteria"]["required_registered_outcomes_have_receipts"])
        self.assertFalse(audit["criteria"]["inspection_approved_by_settled_receipt"])

    def test_same_receipt_id_with_mismatched_typed_args_is_not_native_witness(self):
        trace, db = self._evidence()
        ledger = db["scenes"][0]["objects"][0]["attributes"]["native_p3"]["p4_ledger"]
        ledger[0]["typed_args"]["actor_id"] = 999
        audit = audit_station_work(trace, db, required_outcomes=("inspect_supply",))
        self.assertFalse(audit["pass"])
        check = next(row for row in audit["receipt_checks"] if row["receipt_id"] == "inspect-1")
        self.assertFalse(check["ledger_witness_matches"])

    def test_expected_negative_goal_is_verified_without_calling_objective_success(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["real_verdicts"]["constraints"] = [
            {"id": "storage", "status": "VIOLATED"}]
        audit = audit_station_episode(trace, db,
            expected_constraint_statuses={"storage": "VIOLATED"},
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertEqual(audit["status"], "VERIFIED_NEGATIVE")
        self.assertFalse(audit["pass"])
        self.assertTrue(audit["evidence_complete"])
        self.assertEqual(audit["objective_outcome_by_deadline"], "VIOLATED")

    def test_satisfied_author_verdict_cannot_override_missing_database_storage_effect(self):
        trace, db = self._evidence()
        objects = db["scenes"][0]["objects"]
        next(row for row in objects if row["id"] == 3)["location"]["id"] = 1
        next(row for row in objects if row["id"] == 5)["contents_ids"] = []
        audit = audit_station_episode(trace, db,
            expected_constraint_statuses={"goal": "SATISFIED"},
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertEqual(audit["status"], "NOT_CERTIFIED")
        self.assertFalse(audit["evidence_complete"])
        self.assertFalse(audit["physical_work_audit"]["criteria"]
                         ["registered_storage_contains_exact_supply_in_db"])

    def test_verified_negative_can_require_only_named_independent_work_outcomes(self):
        trace, db = self._evidence()
        station = trace["ongoing_station"]
        station["real_verdicts"]["constraints"] = [{"id": "goal", "status": "VIOLATED"}]
        station["station_store_receipts"]["A"].clear()
        station["station_work"]["supply"]["location_id"] = 1
        station["station_work"]["storage"]["stored_item_ids"] = []
        objects = db["scenes"][0]["objects"]
        next(row for row in objects if row["id"] == 3)["location"]["id"] = 1
        next(row for row in objects if row["id"] == 5)["contents_ids"] = []
        ledger = next(row for row in objects if row["id"] == 1)["attributes"]
        ledger["native_p3"]["p4_ledger"] = [
            row for row in ledger["native_p3"]["p4_ledger"] if row["receipt_id"] != "store-1"]
        audit = audit_station_episode(trace, db,
            expected_constraint_statuses={"goal": "VIOLATED"},
            required_outcomes=("inspect_supply", "repair_passage"))
        self.assertEqual(audit["status"], "VERIFIED_NEGATIVE")
        self.assertTrue(audit["evidence_complete"])
        self.assertEqual(audit["objective_outcome_by_deadline"], "VIOLATED")

    def test_negative_with_missing_declared_receipt_is_not_evidence_complete(self):
        trace, db = self._evidence()
        station = trace["ongoing_station"]
        station["real_verdicts"]["constraints"] = [{"id": "goal", "status": "VIOLATED"}]
        station["station_work_receipts"]["A"] = [
            row for row in station["station_work_receipts"]["A"]
            if row.get("task_kind") != "repair_passage"]
        audit = audit_station_episode(trace, db,
            expected_constraint_statuses={"goal": "VIOLATED"},
            required_outcomes=("inspect_supply", "repair_passage"))
        self.assertEqual(audit["status"], "NOT_CERTIFIED")
        self.assertFalse(audit["evidence_complete"])
        self.assertFalse(audit["physical_work_audit"]["criteria"]
                         ["required_registered_outcomes_have_receipts"])

    def test_unexpected_author_verdict_is_not_evidence_complete(self):
        trace, db = self._evidence()
        audit = audit_station_episode(trace, db,
            expected_constraint_statuses={"not-the-real-goal": "VIOLATED"})
        self.assertEqual(audit["status"], "NOT_CERTIFIED")
        self.assertFalse(audit["evidence_complete"])

    def test_independent_db_exit_lock_and_container_location_are_not_inferred_from_trace(self):
        trace, db = self._evidence()
        objects = db["scenes"][0]["objects"]
        next(row for row in objects if row["id"] == 8)["exit_traverse_lock"] = "traverse:false()"
        next(row for row in objects if row["id"] == 3)["location"]["id"] = 1
        audit = audit_station_work(trace, db,
            required_outcomes=("inspect_supply", "repair_passage", "store_item"))
        self.assertFalse(audit["criteria"]["registered_exit_identity_and_persisted_traverse_lock_match_db"])
        self.assertFalse(audit["criteria"]["registered_storage_contains_exact_supply_in_db"])

    def test_malformed_work_duration_is_not_silently_omitted_from_capacity_check(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["station_work_receipts"]["A"][0]["completed_minute"] = 3
        audit = audit_station_work(trace, db)
        self.assertFalse(audit["criteria"]["work_receipt_intervals_are_well_formed_and_duration_bounded"])
        self.assertEqual(audit["invalid_work_interval_receipt_ids"], ["inspect-1"])

    def test_overlapping_work_receipt_intervals_fail_capacity_one_audit(self):
        trace, db = self._evidence()
        trace["ongoing_station"]["station_work_receipts"]["B"] = [{
            "receipt_id": "repair-overlap", "task_kind": "repair_passage",
            "action_id": "a3", "commitment_id": "c3",
            "started_minute": 3, "due_minute": 6, "completed_minute": 5,
            "duration_minutes": 3, "settled": False,
            "outcome": "ABORTED"}]
        audit = audit_station_work(trace, db)
        self.assertFalse(audit["criteria"]["single_shared_tool_has_no_overlapping_work_leases"])
        self.assertEqual(audit["overlapping_work_intervals"],
                         [["inspect-1", "repair-overlap"]])

    def _frontier(self, *, known_events, room=1):
        return {"scene_id": "separate-scene", "complete_through": 9,
            "actor_evidence": [
                {"actor_alias": "A", "room_id": room, "inventory_ids": [4],
                 "log": [{"kind": "ongoing_station_decision", "view": {
                     "observation": {"room_id": room, "inventory": [4],
                                     "known_tool_events": known_events}}}]},
                {"actor_alias": "B", "room_id": 2, "inventory_ids": [],
                 "log": [{"kind": "ongoing_station_decision", "view": {
                     "observation": {"room_id": 2, "inventory": [],
                                     "known_tool_events": []}}}]},
            ],
            "ongoing_station": {"station_work": {
                "tool": {"id": 4, "room_id": 1, "held_by_actor_id": 10,
                         "lease": {"status": "FREE"}},
                "supply": {"id": 3, "location_id": 1, "inspection_status": "APPROVED"},
                "storage": {"id": 5, "stored_item_ids": []},
                "repair_exit": {"id": 8, "traversable": False}},
                "commitments": [], "pending_offers": []}}

    def test_history_pair_only_ignores_declared_actor_local_history_difference(self):
        left = self._frontier(known_events=[{"event": "p5_station_tool_returned",
                                               "outcome": "ON_TIME"}])
        right = self._frontier(known_events=[{"event": "p5_station_tool_returned",
                                                "outcome": "LATE"}])
        comparison = compare_history_frontiers(left, right)
        self.assertEqual(comparison["status"], "MATCHED_EXCEPT_DECLARED_HISTORY")
        self.assertFalse(comparison["history_causal_claim_allowed"])
        self.assertIn("missing_receipt_backed_actor_local_history",
                      comparison["causal_claim_blockers"])
        self.assertEqual(left["actor_evidence"][0]["log"][0]["view"]["observation"]
                         ["known_tool_events"][0]["outcome"], "ON_TIME")
        right["actor_evidence"][0]["room_id"] = 99
        comparison = compare_history_frontiers(left, right)
        self.assertEqual(comparison["status"], "CONFOUNDED")
        self.assertFalse(comparison["history_causal_claim_allowed"])
        self.assertIn("$.actors.A.room_id", comparison["mismatch_paths"])

    def _history_trace(self, *, outcome, selected):
        loan_id = f"loan-{outcome}"
        loan_receipt, return_receipt = f"loan-receipt-{outcome}", f"return-receipt-{outcome}"
        loan_event, return_event = f"station:{loan_receipt}", f"station:{return_receipt}"
        loan = {"event_type": "p5_station_tool_loaned", "event_id": loan_event,
                "receipt_id": loan_receipt, "loan_id": loan_id, "tool_id": 4,
                "lender_alias": "A", "borrower_alias": "B", "due_minute": 6,
                "outcome": "SETTLED",
                "witnessed_by_alias": "A", "witnessed_minute": 2}
        returned_minute = 5 if outcome == "ON_TIME" else 8
        returned = {"event_type": "p5_station_tool_returned", "event_id": return_event,
                "receipt_id": return_receipt, "loan_id": loan_id, "tool_id": 4,
                "lender_alias": "A", "borrower_alias": "B", "due_minute": 6,
                "returned_minute": returned_minute, "outcome": outcome,
                "witnessed_by_alias": "A", "witnessed_minute": returned_minute}
        def ledger_row(row, event_type):
            return {"event_id": row["event_id"], "event_type": event_type,
                "minute": row["witnessed_minute"],
                "receipt_id": row["receipt_id"], "sealed": True,
                "typed_args": {key: row[key] for key in
                    ("receipt_id", "loan_id", "tool_id", "lender_alias",
                     "borrower_alias", "due_minute", "returned_minute", "outcome")
                    if key in row}}
        request = {"source": "SELF", "task_kind": "lend_tool", "goal_id": "loan-goal",
                   "actor_alias": "A", "recipient_alias": "B", "tool_alias": "station_tool",
                   "due_minute": 10, "deadline_minute": 10, "prerequisites": []}
        decision = {"kind": "ongoing_station_decision", "minute": 10,
            "disposition": "ACCEPTED" if selected else "DEFERRED",
            "selected_goal": "request" if selected else None,
            "rationale": "history-conditioned choice",
            "goal_candidates": [request],
            "view": {"observation": {"room_id": 1, "inventory": [],
                "known_tool_events": [loan, returned], "visible_items": [], "exits": []}}}
        trace = self._frontier(known_events=[loan, returned])
        trace["ledger"] = [ledger_row(loan, "P5_STATION_TOOL_LOANED"),
                           ledger_row(returned, "P5_STATION_TOOL_RETURNED")]
        a_actor = next(row for row in trace["actor_evidence"] if row["actor_alias"] == "A")
        a_actor["log"] = [decision]
        return trace

    def test_history_causal_claim_requires_real_ledger_witness_same_request_and_changed_decision(self):
        left = self._history_trace(outcome="ON_TIME", selected=True)
        right = self._history_trace(outcome="LATE", selected=False)
        comparison = compare_history_frontiers(left, right)
        self.assertTrue(comparison["strict_physical_and_observation_match"])
        self.assertTrue(comparison["same_later_request"])
        self.assertTrue(comparison["history_outcomes_differ"])
        self.assertTrue(comparison["subsequent_actor_decisions_differ"])
        self.assertTrue(comparison["history_causal_claim_allowed"])
        right["ledger"].pop()
        comparison = compare_history_frontiers(left, right)
        self.assertFalse(comparison["history_causal_claim_allowed"])
        self.assertIn("missing_receipt_backed_actor_local_history",
                      comparison["causal_claim_blockers"])

    def test_history_comparison_does_not_mutate_input_and_requires_decision_difference(self):
        from copy import deepcopy
        left = self._history_trace(outcome="ON_TIME", selected=True)
        right = self._history_trace(outcome="LATE", selected=True)
        before = deepcopy((left, right))
        comparison = compare_history_frontiers(left, right)
        self.assertFalse(comparison["history_causal_claim_allowed"])
        self.assertEqual((left, right), before)

    def test_cross_scene_frontier_needs_stable_alias_maps_for_id_normalization(self):
        left = self._frontier(known_events=[])
        right = self._frontier(known_events=[])
        left["scene_id"], right["scene_id"] = "scene-left", "scene-right"
        for actor, actor_id, room, inventory in (
                (left["actor_evidence"][0], 10, 1, [4]),
                (left["actor_evidence"][1], 20, 2, [])):
            actor.update(actor_id=actor_id, room_id=room, inventory_ids=inventory)
            actor["log"][0]["view"]["observation"]["room_id"] = room
            actor["log"][0]["view"]["observation"]["inventory"] = [
                {"id": item} for item in inventory]
        left["ongoing_station"]["station_work"]["storage"]["room_id"] = 2
        for actor, actor_id, room, inventory in (
                (right["actor_evidence"][0], 110, 101, [104]),
                (right["actor_evidence"][1], 120, 102, [])):
            actor.update(actor_id=actor_id, room_id=room, inventory_ids=inventory)
            actor["log"][0]["view"]["observation"]["room_id"] = room
            actor["log"][0]["view"]["observation"]["inventory"] = [
                {"id": item} for item in inventory]
        right_state = right["ongoing_station"]["station_work"]
        right_state["tool"].update(id=104, room_id=101, held_by_actor_id=110)
        right_state["supply"].update(id=103, location_id=101)
        right_state["storage"].update(id=105, room_id=102)
        right_state["repair_exit"].update(id=108)
        without_maps = compare_history_frontiers(left, right)
        self.assertEqual(without_maps["status"], "CONFOUNDED")
        aliases_left = {"1": "pickup", "2": "side", "3": "courier_supply",
                        "4": "station_tool", "5": "station_storage",
                        "8": "pickup_to_side_south", "10": "A", "20": "B"}
        aliases_right = {"101": "pickup", "102": "side", "103": "courier_supply",
                         "104": "station_tool", "105": "station_storage",
                         "108": "pickup_to_side_south", "110": "A", "120": "B"}
        comparison = compare_history_frontiers(left, right,
            left_entity_aliases=aliases_left, right_entity_aliases=aliases_right)
        self.assertEqual(comparison["status"], "MATCHED_EXCEPT_DECLARED_HISTORY")
        self.assertTrue(comparison["entity_aliases_supplied"])


if __name__ == "__main__":
    unittest.main()
