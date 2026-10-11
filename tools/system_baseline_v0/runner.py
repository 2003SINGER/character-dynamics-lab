"""Minute-bounded external Sabre controller for the native P5 scene."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
from typing import Any, Callable, Mapping

from tools.native_platform_v0.p3.mcp_stdio import PROJECT_ROOT, rpc_call
from .model import NO_OP, Candidate, PlanningView, project_p5_for_sabre
from .sabre import candidate_from_result, invoke_sabre, render_problem


RUNS_DIR = PROJECT_ROOT / "02_实验/System_Baseline_v0/runs"
BASELINE_GIT_COMMIT = "50eb855"
SOURCE_PATHS = (
    "tools/system_baseline_v0/model.py", "tools/system_baseline_v0/sabre.py",
    "tools/system_baseline_v0/runner.py", "tools/native_platform_v0/p5/bundle.py",
    "tools/native_platform_v0/p5/monitor.py", "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p5/world.py", "tools/native_platform_v0/p5/agency.py",
    "tools/native_platform_v0/p3/control_service.py", "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/scene.py", "tools/native_platform_v0/p3/p4_world.py",
    "tools/native_platform_v0/p3/agency.py", "tools/native_platform_v0/p3/p4_agency.py",
    "tools/native_platform_v0/p3/p4_social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
)


def source_manifest() -> dict[str, str]:
    return {relative: sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
            for relative in SOURCE_PATHS}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _allocate_run_dir(parent: Path, case_id: str) -> Path:
    slug = "".join(char if char.isalnum() or char in "-_" else "-" for char in case_id)[:48]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(12):
        path = parent / f"{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir(parents=True, exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique System Baseline run directory")


def _run_case_impl(case: Mapping[str, Any], *, rpc: Callable[[str, dict[str, Any]], Any],
                   output_parent: str | Path, sabre: Callable[[Path], dict[str, Any]],
                   db_readback: Callable[[str], Any] | None,
                   run_dir: Path | None = None) -> dict[str, Any]:
    """Run one explicit case. Each action is replanned from a fresh sealed prefix.

    `case` keys: id, bundle, preset, horizon, seed, initial_main_open,
    shared_supply, scheduled_edit, and scheduled_intervention. Edits suppress
    any candidate based on the previous bundle; dispatch occurs no earlier
    than the following minute after reading the edited active bundle.
    """
    required = {"id", "bundle", "preset", "horizon"}
    if not isinstance(case, Mapping) or not required <= set(case):
        raise ValueError("case needs id, bundle, preset, and horizon")
    case_id = case["id"]
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("case id must be a nonempty string")
    bundle_path = Path(case["bundle"]).resolve()
    bundle_bytes = bundle_path.read_bytes()
    active_bundle = json.loads(bundle_bytes.decode("utf-8"))
    if not isinstance(active_bundle, dict):
        raise ValueError("case bundle must be a JSON object")
    horizon = case["horizon"]
    if type(horizon) is not int or not 1 <= horizon <= 24:
        raise ValueError("case horizon must be in [1,24]")
    run_dir = run_dir or _allocate_run_dir(Path(output_parent), case_id)
    source_identity = {"baseline_git_commit": BASELINE_GIT_COMMIT,
                       "source_sha256": source_manifest(),
                       "bundle_path": str(bundle_path),
                       "bundle_sha256": sha256(bundle_bytes).hexdigest(),
                       "runner": "tools.system_baseline_v0.runner.run_case"}
    _write_json(run_dir / "case.json", {"case": dict(case), "source_identity": source_identity})

    created = rpc("reset_p5_scenario", {
        "bundle": active_bundle, "initial_social_preset": case["preset"],
        "horizon": horizon, "seed": case.get("seed", 20261012),
        "director_enabled": False, "shared_supply": case.get("shared_supply", False),
        "initial_main_open": case.get("initial_main_open", False)})
    if not isinstance(created, Mapping) or created.get("ok") is not True:
        result = {"status": "RESET_REJECTED", "created": created, "run_dir": str(run_dir)}
        _write_json(run_dir / "result.json", result)
        return result
    scene = created.get("scene")
    scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
    if not isinstance(scene_id, str) or not scene_id:
        raise RuntimeError("native P5 reset returned no scene identity")
    _write_json(run_dir / "native_reset.json", dict(created))
    steps = []
    scheduled_edit = case.get("scheduled_edit")
    intervention_rows = case.get("scheduled_interventions", [])
    if not isinstance(intervention_rows, list) or any(not isinstance(row, Mapping) for row in intervention_rows):
        raise ValueError("scheduled_interventions must be a list of explicit P5 intervention rows")
    edited = False

    for tick in range(horizon):
        trace = rpc("get_trace", {"scene_id": scene_id})
        if not isinstance(trace, Mapping):
            raise RuntimeError("native get_trace returned a non-object")
        view = project_p5_for_sabre(trace, active_bundle, scene_id)
        next_minute = view.now + 1
        edit_now = (isinstance(scheduled_edit, Mapping) and not edited
                    and scheduled_edit.get("at") == next_minute)
        interventions_due = [dict(row) for row in intervention_rows
                             if row.get("at") == next_minute]
        if len(interventions_due) > 1:
            raise ValueError("at most one player intervention may be scheduled per minute")
        player_now = bool(interventions_due)
        candidate: Candidate | None = None
        problem = None
        sabre_result: dict[str, Any] | None = None
        if not edit_now and not view.hard_route_blockers and view.hard_route_targets:
            problem = render_problem(view)
            problem_path = run_dir / "problems" / f"minute-{view.now:02d}.problem"
            problem_path.parent.mkdir(parents=True, exist_ok=True)
            with problem_path.open("x", encoding="utf-8") as handle:
                handle.write(problem)
            sabre_result = sabre(problem_path)
            candidate = candidate_from_result(view, problem, sabre_result)
        elif view.hard_unresolved:
            sabre_result = {"status": "HARD_RESIDUAL_NO_SAT_CLAIM",
                            "hard_unresolved": list(view.hard_unresolved)}

        edits = []
        if edit_now:
            new_path = Path(scheduled_edit["bundle"]).resolve()
            new_bytes = new_path.read_bytes()
            new_bundle = json.loads(new_bytes.decode("utf-8"))
            edit_row = {"at": next_minute,
                        "expected_version": active_bundle["version"],
                        "raw_bundle": new_bundle}
            edits.append(edit_row)
        interventions = []
        if player_now:
            interventions.append(interventions_due[0])
        native_plan_found = (isinstance(sabre_result, Mapping)
                             and sabre_result.get("status") == "PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                             and sabre_result.get("returncode") == 0)
        if (candidate is not None and native_plan_found
                and candidate.selected_action != NO_OP and not (edit_now or player_now)):
            interventions.append({"at": next_minute, "kind": "author_opportunity",
                                  "operation": "open_passage",
                                  "opportunity_id": candidate.opportunity_id,
                                  "candidate_guard": candidate.native_guard()})

        step_result = rpc("step_world", {"scene_id": scene_id, "rounds": 1,
                                          "interventions": interventions, "edits": edits})
        edit_receipt = None
        if edit_now:
            rounds = step_result.get("rounds", []) if isinstance(step_result, Mapping) else []
            first = rounds[0] if rounds and isinstance(rounds[0], Mapping) else {}
            edits_result = first.get("edits", [])
            edit_receipt = edits_result[0] if edits_result and isinstance(edits_result[0], Mapping) else None
            if edit_receipt and edit_receipt.get("ok") is True:
                edited = True
                active_bundle = new_bundle
        step_row = {"minute_from": view.now, "minute_to": next_minute,
                    "view_sha256": view.evidence_sha256,
                    "problem_sha256": None if problem is None else sha256(problem.encode()).hexdigest(),
                    "sabre": sabre_result, "candidate": None if candidate is None else {
                        "action": candidate.selected_action,
                        "opportunity_id": candidate.opportunity_id,
                        "bundle_version": candidate.bundle_version,
                        "guard": candidate.native_guard(),
                        "plan_sha256": candidate.plan_sha256},
                    "edit": None if not edit_now else {
                        "bundle": str(new_path), "sha256": sha256(new_bytes).hexdigest(),
                        "expected_version": edit_row["expected_version"],
                        "native_receipt": edit_receipt},
                    "player_intervention": player_now, "native_step": step_result}
        steps.append(step_row)
        _write_json(run_dir / "steps" / f"minute-{next_minute:02d}.json", step_row)

    final_trace = rpc("get_trace", {"scene_id": scene_id})
    _write_json(run_dir / "native_final_trace.json", final_trace)
    db_result = None if db_readback is None else db_readback(scene_id)
    if db_result is None and db_readback is None:
        try:
            from tools.native_platform_v0.p5.runner import export_db_evidence
            db_result = export_db_evidence(scene_id)
        except Exception as exc:
            db_result = {"status": "DB_READBACK_ERROR", "error_type": type(exc).__name__}
    db_evidence, db_meta = (None, {"status": "NOT_AVAILABLE"})
    if isinstance(db_result, tuple) and len(db_result) == 2:
        db_evidence, db_meta = db_result
    if (isinstance(db_evidence, Mapping)
            and (db_evidence.get("schema") != "native-p3-db-evidence-v1"
                 or scene_id not in db_evidence.get("selection", {}).get("scene_ids", []))):
        db_evidence = None
        db_meta = {"status": "INVALID_DB_READBACK_EVIDENCE"}
    if db_evidence is not None:
        _write_json(run_dir / "independent_db_readback.json", db_evidence)
    _write_json(run_dir / "db_readback_meta.json", db_meta)
    result = {"status": "DEVELOPMENT_RUN_RECORDED",
              "scene_id": scene_id, "run_status": final_trace.get("run_status"),
              "steps": len(steps), "run_dir": str(run_dir),
              "source_identity": source_identity,
              "native_final_trace_sha256": sha256(json.dumps(final_trace, sort_keys=True,
                  ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
              "db_readback_recorded": bool(
                  db_evidence is not None and db_meta.get("exit_code") == 0
                  and isinstance(db_meta.get("artifact_sha256"), str)),
              "hard_unresolved_constraints": list(
                  project_p5_for_sabre(final_trace, active_bundle, scene_id).hard_unresolved)}
    _write_json(run_dir / "result.json", result)
    return result


def run_case(case: Mapping[str, Any], *, rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
             output_parent: str | Path = RUNS_DIR,
             sabre: Callable[[Path], dict[str, Any]] = invoke_sabre,
             db_readback: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Run a case and preserve an explicit incomplete artifact on exceptions."""
    case_id = case.get("id", "invalid-case") if isinstance(case, Mapping) else "invalid-case"
    run_dir = _allocate_run_dir(Path(output_parent), str(case_id))
    try:
        return _run_case_impl(case, rpc=rpc, output_parent=output_parent,
                              sabre=sabre, db_readback=db_readback, run_dir=run_dir)
    except Exception as exc:
        error = {"status": "INCOMPLETE_ERROR", "case_id": str(case_id),
                 "error_type": type(exc).__name__, "message": str(exc)[:1000],
                 "run_dir": str(run_dir)}
        _write_json(run_dir / "INCOMPLETE_ERROR.json", error)
        return error


def run_stale_edit_negative(*, bundle_path: str | Path,
                            edited_bundle_path: str | Path,
                            output_parent: str | Path = RUNS_DIR,
                            rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
                            sabre: Callable[[Path], dict[str, Any]] = invoke_sabre,
                            db_readback: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Deliberately submit an old candidate after a same-minute native CAS edit.

    This is a named adversarial negative control, not the mainline controller
    policy (which suppresses dispatch on edit minutes).
    """
    run_dir = _allocate_run_dir(Path(output_parent), "stale-edit-negative")
    try:
        original_path = Path(bundle_path).resolve()
        edited_path = Path(edited_bundle_path).resolve()
        original_bytes, edited_bytes = original_path.read_bytes(), edited_path.read_bytes()
        original = json.loads(original_bytes.decode("utf-8"))
        edited = json.loads(edited_bytes.decode("utf-8"))
        created = rpc("reset_p5_scenario", {
            "bundle": original, "initial_social_preset": "native_default_reject_v0",
            "horizon": 8, "seed": 20261012, "director_enabled": False,
            "shared_supply": False, "initial_main_open": False})
        scene = created.get("scene") if isinstance(created, Mapping) else None
        scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
        if not isinstance(scene_id, str) or not scene_id:
            raise RuntimeError("native stale-guard reset returned no scene ID")
        trace = rpc("get_trace", {"scene_id": scene_id})
        view = project_p5_for_sabre(trace, original, scene_id)
        problem = render_problem(view)
        problem_path = run_dir / "stale-candidate.problem"
        with problem_path.open("x", encoding="utf-8") as handle:
            handle.write(problem)
        plan = sabre(problem_path)
        candidate = candidate_from_result(view, problem, plan)
        if (plan.get("status") != "PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                or plan.get("returncode") != 0
                or candidate.opportunity_id is None):
            raise RuntimeError("Sabre did not produce the preconditioned stale candidate")
        step = rpc("step_world", {"scene_id": scene_id, "rounds": 1,
            "edits": [{"at": 1, "expected_version": original["version"],
                       "raw_bundle": edited}],
            "interventions": [{"at": 1, "kind": "author_opportunity",
                               "operation": "open_passage",
                               "opportunity_id": candidate.opportunity_id,
                               "candidate_guard": candidate.native_guard()}]})
        final_trace = rpc("get_trace", {"scene_id": scene_id})
        round_rows = step.get("rounds", []) if isinstance(step, Mapping) else []
        first = round_rows[0] if round_rows and isinstance(round_rows[0], Mapping) else {}
        edit_rows = first.get("edits", [])
        intervention_rows = first.get("interventions", [])
        edit_receipt = edit_rows[0] if edit_rows and isinstance(edit_rows[0], Mapping) else {}
        intervention_receipt = (intervention_rows[0]
                                if intervention_rows and isinstance(intervention_rows[0], Mapping) else {})
        route_state = next((dict(row["routes"]) for row in final_trace.get("world_snapshots", [])
                            if isinstance(row, Mapping) and row.get("minute") == 1
                            and isinstance(row.get("routes"), Mapping)), {})
        no_route_opened = bool(route_state) and not any(value is True for value in route_state.values())
        guard_rejected = intervention_receipt.get("status") == "STALE_CANDIDATE"
        edit_accepted = edit_receipt.get("ok") is True
        result = {"status": ("STALE_GUARD_NEGATIVE_PASS" if guard_rejected and no_route_opened
                             and edit_accepted else "STALE_GUARD_NEGATIVE_FAIL"),
                  "scene_id": scene_id, "run_dir": str(run_dir),
                  "candidate_bundle_version": candidate.bundle_version,
                  "native_active_bundle": final_trace.get("bundle_identity"),
                  "native_edit_accepted": edit_accepted,
                  "native_intervention_status": intervention_receipt.get("status"),
                  "route_state_at_dispatch_minute": route_state,
                  "route_opened_after_stale_dispatch": any(value is True for value in route_state.values()),
                  "native_guard_rejected": guard_rejected}
        _write_json(run_dir / "case.json", {"scenario": "same-minute-edit-then-old-plan-negative",
            "baseline_git_commit": BASELINE_GIT_COMMIT, "source_sha256": source_manifest(),
            "original_bundle_sha256": sha256(original_bytes).hexdigest(),
            "edited_bundle_sha256": sha256(edited_bytes).hexdigest()})
        _write_json(run_dir / "native_reset.json", dict(created))
        _write_json(run_dir / "stale-candidate.json", {"problem": problem, "plan": plan,
            "candidate_guard": candidate.native_guard(), "native_step": step})
        _write_json(run_dir / "native_final_trace.json", final_trace)
        if db_readback is None:
            from tools.native_platform_v0.p5.runner import export_db_evidence
            db_readback = export_db_evidence
        evidence, meta = db_readback(scene_id)
        db_valid = (isinstance(evidence, Mapping)
                    and evidence.get("schema") == "native-p3-db-evidence-v1"
                    and scene_id in evidence.get("selection", {}).get("scene_ids", [])
                    and isinstance(meta, Mapping) and meta.get("exit_code") == 0
                    and isinstance(meta.get("artifact_sha256"), str))
        if db_valid:
            _write_json(run_dir / "independent_db_readback.json", evidence)
        _write_json(run_dir / "db_readback_meta.json", meta)
        result["db_readback_recorded"] = db_valid
        result["db_evidence_sha256"] = (sha256(json.dumps(evidence, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode()).hexdigest() if db_valid else None)
        _write_json(run_dir / "result.json", result)
        return result
    except Exception as exc:
        error = {"status": "INCOMPLETE_ERROR", "case_id": "stale-edit-negative",
                 "error_type": type(exc).__name__, "message": str(exc)[:1000],
                 "run_dir": str(run_dir)}
        _write_json(run_dir / "INCOMPLETE_ERROR.json", error)
        return error


__all__ = ["RUNS_DIR", "run_case", "run_stale_edit_negative"]
