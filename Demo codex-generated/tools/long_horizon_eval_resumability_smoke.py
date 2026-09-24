"""Model-free regression coverage for long-horizon actor checkpoints and modes."""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from unittest import mock

import long_horizon_eval as evaluator


FAKE_RUNNER = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
scenario, seed, days = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
profile, output = sys.argv[4], pathlib.Path(sys.argv[5])
policy = "laya-typed-policy-v0" if "--laya-port" in sys.argv else "rule-policy-v0"
log = pathlib.Path(os.environ["EVAL_RESUME_CALL_LOG"])
with log.open("a") as f: f.write("called\n")
personality = {name: 0.5 for name in ("procrastination", "self_control", "rest_preference",
              "stimulation_seeking", "task_anxiety_sensitivity", "screen_strain_sensitivity",
              "need_response", "action_noise")}
with output.open("w") as f:
    def emit(row): f.write(json.dumps(row, separators=(",", ":")) + "\n")
    emit({"type":"run", "profile_id":profile, "personality":personality,
          "scenario_seed":scenario, "policy_seed":seed, "days":days,
          "policy_id":policy, "dynamics_model":"demo-living-v1",
          "life_tape_cycle_days":3, "initial_task_effort_target":10,
          "initial_task_deadline":1000, "initial_state":{"fatigue":0.0}})
    for day in range(1, days + 1):
        emit({"type":"daily", "day":day, "profile_id":profile,
              "study_minutes":1, "leisure_minutes":1, "rest_minutes":1,
              "sleep_minutes":1, "idle_minutes":1, "bodily_minutes":1,
              "task_completions":0, "decision_count":1,
              "state":{"task_pressure":0.2, "fatigue":0.1, "anxiety":0.1}})
    emit({"type":"boundary", "elapsed_minutes":10, "running_action_before":None,
          "running_action_started_at":None, "commitment_before":"none",
          "selected_action":"idle", "timestamp":0, "world_events":["event-1"]})
    checkpoints = [7, 30, 60, 120, 180] if days >= 180 else sorted({7, days})
    for checkpoint in [day for day in checkpoints if day <= days]:
        for horizon in (360, 1440, 4320):
            for branch in ("correct", "reset", "stale_24h"):
                emit({"type":"fork", "scenario_seed":scenario, "profile_id":profile,
                      "checkpoint_day":checkpoint, "horizon_minutes":horizon,
                      "branch":branch, "future_world_events":[[1,"event-1"]],
                      "immediate_pi_js":0.0, "immediate_top1_changed":False,
                      "study_minutes":0, "leisure_minutes":0, "task_effort":0,
                      "state":{"fatigue":0.0}})
fail_profile = os.environ.get("EVAL_RESUME_FAIL_PROFILE")
marker = os.environ.get("EVAL_RESUME_FAIL_MARKER")
if profile == fail_profile and marker and not pathlib.Path(marker).exists():
    pathlib.Path(marker).write_text("failed once")
    raise SystemExit(7)
'''


def expect_failure(call, fragment):
    try:
        call()
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        if fragment not in str(error):
            raise SystemExit(f"unexpected failure: {error}")
    else:
        raise SystemExit(f"expected failure containing {fragment!r}")


def main():
    policy_mode = evaluator.mode_metadata("laya")
    xi_mode = evaluator.mode_metadata("laya", commitment=True, appraisal=True)
    if not policy_mode["paired_policy_compare_eligible"]:
        raise SystemExit("policy-only Laya mode should remain comparator eligible")
    if xi_mode["paired_policy_compare_eligible"] or "typed-xi" not in xi_mode["comparison_scope"]:
        raise SystemExit("full typed mode was not isolated as a supplement")
    if xi_mode["policy_id"] == policy_mode["policy_id"]:
        raise SystemExit("supplement mode would pass the existing policy-only comparator gate")
    command = evaluator.run_command("binary", "trace", 7, 0, "balanced", None, None,
                                    "laya", 8743,
                                    {"soft_gate":True, "commitment":True, "appraisal":True})
    if command[-3:] != ["--laya-soft-gate", "--laya-commitment", "--laya-appraisal"]:
        raise SystemExit("Laya intervention flags were not passed to the executable")

    with tempfile.TemporaryDirectory(prefix="long-horizon-resume-smoke-") as temporary:
        root = pathlib.Path(temporary)
        runner = root / "fake-runner"
        runner.write_text(FAKE_RUNNER)
        runner.chmod(0o755)
        log = root / "calls.log"
        os.environ["EVAL_RESUME_CALL_LOG"] = str(log)
        output = root / "output"
        command = [sys.executable, str(pathlib.Path(evaluator.__file__)), str(runner),
                   str(output), "--days", "7", "--cases", "1"]
        subprocess.run(command, check=True, timeout=30)
        first_count = len(log.read_text().splitlines())
        if first_count != 16:
            raise SystemExit(f"expected two executions for each of 8 actors, got {first_count}")
        manifest = json.loads((output / "manifest.json").read_text())
        if len(manifest["runs"]) != 8 or not all(
                row["mode"]["paired_policy_compare_eligible"] is False for row in manifest["runs"]):
            raise SystemExit("actor manifest lacks per-actor mode evidence")
        subprocess.run(command, check=True, timeout=30)
        if len(log.read_text().splitlines()) != first_count:
            raise SystemExit("completed actors were rerun instead of resumed")
        trace = output / manifest["runs"][0]["trace"]
        with trace.open("ab") as handle:
            handle.write(b"tamper")
        expect_failure(lambda: subprocess.run(command, check=True, timeout=30,
                                              capture_output=True, text=True),
                       "returned non-zero exit status")
        if len(log.read_text().splitlines()) != first_count:
            raise SystemExit("a tampered completed trace triggered rerunning")

        interrupted = root / "interrupted-output"
        marker = root / "fail-once.marker"
        os.environ["EVAL_RESUME_FAIL_PROFILE"] = "procrastinating"
        os.environ["EVAL_RESUME_FAIL_MARKER"] = str(marker)
        interrupted_command = [sys.executable, str(pathlib.Path(evaluator.__file__)),
                              str(runner), str(interrupted), "--days", "7", "--cases", "1"]
        expect_failure(lambda: subprocess.run(interrupted_command, check=True, timeout=30,
                                              capture_output=True, text=True),
                       "returned non-zero exit status")
        if len(log.read_text().splitlines()) != first_count + 5:
            raise SystemExit("interrupted run did not stop at the first unfinished actor")
        subprocess.run(interrupted_command, check=True, timeout=30)
        resumed_count = first_count + 17
        if len(log.read_text().splitlines()) != resumed_count:
            raise SystemExit("resume did not skip completed actors and restart the partial actor")
        subprocess.run(interrupted_command, check=True, timeout=30)
        if len(log.read_text().splitlines()) != resumed_count:
            raise SystemExit("second resume reran completed actors")

        legacy = root / "legacy"
        legacy.mkdir()
        (legacy / "partial.jsonl").write_text("partial\n")
        signature = {"signature_version":1}
        expect_failure(lambda: evaluator.acquire_output(legacy, signature),
                       "no experiment signature")

        identity = {"checkpoint":"model", "checkpoint_revision":"rev",
                    "prompt_version":"prompt", "protocol_version":"proto",
                    "proxy_source_sha256":"a" * 64}
        request = {"protocol_version":"proto", "prompt_version":"prompt", "timestamp":1}
        request_hash = hashlib.sha256(json.dumps(
            request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        row = {"type":"laya_typed_choice", "model":"model", "checkpoint_revision":"rev",
               "prompt_version":"prompt", "protocol_version":"proto", "request":request,
               "proxy_source_sha256":"a" * 64, "request_hash":request_hash}
        cassette = root / "cassette.jsonl"
        cassette.write_text(json.dumps(row) + "\n")
        if evaluator.validate_cassette(cassette, identity) != 1 or "request_id" in request:
            raise SystemExit("cassette validation mutated request or rejected exact provenance")
        changed = dict(row, prompt_version="other")
        cassette.write_text(json.dumps(changed) + "\n")
        expect_failure(lambda: evaluator.validate_cassette(cassette, identity),
                       "prompt_version")
        changed = dict(row, proxy_source_sha256="b" * 64)
        cassette.write_text(json.dumps(changed) + "\n")
        expect_failure(lambda: evaluator.validate_cassette(cassette, identity),
                       "proxy_source_sha256")

        class FakeStream:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def readline(self):
                return json.dumps({"model":"model", "checkpoint_revision":"rev",
                                   "prompt_version":"prompt", "protocol_version":"proto",
                                   "proxy_source_sha256":"b" * 64}).encode() + b"\n"

        class FakeConnection:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def settimeout(self, _): pass
            def sendall(self, _): pass
            def makefile(self, _): return FakeStream()

        with mock.patch.object(evaluator.socket, "create_connection",
                               return_value=FakeConnection()):
            expect_failure(lambda: evaluator.verify_live_laya_identity(8743, identity),
                           "identity does not match")
    print("long_horizon_eval_resumability_smoke: PASS")


if __name__ == "__main__":
    main()
