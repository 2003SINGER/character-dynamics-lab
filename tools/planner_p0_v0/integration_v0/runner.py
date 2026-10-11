"""Bounded Sabre -> existing P3 HTN refinement -> native integration runner.

This runner never starts/stops the Evennia server. Sabre plans the fixture
domain; only `deliver_shelter` is refined by the existing P3 GTPyhop planner.
Every refined primitive is separately sent to native Evennia and recorded.
"""
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
from tools.native_platform_v0.p3.planning import plan_next
from tools.planner_p0_v0.integration_v0.monitor import (
    classify_native_step, classify_planner_result, evaluate_native_trace,
)
from tools.planner_p0_v0.integration_v0.sabre_export import export_problem, _delivery_costs
from tools.native_platform_v0.p3 import planning as p3_planning

EVIDENCE = ROOT / "02_实验/Planner_P0_Integration_v0/runs"
SABRE_EVIDENCE = ROOT / "02_实验/Planner_P0_v0/sabre_baseline/evidence/integration-v0"
WRAPPER = ROOT / "tools/planner_p0_v0/sabre_baseline/runner.py"
JDK = ROOT / "_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java"
SABRE_CLASSPATH = ROOT / "_local_data/planner_p0_v0/sabre/bin"
MAX_REPLANS = 40
MAX_PRIMITIVES_PER_MACRO = 12
MAX_VISITED = 200
MAX_GENERATED = 5000
SEARCH_MS = 5000
PROCESS_TIMEOUT_S = 12


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("run id must be a bounded slug")
    return value


def _plan(snapshot: dict, run_dir: Path, run_id: str, index: int,
          *, meeting_witness: bool = False) -> dict:
    problem = export_problem(snapshot, run_dir / f"problem-{index:02d}.txt",
                             meeting_witness=meeting_witness)
    sabre_run = _slug(f"{run_id}-s{index:02d}")
    command = [sys.executable, str(WRAPPER), "--problem", str(problem),
               "--run-id", sabre_run, "--output-root", str(SABRE_EVIDENCE / run_id),
               "--java", str(JDK), "--classpath", str(SABRE_CLASSPATH),
               "--planner-version", "Sabre v0.8.0", "--method", "bf", "--cost", "t",
               "--heuristic", "h+", "--epistemic-limit", "1", "--max-visited", str(MAX_VISITED),
               "--max-generated", str(MAX_GENERATED), "--time-limit-ms", str(SEARCH_MS),
               "--process-timeout-s", str(PROCESS_TIMEOUT_S), "--character-limit", "2",
               "--stack-size", "8m", "--goal-utility", "1", "--author-limit", "24"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               check=False, timeout=PROCESS_TIMEOUT_S + 3)
    parsed = None
    for line in reversed(completed.stdout.splitlines()):
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(parsed, dict):
        parsed = {"status": "WRAPPER_ERROR", "plan_actions": [],
                  "native_result": "wrapper returned no JSON result"}
    parsed.update({"wrapper_exit_code": completed.returncode,
                   "wrapper_stderr": completed.stderr[-3000:],
                   "problem": str(problem), "problem_sha256": _sha(problem),
                   "sabre_command": command})
    return parsed


def _parse_token(token: str) -> tuple[str, list[str]]:
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", token.strip())
    if not match:
        raise ValueError(f"unsupported Sabre action token: {token!r}")
    raw = match.group(2)
    return match.group(1), [] if not raw else [part.strip() for part in raw.split(",")]


def _room_alias(snapshot: dict, room_id: int) -> str:
    for name, value in snapshot["rooms"].items():
        if int(value) == int(room_id):
            return name
    raise ValueError("plan referred to a room outside the integration fixture")


def _step(call_rpc, scene_id: str, request_id: str, driver: str, action: dict) -> dict:
    return call_rpc("step_p0_integration_v0", {"scene_id": scene_id,
            "request_id": request_id, "driver": driver, "action": action})


def _has_meeting_receipt(trace: dict) -> bool:
    return any(isinstance(e, dict) and e.get("event_type") == "MEETING_WITNESS"
               and e.get("source") == "native_meet_command" and e.get("accepted") is True
               and e.get("settled") is True and e.get("receipt_id")
               for e in trace.get("events", []))


def _drain_evaluation_clock(call_rpc, scene_id: str, run_id: str, driver: str,
                            steps: list, snapshot: dict) -> dict:
    """Stop story actions after a real witness, then settle the fixed 24-min window."""
    while snapshot["clock"]["now"] < 24:
        result = _step(call_rpc, scene_id,
                       f"{run_id}-evaluation-wait-{snapshot['clock']['now']:02d}",
                       driver, {"kind": "wait", "actor": "A"})
        steps.append({"phase": "EVALUATION_CLOCK_DRAIN", "native": result,
                      "non_agency_evaluation_only": True})
        if not result.get("settled"):
            raise RuntimeError("evaluation clock drain wait did not settle natively")
        snapshot = result.get("post") or call_rpc("snapshot_p0_integration_v0",
                                                   {"scene_id": scene_id})["snapshot"]
    return snapshot


def _run_macro(call_rpc, *, scene_id: str, run_id: str, snapshot: dict,
               driver: str, steps: list, inject_route_repair: bool,
               state: dict) -> tuple[dict, bool, bool]:
    repairs, injected, macro_deviation = 0, False, False
    start_minute = snapshot["clock"]["now"]
    start_room = _room_alias(snapshot, snapshot["actors"]["A"]["room_id"])
    predicted_duration = _delivery_costs(snapshot).get(start_room)
    for primitive_index in range(MAX_PRIMITIVES_PER_MACRO):
        actor = snapshot["actors"]["A"]
        task = actor.get("active_task")
        if not task or task.get("status") not in {"accepted", "active", "blocked"}:
            raise RuntimeError("deliver_shelter requested without a live accepted task")
        local_view = actor.get("local_view")
        if not local_view or not local_view.get("observation", {}).get("task_item"):
            raise RuntimeError("A has no task-bound local view for existing P3 refinement")
        before_progress = (task.get("task_id"), task.get("progress_seq"),
                           task.get("held"), task.get("status"))
        intent = plan_next(local_view, "deliver_supply", max_visits=500, wall_seconds=0.25,
                           respect_local_traversability=False)
        steps.append({"phase": "htn_proposal", "snapshot_minute": snapshot["clock"]["now"],
                      "task_id": task.get("task_id"), "task_progress_before": before_progress,
                      "proposal": intent, "prediction_only": True})
        if intent.get("status") == "BUDGET":
            raise RuntimeError("P3 HTN search budget exhausted")
        plan = intent.get("plan", [])
        if intent.get("status") != "SOLVED" or not plan:
            if task.get("status") == "settled":
                break
            raise RuntimeError(f"P3 HTN did not return a primitive: {intent.get('status')}")
        primitive = plan[0]
        pre = snapshot
        if (inject_route_repair and not injected and primitive["operator"] == "move"
                and _room_alias(snapshot, primitive["destination_id"]) == "inn"
                and snapshot["actors"]["A"]["room_id"] == snapshot["rooms"]["junction"]):
            mutation = call_rpc("inject_p0_integration_mutation_v0", {
                "scene_id": scene_id, "request_id": f"{run_id}-mutation-block-main",
                "kind": "block_route", "route": "main"})
            state["mutations"].append({"phase": "before_current_htn_move_dispatch",
                                       "htn_intent": primitive, "native": mutation})
            injected = True
            snapshot = call_rpc("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
        source = _room_alias(snapshot, snapshot["actors"]["A"]["room_id"])
        if primitive["operator"] == "move":
            action = {"kind": "move", "actor": "A", "from": source,
                      "to": _room_alias(snapshot, primitive["destination_id"])}
        elif primitive["operator"] == "get":
            action = {"kind": "get", "actor": "A", "item": "shelter_kit"}
        elif primitive["operator"] == "drop":
            action = {"kind": "drop", "actor": "A", "item": "shelter_kit", "to": "inn"}
        else:
            raise ValueError(f"P3 returned an unregistered primitive: {primitive}")
        result = _step(call_rpc, scene_id, f"{run_id}-primitive-{primitive_index:02d}-{secrets.token_hex(2)}",
                       driver, action)
        steps.append({"phase": "native_htn_primitive", "primitive": primitive,
                      "action": action, "native": result,
                      "classification": classify_native_step(result),
                      "task_id": task.get("task_id"), "progress_before": before_progress})
        snapshot = result.get("post", call_rpc("snapshot_p0_integration_v0",
                                               {"scene_id": scene_id})["snapshot"])
        post_task = snapshot["actors"]["A"].get("active_task") or {}
        after_progress = (post_task.get("task_id"), post_task.get("progress_seq"),
                          post_task.get("held"), post_task.get("status"))
        if not result.get("settled"):
            repairs += 1
            if repairs > 4:
                raise RuntimeError("native HTN repair cap reached after unsettled primitive")
        if after_progress[0] != before_progress[0]:
            raise RuntimeError("native repair changed accepted task identity")
        if before_progress[2] and not after_progress[2] and result.get("settled"):
            if primitive["operator"] != "drop" or snapshot["items"]["shelter_kit"].get("location_id") != snapshot["rooms"]["inn"]:
                raise RuntimeError("held kit changed outside a settled native drop at the inn")
        if not result.get("settled"):
            macro_deviation = True
        if post_task.get("status") == "settled":
            actual_duration = snapshot["clock"]["now"] - start_minute
            if predicted_duration is None or actual_duration != predicted_duration:
                macro_deviation = True
                steps.append({"phase": "TEMPORAL_REBASE", "expected_macro_minutes": predicted_duration,
                              "actual_macro_minutes": actual_duration, "task_retained": post_task.get("task_id"),
                              "reason": "native primitive count differs from Sabre cost forecast"})
            return snapshot, injected, macro_deviation
    raise RuntimeError("HTN macro exceeded primitive cap without settled delivery")


def run_case(case: str, *, seed: int = 0, call_rpc=None) -> dict:
    cases = {"direct-clean": "direct", "route-repair": "direct",
             "high-causal-replan": "direct", "conditional-consent-smoke": "conditional",
             "free-acl-negative": "free"}
    if case not in cases:
        raise ValueError(f"case must be one of {sorted(cases)}")
    _slug(case)
    call_rpc = call_rpc or rpc_call
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = _slug(f"p0i-{case}-{stamp}-{secrets.token_hex(3)}")
    run_dir = EVIDENCE / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    mode = cases[case]
    driver = "direct_driver" if mode == "direct" else "trusted_driver" if mode == "conditional" else None
    record = {"schema": "planner-p0-integration-v0", "run_id": run_id, "case": case,
              "mode": mode, "classification": "INCOMPLETE", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "configuration": {"seed": seed, "sabre": "v0.8.0", "method": "bf", "cost": "t",
                  "heuristic": "h+", "max_visited": MAX_VISITED, "max_generated": MAX_GENERATED,
                  "native_time_limit_ms": SEARCH_MS, "wrapper_process_timeout_s": PROCESS_TIMEOUT_S,
                  "java_stack_size": "8m", "p3_goal": "deliver_supply", "p3_budget": {"visits": 500, "wall_seconds": 0.25},
                  "driver_semantics": {"direct": "authorized joint control, not independent agency",
                                       "conditional": "fixed own-goal offer gate plus trusted controller; not autonomous NPC",
                                       "free": "author/direct-driver ACL negative control; no autonomous loop tested"}},
              "source_sha256": {str(path.relative_to(ROOT)): _sha(path) for path in (
                  Path(__file__), Path(__file__).with_name("sabre_export.py"),
                  Path(__file__).with_name("monitor.py"), Path(p3_planning.__file__),
                  ROOT / "tools/planner_p0_v0/sabre_baseline/runner.py",
                  ROOT / "tools/planner_p0_v0/integration_v0/contract.py",
                  ROOT / "tools/native_platform_v0/p3/mcp_stdio.py",
                  ROOT / "tools/native_platform_v0/p3/control_service.py",
                  ROOT / "tools/planner_p0_v0/integration_v0/native_world.py",
                  ROOT / "tools/planner_p0_v0/integration_v0/audit_readback.py")},
              "planner_runs": [], "steps": [], "mutations": [], "status": "INCOMPLETE"}
    scene_id = None
    try:
        scene_data = call_rpc("reset_p0_integration_v0", {"mode": mode, "seed": seed,
                                                            "accept_task": True})
        scene = scene_data.get("scene", scene_data)
        scene_id = scene["scene_id"]
        record["scene"] = scene
        mutated = False
        for iteration in range(1, MAX_REPLANS + 1):
            snapshot = call_rpc("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
            trace_result = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
            live_trace = trace_result.get("trace", trace_result)
            if _has_meeting_receipt(live_trace):
                snapshot = _drain_evaluation_clock(call_rpc, scene_id, run_id, driver,
                                                   record["steps"], snapshot)
                trace_result = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
                live_trace = trace_result.get("trace", trace_result)
                live_monitor = evaluate_native_trace(live_trace)
                record["steps"].append({"phase": "FINAL_TYPED_EVALUATION",
                                        "minute": snapshot["clock"]["now"],
                                        "typed_monitor": live_monitor})
                record["typed_monitor"] = live_monitor
                record["native_trace"] = live_trace
                record["status"] = "COMPLETED" if live_monitor["status"] == "SATISFIED" else "GOAL_" + live_monitor["status"]
                break
            live_monitor = evaluate_native_trace(live_trace)
            record["steps"].append({"phase": "RECEDING_HORIZON_CHECK", "iteration": iteration,
                                    "minute": snapshot["clock"]["now"], "typed_monitor": live_monitor})
            if live_monitor["status"] == "SATISFIED":
                record["status"] = "COMPLETED"
                record["typed_monitor"] = live_monitor
                record["native_trace"] = live_trace
                break
            witness = any(e.get("event_type") == "MEETING_WITNESS"
                          and e.get("source") == "native_meet_command"
                          and e.get("settled") is True and e.get("receipt_id")
                          for e in live_trace.get("events", []))
            problem = _plan(snapshot, run_dir, run_id, iteration, meeting_witness=witness)
            record["planner_runs"].append(problem)
            status = classify_planner_result(problem)
            if problem.get("status") != "SUCCESS":
                record["status"] = status
                if case == "free-acl-negative" and problem.get("status") == "NATIVE_NO_SOLUTION":
                    denied = _step(call_rpc, scene_id, f"{run_id}-acl-probe",
                                   "author", {"kind": "cloud_seed"})
                    record["steps"].append({"phase": "acl_negative_control", "native": denied,
                                            "classification": classify_native_step(denied)})
                    record["status"] = "FREE_DOMAIN_NO_PLAN_AND_NATIVE_ACL_DENIED"
                break
            tokens = problem.get("plan_actions", [])
            if not tokens:
                record["status"] = "SABRE_SUCCESS_WITH_EMPTY_PLAN"
                break
            token = tokens[0]
            name, args = _parse_token(token)
            if name == "deliver_shelter":
                if len(args) != 1 or args[0] not in {"Junction", "SidePassage", "Inn"}:
                    raise ValueError(f"invalid grounded deliver_shelter token: {token}")
                actual_source = _room_alias(snapshot, snapshot["actors"]["A"]["room_id"])
                if {"Junction": "junction", "SidePassage": "side_passage", "Inn": "inn"}[args[0]] != actual_source:
                    raise ValueError("Sabre macro source does not match authoritative A position")
                snapshot, injected, deviated = _run_macro(
                    call_rpc, scene_id=scene_id, run_id=f"{run_id}-m{iteration}",
                    snapshot=snapshot, driver=driver, steps=record["steps"],
                    inject_route_repair=(case == "route-repair" and not mutated), state=record)
                mutated = mutated or injected
                if deviated:
                    record["steps"].append({"phase": "TEMPORAL_REBASE",
                                            "reason": "native macro settlement differed from symbolic expected primitive prefix",
                                            "task_retained": snapshot["actors"]["A"].get("active_task", {}).get("task_id")})
                continue
            if name == "cloud_seed":
                action = {"kind": "cloud_seed"}; driver_now = "author"
            elif name == "offer_task":
                action = {"kind": "offer_task", "actor": "A", "task": "deliver_shelter"}; driver_now = "author"
            elif name == "dispatch_task":
                action = {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"}; driver_now = "author"
            elif name == "wait" and len(args) == 1 and args[0] in {"A", "B"}:
                action = {"kind": "wait", "actor": args[0]}; driver_now = driver
            elif name == "look" and len(args) == 1 and args[0] in {"A", "B"}:
                action = {"kind": "look", "actor": args[0]}; driver_now = driver
            elif name == "move" and len(args) == 3:
                rooms = {"Junction": "junction", "SidePassage": "side_passage", "Inn": "inn"}
                if args[0] not in {"A", "B"} or args[1] not in rooms or args[2] not in rooms:
                    raise ValueError(f"invalid grounded move token {token}")
                action = {"kind": "move", "actor": args[0], "from": rooms[args[1]], "to": rooms[args[2]]}
                driver_now = driver
            elif name == "meet" and not args:
                action = {"kind": "meet", "actors": ["A", "B"]}; driver_now = driver
            else:
                raise ValueError(f"Sabre action outside registered integration-v0 grounding: {token}")
            native = _step(call_rpc, scene_id, f"{run_id}-atom-{iteration:02d}", driver_now, action)
            record["steps"].append({"phase": "sabre_atomic_action", "token": token,
                                    "action": action, "native": native,
                                    "classification": classify_native_step(native)})
            if not native.get("accepted") and case == "high-causal-replan" and name == "cloud_seed":
                raise RuntimeError("cloud seed was not accepted; refusing to claim high causal repair")
            if case == "high-causal-replan" and name == "cloud_seed" and not mutated:
                if native.get("settled"):
                    before_mutation = native.get("post")
                    mutation = call_rpc("inject_p0_integration_mutation_v0", {
                        "scene_id": scene_id, "request_id": f"{run_id}-dissipate-cloud",
                        "kind": "dissipate_cloud"})
                    after_mutation = call_rpc("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
                    record["mutations"].append({"phase": "CAUSAL_REPAIR", "cause": "pending_cloud_dissipated",
                                                "native": mutation, "snapshot_before": before_mutation,
                                                "snapshot_after": after_mutation,
                                                "task_id_preserved": after_mutation["actors"]["A"].get("active_task", {}).get("task_id")})
                    mutated = True
            if not native.get("accepted") and native.get("code") == "ACL_DENIED":
                record["status"] = "NATIVE_ACL_DENIED"
                break
            if name == "meet" and native.get("settled"):
                fresh = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
                fresh_trace = fresh.get("trace", fresh)
                if _has_meeting_receipt(fresh_trace):
                    fresh_snapshot = call_rpc("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
                    _drain_evaluation_clock(call_rpc, scene_id, run_id, driver,
                                            record["steps"], fresh_snapshot)
                    final = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
                    final_trace = final.get("trace", final)
                    record["native_trace"] = final_trace
                    record["typed_monitor"] = evaluate_native_trace(final_trace)
                    record["status"] = ("COMPLETED" if record["typed_monitor"]["status"] == "SATISFIED"
                                         else "GOAL_" + record["typed_monitor"]["status"])
                    record["steps"].append({"phase": "FINAL_TYPED_EVALUATION", "minute": 24,
                                            "typed_monitor": record["typed_monitor"]})
                    break
        else:
            record["status"] = "REPLAN_LIMIT"
        trace_result = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
        trace = trace_result.get("trace", trace_result)
        record["native_trace"] = trace
        record["typed_monitor"] = evaluate_native_trace(trace)
        if record["status"] == "INCOMPLETE":
            record["status"] = "COMPLETED" if record["typed_monitor"]["status"] == "SATISFIED" else "GOAL_" + record["typed_monitor"]["status"]
        record["classification"] = record["status"]
    except Exception as exc:
        record["status"] = "FAILED"
        record["failure"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
        if scene_id:
            try:
                raw = call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id})
                record["partial_trace"] = raw.get("trace", raw)
            except Exception as trace_exc:
                record["partial_trace_error"] = type(trace_exc).__name__
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return {"run_id": run_id, "run_dir": str(run_dir), "scene_id": scene_id,
            "status": record["status"], "failure": record.get("failure"),
            "typed_monitor": record.get("typed_monitor")}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("direct-clean", "route-repair", "high-causal-replan",
                    "conditional-consent-smoke", "free-acl-negative"), required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = run_case(args.case, seed=args.seed)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] in {"COMPLETED", "FREE_DOMAIN_NO_PLAN_AND_NATIVE_ACL_DENIED"} else 2)
