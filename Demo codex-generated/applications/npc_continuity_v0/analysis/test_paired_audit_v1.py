import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("paired_audit_v1.py")
SPEC = importlib.util.spec_from_file_location("paired_audit_v1", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def make_fixture(policy):
    facts = [
        {"key": "clock.total_minutes", "value": "110", "status": "known", "source": "runtime", "observed_at": "01:50"},
        {"key": "clock.time", "value": "01:50", "status": "known", "source": "runtime", "observed_at": "01:50"},
        {"key": "task.coursework.status", "value": "active", "status": "known", "source": "initial_task_brief", "observed_at": "01:40"},
        {"key": "task.coursework.effort", "value": "0", "status": "known", "source": "initial_task_brief", "observed_at": "01:40"},
    ]
    request = {
        "protocol": "npc-history-llm-request-v1", "clock_total_minutes": 110,
        "clock_time": {"value": "01:50", "status": "known"},
        "observation_history_window": "runtime_actor_ledger_48h",
        "observation_known_facts": [{k: f[k] for k in ("key", "value", "status")} for f in facts],
        "actor_history": {"ledger_window": "runtime_pruned_to_48h", "episodes": [], "observed_events": []},
        "running_action": {"action": "study_focused", "target": "desk", "start_total_minutes": 100,
                           "elapsed_minutes": 5, "planned_minutes": 10, "remaining_minutes": 5},
        "candidates": [{"candidate_id": "c0", "action": "study_focused", "hard_admissible": True,
                        "target": "desk", "planned_minutes": 5, "nominal_default_minutes": 10,
                        "retains_progress": True}],
    }
    selection = {"clock_total_minutes": 110, "clock_time": request["clock_time"],
                 "observation_known_facts": facts, "actor_history": request["actor_history"],
                 "running_action": request["running_action"], "candidates": request["candidates"],
                 "request_json": json.dumps(request, separators=(",", ":"))}
    running0 = {"action": "study_focused", "target": "desk", "started_at_total_minutes": 100,
                "elapsed_minutes": 0, "planned_minutes": 10, "status": "running"}
    running5 = dict(running0, elapsed_minutes=5)
    running_next = dict(running0, started_at_total_minutes=110, elapsed_minutes=0)
    header = {"kind": "header", "protocol": audit.PROTOCOL, "case": "alarm_active", "policy": policy,
              "policy_identity": "test", "requested_model_id": "mock-model" if policy == "history-llm" else "mock-model",
              "fixture_seed": 0, "policy_seed": 17, "horizon_minutes": 90, "max_boundaries": 1000,
              "history_window": "runtime_actor_ledger_pruned_to_48h",
              "scenario_setup": {"start_total_minutes": 100, "task_status": "active", "task_effort": 0,
                  "task_effort_target": 8, "task_setup_source": "initial_task_brief", "initial_action": "study_focused",
                  "initial_action_target": "desk", "initial_action_planned_minutes": 10,
                  "initial_action_source": "scenario_setup", "initial_action_world_accepted": True}}
    initial = {"kind": "initial_state", "minute": 100,
               "observation": {"facts": facts, "clock_total_minutes": 100,
                   "clock_total_minutes_status": "known", "clock_time": "01:40", "clock_time_status": "known"},
               "running_action": running0,
               "task_world": {"status": "active", "effort_done": 0, "effort_target": 8, "completed_at_total_minutes": None},
               "actor_history": request["actor_history"]}
    b1 = {"kind": "boundary", "index": 0,
          "interval": {"from_total_minutes": 100, "at_total_minutes": 105, "elapsed_minutes": 5,
                       "ownership": "interval_before_boundary_then_events_at_at_total_minutes"},
          "policy_evaluated": False, "policy_call_index": None, "gate_reasons": [], "running_before": running0,
          "running_after": running5, "selected_action": None, "selected_target": "",
          "replacement_validation": {"performed": False, "accepted": None}, "world_events": [],
          "observation_deltas": [], "observation_facts": facts, "pre_policy_outcome": None,
          "post_policy_outcome": None, "task_world_after": initial["task_world"], "candidate_signature": "",
          "policy_provenance": "", "selection_input": None, "actor_history_after": request["actor_history"]}
    b2 = {"kind": "boundary", "index": 1,
          "interval": {"from_total_minutes": 105, "at_total_minutes": 110, "elapsed_minutes": 5,
                       "ownership": "interval_before_boundary_then_events_at_at_total_minutes"},
          "policy_evaluated": True, "policy_call_index": 1, "gate_reasons": ["action_completed"],
          "running_before": running5, "running_after": running_next, "selected_action": "study_focused",
          "selected_target": "desk", "replacement_validation": {"performed": False, "accepted": None},
          "world_events": [], "observation_deltas": [], "observation_facts": facts,
          "pre_policy_outcome": {"action": "study_focused", "accepted": True, "rejection_reason": "none",
              "provenance": "runtime_completion", "task_completed": False, "interrupted": False,
              "plan_invalidated": False, "elapsed_minutes": 5, "action_elapsed_minutes": 10,
              "task_effort_before": 0, "task_effort_gained": 2, "task_effort_after": 2},
          "post_policy_outcome": None, "task_world_after": {"status": "active", "effort_done": 2,
              "effort_target": 8, "completed_at_total_minutes": None}, "candidate_signature": "study_focused:desk:1",
          "policy_provenance": "fake", "selection_input": selection, "actor_history_after": request["actor_history"]}
    termination = {"kind": "termination", "reason": "call_limit", "minute": 110,
                   "policy_calls": 1, "boundaries": 2, "simulated_minutes": 10}
    return [header, initial, b1, b2, termination], request


def make_api_journal(request, model="mock-model", candidate_id="c0"):
    api_request = {"model": model, "messages": [
        {"role": "system", "content": "system"},
        {"role": "user", "content": json.dumps(request, separators=(",", ":"))}],
        "response_format": {"type": "json_schema"}}
    digest = hashlib.sha256(json.dumps(api_request, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    return {"status": "ok", "model": model, "request": api_request, "request_sha256": digest,
            "candidate_id": candidate_id, "elapsed_ms": 12,
            "usage": {"prompt_tokens": 90, "completion_tokens": 4}}


class PairedAuditContract(unittest.TestCase):
    def summarize(self, rows, journal=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            journal_path = None
            if journal is not None:
                journal_path = Path(tmp) / "calls.jsonl"
                journal_path.write_text("".join(json.dumps(row) + "\n" for row in journal), encoding="utf-8")
            return audit._run_summary(path, journal_path)

    def test_duration_belongs_to_running_before_and_limit_is_not_full_horizon(self):
        rows, _ = make_fixture("utility")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = audit._run_summary(path, None)
        self.assertEqual(result["action_minutes_by_running_before"], {"study_focused": 10})
        self.assertFalse(result["full_horizon"])
        self.assertEqual(result["http_journal"]["api_elapsed_ms_total"], None)
        self.assertEqual(result["http_journal"]["elapsed_status"], "no_calls")

    def test_pair_requires_exact_initial_and_first_selection_match(self):
        utility_rows, _ = make_fixture("utility")
        llm_rows, llm_request = make_fixture("history-llm")
        with tempfile.TemporaryDirectory() as tmp:
            u = Path(tmp) / "u.jsonl"; l = Path(tmp) / "l.jsonl"
            u.write_text("".join(json.dumps(row) + "\n" for row in utility_rows), encoding="utf-8")
            l.write_text("".join(json.dumps(row) + "\n" for row in llm_rows), encoding="utf-8")
            journal_path = Path(tmp) / "calls.jsonl"
            journal_path.write_text(json.dumps(make_api_journal(llm_request)) + "\n", encoding="utf-8")
            pair = audit.audit_pair(audit._run_summary(u, None), audit._run_summary(l, journal_path))
            self.assertTrue(pair["first_selection_input_equal"])
            llm_rows[3]["selection_input"]["clock_total_minutes"] += 1
            l.write_text("".join(json.dumps(row) + "\n" for row in llm_rows), encoding="utf-8")
            with self.assertRaises(audit.AuditError):
                audit.audit_pair(audit._run_summary(u, None), audit._run_summary(l, journal_path))

    def test_completed_world_without_typed_completion_outcome_is_rejected(self):
        rows, _ = make_fixture("utility")
        rows[3]["task_world_after"]["status"] = "completed"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(audit.AuditError, "matching true Runtime outcome"):
                audit._run_summary(path, None)

    def test_unperformed_validation_cannot_be_reported_as_rejection(self):
        rows, _ = make_fixture("utility")
        rows[3]["replacement_validation"]["accepted"] = False
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(audit.AuditError, "accepted=null"):
                audit._run_summary(path, None)

    def test_history_journal_hash_and_policy_request_are_verified(self):
        rows, request = make_fixture("history-llm")
        api_request = {"model": "mock-model", "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": json.dumps(request, separators=(",", ":"))}],
            "response_format": {"type": "json_schema"}}
        digest = hashlib.sha256(json.dumps(api_request, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        journal = {"status": "ok", "model": "mock-model", "request": api_request,
                   "request_sha256": digest, "candidate_id": "c0", "elapsed_ms": 12,
                   "usage": {"prompt_tokens": 90, "completion_tokens": 4}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); trace = root / "trace.jsonl"; calls = root / "calls.jsonl"
            trace.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            calls.write_text(json.dumps(journal) + "\n", encoding="utf-8")
            result = audit._run_summary(trace, calls)
            self.assertEqual(result["http_journal"]["api_elapsed_ms_total"], 12)
            self.assertEqual(result["http_journal"]["prompt_tokens"], 90)
            journal["request_sha256"] = "0" * 64
            calls.write_text(json.dumps(journal) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(audit.AuditError, "request_sha256 mismatch"):
                audit._run_summary(trace, calls)

    def test_actor_history_or_candidates_drifting_from_request_is_rejected(self):
        rows, _ = make_fixture("utility")
        rows[3]["selection_input"]["actor_history"]["episodes"].append({"action": "phone"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(audit.AuditError, "actor history differs"):
                audit._run_summary(path, None)

    def test_policy_calls_must_equal_evaluations_or_one_recorded_failed_attempt(self):
        rows, _ = make_fixture("utility")
        rows[-1]["policy_calls"] = 2
        with self.assertRaisesRegex(audit.AuditError, "policy_calls does not match"):
            self.summarize(rows)

    def test_full_horizon_history_run_requires_a_journal_row_per_evaluation(self):
        rows, _ = make_fixture("history-llm")
        rows[0]["horizon_minutes"] = 10
        rows[-1].update(reason="horizon", minute=110, simulated_minutes=10)
        with self.assertRaisesRegex(audit.AuditError, "one row per evaluation"):
            self.summarize(rows)

        rows, request = make_fixture("history-llm")
        rows[0]["horizon_minutes"] = 10
        rows[-1].update(reason="horizon", minute=110, simulated_minutes=10)
        failed = make_api_journal(request)
        failed["status"] = "error"
        with self.assertRaisesRegex(audit.AuditError, "contains failed calls"):
            self.summarize(rows, [failed])

    def test_selection_clock_must_match_actual_boundary_time(self):
        rows, request = make_fixture("utility")
        request["clock_total_minutes"] = 111
        rows[3]["selection_input"]["clock_total_minutes"] = 111
        rows[3]["selection_input"]["request_json"] = json.dumps(request, separators=(",", ":"))
        with self.assertRaisesRegex(audit.AuditError, "selection clock is not the boundary clock"):
            self.summarize(rows)

    def test_boundary_indices_and_running_state_chain_are_checked(self):
        rows, _ = make_fixture("utility")
        rows[3]["index"] = 4
        with self.assertRaisesRegex(audit.AuditError, "zero-based"):
            self.summarize(rows)
        rows, _ = make_fixture("utility")
        rows[3]["running_before"] = dict(rows[3]["running_before"])
        rows[2]["running_after"]["started_at_total_minutes"] = 101
        rows[2]["running_after"]["elapsed_minutes"] = 4
        with self.assertRaisesRegex(audit.AuditError, "running_before differs"):
            self.summarize(rows)

    def test_same_intent_cannot_reset_progress_before_planned_end(self):
        rows, request = make_fixture("utility")
        rows[3]["interval"].update(at_total_minutes=108, elapsed_minutes=3)
        rows[3]["pre_policy_outcome"] = None
        request["clock_total_minutes"] = 108
        request["clock_time"]["value"] = "01:48"
        for fact in request["observation_known_facts"]:
            if fact["key"] == "clock.total_minutes": fact["value"] = "108"
            if fact["key"] == "clock.time": fact["value"] = "01:48"
        selection = rows[3]["selection_input"]
        selection["clock_total_minutes"] = 108
        selection["clock_time"]["value"] = "01:48"
        for fact in selection["observation_known_facts"]:
            if fact["key"] == "clock.total_minutes": fact["value"] = "108"
            if fact["key"] == "clock.time": fact["value"] = "01:48"
        selection["request_json"] = json.dumps(request, separators=(",", ":"))
        rows[3]["running_after"]["started_at_total_minutes"] = 103
        rows[3]["running_after"]["elapsed_minutes"] = 5
        rows[-1].update(minute=108, simulated_minutes=8)
        with self.assertRaisesRegex(audit.AuditError, "same-intent continuation reset"):
            self.summarize(rows)

    def test_task_completion_requires_accepted_noninterrupted_runtime_outcome(self):
        rows, _ = make_fixture("utility")
        rows[3]["pre_policy_outcome"].update(task_completed=True, accepted=False)
        rows[3]["task_world_after"].update(status="completed", effort_done=8)
        with self.assertRaisesRegex(audit.AuditError, "not an accepted completion"):
            self.summarize(rows)

    def test_order_unknown_records_and_error_horizon_are_not_accepted(self):
        rows, _ = make_fixture("utility")
        rows[2], rows[1] = rows[1], rows[2]
        with self.assertRaisesRegex(audit.AuditError, "ordering"):
            self.summarize(rows)
        rows, _ = make_fixture("utility")
        rows.insert(-1, {"kind": "unexpected"})
        with self.assertRaisesRegex(audit.AuditError, "unknown record kinds"):
            self.summarize(rows)
        rows, _ = make_fixture("utility")
        rows[0]["horizon_minutes"] = 10
        rows[-1].update(reason="horizon", minute=110, simulated_minutes=10)
        rows.insert(-1, {"kind": "error", "stage": "transport", "type": "Timeout"})
        with self.assertRaisesRegex(audit.AuditError, "cannot contain an error record"):
            self.summarize(rows)

    def test_failed_history_attempt_requires_matching_error_and_journal(self):
        rows, request = make_fixture("history-llm")
        rows[3]["selection_input"]["request_json"] = json.dumps(request, separators=(",", ":"))
        rows.insert(-1, {"kind": "error", "stage": "transport", "type": "Timeout",
                         "minute": 110, "selection_input": rows[3]["selection_input"]})
        rows[-1].update(reason="errors", policy_calls=2)
        api_request = {"model": "mock-model", "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": json.dumps(request, separators=(",", ":"))}],
            "response_format": {"type": "json_schema"}}
        digest = hashlib.sha256(json.dumps(api_request, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        first = {"status": "ok", "model": "mock-model", "request": api_request, "request_sha256": digest,
                 "candidate_id": "c0", "elapsed_ms": 12, "usage": {"prompt_tokens": 90, "completion_tokens": 4}}
        failed = {"status": "error", "stage": "transport", "error_type": "Timeout", "model": "mock-model",
                  "request": api_request, "request_sha256": digest, "elapsed_ms": 1000}
        result = self.summarize(rows, [first, failed])
        self.assertEqual(result["termination_reason"], "errors")
        with self.assertRaisesRegex(audit.AuditError, "lacks a matching HTTP journal"):
            self.summarize(rows, [first])



if __name__ == "__main__":
    unittest.main()
