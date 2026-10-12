"""Load the fixed integration-v1 case matrix and run only when explicitly invoked."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
from typing import Any, Mapping

from .runner import RUNS_DIR, SEARCH_CONFIG_ID, run_case, run_stale_edit_negative
from .sabre import SEARCH_LIMITS


DEFAULT_SUITE = Path(__file__).resolve().parent / "cases/suite.json"
SCHEMA = "planner-adapter-integration-v1-cases"


def load_suite(path: Path = DEFAULT_SUITE) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(suite, dict) or suite.get("schema") != SCHEMA:
        raise ValueError("unknown Planner Adapter Integration suite schema")
    methods, scenarios = suite.get("methods"), suite.get("scenarios")
    if methods != ["sabre", "p5_director"] or not isinstance(scenarios, list) or not scenarios:
        raise ValueError("suite must declare matched Sabre/P5 Director cases")
    expanded = []
    seen = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("scenario rows must be objects")
        for method in methods:
            row = dict(scenario)
            row["method"] = method
            row["id"] = f"{scenario.get('id', 'case')}-{method}"
            for key in ("bundle",):
                candidate = Path(row[key])
                row[key] = str((path.parent / candidate).resolve()) if not candidate.is_absolute() else str(candidate)
            edit = row.get("scheduled_edit")
            if isinstance(edit, dict) and "bundle" in edit:
                edit = dict(edit)
                candidate = Path(edit["bundle"])
                edit["bundle"] = str((path.parent / candidate).resolve()) if not candidate.is_absolute() else str(candidate)
                row["scheduled_edit"] = edit
            if row["id"] in seen:
                raise ValueError(f"duplicate expanded case id {row['id']}")
            seen.add(row["id"])
            expanded.append(row)
    return suite, expanded


def run_suite(path: Path = DEFAULT_SUITE, *, output_parent: Path = RUNS_DIR) -> dict[str, Any]:
    suite, cases = load_suite(path)
    results = [run_case(case, output_parent=output_parent) for case in cases]
    stale = suite.get("stale_negative")
    if isinstance(stale, dict):
        results.append(run_stale_edit_negative(
            bundle_path=(path.parent / stale["bundle"]).resolve(),
            edited_bundle_path=(path.parent / stale["edited_bundle"]).resolve(),
            output_parent=output_parent))
    summary = {"schema": "planner-adapter-integration-v1-run-summary",
               "recorded_at": datetime.now(timezone.utc).isoformat(),
               "suite_path": str(path.resolve()),
               "suite_sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
               "search_config_id": SEARCH_CONFIG_ID,
               "search_limits": dict(SEARCH_LIMITS),
               "purpose": suite.get("purpose"),
               "runtime_comparison_claim": "NOT_ESTIMATED_N1_DESCRIPTIVE_ONLY",
               "runtime_comparison_note": ("Per-step adapter/search and native-step RPC wall times are retained, "
                   "but Sabre search caps and P5 callback/runtime work are heterogeneous; this small pilot "
                   "does not support an algorithm-efficiency claim."),
               "results": results}
    output_parent.mkdir(parents=True, exist_ok=True)
    target = output_parent / f"suite-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    summary["summary_path"] = str(target)
    return summary


def index_existing_runs(path: Path = DEFAULT_SUITE, *, output_parent: Path = RUNS_DIR) -> dict[str, Any]:
    """Index already-recorded fixed-case trajectories without running any native case."""
    suite, cases = load_suite(path)
    expected = {row["id"]: row for row in cases}
    discovered: dict[str, list[Path]] = {case_id: [] for case_id in expected}
    for case_file in output_parent.glob("outcome-*/case.json"):
        try:
            case_meta = json.loads(case_file.read_text(encoding="utf-8"))
            case_id = case_meta.get("case", {}).get("id")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if case_id in discovered and (case_file.parent / "result.json").is_file():
            discovered[case_id].append(case_file.parent)
    missing = sorted(case_id for case_id, dirs in discovered.items() if not dirs)
    ambiguous = sorted(case_id for case_id, dirs in discovered.items() if len(dirs) > 1)
    if missing or ambiguous:
        raise RuntimeError(f"fixed run inventory incomplete/ambiguous: missing={missing}, ambiguous={ambiguous}")
    all_run_dirs = [dirs[0] for dirs in discovered.values()]
    stale_dirs = sorted(p.parent for p in output_parent.glob("stale-edit-negative-*/result.json"))
    suite_bytes = path.read_bytes()
    expected_fields = ("bundle", "preset", "horizon", "seed", "initial_main_open",
                       "scheduled_edit", "scheduled_interventions")
    pairs = []
    for scenario in suite["scenarios"]:
        left_id, right_id = f"{scenario['id']}-sabre", f"{scenario['id']}-p5_director"
        left = json.loads((discovered[left_id][0] / "case.json").read_text(encoding="utf-8"))["case"]
        right = json.loads((discovered[right_id][0] / "case.json").read_text(encoding="utf-8"))["case"]
        pairs.append({"scenario_id": scenario["id"], "sabre_run_dir": str(discovered[left_id][0]),
                      "p5_director_run_dir": str(discovered[right_id][0]),
                      "shared_inputs_match": all(left.get(k) == right.get(k) for k in expected_fields),
                      "compared_methods_only": left.get("method") != right.get("method")})
    indexed_runs = []
    for run_dir in sorted(all_run_dirs + stale_dirs):
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        files = []
        for file_path in sorted(run_dir.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in {".json", ".problem", ".md"}:
                continue
            if any(part.startswith(".") for part in file_path.relative_to(run_dir).parts):
                continue
            raw = file_path.read_bytes()
            files.append({"path": str(file_path.relative_to(run_dir)),
                          "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()})
        case_id = result.get("source_identity", {}).get("case", {}).get("id")
        summary: dict[str, Any] = {"run_dir": str(run_dir), "status": result.get("status"),
            "scene_id": result.get("scene_id"), "run_status": result.get("run_status"),
            "steps": result.get("steps"), "db_readback_recorded": result.get("db_readback_recorded"),
            "files": files}
        if case_id:
            trace = json.loads((run_dir / "native_final_trace.json").read_text(encoding="utf-8"))
            step_rows = [json.loads(p.read_text(encoding="utf-8"))
                         for p in sorted((run_dir / "steps").glob("minute-*.json"))]
            verdicts = trace.get("verdicts", {}).get("constraints", [])
            method = result.get("source_identity", {}).get("case", {}).get("method")
            raw_statuses = [row.get("sabre", {}).get("status") for row in step_rows]
            adapter_seconds = [row.get("adapter_and_search_wall_seconds") for row in step_rows
                               if isinstance(row.get("adapter_and_search_wall_seconds"), (int, float))]
            native_step_seconds = [row.get("native_step_rpc_wall_seconds") for row in step_rows
                                   if isinstance(row.get("native_step_rpc_wall_seconds"), (int, float))]
            round_rows = [round_row for row in step_rows
                          for round_row in row.get("native_step", {}).get("rounds", [])
                          if isinstance(round_row, Mapping)]
            actor_steps = [actor_step for round_row in round_rows
                           for actor_step in round_row.get("actor_steps", [])
                           if isinstance(actor_step, Mapping)]
            planning_visits = [decision.get("planner", {}).get("method_action_visits")
                for actor_step in actor_steps for decision in actor_step.get("local_decisions", [])
                if isinstance(decision, Mapping)
                and isinstance(decision.get("planner", {}).get("method_action_visits"), int)]
            actor_observation_counts: dict[str, int] = {}
            for step_row in step_rows:
                for alias in step_row.get("actor_observations", {}).get("observations", {}):
                    actor_observation_counts[alias] = actor_observation_counts.get(alias, 0) + 1
            feedback_rows = [row.get("native_join_audit", {}).get("feedback", {})
                             for row in step_rows]
            final_snapshot = trace.get("world_snapshots", [])
            final_routes = final_snapshot[-1].get("routes", {}) if final_snapshot else {}
            edit_summaries = []
            for step_row in step_rows:
                if not step_row.get("scheduled_edit"):
                    continue
                edit_receipts = step_row.get("native_step", {}).get("rounds", [{}])[0].get("edits", [])
                edit_summaries.append({"minute_to": step_row.get("minute_to"),
                    "receipt_count": len(edit_receipts),
                    "receipts": [{"ok": edit.get("ok"),
                        "active_bundle": edit.get("active_bundle"),
                        "prior_version": edit.get("archive", {}).get("prior_version"),
                        "historical_prefix_preserved": edit.get("historical_prefix_preserved"),
                        "pending_identity_preserved": edit.get("pending_identity_preserved"),
                        "ledger_prefix_before_count": len(edit.get("ledger_prefix_before", [])),
                        "ledger_prefix_after_count": len(edit.get("ledger_prefix_after", []))}
                        for edit in edit_receipts if isinstance(edit, Mapping)]})
            constraint_statuses = [{"constraint_id": row.get("constraint_id"),
                "status": row.get("status")} for row in verdicts]
            summary.update({"case_id": case_id,
                "method": method,
                "hard_constraint_statuses": constraint_statuses,
                "all_final_hard_constraints_satisfied": bool(constraint_statuses)
                    and all(row["status"] == "SATISFIED" for row in constraint_statuses),
                "typed_event_count": len(trace.get("typed_trace", {}).get("events", [])),
                "historical_ledger_event_count": len(trace.get("ledger", [])),
                "actor_receipt_counts": {actor.get("actor_alias"): len(actor.get("native_receipts", []))
                    for actor in trace.get("actor_evidence", [])},
                "actor_observation_counts": actor_observation_counts,
                "runner_dispatch_count": sum(bool(row.get("native_dispatch", {}).get("attempted"))
                                              for row in step_rows),
                "raw_search_status_counts": ({status: raw_statuses.count(status)
                    for status in sorted({status for status in raw_statuses if status is not None})}
                    if method == "sabre" else {"NOT_RUN_CONTROL_METHOD": len(step_rows)}),
                "search_status_counts": ({status: sum(row.get("normalized_search_status") == status
                    for row in step_rows) for status in sorted({row.get("normalized_search_status")
                                                                for row in step_rows})}
                    if method == "sabre" else {"NOT_APPLICABLE_CONTROL_METHOD": len(step_rows)}),
                "adapter_and_search_wall_seconds_sum": sum(adapter_seconds),
                "native_step_rpc_wall_seconds_sum": sum(native_step_seconds),
                "director_actor_planner_method_action_visits_sum": sum(planning_visits),
                "final_bundle_identity": trace.get("bundle_identity"),
                "final_route_state": final_routes,
                "final_pending_future_count": len(trace.get("pending_future_nonexecuted", {})),
                "final_pending_actor_aliases": [actor.get("actor_alias") for actor in trace.get("actor_evidence", [])
                    if actor.get("pending_action")],
                "sealed_historical_prefix_preserved_step_count": sum(
                    row.get("sealed_historical_ledger_prefix_preserved") is True
                    for row in feedback_rows),
                "bundle_version_changed_step_count": sum(
                    row.get("bundle_version_changed") is True for row in step_rows),
                "feedback_route_change_step_count": sum(
                    row.get("route_state_changed") is True for row in feedback_rows),
                "feedback_item_support_change_step_count": sum(
                    row.get("item_support_changed") is True for row in feedback_rows),
                "native_edit_receipts": edit_summaries,
                "player_intervention_rows": [{"minute_to": row.get("minute_to"),
                    "intervention": row.get("scheduled_player_intervention")} for row in step_rows
                    if row.get("scheduled_player_intervention")]})
        else:
            summary["stale_negative"] = {key: result.get(key) for key in (
                "candidate_bundle_version", "native_bundle_identity", "native_edit_accepted",
                "native_edit_identity_matches", "native_intervention_status", "status")}
        indexed_runs.append(summary)
    lifecycle_path = output_parent / "server-restart-epoch-20261012T031737Z/lifecycle.md"
    validation_root = RUNS_DIR.parent / "validation"
    validation_files = []
    for file_path in sorted(validation_root.rglob("*")):
        if (not file_path.is_file() or file_path.suffix.lower() not in
                {".json", ".problem", ".txt", ".md", ".java"}):
            continue
        if any(part.startswith(".") for part in file_path.relative_to(validation_root).parts):
            continue
        raw = file_path.read_bytes()
        validation_files.append({"path": str(file_path.relative_to(validation_root)),
                                 "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    supporting_paths = list({p.resolve() for p in [path, *sorted(path.parent.glob("*.json")),
        path.parent.parent / "runner.py", path.parent.parent / "run_suite.py",
        path.parent.parent / "audit.py", path.parent.parent / "model.py",
        path.parent.parent / "sabre.py", path.parent.parent / "README.md"]})
    supporting_files = []
    for file_path in supporting_paths:
        if not file_path.is_file():
            continue
        raw = file_path.read_bytes()
        supporting_files.append({"path": str(file_path.resolve()),
                                 "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    evidence_index = {"schema": "planner-adapter-integration-v1-existing-evidence-index",
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "suite_path": str(path.resolve()), "suite_sha256": sha256(suite_bytes).hexdigest(),
        "search_config_id": SEARCH_CONFIG_ID, "search_limits": dict(SEARCH_LIMITS),
        "runtime_comparison_claim": "NOT_ESTIMATED_N1_DESCRIPTIVE_ONLY",
        "sampling_protocol_note": ("Both methods used A-then-B native observe_actor at matching sealed-minute points. "
            "These calls update retained O/witness evidence; comparisons are conditional on this shared protocol, "
            "not earlier unsampled diagnostics."),
        "outcome_semantics_note": ("DEVELOPMENT_RUN_RECORDED means trajectory/evidence collection completed, "
            "not that hard constraints passed. BUDGET_LIMIT is search exhaustion, not world-unreachability. "
            "STALE_CONTROL_NOT_EXERCISED is not a stale-guard pass."),
        "process_epochs": [{"label": "before-parent-authorized-restart",
             "method_scenario_runs": 14, "one_minute_stale_control_runs": 0},
            {"label": "after-parent-authorized-same-db-restart",
             "method_scenario_runs": 2, "one_minute_stale_control_runs": 1,
             "lifecycle_record": str(lifecycle_path),
             "lifecycle_sha256": sha256(lifecycle_path.read_bytes()).hexdigest()}],
        "matched_pairs": pairs, "runs": indexed_runs,
        "supporting_input_and_code_files": supporting_files,
        "validation_and_preflight_files": validation_files,
        "evidence_scope": ("Per-file hashes cover JSON traces, step evidence, DB readbacks, problem inputs, "
            "preflight evidence, source code, case inputs, and lifecycle note; secrets, tokens, raw dialogue, "
            "and unrelated workspace files are excluded.")}
    target = output_parent / f"evidence-index-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(evidence_index, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    evidence_index["index_path"] = str(target)
    return evidence_index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output-parent", type=Path, default=RUNS_DIR)
    args = parser.parse_args()
    result = run_suite(args.suite, output_parent=args.output_parent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    accepted = {"DEVELOPMENT_RUN_RECORDED", "STALE_GUARD_NEGATIVE_PASS"}
    return 0 if all(row.get("status") in accepted for row in result["results"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
