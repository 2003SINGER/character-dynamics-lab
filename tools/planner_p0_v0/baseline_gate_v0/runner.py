"""Run matched bounded baseline-gate cases with atomic Sabre (A) or HTN (B)."""
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
from tools.planner_p0_v0.integration_v0 import runner as frozen
from tools.planner_p0_v0.integration_v0.monitor import (
    classify_native_step, classify_planner_result, evaluate_native_trace,
)
from tools.planner_p0_v0.baseline_gate_v0.sabre_export import export_problem

RUN_ROOT = ROOT / "02_实验/Planner_P0_Baseline_Gate_v0/runs"
SABRE_ROOT = ROOT / "02_实验/Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0"
CASES = {"direct-clean", "route-repair", "high-causal-replan"}
VARIANTS = {"A", "B"}
VISITED, GENERATED, SEARCH_MS, PROCESS_TIMEOUT = 200, 5000, 5000, 12


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
    return digest.hexdigest()


def _slug(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("run ids must be bounded path-safe slugs")
    return value


def _rpc_meter(call, metrics):
    def wrapped(name, args):
        if name == "inject_p0_integration_mutation_v0":
            pre = wrapped("snapshot_p0_integration_v0", {"scene_id": args["scene_id"]})["snapshot"]
            started = time.perf_counter()
            result = call(name, args)
            metrics["rpc_calls"] += 1
            metrics["rpc_wall_ms"] += (time.perf_counter() - started) * 1000
            post = wrapped("snapshot_p0_integration_v0", {"scene_id": args["scene_id"]})["snapshot"]
            metrics["mutation_boundaries"].append({"kind": args["kind"], "pre": pre,
                                                    "result": result, "post": post})
            return result
        started = time.perf_counter()
        try:
            if name == "step_p0_integration_v0":
                metrics["native_action_calls"] += 1
            return call(name, args)
        finally:
            metrics["rpc_calls"] += 1
            metrics["rpc_wall_ms"] += (time.perf_counter() - started) * 1000
    return wrapped


def _plan(snapshot, variant, run_dir, run_id, index, metrics):
    started = time.perf_counter()
    problem = export_problem(snapshot, variant, run_dir / f"problem-{index:02d}.txt")
    metrics["problem_export_wall_ms"] += (time.perf_counter() - started) * 1000
    native_run_id = _slug(f"{run_id}-{variant.lower()}-{index:02d}")
    command = [sys.executable, str(ROOT / "tools/planner_p0_v0/sabre_baseline/runner.py"),
               "--problem", str(problem), "--run-id", native_run_id,
               "--output-root", str(SABRE_ROOT / run_id),
               "--java", str(ROOT / "_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java"),
               "--classpath", str(ROOT / "_local_data/planner_p0_v0/sabre/bin"),
               "--planner-version", "Sabre v0.8.0", "--method", "bf", "--cost", "t",
               "--heuristic", "h+", "--epistemic-limit", "1", "--max-visited", str(VISITED),
               "--max-generated", str(GENERATED), "--time-limit-ms", str(SEARCH_MS),
               "--process-timeout-s", str(PROCESS_TIMEOUT), "--character-limit", "2",
               "--stack-size", "8m", "--goal-utility", "1", "--author-limit", "24"]
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              check=False, timeout=PROCESS_TIMEOUT + 3)
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code = None
    wrapper_wall = (time.perf_counter() - started) * 1000
    metrics["wrapper_wall_ms"] += wrapper_wall
    result = None
    for line in reversed(stdout.splitlines()):
        try:
            result = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if result is None:
        result = {"status": "PROCESS_TIMEOUT" if exit_code is None else "WRAPPER_ERROR",
                  "plan_actions": [], "native_result": "no wrapper JSON result"}
    result.update({"variant": variant, "wrapper_exit_code": exit_code,
                   "wrapper_wall_ms": wrapper_wall, "wrapper_stderr": stderr,
                   "problem_path": str(problem), "problem_sha256": _hash(problem),
                   "command": command})
    metrics["sabre_plan_calls"] += 1
    metrics["sabre_visited"] += result.get("nodes_visited") or 0
    metrics["sabre_generated"] += result.get("nodes_generated") or 0
    metrics["sabre_native_search_ms"] += result.get("elapsed_native_ms") or 0
    metrics["sabre_results"].append({k: result.get(k) for k in
        ("status", "nodes_visited", "nodes_generated", "elapsed_native_ms", "utility_achieved")})
    return result


def _action_for_atomic(name, args, snapshot):
    rooms = {"Junction": "junction", "SidePassage": "side_passage", "Inn": "inn"}
    if name == "get_shelter_kit" and len(args) == 1 and args[0] in rooms:
        return {"kind": "get", "actor": "A", "item": "shelter_kit"}, "direct_driver"
    if name == "drop_shelter_kit" and not args:
        return {"kind": "drop", "actor": "A", "item": "shelter_kit", "to": "inn"}, "direct_driver"
    if name == "move" and len(args) == 3 and args[0] in {"A", "B"} and args[1] in rooms and args[2] in rooms:
        return {"kind": "move", "actor": args[0], "from": rooms[args[1]], "to": rooms[args[2]]}, "direct_driver"
    if name == "dispatch_task" and not args:
        return {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"}, "author"
    if name == "cloud_seed" and not args:
        return {"kind": "cloud_seed"}, "author"
    if name == "wait" and len(args) == 1 and args[0] in {"A", "B"}:
        return {"kind": "wait", "actor": args[0]}, "direct_driver"
    if name == "look" and len(args) == 1 and args[0] in {"A", "B"}:
        return {"kind": "look", "actor": args[0]}, "direct_driver"
    if name == "meet" and not args:
        return {"kind": "meet", "actors": ["A", "B"]}, "direct_driver"
    raise ValueError(f"unsupported baseline Sabre token: {name}({','.join(args)})")


def _has_witness(trace):
    return frozen._has_meeting_receipt(trace)


def _assert_main_observed_closed(snapshot):
    observation = snapshot["actors"]["A"].get("local_view", {}).get("observation", {})
    known = observation.get("known_traversability", {})
    junction = str(snapshot["rooms"]["junction"])
    inn = str(snapshot["rooms"]["inn"])
    if known.get(junction, {}).get(inn) is not False:
        raise RuntimeError("A did not observe the main route closed after its failed move")


def run_case(case: str, variant: str, *, seed: int = 0, call_rpc=None) -> dict:
    if case not in CASES or variant not in VARIANTS:
        raise ValueError(f"case must be one of {sorted(CASES)}; variant must be A or B")
    call = call_rpc or rpc_call
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = _slug(f"p0bg-{case}-{variant}-{stamp}-{secrets.token_hex(3)}")
    out = RUN_ROOT / run_id
    out.mkdir(parents=True, exist_ok=False)
    metrics = {"sabre_plan_calls": 0, "sabre_visited": 0, "sabre_generated": 0,
               "sabre_native_search_ms": 0.0, "wrapper_wall_ms": 0.0,
               "problem_export_wall_ms": 0.0, "rpc_calls": 0, "rpc_wall_ms": 0.0,
               "native_action_calls": 0, "htn_proposal_calls": 0,
               "mutation_boundaries": [],
               "htn_method_action_visits": 0, "htn_refinement_and_native_wall_ms": 0.0,
               "sabre_results": []}
    metered_call = _rpc_meter(call, metrics)
    source_paths = [Path(__file__), Path(__file__).with_name("sabre_export.py"),
                    ROOT / "tools/planner_p0_v0/integration_v0/runner.py",
                    ROOT / "tools/planner_p0_v0/integration_v0/sabre_export.py",
                    ROOT / "tools/planner_p0_v0/integration_v0/monitor.py",
                    ROOT / "tools/planner_p0_v0/integration_v0/contract.py",
                    ROOT / "tools/planner_p0_v0/integration_v0/native_world.py",
                    ROOT / "tools/planner_p0_v0/integration_v0/audit_readback.py",
                    ROOT / "tools/native_platform_v0/p3/planning.py",
                    ROOT / "tools/native_platform_v0/p3/control_service.py",
                    ROOT / "tools/native_platform_v0/p3/mcp_stdio.py",
                    ROOT / "tools/planner_p0_v0/sabre_baseline/runner.py"]
    record = {"schema": "planner-p0-baseline-gate-v0", "run_id": run_id,
              "case": case, "variant": variant, "seed": seed,
              "comparison_note": "A atomic Sabre vs B Sabre macro + existing P3 HTN; not equal search-depth units",
              "status": "INCOMPLETE", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "configuration": {"sabre": "v0.8.0", "sabre_checkout_revision": "73a128123b10a57843068b69d0b0e0601f37488a",
                  "sabre_classpath_tree_sha256": _tree_hash(ROOT / "_local_data/planner_p0_v0/sabre/bin"),
                  "sabre_temporal_cost_source_sha256": _hash(ROOT / "_local_data/planner_p0_v0/sabre/src/main/java/edu/uky/cs/nil/sabre/prog/ProgressionCost.java"),
                  "java_runtime": "Temurin OpenJDK 17.0.20.1", "method": "bf", "cost": "t", "heuristic": "h+",
                  "max_visited_per_call": VISITED, "max_generated_per_call": GENERATED,
                  "native_time_limit_ms_per_call": SEARCH_MS, "wrapper_timeout_s_per_call": PROCESS_TIMEOUT,
                  "java_stack_size": "8m", "author_limit": 24, "character_limit": 2,
                  "p3_budget_per_proposal": {"visits": 500, "wall_seconds": 0.25},
                  "domain_difference": "A has atomic GET/MOVE/DROP; B has frozen delivery macro refined by P3 local-view HTN",
                  "cost_semantics": "Sabre cost t is native progression temporal-depth, not this world's minute fluent; author_limit 24 is symbolic depth, not world deadline",
                  "route_model": "both Sabre variants receive the same authorized full snapshot.routes projection",
                  "route_cost_model": "B macro duration uses manually priced W route costs; this does not make A and B observation architecture identical",
                  "driver": "direct_driver with author-only dispatch/cloud actions; authorized joint control, not independent agency"},
              "model_complexity": {"metric": "generated action declarations and maintained source LOC; no author-hours inferred",
                  "dependency_boundary": ["baseline_gate renderer", "frozen integration renderer/runner/monitor", "P3 planning", "Sabre v0.8.0 CLI"]},
              "source_sha256": {str(p.relative_to(ROOT)): _hash(p) for p in source_paths},
              "scene": None, "planner_runs": [], "steps": [], "mutations": [],
              "metrics": metrics}
    scene_id = None
    mutated = False
    start_wall = time.perf_counter()
    try:
        created = metered_call("reset_p0_integration_v0", {"mode": "direct", "seed": seed,
                                                              "accept_task": True})
        scene = created.get("scene", created)
        scene_id = scene["scene_id"]
        record["scene"] = scene
        for index in range(1, 41):
            snapshot = metered_call("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
            if index == 1:
                record["initial_snapshot"] = snapshot
            trace_result = metered_call("get_p0_integration_trace_v0", {"scene_id": scene_id})
            trace = trace_result.get("trace", trace_result)
            if _has_witness(trace):
                drain_started = time.perf_counter()
                drain_step_start = len(record["steps"])
                snapshot = frozen._drain_evaluation_clock(metered_call, scene_id, run_id,
                                                           "direct_driver", record["steps"], snapshot)
                metrics["evaluation_drain_wall_ms"] = (time.perf_counter() - drain_started) * 1000
                metrics["evaluation_drain_actions"] = sum(
                    1 for s in record["steps"][drain_step_start:]
                    if s.get("phase") == "EVALUATION_CLOCK_DRAIN")
                final_result = metered_call("get_p0_integration_trace_v0", {"scene_id": scene_id})
                record["native_trace"] = final_result.get("trace", final_result)
                record["typed_monitor"] = evaluate_native_trace(record["native_trace"])
                record["steps"].append({"phase": "FINAL_TYPED_EVALUATION", "minute": 24,
                                        "typed_monitor": record["typed_monitor"]})
                record["status"] = ("COMPLETED" if record["typed_monitor"]["status"] == "SATISFIED"
                                     else "GOAL_" + record["typed_monitor"]["status"])
                break
            t0 = time.perf_counter()
            problem = _plan(snapshot, variant, out, run_id, index, metrics)
            domain_text = Path(problem["problem_path"]).read_text(encoding="utf-8")
            record["model_complexity"].update({
                "generated_sabre_action_declarations": sum(
                    1 for line in domain_text.splitlines() if line.startswith("action ")),
                "variant_exporter_loc": len(Path(__file__).with_name("sabre_export.py").read_text().splitlines()),
                "frozen_exporter_loc": len((ROOT / "tools/planner_p0_v0/integration_v0/sabre_export.py").read_text().splitlines()),
                "existing_p3_planning_loc": len((ROOT / "tools/native_platform_v0/p3/planning.py").read_text().splitlines())})
            record["planner_runs"].append(problem)
            record["steps"].append({"phase": "SABRE_PLAN", "index": index,
                                    "snapshot_minute": snapshot["clock"]["now"],
                                    "variant": variant, "result": problem})
            if problem.get("status") != "SUCCESS":
                record["status"] = classify_planner_result(problem)
                break
            actions = problem.get("plan_actions", [])
            if not actions:
                record["status"] = "SUCCESS_EMPTY_PLAN"
                break
            name, args = frozen._parse_token(actions[0])
            if variant == "B" and name == "deliver_shelter":
                before_htn = time.perf_counter()
                before_steps = len(record["steps"])
                snapshot, injected, deviated = frozen._run_macro(
                    metered_call, scene_id=scene_id, run_id=f"{run_id}-m{index}",
                    snapshot=snapshot, driver="direct_driver", steps=record["steps"],
                    inject_route_repair=(case == "route-repair" and not mutated), state=record)
                metrics["htn_refinement_and_native_wall_ms"] += (time.perf_counter() - before_htn) * 1000
                metrics["b_macro_native_primitive_calls"] = metrics.get("b_macro_native_primitive_calls", 0) + sum(
                    1 for s in record["steps"][before_steps:]
                    if s.get("phase") == "native_htn_primitive")
                mutated = mutated or injected
                proposals = [step for step in record["steps"] if step.get("phase") == "htn_proposal"]
                metrics["htn_proposal_calls"] = len(proposals)
                metrics["htn_method_action_visits"] = sum(
                    (p.get("proposal", {}).get("method_action_visits") or 0) for p in proposals)
                if injected and case == "route-repair":
                    boundary = metrics["mutation_boundaries"][-1]
                    if boundary["pre"]["clock"]["now"] != boundary["post"]["clock"]["now"]:
                        raise RuntimeError("route mutation advanced the native clock")
                    failures = [s for s in record["steps"]
                                if s.get("phase") == "native_htn_primitive"
                                and s.get("native", {}).get("code") == "EXECUTION_FAILURE"
                                and s.get("action", {}).get("from") == "junction"
                                and s.get("action", {}).get("to") == "inn"]
                    if not failures:
                        raise RuntimeError("B did not dispatch the proposed main move and observe native failure")
                    failure = failures[-1]
                    if failure.get("primitive", {}).get("destination_id") != failure["native"]["pre"]["rooms"]["inn"]:
                        raise RuntimeError("B dispatched a different primitive than its proposed main move")
                    if failure["native"]["post"]["clock"]["now"] != failure["native"]["pre"]["clock"]["now"] + 1:
                        raise RuntimeError("B failed move did not consume exactly one minute")
                    before_task = failure["native"]["pre"]["actors"]["A"].get("active_task") or {}
                    after_task = failure["native"]["post"]["actors"]["A"].get("active_task") or {}
                    if (before_task.get("task_id") != after_task.get("task_id")
                            or before_task.get("held") is not True or after_task.get("held") is not True
                            or before_task.get("progress_seq") != after_task.get("progress_seq")):
                        raise RuntimeError("B route failure did not preserve task/held/progress")
                    _assert_main_observed_closed(failure["native"]["post"])
                    later = [s for s in record["steps"] if s.get("phase") == "htn_proposal"
                             and s.get("snapshot_minute", -1) > failure["native"]["pre"]["clock"]["now"]]
                    if not later:
                        raise RuntimeError("B did not locally re-propose after failed move")
                    record["steps"].append({"phase": "ROUTE_REPAIR_ASSERTIONS", "passed": True,
                        "failure_code": failure["native"].get("code"),
                        "task_id_preserved": after_task.get("task_id"),
                        "progress_seq_preserved": after_task.get("progress_seq"),
                        "main_closed_in_local_view": True,
                        "next_htn_proposal": later[-1].get("proposal")})
                if deviated:
                    record["steps"].append({"phase": "TEMPORAL_REBASE",
                        "cause": "native HTN primitive count differed from frozen macro forecast",
                        "task_id": snapshot["actors"]["A"].get("active_task", {}).get("task_id")})
                continue
            action, driver = _action_for_atomic(name, args, snapshot)
            if (case == "route-repair" and not mutated and variant == "A"
                    and action.get("kind") == "move" and action.get("actor") == "A"
                    and action.get("from") == "junction" and action.get("to") == "inn"
                    and snapshot["items"]["shelter_kit"].get("holder_role") == "A"):
                mutation = metered_call("inject_p0_integration_mutation_v0", {
                    "scene_id": scene_id, "request_id": f"{run_id}-mutation-block-main",
                    "kind": "block_route", "route": "main"})
                after = metered_call("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
                record["mutations"].append({"phase": "BEFORE_PROPOSED_MAIN_MOVE_DISPATCH",
                    "pre_mutation_snapshot": snapshot, "proposal": actions[0],
                    "mutation": mutation, "post_mutation_snapshot": after})
                if snapshot["clock"]["now"] != after["clock"]["now"]:
                    raise RuntimeError("route mutation advanced the native clock")
                mutated = True
                snapshot = after
            native = metered_call("step_p0_integration_v0", {"scene_id": scene_id,
                "request_id": f"{run_id}-atomic-{index:02d}", "driver": driver,
                "action": action})
            record["steps"].append({"phase": "SABRE_ATOMIC_NATIVE", "token": actions[0],
                "action": action, "native": native,
                "classification": classify_native_step(native),
                "plan_call_wall_ms": (time.perf_counter() - t0) * 1000})
            if (case == "route-repair" and variant == "A" and mutated
                    and action.get("kind") == "move" and action.get("from") == "junction"
                    and action.get("to") == "inn" and native.get("code") == "EXECUTION_FAILURE"):
                if native["post"]["clock"]["now"] != native["pre"]["clock"]["now"] + 1:
                    raise RuntimeError("A failed move did not consume exactly one minute")
                before_task = native["pre"]["actors"]["A"].get("active_task") or {}
                after_task = native["post"]["actors"]["A"].get("active_task") or {}
                if (before_task.get("task_id") != after_task.get("task_id")
                        or before_task.get("held") is not True or after_task.get("held") is not True
                        or before_task.get("progress_seq") != after_task.get("progress_seq")):
                    raise RuntimeError("A route failure did not preserve task/held/progress")
                _assert_main_observed_closed(native["post"])
                record["steps"].append({"phase": "ROUTE_REPAIR_ASSERTIONS", "passed": True,
                    "proposal_and_dispatch_same_token": True, "failure_code": native.get("code"),
                    "task_id_preserved": after_task.get("task_id"),
                    "progress_seq_preserved": after_task.get("progress_seq"),
                    "main_closed_in_local_view": True})
            if (case == "high-causal-replan" and not mutated and name == "cloud_seed"
                    and native.get("settled")):
                before = native.get("post")
                if not before or not before.get("pending_cloud"):
                    raise RuntimeError("seed did not leave a pending cloud before mutation")
                mutation = metered_call("inject_p0_integration_mutation_v0", {
                    "scene_id": scene_id, "request_id": f"{run_id}-dissipate-cloud",
                    "kind": "dissipate_cloud"})
                after = metered_call("snapshot_p0_integration_v0", {"scene_id": scene_id})["snapshot"]
                record["mutations"].append({"phase": "CAUSAL_REPAIR_AFTER_FIRST_PENDING_SEED",
                    "snapshot_before": before, "mutation": mutation, "snapshot_after": after})
                if before["clock"]["now"] != after["clock"]["now"] or after.get("pending_cloud") is not None:
                    raise RuntimeError("cloud mutation ticked the clock or did not cancel pending cloud")
                mutated = True
        else:
            record["status"] = "REPLAN_LIMIT"
        final = metered_call("get_p0_integration_trace_v0", {"scene_id": scene_id})
        record["native_trace"] = final.get("trace", final)
        record["typed_monitor"] = evaluate_native_trace(record["native_trace"])
        if record["status"] == "INCOMPLETE":
            record["status"] = "COMPLETED" if record["typed_monitor"]["status"] == "SATISFIED" else "GOAL_" + record["typed_monitor"]["status"]
    except Exception as exc:
        record["status"] = "FAILED"
        record["failure"] = {"type": type(exc).__name__, "message": str(exc)[:1500]}
        if scene_id:
            try:
                last = metered_call("get_p0_integration_trace_v0", {"scene_id": scene_id})
                record["partial_trace"] = last.get("trace", last)
            except Exception as trace_exc:
                record["trace_error"] = type(trace_exc).__name__
    finally:
        metrics["total_wall_ms"] = (time.perf_counter() - start_wall) * 1000
        metrics["wrapper_nonsearch_overhead_proxy_ms"] = max(
            0.0, metrics["wrapper_wall_ms"] - metrics["sabre_native_search_ms"])
        metrics["story_native_action_calls"] = metrics.get("native_action_calls", 0) - metrics.get("evaluation_drain_actions", 0)
        record["mutation_rpc_boundaries"] = metrics["mutation_boundaries"]
        metrics["clock_minutes_elapsed"] = (record.get("native_trace", {}).get("snapshot", {})
                                             .get("clock", {}).get("now"))
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["classification"] = record["status"]
        (out / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return {"run_id": run_id, "run_dir": str(out), "scene_id": scene_id,
            "case": case, "variant": variant, "status": record["status"],
            "typed_monitor": record.get("typed_monitor")}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=sorted(CASES))
    parser.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = run_case(args.case, args.variant, seed=args.seed)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "COMPLETED" else 2)
