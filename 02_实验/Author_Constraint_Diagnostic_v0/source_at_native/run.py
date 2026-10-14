"""One original-candidate search, at most one native diagnostic episode."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from tools.llm_admission_v0.binding import compile_candidate, parse_candidate
from tools.open_adventure_planning_v0.domain import initial_state
from tools.open_adventure_planning_v0.search import SearchLimits, uniform_cost_search
from tools.open_adventure_planning_v0.execute import run_episode, _goal_hash
from .contracts import author_constraints, plan_dependencies, Constraint, obligation_phase, native_plan_lifecycle
from .monitor import inspect_ledger

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "02_实验/Author_Constraint_Diagnostic_v0"
BASE = "416df310fda608a24bdb2f32e95cd1914276ac8b"
RAW = ROOT / "02_实验/LLM_Admission_v0/calls/e/response.raw.txt"
PROTECTED = ("tools/open_adventure_v0", "tools/open_adventure_planning_v0",
             "tools/llm_admission_v0", "02_实验/LLM_Admission_v0",
             "02_实验/OpenAdventure_Planning_B0_v0")


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write(path: Path, value):
    if path.exists():
        raise FileExistsError("diagnostic evidence must not be overwritten")
    path.write_bytes(canonical(value) + b"\n")


def protected_hashes() -> dict:
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "-z", BASE, "--", *PROTECTED], cwd=ROOT).decode().rstrip("\0").split("\0")
    result = {}
    for name in names:
        data = (ROOT / name).read_bytes()
        old = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        if data != old:
            raise ValueError(f"protected baseline changed: {name}")
        result[name] = hashlib.sha256(data).hexdigest()
    return result


def run_once(*, execute_native: bool) -> dict:
    # A directory claim precedes search/native launch; interrupted runs are
    # preserved, not silently restarted by rerunning this entry point.
    execution = OUT / "execution"
    execution.mkdir(parents=True, exist_ok=False)
    before = protected_hashes()
    write(execution / "protected_before.json", before)
    raw_bytes = RAW.read_bytes()
    candidate = parse_candidate(raw_bytes.decode("utf-8"))
    goal = compile_candidate(candidate)  # actual four atoms, no gold lookup
    supplied = {"required": sorted(goal.required), "forbidden": sorted(goal.forbidden)}
    if len(goal.required) != 4 or ("bridge",) in goal.required:
        raise ValueError("not the original four-atom diagnostic")
    old_gate = json.loads((RAW.parents[2] / "e_validation.json").read_text())
    if old_gate["status"] != "FAIL":
        raise ValueError("old admission must remain FAIL")
    write(execution / "input.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "base": BASE,
        "raw_output_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_output_source": str(RAW.relative_to(ROOT)), "all_original_fields_retained": True,
        "complete_goal_passed_to_ucs": supplied, "goal_predicate_sha256": _goal_hash(goal),
        "controller_added_atoms": [], "old_admission": "FAIL",
        "authorization": "separate diagnostic bypass; not B2 admission or changed old verdict",
        "model_calls": 0, "offline_search_diagnostics": 1,
        "offline_limits": asdict(SearchLimits(10000, 10.0)),
        "native_controller_limits": {"inputs": 80, "per_search_expansions": 10000,
                                      "per_search_seconds": 10, "total_search_seconds": 120},
        "native_ucs_calls": "per-action re-search from frozen B0; reported separately, not additional diagnostic probes",
        "original_residual_fields": candidate.get("residual_obligations"),
        "scope_specific_obligation_mapping": obligation_phase(capability=True, monitor=True, ended=False, verdict="PENDING")})
    searched = uniform_cost_search(initial_state(), goal, limits=SearchLimits(10000, 10.0))
    plan_id = hashlib.sha256(canonical([asdict(op) for op in searched.plan])).hexdigest()
    states, cursor, bridge_nodes = [], initial_state(), []
    for i, op in enumerate(searched.plan):
        predicted = op.apply(cursor)
        states.append({"index": i, "operator": asdict(op), "before": sorted(cursor), "after": sorted(predicted), "prediction_only": True})
        if ("bridge",) not in cursor and ("bridge",) in predicted:
            bridge_nodes.append(i)
        cursor = predicted
    search_record = {**asdict(searched), "plan_id": plan_id, "actual_goal": supplied,
                     "goal_predicate_sha256": _goal_hash(goal), "predictions": states,
                     "bridge_creation_plan_indices": bridge_nodes,
                     "bridge_consuming_plan_indices": [i for i, op in enumerate(searched.plan) if ("bridge",) in op.preconditions],
                     "plan_legally_replayed_in_model": goal.satisfied(cursor) if searched.status == "FOUND" else None,
                     "model_calls": 0, "read_walkthrough": False}
    write(execution / "search.json", search_record)
    records = author_constraints() + plan_dependencies(plan_id, searched.plan) + (
        Constraint("game-crossing-bridge-rule", "GAME", "MUST", "BEFORE", ("bridge",),
                   "upstream/adventure.yaml:641-659,768-784; applies when consuming fissure over action"),)
    write(execution / "constraints.json", [asdict(row) for row in records])
    if searched.status != "FOUND" or not execute_native:
        result = {"search": searched.status, "native": "NOT_RUN", "author_verdict": "UNKNOWN",
                  "reason": "search_not_found" if searched.status != "FOUND" else "native_not_authorized"}
    else:
        write(execution / "native_attempt_claim.json", {"maximum_episodes": 1, "attempt": 1,
              "old_admission_still_FAIL": True, "external_goal_hash": _goal_hash(goal),
              "inherited_goal_origin_label": "B0 external_validated_candidate describes interface origin, NOT old semantic-admission PASS"})
        try:
            native = run_episode("E", scenario="clean", execute_native=True, external_goal=goal,
                                 external_goal_text=candidate["author_text"], runs_root=OUT / "runs")
            write(execution / "native.json", native)
            temporal = inspect_ledger(Path(native["native_ledger"]), ended=True)
            write(execution / "temporal.json", temporal)
            write(execution / "native_plan_lifecycle.json", native_plan_lifecycle(Path(native["decision_trace"]), temporal))
            result = {"search": searched.status, "native": native["status"],
                      "old_native_verifier": native.get("verifier"), "author_verdict": temporal["status"],
                      "model_calls_this_round": 0, "episodes_this_round": 1}
        except Exception as exc:
            result = {"search": searched.status, "native": "EXECUTION_ERROR", "author_verdict": "UNKNOWN",
                      "error": f"{type(exc).__name__}: {exc}", "episodes_attempted": 1, "retry": False}
    after = protected_hashes()
    write(execution / "protected_after.json", after)
    result["protected_bytes_unchanged"] = before == after
    result["raw_output_unchanged"] = RAW.read_bytes() == raw_bytes
    write(execution / "outcome.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-native", action="store_true")
    print(json.dumps(run_once(execute_native=parser.parse_args().execute_native), ensure_ascii=False, indent=2))
