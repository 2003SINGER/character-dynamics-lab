from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.mature_methods_integration_v1.story_runner import (
    _assess_case, _at_path, _matching_actions, _patch_request, _replace_scene_token,
    _expected_continuation_request, _story_envelope, _validate_active_db_prefix, run_case,
)


ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "story_cases/suite.json").read_text(encoding="utf-8"))
BUNDLE = json.loads((ROOT / "story_cases/story-bundle-v1.json").read_text(encoding="utf-8"))


class StoryCaseMatrixContractTests(unittest.TestCase):
    def test_matrix_is_finite_and_limits_first_release(self):
        rows = SUITE["cases"]
        self.assertEqual(len(rows), 14)
        self.assertEqual(SUITE["run_policy"]["max_scenes"], 13)
        self.assertEqual(SUITE["run_policy"]["max_cases_including_precreate_rejection"], 14)
        self.assertEqual(SUITE["run_policy"]["first_scene_release"], "accepted-gtpyhop")
        self.assertEqual(SUITE["run_policy"]["prior_s1_s4_runs"], "DO_NOT_RERUN")
        self.assertEqual(len({row["case_id"] for row in rows}), len(rows))

    def test_two_positive_and_rejection_pairs_hold_conditions_constant(self):
        by_id = {row["case_id"]: row for row in SUITE["cases"]}
        for left_id, right_id in (("accepted-gtpyhop", "accepted-event-driven"),
                                  ("rejected-gtpyhop", "rejected-event-driven"),
                                  ("task-refusal-gtpyhop", "task-refusal-event-driven")):
            left, right = by_id[left_id], by_id[right_id]
            self.assertEqual(left["pair_id"], right["pair_id"])
            self.assertNotEqual(left["strategy"], right["strategy"])
            for key in ("preset", "control", "actor_postresponse", "expected"):
                self.assertEqual(left[key], right[key])
        for case_id in ("accepted-gtpyhop", "accepted-event-driven", "rejected-gtpyhop", "rejected-event-driven"):
            control = by_id[case_id]["control"]
            self.assertEqual(control["mode"], "result_only")
            self.assertIsNone(control["file_actor"])
            self.assertEqual(set(control["allowed_methods"]), {"file_by_B", "return_then_file_by_A"})
        envelope = _story_envelope(SUITE, by_id["accepted-gtpyhop"])
        self.assertEqual(envelope["actor_postresponse"]["rejected"]["B_archive"], "UNWILLING")

    def test_story_goal_is_one_new_note_archive_goal_not_old_delivery_suite(self):
        self.assertEqual(SUITE["common"]["objective"]["kind"], "archive_same_note_after_response")
        self.assertEqual(SUITE["common"]["objective"]["note_id"], None)
        self.assertEqual(SUITE["common"]["objective"]["by_minute"], 24)
        constraint_ids = [row["id"] for row in BUNDLE["constraints"]]
        self.assertEqual(constraint_ids, ["native-note-response"])
        self.assertNotIn("courier-delivery", constraint_ids)
        self.assertNotIn("resident-delivery", constraint_ids)

    def test_rejection_only_registers_return_then_file_method(self):
        row = next(case for case in SUITE["cases"] if case["case_id"] == "rejected-gtpyhop")
        self.assertEqual(row["control"]["allowed_methods"], ["file_by_B", "return_then_file_by_A"])
        self.assertIsNone(row["control"]["file_actor"])
        self.assertTrue(row["expected"]["distinct_future_from_accept"])

    def test_control_sources_are_distinct_and_explicit(self):
        by_id = {row["case_id"]: row for row in SUITE["cases"]}
        self.assertEqual(by_id["process-control"]["control"]["source"], "SYSTEM")
        self.assertEqual(by_id["direct-control"]["control"]["source"], "AUTHORED")
        self.assertEqual(by_id["locked-fragment"]["control"]["mode"], "locked_fragment")
        fragment = by_id["locked-fragment"]["locked_fragment_template"]
        canonical = json.dumps(fragment["sequence"], sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(fragment["sequence_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(fragment["abort_policy"], "ABORT_LOCKED_CORE")

    def test_negative_cases_are_separate_new_goal_witnesses(self):
        negatives = [row for row in SUITE["cases"] if row["case_id"] in {
            "no-task-authority", "resource-held-by-player", "absolute-deadline-negative"}]
        self.assertEqual(len(negatives), 3)
        self.assertTrue(all(row["expected"]["not_p5_four_goal_proxy"] for row in negatives))
        no_authority = next(row for row in negatives if row["case_id"] == "no-task-authority")
        self.assertEqual(no_authority["expected"]["reset"], "REJECTED_BEFORE_SCENE_CREATE")
        resource = next(row for row in negatives if row["case_id"] == "resource-held-by-player")
        self.assertEqual(resource["reactive_actions"][0]["at_minute"], 2)
        self.assertEqual(resource["reactive_actions"][0]["action"]["item_alias"], "courier_supply")
        deadline = next(row for row in negatives if row["case_id"] == "absolute-deadline-negative")
        self.assertEqual(deadline["objective_override"]["by_minute"], 18)
        locked_refusal = next(row for row in SUITE["cases"] if row["case_id"] == "locked-refusal-abort")
        self.assertTrue(locked_refusal["expected"]["abort_event"])


class StoryRunnerContractTests(unittest.TestCase):
    def test_scene_binding_replaces_only_template_strings(self):
        value = {"scenario_id": None, "marker": "${scene_id}", "nested": ["prefix-${scene_id}"]}
        self.assertEqual(_replace_scene_token(value, "scene-1"), {
            "scenario_id": None, "marker": "scene-1", "nested": ["prefix-scene-1"]})

    def test_observation_trigger_is_based_on_returned_native_fields(self):
        rules = [{"when": {"path": "story_process.decision.selected_method", "equals": "file_by_B"},
                  "action": {"kind": "author_story_edit"}}]
        self.assertEqual(_matching_actions(rules, {"story_process": {"decision": {
            "selected_method": "file_by_B"}}}, set())[0]["rule_index"], 0)
        self.assertEqual(_matching_actions(rules, {"story_process": {"decision": {
            "selected_method": "return_then_file_by_A"}}}, set()), [])
        self.assertEqual(_at_path({"rows": [{"minute": 2}]}, "rows.0.minute"), 2)
        scheduled = [{"at_minute": 2, "action": {"kind": "player_command", "operation": "get",
                                                   "item_alias": "courier_supply"}}]
        self.assertEqual(_matching_actions(scheduled, {}, set(), minute=1), [])
        self.assertEqual(_matching_actions(scheduled, {}, set(), minute=2)[0]["action"]["item_alias"],
                         "courier_supply")

    def test_future_edit_patch_cannot_touch_grant_or_permissions(self):
        request = {"version": 1, "control": {"file_actor": None,
                    "allowed_methods": ["file_by_B", "return_then_file_by_A"]}}
        updated = _patch_request(request, {"control.file_actor": "A",
                                  "control.allowed_methods": ["return_then_file_by_A"]}, new_version=2)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["control"]["file_actor"], "A")
        with self.assertRaises(ValueError):
            _patch_request(request, {"task_control_grant.actor_aliases": []}, new_version=2)

    def test_runner_steps_from_incremental_responses_and_keeps_one_final_trace(self):
        suite_copy = json.loads(json.dumps(SUITE))
        suite_copy["cases"] = [row for row in suite_copy["cases"]
                               if row["case_id"] == "accepted-gtpyhop"]
        counts = {"reset": 0, "step": 0, "trace": 0}

        def fake_rpc(operation, args):
            if operation == "reset_p5_scenario":
                counts["reset"] += 1
                return {"ok": True, "scene": {"scene_id": "scene-123", "seed": 1,
                        "horizon": 24, "preset": "hero_intelligence_30_v0",
                        "active_bundle": {"bundle_id": "story", "version": 1}}}
            if operation == "get_trace":
                counts["trace"] += 1
                now = 0 if counts["trace"] == 1 else 24
                request = {"schema": "story-process-request-v1", "request_id": "story-accepted-gtpyhop",
                           "version": 1, "scenario_id": "scene-123",
                           "objective": {**suite_copy["common"]["objective"], "note_id": 123},
                           "control": suite_copy["cases"][0]["control"],
                           "task_control_grant": {**suite_copy["common"]["task_control_grant"],
                                                   "scenario_id": "scene-123"},
                           "edit_policy": suite_copy["common"]["edit_policy"], "locked_fragment": None}
                story = {"request": request, "strategy": "gtpyhop", "bound_note_id": 123,
                         "controller_decisions": [], "receipts": [], "real_verdicts": []}
                return {"scene_id": "scene-123", "now": now,
                        "complete_through": {"events": now, "values": now},
                        "bundle_identity": {"bundle_id": "story", "version": 1},
                        "run_status": "COMPLETE", "story_process": story,
                        "large_ledger": ["not copied until the one final trace"] if now == 24 else []}
            if operation == "step_world":
                counts["step"] += 1
                minute = args["rounds"] if counts["step"] == 1 else counts["step"]
                delta = {"minute": minute, "minute_complete": True,
                         "trace_frontier": {"events_through": minute, "values_through": minute},
                         "story_process": {"decision": {"selected_method": "file_by_B"},
                                           "bound_note_id": 123, "effects_applied": False},
                         "typed_trace": {"now": str(minute), "events": [
                             {"event_id": f"e{minute}", "time": str(minute)}],
                             "points": [{"observable_id": "x", "time": str(minute)}]},
                         "actor_steps": [], "verdicts": []}
                return {"scene_id": "scene-123", "rounds": [delta],
                        "final": {"large_cumulative_evidence": ["do not persist per minute"]}}
            raise AssertionError(operation)

        with tempfile.TemporaryDirectory() as temporary:
            suite_path = Path(temporary) / "suite.json"
            suite_path.write_text(json.dumps(suite_copy), encoding="utf-8")
            (Path(temporary) / "story-bundle-v1.json").write_text(
                json.dumps(BUNDLE), encoding="utf-8")
            summary, run_dir = run_case("accepted-gtpyhop", suite_path=suite_path,
                                        runs_dir=Path(temporary) / "runs",
                                        call_rpc=fake_rpc, export_db=False)
            self.assertIsNone(summary["error"])
            self.assertEqual(summary["steps_recorded"], 24)
            self.assertEqual(counts, {"reset": 1, "step": 24, "trace": 2})
            step_docs = list(run_dir.glob("rpc-*-step_world-response.json"))
            self.assertEqual(len(step_docs), 24)
            self.assertNotIn("large_cumulative_evidence", "".join(
                path.read_text(encoding="utf-8") for path in step_docs))
            self.assertTrue((run_dir / "final-native-trace.json").is_file())
            identity = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))
            manifest = identity["source_manifest"]
            for source in ("tools/native_platform_v0/p5/story_process/actor.py",
                           "tools/native_platform_v0/p5/story_process/__init__.py"):
                relative = manifest["source_snapshot_relative_paths"][source]
                snapshot = run_dir / "source-snapshot" / relative
                self.assertTrue(snapshot.is_file())
                self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                                 manifest["working_tree_file_sha256"][source])
            self.assertEqual(manifest["remote_review_ref"], "refs/heads/webgpt-sync")

    def test_no_authority_rpc_rejection_is_not_reported_as_goal_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite_path = Path(temporary) / "suite.json"
            suite_path.write_text(json.dumps(SUITE), encoding="utf-8")
            (Path(temporary) / "story-bundle-v1.json").write_text(json.dumps(BUNDLE), encoding="utf-8")

            def reject_reset(operation, _args):
                if operation == "reset_p5_scenario":
                    raise RuntimeError("P3 control rejected operation (ValueError)")
                self.fail("No scene exists after pre-create rejection")

            summary, run_dir = run_case("no-task-authority", suite_path=suite_path,
                                        runs_dir=Path(temporary) / "runs",
                                        call_rpc=reject_reset, export_db=False)
            self.assertEqual(summary["status"], "EXPECTED_RESET_REJECTION")
            self.assertIsNone(summary["scene_id"])
            self.assertIsNone(summary["error"])
            evidence = json.loads((run_dir / "reset-rejection-evidence.json").read_text(encoding="utf-8"))
            self.assertFalse(evidence["scene_created"])
            self.assertTrue(evidence["expected"]["not_goal_pass"])

    def test_resume_existing_scene_never_resets_and_requires_exact_minute_zero_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prior = root / "prior"
            prior.mkdir()
            suite_path = root / "suite.json"
            suite_path.write_text(json.dumps(SUITE), encoding="utf-8")
            bundle_path = root / "story-bundle-v1.json"
            bundle_path.write_text(json.dumps(BUNDLE), encoding="utf-8")
            case = next(row for row in SUITE["cases"] if row["case_id"] == "accepted-gtpyhop")
            bundle_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
            (prior / "identity.json").write_text(json.dumps({
                "case_id": case["case_id"], "strategy": case["strategy"],
                "preset": case["preset"], "bundle_sha256": bundle_sha,
                "source_manifest": {"working_tree_file_set_sha256": "base-source",
                                    "working_tree_file_sha256": {"model.py": "base-hash"}},
            }), encoding="utf-8")
            scene_identity = {"scene_id": "existing-accepted-scene", "horizon": 24,
                              "seed": SUITE["common"]["seed"], "preset": case["preset"],
                              "active_bundle": {"bundle_id": "story-process-note-response-v1", "version": 1},
                              "player": {"id": 6572},
                              "items": {"courier_supply": {"id": 6570},
                                        "resident_parcel": {"id": 6571}}}
            (prior / "scene_identity.json").write_text(json.dumps(scene_identity), encoding="utf-8")
            (prior / "failure.json").write_text('{"error":"expected original t0 capture failure"}',
                                                 encoding="utf-8")
            counts = {"reset": 0, "trace": 0, "step": 0}
            request = _story_envelope(SUITE, case)
            request["scenario_id"] = scene_identity["scene_id"]
            request["task_control_grant"]["scenario_id"] = scene_identity["scene_id"]

            def fake_rpc(operation, args):
                if operation == "reset_p5_scenario":
                    counts["reset"] += 1
                    self.fail("continuation must never reset an existing scene")
                if operation == "get_trace":
                    counts["trace"] += 1
                    minute = 0 if counts["trace"] == 1 else 24
                    return {"scene_id": scene_identity["scene_id"], "now": minute,
                            "complete_through": {"events": minute, "values": minute},
                            "bundle_identity": {**scene_identity["active_bundle"], "sha256": "b" * 64},
                            "run_status": "COMPLETE",
                            "story_process": {"request": request, "strategy": "gtpyhop",
                                              "bound_note_id": None,
                                              "controller_decisions": [], "receipts": [],
                                              "real_verdicts": []}}
                if operation == "step_world":
                    counts["step"] += 1
                    return {"scene_id": scene_identity["scene_id"], "rounds": [{
                        "minute": counts["step"], "minute_complete": True,
                        "trace_frontier": {"events_through": counts["step"],
                                           "values_through": counts["step"]},
                        "story_process": {"bound_note_id": None}, "typed_trace": {},
                        "actor_steps": [], "verdicts": []}], "final": {}}
                self.fail(f"unexpected RPC operation: {operation}")

            summary, run_dir = run_case(
                case["case_id"], suite_path=suite_path, runs_dir=root / "runs",
                call_rpc=fake_rpc, export_db=False,
                existing_scene_id=scene_identity["scene_id"], expected_minute=0,
                continuation_of=prior)
            self.assertIsNone(summary["error"])
            self.assertEqual(counts, {"reset": 0, "trace": 2, "step": 24})
            continuation = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))["continuation"]
            self.assertEqual(continuation["mode"], "existing_scene_only_no_reset")
            self.assertEqual(continuation["prior_run_directory"], str(prior))
            self.assertEqual(continuation["prior_source_file_set_sha256"], "base-source")
            self.assertTrue((run_dir / "initial-observation.json").is_file())
            prefix = json.loads((run_dir / "continuation-prefix-verification.json").read_text(encoding="utf-8"))
            self.assertEqual(prefix["bundle_sha256_pin_status"], "ESTABLISHED")
            self.assertEqual(prefix["observed_bundle_sha256"], "b" * 64)

    def test_t18_continuation_fixture_preserves_active_note_task_and_raw_receipt(self):
        case = next(row for row in SUITE["cases"] if row["case_id"] == "accepted-gtpyhop")
        scene_id = "scene-t18-fixture"
        request = _story_envelope(SUITE, case)
        request["scenario_id"] = scene_id
        request["task_control_grant"]["scenario_id"] = scene_id
        request["objective"]["note_id"] = 30
        task = {"request_id": "request-file-b", "actor_alias": "B", "task_kind": "archive_note",
                "item_id": 30, "destination_id": 57, "source_method_id": "file_by_B",
                "control_source": "PLANNER", "grant_id": request["task_control_grant"]["grant_id"],
                "status": "IN_PROGRESS", "accepted_at_minute": 18}
        decision = {"selected_method": "file_by_B", "method_plans": [
            {"method_id": "file_by_B", "feasible": True},
            {"method_id": "return_then_file_by_A", "feasible": True}],
            "attempted_methods": [{"method_id": "file_by_B", "feasible": True},
                                  {"method_id": "return_then_file_by_A", "feasible": True}]}
        story = {"request": request, "bound_note_id": 30,
                 "controller_decisions": [decision], "actor_tasks": [
                     {"actor_alias": "A", "task": None}, {"actor_alias": "B", "task": task}],
                 "receipts": []}
        prior_trace = {"scene_id": scene_id, "now": 18,
                       "complete_through": {"events": 18, "values": 18},
                       "story_process": story}
        objects = [
            {"id": 12, "attributes": {"native_p5": {}}},
            {"id": 10, "attributes": {"native_p5": {}}},
            {"id": 11, "attributes": {"native_p5": {}}},
            {"id": 50, "location": {"id": 57}, "attributes": {"native_p5": {
                "p5_actor_alias": "B", "p5_story_task": task,
                "p5_story_receipts": [{"receipt_id": "move-1", "kind": "move",
                                       "item_id": 30, "after_room_id": 57, "settled": True}]}}},
            {"id": 30, "location": {"id": 50}, "attributes": {"native_p5": {"p5_item_alias": "note"}}},
            {"id": 40, "attributes": {"native_p5": {"p5_story_meta": {
                "controller_decisions": [decision], "controller_authored_npc_commands": 0,
                "controller_authored_npc_task_requests": 0},
                "p5_story_request": request,
                "p5_completed_minutes": list(range(19)),
                "p5_event_coverage_minute": 18, "p5_snapshot_coverage_minute": 18},
                "native_p3": {"p4_ledger": [
                    {"event_type": "p5_delivery_settled", "sealed": True,
                     "typed_args": {"actor": "A", "item": "courier_supply"}},
                    {"event_type": "p5_delivery_settled", "sealed": True,
                     "typed_args": {"actor": "B", "item": "resident_parcel"}}]}}},
        ]
        scene_identity = {"player": {"id": 12}, "items": {
            "courier_supply": {"id": 10}, "resident_parcel": {"id": 11}}}
        evidence = {"scenes": [{"scene_id": scene_id, "objects": objects}]}
        expected = _expected_continuation_request(_story_envelope(SUITE, case), scene_id, prior_trace)
        self.assertEqual(expected, request)
        result = _validate_active_db_prefix(evidence, scene_id, scene_identity, prior_trace, 18)
        self.assertEqual(result["bound_note_id"], 30)
        self.assertEqual(result["b_task_status"], "IN_PROGRESS")
        self.assertEqual(result["b_actor_room_id"], 57)
        self.assertEqual(result["move_receipt_id"], "move-1")
        self.assertTrue(result["both_methods_feasible"])

    def test_resource_assessment_requires_settled_receipt_persistent_holder_and_no_note_verdict(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "scene_identity.json").write_text(json.dumps({
                "player": {"id": 30}, "items": {"courier_supply": {"id": 40}}}), encoding="utf-8")
            case = next(row for row in SUITE["cases"] if row["case_id"] == "resource-held-by-player")
            steps = [{"minute": 2, "intervention_results": [{"status": "SETTLED", "receipt": {
                "actor_alias": "player", "item_id": 40, "settled": True}}]}]
            trace = {"world_snapshots": [{"item_locations": {"courier_supply": 30}}],
                     "world_capability_projection": {"task_bindings": {"A": {
                         "item_alias": "courier_supply", "item_id": 40}}},
                     "actor_evidence": [{"actor_alias": "A", "native_receipts": []}],
                     "now": 24, "horizon": 24, "complete_through": {"events": 24, "values": 24},
                     "story_process": {"bound_note_id": None, "real_verdicts": [{
                         "status": "NO_NATIVE_NOTE_EVIDENCE", "verdict": "NOT_SATISFIED"}]}}
            result = _assess_case(case, trace, steps, run_dir)
            self.assertEqual(result["story_result"], "UNBOUND_NO_NATIVE_NOTE")
            self.assertEqual(result["goal_result"], "NOT_SATISFIED")
            self.assertTrue(result["pass"])
            trace["world_snapshots"][0]["item_locations"]["courier_supply"] = 22
            self.assertFalse(_assess_case(case, trace, steps, run_dir)["pass"])

    def test_locked_negative_requires_real_sealed_abort_and_unchanged_core(self):
        case = next(row for row in SUITE["cases"] if row["case_id"] == "locked-refusal-abort")
        digest = case["locked_fragment_template"]["sequence_sha256"]
        trace = {"story_process": {
            "controller_events": [{"event_type": "P5_STORY_LOCKED_FRAGMENT_ABORTED", "sealed": True,
                                   "reason": ["locked_fragment_entry_guard_note_holder_mismatch"],
                                   "immutable_sequence_sha256": digest}],
            "controller_decisions": [{"status": "LOCKED_ABORTED", "task_requests": []}],
            "real_verdicts": [{"status": "VIOLATED"}]}}
        result = _assess_case(case, trace, [], Path("."))
        self.assertTrue(result["pass"])
        trace["story_process"]["controller_events"][0]["immutable_sequence_sha256"] = "different"
        self.assertFalse(_assess_case(case, trace, [], Path("."))["pass"])

    def test_locked_negative_reads_native_nested_reasons_and_typedir_verdicts(self):
        case = next(row for row in SUITE["cases"] if row["case_id"] == "locked-refusal-abort")
        digest = case["locked_fragment_template"]["sequence_sha256"]
        trace = {"story_process": {
            "controller_events": [{"event_type": "P5_STORY_LOCKED_FRAGMENT_ABORTED", "sealed": True,
                                   "reason": [{"kind": "LOCKED_FRAGMENT_ENTRY_GUARD",
                                               "reasons": ["locked_fragment_entry_guard_note_holder_mismatch"]}],
                                   "immutable_sequence_sha256": digest}],
            "controller_decisions": [{"status": "LOCKED_ABORTED", "task_requests": []}],
            "real_verdicts": [{"constraint_id": "story-note-archive-by-deadline",
                               "verdicts": [{"verdict": "VIOLATED"}]}]}}
        result = _assess_case(case, trace, [], Path("."))
        self.assertTrue(result["expected_guard_mismatch_observed"])
        self.assertEqual(result["goal_result"], "VIOLATED")
        self.assertTrue(result["pass"])


if __name__ == "__main__":
    unittest.main()
