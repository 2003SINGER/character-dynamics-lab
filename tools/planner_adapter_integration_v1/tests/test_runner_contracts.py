from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.planner_adapter_integration_v1.run_suite import load_suite
from tools.planner_adapter_integration_v1.runner import (
    _allocate, _dispatch_allowed, _native_action, replay_saved_snapshot_pilot)
from tools.planner_adapter_integration_v1.audit import build_step_audit
from tools.planner_adapter_integration_v1.sabre import decode_plan
from tools.native_platform_v0.p5.bundle import load_bundle


class RunnerContractTests(unittest.TestCase):
    def test_saved_snapshot_replay_refuses_changed_frontier_without_reset_or_observe(self):
        prior = Path(__file__).parent / "fixtures/native-minute0-replay-contract"
        calls = []
        def rpc(op, args):
            calls.append(op)
            return {"scene_id": args["scene_id"], "now": 1,
                    "complete_through": {"events": 0, "values": 0}, "ledger": [],
                    "typed_trace": {"events": []}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            result = replay_saved_snapshot_pilot(scene_id="20261012024000-c1f859",
                bundle_path=Path(__file__).resolve().parents[1] / "cases/wide24.json",
                prior_run_dir=prior, output_parent=directory, rpc=rpc)
            self.assertEqual(result["status"], "INCOMPLETE_ERROR")
            self.assertEqual(result["stage"], "verify_existing_sealed_frontier")
        self.assertEqual(calls, ["get_trace"])

    def test_only_registered_first_action_is_native_dispatchable(self):
        self.assertEqual(_native_action({"plan_actions": ["open_side_passage()", "move(A, Pickup, Side)"]}),
                         ("open_side_passage()", "open_side_passage"))
        self.assertEqual(_native_action({"plan_actions": ["move(A, Pickup, Side)", "open_side_passage()"]}),
                         (None, None))
        self.assertEqual(_native_action({"plan_actions": ["respond_note(Accepted)"]}), (None, None))
        failed_parse = decode_plan(["open_side_passage()"], native_status="NO_CANDIDATE")
        self.assertIsNone(failed_parse["dispatch_action"])
        self.assertEqual(failed_parse["evidence_status"], "NO_CANDIDATE")

    def test_projection_residual_and_pending_wait_block_native_dispatch(self):
        common = {"method": "sabre", "plan": {"status": "SUCCESS", "returncode": 0},
                  "decoded": {"native_dispatchable": True}, "opportunity": "open_side_passage",
                  "player_intervention": None, "edit_now": False}
        self.assertTrue(_dispatch_allowed(projection={"dispatchable": True,
            "hard_residuals": [], "wait_reason": None}, **common))
        self.assertFalse(_dispatch_allowed(projection={"dispatchable": False,
            "hard_residuals": ["unsupported hard target"], "wait_reason": None}, **common))
        self.assertFalse(_dispatch_allowed(projection={"dispatchable": False,
            "hard_residuals": [], "wait_reason": "actor A has pending action"}, **common))

    def test_run_allocation_is_non_overwriting(self):
        # The managed environment can deny system temporary directories; keep
        # this self-cleaning fixture under the package test directory.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            first = _allocate(Path(directory), "same-case")
            second = _allocate(Path(directory), "same-case")
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_fixed_suite_has_method_matched_wide_tight_and_failure_cases(self):
        suite, cases = load_suite()
        self.assertEqual(suite["schema"], "planner-adapter-integration-v1-cases")
        by_id = {row["id"]: row for row in cases}
        for stem in ("outcome-wide24", "outcome-tight12", "outcome-wide24-budget1",
                     "outcome-tight12-budget1", "outcome-no-opportunity-budget",
                     "outcome-no-world-permission",
                     "outcome-player-interruption-cas-edit"):
            self.assertIn(f"{stem}-sabre", by_id)
            self.assertIn(f"{stem}-p5_director", by_id)
            left, right = by_id[f"{stem}-sabre"], by_id[f"{stem}-p5_director"]
            for key in ("bundle", "preset", "horizon", "seed", "initial_main_open",
                        "scheduled_edit", "scheduled_interventions"):
                self.assertEqual(left.get(key), right.get(key))
        self.assertEqual(by_id["outcome-wide24-sabre"]["horizon"], 24)
        self.assertEqual(by_id["outcome-tight12-sabre"]["horizon"], 24)
        wide = json.loads(Path(by_id["outcome-wide24-sabre"]["bundle"]).read_text())
        tight = json.loads(Path(by_id["outcome-tight12-sabre"]["bundle"]).read_text())
        for actor, item in (("A", "courier_supply"), ("B", "resident_parcel")):
            def deadline(bundle):
                return next(row["deadline"] for row in bundle["constraints"]
                            if row.get("event") == "delivery_settled"
                            and row.get("filters", {}).get("actor") == actor
                            and row.get("filters", {}).get("item") == item)
            self.assertEqual(deadline(wide), 24)
            self.assertEqual(deadline(tight), 12)
        self.assertEqual(wide["permissions"]["cost_budget"], 2)
        self.assertEqual(tight["permissions"]["cost_budget"], 2)
        self.assertEqual(wide["permissions"]["world_opportunities"],
                         tight["permissions"]["world_opportunities"])
        budget_wide = json.loads(Path(by_id["outcome-wide24-budget1-sabre"]["bundle"]).read_text())
        budget_tight = json.loads(Path(by_id["outcome-tight12-budget1-sabre"]["bundle"]).read_text())
        self.assertEqual(budget_wide["permissions"]["cost_budget"], 1)
        self.assertEqual(budget_tight["permissions"]["cost_budget"], 1)
        for row in cases:
            load_bundle(json.loads(Path(row["bundle"]).read_text(encoding="utf-8")))

    def test_permission_and_budget_failures_are_separate_controls(self):
        suite, cases = load_suite()
        row = next(c for c in cases if c["id"] == "outcome-no-opportunity-budget-sabre")
        bundle = json.loads(Path(row["bundle"]).read_text(encoding="utf-8"))
        self.assertEqual(set(bundle["permissions"]["world_opportunities"]),
                         {"open_main_passage", "open_side_passage"})
        self.assertEqual(bundle["permissions"]["cost_budget"], 0)
        denied = next(c for c in cases if c["id"] == "outcome-no-world-permission-sabre")
        denied_bundle = json.loads(Path(denied["bundle"]).read_text(encoding="utf-8"))
        self.assertEqual(denied_bundle["permissions"]["world_opportunities"], [])
        self.assertEqual(denied_bundle["permissions"]["cost_budget"], 2)

    def test_player_interruption_has_fixed_get_edit_and_same_room_drop_schedule(self):
        suite, cases = load_suite()
        case = next(c for c in cases if c["id"] == "outcome-player-interruption-cas-edit-sabre")
        self.assertEqual(case["scheduled_interventions"], [
            {"at": 2, "kind": "player_command", "operation": "get",
             "item_alias": "courier_supply"},
            {"at": 6, "kind": "player_command", "operation": "drop",
             "item_alias": "courier_supply"}])
        self.assertEqual(case["scheduled_edit"]["at"], 2)

    def test_stale_guard_control_uses_same_bundle_identity_next_version(self):
        suite = json.loads((Path(__file__).parent.parent / "cases/suite.json").read_text())
        case_dir = Path(__file__).parent.parent / "cases"
        original = json.loads((case_dir / suite["stale_negative"]["bundle"]).read_text())
        edited = json.loads((case_dir / suite["stale_negative"]["edited_bundle"]).read_text())
        self.assertEqual(original["bundle_id"], edited["bundle_id"])
        self.assertEqual(edited["version"], original["version"] + 1)

    def test_native_join_keeps_prediction_separate_and_verifies_prefix(self):
        pending = {"operation_id": "op-1", "status": "planned", "planned_at_tick": 0,
                   "intent": {"operator": "drop", "destination_id": 901},
                   "view": {"goal_contract": {"item_id": 501},
                            "observation": {"room_id": 901}}}
        before_actor = {"actor_alias": "A", "pending_action": pending,
                        "native_receipts": [], "log": [
                            {"kind": "p5_primitive_intent", "pending_action": {
                                "operation_id": "op-1", "status": "planned",
                                "intent": {"operator": "drop", "destination_id": 901},
                                "view": {"goal_contract": {"item_id": 501}}}, "sim_minute": 0}]}
        before = {"now": 0, "ledger": [{"event_id": "e0"}],
                  "pending_future_nonexecuted": {}, "world_snapshots": [
                      {"minute": 0, "routes": {"main_passage": False}}],
                  "actor_evidence": [before_actor, {"actor_alias": "B", "pending_action": {
                      "operation_id": "op-2", "status": "planned", "intent": {
                          "operator": "get", "item_id": 601}, "view": {"goal_contract": {
                              "item_id": 601}, "observation": {"room_id": 902}}},
                      "native_receipts": [], "log": [{"kind": "p5_primitive_intent",
                          "sim_minute": 0, "pending_action": {"operation_id": "op-2",
                              "intent": {"operator": "get", "item_id": 601},
                              "view": {"goal_contract": {"item_id": 601},
                                       "observation": {"room_id": 902}}}}]}],
                  "world_capability_projection": {"task_bindings": {
                      "A": {"item_id": 501, "destination_id": 901},
                      "B": {"item_id": 601, "destination_id": 901}}}}
        after = {"now": 1, "ledger": [{"event_id": "e0"}, {"event_id": "e1"}],
                 "pending_future_nonexecuted": {}, "bundle_identity": {"version": 1},
                 "world_snapshots": [{"minute": 1, "routes": {"main_passage": True}}],
                 "actor_evidence": [{"actor_alias": "A", "pending_action": None,
                    "native_receipts": [{"receipt_id": "receipt-1", "kind": "drop",
                        "item_id": 501, "after_item_room_id": 901, "settled": True}],
                    "log": [{"kind": "p5_goal_choice", "choice": "deliver_supply", "view": {
                        "observation": {"task_item": {"id": 501}, "task_destination": 901}}},
                        {"kind": "execution_settlement", "status": "SETTLED", "sim_minute": 1,
                         "intent": {"operator": "drop", "destination_id": 901},
                         "receipt": {"receipt_id": "receipt-1", "kind": "drop", "item_id": 501,
                            "after_item_room_id": 901, "settled": True}}]},
                    {"actor_alias": "B", "pending_action": None, "native_receipts": [],
                     "log": [{"kind": "execution_settlement", "status": "WORLD_VALIDATION_REJECTED",
                         "sim_minute": 1, "intent": {"operator": "get", "item_id": 601},
                         "receipt": {"receipt_id": "receipt-failed", "kind": "get", "item_id": 601,
                             "before_room_id": 902, "after_room_id": 902,
                             "after_inventory_ids": [], "settled": False}}]}],
                 "world_capability_projection": before["world_capability_projection"]}
        step = {"rounds": [{"actor_steps": [{"actor_alias": "A", "local_decisions": [],
            "native_receipts": [{"receipt_id": "receipt-1", "kind": "drop", "item_id": 501,
                "after_item_room_id": 901, "settled": True}]},
            {"actor_alias": "B", "local_decisions": [], "native_receipts": []}]}]}
        report = build_step_audit(decoded_plan={"ordered_actions": ["move(A, Pickup, Porch)"],
            "handoff_status": "PREDICTION_ONLY_NOT_DISPATCHED"}, native_step=step,
            before_trace=before, after_trace=after, candidate_bundle_version=1)
        self.assertTrue(report["feedback"]["sealed_historical_ledger_prefix_preserved"])
        self.assertTrue(report["feedback"]["route_state_changed"])
        self.assertFalse(report["native_dynamic_task_dispatch_supported"])
        actor_a = report["actor_evidence_join"]["A"]
        self.assertTrue(actor_a["task_binding_matches"][0]["exact_existing_task_binding"])
        self.assertEqual(actor_a["operation_id_receipt_join_status"],
                         "UNAVAILABLE_NATIVE_RECEIPT_SCHEMA")
        self.assertEqual(actor_a["intent_receipt_semantic_joins"][0]["receipt_id"], "receipt-1")
        self.assertEqual(actor_a["intent_receipt_semantic_joins"][0]["join_method"],
                         "sequenced_single_pending_callback_semantic")
        actor_b = report["actor_evidence_join"]["B"]
        self.assertEqual(actor_b["intent_receipt_semantic_joins"][0]["status"],
                         "WORLD_VALIDATION_REJECTED")
        self.assertFalse(actor_b["intent_receipt_semantic_joins"][0]["expected_transition_observed"])
        self.assertFalse(actor_b["intent_receipt_semantic_joins"][0]["settled_receipt_stored"])


if __name__ == "__main__":
    unittest.main()
