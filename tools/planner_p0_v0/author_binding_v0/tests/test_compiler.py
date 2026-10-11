from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.planner_p0_v0.author_binding_v0.compiler import (
    PINNED_RUNS, AuthorBinding, AuthorClause, assert_plan_binding_current,
    _validate_snapshot, compile_binding, evaluate_binding, load_pinned_native_trace,
    p0_author_binding, classify_candidate_result, plan_binding_metadata,
)


ROOT = Path(__file__).resolve().parents[4]


def p0_inputs():
    evidence = load_pinned_native_trace(ROOT, "direct-clean-A")
    return evidence["initial_snapshot"], evidence["scene_identity"]


class AuthorBindingTests(unittest.TestCase):
    def test_shared_binding_emits_atomic_goal_and_typedir_constraints(self):
        result = compile_binding(fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "COMPILED")
        self.assertEqual(len(result.constraints), 5)
        self.assertEqual(result.compile_record.binding.source_text, p0_author_binding().source_text)
        self.assertEqual(result.compile_record.fixture_id, "direct-clean-A")
        self.assertTrue(result.compile_record.fixture_sha256)
        self.assertIn(("actor:A", 4111), result.compile_record.role_to_entity_ids)
        self.assertTrue(all("Sabre:" in row and "TypedIR:" in row
                            for _, row in result.projection_map))
        self.assertEqual([type(x).__name__ for x in result.constraints],
                         ["EventCount", "EventCount", "EventCount", "EventOrder", "EventOrder"])
        self.assertIn("utility(): if(delivery_count() == 1 & storm_observation_count(B) == 1 & meeting_count() == 1)", result.sabre_problem)
        self.assertIn("storm_observation_count(actor) = storm_observation_count(actor) + 1", result.sabre_problem)
        self.assertIn("delivery_count() = delivery_count() + 1", result.sabre_problem)
        self.assertIn("meeting_count() = meeting_count() + 1", result.sabre_problem)
        self.assertIn("delivery_count() == 1 & delivery_time() < now()", result.sabre_problem)
        self.assertIn("storm_observation_count(B) == 1 & observation_time(B) < now()", result.sabre_problem)
        self.assertEqual(len(result.derived_subgoals), 3)

    def test_absolute_deadline_reaches_planner_guards_and_typedir_window(self):
        binding = replace(p0_author_binding(8))
        result = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "COMPILED")
        self.assertIn("now() <= 8 & now() < 24;", result.sabre_problem)
        self.assertIn("now() <= 22 & now() <= 8;", result.sabre_problem)
        self.assertTrue(all(c.window.end == 8 for c in result.constraints))
        self.assertIn("delivery_time() < now()", result.sabre_problem)

    def test_delivery_only_does_not_strengthen_author_goal_to_weather_or_meeting(self):
        binding = AuthorBinding("delivery-only", p0_author_binding().version,
                                "A delivers the kit", 12,
                                (AuthorClause("delivery", "event_once", event="p0_delivery", actor="A"),))
        result = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "COMPILED")
        self.assertIn("utility(): if(delivery_count() == 1) 1 else 0;", result.sabre_problem)
        self.assertNotIn("utility(): if(delivery_count() == 1 & storm_observation_count(B)", result.sabre_problem)

    def test_unbound_roles_unauthorized_mode_and_unregistered_ability_reject(self):
        snapshot, scene = p0_inputs()
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_INPUT"):
            compile_binding()
        with self.assertRaisesRegex(PermissionError, "UNAUTHORIZED_BINDING"):
            _validate_snapshot({**snapshot, "mode": "free"}, scene, p0_author_binding(),
                               ("look", "dispatch_task", "meet"))
        with self.assertRaisesRegex(PermissionError, "UNREGISTERED_ABILITY"):
            _validate_snapshot(snapshot, scene, p0_author_binding(), ("teleport",))

    def test_unsupported_hard_clause_stays_residual_and_blocks_sat_projection(self):
        binding = replace(p0_author_binding(), clauses=p0_author_binding().clauses +
                          (AuthorClause("relationship", "relationship_drop", hard=True),))
        result = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "PARTIAL_UNRESOLVED")
        self.assertIsNone(result.sabre_problem)
        self.assertIn("relationship: unsupported hard clause", result.hard_residual_obligations[0])

    def test_unregistered_order_direction_is_residual_and_order_only_is_not_goal(self):
        unsupported = AuthorBinding("reverse-order", p0_author_binding().version, "meeting before delivery", 24,
                                    (AuthorClause("reverse", "before", before="p0_meeting_witness",
                                                  after="p0_delivery"),))
        result = compile_binding(unsupported, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "PARTIAL_UNRESOLVED")
        self.assertIsNone(result.sabre_problem)
        order_only = AuthorBinding("order-only", p0_author_binding().version, "delivery before meeting", 24,
                                   (AuthorClause("order", "before", before="p0_delivery",
                                                 after="p0_meeting_witness"),))
        result = compile_binding(order_only, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "PARTIAL_UNRESOLVED")
        self.assertIsNone(result.sabre_problem)
        self.assertIn("no supported hard planner goal", result.hard_residual_obligations)

    def test_soft_unscored_clause_is_separate_and_does_not_block_hard_projection(self):
        binding = replace(p0_author_binding(), clauses=p0_author_binding().clauses +
                          (AuthorClause("pleasant-tone", "semantic_quality", hard=False),))
        result = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "COMPILED_WITH_SOFT_RESIDUAL")
        self.assertIsNotNone(result.sabre_problem)
        self.assertFalse(result.hard_residual_obligations)
        self.assertEqual(len(result.soft_unscored_obligations), 1)

    def test_plan_dispatch_requires_exact_current_binding_version(self):
        active = p0_author_binding()
        compilation = compile_binding(active, fixture_id="direct-clean-A", repo_root=ROOT)
        token = plan_binding_metadata(compilation)
        assert_plan_binding_current(token, active, compilation)
        with self.assertRaisesRegex(ValueError, "STALE_BINDING_VERSION"):
            assert_plan_binding_current({**token, "binding_version": "old"}, active, compilation)
        with self.assertRaisesRegex(ValueError, "UNBOUND_PLAN"):
            assert_plan_binding_current({}, active, compilation)
        changed = replace(active, deadline_minute=8)
        old = compile_binding(active, fixture_id="direct-clean-A", repo_root=ROOT)
        with self.assertRaisesRegex(ValueError, "STALE_BINDING_CONTENT"):
            assert_plan_binding_current({**plan_binding_metadata(old),
                                         "binding_version": changed.version}, changed, old)
        other_scene = compile_binding(active, fixture_id="route-repair-A", repo_root=ROOT)
        with self.assertRaisesRegex(ValueError, "STALE_SCENE_BINDING"):
            assert_plan_binding_current(plan_binding_metadata(other_scene), active, old)

    def test_budget_no_plan_and_unbound_are_distinct(self):
        partial = compile_binding(replace(p0_author_binding(), clauses=(
            AuthorClause("unknown", "unknown-hard-kind"),)),
            fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(classify_candidate_result({"status": "SUCCESS"}, partial),
                         "UNBOUND_OR_RESIDUAL")
        complete = compile_binding(fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(classify_candidate_result({"status": "BUDGET_LIMIT"}, complete),
                         "SEARCH_BUDGET")
        self.assertEqual(classify_candidate_result({"status": "NATIVE_NO_SOLUTION"}, complete),
                         "NO_PLAN_IN_EXPORTED_DOMAIN")

    def test_malformed_binding_fields_stay_residual_or_reject(self):
        snapshot, scene = p0_inputs()
        bad = replace(p0_author_binding(), clauses=(AuthorClause(
            "bad", "event_once", event="p0_delivery", before="p0_meeting_witness"),))
        result = compile_binding(bad, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(result.status, "PARTIAL_UNRESOLVED")
        duplicate = replace(p0_author_binding(), clauses=(
            AuthorClause("duplicate", "event_once", event="p0_delivery"),
            AuthorClause("duplicate", "event_once", event="p0_meeting_witness")))
        with self.assertRaisesRegex(ValueError, "clause IDs"):
            _validate_snapshot(snapshot, scene, duplicate, ("look", "dispatch_task", "meet"))

    def test_clause_ids_do_not_select_semantics(self):
        base = p0_author_binding()
        renamed = replace(base, clauses=tuple(
            replace(c, clause_id=f"renamed-{i}") for i, c in enumerate(base.clauses)))
        a = compile_binding(base, fixture_id="direct-clean-A", repo_root=ROOT)
        b = compile_binding(renamed, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertIn("delivery_count() == 1 & delivery_time() < now()", a.sabre_problem)
        self.assertIn("delivery_count() == 1 & delivery_time() < now()", b.sabre_problem)
        self.assertEqual([type(c) for c in a.constraints], [type(c) for c in b.constraints])


class PinnedNativeEvidenceTests(unittest.TestCase):
    def test_all_six_committed_raw_runs_are_hash_pinned_and_typedir_passes(self):
        for fixture_id in PINNED_RUNS:
            with self.subTest(fixture_id=fixture_id):
                evidence = load_pinned_native_trace(ROOT, fixture_id)
                self.assertIn("producer identity not authenticated", evidence["trust_scope"])
                binding = p0_author_binding()
                compilation = compile_binding(binding, fixture_id=fixture_id, repo_root=ROOT)
                report = evaluate_binding(binding, compilation, repo_root=ROOT, fixture_id=fixture_id)
                self.assertEqual(report["status"], "SATISFIED")
                self.assertTrue(report["complete_ledger_prefix"])
                self.assertEqual(len(report["constraints"]), 5)

    def test_arbitrary_receipt_shaped_mapping_is_not_an_evidence_api(self):
        # There is intentionally no public trusted=True/mapping receipt path.
        with self.assertRaisesRegex(ValueError, "UNKNOWN_FIXTURE"):
            load_pinned_native_trace(ROOT, "caller-supplied-native")
        binding = p0_author_binding()
        compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        self.assertEqual(evaluate_binding(binding, compilation, repo_root=ROOT)["status"], "INDETERMINATE")

    def test_modified_pinned_file_bytes_are_rejected(self):
        original = Path.read_bytes

        def altered(path):
            payload = original(path)
            if path.name == "run.json" and "p0bg-direct-clean-A-" in str(path):
                return payload + b" "
            return payload

        with patch.object(Path, "read_bytes", altered):
            with self.assertRaisesRegex(ValueError, "FIXTURE_DIGEST_MISMATCH"):
                load_pinned_native_trace(ROOT, "direct-clean-A")

    def test_hard_residual_blocks_all_satisfied_claim_even_on_full_receipts(self):
        base = p0_author_binding()
        binding = replace(base, clauses=base.clauses +
                          (AuthorClause("unknown", "relationship_drop", hard=True),))
        compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=ROOT)
        report = evaluate_binding(binding, compilation, repo_root=ROOT, fixture_id="direct-clean-A")
        self.assertEqual(report["status"], "INDETERMINATE")
        self.assertTrue(report["hard_residual_obligations"])

    def test_evaluator_rejects_compilation_under_changed_same_version_content(self):
        original = p0_author_binding()
        compiled = compile_binding(original, fixture_id="direct-clean-A", repo_root=ROOT)
        changed = replace(original, deadline_minute=8)
        with self.assertRaisesRegex(ValueError, "STALE_COMPILATION"):
            evaluate_binding(changed, compiled, repo_root=ROOT, fixture_id="direct-clean-A")


if __name__ == "__main__":
    unittest.main()
