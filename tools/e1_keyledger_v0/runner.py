"""Deterministic development runner; outputs are non-overwriting and DEV_ONLY."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import subprocess

from .executor import Executor, scheduled_actor
from .fixtures import CASE_IDS, E1_PRODUCER_VERSION, initial_checkpoint
from .monitor_bridge import evaluate_goals, validate_e1_evidence
from .oracle import solve as solve_oracle
from .planner import restore_budget, snapshot_budget, uniform_cost_search
from .policy import actor_view, choose_b, explain_b, a_input, forecast_b_from_a

EXPANSION_CAP = 10_000
WALL_SECONDS = 2.0


def _hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _hash_obj(value):
    return _hash_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode())


def _source_manifest():
    root = Path(__file__).resolve().parents[2]
    package = Path(__file__).resolve().parent
    paths = list(package.glob("*.py")) + list(package.glob("tests/*.py"))
    paths += list((root / "tools" / "e0_keyledger_v0").glob("*.py"))
    paths += list((root / "tools" / "trajectory_constraints_v0").glob("*.py"))
    paths += [package / "README.md", root / "00_研究设计" / "E1_KeyLedger_LocalAgency_Protocol_v0.md"]
    return {str(p.relative_to(root)): _hash_bytes(p.read_bytes()) for p in paths}


def _git_revision():
    root = Path(__file__).resolve().parents[2]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"unavailable": type(exc).__name__}


def _expected(cp, mode):
    policy = cp["config_pins"]["e1"]["policy"]
    deadline = cp["config_pins"]["deadline"]
    if mode == "world":
        return "SOLVED", 8
    if policy == "PAY":
        return "SOLVED", 8
    if policy == "TOOL":
        return ("PROVEN_UNREACHABLE_IN_FINITE_DOMAIN", None) if deadline == 8 else ("SOLVED", 9)
    return "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN", None


def _run_trace(initial, max_expansions, wall_seconds):
    executor = Executor(initial)
    steps, decisions, policy_inputs, budgets, errors = [], [], [], [], []
    budget = restore_budget(initial.get("actor_planning", {}).get("budget", {}),
                            max_expansions=max_expansions, wall_seconds=wall_seconds)
    planner_last = None
    try:
        while executor.checkpoint()["clock"]["now"] < executor.checkpoint()["config_pins"]["deadline"]:
            cp = executor.checkpoint()
            actor = scheduled_actor(cp)
            if actor == "CONTINUE":
                raise AssertionError("synchronous development runner found unexpected R")
            if actor == "B":
                view = actor_view(cp, "B")
                action = choose_b(view)
                policy_inputs.append({"actor": "B", "input": view, "hash": _hash_obj(view)})
                decisions.append({"actor": "B", "action": action, "policy": explain_b(view, action)})
            else:
                inputs = a_input(cp)
                policy_inputs.append({"actor": "A", **inputs})
                forecast = forecast_b_from_a(inputs["view"])
                for assumption in inputs["assumptions"]:
                    executor.record_actor_planning(assumption={"time": cp["clock"]["now"],
                                                               "text": assumption})
                if ("key1" in inputs["view"]["observation"]["known_entities"]
                        and "key1_disclosed_by_B" in inputs["view"]["observation"]["known_facts"]):
                    offer_id = next((x for x in inputs["view"]["observation"]["known_entities"]
                                     if x.startswith("offer-")), "offer-unknown")
                    executor.record_actor_planning(binding={"symbol": f"LoanKey({offer_id})",
                                                            "actual_id": "key1"})
                planner_last = uniform_cost_search(inputs["view"], max_expansions=max_expansions,
                                                   wall_seconds=wall_seconds, budget=budget)
                executor.record_actor_planning(budget=snapshot_budget(budget))
                decisions.append({"actor": "A", "input_hash": inputs["input_hash"],
                    "forecast": forecast, "plan": planner_last})
                action = planner_last["selected_action"] if planner_last["solve_status"] == "SOLVED" else None
                if action is None:
                    action = {"operator": "idle", "actor": "WorldStep", "args": {}}
            before = executor.checkpoint()
            receipt = executor.execute(action)
            after = executor.checkpoint()
            steps.append({"at": before["clock"]["now"], "action": deepcopy(action),
                          "receipt": deepcopy(receipt), "before_hash": _hash_obj(before),
                          "after_hash": _hash_obj(after), "state": after})
            if not receipt.get("accepted") or receipt.get("status") != "SUCCESS":
                errors.append({"kind": "EXECUTOR_REJECTED", "receipt": deepcopy(receipt)})
                # Rejection is a zero-effect pre-start result; consume one
                # no-control minute and replan from the unchanged observations.
                if executor.checkpoint()["clock"]["now"] < executor.checkpoint()["config_pins"]["deadline"]:
                    idle_before = executor.checkpoint()
                    idle = executor.execute({"operator": "idle", "actor": "WorldStep", "args": {}})
                    idle_after = executor.checkpoint()
                    steps.append({"at": idle_before["clock"]["now"], "action": idle["intent"],
                                  "receipt": idle, "before_hash": _hash_obj(idle_before),
                                  "after_hash": _hash_obj(idle_after), "state": idle_after,
                                  "reason": "NO_CONTROL_AFTER_REJECTION"})
        final = executor.checkpoint()
        validate_e1_evidence(final)
        monitor = evaluate_goals(final)
        trace_status = "TRACE_SATISFIED" if monitor["status"] == "SATISFIED" else (
            "TRACE_VIOLATED" if monitor["status"] == "VIOLATED" else "TRACE_INDETERMINATE")
        return {"trace_status": trace_status, "monitor": monitor, "final": final,
                "steps": steps, "decisions": decisions, "actor_inputs": policy_inputs,
                "planner_budget": snapshot_budget(budget),
                "planner_last": planner_last, "errors": errors}
    except Exception as exc:
        errors.append({"kind": "RUNNER_EXCEPTION", "type": type(exc).__name__,
                       "message": str(exc), "traceback": traceback.format_exc()})
        return {"trace_status": "TRACE_INDETERMINATE", "monitor": None,
                "final": executor.checkpoint(), "steps": steps, "decisions": decisions,
                "actor_inputs": policy_inputs, "planner_budget": snapshot_budget(budget),
                "planner_last": planner_last, "errors": errors}


def run_case(cp, *, max_expansions=EXPANSION_CAP, wall_seconds=WALL_SECONDS):
    out = {"fixture_id": cp["fixture_id"], "initial": deepcopy(cp),
           "initial_hash": _hash_obj(cp), "limits": {"max_expansions": max_expansions,
                                                       "wall_seconds": wall_seconds}}
    try:
        world = solve_oracle(deepcopy(cp), mode="world", max_expansions=max_expansions,
                             wall_seconds=wall_seconds)
        fixed = solve_oracle(deepcopy(cp), mode="fixed_b", max_expansions=max_expansions,
                             wall_seconds=wall_seconds)
        out["oracles"] = {"world": world, "fixed_b": fixed}
        out["oracle_checks"] = {}
        for mode, result in (("world", world), ("fixed_b", fixed)):
            if not result["complete"]:
                out["oracle_checks"][mode] = "INCOMPLETE_BUDGET"
            else:
                out["oracle_checks"][mode] = "EXPECTED_VERDICT_CHECK" if (
                    result["solve_status"], result["earliest_completion_time"]) == _expected(cp, mode) else "FAIL"
        trace = _run_trace(cp, max_expansions, wall_seconds)
        policy = cp["config_pins"]["e1"]["policy"]
        deadline = cp["config_pins"]["deadline"]
        expected_trace = ("TRACE_SATISFIED", 8) if policy == "PAY" else (
            ("TRACE_SATISFIED", 9) if policy == "TOOL" and deadline == 10
            else ("TRACE_VIOLATED", None))
        final = trace["final"]
        event_by_id = {e["event_id"]: e for e in final["events"]}
        witness_times = ([event_by_id[eid]["time"] for eid in trace["monitor"]["witness_event_ids"]
                          if eid in event_by_id] if trace["monitor"] else [])
        observed_trace = (trace["trace_status"], min(witness_times) if witness_times else None)
        if trace["errors"] or trace["monitor"] is None:
            trace["trace_check"] = "FAIL"
        elif trace["planner_last"] and not trace["planner_last"]["complete"]:
            trace["trace_check"] = "INCOMPLETE_BUDGET"
        else:
            trace["trace_check"] = ("EXPECTED_VERDICT_CHECK" if observed_trace == expected_trace else "FAIL")
        trace["expected_trace"] = {"status": expected_trace[0], "witness_time": expected_trace[1]}
        trace["observed_trace"] = {"status": observed_trace[0], "witness_time": observed_trace[1]}
        out["actual_trace"] = trace
        out["status"] = "FAIL" if ("FAIL" in out["oracle_checks"].values()
            or trace["trace_check"] == "FAIL" or trace["errors"]) else (
            "INCOMPLETE_BUDGET" if "INCOMPLETE_BUDGET" in out["oracle_checks"].values()
            or trace["trace_check"] == "INCOMPLETE_BUDGET" else "DEVELOPMENT_RECORDED")
    except Exception as exc:
        out.update({"status": "FAIL", "error": {"type": type(exc).__name__, "message": str(exc),
                    "traceback": traceback.format_exc()}})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="all", choices=("all", *CASE_IDS))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--max-expansions", type=int, default=EXPANSION_CAP)
    parser.add_argument("--wall-seconds", type=float, default=WALL_SECONDS)
    args = parser.parse_args(argv)
    if args.max_expansions < 1 or args.wall_seconds <= 0:
        parser.error("budgets must be positive")
    root = Path(args.output_root).expanduser().resolve()
    run_dir = root / args.run_id
    if run_dir.exists():
        parser.error(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    cases = [initial_checkpoint(k, p, t) for k in ("known", "unknown")
             for p in ("PAY", "TOOL", "KEEP") for t in (8, 10)] if args.case == "all" else [
                 initial_checkpoint(args.case.split("-")[1], args.case.split("-")[2],
                                    int(args.case.split("-")[3]))]
    manifest = {"status": "DEV_ONLY", "formal_experiment": False,
        "run_id": args.run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "environment": {k: os.environ.get(k) for k in ("PYTHONHASHSEED", "LANG", "LC_ALL")},
        "limits": {"max_expansions": args.max_expansions, "wall_seconds": args.wall_seconds},
        "source_hashes": _source_manifest(), "git_revision": _git_revision(),
        "case_count": len(cases), "results": []}
    for cp in cases:
        result = run_case(cp, max_expansions=args.max_expansions, wall_seconds=args.wall_seconds)
        manifest["results"].append(result)
        (run_dir / f"{cp['fixture_id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    statuses = {row["status"] for row in manifest["results"]}
    print(json.dumps({"run_dir": str(run_dir), "status": "FAIL" if "FAIL" in statuses else
        "INCOMPLETE_BUDGET" if "INCOMPLETE_BUDGET" in statuses else "DEV_ONLY_RECORDED",
        "cases": len(cases), "manifest": str(run_dir / "manifest.json")}, ensure_ascii=False))
    return 1 if "FAIL" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
