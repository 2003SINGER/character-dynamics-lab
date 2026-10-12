import json
import importlib.util
from pathlib import Path
import unittest

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.native_platform_v0.p5.planning import plan
from tools.native_platform_v0.p5.service import _candidate_guard_matches
from tools.mature_methods_integration_v1.audit import _ordered_prefix
from tools.mature_methods_integration_v1.runner import (
    SOURCE_PATHS, _candidate_and_guard, _source_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"


def _raw(name):
    return json.loads((CASES / name).read_text(encoding="utf-8"))


def _initial_state(bundle):
    return {
        "now": 0,
        "horizon": 24,
        "routes": [
            {"id": "main_passage", "opportunity_id": "open_main_passage",
             "open": False, "available": True, "cost": 2,
             "min_minutes": 2, "resource": None},
            {"id": "side_passage", "opportunity_id": "open_side_passage",
             "open": False, "available": True, "cost": 1,
             "min_minutes": 3, "resource": None},
        ],
        "spent_cost": 0,
        "opportunities_used": 0,
        "verdicts": [{"constraint_id": goal.constraint_id, "status": "PENDING"}
                     for goal in bundle.goals],
        "physical_budget": 2,
    }


class FixedCaseMatrixContractTests(unittest.TestCase):
    def test_suite_is_exactly_four_pairs_with_symmetric_native_sampling(self):
        suite = _raw("suite.json")
        self.assertEqual(suite["schema"], "mature-methods-integration-suite-v1")
        self.assertEqual(len(suite["cases"]), 4)
        self.assertEqual(suite["native_run_policy"]["max_case_pairs"], 4)
        self.assertEqual(suite["native_run_policy"]["max_native_scenes"], 8)
        self.assertEqual(suite["common"]["external_observe_actor_calls"], 0)
        self.assertEqual(suite["common"]["seed"], 20261012)
        self.assertEqual(suite["common"]["horizon"], 24)
        self.assertFalse(suite["acceptance_vocabulary"]["proposal_is_goal_satisfaction"])
        self.assertFalse(suite["acceptance_vocabulary"]["wait_is_native_fact"])
        self.assertFalse(suite["acceptance_vocabulary"]["npc_plan_is_native_receipt"])

    def test_result_only_goal_keeps_route_out_of_author_bundle(self):
        raw = _raw("bundle-result-only-v1.json")
        bundle = load_bundle(raw)
        hard_ids = {goal.constraint_id for goal in bundle.goals if goal.hard}
        self.assertEqual(hard_ids, {
            "courier-delivery", "resident-delivery", "native-note-response",
            "A-delivery-before-note",
        })
        self.assertFalse(any(goal["kind"] == "state_by_deadline" for goal in raw["constraints"]))
        self.assertEqual(set(bundle.permissions["world_opportunities"]),
                         {"open_main_passage", "open_side_passage"})
        order = next(goal.constraint for goal in bundle.goals
                     if goal.constraint_id == "A-delivery-before-note")
        self.assertEqual(order.order.value, "PHYSICAL_TIME")
        self.assertEqual(order.before_filter["actor"].stable_id, "A")
        self.assertEqual(order.after_filter["actor"].stable_id, "A")
        self.assertEqual(order.after_filter["recipient"].stable_id, "B")
        self.assertEqual(order.before_filter["item"].stable_id, "courier_supply")
        self.assertEqual(order.after_filter["item"].stable_id, "note")

    def test_unchanged_director_selects_from_actual_registered_candidates(self):
        bundle = load_bundle(_raw("bundle-result-only-v1.json"))
        state = _initial_state(bundle)
        result = plan(bundle, state)
        self.assertEqual(result["selected_action"], "open_side_passage")
        self.assertEqual(result["schema"], "p5-plan-v1")
        self.assertFalse(result["prediction_guarantee"])
        side = next(row for row in result["candidates"] if row["candidate_id"] == "path:side_passage")
        main = next(row for row in result["candidates"] if row["candidate_id"] == "path:main_passage")
        self.assertTrue(side["feasible"])
        self.assertTrue(main["feasible"])
        self.assertEqual(side["incremental_cost"], 1)
        self.assertEqual(main["incremental_cost"], 2)
        self.assertFalse(any(row["constraint_id"] == "resident-delivery"
                             and not row["parallel_unaffected"]
                             for row in side["goal_support"]))

    def test_s2_permission_edit_preserves_goals_and_changes_legal_candidate(self):
        v1 = load_bundle(_raw("bundle-result-only-v1.json"))
        v2 = load_bundle(_raw("bundle-main-only-v2.json"))
        self.assertEqual(v1.bundle_id, v2.bundle_id)
        self.assertEqual(v2.version, v1.version + 1)
        self.assertEqual([goal.constraint_id for goal in v1.goals],
                         [goal.constraint_id for goal in v2.goals])
        self.assertEqual(v2.permissions["cost_budget"], 2)
        plan_v1 = plan(v1, _initial_state(v1))
        state_v2 = _initial_state(v2)
        state_v2["routes"][1]["available"] = False
        plan_v2 = plan(v2, state_v2)
        self.assertEqual(plan_v1["selected_action"], "open_side_passage")
        self.assertEqual(plan_v2["selected_action"], "open_main_passage")
        self.assertEqual(state_v2["opportunities_used"], 0)

    def test_s2_old_candidate_guard_is_rejected_after_same_boundary_edit(self):
        old_guard = {
            "scene_id": "offline-scene",
            "bundle_version": 1,
            "based_on_minute": 0,
            "events_through": 0,
            "values_through": 0,
            "selected_action": "open_side_passage",
            "opportunity_id": "open_side_passage",
        }
        self.assertTrue(_candidate_guard_matches(
            old_guard, scene_id="offline-scene", bundle_version=1, now=1,
            events_through=0, values_through=0, action="open_side_passage",
            opportunity_id="open_side_passage"))
        self.assertFalse(_candidate_guard_matches(
            old_guard, scene_id="offline-scene", bundle_version=2, now=1,
            events_through=0, values_through=0, action="open_side_passage",
            opportunity_id="open_side_passage"))

    def test_s3_player_intervention_and_s4_negative_are_predeclared(self):
        suite = _raw("suite.json")
        s3 = next(row for row in suite["cases"] if row["case_id"].startswith("S3-"))
        self.assertEqual([(row["at"], row["operation"], row["item_alias"])
                          for row in s3["interventions"]],
                         [(2, "get", "courier_supply"), (6, "drop", "courier_supply")])
        s4 = load_bundle(_raw("bundle-no-opportunities-v1.json"))
        self.assertEqual(tuple(s4.permissions["world_opportunities"]), ())
        self.assertEqual(s4.permissions["cost_budget"], 0)
        self.assertTrue(suite["cases"][3]["expected"]["must_not_claim_world_unreachable"])

    def test_source_manifest_is_complete_and_prefix_audit_is_order_sensitive(self):
        manifest = _source_manifest()
        self.assertEqual(set(manifest["working_tree_source_sha256"]), set(SOURCE_PATHS))
        self.assertFalse([path for path, digest in manifest["working_tree_source_sha256"].items()
                          if digest == "MISSING"])
        self.assertTrue(_ordered_prefix([{"event": 1}], [{"event": 1}, {"event": 2}]))
        self.assertFalse(_ordered_prefix([{"event": 1}], [{"event": 2}, {"event": 1}]))

    @unittest.skipUnless(importlib.util.find_spec("gtpyhop"), "requires project GTPyhop runtime")
    def test_real_s4_blocked_proposal_with_diagnostic_payload_never_dispatches(self):
        from tools.native_platform_v0.p5.mature_methods.method_adapters import snapshot_from_native
        from tools.native_platform_v0.p5.mature_methods.narrative_methods import plan_high_level
        from tools.native_platform_v0.p5.tests.test_mature_methods import native_evidence

        bundle = load_bundle(_raw("bundle-no-opportunities-v1.json"))
        state = _initial_state(bundle)
        state["physical_budget"] = 0
        state["horizon"] = 24
        for route in state["routes"]:
            route["available"] = False
        evidence = native_evidence(bundle, state_override=state)
        evidence["horizon"] = 24
        snapshot = snapshot_from_native(bundle, evidence)
        decision = plan_high_level(bundle, snapshot)
        self.assertEqual(decision["method_trace"][0]["method_id"], "blocked")
        self.assertEqual(decision["control_proposal_status"], "BLOCKED")
        self.assertEqual(decision["control_proposal"]["selected_action"], "NO_OP")
        self.assertIsNotNone(decision["method_trace"][0]["candidate"])
        self.assertIsNone(decision["control_proposal"]["candidate_guard"])
        self.assertEqual(_candidate_and_guard(decision, snapshot), (None, None))

    @unittest.skipUnless(importlib.util.find_spec("gtpyhop"), "requires project GTPyhop runtime")
    def test_real_settled_noop_proposal_with_no_candidate_is_not_malformed(self):
        from tools.native_platform_v0.p5.mature_methods.method_adapters import snapshot_from_native
        from tools.native_platform_v0.p5.mature_methods.narrative_methods import plan_high_level
        from tools.native_platform_v0.p5.tests.test_mature_methods import native_evidence

        bundle = load_bundle(_raw("bundle-result-only-v1.json"))
        state = _initial_state(bundle)
        state["horizon"] = 24
        evidence = native_evidence(bundle, state_override=state)
        evidence["horizon"] = 24
        events = []
        for goal in bundle.goals:
            evidence["verdicts"]["constraints"] = [
                {**row, "status": "SATISFIED"}
                for row in evidence["verdicts"]["constraints"]]
            evidence["planning_view"]["state"]["verdicts"] = [
                {"constraint_id": row["constraint_id"], "status": "SATISFIED"}
                for row in evidence["verdicts"]["constraints"]]
            constraint = goal.constraint
            event_type = getattr(constraint, "event_type", getattr(constraint, "after_type", None))
            filters = dict(getattr(constraint, "event_filter", None) or
                           getattr(constraint, "after_filter", None) or {})
            args = {}
            for key, value in filters.items():
                args[key] = value.stable_id if hasattr(value, "stable_id") else value
            events.append({"event_id": f"witness-{goal.constraint_id}",
                           "event_type": event_type, "provenance": "committed_ledger",
                           "args": args})
        evidence["typed_trace"]["events"] = events
        snapshot = snapshot_from_native(bundle, evidence)
        decision = plan_high_level(bundle, snapshot)
        self.assertEqual(decision["method_trace"][0]["method_id"], "existing_path")
        self.assertEqual(decision["control_proposal_status"], "PROPOSAL_AVAILABLE")
        self.assertEqual(decision["control_proposal"]["selected_action"], "NO_OP")
        self.assertIsNone(decision["method_trace"][0]["candidate"])
        self.assertIsNone(decision["control_proposal"]["candidate"])
        self.assertEqual(_candidate_and_guard(decision, snapshot), (None, None))


if __name__ == "__main__":
    unittest.main()
