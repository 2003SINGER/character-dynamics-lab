"""Small fake-RPC contracts for the live System Baseline runner boundary."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.system_baseline_v0.runner import run_case
from test_contracts import raw_bundle, trace


class RunnerRPCContracts(unittest.TestCase):
    def _execute(self, sabre_result, db_result=(None, {"exit_code": 0}), *, reset_ok=True):
        with tempfile.TemporaryDirectory(prefix="system-baseline-runner-contract-") as temp:
            root = Path(temp)
            bundle_path = root / "bundle.json"
            bundle_path.write_text(json.dumps(raw_bundle()), encoding="utf-8")
            calls = []

            def rpc(method, params):
                calls.append((method, params))
                if method == "reset_p5_scenario":
                    return {"ok": reset_ok, "scene": {"scene_id": "runner-contract-scene"}}
                if method == "get_trace":
                    evidence = trace()
                    evidence["scene_id"] = "runner-contract-scene"
                    return evidence
                if method == "step_world":
                    return {"rounds": [{"edits": [], "interventions": [],
                                        "minute": 1, "minute_complete": True}]}
                raise AssertionError(f"unexpected RPC {method}")

            result = run_case(
                {"id": "runner-contract", "bundle": str(bundle_path),
                 "preset": "native_default_reject_v0", "horizon": 1},
                rpc=rpc, output_parent=root / "runs",
                sabre=lambda _problem: dict(sabre_result),
                db_readback=lambda _scene: db_result,
            )
            artifacts = Path(result["run_dir"])
            return result, calls, artifacts

    @staticmethod
    def _success_result(*, native_result="Success!", returncode=0,
                        status="PLAN_FOUND_NOT_EXECUTION_EVIDENCE"):
        return {"status": status,
                "selected_action": "open_main_passage", "native_result": native_result,
                "returncode": returncode, "raw_stdout": native_result}

    def test_nested_reset_and_normalized_raw_success_exit_zero_dispatch_guarded_candidate(self):
        result, calls, artifacts = self._execute(self._success_result())
        self.assertEqual(result["status"], "DEVELOPMENT_RUN_RECORDED", result)
        reset = next(params for method, params in calls if method == "reset_p5_scenario")
        self.assertEqual(reset["horizon"], 1)
        step = next(params for method, params in calls if method == "step_world")
        self.assertEqual(step["scene_id"], "runner-contract-scene")
        dispatched = [row for row in step["interventions"]
                      if row.get("kind") == "author_opportunity"]
        self.assertEqual(len(dispatched), 1, step)
        self.assertEqual(dispatched[0]["opportunity_id"], "open_main_passage")
        self.assertEqual(dispatched[0]["candidate_guard"]["selected_action"],
                         "open_main_passage")
        self.assertFalse(result["db_readback_recorded"])
        self.assertFalse((artifacts / "independent_db_readback.json").exists())

    def test_nonzero_exit_never_dispatches_even_with_normalized_success_and_raw_success(self):
        result, calls, _ = self._execute(self._success_result(returncode=1))
        step = next(params for method, params in calls if method == "step_world")
        self.assertFalse(any(row.get("kind") == "author_opportunity"
                             for row in step["interventions"]))
        self.assertEqual(result["status"], "DEVELOPMENT_RUN_RECORDED")

    def test_non_success_normalized_status_and_raw_failure_never_dispatch(self):
        result, calls, _ = self._execute(self._success_result(
            native_result="Failure!", status="SEARCH_BUDGET"))
        step = next(params for method, params in calls if method == "step_world")
        self.assertFalse(any(row.get("kind") == "author_opportunity"
                             for row in step["interventions"]))
        self.assertEqual(result["status"], "DEVELOPMENT_RUN_RECORDED")

    def test_empty_and_error_db_exports_are_not_readback_evidence(self):
        for db_result in ((None, {"exit_code": 0, "artifact_sha256": "abc"}),
                          {"status": "DB_READBACK_ERROR", "error_type": "RuntimeError"}):
            with self.subTest(db_result=db_result):
                result, _, artifacts = self._execute(self._success_result(), db_result)
                self.assertFalse(result["db_readback_recorded"])
                self.assertFalse((artifacts / "independent_db_readback.json").exists())

    def test_nested_reset_without_scene_identity_is_not_silently_accepted(self):
        result, _, _ = self._execute(self._success_result(), reset_ok=False)
        self.assertEqual(result["status"], "RESET_REJECTED")


if __name__ == "__main__":
    unittest.main()
