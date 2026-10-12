"""Offline integrity audit for one saved matched-pair directory.

This module reads artifacts only. It does not call P3/P5, infer task success from
proposals, or turn a missing receipt into evidence of completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ordered_prefix(before: list[Any], after: list[Any]) -> bool:
    return len(after) >= len(before) and after[:len(before)] == before


def audit_pair(pair_dir: Path) -> dict[str, Any]:
    pair_dir = pair_dir.resolve()
    pair = _read(pair_dir / "pair-result.json")
    case_input = _read(pair_dir / "case-input.json")
    suite, case = case_input["suite"], case_input["case"]
    findings: list[dict[str, Any]] = []
    checks: dict[str, bool | str] = {}
    checks["two_arms_present"] = all((pair_dir / arm / "identity.json").is_file()
                                       for arm in ("baseline", "mature_methods"))
    checks["common_suite_input_equal"] = all(
        pair["baseline"].get("case_id") == pair["mature_methods"].get("case_id") == case["case_id"]
        and pair["baseline"].get("scene_id") != pair["mature_methods"].get("scene_id")
        for _ in (0,))
    checks["no_external_observe_actor_calls"] = suite["common"].get("external_observe_actor_calls") == 0
    checks["same_seed_preset_horizon_bundle"] = True
    checks["only_native_director_switch_differs"] = True
    identities = {}
    for arm in ("baseline", "mature_methods"):
        arm_dir = pair_dir / arm
        identity = _read(arm_dir / "identity.json")
        identities[arm] = identity
        checks["same_seed_preset_horizon_bundle"] &= (
            identity.get("common_inputs") == identities.get("baseline", identity).get("common_inputs")
            and identity.get("social_preset") == case["preset"]
            and identity.get("bundle_sha256") == identities.get("baseline", identity).get("bundle_sha256")
        )
        checks["only_native_director_switch_differs"] &= identity.get("native_director_enabled") is (arm == "baseline")
        source_manifest = identity.get("source_manifest", {}).get("working_tree_source_sha256", {})
        checks[f"{arm}_source_manifest_complete"] = bool(source_manifest) and all(
            value != "MISSING" for value in source_manifest.values())
        if not (arm_dir / "INCOMPLETE_ERROR.json").exists():
            arm_result_path = arm_dir / "result.json"
            arm_result = _read(arm_result_path) if arm_result_path.is_file() else {}
            checks[f"{arm}_completed_cleanly"] = bool(
                arm_result.get("run_status") == "COMPLETE"
                and not (arm_dir / "INCOMPLETE_ERROR.json").exists())
            checks[f"{arm}_db_readback_present"] = (arm_dir / "database-readback.json").is_file()
            checks[f"{arm}_costs_present"] = (arm_dir / "costs.json").is_file()
            if checks[f"{arm}_costs_present"]:
                costs = _read(arm_dir / "costs.json")
                root_calls = len(list(arm_dir.glob("high-level-plan-minute-*.json")))
                checks[f"{arm}_root_call_cost_count_consistent"] = (
                    costs.get("gtp_root_plan", {}).get("calls") ==
                    (root_calls if arm == "mature_methods" else 0))
                checks[f"{arm}_p5_snapshot_cost_count_consistent"] = (
                    costs.get("p5_snapshot_pure_plan", {}).get("calls", 0) > 0)
                checks[f"{arm}_advance_cost_count_consistent"] = (
                    costs.get("sealed_advance", {}).get("calls", 0) ==
                    len(list(arm_dir.glob("advance-minute-*.json"))))
                checks[f"{arm}_cost_scopes_distinct"] = all(key in costs for key in
                    ("p5_snapshot_pure_plan", "gtp_root_plan", "sealed_advance"))
            if arm == "mature_methods":
                proposal_truthful = True
                for plan_path in sorted(arm_dir.glob("high-level-plan-minute-*.json")):
                    decision = _read(plan_path)
                    if (decision.get("author_goals_satisfied_by_meta_plan") is not False
                            or decision.get("native_execution_occurred") is not False):
                        proposal_truthful = False
                        break
                checks["mature_meta_plan_not_goal_or_execution_evidence"] = proposal_truthful
            trace_paths = sorted(arm_dir.glob("native-trace-minute-*.json"))
            checks[f"{arm}_sealed_traces_present"] = bool(trace_paths)
            ledger_prefixes = []
            for trace_path in trace_paths:
                trace = _read(trace_path)
                ledger_prefixes.append(trace.get("ledger", []))
            prefix_ok = all(_ordered_prefix(ledger_prefixes[i], ledger_prefixes[i + 1])
                            for i in range(len(ledger_prefixes) - 1))
            checks[f"{arm}_ordered_ledger_prefix"] = prefix_ok
            rpc_names = [p.name for p in arm_dir.glob("rpc-*-request.json")]
            checks[f"{arm}_no_external_observation_rpc"] = not any(
                "observe_actor" in name for name in rpc_names)
            if not prefix_ok:
                findings.append({"kind": "LEDGER_PREFIX_MISMATCH", "arm": arm})
            if not checks[f"{arm}_completed_cleanly"]:
                findings.append({"kind": "ARM_NOT_COMPLETE", "arm": arm})
        else:
            checks[f"{arm}_completed_cleanly"] = False
            failure = _read(arm_dir / "INCOMPLETE_ERROR.json")
            findings.append({"kind": "ARM_RETAINED_FAILURE", "arm": arm,
                             "stage": failure.get("stage"),
                             "error_type": failure.get("error_type"),
                             "error_message": failure.get("error_message")})

    # Input equality is checked against the exact frozen case and per-arm identity,
    # not against observed outcomes (which are allowed to diverge by method).
    if checks.get("same_seed_preset_horizon_bundle") is not True:
        findings.append({"kind": "MATCHED_INPUT_MISMATCH"})

    case_id = case["case_id"]
    semantics: dict[str, Any] = {"proposal_is_not_goal_satisfaction": True,
                                 "wait_is_not_native_fact": True,
                                 "native_receipt_required_for_execution_claim": True}
    if case_id.startswith("S2-"):
        method_dir = pair_dir / "mature_methods"
        stale_files = sorted(method_dir.glob("stale-candidate-minute-*.json"))
        semantics["old_candidate_guard_artifact_count"] = len(stale_files)
        semantics["stale_candidate_rejection_recorded"] = any(
            _read(path).get("status") == "STALE_CANDIDATE" for path in stale_files)
        semantics["replan_plan_artifacts"] = len(list(method_dir.glob("high-level-plan-minute-*.json")))
        semantics["edit_response_status"] = "requires native trace/verdict audit"
    elif case_id.startswith("S3-"):
        semantics["player_interruption_and_recovery"] = "requires exact native item receipts and W snapshots"
        semantics["npc_status_mutations_claimed"] = False
    elif case_id.startswith("S4-"):
        semantics["world_unreachable_claim"] = False
        semantics["safety_negative"] = "unmet hard monitor and no registered opportunity must be confirmed from raw artifacts"

    report = {"schema": "mature-methods-offline-audit-v1", "pair_dir": str(pair_dir),
              "case_id": case_id, "checks": checks, "semantics": semantics,
              "findings": findings, "artifact_hashes": {
                  str(path.relative_to(pair_dir)): _sha(path)
                  for path in sorted(pair_dir.rglob("*") if pair_dir.exists() else [])
                  if path.is_file() and path.name != "offline-audit.json"},
              "overall": "PASS_CONTRACTS" if all(value is True for value in checks.values())
                         and not findings else "REVIEW_REQUIRED"}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pair_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_pair(args.pair_dir)
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["overall"] == "PASS_CONTRACTS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
