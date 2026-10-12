"""Record one bounded Sabre-to-native-P5 integration run.

Sabre's non-route actions remain predictions/conditional handoffs. The only
native commands this runner can submit are the two registered, guarded author
opportunities; NPC delivery and social responses stay native and autonomous.
"""
from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import secrets
from time import perf_counter
from typing import Any, Callable, Mapping

from tools.native_platform_v0.p3.mcp_stdio import PROJECT_ROOT, rpc_call
from .audit import build_step_audit
from .model import build_snapshot
from .sabre import SEARCH_LIMITS, decode_plan, invoke_sabre, projection_status, render_problem


RUNS_DIR = PROJECT_ROOT / "02_实验/Planner_Adapter_Integration_v1/runs"
VALIDATION_DIR = PROJECT_ROOT / "02_实验/Planner_Adapter_Integration_v1/validation/real-source-runs"
BASELINE_GIT_COMMIT = "40048c7cf778e9110d6305fd992c8c60f186263a"
SEARCH_CONFIG_ID = "planner-adapter-sabre-r2"
SEARCH_LIMITS_R2 = {"revision": "primitive-domain-r2",
    "revision_reason": "r1 hit the inherited 200-node cap in 29ms (604 generated), before its 5s native time limit",
    "method": "bf", "cost": "t", "heuristic": "h+",
    "epistemic_limit": 1, "max_visited": 10000, "max_generated": 100000,
    "time_limit_ms": 5000, "author_limit": 24, "character_limit": 16,
    "heap_min": "64m", "heap_max": "1g", "stack_size": "8m"}
SOURCE_PATHS = (
    "tools/planner_adapter_integration_v1/model.py",
    "tools/planner_adapter_integration_v1/sabre.py",
    "tools/planner_adapter_integration_v1/runner.py",
    "tools/planner_adapter_integration_v1/audit.py",
    "tools/native_platform_v0/p5/bundle.py",
    "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p5/world.py",
    "tools/native_platform_v0/p5/agency.py",
    "tools/native_platform_v0/p5/planning.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
)
def _sample_actor_observations(scene_id: str, minute: int,
                               rpc: Callable[[str, dict[str, Any]], Any], *,
                               on_sample: Callable[[str, Mapping[str, Any]], None] | None = None
                               ) -> dict[str, Any]:
    """Sample both actor-local O views in fixed A-then-B order, without stepping W."""
    observations = {}
    for alias, role in (("A", "courier"), ("B", "resident")):
        result = rpc("observe_actor", {"scene_id": scene_id, "actor_role": role})
        local = result.get("local_observation") if isinstance(result, Mapping) else None
        if (not isinstance(result, Mapping) or result.get("scene_id") != scene_id
                or result.get("actor_role") != role or not isinstance(local, Mapping)):
            raise ValueError(f"native actor-local observation unavailable for {alias}/{role}")
        observations[alias] = {"actor_role": role, "local_observation": dict(local)}
        if on_sample is not None:
            on_sample(alias, observations[alias])
    return {"schema": "planner-adapter-actor-observation-v1",
            "source": "p3.control_service.observe_actor", "scene_id": scene_id,
            "sampled_at_minute": minute, "sampling_order": ["A", "B"],
            "observations": observations}


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _allocate(parent: Path, case_id: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in case_id)[:48]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(16):
        path = parent / f"{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            pass
    raise FileExistsError("could not allocate a unique integration run directory")


def _source_hashes() -> dict[str, str]:
    return {p: sha256((PROJECT_ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}


def _validate_search_revision() -> None:
    if dict(SEARCH_LIMITS) != SEARCH_LIMITS_R2:
        raise RuntimeError(f"expected frozen {SEARCH_CONFIG_ID} limits; found {dict(SEARCH_LIMITS)!r}")


def _native_action(plan: Mapping[str, Any]) -> tuple[str | None, str | None]:
    actions = plan.get("plan_actions", [])
    decoded = decode_plan(actions if isinstance(actions, list) else [])
    action = decoded["first_action"]
    if action == "open_main_passage()":
        return action, "open_main_passage"
    if action == "open_side_passage()":
        return action, "open_side_passage"
    return None, None


def _normalized_search_status(plan: Mapping[str, Any], projection: Mapping[str, Any]) -> str:
    """Keep search exhaustion distinct from indeterminate/stale projection."""
    if projection.get("wait_reason"):
        return "WAITING_FOR_NATIVE_PROGRESS"
    if projection.get("hard_residuals") or projection.get("dispatchable") is not True:
        return "PROJECTION_INDETERMINATE"
    if plan.get("status") == "SUCCESS" and plan.get("returncode") == 0:
        return ("CANDIDATE_FOUND_NOT_EXECUTION_EVIDENCE"
                if plan.get("plan_actions") else "NO_CANDIDATE")
    return str(plan.get("status", "SABRE_STATUS_UNKNOWN"))


def _dispatch_allowed(*, method: str, plan: Mapping[str, Any], decoded: Mapping[str, Any],
                      projection: Mapping[str, Any], opportunity: str | None,
                      player_intervention: Any, edit_now: bool) -> bool:
    return (method == "sabre" and plan.get("status") == "SUCCESS"
            and plan.get("returncode") == 0
            and decoded.get("native_dispatchable") is True
            and projection.get("dispatchable") is True
            and not projection.get("hard_residuals")
            and not projection.get("wait_reason")
            and opportunity is not None and not player_intervention and not edit_now)


def run_snapshot_pilot(*, bundle_path: str | Path, preset: str = "native_default_reject_v0",
                       horizon: int = 24, seed: int = 20261012,
                       output_parent: str | Path = VALIDATION_DIR,
                       rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
                       sabre: Callable[[Path], dict[str, Any]] = invoke_sabre) -> dict[str, Any]:
    """Search one real sealed P5 source snapshot without advancing its clock.

    This is a source/model pilot only: it dispatches no candidate and is not a
    method comparison. Its raw traces and local-O envelope are immutable evidence.
    """
    run_dir = _allocate(Path(output_parent), "real-source-snapshot-pilot")
    stage = "initialize"
    scene_id = None
    try:
        _validate_search_revision()
        bundle_file = Path(bundle_path).resolve()
        bundle_bytes = bundle_file.read_bytes()
        raw_bundle = json.loads(bundle_bytes.decode("utf-8"))
        source_hashes = _source_hashes()
        identity = {"schema": "planner-adapter-real-source-snapshot-pilot-v1",
            "evidence_class": "REAL_P5_SNAPSHOT_SEARCH_NO_NATIVE_DISPATCH",
            "bundle_path": str(bundle_file),
            "bundle_sha256": sha256(bundle_bytes).hexdigest(),
            "baseline_git_commit": BASELINE_GIT_COMMIT,
            "search_config_id": SEARCH_CONFIG_ID, "search_limits": dict(SEARCH_LIMITS),
            "source_sha256": source_hashes,
            "scoped_worktree_sha256": sha256(json.dumps(source_hashes, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()}
        _json(run_dir / "identity.json", identity)
        stage = "reset_p5_scenario"
        created = rpc("reset_p5_scenario", {"bundle": raw_bundle,
            "initial_social_preset": preset, "horizon": horizon, "seed": seed,
            "director_enabled": False, "shared_supply": False, "initial_main_open": False})
        _json(run_dir / "native_reset.json", created)
        scene = created.get("scene") if isinstance(created, Mapping) else None
        scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
        if not isinstance(scene_id, str) or not scene_id:
            raise RuntimeError(f"real-source reset rejected or returned no scene id: {created!r}")
        _json(run_dir / "scene_identity.json", {"scene_id": scene_id,
            "bundle_id": scene.get("bundle_id"), "bundle_version": scene.get("bundle_version")})
        stage = "get_trace_before_observation"
        before = rpc("get_trace", {"scene_id": scene_id})
        _json(run_dir / "native_initial_trace.json", before)
        minute = before.get("now") if isinstance(before, Mapping) else None
        if type(minute) is not int:
            raise RuntimeError("real-source trace lacks current minute")
        stage = "observe_actor_A_then_B"
        def persist_sample(alias: str, sample: Mapping[str, Any]) -> None:
            _json(run_dir / f"actor_observation_{alias}.json", sample)
        actor_samples = _sample_actor_observations(scene_id, minute, rpc,
                                                    on_sample=persist_sample)
        _json(run_dir / "actor_observations.json", actor_samples)
        stage = "get_trace_after_observation"
        trace = rpc("get_trace", {"scene_id": scene_id})
        _json(run_dir / "native_source_trace.json", trace)
        if not isinstance(trace, Mapping) or trace.get("now") != minute:
            raise RuntimeError("real-source world advanced during A/B observation sampling")
        stage = "build_snapshot"
        snapshot = build_snapshot(trace, raw_bundle, scene_id=scene_id,
                                  actor_observations=actor_samples)
        projection = projection_status(snapshot)
        _json(run_dir / "snapshot.json", asdict(snapshot))
        _json(run_dir / "projection_status.json", projection)
        stage = "render_problem"
        problem = render_problem(snapshot)
        problem_path = run_dir / "real-source.problem"
        with problem_path.open("x", encoding="utf-8") as stream:
            stream.write(problem)
        stage = "invoke_sabre"
        plan = sabre(problem_path)
        actions = plan.get("plan_actions", []) if isinstance(plan, Mapping) else []
        decoded = decode_plan(actions if isinstance(actions, list) else [],
            native_status=("PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                           if isinstance(plan, Mapping) and plan.get("status") == "SUCCESS"
                           and plan.get("returncode") == 0 else "NO_CANDIDATE"))
        stage = "get_trace_after_search"
        after_search = rpc("get_trace", {"scene_id": scene_id})
        same_frontier = (after_search.get("now") == minute
                         and after_search.get("complete_through") == trace.get("complete_through"))
        _json(run_dir / "sabre_result.json", {"raw_result": plan, "decoded_plan": decoded,
             "normalized_search_status": _normalized_search_status(plan, projection),
             "candidate_dispatched": False})
        _json(run_dir / "native_after_search_trace.json", after_search)
        result = {"status": "REAL_SOURCE_SNAPSHOT_RECORDED" if same_frontier
                  else "REAL_SOURCE_FRONTIER_CHANGED_UNEXPECTEDLY",
                  "scene_id": scene_id, "minute": minute, "same_frontier_after_search": same_frontier,
                  "normalized_search_status": _normalized_search_status(plan, projection),
                  "run_dir": str(run_dir), "identity": identity}
        _json(run_dir / "result.json", result)
        return result
    except Exception as exc:
        result = {"status": "INCOMPLETE_ERROR", "case_id": "real-source-snapshot-pilot",
                  "error_type": type(exc).__name__, "message": str(exc)[:1000],
                  "stage": stage, "scene_id": scene_id, "run_dir": str(run_dir)}
        _json(run_dir / "INCOMPLETE_ERROR.json", result)
        return result


def replay_saved_snapshot_pilot(*, scene_id: str, bundle_path: str | Path,
                               prior_run_dir: str | Path,
                               output_parent: str | Path = VALIDATION_DIR,
                               rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
                               sabre: Callable[[Path], dict[str, Any]] = invoke_sabre
                               ) -> dict[str, Any]:
    """Search a prior sealed native snapshot/O on its existing scene; no reset or sampling."""
    run_dir = _allocate(Path(output_parent), "real-source-snapshot-replay")
    stage = "initialize"
    try:
        _validate_search_revision()
        prior = Path(prior_run_dir).resolve()
        original_identity = json.loads((prior / "identity.json").read_text(encoding="utf-8"))
        trace = json.loads((prior / "native_source_trace.json").read_text(encoding="utf-8"))
        observations = json.loads((prior / "actor_observations.json").read_text(encoding="utf-8"))
        bundle_file = Path(bundle_path).resolve()
        bundle_bytes = bundle_file.read_bytes()
        raw_bundle = json.loads(bundle_bytes.decode("utf-8"))
        if (trace.get("scene_id") != scene_id or observations.get("scene_id") != scene_id
                or trace.get("now") != observations.get("sampled_at_minute")):
            raise ValueError("saved native trace/actor observations do not match requested scene and minute")
        stage = "verify_existing_sealed_frontier"
        current = rpc("get_trace", {"scene_id": scene_id})
        if (not isinstance(current, Mapping) or current.get("scene_id") != scene_id
                or current.get("now") != trace.get("now")
                or current.get("complete_through") != trace.get("complete_through")
                or current.get("ledger") != trace.get("ledger")
                or (current.get("typed_trace") or {}).get("events")
                   != (trace.get("typed_trace") or {}).get("events")):
            raise RuntimeError("existing native scene no longer matches saved sealed prefix; replay refused")
        _json(run_dir / "native_frontier_verification.json", current)
        source_hashes = _source_hashes()
        identity = {"schema": "planner-adapter-real-source-snapshot-replay-v1",
            "evidence_class": "REAL_P5_SAVED_SNAPSHOT_REPLAY_NO_NATIVE_DISPATCH",
            "scene_id": scene_id, "minute": trace.get("now"), "bundle_path": str(bundle_file),
            "bundle_sha256": sha256(bundle_bytes).hexdigest(), "prior_run_dir": str(prior),
            "original_native_source_sha256": original_identity.get("source_sha256"),
            "baseline_git_commit": BASELINE_GIT_COMMIT,
            "search_config_id": SEARCH_CONFIG_ID, "search_limits": dict(SEARCH_LIMITS),
            "source_sha256": source_hashes,
            "scoped_worktree_sha256": sha256(json.dumps(source_hashes, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()}
        _json(run_dir / "identity.json", identity)
        _json(run_dir / "native_source_trace.json", trace)
        _json(run_dir / "actor_observations.json", observations)
        stage = "build_snapshot"
        snapshot = build_snapshot(trace, raw_bundle, scene_id=scene_id,
                                  actor_observations=observations)
        projection = projection_status(snapshot)
        _json(run_dir / "snapshot.json", asdict(snapshot))
        _json(run_dir / "projection_status.json", projection)
        stage = "render_problem"
        problem = render_problem(snapshot)
        problem_path = run_dir / "real-source.problem"
        with problem_path.open("x", encoding="utf-8") as stream:
            stream.write(problem)
        stage = "invoke_sabre"
        plan = sabre(problem_path)
        actions = plan.get("plan_actions", []) if isinstance(plan, Mapping) else []
        decoded = decode_plan(actions if isinstance(actions, list) else [],
            native_status=("PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                           if isinstance(plan, Mapping) and plan.get("status") == "SUCCESS"
                           and plan.get("returncode") == 0 else "NO_CANDIDATE"))
        _json(run_dir / "sabre_result.json", {"raw_result": plan, "decoded_plan": decoded,
            "normalized_search_status": _normalized_search_status(plan, projection),
            "candidate_dispatched": False})
        result = {"status": "REAL_SOURCE_SAVED_SNAPSHOT_SEARCH_RECORDED",
            "scene_id": scene_id, "minute": trace.get("now"),
            "normalized_search_status": _normalized_search_status(plan, projection),
            "run_dir": str(run_dir), "identity": identity}
        _json(run_dir / "result.json", result)
        return result
    except Exception as exc:
        result = {"status": "INCOMPLETE_ERROR", "case_id": "real-source-snapshot-replay",
            "error_type": type(exc).__name__, "message": str(exc)[:1000],
            "stage": stage, "scene_id": scene_id, "run_dir": str(run_dir)}
        _json(run_dir / "INCOMPLETE_ERROR.json", result)
        return result


def _db_evidence(scene_id: str, exporter: Callable[[str], Any] | None) -> tuple[Any, Any]:
    try:
        if exporter is None:
            from tools.native_platform_v0.p5.runner import export_db_evidence
            exporter = export_db_evidence
        result = exporter(scene_id)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return None, {"status": "INVALID_EXPORTER_RETURN", "return_type": type(result).__name__}
    except Exception as exc:  # Preserve the native trajectory even if independent readback fails.
        return None, {"status": "DB_READBACK_ERROR", "error_type": type(exc).__name__,
                      "message": str(exc)[:500]}


def run_case(case: Mapping[str, Any], *, rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
             output_parent: str | Path = RUNS_DIR,
             sabre: Callable[[Path], dict[str, Any]] = invoke_sabre,
             db_exporter: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Run a fixed case minute-by-minute and preserve every failure artifact."""
    case_id = case.get("id", "invalid-case") if isinstance(case, Mapping) else "invalid-case"
    run_dir = _allocate(Path(output_parent), str(case_id))
    try:
        if not isinstance(case, Mapping) or not {"id", "bundle", "preset", "horizon"} <= set(case):
            raise ValueError("case requires id, bundle, preset and horizon")
        _validate_search_revision()
        bundle_path = Path(case["bundle"]).resolve()
        bundle_bytes = bundle_path.read_bytes()
        raw_bundle = json.loads(bundle_bytes.decode("utf-8"))
        if not isinstance(raw_bundle, dict):
            raise ValueError("bundle must be a JSON object")
        horizon = case["horizon"]
        if type(horizon) is not int or not 1 <= horizon <= 24:
            raise ValueError("horizon must be an integer in [1,24]")
        identity = {"case": dict(case), "bundle_sha256": sha256(bundle_bytes).hexdigest(),
                    "baseline_git_commit": BASELINE_GIT_COMMIT,
                    "search_config_id": SEARCH_CONFIG_ID,
                    "search_limits": dict(SEARCH_LIMITS),
                    "source_sha256": _source_hashes(), "runner": "planner_adapter_integration_v1"}
        identity["scoped_worktree_sha256"] = sha256(json.dumps(
            identity["source_sha256"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        _json(run_dir / "case.json", identity)
        created = rpc("reset_p5_scenario", {
            "bundle": raw_bundle, "initial_social_preset": case["preset"],
            "horizon": horizon, "seed": case.get("seed", 20261012),
            "director_enabled": case.get("method") == "p5_director",
            "shared_supply": case.get("shared_supply", False),
            "initial_main_open": case.get("initial_main_open", False)})
        _json(run_dir / "native_reset.json", created)
        scene = created.get("scene") if isinstance(created, Mapping) else None
        scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
        if not isinstance(scene_id, str) or not scene_id:
            raise RuntimeError(f"native reset rejected or returned no scene id: {created!r}")
        steps = []
        edit_path = case.get("scheduled_edit")
        new_bundle = None
        if isinstance(edit_path, Mapping):
            candidate_path = Path(edit_path["bundle"]).resolve()
            new_bundle = json.loads(candidate_path.read_text(encoding="utf-8"))
        scheduled = {int(row["at"]): row for row in case.get("scheduled_interventions", [])}
        method = case.get("method", "sabre")
        if method not in {"sabre", "p5_director"}:
            raise ValueError("method must be sabre or p5_director")
        for minute_to in range(1, horizon + 1):
            before_sampling = rpc("get_trace", {"scene_id": scene_id})
            sample_minute = before_sampling.get("now") if isinstance(before_sampling, Mapping) else None
            if type(sample_minute) is not int:
                raise RuntimeError("native pre-sample trace has no current minute")
            actor_samples = _sample_actor_observations(scene_id, sample_minute, rpc)
            trace = rpc("get_trace", {"scene_id": scene_id})
            if not isinstance(trace, Mapping) or trace.get("now") != sample_minute:
                raise RuntimeError("world minute changed during matched actor observation sampling")
            snapshot = build_snapshot(trace, raw_bundle, scene_id=scene_id,
                                      actor_observations=actor_samples)
            problem = None
            plan = {"status": "NOT_RUN_CONTROL_METHOD"}
            decoded_plan = {"handoff_status": "NOT_APPLICABLE_CONTROL_METHOD"}
            projection = {"dispatchable": False, "status": "NOT_RUN_CONTROL_METHOD"}
            action, opportunity = None, None
            adapter_started = perf_counter()
            if method == "sabre":
                projection = projection_status(snapshot)
                problem = render_problem(snapshot)
                problem_path = run_dir / "problems" / f"minute-{snapshot.minute:02d}.problem"
                problem_path.parent.mkdir(parents=True, exist_ok=True)
                with problem_path.open("x", encoding="utf-8") as stream:
                    stream.write(problem)
                plan = sabre(problem_path)
                actions = plan.get("plan_actions", []) if isinstance(plan, Mapping) else []
                decoded_plan = decode_plan(actions if isinstance(actions, list) else [],
                    native_status=("PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                                   if plan.get("status") == "SUCCESS"
                                   and plan.get("returncode") == 0 else "NO_CANDIDATE"))
                action = decoded_plan.get("dispatch_action")
                opportunity = {"open_main_passage()": "open_main_passage",
                               "open_side_passage()": "open_side_passage"}.get(action)
            adapter_wall_seconds = perf_counter() - adapter_started if method == "sabre" else None
            complete = trace.get("complete_through", {})
            frontier = complete.get("events") if isinstance(complete, Mapping) else None
            value_frontier = complete.get("values") if isinstance(complete, Mapping) else None
            guard = None
            if opportunity is not None:
                guard = {"scene_id": scene_id, "bundle_version": snapshot.bundle_version,
                         "based_on_minute": snapshot.minute, "events_through": frontier,
                         "values_through": value_frontier, "selected_action": opportunity,
                         "opportunity_id": opportunity}
            interventions = []
            player = scheduled.get(minute_to)
            if player:
                interventions.append(dict(player))
            # An edit on this tick takes precedence; the old candidate is never dispatched.
            edit_now = isinstance(edit_path, Mapping) and edit_path.get("at") == minute_to
            dispatchable = _dispatch_allowed(method=method, plan=plan, decoded=decoded_plan,
                projection=projection, opportunity=opportunity,
                player_intervention=player, edit_now=edit_now)
            if dispatchable:
                interventions.append({"at": minute_to, "kind": "author_opportunity",
                                      "operation": "open_passage", "opportunity_id": opportunity,
                                      "candidate_guard": guard})
            edits = []
            if edit_now and new_bundle is not None:
                edits.append({"at": minute_to, "expected_version": raw_bundle["version"],
                              "raw_bundle": new_bundle})
            native_step_started = perf_counter()
            step = rpc("step_world", {"scene_id": scene_id, "rounds": 1,
                                       "interventions": interventions, "edits": edits})
            native_step_wall_seconds = perf_counter() - native_step_started
            after_trace = rpc("get_trace", {"scene_id": scene_id})
            step_audit = build_step_audit(decoded_plan=decoded_plan, native_step=step,
                                          before_trace=trace, after_trace=after_trace,
                                          candidate_bundle_version=snapshot.bundle_version,
                                          hard_requirements=snapshot.hard_requirements,
                                          candidate_constraint_statuses=snapshot.constraint_statuses)
            row = {"minute_from": snapshot.minute, "minute_to": minute_to,
                   "snapshot_sha256": snapshot.source_trace_sha256,
                   "problem_sha256": (sha256(problem.encode("utf-8")).hexdigest()
                                      if problem is not None else None),
                   "method": method,
                   "sabre": plan, "ordered_actions": plan.get("plan_actions", []),
                   "decoded_plan": decoded_plan,
                   "projection_status": projection,
                   "normalized_search_status": _normalized_search_status(plan, projection),
                   "adapter_and_search_wall_seconds": adapter_wall_seconds,
                   "native_step_rpc_wall_seconds": native_step_wall_seconds,
                   "native_join_audit": step_audit,
                   "actor_observations": actor_samples,
                   "native_dispatch": {"attempted": dispatchable, "action": action,
                                       "guard": guard},
                   "scheduled_player_intervention": player, "scheduled_edit": edit_now,
                   "native_step": step}
            _json(run_dir / "steps" / f"minute-{minute_to:02d}.json", row)
            steps.append(row)
            if edit_now and isinstance(step, Mapping):
                rounds = step.get("rounds", [])
                first = rounds[0] if rounds and isinstance(rounds[0], Mapping) else {}
                receipts = first.get("edits", [])
                receipt = receipts[0] if receipts and isinstance(receipts[0], Mapping) else {}
                if receipt.get("ok") is True:
                    raw_bundle = new_bundle
                    if isinstance(edit_path, Mapping):
                        edit_path = dict(edit_path)
                        edit_path["at"] = -1  # one-shot CAS edit
        final_trace = rpc("get_trace", {"scene_id": scene_id})
        _json(run_dir / "native_final_trace.json", final_trace)
        evidence, db_meta = _db_evidence(scene_id, db_exporter)
        if (isinstance(evidence, Mapping) and evidence.get("schema") == "native-p3-db-evidence-v1"
                and scene_id in evidence.get("selection", {}).get("scene_ids", [])):
            _json(run_dir / "independent_db_readback.json", evidence)
            db_valid = True
        else:
            db_valid = False
        _json(run_dir / "db_readback_meta.json", db_meta)
        result = {"status": "DEVELOPMENT_RUN_RECORDED", "scene_id": scene_id,
                  "run_status": final_trace.get("run_status"), "steps": len(steps),
                  "run_dir": str(run_dir), "source_identity": identity,
                  "db_readback_recorded": db_valid,
                  "native_trace_sha256": sha256(json.dumps(final_trace, sort_keys=True,
                      ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()}
        _json(run_dir / "result.json", result)
        return result
    except Exception as exc:
        result = {"status": "INCOMPLETE_ERROR", "case_id": str(case_id),
                  "error_type": type(exc).__name__, "message": str(exc)[:1000],
                  "run_dir": str(run_dir)}
        _json(run_dir / "INCOMPLETE_ERROR.json", result)
        return result


def run_stale_edit_negative(*, bundle_path: str | Path, edited_bundle_path: str | Path,
                            output_parent: str | Path = RUNS_DIR,
                            rpc: Callable[[str, dict[str, Any]], Any] = rpc_call,
                            sabre: Callable[[Path], dict[str, Any]] = invoke_sabre,
                            db_exporter: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Submit a Sabre-derived old route candidate on the same tick as a CAS edit."""
    run_dir = _allocate(Path(output_parent), "stale-edit-negative")
    try:
        original_path, edited_path = Path(bundle_path).resolve(), Path(edited_bundle_path).resolve()
        _validate_search_revision()
        original_bytes, edited_bytes = original_path.read_bytes(), edited_path.read_bytes()
        original = json.loads(original_bytes.decode("utf-8"))
        edited = json.loads(edited_bytes.decode("utf-8"))
        created = rpc("reset_p5_scenario", {
            "bundle": original, "initial_social_preset": "native_default_reject_v0",
            "horizon": 24, "seed": 20261012, "director_enabled": False,
            "shared_supply": False, "initial_main_open": False})
        scene = created.get("scene") if isinstance(created, Mapping) else None
        scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
        if not isinstance(scene_id, str) or not scene_id:
            raise RuntimeError(f"stale-control reset failed: {created!r}")
        before_sampling = rpc("get_trace", {"scene_id": scene_id})
        sample_minute = before_sampling.get("now") if isinstance(before_sampling, Mapping) else None
        if type(sample_minute) is not int:
            raise RuntimeError("stale-control pre-sample trace has no current minute")
        actor_samples = _sample_actor_observations(scene_id, sample_minute, rpc)
        trace = rpc("get_trace", {"scene_id": scene_id})
        if not isinstance(trace, Mapping) or trace.get("now") != sample_minute:
            raise RuntimeError("world minute changed during stale-control actor sampling")
        snapshot = build_snapshot(trace, original, scene_id=scene_id,
                                  actor_observations=actor_samples)
        projection = projection_status(snapshot)
        problem = render_problem(snapshot)
        problem_path = run_dir / "stale-candidate.problem"
        problem_path.write_text(problem, encoding="utf-8")
        plan = sabre(problem_path)
        actions = plan.get("plan_actions", []) if isinstance(plan, Mapping) else []
        decoded = decode_plan(actions if isinstance(actions, list) else [],
            native_status=("PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
                           if isinstance(plan, Mapping) and plan.get("status") == "SUCCESS"
                           and plan.get("returncode") == 0 else "NO_CANDIDATE"))
        dispatch_action = decoded.get("dispatch_action")
        opportunity = {"open_main_passage()": "open_main_passage",
                       "open_side_passage()": "open_side_passage"}.get(dispatch_action)
        complete = trace.get("complete_through", {})
        guard = None
        if _dispatch_allowed(method="sabre", plan=plan, decoded=decoded,
                             projection=projection, opportunity=opportunity,
                             player_intervention=None, edit_now=False):
            guard = {"scene_id": scene_id, "bundle_version": snapshot.bundle_version,
                     "based_on_minute": snapshot.minute,
                     "events_through": complete.get("events"),
                     "values_through": complete.get("values"),
                     "selected_action": opportunity, "opportunity_id": opportunity}
        intervention = ([] if guard is None else [{
            "at": 1, "kind": "author_opportunity", "operation": "open_passage",
            "opportunity_id": opportunity, "candidate_guard": guard}])
        step = rpc("step_world", {"scene_id": scene_id, "rounds": 1,
                                  "edits": [{"at": 1, "expected_version": original["version"],
                                             "raw_bundle": edited}],
                                  "interventions": intervention})
        final_trace = rpc("get_trace", {"scene_id": scene_id})
        rounds = step.get("rounds", []) if isinstance(step, Mapping) else []
        first = rounds[0] if rounds and isinstance(rounds[0], Mapping) else {}
        edit_rows, int_rows = first.get("edits", []), first.get("interventions", [])
        edit_receipt = edit_rows[0] if edit_rows and isinstance(edit_rows[0], Mapping) else {}
        int_receipt = int_rows[0] if int_rows and isinstance(int_rows[0], Mapping) else {}
        route_state = next((row.get("routes") for row in final_trace.get("world_snapshots", [])
                            if isinstance(row, Mapping) and row.get("minute") == 1
                            and isinstance(row.get("routes"), Mapping)), {})
        rejected = int_receipt.get("status") == "STALE_CANDIDATE"
        no_route_open = route_state == {"main_passage": False, "side_passage": False}
        edit_accepted = edit_receipt.get("ok") is True
        active_identity = final_trace.get("bundle_identity")
        edit_identity_ok = (isinstance(active_identity, Mapping)
                            and active_identity.get("bundle_id") == edited.get("bundle_id")
                            and active_identity.get("version") == edited.get("version"))
        status = ("STALE_GUARD_NEGATIVE_PASS" if guard is not None and rejected
                  and edit_accepted and edit_identity_ok and no_route_open else
                  "STALE_CONTROL_NOT_EXERCISED" if guard is None else "STALE_GUARD_NEGATIVE_FAIL")
        source_hashes = _source_hashes()
        _json(run_dir / "case.json", {"scenario": "same-minute-cas-edit-and-old-candidate",
              "bundle_sha256": sha256(original_bytes).hexdigest(),
              "edited_bundle_sha256": sha256(edited_bytes).hexdigest(),
              "baseline_git_commit": BASELINE_GIT_COMMIT,
              "search_config_id": SEARCH_CONFIG_ID,
              "search_limits": dict(SEARCH_LIMITS),
              "source_sha256": source_hashes,
              "scoped_worktree_sha256": sha256(json.dumps(
                  source_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
        _json(run_dir / "native_reset.json", created)
        _json(run_dir / "candidate.json", {"problem": problem, "plan": plan,
                                             "actor_observations": actor_samples,
                                             "projection_status": projection,
                                             "normalized_search_status": _normalized_search_status(plan, projection),
                                             "decoded_plan": decoded, "guard": guard})
        _json(run_dir / "native_step.json", step)
        _json(run_dir / "native_final_trace.json", final_trace)
        evidence, db_meta = _db_evidence(scene_id, db_exporter)
        db_valid = (isinstance(evidence, Mapping)
                    and evidence.get("schema") == "native-p3-db-evidence-v1"
                    and scene_id in evidence.get("selection", {}).get("scene_ids", []))
        if db_valid:
            _json(run_dir / "independent_db_readback.json", evidence)
        _json(run_dir / "db_readback_meta.json", db_meta)
        result = {"status": status, "scene_id": scene_id, "run_dir": str(run_dir),
                  "candidate_bundle_version": snapshot.bundle_version,
                  "native_bundle_identity": active_identity,
                  "native_edit_accepted": edit_accepted, "native_edit_identity_matches": edit_identity_ok,
                  "native_intervention_status": int_receipt.get("status"),
                  "route_state_at_dispatch_minute": route_state,
                  "db_readback_recorded": db_valid}
        _json(run_dir / "result.json", result)
        return result
    except Exception as exc:
        result = {"status": "INCOMPLETE_ERROR", "case_id": "stale-edit-negative",
                  "error_type": type(exc).__name__, "message": str(exc)[:1000],
                  "run_dir": str(run_dir)}
        _json(run_dir / "INCOMPLETE_ERROR.json", result)
        return result


__all__ = ["RUNS_DIR", "VALIDATION_DIR", "run_case", "run_stale_edit_negative",
           "run_snapshot_pilot", "replay_saved_snapshot_pilot"]
