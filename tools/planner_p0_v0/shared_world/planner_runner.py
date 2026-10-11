"""Run Sabre on a live P0 snapshot, then execute only its grounded native plan."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.native_platform_v0.p3.mcp_stdio import rpc_call
from tools.planner_p0_v0.shared_world.sabre_export import export_problem
from tools.planner_p0_v0.shared_world.semantics import predict_post

EVIDENCE = ROOT / "02_实验/Planner_P0_v0/shared_world/runs"
WRAPPER = ROOT / "tools/planner_p0_v0/sabre_baseline/runner.py"
MAX_SECONDS = 180
MAX_PLAN_ACTIONS = 32


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _grounded_action(token: str, state: dict) -> dict:
    match = re.fullmatch(r"([A-Za-z_][\w-]*)\((.*)\)", token.strip())
    if not match:
        raise ValueError("native plan contained an unsupported action token")
    name, raw = match.groups()
    args = [item.strip() for item in raw.split(",")]
    now = state["now"]
    expected_time = [f"H{now}", f"H{min(now + 1, state['deadline'])}"]
    if name in ("wait", "observe_weather") and len(args) == 3:
        if args[1:] != expected_time:
            raise ValueError("Sabre action clock does not match the live native snapshot")
        if args[0] not in ("A", "B"):
            raise ValueError("Sabre plan named an unregistered actor")
        return {"kind": name, "actor": args[0]}
    rooms = {"Junction": "junction", "SidePassage": "side_passage", "Inn": "inn"}
    if name == "move" and len(args) == 5:
        if args[3:] != expected_time or args[0] not in ("A", "B"):
            raise ValueError("Sabre move clock/actor does not match the live snapshot")
        if args[1] not in rooms or args[2] not in rooms:
            raise ValueError("Sabre move named a room outside the native fixture")
        return {"kind": "move", "actor": args[0], "from": rooms[args[1]], "to": rooms[args[2]]}
    if name == "meet" and len(args) == 2:
        if args != expected_time:
            raise ValueError("Sabre meet clock does not match the live native snapshot")
        return {"kind": "meet", "actors": ["A", "B"]}
    raise ValueError("Sabre plan action is outside the P0 registered operator set")


def _plan_from_snapshot(state: dict, run_dir: Path, run_id: str) -> dict:
    problem = export_problem(state, run_dir / f"{run_id}.txt")
    command = [sys.executable, str(WRAPPER), "--problem", str(problem),
               "--run-id", run_id, "--stack-size", "8m", "--method", "bf",
               "--cost", "t", "--heuristic", "h+", "--epistemic-limit", "1",
               "--max-visited", "200", "--max-generated", "5000",
               "--time-limit-ms", "5000", "--process-timeout-s", "12",
               "--author-limit", "48", "--goal-utility", "1"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               check=False, timeout=20)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    parsed = json.loads(lines[-1]) if lines else {
        "status": "WRAPPER_ERROR", "native_result": "wrapper emitted no JSON result",
        "plan_actions": []}
    parsed["wrapper_exit_code"] = completed.returncode
    if completed.stderr:
        parsed["wrapper_stderr"] = completed.stderr[-4000:]
    parsed["problem_path"] = str(problem)
    parsed["problem_sha256"] = _hash(problem)
    return parsed


def _rpc_step(case, scene_id, index, action, state):
    predicted = predict_post(state, action)
    result = rpc_call("step_p0_shared_world", {
        "scene_id": scene_id, "request_id": f"{case}-planner-step-{index:02d}",
        "action": action, "predicted_post": predicted})
    if result.get("prediction_matches") is not True:
        raise AssertionError(f"predicted/native state mismatch at action {index}")
    if not result.get("accepted") or not result.get("settled"):
        raise AssertionError(f"Sabre action failed native settlement at action {index}")
    return result


def run_case(case: str) -> dict:
    if case not in ("clean", "mainblockedrepair", "allblockednegative"):
        raise ValueError("case must be clean, mainblockedrepair, or allblockednegative")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"p0-sabre-{case}-{stamp}-{secrets.token_hex(3)}"
    run_dir = EVIDENCE / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = {"schema": "planner-p0-sabre-native-v0", "run_id": run_id,
              "case": case, "classification": "ORIGINAL_SABRE_PLAN_EXECUTED_IN_NATIVE_EVENNIA",
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": {p: _hash(ROOT / p) for p in (
                  "tools/planner_p0_v0/shared_world/semantics.py",
                  "tools/planner_p0_v0/shared_world/native_world.py",
                  "tools/planner_p0_v0/shared_world/sabre_export.py",
                  "tools/planner_p0_v0/shared_world/planner_runner.py",
                  "tools/native_platform_v0/p3/control_service.py")},
              "steps": [], "planner_runs": [], "status": "INCOMPLETE"}
    (run_dir / "config.json").write_text(json.dumps({
        "case": case, "scene": "registered three-room P0 fixture", "seed": 0,
        "deadline_hours": 48, "storm_at_hour": 2,
        "control_mode": "explicit_joint_orchestration",
        "prefix_policy": "first_two_actions_from_original_clean_Sabre_plan_then_testplayer_route_block",
        "planner": {"version": "Sabre v0.8.0", "java_stack_size": "8m",
                    "method": "bf", "cost": "t", "heuristic": "h+",
                    "epistemic_limit": 1, "max_visited": 200,
                    "max_generated": 5000, "time_limit_ms": 5000,
                    "author_limit": 48, "goal_utility": 1}},
        ensure_ascii=False, indent=2) + "\n")
    scene_id = None
    failure = None
    try:
        scene = rpc_call("reset_p0_shared_world", {"seed": 0})["scene"]
        scene_id = scene["scene_id"]
        record["scene"] = scene
        state = rpc_call("snapshot_p0_shared_world", {"scene_id": scene_id})["snapshot"]

        first = _plan_from_snapshot(state, run_dir, f"{run_id}-initial")
        record["planner_runs"].append(first)
        if first.get("status") != "SUCCESS":
            record["status"] = "PLANNER_" + str(first.get("status", "UNKNOWN"))
        else:
            tokens = first.get("plan_actions", [])
            if not tokens or len(tokens) > MAX_PLAN_ACTIONS:
                raise ValueError("Sabre returned an empty or over-cap plan")
            prefix_count = 2 if case != "clean" else len(tokens)
            for idx, token in enumerate(tokens[:prefix_count], 1):
                action = _grounded_action(token, state)
                step = _rpc_step(case, scene_id, idx, action, state)
                record["steps"].append({"phase": "original_plan_prefix", "token": token,
                                        "action": action, "native": step})
                state = step["post"]

            if case != "clean":
                route = "main" if case == "mainblockedrepair" else "all"
                blocked = rpc_call("inject_p0_route_block", {
                    "scene_id": scene_id, "route": route,
                    "request_id": f"{case}-testplayer-block-at-sealed-prefix"})
                record["steps"].append({"phase": "testplayer_intervention", "native": blocked})
                state = blocked["post"]
                replanned = _plan_from_snapshot(state, run_dir, f"{run_id}-after-block")
                record["planner_runs"].append(replanned)
                if replanned.get("status") == "SUCCESS":
                    tokens = replanned.get("plan_actions", [])
                    if len(tokens) > MAX_PLAN_ACTIONS:
                        raise ValueError("Sabre replan exceeded the registered action cap")
                    for idx, token in enumerate(tokens, 1):
                        action = _grounded_action(token, state)
                        step = _rpc_step(case, scene_id, idx, action, state)
                        record["steps"].append({"phase": "native_replan", "token": token,
                                                "action": action, "native": step})
                        state = step["post"]
                else:
                    record["status"] = "REPLAN_" + str(replanned.get("status", "UNKNOWN"))

        if scene_id:
            record["trace"] = rpc_call("get_p0_shared_world_trace", {"scene_id": scene_id})["trace"]
        state = record.get("trace", {}).get("snapshot", state)
        witnessed = bool(state["weather"] == "storm" and
                         "storm" in state["actors"]["B"]["known_weather"] and
                         state["actors"]["A"]["room"] == "inn" and
                         state["actors"]["B"]["room"] == "inn" and state["met"])
        record["author_goal_witnessed"] = witnessed
        if case in ("clean", "mainblockedrepair"):
            if witnessed:
                record["status"] = "COMPLETED"
            elif record["status"] == "INCOMPLETE":
                record["status"] = "GOAL_NOT_WITNESSED"
        elif record["status"] == "INCOMPLETE" and witnessed:
            record["status"] = "NEGATIVE_CASE_UNEXPECTEDLY_WITNESSED"
        elif record["status"] == "INCOMPLETE":
            record["status"] = "NEGATIVE_CASE_NO_WITNESS"
        record["elapsed_wall_seconds"] = round(time.monotonic() - started, 3)
    except Exception as error:  # Persist partial, non-secret evidence before returning failure.
        failure = {"type": type(error).__name__, "message": str(error)[:1000]}
        record["failure"] = failure
        record["status"] = "FAILED"
        if scene_id:
            try:
                record["partial_trace"] = rpc_call(
                    "get_p0_shared_world_trace", {"scene_id": scene_id})["trace"]
            except Exception as trace_error:
                record["partial_trace_error"] = type(trace_error).__name__
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["elapsed_wall_seconds"] = round(time.monotonic() - started, 3)
        (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return {"status": record["status"], "run_dir": str(run_dir), "scene_id": scene_id,
            "author_goal_witnessed": record.get("author_goal_witnessed"),
            "failure": failure}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("clean", "mainblockedrepair", "allblockednegative"), required=True)
    args = parser.parse_args()
    result = run_case(args.case)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] in ("COMPLETED", "NEGATIVE_CASE_NO_WITNESS") else 2)
