"""Record one fixed Mature-Methods/P5-Director matched case pair.

The runner never samples actor O externally, issues NPC commands, or changes
the native service. It can submit only the registered, version/frontier-guarded
P5 route opportunity; all actor work and social outcomes stay native.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

from tools.native_platform_v0.p3.mcp_stdio import PROJECT_ROOT, rpc_call
from tools.native_platform_v0.p5.bundle import load_bundle
from tools.native_platform_v0.p5.mature_methods import (
    advance_from_sealed, plan_high_level, snapshot_from_native,
)


SUITE_PATH = PROJECT_ROOT / "tools/mature_methods_integration_v1/cases/suite.json"
RUNS_DIR = PROJECT_ROOT / "02_实验/Mature_Methods_Integration_v1/runs"
SOURCE_PATHS = (
    "tools/mature_methods_integration_v1/runner.py",
    "tools/mature_methods_integration_v1/run_suite.py",
    "tools/mature_methods_integration_v1/audit.py",
    "tools/mature_methods_integration_v1/__init__.py",
    "tools/mature_methods_integration_v1/tests/test_case_matrix_contract.py",
    "tools/mature_methods_integration_v1/cases/suite.json",
    "tools/mature_methods_integration_v1/cases/bundle-result-only-v1.json",
    "tools/mature_methods_integration_v1/cases/bundle-main-only-v2.json",
    "tools/mature_methods_integration_v1/cases/bundle-no-opportunities-v1.json",
    "tools/native_platform_v0/p5/mature_methods/method_adapters.py",
    "tools/native_platform_v0/p5/mature_methods/narrative_methods.py",
    "tools/native_platform_v0/p5/mature_methods/orchestrator.py",
    "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p5/planning.py",
    "tools/native_platform_v0/p5/world.py",
    "tools/native_platform_v0/p5/bundle.py",
    "tools/native_platform_v0/p5/monitor.py",
    "tools/native_platform_v0/p5/runner.py",
    "tools/native_platform_v0/p5/tests/test_mature_methods.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/export_evidence.py",
)
ARM_DIRECTOR = {"mature_methods": False, "baseline": True}


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical_sha(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8"))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        stream.write("\n")


def _source_manifest() -> dict[str, Any]:
    files = {name: _sha((PROJECT_ROOT / name).read_bytes())
             if (PROJECT_ROOT / name).is_file() else "MISSING"
             for name in SOURCE_PATHS}
    packed = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              capture_output=True, text=True, check=False)
    return {"git_base_commit": revision.stdout.strip() if revision.returncode == 0 else None,
            "working_tree_source_sha256": files,
            "working_tree_source_set_sha256": _sha(packed)}


def _runtime_manifest() -> dict[str, Any]:
    """Fail before any native reset when the mature planner runtime is absent."""
    try:
        import gtpyhop
        try:
            from importlib.metadata import version
            package_version = version("gtpyhop")
        except Exception:
            package_version = getattr(gtpyhop, "__version__", None)
        if not isinstance(package_version, str) or not package_version:
            raise RuntimeError("GTPyhop version metadata is unavailable")
    except Exception as exc:
        raise RuntimeError(
            f"GTPyhop runtime preflight failed under {sys.executable}: {type(exc).__name__}: {exc}"
        ) from exc
    return {"python_executable": sys.executable, "python_version": sys.version,
            "gtpyhop_version": package_version,
            "gtpyhop_module": str(getattr(gtpyhop, "__file__", "unknown"))}


def _case_bundle(case: Mapping[str, Any], suite_path: Path) -> tuple[dict[str, Any], str]:
    path = (suite_path.parent / case["bundle"]).resolve()
    raw_bytes = path.read_bytes()
    bundle = json.loads(raw_bytes.decode("utf-8"))
    load_bundle(bundle)
    return bundle, _sha(raw_bytes)


def _scheduled_inputs(case: Mapping[str, Any], suite_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edits = []
    for row in case.get("edits", []):
        raw_bundle, digest = _case_bundle({"bundle": row["bundle"]}, suite_path)
        edits.append({"at": row["at"], "expected_version": row["expected_version"],
                      "raw_bundle": raw_bundle, "bundle_sha256": digest})
    interventions = [dict(row) for row in case.get("interventions", [])]
    return edits, interventions


def _allocate_pair(case_id: str, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in case_id)[:48]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(16):
        path = runs_dir / f"{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            pass
    raise FileExistsError("could not allocate a non-overwriting matched-pair directory")


def _candidate_and_guard(decision: Mapping[str, Any], snapshot) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    methods = decision.get("method_trace")
    if not isinstance(methods, list) or len(methods) != 1 or not isinstance(methods[0], Mapping):
        raise ValueError("high-level decision must contain exactly one recorded support method")
    method = methods[0]
    method_id = method.get("method_id")
    candidate = method.get("candidate")
    proposal = decision.get("control_proposal")
    proposal_status = decision.get("control_proposal_status")
    if method_id == "blocked":
        if (proposal_status != "BLOCKED" or not isinstance(proposal, Mapping)
                or proposal.get("candidate") != candidate
                or proposal.get("selected_action") != "NO_OP"
                or proposal.get("candidate_guard") is not None):
            raise ValueError("blocked high-level method disagrees with control-proposal status")
        return None, None
    if method_id == "existing_path" and (candidate is None or
                                           isinstance(candidate, Mapping) and candidate.get("action") == "NO_OP"):
        if (proposal_status != "PROPOSAL_AVAILABLE" or not isinstance(proposal, Mapping)
                or proposal.get("selected_action") != "NO_OP"
                or proposal.get("candidate") != candidate
                or proposal.get("candidate_guard") is not None):
            raise ValueError("existing-path/no-op method disagrees with the non-dispatchable control proposal")
        return None, None
    if not isinstance(candidate, Mapping):
        raise ValueError("selected route-opening method omitted its registered candidate")
    if proposal_status != "PROPOSAL_AVAILABLE" or not isinstance(proposal, Mapping):
        raise ValueError("selected high-level method has no separately recorded control proposal")
    action = candidate.get("action")
    opportunity = candidate.get("opportunity_id")
    if action not in {"open_main_passage", "open_side_passage"}:
        return None, None
    if opportunity != action or candidate.get("feasible") is not True:
        raise ValueError("proposed P5 candidate is not the exact feasible registered route action")
    if decision.get("scene_id") != snapshot.scene_id or decision.get("based_on_minute") != snapshot.now:
        raise ValueError("high-level decision identity does not match its sealed snapshot")
    if (decision.get("bundle_id") != snapshot.bundle_id
            or decision.get("bundle_version") != snapshot.bundle_version
            or decision.get("bundle_sha256") != snapshot.bundle_sha256):
        raise ValueError("high-level candidate is bound to another active AuthorBundle")
    if (proposal.get("selected_action") != action
            or proposal.get("selection_source") != "unchanged_p5_planning_plan"
            or proposal.get("candidate") != dict(candidate)):
        raise ValueError("control proposal differs from the exact selected P5 method candidate")
    frontier = snapshot.trace_identity
    guard = proposal.get("candidate_guard")
    expected_guard = {"scene_id": snapshot.scene_id, "bundle_version": snapshot.bundle_version,
                      "based_on_minute": snapshot.now,
                      "events_through": frontier["events_through"],
                      "values_through": frontier["values_through"],
                      "selected_action": action, "opportunity_id": opportunity}
    if not isinstance(guard, Mapping) or dict(guard) != expected_guard:
        raise ValueError("adapter-provided candidate guard does not match sealed snapshot identity")
    return dict(candidate), guard


def _rpc_record(rpc: Callable[[str, dict[str, Any]], Any], run_dir: Path,
                index: int, op: str, args: dict[str, Any]) -> Any:
    stem = f"rpc-{index:04d}-{op}"
    _write_once(run_dir / f"{stem}-request.json", args)
    try:
        result = rpc(op, args)
    except Exception as exc:
        error = {"rpc_operation": op, "error_type": type(exc).__name__,
                 "error_message": str(exc)[:500]}
        _write_once(run_dir / f"{stem}-error.json", error)
        raise
    _write_once(run_dir / f"{stem}-response.json", result)
    return result


def _run_arm(*, pair_dir: Path, case: Mapping[str, Any], suite: Mapping[str, Any],
             suite_path: Path, arm: str, rpc: Callable[[str, dict[str, Any]], Any],
             resume_pristine_scene: Mapping[str, Any] | None = None,
             continue_s1_checkpoint17: Mapping[str, Any] | None = None) -> dict[str, Any]:
    run_dir = pair_dir / arm
    run_dir.mkdir(exist_ok=False)
    stage, scene_id, call_index = "prepare", None, 0
    costs = {"p5_snapshot_pure_plan": {"calls": 0, "wall_seconds": 0.0},
             "gtp_root_plan": {"calls": 0, "wall_seconds": 0.0},
             "sealed_advance": {"calls": 0, "wall_seconds": 0.0},
             "checkpoint_ranges": []}

    def make_snapshot(bundle_obj, native_evidence):
        started = time.perf_counter()
        try:
            return snapshot_from_native(bundle_obj, native_evidence)
        finally:
            costs["p5_snapshot_pure_plan"]["calls"] += 1
            costs["p5_snapshot_pure_plan"]["wall_seconds"] += time.perf_counter() - started

    def make_high_plan(bundle_obj, snapshot_obj, reason):
        started = time.perf_counter()
        try:
            return plan_high_level(bundle_obj, snapshot_obj)
        finally:
            costs["gtp_root_plan"]["calls"] += 1
            costs["gtp_root_plan"]["wall_seconds"] += time.perf_counter() - started
            costs["checkpoint_ranges"].append({"reason": reason, "minute": snapshot_obj.now,
                                                 "scene_id": snapshot_obj.scene_id,
                                                 "bundle_version": snapshot_obj.bundle_version,
                                                 "trace_identity": dict(snapshot_obj.trace_identity)})
    raw_bundle, bundle_sha = _case_bundle(case, suite_path)
    edits, interventions = _scheduled_inputs(case, suite_path)
    common = suite["common"]
    if arm not in ARM_DIRECTOR:
        raise ValueError(f"unknown controller arm {arm!r}")
    identity = {"schema": "mature-methods-run-identity-v1", "case_id": case["case_id"],
                "arm": arm, "controller": suite["arms"][arm]["controller"],
                "source_manifest": _source_manifest(), "suite_sha256": _sha(suite_path.read_bytes()),
                "runtime": _runtime_manifest(),
                "case_sha256": _canonical_sha(case), "bundle_sha256": bundle_sha,
                "bundle_edit_sha256": [{"at": row["at"], "sha256": row["bundle_sha256"]}
                                        for row in edits],
                "common_inputs": {key: common[key] for key in
                                  ("horizon", "seed", "initial_main_open", "shared_supply",
                                   "external_observe_actor_calls")},
                "social_preset": case["preset"],
                "native_director_enabled": ARM_DIRECTOR[arm],
                "raw_actor_dialogue_publication": "PROHIBITED"}
    _write_once(run_dir / "identity.json", identity)
    try:
        if resume_pristine_scene is None and continue_s1_checkpoint17 is None:
            stage = "reset_p5_scenario"
            reset_args = {"bundle": raw_bundle, "initial_social_preset": case["preset"],
                          "horizon": common["horizon"], "seed": common["seed"],
                          "director_enabled": ARM_DIRECTOR[arm],
                          "shared_supply": common["shared_supply"],
                          "initial_main_open": common["initial_main_open"]}
            call_index += 1
            created = _rpc_record(rpc, run_dir, call_index, "reset_p5_scenario", reset_args)
            scene = created.get("scene") if isinstance(created, Mapping) else None
            scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
            if not isinstance(scene_id, str) or not scene_id:
                raise RuntimeError("P5 reset returned no native scene identity")
            _write_once(run_dir / "scene_identity.json", {
                "scene_id": scene_id, "reset_bundle": scene.get("active_bundle"),
                "preset": scene.get("preset"), "seed": scene.get("seed"),
                "horizon": scene.get("horizon"), "native_director_enabled": scene.get("director_enabled")})
        elif resume_pristine_scene is not None:
            if arm != "mature_methods" or case["case_id"] != "S1-result-only-reject":
                raise ValueError("pristine-scene continuation is authorized only for the failed S1 method arm")
            scene_id = resume_pristine_scene["scene_id"]
            _write_once(run_dir / "reused-native-reset-reference.json", {
                "schema": "mature-methods-reused-reset-reference-v1",
                "scene_id": scene_id,
                "original_reset_receipt": resume_pristine_scene["reset_receipt_path"],
                "original_reset_receipt_sha256": resume_pristine_scene["reset_receipt_sha256"],
                "original_failed_arm_error": resume_pristine_scene["failure_path"],
                "original_failed_arm_error_sha256": resume_pristine_scene["failure_sha256"],
                "reuse_claim": "same already-created scene; no reset RPC issued by continuation"})
        else:
            if arm != "mature_methods" or case["case_id"] != "S1-result-only-reject":
                raise ValueError("minute-17 continuation is authorized only for the S1 method arm")
            scene_id = continue_s1_checkpoint17["scene_id"]
            _write_once(run_dir / "reused-native-checkpoint-reference.json", {
                "schema": "mature-methods-reused-checkpoint-reference-v1",
                "scene_id": scene_id, "checkpoint_minute": 17,
                "source_checkpoint_snapshot": continue_s1_checkpoint17["snapshot_path"],
                "source_checkpoint_sha256": continue_s1_checkpoint17["snapshot_sha256"],
                "prior_runner_error": continue_s1_checkpoint17["failure_path"],
                "prior_runner_error_sha256": continue_s1_checkpoint17["failure_sha256"],
                "reset_rpc_replayed": False,
                "resume_claim": "continue same scene from sealed minute 17; no history reset"})

        stage = "initial_get_trace"
        call_index += 1
        evidence = _rpc_record(rpc, run_dir, call_index, "get_trace", {"scene_id": scene_id})
        initial_minute = evidence.get("now", 0)
        _write_once(run_dir / f"native-trace-minute-{initial_minute:03d}.json", evidence)
        bundle = load_bundle(raw_bundle)
        initial_snapshot = make_snapshot(bundle, evidence)
        if resume_pristine_scene is not None:
            expected_snapshot = resume_pristine_scene["expected_initial_snapshot"]
            same_pristine_prefix = initial_snapshot.as_dict() == expected_snapshot
            _write_once(run_dir / "resume-pristine-check.json", {
                "scene_id": scene_id, "now": initial_snapshot.now,
                "expected_snapshot_matches_live": same_pristine_prefix,
                "expected_snapshot_sha256": _canonical_sha(expected_snapshot),
                "live_snapshot_sha256": _canonical_sha(initial_snapshot.as_dict()),
                "no_reset_replayed": True, "no_observe_actor_called": True})
            if not same_pristine_prefix or initial_snapshot.now != 0:
                raise RuntimeError("failed-scene continuation refused: sealed minute-0 snapshot is not identical")
            _write_once(run_dir / "scene_identity.json", {
                "scene_id": scene_id, "reset_replayed": False,
                "reused_native_reset_receipt_sha256": resume_pristine_scene["reset_receipt_sha256"],
                "preset": case["preset"], "seed": common["seed"],
                "horizon": common["horizon"], "native_director_enabled": False})
        if continue_s1_checkpoint17 is not None:
            expected_snapshot = continue_s1_checkpoint17["expected_snapshot"]
            same_checkpoint = initial_snapshot.as_dict() == expected_snapshot
            _write_once(run_dir / "resume-checkpoint17-check.json", {
                "scene_id": scene_id, "expected_minute": 17,
                "live_minute": initial_snapshot.now,
                "expected_snapshot_matches_live": same_checkpoint,
                "expected_snapshot_sha256": _canonical_sha(expected_snapshot),
                "live_snapshot_sha256": _canonical_sha(initial_snapshot.as_dict()),
                "no_reset_replayed": True, "no_observe_actor_called": True,
                "ledger_prefix_preserved": same_checkpoint})
            if not same_checkpoint or initial_snapshot.now != 17:
                raise RuntimeError("minute-17 continuation refused: live sealed checkpoint differs")
            _write_once(run_dir / "scene_identity.json", {
                "scene_id": scene_id, "reset_replayed": False,
                "continued_from_minute": 17,
                "preset": case["preset"], "seed": common["seed"],
                "horizon": common["horizon"], "native_director_enabled": False})
        _write_once(run_dir / "initial-p5-director-plan.json", initial_snapshot.director_plan)
        if continue_s1_checkpoint17 is None:
            expected_routes = case["expected"]["initial_routes"]
            opened = {row["id"]: row["open"] for row in initial_snapshot.director_state["routes"]}
            if opened != expected_routes:
                raise RuntimeError(f"fixed initial route precondition mismatch: {opened!r}")
        _write_once(run_dir / "initial-snapshot.json", initial_snapshot.as_dict())
        expected_candidate = case["expected"].get("candidate_before_edit")
        if expected_candidate:
            native_selected = initial_snapshot.director_plan.get("selected_action")
            if native_selected != expected_candidate:
                raise RuntimeError(
                    f"fixed pre-edit native P5 selection mismatch: {native_selected!r}"
                )

        decision = None
        decision_snapshot = initial_snapshot
        candidate, guard = None, None
        start_minute = 0
        if arm == "mature_methods":
            if continue_s1_checkpoint17 is None:
                stage = "initial_high_level_plan"
                decision = make_high_plan(bundle, initial_snapshot, "initial")
            else:
                start_minute = 17
                decision = continue_s1_checkpoint17["checkpoint_plan"]
                if (decision.get("scene_id") != scene_id or decision.get("based_on_minute") != 17
                        or decision.get("bundle_version") != initial_snapshot.bundle_version
                        or decision.get("trace_identity") != dict(initial_snapshot.trace_identity)):
                    raise RuntimeError("saved minute-17 high-level plan does not match the sealed checkpoint")
            _write_once(run_dir / f"high-level-plan-minute-{initial_snapshot.now:03d}.json", decision)
            candidate, guard = _candidate_and_guard(decision, initial_snapshot)
            if expected_candidate and (not candidate or candidate.get("action") != expected_candidate):
                raise RuntimeError("S2 predeclared initial candidate differs; stop before stepping the world")
            _write_once(run_dir / "initial-candidate-guard.json", {
                "candidate": candidate, "candidate_guard": guard,
                "execution_evidence": False})

        advanced_evidence = 0
        for minute in range(start_minute + 1, common["horizon"] + 1):
            stage = f"step_world_minute_{minute}"
            minute_interventions = [dict(row) for row in interventions if row.get("at") == minute]
            if arm == "mature_methods" and candidate is not None and guard is not None:
                stale_candidate = {"at": minute, "kind": "author_opportunity",
                                  "operation": "open_passage",
                                  "opportunity_id": candidate["opportunity_id"],
                                  "candidate_guard": guard}
                minute_interventions.append(stale_candidate)
                candidate, guard = None, None
            if len(minute_interventions) > 1:
                raise RuntimeError(f"fixed case has multiple interventions at minute {minute}")
            minute_edits = [{"at": minute, "expected_version": row["expected_version"],
                             "raw_bundle": row["raw_bundle"]}
                            for row in edits if row["at"] == minute]
            if len(minute_edits) > 1:
                raise RuntimeError(f"fixed case has multiple bundle edits at minute {minute}")
            step_args = {"scene_id": scene_id, "rounds": 1,
                         "interventions": minute_interventions, "edits": minute_edits}
            call_index += 1
            step_response = _rpc_record(rpc, run_dir, call_index, "step_world", step_args)
            rounds = step_response.get("rounds") if isinstance(step_response, Mapping) else None
            if not isinstance(rounds, list) or len(rounds) != 1:
                raise RuntimeError("one-minute native step did not return exactly one result row")
            _write_once(run_dir / f"step-minute-{minute:03d}.json", rounds[0])
            if arm == "mature_methods":
                for intervention_result in rounds[0].get("interventions", []):
                    if intervention_result.get("status") == "STALE_CANDIDATE":
                        _write_once(run_dir / f"stale-candidate-minute-{minute:03d}.json",
                                    intervention_result)

            stage = f"get_trace_minute_{minute}"
            call_index += 1
            evidence = _rpc_record(rpc, run_dir, call_index, "get_trace", {"scene_id": scene_id})
            _write_once(run_dir / f"native-trace-minute-{minute:03d}.json", evidence)
            active_identity = evidence.get("bundle_identity", {})
            active_bundle_raw = (raw_bundle if active_identity.get("version") == raw_bundle.get("version")
                                 else next((row["raw_bundle"] for row in edits
                                            if row["raw_bundle"].get("version") == active_identity.get("version")), None))
            if not isinstance(active_bundle_raw, Mapping):
                raise RuntimeError("native active bundle version has no fixed suite input")
            active_bundle = load_bundle(dict(active_bundle_raw))
            after = make_snapshot(active_bundle, evidence)
            _write_once(run_dir / f"snapshot-minute-{minute:03d}.json", after.as_dict())

            if arm == "mature_methods" and decision is not None:
                stage = f"advance_from_sealed_minute_{minute}"
                advance_started = time.perf_counter()
                try:
                    advance = advance_from_sealed(decision, decision_snapshot, after)
                finally:
                    costs["sealed_advance"]["calls"] += 1
                    costs["sealed_advance"]["wall_seconds"] += time.perf_counter() - advance_started
                advance["comparison_scope"] = "checkpoint_range_from_last_root_plan_not_per_minute_delta"
                _write_once(run_dir / f"advance-minute-{minute:03d}.json", advance)
                if advance.get("status") == "REPLAN_REQUIRED":
                    previous_root_minute = decision_snapshot.now
                    decision_snapshot = after
                    decision = make_high_plan(active_bundle, after,
                                              f"replan_after_checkpoint_range_{previous_root_minute}_{after.now}")
                    _write_once(run_dir / f"high-level-plan-minute-{minute:03d}.json", decision)
                    candidate, guard = _candidate_and_guard(decision, after)
                else:
                    candidate, guard = None, None

        stage = "final_native_export"
        call_index += 1
        final_trace = _rpc_record(rpc, run_dir, call_index, "get_trace", {"scene_id": scene_id})
        _write_once(run_dir / "final-native-trace.json", final_trace)
        from tools.native_platform_v0.p5.runner import export_db_evidence
        db_evidence, db_status = export_db_evidence(scene_id)
        _write_once(run_dir / "database-readback.json", {"status": db_status,
                                                           "evidence": db_evidence})
        _write_once(run_dir / "costs.json", costs)
        final_source_manifest = _source_manifest()
        _write_once(run_dir / "final-source-manifest.json", final_source_manifest)
        result = {"schema": "mature-methods-arm-result-v1", "case_id": case["case_id"],
                  "arm": arm, "scene_id": scene_id,
                  "run_status": final_trace.get("run_status"),
                  "final_verdicts": final_trace.get("verdicts"),
                  "native_opportunity_attempts": [row for row in final_trace.get("ledger", [])
                      if row.get("event_type") in {"P5_OPPORTUNITY_ATTEMPT", "P5_INTERVENTION"}],
                  "database_export_status": db_status.get("exit_code"),
                  "costs": costs,
                  "source_unchanged_during_arm": identity["source_manifest"]["working_tree_source_sha256"] == final_source_manifest["working_tree_source_sha256"],
                  "final_source_manifest": final_source_manifest,
                  "run_dir": str(run_dir), "source_manifest": identity["source_manifest"]}
        _write_once(run_dir / "result.json", result)
        return result
    except Exception as exc:
        failure = {"schema": "mature-methods-arm-error-v1", "case_id": case["case_id"],
                   "arm": arm, "scene_id": scene_id, "stage": stage,
                   "error_type": type(exc).__name__, "error_message": str(exc)[:1000],
                   "run_dir": str(run_dir)}
        failure["costs"] = costs
        failure["final_source_manifest"] = _source_manifest()
        _write_once(run_dir / "INCOMPLETE_ERROR.json", failure)
        return failure


def run_matched_pair(case_id: str, *, suite_path: Path = SUITE_PATH,
                     runs_dir: Path = RUNS_DIR,
                     rpc: Callable[[str, dict[str, Any]], Any] = rpc_call) -> dict[str, Any]:
    suite_path = suite_path.resolve()
    suite = _read_json(suite_path)
    if suite.get("schema") != "mature-methods-integration-suite-v1":
        raise ValueError("unsupported Mature-Methods suite schema")
    cases = {row["case_id"]: row for row in suite.get("cases", [])}
    if case_id not in cases:
        raise ValueError(f"unknown fixed case id {case_id!r}")
    case = cases[case_id]
    runtime = _runtime_manifest()
    if case.get("preset") not in {"native_default_reject_v0", "hero_intelligence_30_v0"}:
        raise ValueError("suite case has an unsupported native Ensemble preset")
    if suite["common"].get("external_observe_actor_calls") != 0:
        raise ValueError("this protocol forbids external observe_actor sampling")
    pair_dir = _allocate_pair(case_id, runs_dir)
    _write_once(pair_dir / "case-input.json", {"suite": suite, "case": case})
    identity = {"schema": "mature-methods-pair-identity-v1",
                "case_id": case_id, "suite_id": suite["suite_id"],
                "suite_sha256": _sha(suite_path.read_bytes()),
                "source_manifest": _source_manifest(),
                "runtime": runtime,
                "arms": ["baseline", "mature_methods"],
                "matched_inputs": True, "native_director_is_only_controller_difference": True}
    _write_once(pair_dir / "pair-identity.json", identity)
    baseline = _run_arm(pair_dir=pair_dir, case=case, suite=suite, suite_path=suite_path,
                        arm="baseline", rpc=rpc)
    method = _run_arm(pair_dir=pair_dir, case=case, suite=suite, suite_path=suite_path,
                      arm="mature_methods", rpc=rpc)
    pair = {"schema": "mature-methods-pair-result-v1", "case_id": case_id,
            "pair_dir": str(pair_dir), "pair_identity": identity,
            "baseline": baseline, "mature_methods": method,
            "claims": {"superiority_test": False, "n1_algorithm_advantage": None,
                       "arm_results_are_descriptive": True}}
    _write_once(pair_dir / "pair-result.json", pair)
    return pair


def resume_pristine_scene(failed_pair_dir: Path, *, runs_dir: Path = RUNS_DIR,
                          rpc: Callable[[str, dict[str, Any]], Any] = rpc_call) -> dict[str, Any]:
    """One-off, S1-only continuation of a proven untouched failed method scene.

    The original reset is never replayed. The original P5 Director baseline stays
    as a byte-preserved reference; this function creates only a continuation
    evidence directory and executes the failed method arm in the same scene.
    """
    failed_pair_dir = failed_pair_dir.resolve()
    case_input = _read_json(failed_pair_dir / "case-input.json")
    suite, case = case_input["suite"], case_input["case"]
    if case.get("case_id") != "S1-result-only-reject":
        raise ValueError("only the specifically authorized S1 continuation is supported")
    original_method_dir = failed_pair_dir / "mature_methods"
    failure_path = original_method_dir / "INCOMPLETE_ERROR.json"
    failure = _read_json(failure_path)
    if (failure.get("stage") != "initial_high_level_plan"
            or failure.get("error_type") != "RuntimeError"
            or "GTPyhop installation" not in failure.get("error_message", "")):
        raise ValueError("original S1 method failure does not match the authorized runtime-entry failure")
    if list(original_method_dir.glob("step-minute-*.json")):
        raise ValueError("original scene has step artifacts; it is not pristine and will not be resumed")
    if list(original_method_dir.glob("stale-candidate-minute-*.json")):
        raise ValueError("original scene has candidate artifacts; it is not pristine and will not be resumed")
    old_rpc_requests = sorted(path.name for path in original_method_dir.glob("rpc-*-request.json"))
    if old_rpc_requests != ["rpc-0001-reset_p5_scenario-request.json",
                            "rpc-0002-get_trace-request.json"]:
        raise ValueError(f"original scene request history is not reset + initial trace only: {old_rpc_requests!r}")
    if any("observe_actor" in name for name in old_rpc_requests):
        raise ValueError("original scene unexpectedly contains external actor observation sampling")

    suite_path = (Path(__file__).resolve().parent / "cases/suite.json")
    raw_bundle, _ = _case_bundle(case, suite_path)
    common = suite["common"]
    reset_request = _read_json(original_method_dir / old_rpc_requests[0])
    expected_reset = {"bundle": raw_bundle, "initial_social_preset": case["preset"],
                      "horizon": common["horizon"], "seed": common["seed"],
                      "director_enabled": False, "shared_supply": common["shared_supply"],
                      "initial_main_open": common["initial_main_open"]}
    if reset_request != expected_reset:
        raise ValueError("original S1 reset input differs from the frozen case configuration")
    reset_receipt_path = original_method_dir / "rpc-0001-reset_p5_scenario-response.json"
    reset_receipt = _read_json(reset_receipt_path)
    scene = reset_receipt.get("scene", {})
    scene_id = scene.get("scene_id")
    if (scene_id != failure.get("scene_id") or scene.get("now") != 0
            or scene.get("horizon") != common["horizon"]
            or scene.get("seed") != common["seed"]
            or scene.get("director_enabled") is not False
            or scene.get("preset") != case["preset"]
            or scene.get("active_bundle", {}).get("bundle_id") != raw_bundle.get("bundle_id")
            or scene.get("active_bundle", {}).get("version") != raw_bundle.get("version")):
        raise ValueError("saved reset receipt is not the exact pristine S1 method scene")
    expected_snapshot = _read_json(original_method_dir / "initial-snapshot.json")
    if expected_snapshot.get("now") != 0 or expected_snapshot.get("scene_id") != scene_id:
        raise ValueError("saved initial snapshot is not minute zero for the failed S1 scene")

    runtime = _runtime_manifest()
    pair_dir = _allocate_pair("S1-result-only-reject-continuation", runs_dir)
    baseline_result_path = failed_pair_dir / "baseline/result.json"
    _write_once(pair_dir / "baseline-reference.json", {
        "schema": "mature-methods-original-baseline-reference-v1",
        "path": str(baseline_result_path),
        "sha256": _sha(baseline_result_path.read_bytes()),
        "original_baseline_scene": _read_json(baseline_result_path).get("scene_id"),
        "baseline_was_not_replayed": True,
        "performance_comparison_valid": False,
        "performance_limitation": "original baseline used system Python; continuation uses project Evennia venv"})
    _write_once(pair_dir / "continuation-identity.json", {
        "schema": "mature-methods-s1-pristine-continuation-v1",
        "case_id": case["case_id"], "scene_id": scene_id,
        "original_pair_dir": str(failed_pair_dir), "same_existing_scene_reused": True,
        "reset_rpc_replayed": False, "external_observe_actor_calls": 0,
        "original_failure_sha256": _sha(failure_path.read_bytes()),
        "original_reset_receipt_sha256": _sha(reset_receipt_path.read_bytes()),
        "runtime": runtime, "source_manifest": _source_manifest(),
        "comparison_scope": "native-outcome continuation only; no runtime-efficiency comparison"})
    resume_info = {"scene_id": scene_id,
                   "reset_receipt_path": str(reset_receipt_path),
                   "reset_receipt_sha256": _sha(reset_receipt_path.read_bytes()),
                   "failure_path": str(failure_path),
                   "failure_sha256": _sha(failure_path.read_bytes()),
                   "expected_initial_snapshot": expected_snapshot}
    method = _run_arm(pair_dir=pair_dir, case=case, suite=suite,
                      suite_path=suite_path, arm="mature_methods", rpc=rpc,
                      resume_pristine_scene=resume_info)
    result = {"schema": "mature-methods-s1-continuation-result-v1",
              "case_id": case["case_id"], "continuation_dir": str(pair_dir),
              "original_baseline_reference": str(baseline_result_path),
              "baseline_replayed": False, "new_native_scene_created": False,
              "method_arm": method,
              "claims": {"matched_native_input_by_minute0_snapshot": True,
                         "runtime_performance_comparison": False,
                         "overall_method_success": method.get("run_status") == "COMPLETE" and
                            "error_type" not in method}}
    _write_once(pair_dir / "continuation-result.json", result)
    return result


def continue_s1_minute17_checkpoint(failed_pair_dir: Path, prior_continuation_dir: Path, *,
                                    runs_dir: Path = RUNS_DIR,
                                    rpc: Callable[[str, dict[str, Any]], Any] = rpc_call) -> dict[str, Any]:
    """Continue only the authorized S1 scene from its verified sealed minute-17 checkpoint."""
    failed_pair_dir, prior_continuation_dir = failed_pair_dir.resolve(), prior_continuation_dir.resolve()
    case_input = _read_json(failed_pair_dir / "case-input.json")
    suite, case = case_input["suite"], case_input["case"]
    if case.get("case_id") != "S1-result-only-reject":
        raise ValueError("minute-17 continuation is specific to S1-result-only-reject")
    prior_arm = prior_continuation_dir / "mature_methods"
    prior_error_path = prior_arm / "INCOMPLETE_ERROR.json"
    prior_error = _read_json(prior_error_path)
    if (prior_error.get("scene_id") != "20261012075840-41a78a"
            or prior_error.get("stage") != "advance_from_sealed_minute_17"
            or "existing_path" not in prior_error.get("error_message", "")
            and "control-proposal status" not in prior_error.get("error_message", "")):
        raise ValueError("prior S1 stop does not match the authorized minute-17 runner-classification failure")
    if not (prior_arm / "step-minute-017.json").is_file() or \
            (prior_arm / "step-minute-018.json").exists():
        raise ValueError("prior continuation does not end exactly after sealed minute 17")
    if any("observe_actor" in path.name for path in prior_arm.glob("rpc-*-request.json")):
        raise ValueError("prior continuation unexpectedly contains external observe_actor sampling")

    suite_path = Path(__file__).resolve().parent / "cases/suite.json"
    raw_bundle, _ = _case_bundle(case, suite_path)
    bundle = load_bundle(raw_bundle)
    scene_id = prior_error["scene_id"]
    snapshot_path = prior_arm / "snapshot-minute-017.json"
    checkpoint_snapshot = _read_json(snapshot_path)
    plan_path = prior_arm / "high-level-plan-minute-017.json"
    checkpoint_plan = _read_json(plan_path)
    terminal_trace_path = prior_arm / "terminal-native-trace-after-runner-error.json"
    terminal_trace = _read_json(terminal_trace_path)
    terminal_snapshot = snapshot_from_native(bundle, terminal_trace)
    if terminal_snapshot.as_dict() != checkpoint_snapshot:
        raise ValueError("minute-17 terminal live trace differs from the saved snapshot checkpoint")
    if (terminal_snapshot.scene_id != scene_id or terminal_snapshot.now != 17
            or checkpoint_plan.get("scene_id") != scene_id
            or checkpoint_plan.get("based_on_minute") != 17
            or checkpoint_plan.get("trace_identity") != dict(terminal_snapshot.trace_identity)):
        raise ValueError("minute-17 snapshot and final high-level plan identities differ")
    if (checkpoint_plan.get("control_proposal_status") != "PROPOSAL_AVAILABLE"
            or checkpoint_plan.get("control_proposal", {}).get("selected_action") != "NO_OP"
            or checkpoint_plan.get("method_trace", [{}])[0].get("method_id") != "existing_path"):
        raise ValueError("minute-17 checkpoint is not the exact existing_path/NO_OP branch being resumed")
    if _candidate_and_guard(checkpoint_plan, terminal_snapshot) != (None, None):
        raise ValueError("minute-17 no-op plan unexpectedly contains a dispatchable candidate")

    minute_traces = sorted(prior_arm.glob("native-trace-minute-*.json"))
    ledger_prefixes = [_read_json(path).get("ledger", []) for path in minute_traces]
    if len(minute_traces) != 18 or not all(
            len(b) >= len(a) and b[:len(a)] == a
            for a, b in zip(ledger_prefixes, ledger_prefixes[1:])):
        raise ValueError("minute-17 trace history is incomplete or not an ordered sealed-ledger prefix")

    prior_source_manifest = prior_error.get("final_source_manifest", {}).get(
        "working_tree_source_sha256", {})
    protected_core = (
        "tools/native_platform_v0/p5/mature_methods/method_adapters.py",
        "tools/native_platform_v0/p5/mature_methods/narrative_methods.py",
        "tools/native_platform_v0/p5/mature_methods/orchestrator.py",
        "tools/native_platform_v0/p5/service.py",
        "tools/native_platform_v0/p5/planning.py",
        "tools/native_platform_v0/p5/world.py",
        "tools/native_platform_v0/p5/bundle.py",
        "tools/native_platform_v0/p5/monitor.py")
    changed_core = {name: {"at_checkpoint": prior_source_manifest.get(name),
                           "current": _sha((PROJECT_ROOT / name).read_bytes())}
                    for name in protected_core
                    if prior_source_manifest.get(name) != _sha((PROJECT_ROOT / name).read_bytes())}
    if changed_core:
        raise ValueError(f"protected P5 core changed since minute-17 checkpoint: {changed_core!r}")

    runtime = _runtime_manifest()
    pair_dir = _allocate_pair("S1-result-only-reject-minute17-continuation", runs_dir)
    baseline_path = failed_pair_dir / "baseline/result.json"
    _write_once(pair_dir / "baseline-reference.json", {
        "schema": "mature-methods-original-baseline-reference-v1",
        "path": str(baseline_path), "sha256": _sha(baseline_path.read_bytes()),
        "original_baseline_scene": _read_json(baseline_path).get("scene_id"),
        "baseline_was_not_replayed": True, "performance_comparison_valid": False,
        "performance_limitation": "original baseline controller ran under system Python; method continuation uses project venv"})
    _write_once(pair_dir / "checkpoint17-identity.json", {
        "schema": "mature-methods-s1-minute17-continuation-v1",
        "case_id": case["case_id"], "scene_id": scene_id,
        "original_pair_dir": str(failed_pair_dir),
        "pristine_recovery_dir": str(prior_continuation_dir),
        "continued_from_sealed_minute": 17, "reset_rpc_replayed": False,
        "new_scene_created": False, "external_observe_actor_calls": 0,
        "prior_runner_error_sha256": _sha(prior_error_path.read_bytes()),
        "checkpoint_snapshot_sha256": _sha(snapshot_path.read_bytes()),
        "checkpoint_plan_sha256": _sha(plan_path.read_bytes()),
        "terminal_trace_sha256": _sha(terminal_trace_path.read_bytes()),
        "protected_p5_core_unchanged": True,
        "runtime": runtime, "source_manifest": _source_manifest(),
        "comparison_scope": "continuation of same native scene; not a fresh matched replication"})
    continuation = {"scene_id": scene_id, "snapshot_path": str(snapshot_path),
                    "snapshot_sha256": _sha(snapshot_path.read_bytes()),
                    "expected_snapshot": checkpoint_snapshot,
                    "checkpoint_plan": checkpoint_plan,
                    "failure_path": str(prior_error_path),
                    "failure_sha256": _sha(prior_error_path.read_bytes())}
    method = _run_arm(pair_dir=pair_dir, case=case, suite=suite, suite_path=suite_path,
                      arm="mature_methods", rpc=rpc,
                      continue_s1_checkpoint17=continuation)
    result = {"schema": "mature-methods-s1-minute17-continuation-result-v1",
              "case_id": case["case_id"], "continuation_dir": str(pair_dir),
              "original_baseline_reference": str(baseline_path), "baseline_replayed": False,
              "new_native_scene_created": False, "continued_from_minute": 17,
              "prior_pristine_recovery_dir": str(prior_continuation_dir),
              "method_arm": method,
              "claims": {"same_scene_checkpoint_verified": True,
                         "runtime_performance_comparison": False,
                         "overall_method_success": method.get("run_status") == "COMPLETE" and
                             "error_type" not in method}}
    _write_once(pair_dir / "continuation-result.json", result)
    return result


__all__ = ["run_matched_pair", "resume_pristine_scene", "continue_s1_minute17_checkpoint",
           "SUITE_PATH", "RUNS_DIR"]
