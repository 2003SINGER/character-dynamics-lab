from __future__ import annotations

import unittest
from dataclasses import replace

from tools.author_obligation_planning_v0.contracts import (
    EvidenceEvent, Eventually, InOrder, MaxCount, Never, TaskSpecError,
    task_spec_from_dict,
)
from tools.author_obligation_planning_v0.search import (
    SearchLimits, compile_history_progress, plan_task,
)
from tools.author_obligation_planning_v0.tasks import (
    ALL_TASK_IDS, DYNAMIC_CASES, STATIC_TASKS, revise_after, serialize_task,
    task_by_id,
)
from tools.author_obligation_planning_v0.verify import inspect_rows


class TaskCatalogContracts(unittest.TestCase):
    def test_catalog_has_28_static_and_4_dynamic_candidates(self):
        self.assertEqual(len(STATIC_TASKS), 28)
        self.assertEqual(len(DYNAMIC_CASES), 4)
        self.assertEqual(len(ALL_TASK_IDS), 32)
        self.assertEqual(len(set(ALL_TASK_IDS)), 32)
        self.assertTrue(all(task.always_no_death for task in STATIC_TASKS))
        self.assertTrue(all(case.task.always_no_death for case in DYNAMIC_CASES))
        h4 = task_by_id("H4")
        self.assertTrue(h4.requires_native_feedback)
        self.assertEqual(h4.task.goal, task_by_id("A2").goal)
        self.assertEqual(h4.task.obligations, (Eventually("create_bridge"),))
        self.assertIn("true-execution rejection and feedback", h4.task.text)

    def test_goal_equivalence_does_not_merge_different_histories(self):
        a2, b2, f2 = (task_by_id(name) for name in ("A2", "B2", "F2"))
        self.assertEqual(a2.goal, b2.goal)
        self.assertEqual(a2.goal, f2.goal)
        self.assertEqual(a2.obligations, ())
        self.assertEqual(b2.obligations, (Eventually("create_bridge"),))
        self.assertEqual(f2.obligations, (Never("create_bridge"),))
        # A3's bridge state is unrestricted and it does not inherit A1/A2 history.
        a3 = task_by_id("A3")
        self.assertNotIn(("bridge",), a3.goal.required)
        self.assertNotIn(("unbridged",), a3.goal.required)
        self.assertEqual(a3.obligations, ())

    def test_repeated_bridge_obligations_are_explicit(self):
        for case_id in ("E1", "E2", "E3"):
            with self.subTest(case_id=case_id):
                self.assertEqual(task_by_id(case_id).obligations,
                                 (InOrder(("create_bridge", "destroy_bridge")),))
        self.assertEqual(task_by_id("G10").obligations,
                         (MaxCount("create_bridge", 1),))
        self.assertEqual(task_by_id("C2").obligations,
                         (InOrder(("arrive_west", "return_east")),))

    def test_every_candidate_round_trips_through_strict_json_schema(self):
        all_specs = list(STATIC_TASKS) + [case.task for case in DYNAMIC_CASES]
        for spec in all_specs:
            with self.subTest(task=spec.id):
                self.assertEqual(task_spec_from_dict(serialize_task(spec)), spec)

    def test_unsupported_or_empty_task_payloads_are_rejected(self):
        valid = serialize_task(task_by_id("A1"))
        with self.assertRaises(TaskSpecError):
            task_spec_from_dict({**valid, "surprise": True})
        unknown = serialize_task(task_by_id("A1"))
        unknown["obligations"] = [{"type": "eventually", "event": "invented_event"}]
        with self.assertRaises(TaskSpecError):
            task_spec_from_dict(unknown)
        empty = {"id": "empty", "version": "1", "text": "empty", "goal": {
            "required": [], "forbidden": []}, "obligations": [], "always_no_death": False}
        with self.assertRaises(TaskSpecError):
            task_spec_from_dict(empty)

    def test_author_edits_create_new_versions_and_leave_original_task_intact(self):
        h1, h2, h3 = (task_by_id(name).task for name in ("H1", "H2", "H3"))
        prior_author_rule = Never("create_bridge")
        h1_with_rule = replace(h1, obligations=(prior_author_rule,))
        h2_with_rule = replace(h2, obligations=(prior_author_rule,))
        h3_with_rule = replace(h3, obligations=(prior_author_rule,))
        h1_v2 = revise_after(h1_with_rule, "after_successful_take_rod")
        h2_v2 = revise_after(h2_with_rule, "after_first_arrive_east")
        h3_v2 = revise_after(h3_with_rule, "immediately_before_build")
        self.assertEqual((h1.id, h1.version), ("H1", "1"))
        self.assertEqual((h1_v2.id, h1_v2.version), ("H1", "2"))
        self.assertEqual(h1_v2.goal, task_by_id("A1").goal)
        self.assertEqual(h1_v2.obligations, (prior_author_rule,))
        self.assertEqual((h2.id, h2.version), ("H2", "1"))
        self.assertEqual(h2_v2.obligations,
                         (prior_author_rule, InOrder(("arrive_west", "return_east"))))
        self.assertEqual((h3.id, h3.version), ("H3", "1"))
        self.assertEqual(h3_v2.obligations, (prior_author_rule, Never("create_bridge")))
        for revision in (h1_v2, h2_v2, h3_v2):
            self.assertTrue(revision.always_no_death)
            self.assertTrue(revision.id.startswith("H"))  # author source keeps its stable task identity
        self.assertEqual(h1.obligations, ())
        self.assertEqual(h2.obligations, ())
        self.assertEqual(h3.obligations, ())
        with self.assertRaises(ValueError):
            revise_after(h1, "wrong-trigger")

    def test_author_revision_recompiles_and_preserves_prior_native_history(self):
        h3 = task_by_id("H3").task
        revision = revise_after(h3, "immediately_before_build")
        prior = (EvidenceEvent("create_bridge", "native-step-4", 4),)
        progress = compile_history_progress(revision, prior)
        self.assertIn("never:create_bridge", progress.violations)
        self.assertEqual(progress.history_source_ids, ("native-step-4",))
        self.assertEqual(progress.history_events_used, 1)

    def test_one_native_receipt_cannot_advance_two_positions_in_a_strict_order(self):
        task = task_by_id("E1")
        same_receipt = (
            EvidenceEvent("create_bridge", "native-step-12", 12),
            EvidenceEvent("destroy_bridge", "native-step-12", 12),
        )
        progress = compile_history_progress(task, same_receipt)
        self.assertEqual(progress.ordered_cursors, (1,))
        self.assertFalse(progress.complete)


class PlanningAndEvidenceContracts(unittest.TestCase):
    @staticmethod
    def _near_f2_state():
        # All final facts except bridge are already true. The sole bridge
        # creation route violates F2's whole-plan Never(create_bridge).
        return frozenset({
            ("at", "player", "EASTBANK"),
            ("at", "keys", "CARRIED"), ("carrying", "keys"),
            ("at", "lamp", "CARRIED"), ("carrying", "lamp"),
            ("at", "rod", "EASTBANK"), ("lamp_on",), ("unbridged",),
        })

    def test_f2_finite_exhaustion_is_distinct_from_search_budget(self):
        f2 = task_by_id("F2")
        initial = self._near_f2_state()
        finite = plan_task(initial, f2, limits=SearchLimits(max_expansions=5000, max_seconds=10))
        budget = plan_task(initial, f2, limits=SearchLimits(max_expansions=0, max_seconds=10))
        self.assertEqual(finite.status, "EXHAUSTED_FINITE_MODEL")
        self.assertEqual(budget.status, "BUDGET")

    def test_unknown_native_evidence_cannot_verify_no_death_or_final_state(self):
        a1 = serialize_task(task_by_id("A1"))
        report = inspect_rows([], a1)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["obligations"]["always:no_death"], "UNKNOWN")
        self.assertNotIn("PASS", report["obligations"].values())


if __name__ == "__main__":
    unittest.main()
