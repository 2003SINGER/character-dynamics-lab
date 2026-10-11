"""Independent contracts for the bounded System Baseline v0 Sabre/P5 seam."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.native_platform_v0.p5.monitor import evaluate_bundle
from tools.native_platform_v0.p5 import service as p5_service
from tools.system_baseline_v0.model import (
    Candidate, NO_OP, project_p5_for_sabre, validate_candidate_guard,
)
from tools.system_baseline_v0.sabre import (
    candidate_from_result, invoke_sabre, render_problem,
)
from tools.system_baseline_v0 import sabre as sabre_backend
from tools.trajectory_constraints_v0.trace import Event, Trace


SOURCE = "native_platform_v0.p5.service._evidence"


def raw_bundle(*, route="main_passage", value=True, deadline=8, start=0,
               allowed=None, cost_budget=2, version=1, extra_constraints=()):
    constraints = [{"id": f"{route}-target", "kind": "state_by_deadline",
                    "observable": "route_open", "args": {"route": route},
                    "value": value, "start": start, "deadline": deadline, "hard": True}]
    constraints.extend(extra_constraints)
    return {"schema": "native-author-bundle-v1", "bundle_id": "system-baseline-contract",
            "version": version, "source": "independent-contract-test",
            "constraints": constraints, "branches": [],
            "permissions": {"world_opportunities": list(allowed or [
                "open_main_passage", "open_side_passage"]),
                "force_npc_response": False, "max_opportunities": 1,
                "cost_budget": cost_budget}}


def trace(*, minute=0, main_open=False, side_open=False, events=None, values=None,
          prefix_status="SEALED_COMPLETE", evidence_schema="p5-live-trace-v1",
          source=SOURCE, bundle_version=1):
    events = minute if events is None else events
    values = minute if values is None else values
    return {"scene_id": "p5-scene-contract", "source": source,
            "evidence_schema": evidence_schema, "prefix_status": prefix_status,
            "bundle_identity": {"bundle_id": "system-baseline-contract", "version": bundle_version},
            "now": minute, "horizon": 24,
            "complete_through": {"events": events, "values": values},
            "world_snapshots": [{"minute": values,
                                 "routes": {"main_passage": main_open,
                                            "side_passage": side_open}}],
            "ledger": [], "verdicts": {"constraints": [
                {"constraint_id": "main_passage-target", "status": "PENDING"},
                {"constraint_id": "side_passage-target", "status": "PENDING"},
                {"constraint_id": "delivery", "status": "PENDING"},
                {"constraint_id": "note-response", "status": "PENDING"},
            ]}}


class ProjectionAndFreshnessContracts(unittest.TestCase):
    def test_projection_requires_matching_scene_versioned_complete_prefix(self):
        raw = raw_bundle()
        good = project_p5_for_sabre(trace(), raw, "p5-scene-contract")
        self.assertEqual(good.bundle_version, 1)
        self.assertEqual(good.events_through, good.values_through)
        for bad in (
            trace(source="forged-or-wrong-source"),
            trace(evidence_schema="unknown-schema"),
            trace(prefix_status="INCOMPLETE"),
            trace(bundle_version=2),
            trace(events=0, values=-1),
            trace(events=0, values=0, minute=1),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises((ValueError, TypeError)):
                    project_p5_for_sabre(bad, raw, "p5-scene-contract")

    def test_candidate_stales_on_scene_bundle_minute_or_either_frontier(self):
        candidate = Candidate(
            "open_main_passage", "open_main_passage", "p5-scene-contract",
            "system-baseline-contract", 1, 0, 0, 0, "problem", "plan",
            "PLAN_FOUND_NOT_EXECUTION_EVIDENCE", (),
        )
        valid = dict(scene_id="p5-scene-contract", bundle_id="system-baseline-contract",
                     bundle_version=1, now=1, events_through=0, values_through=0,
                     action="open_main_passage", opportunity_id="open_main_passage")
        self.assertTrue(validate_candidate_guard(candidate, **valid))
        for field, replacement in (("scene_id", "other-scene"),
                                   ("bundle_id", "other-bundle"),
                                   ("bundle_version", 2), ("now", 2),
                                   ("events_through", 1), ("values_through", 1),
                                   ("action", "open_side_passage"),
                                   ("opportunity_id", "open_side_passage")):
            bad = dict(valid)
            bad[field] = replacement
            with self.subTest(field=field):
                self.assertFalse(validate_candidate_guard(candidate, **bad))

    def test_sabre_view_does_not_call_or_wrap_p5_finite_planner(self):
        view = project_p5_for_sabre(trace(), raw_bundle(), "p5-scene-contract")
        problem = render_problem(view)
        self.assertIn("action open_route(route : route)", problem)
        self.assertIn("selected(route)", problem)
        self.assertNotIn("note_response", problem)
        self.assertNotIn("selected_action", problem)
        self.assertNotIn("supported_hard_constraints", problem)

    def test_social_response_is_residual_and_never_a_sabre_world_action(self):
        note = {"id": "note-response", "kind": "event_by_deadline",
                "event": "note_response",
                "filters": {"actor": "A", "recipient": "B", "item": "note",
                            "response": "rejected"},
                "start": 0, "deadline": 8, "hard": True}
        raw = raw_bundle(extra_constraints=(note,))
        view = project_p5_for_sabre(trace(), raw, "p5-scene-contract")
        problem = render_problem(view)
        self.assertTrue(any(cid == "note-response" and "RESIDUAL" in reason
                            for cid, reason in view.projection_obligations))
        self.assertIn("note-response", view.hard_unresolved)
        self.assertNotIn("note_response", problem)
        self.assertFalse(load_bundle(raw).permissions["force_npc_response"])

    def test_native_receipt_monitor_does_not_accept_a_planner_prediction(self):
        note = {"id": "note-response", "kind": "event_by_deadline",
                "event": "note_response",
                "filters": {"actor": "A", "recipient": "B", "item": "note",
                            "response": "rejected"},
                "start": 0, "deadline": 8, "hard": True}
        raw = raw_bundle(extra_constraints=(note,))
        raw["branches"] = [{"id": "reject", "when": {"event": "note_response", "response": "rejected"},
                             "storylet": {"id": "reject-text", "text": "Rejected."}}]
        bundle = load_bundle(raw)
        trace_without_receipt = Trace(now=0)
        trace_without_receipt.finalize_events()
        monitored = evaluate_bundle(bundle, trace_without_receipt)
        self.assertNotEqual(monitored["hard_status"], "SATISFIED")
        self.assertNotEqual(monitored["branches"][0]["status"], "ELIGIBLE")

        proposal = Trace(now=0)
        from tools.trajectory_constraints_v0.types import StableEntity
        proposal.add_event(Event("proposal-only", "p5_note_response", 0, 1,
                                 {"actor": StableEntity("Actor", "A"),
                                  "recipient": StableEntity("Actor", "B"),
                                  "item": StableEntity("Item", "note"),
                                  "response": "rejected"},
                                 provenance="delivered_observation"))
        with self.assertRaises(ValueError):
            evaluate_bundle(bundle, proposal)

    def test_hard_nonroute_goal_stays_explicit_residual_not_sat(self):
        delivery = {"id": "delivery", "kind": "event_by_deadline",
                    "event": "delivery_settled",
                    "filters": {"actor": "A", "item": "courier_supply"},
                    "start": 0, "deadline": 12, "hard": True}
        raw = raw_bundle(extra_constraints=(delivery,))
        view = project_p5_for_sabre(trace(), raw, "p5-scene-contract")
        self.assertTrue(any(cid == "delivery" and "RESIDUAL" in reason
                            for cid, reason in view.projection_obligations))
        candidate = candidate_from_result(view, render_problem(view), {
            "selected_action": "open_main_passage",
            "status": "PLAN_FOUND_NOT_EXECUTION_EVIDENCE",
        })
        self.assertNotEqual(candidate.search_status, "SATISFIED")
        self.assertNotEqual(candidate.search_status, "COMPLETE")

    def test_unsupported_route_polarity_and_unreachable_window_remain_hard_residuals(self):
        must_close = project_p5_for_sabre(
            trace(main_open=True), raw_bundle(route="main_passage", value=False),
            "p5-scene-contract")
        self.assertIn("main_passage-target", must_close.hard_unresolved)
        self.assertTrue(any(cid == "main_passage-target" and "RESIDUAL" in reason
                            for cid, reason in must_close.projection_obligations))

        deadline_now = project_p5_for_sabre(
            trace(), raw_bundle(route="main_passage", deadline=0), "p5-scene-contract")
        self.assertIn("main_passage-target", deadline_now.hard_unresolved)
        self.assertTrue(any(cid == "main_passage-target" and "RESIDUAL" in reason
                            for cid, reason in deadline_now.projection_obligations))


class SabreSelectionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CI builds the same pinned upstream source into the ignored local-data
        # path; this override keeps the test pointed at that exact build.
        java = os.environ.get("SYSTEM_BASELINE_SABRE_JAVA")
        classpath = os.environ.get("SYSTEM_BASELINE_SABRE_CLASSPATH")
        if java and classpath:
            sabre_backend.JAVA = Path(java)
            sabre_backend.CLASSPATH = Path(classpath)

    def _run(self, raw):
        view = project_p5_for_sabre(trace(), raw, "p5-scene-contract")
        problem = render_problem(view)
        with tempfile.TemporaryDirectory(prefix="system-baseline-sabre-") as temp:
            path = Path(temp) / "problem.txt"
            path.write_text(problem, encoding="utf-8")
            result = invoke_sabre(path)
        candidate = candidate_from_result(view, problem, result)
        return view, problem, result, candidate

    def test_real_sabre_selection_changes_with_author_route_target(self):
        _, _, main, main_candidate = self._run(raw_bundle(route="main_passage"))
        _, _, side, side_candidate = self._run(raw_bundle(route="side_passage"))
        self.assertEqual(main["status"], "PLAN_FOUND_NOT_EXECUTION_EVIDENCE", main)
        self.assertEqual(side["status"], "PLAN_FOUND_NOT_EXECUTION_EVIDENCE", side)
        self.assertEqual(main["selected_action"], "open_main_passage", main)
        self.assertEqual(side["selected_action"], "open_side_passage", side)
        self.assertNotEqual(main_candidate.selected_action, side_candidate.selected_action)
        self.assertNotEqual(main_candidate.problem_sha256, side_candidate.problem_sha256)

    def test_sabre_cannot_emit_unpermitted_or_overbudget_route_action(self):
        _, _, permission_result, permission_candidate = self._run(
            raw_bundle(route="side_passage", allowed=["open_main_passage"]))
        self.assertNotEqual(permission_result.get("selected_action"), "open_side_passage")
        self.assertNotEqual(permission_candidate.selected_action, "open_side_passage")
        _, _, budget_result, budget_candidate = self._run(
            raw_bundle(route="side_passage", cost_budget=0))
        self.assertNotEqual(budget_result.get("selected_action"), "open_side_passage")
        self.assertNotEqual(budget_candidate.selected_action, "open_side_passage")


class NativeDispatchGuardContracts(unittest.TestCase):
    def _guard(self, action="open_main_passage"):
        return {"scene_id": "p5-scene-contract", "bundle_version": 1,
                "based_on_minute": 0, "events_through": 0, "values_through": 0,
                "selected_action": action, "opportunity_id": action}

    def test_p5_native_guard_rejects_old_plan_after_same_minute_author_edit(self):
        guard = self._guard()
        # The minute-1 edit is processed before the candidate intervention.
        # Even with unchanged world frontiers, active version 2 invalidates v1.
        self.assertFalse(p5_service._candidate_guard_matches(
            guard, scene_id="p5-scene-contract", bundle_version=2, now=1,
            events_through=0, values_through=0, action="open_main_passage",
            opportunity_id="open_main_passage"))

    def test_p5_native_guard_rejects_frontier_or_action_substitution(self):
        guard = self._guard()
        common = dict(scene_id="p5-scene-contract", bundle_version=1, now=1,
                      events_through=0, values_through=0,
                      action="open_main_passage", opportunity_id="open_main_passage")
        self.assertTrue(p5_service._candidate_guard_matches(guard, **common))
        self.assertFalse(p5_service._candidate_guard_matches(
            guard, **(common | {"action": "open_side_passage",
                                "opportunity_id": "open_side_passage"})))
        self.assertFalse(p5_service._candidate_guard_matches(
            guard, **(common | {"events_through": 1})))
        self.assertFalse(p5_service._candidate_guard_matches(
            guard, **(common | {"values_through": 1})))

    def test_action_and_opportunity_id_must_match_candidate_identity(self):
        guard = self._guard()
        common = dict(scene_id="p5-scene-contract", bundle_version=1, now=1,
                      events_through=0, values_through=0,
                      action="open_side_passage", opportunity_id="open_side_passage")
        self.assertFalse(p5_service._candidate_guard_matches(guard, **common))

    def test_native_service_records_edit_stale_candidate_without_world_dispatch(self):
        from twisted.internet import defer

        class Attributes:
            def get(self, key, category=None, default=None):
                return {"p4_clock": {"now": 1},
                        "p5_event_coverage_minute": 0,
                        "p5_snapshot_coverage_minute": 0,
                        "scenario_seed": 42}.get(key, default)

        pickup = SimpleNamespace(attributes=Attributes())
        row = {"at": 1, "kind": "author_opportunity", "operation": "open_passage",
               "opportunity_id": "open_main_passage", "candidate_guard": self._guard()}
        events = []
        with patch("tools.native_platform_v0.p5.service._scene_objects",
                   return_value=(pickup, [])), \
             patch("tools.native_platform_v0.p3.p4_world.append_event",
                   side_effect=lambda scene, event: events.append((scene, event))), \
             patch("tools.native_platform_v0.p5.service.world.activate_opportunity") as activate:
            pending = p5_service._apply_intervention(
                "p5-scene-contract", row, SimpleNamespace(version=2))
            self.assertIsInstance(pending, defer.Deferred)
            self.assertTrue(pending.called)
            outcome = pending.result

        self.assertEqual(outcome["status"], "STALE_CANDIDATE")
        self.assertFalse(outcome["settled"])
        activate.assert_not_called()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "p5-scene-contract")
        event = events[0][1]
        self.assertEqual(event["event_type"], "P5_INTERVENTION")
        self.assertEqual(event["typed_args"]["kind"], "stale_planner_candidate")
        self.assertEqual(event["typed_args"]["settlement"]["status"], "STALE_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
