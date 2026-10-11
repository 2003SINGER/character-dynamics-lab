"""Run the three registered, human-authored P0 control traces against live Evennia."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.native_platform_v0.p3.mcp_stdio import rpc_call
from tools.planner_p0_v0.shared_world.semantics import plan_cases

RUNS = ROOT / "02_实验/Planner_P0_v0/shared_world/runs"
CASES = ("clean", "mainblockedrepair", "allblockednegative")
MAX_SECONDS = 180
MAX_ACTIONS = 16


def _hash_sources():
    paths = ("tools/planner_p0_v0/shared_world/semantics.py",
             "tools/planner_p0_v0/shared_world/native_world.py",
             "tools/planner_p0_v0/shared_world/sabre_export.py",
             "tools/native_platform_v0/p3/control_service.py")
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def _action(case, scene_id, index, action):
    result = rpc_call("step_p0_shared_world", {
        "scene_id": scene_id, "request_id": f"{case}-step-{index:02d}", "action": action})
    return result


def run_case(case: str) -> dict:
    if case not in CASES:
        raise ValueError("case must be one of the three registered hand traces")
    started = time.monotonic()
    result = {"schema": "planner-p0-native-handtrace-v0", "case": case,
              "classification": "SCRIPTED_CONTROL_NOT_PLANNER_OUTPUT",
              "source_sha256": _hash_sources(), "steps": []}
    scene = rpc_call("reset_p0_shared_world", {"seed": 0})["scene"]
    scene_id = scene["scene_id"]
    result["scene"] = scene
    plans = plan_cases()
    if case == "clean":
        actions = plans["clean"]
        block_at = None
    elif case == "mainblockedrepair":
        actions = plans["mainblockedrepair"]
        block_at = 2
    else:
        actions = plans["allblockednegative"]
        block_at = 2
    if len(actions) > MAX_ACTIONS:
        raise RuntimeError("registered hand trace exceeded action cap")
    for idx, action in enumerate(actions, 1):
        if time.monotonic() - started > MAX_SECONDS:
            raise TimeoutError("P0 trace exceeded the 180-second watchdog")
        if block_at == idx - 1:
            blocked = rpc_call("inject_p0_route_block", {
                "scene_id": scene_id, "route": "main" if case == "mainblockedrepair" else "all",
                "request_id": f"{case}-testplayer-block"})
            result["steps"].append({"testplayer_intervention": blocked})
        result["steps"].append(_action(case, scene_id, idx, action))
    trace = rpc_call("get_p0_shared_world_trace", {"scene_id": scene_id})["trace"]
    result["trace"] = trace
    result["elapsed_wall_seconds"] = round(time.monotonic() - started, 3)
    state = trace["snapshot"]
    witnessed = bool(state["weather"] == "storm" and
                     "storm" in state["actors"]["B"]["known_weather"] and
                     state["actors"]["A"]["room"] == "inn" and
                     state["actors"]["B"]["room"] == "inn" and state["met"])
    expected = case != "allblockednegative"
    result["expected_author_goal"] = expected
    result["author_goal_witnessed"] = witnessed
    result["status"] = "COMPLETED_AS_EXPECTED" if witnessed == expected else "MISMATCH"
    RUNS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = RUNS / f"p0-handtrace-{case}-{stamp}-{secrets.token_hex(3)}.json"
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {"status": result["status"], "path": str(output), "scene_id": scene_id,
            "author_goal_witnessed": witnessed, "expected_author_goal": expected}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    args = parser.parse_args()
    print(json.dumps(run_case(args.case), ensure_ascii=False))
