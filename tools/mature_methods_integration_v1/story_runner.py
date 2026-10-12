"""Run one opt-in native story-process case against the existing P5 service.

The native seal callback performs planning. This client only advances one
minute at a time, reacts to returned native evidence, and reads one full final
trace and one independent DB export. It never invokes a planner or NPC command.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import shutil
import subprocess
from time import monotonic
from typing import Any, Callable, Mapping

from tools.mature_methods_integration_v1.runner import (
    RUNS_DIR as DEFAULT_RUNS_DIR,
    _rpc_record,
    _write_once,
)
from tools.native_platform_v0.p3.mcp_stdio import PROJECT_ROOT, rpc_call
from tools.native_platform_v0.p5.runner import export_db_evidence


SUITE_PATH = PROJECT_ROOT / "tools/mature_methods_integration_v1/story_cases/suite.json"
SOURCE_PATHS = (
    "tools/mature_methods_integration_v1/story_runner.py",
    "tools/mature_methods_integration_v1/story_cases/suite.json",
    "tools/mature_methods_integration_v1/story_cases/story-bundle-v1.json",
    "tools/mature_methods_integration_v1/tests/test_story_cases_contract.py",
    "tools/native_platform_v0/p5/story_process/model.py",
    "tools/native_platform_v0/p5/story_process/__init__.py",
    "tools/native_platform_v0/p5/story_process/native.py",
    "tools/native_platform_v0/p5/story_process/planning.py",
    "tools/native_platform_v0/p5/story_process/actor.py",
    "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p5/agency.py",
    "tools/native_platform_v0/p5/world.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
)
SCENE_TOKEN = "${scene_id}"


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_text(*args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=PROJECT_ROOT,
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _source_manifest(snapshot_root: Path) -> dict[str, Any]:
    snapshot_root.mkdir(parents=True, exist_ok=False)
    files = {name: _sha((PROJECT_ROOT / name).read_bytes())
             if (PROJECT_ROOT / name).is_file() else "MISSING" for name in SOURCE_PATHS}
    snapshot_paths = {}
    for name, digest in files.items():
        if digest == "MISSING":
            continue
        destination = snapshot_root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / name, destination)
        copied_hash = _sha(destination.read_bytes())
        if copied_hash != digest:
            raise RuntimeError(f"source snapshot hash mismatch for {name}")
        snapshot_paths[name] = str(destination.relative_to(snapshot_root))
    packed = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    remotes = _git_text("remote")
    remote_names = remotes.splitlines() if remotes else []
    review_remote = "origin" if "origin" in remote_names else None
    review_tracking_ref = f"refs/remotes/{review_remote}/webgpt-sync" if review_remote else None
    local_review_hash = _git_text("rev-parse", "refs/heads/webgpt-sync")
    tracking_review_hash = (_git_text("rev-parse", review_tracking_ref)
                            if review_tracking_ref else None)
    return {"git_head": _git_text("rev-parse", "HEAD"),
            "git_branch": _git_text("symbolic-ref", "--short", "HEAD"),
            "remote_review_ref": "refs/heads/webgpt-sync",
            "remote_name": review_remote,
            "remote_tracking_ref": review_tracking_ref,
            "remote_tracking_ref_sha256_target": tracking_review_hash,
            "local_review_ref": "refs/heads/webgpt-sync",
            "local_review_ref_sha": local_review_hash,
            "configured_upstream_ref": _git_text("rev-parse", "--abbrev-ref",
                                                   "--symbolic-full-name", "@{upstream}"),
            "working_tree_file_sha256": files,
            "source_snapshot_relative_paths": snapshot_paths,
            "working_tree_file_set_sha256": _sha(packed)}


def _allocate_run_dir(root: Path, case_id: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in case_id)[:48]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(16):
        path = root / f"story-{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique non-overwriting story run directory")


def _replace_scene_token(value: Any, scene_id: str) -> Any:
    if isinstance(value, str):
        return value.replace(SCENE_TOKEN, scene_id)
    if isinstance(value, list):
        return [_replace_scene_token(item, scene_id) for item in value]
    if isinstance(value, Mapping):
        return {key: _replace_scene_token(item, scene_id) for key, item in value.items()}
    return deepcopy(value)


def _at_path(value: Any, path: str) -> Any:
    current = value
    for key in path.split("."):
        if isinstance(current, Mapping):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            index = int(key)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def _matching_actions(rules: list[Mapping[str, Any]], observation: Mapping[str, Any],
                      fired: set[int], *, minute: int | None = None) -> list[dict[str, Any]]:
    actions = []
    for index, rule in enumerate(rules):
        if index in fired:
            continue
        if set(rule) == {"at_minute", "action"}:
            if type(rule["at_minute"]) is not int or rule["at_minute"] < 1:
                raise ValueError("scheduled author intervention requires a positive at_minute")
            if rule["at_minute"] == minute:
                action = rule["action"]
                if not isinstance(action, Mapping) or not isinstance(action.get("kind"), str):
                    raise ValueError("scheduled action needs a typed native intervention")
                actions.append({"rule_index": index, "action": deepcopy(dict(action))})
            continue
        condition = rule.get("when")
        if set(rule) != {"when", "action"} or not isinstance(condition, Mapping) or set(condition) != {"path", "equals"}:
            raise ValueError("action needs either at_minute/action or exact when.path/when.equals/action")
        if _at_path(observation, condition["path"]) == condition["equals"]:
            action = rule.get("action")
            if not isinstance(action, Mapping) or not isinstance(action.get("kind"), str):
                raise ValueError("reactive action needs a typed native intervention")
            actions.append({"rule_index": index, "action": deepcopy(dict(action))})
    return actions


def _compact_typed_delta(trace: Any, minute: int) -> Any:
    if not isinstance(trace, Mapping):
        return trace
    result = {key: value for key, value in trace.items() if key not in {"events", "points"}}
    result["events"] = [row for row in trace.get("events", [])
                        if isinstance(row, Mapping) and str(row.get("time")) == str(minute)]
    result["points"] = [row for row in trace.get("points", [])
                        if isinstance(row, Mapping) and str(row.get("time")) == str(minute)]
    return result


def _rpc_step_record(rpc: Callable, run_dir: Path, index: int,
                     args: dict[str, Any], minute: int) -> dict[str, Any]:
    """Persist the request and only the per-minute response, dropping its cumulative final trace."""
    stem = f"rpc-{index:04d}-step_world"
    _write_once(run_dir / f"{stem}-request.json", args)
    try:
        result = rpc("step_world", args)
    except Exception as exc:
        _write_once(run_dir / f"{stem}-error.json", {
            "rpc_operation": "step_world", "error_type": type(exc).__name__,
            "error_message": str(exc)[:500]})
        raise
    rounds = result.get("rounds") if isinstance(result, Mapping) else None
    if not isinstance(rounds, list):
        raise RuntimeError("step_world response omitted rounds[]")
    # service.step_world also returns a cumulative `final` trace; it is intentionally
    # omitted here because the final standalone get_trace below is the sole full copy.
    compact_rounds = []
    for row in rounds:
        if not isinstance(row, Mapping):
            raise RuntimeError("step_world round row must be an object")
        compact_rounds.append({key: row.get(key) for key in
                               ("minute", "edits", "interventions", "director", "actor_steps",
                                "snapshot", "minute_complete", "event_complete",
                                "unsealed_event_ids", "trace_frontier", "verdicts")})
        compact_rounds[-1]["story_process"] = row.get("story_process")
        compact_rounds[-1]["typed_trace"] = _compact_typed_delta(row.get("typed_trace"), minute)
    _write_once(run_dir / f"{stem}-response.json", {
        "scene_id": result.get("scene_id"), "round_count": len(rounds),
        "rounds": compact_rounds, "omitted_cumulative_fields": ["final"]})
    return dict(result)


def _compact_trace_identity(evidence: Mapping[str, Any]) -> dict[str, Any]:
    story = evidence.get("story_process")
    return {"scene_id": evidence.get("scene_id"), "now": evidence.get("now"),
            "complete_through": evidence.get("complete_through"),
            "bundle_identity": evidence.get("bundle_identity"),
            "story_process": story,
            "raw_trace_sha256": _sha(json.dumps(evidence, sort_keys=True,
                                                 ensure_ascii=False, separators=(",", ":"),
                                                 default=str).encode())}


def _patch_request(request: Mapping[str, Any], patch: Mapping[str, Any], *, new_version: int) -> dict[str, Any]:
    result = deepcopy(dict(request))
    for dotted, value in patch.items():
        keys = dotted.split(".")
        if len(keys) != 2 or keys[0] != "control" or keys[1] not in {"file_actor", "allowed_methods"}:
            raise ValueError("future request edit may patch only control.file_actor/allowed_methods")
        result["control"][keys[1]] = deepcopy(value)
    result["version"] = new_version
    return result


def _story_envelope(suite: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    common = suite["common"]
    envelope = {
        "schema": "story-process-request-v1",
        "request_id": f"story-{case['case_id']}",
        "version": 1,
        "scenario_id": None,
        "objective": deepcopy(common["objective"]),
        "control": deepcopy(case["control"]),
        "actor_postresponse": deepcopy(case.get("actor_postresponse", {
            "accepted": {"B_archive": "WILLING", "B_return": "WILLING", "A_archive": "WILLING"},
            "rejected": {"B_archive": "UNWILLING", "B_return": "WILLING", "A_archive": "WILLING"}})),
        "task_control_grant": deepcopy(common["task_control_grant"]),
        "edit_policy": deepcopy(common["edit_policy"]),
        "locked_fragment": None,
    }
    if case.get("locked_fragment_template") is not None:
        envelope["locked_fragment"] = deepcopy(case["locked_fragment_template"])
    if case.get("objective_override"):
        envelope["objective"].update(deepcopy(case["objective_override"]))
    if case.get("task_control_grant_override"):
        envelope["task_control_grant"].update(deepcopy(case["task_control_grant_override"]))
    return envelope


def _validate_continuation_identity(case: Mapping[str, Any], suite: Mapping[str, Any],
                                    prior_identity: Mapping[str, Any],
                                    prior_scene: Mapping[str, Any], scene_id: str,
                                    bundle_path: Path) -> None:
    """Fail closed unless this continuation matches the original accepted scene."""
    if (prior_identity.get("case_id") != case.get("case_id")
            or prior_identity.get("strategy") != case.get("strategy")
            or prior_identity.get("preset") != case.get("preset")
            or prior_identity.get("bundle_sha256") != _sha(bundle_path.read_bytes())
            or prior_scene.get("scene_id") != scene_id
            or prior_scene.get("horizon") != suite["common"]["horizon"]
            or prior_scene.get("seed") != suite["common"]["seed"]
            or prior_scene.get("preset") != case.get("preset")):
        raise ValueError("continuation differs from the original case, scene, bundle or runtime envelope")


def _prior_live_bundle_pin(prior_run: Path) -> str | None:
    """Read an earlier sealed observation as the pin for runtime bundle bytes."""
    verification_path = prior_run / "continuation-prefix-verification.json"
    if verification_path.is_file():
        verification = _read_json(verification_path)
        digest = verification.get("observed_bundle_sha256")
        return digest if isinstance(digest, str) and len(digest) == 64 else None
    observation_path = prior_run / "initial-observation.json"
    if observation_path.is_file():
        observation = _read_json(observation_path)
        bundle = observation.get("bundle_identity", {})
        digest = bundle.get("sha256") if isinstance(bundle, Mapping) else None
        return digest if isinstance(digest, str) and len(digest) == 64 else None
    return None


def _expected_continuation_request(template: Mapping[str, Any], scene_id: str,
                                   prior_trace: Mapping[str, Any] | None) -> dict[str, Any]:
    expected = deepcopy(dict(template))
    expected["scenario_id"] = scene_id
    expected["task_control_grant"]["scenario_id"] = scene_id
    if prior_trace is not None:
        prior_story = prior_trace.get("story_process", {})
        prior_request = prior_story.get("request", {}) if isinstance(prior_story, Mapping) else {}
        note_id = prior_request.get("objective", {}).get("note_id") if isinstance(prior_request, Mapping) else None
        if type(note_id) is not int or prior_story.get("bound_note_id") != note_id:
            raise ValueError("nonzero continuation predecessor must contain its bound native note id")
        expected["objective"]["note_id"] = note_id
    return expected


def _validate_active_db_prefix(evidence: Mapping[str, Any], scene_id: str,
                               scene_identity: Mapping[str, Any],
                               prior_trace: Mapping[str, Any], expected_minute: int) -> dict[str, Any]:
    """Validate and summarize an independently persisted nonzero continuation prefix."""
    exact = next((row for row in evidence.get("scenes", [])
                  if isinstance(row, Mapping) and row.get("scene_id") == scene_id), None)
    if not isinstance(exact, Mapping):
        raise RuntimeError("continuation DB readback omitted the exact original scene")
    objects = {row.get("id"): row for row in exact.get("objects", [])
               if isinstance(row, Mapping)}
    original_ids = [scene_identity.get("player", {}).get("id"),
                    *[row.get("id") for row in scene_identity.get("items", {}).values()
                      if isinstance(row, Mapping)]]
    if any(type(object_id) is not int or object_id not in objects for object_id in original_ids):
        raise RuntimeError("nonzero continuation DB prefix no longer contains original player/item IDs")
    controller = next((row for row in objects.values()
                       if "p5_story_request" in row.get("attributes", {}).get("native_p5", {})), None)
    if not isinstance(controller, Mapping):
        raise RuntimeError("continuation DB readback omitted the native story controller")
    p5 = controller.get("attributes", {}).get("native_p5", {})
    p3 = controller.get("attributes", {}).get("native_p3", {})
    meta = p5.get("p5_story_meta", {})
    expected_minutes = list(range(expected_minute + 1))
    if (p5.get("p5_completed_minutes") != expected_minutes
            or p5.get("p5_event_coverage_minute") != expected_minute
            or p5.get("p5_snapshot_coverage_minute") != expected_minute):
        raise RuntimeError("persisted continuation prefix is not exactly sealed through the expected minute")
    expected_request = prior_trace.get("story_process", {}).get("request")
    if p5.get("p5_story_request") != expected_request:
        raise RuntimeError("persisted native request differs from the preserved predecessor trace")
    prior_story = prior_trace.get("story_process", {})
    if meta.get("controller_decisions") != prior_story.get("controller_decisions"):
        raise RuntimeError("persisted controller decision history differs from the preserved predecessor trace")
    item_id = prior_story.get("bound_note_id")
    b_actor = next((row for row in objects.values()
                    if row.get("attributes", {}).get("native_p5", {}).get("p5_actor_alias") == "B"), None)
    if not isinstance(b_actor, Mapping) or type(item_id) is not int:
        raise RuntimeError("active story task lacks the bound note or B actor")
    b_p5 = b_actor.get("attributes", {}).get("native_p5", {})
    task = b_p5.get("p5_story_task")
    destination = task.get("destination_id") if isinstance(task, Mapping) else None
    move_receipt = next((row for row in b_p5.get("p5_story_receipts", [])
                         if isinstance(row, Mapping) and row.get("kind") == "move"
                         and row.get("item_id") == item_id and row.get("settled") is True), None)
    note = objects.get(item_id)
    if (not isinstance(task, Mapping) or task.get("status") != "IN_PROGRESS"
            or task.get("actor_alias") != "B" or task.get("item_id") != item_id
            or task.get("accepted_at_minute") is None
            or b_actor.get("location", {}).get("id") != destination
            or not isinstance(note, Mapping) or note.get("location", {}).get("id") != b_actor.get("id")
            or not isinstance(move_receipt, Mapping)
            or move_receipt.get("after_room_id") != destination):
        raise RuntimeError("persisted prefix does not preserve B's accepted task, note possession and move receipt")
    delivery_rows = [row for row in p3.get("p4_ledger", [])
                     if isinstance(row, Mapping) and row.get("event_type") == "p5_delivery_settled"
                     and row.get("sealed") is True]
    settled_old_deliveries = {(row.get("typed_args", {}).get("actor"),
                               row.get("typed_args", {}).get("item")) for row in delivery_rows}
    if not {("A", "courier_supply"), ("B", "resident_parcel")}.issubset(settled_old_deliveries):
        raise RuntimeError("the original A/B native delivery receipts are not both preserved as settled")
    decision = next((row for row in prior_story.get("controller_decisions", [])
                     if isinstance(row, Mapping) and row.get("selected_method") == "file_by_B"), None)
    feasible = {row.get("method_id") for row in decision.get("method_plans", [])
                if isinstance(row, Mapping) and row.get("feasible") is True} if isinstance(decision, Mapping) else set()
    if not {"file_by_B", "return_then_file_by_A"}.issubset(feasible):
        raise RuntimeError("preserved sealed decision does not prove both native method guards feasible")
    return {"scene_id": scene_id, "completed_minutes": expected_minutes,
            "event_coverage_minute": expected_minute,
            "snapshot_coverage_minute": expected_minute,
            "bound_note_id": item_id, "b_actor_id": b_actor.get("id"),
            "b_task_status": task.get("status"), "b_task_accepted_at_minute": task.get("accepted_at_minute"),
            "b_actor_room_id": b_actor.get("location", {}).get("id"),
            "note_holder_object_id": note.get("location", {}).get("id"),
            "move_receipt_id": move_receipt.get("receipt_id"),
            "selected_method": decision.get("selected_method"),
            "both_methods_feasible": True,
            "settled_old_deliveries": ["A:courier_supply", "B:resident_parcel"]}


def _validate_locked_fragment_db_prefix(evidence: Mapping[str, Any], scene_id: str,
                                        scene_identity: Mapping[str, Any],
                                        prior_trace: Mapping[str, Any], expected_minute: int) -> dict[str, Any]:
    """Validate only the preserved locked-fragment scene at its approved frontier."""
    if expected_minute != 17 or scene_id != "20261012144034-03df60":
        raise RuntimeError("finite locked-fragment continuation is limited to its preserved minute-17 scene")
    exact = next((row for row in evidence.get("scenes", [])
                  if isinstance(row, Mapping) and row.get("scene_id") == scene_id), None)
    if not isinstance(exact, Mapping):
        raise RuntimeError("locked continuation DB readback omitted the exact original scene")
    objects = {row.get("id"): row for row in exact.get("objects", [])
               if isinstance(row, Mapping)}
    prior_story = prior_trace.get("story_process", {})
    request = prior_story.get("request") if isinstance(prior_story, Mapping) else None
    item_id = prior_story.get("bound_note_id") if isinstance(prior_story, Mapping) else None
    actor_evidence = prior_trace.get("actor_evidence", [])
    actor_ids = {row.get("actor_id") for row in actor_evidence if isinstance(row, Mapping)}
    projection = prior_trace.get("world_capability_projection", {})
    room_roles = projection.get("room_roles", {}) if isinstance(projection, Mapping) else {}
    routes = projection.get("routes", []) if isinstance(projection, Mapping) else []
    exit_ids = {edge.get("exit_id") for route in routes if isinstance(route, Mapping)
                for edge in route.get("directed_edges", []) if isinstance(edge, Mapping)}
    expected_ids = {6802, 6803, 6811, *actor_ids, item_id,
                    scene_identity.get("player", {}).get("id"),
                    *[row.get("id") for row in scene_identity.get("items", {}).values()
                      if isinstance(row, Mapping)], *exit_ids}
    if None in expected_ids or set(objects) != expected_ids:
        raise RuntimeError("locked continuation scene object IDs differ from the preserved scene evidence")
    controller = objects.get(6802)
    if not isinstance(controller, Mapping):
        raise RuntimeError("locked continuation DB readback omitted its original controller object")
    p5 = controller.get("attributes", {}).get("native_p5", {})
    p3 = controller.get("attributes", {}).get("native_p3", {})
    meta = p5.get("p5_story_meta", {})
    if (p5.get("p5_completed_minutes") != list(range(expected_minute + 1))
            or p5.get("p5_event_coverage_minute") != expected_minute
            or p5.get("p5_snapshot_coverage_minute") != expected_minute
            or p5.get("p5_story_request") != request
            or p3.get("p4_ledger") != prior_trace.get("ledger")
            or meta.get("controller_decisions") != prior_story.get("controller_decisions")
            or meta.get("receipts") != prior_story.get("receipts")
            or meta.get("pending_task_requests") != []):
        raise RuntimeError("locked continuation persisted prefix differs from the sealed trace")
    if (not isinstance(request, Mapping) or request.get("scenario_id") != scene_id
            or request.get("version") != 1
            or request.get("objective", {}).get("note_id") != item_id
            or request.get("objective", {}).get("by_minute") != 24
            or request.get("task_control_grant", {}).get("grant_id") != "story-episode-task-grant-v1"
            or request.get("task_control_grant", {}).get("valid_until_minute") != 24
            or request.get("locked_fragment", {}).get("sequence_sha256") !=
               "3098d52d8c4a5569dcf5ea9427b1f64a36f290b3c392416d86b8136413eb3646"):
        raise RuntimeError("locked continuation request, grant, deadline, or immutable core changed")
    b_actor = next((row for row in objects.values()
                    if row.get("attributes", {}).get("native_p5", {}).get("p5_actor_alias") == "B"), None)
    note = objects.get(item_id)
    if (not isinstance(b_actor, Mapping) or not isinstance(note, Mapping)
            or b_actor.get("id") != 6807 or b_actor.get("location", {}).get("id") != 6803
            or note.get("location", {}).get("id") != b_actor.get("id")
            or b_actor.get("attributes", {}).get("native_p5", {}).get("p5_story_task") is not None
            or prior_story.get("controller_decisions") != []
            or prior_story.get("controller_events") != []):
        raise RuntimeError("locked continuation no longer has its original holder/position and undispatched prefix")
    return {"scene_id": scene_id, "completed_minutes": list(range(expected_minute + 1)),
            "event_coverage_minute": expected_minute, "snapshot_coverage_minute": expected_minute,
            "verified_scene_object_ids": sorted(expected_ids), "bound_note_id": item_id,
            "note_holder_object_id": b_actor.get("id"), "b_actor_room_id": 6803,
            "controller_decision_count": 0, "controller_event_count": 0,
            "native_tasks_dispatched": False, "locked_core_sha256": request["locked_fragment"]["sequence_sha256"],
            "grant_id": request["task_control_grant"]["grant_id"], "deadline_minute": 24,
            "prior_trace_pending_verdict_count": len(prior_story.get("real_verdicts", [])),
            "db_story_meta_real_verdict_count": len(meta.get("real_verdicts", [])),
            "db_real_verdict_telemetry": ("MATCHED" if meta.get("real_verdicts") ==
                                           prior_story.get("real_verdicts") else
                                           "KNOWN_PRE_FIX_METADATA_PERSISTENCE_GAP")}


def _copy_db_artifact(db_export: Mapping[str, Any], run_dir: Path, name: str) -> dict[str, Any]:
    artifact_path = db_export.get("artifact_path")
    if not isinstance(artifact_path, str) or not Path(artifact_path).is_file():
        raise RuntimeError("independent DB exporter omitted a readable raw artifact")
    destination = run_dir / name
    shutil.copyfile(artifact_path, destination)
    digest = _sha(destination.read_bytes())
    if digest != db_export.get("artifact_sha256"):
        raise RuntimeError("copied DB evidence hash differs from the independent exporter")
    return {"raw_artifact_relative_path": name, "raw_artifact_sha256": digest,
            "export_artifact_path": artifact_path}


def _db_cost_metrics(evidence: Mapping[str, Any], scene_id: str,
                     story: Mapping[str, Any]) -> dict[str, Any]:
    exact = next((row for row in evidence.get("scenes", [])
                  if isinstance(row, Mapping) and row.get("scene_id") == scene_id), {})
    objects = exact.get("objects", []) if isinstance(exact, Mapping) else []
    controller = next((row for row in objects if isinstance(row, Mapping)
                       and "p5_story_meta" in row.get("attributes", {}).get("native_p5", {})), {})
    attrs = controller.get("attributes", {}) if isinstance(controller, Mapping) else {}
    native_p3 = attrs.get("native_p3", {})
    native_p5 = attrs.get("native_p5", {})
    ledger = native_p3.get("p4_ledger", [])
    event_counts: dict[str, int] = {}
    for row in ledger:
        if isinstance(row, Mapping):
            name = str(row.get("event_type"))
            event_counts[name] = event_counts.get(name, 0) + 1
    accepted_request_ids = {
        str(row.get("typed_args", {}).get("request_id"))
        for row in ledger
        if isinstance(row, Mapping)
        and row.get("event_type") == "P5_STORY_TASK_DECISION"
        and isinstance(row.get("typed_args"), Mapping)
        and row["typed_args"].get("decision") == "ACCEPTED"
        and row["typed_args"].get("request_id")
    }
    decisions = story.get("controller_decisions", [])
    actual_callbacks = [row for decision in decisions if isinstance(decision, Mapping)
                        for row in decision.get("attempted_methods", []) if isinstance(row, Mapping)]
    diagnostics = [row for decision in decisions if isinstance(decision, Mapping)
                   for row in decision.get("alternative_guard_diagnostics", [])
                   if isinstance(row, Mapping)]
    actor_receipts = []
    for actor in objects:
        if not isinstance(actor, Mapping):
            continue
        actor_attrs = actor.get("attributes", {}).get("native_p5", {})
        alias = actor_attrs.get("p5_actor_alias")
        actor_receipts.extend({"actor_alias": alias, "kind": row.get("kind"),
                               "settled": row.get("settled") is True}
                              for row in actor_attrs.get("p5_story_receipts", [])
                              if isinstance(row, Mapping))
    return {"p4_ledger_event_count": len(ledger),
            "p4_ledger_event_type_counts": event_counts,
            "p5_controller_decision_count": len(decisions),
            "gtpyhop_or_event_policy_method_callback_count": len(actual_callbacks),
            "method_callback_counts_by_id": {
                method: sum(row.get("method_id") == method for row in actual_callbacks)
                for method in sorted({str(row.get("method_id")) for row in actual_callbacks})},
            "alternative_guard_diagnostic_count_not_execution": len(diagnostics),
            "native_planner_task_proposal_count": sum(len(row.get("task_requests", []))
                for row in decisions if isinstance(row, Mapping)),
            "native_accepted_task_request_count": len(accepted_request_ids),
            "native_actor_receipt_count": len(actor_receipts),
            "native_actor_receipts_by_actor_and_kind": {
                f"{alias}:{kind}": sum(row.get("actor_alias") == alias and row.get("kind") == kind
                                        for row in actor_receipts)
                for alias, kind in sorted({(str(row.get("actor_alias")), str(row.get("kind")))
                                           for row in actor_receipts})},
            "simulation_minutes_sealed": native_p5.get("p5_completed_minutes", []),
            "wall_time_comparison": "measured per runner continuation only; excludes service lifecycle"}


def run_case(case_id: str, *, suite_path: Path = SUITE_PATH,
             runs_dir: Path = DEFAULT_RUNS_DIR, call_rpc: Callable | None = None,
             export_db: bool = True, lifecycle_dir: Path | None = None,
             existing_scene_id: str | None = None,
             expected_minute: int | None = None,
             continuation_of: Path | None = None,
             run_purpose: str | None = None,
             predecessor_run_dirs: list[Path] | None = None) -> tuple[dict[str, Any], Path]:
    """Run exactly one frozen case; an error after reset is always retained."""
    rpc = call_rpc or rpc_call
    suite = _read_json(suite_path)
    matches = [row for row in suite["cases"] if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise ValueError(f"case_id must identify exactly one frozen case: {case_id}")
    case = matches[0]
    if run_purpose is not None:
        expected_predecessors = 1 if run_purpose == "BUGFIX_REGRESSION" else 2
        if (case_id != "task-refusal-gtpyhop"
                or run_purpose not in {"BUGFIX_REGRESSION", "BUGFIX_REGRESSION_RENDEZVOUS"}
                or not isinstance(predecessor_run_dirs, list)
                or len(predecessor_run_dirs) != expected_predecessors
                or any(not path.is_dir() or not (path / "identity.json").is_file()
                       or not (path / "scene_identity.json").is_file()
                       for path in predecessor_run_dirs)):
            raise ValueError("authorized task-refusal regression requires its exact preserved predecessor set")
    if (existing_scene_id is None) != (expected_minute is None):
        raise ValueError("existing scene continuation requires both scene_id and expected_minute")
    if existing_scene_id is not None:
        if not isinstance(existing_scene_id, str) or not existing_scene_id or type(expected_minute) is not int or expected_minute < 0:
            raise ValueError("continuation scene identity/minute is invalid")
        if continuation_of is None or not continuation_of.is_dir():
            raise ValueError("continuation requires the preserved original run directory")
        old_identity_path = continuation_of / "identity.json"
        old_scene_path = continuation_of / "scene_identity.json"
        if not old_identity_path.is_file() or not old_scene_path.is_file():
            raise ValueError("continuation source must contain the original identity and scene record")
        old_scene = _read_json(old_scene_path)
        old_identity = _read_json(old_identity_path)
        prior_bundle_pin = _prior_live_bundle_pin(continuation_of)
        if old_scene.get("scene_id") != existing_scene_id:
            raise ValueError("continuation scene does not match the preserved original scene record")
    prior_trace = None
    if existing_scene_id is not None and expected_minute != 0:
        prior_trace_path = next((continuation_of / name for name in
                                 ("failure-final-native-trace.json", "final-native-trace.json")
                                 if (continuation_of / name).is_file()), None)
        if prior_trace_path is None:
            raise ValueError("nonzero continuation requires the predecessor's final native trace")
        prior_trace = _read_json(prior_trace_path)
        prior_frontier = prior_trace.get("complete_through", {})
        if (prior_trace.get("scene_id") != existing_scene_id
                or prior_trace.get("now") != expected_minute
                or prior_frontier.get("events") != expected_minute
                or prior_frontier.get("values") != expected_minute):
            raise ValueError("nonzero continuation predecessor does not match the requested sealed minute")
    if case.get("blocked_until_native_resource_intervention") is True:
        raise RuntimeError("case has no registered lawful resource intervention; refusing to fabricate a player action")
    run_dir = _allocate_run_dir(runs_dir, case_id)
    lifecycle_copy = None
    if lifecycle_dir is not None:
        lifecycle_copy = run_dir / "service-lifecycle"
        shutil.copytree(lifecycle_dir, lifecycle_copy)
    bundle_path = suite_path.parent / suite["common"]["bundle"]
    bundle_bytes = bundle_path.read_bytes()
    bundle = json.loads(bundle_bytes.decode("utf-8"))
    story_request = _story_envelope(suite, case)
    if existing_scene_id is not None:
        _validate_continuation_identity(case, suite, old_identity, old_scene, existing_scene_id,
                                        suite_path.parent / suite["common"]["bundle"])
    source_manifest = _source_manifest(run_dir / "source-snapshot")
    identity = {"schema": "native-story-process-run-identity-v1",
                "case_id": case_id, "pair_id": case.get("pair_id"),
                "strategy": case["strategy"], "preset": case["preset"],
                "suite_sha256": _sha(suite_path.read_bytes()),
                "bundle_sha256": _sha(bundle_bytes), "source_manifest": source_manifest,
                "runtime": {"horizon": suite["common"]["horizon"],
                            "seed": suite["common"]["seed"],
                            "native_service": "existing P5 / Evennia / Ensemble"},
                "service_lifecycle_artifacts": (str(lifecycle_copy.relative_to(run_dir))
                                                 if lifecycle_copy else None),
                "story_request_template": story_request,
                "raw_private_dialogue_or_database": "NOT_INCLUDED"}
    if run_purpose is not None:
        identity["run_purpose"] = run_purpose
        identity["predecessor_runs"] = [{
            "run_directory": str(path),
            "identity_sha256": _sha((path / "identity.json").read_bytes()),
            "scene_id": _read_json(path / "scene_identity.json").get("scene_id"),
            "purpose": "preserved failed native case; never resumed or overwritten",
        } for path in predecessor_run_dirs]
    if existing_scene_id is not None:
        identity["continuation"] = {
            "mode": "existing_scene_only_no_reset",
            "scene_id": existing_scene_id,
            "expected_minute": expected_minute,
            "prior_run_directory": str(continuation_of),
            "prior_identity_sha256": _sha((continuation_of / "identity.json").read_bytes()),
            "prior_source_file_set_sha256": old_identity.get("source_manifest", {}).get(
                "working_tree_file_set_sha256"),
            "prior_source_file_sha256": old_identity.get("source_manifest", {}).get(
                "working_tree_file_sha256"),
            "prior_live_bundle_sha256_pin": prior_bundle_pin,
            "prior_failure_sha256": (_sha((continuation_of / "failure.json").read_bytes())
                                     if (continuation_of / "failure.json").is_file() else None),
        }
    _write_once(run_dir / "identity.json", identity)
    scene_id: str | None = None
    call_index = 0
    fired: set[int] = set()
    steps: list[dict[str, Any]] = []
    status = "INCOMPLETE"
    error = None
    final_trace = None
    reset_result = None
    db_evidence, db_export = None, {"status": "NOT_REQUESTED"}
    run_started = monotonic()
    try:
        if existing_scene_id is None:
            reset_args = {"bundle": bundle,
                      "initial_social_preset": case["preset"],
                      "horizon": suite["common"]["horizon"],
                      "seed": suite["common"]["seed"],
                      "director_enabled": True,
                      "shared_supply": suite["common"]["shared_supply"],
                      "initial_main_open": suite["common"]["initial_main_open"],
                      "story_process": story_request,
                      "story_strategy": case["strategy"]}
            call_index += 1
            created = _rpc_record(rpc, run_dir, call_index, "reset_p5_scenario", reset_args)
            reset_result = created
            scene = created.get("scene", created) if isinstance(created, Mapping) else None
            scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
            if not isinstance(scene_id, str) or not scene_id:
                raise RuntimeError("P5 story reset returned no native scene identity")
            _write_once(run_dir / "scene_identity.json", {
                "scene_id": scene_id, "created_at": created.get("created_at") if isinstance(created, Mapping) else None,
                "active_bundle": scene.get("active_bundle"), "preset": scene.get("preset"),
                "seed": scene.get("seed"), "horizon": scene.get("horizon"),
                "player": scene.get("player"), "items": scene.get("items"),
                "story_request_template_sha256": _sha(json.dumps(story_request, sort_keys=True,
                                                                   separators=(",", ":")).encode())})
        else:
            scene_id = existing_scene_id
            shutil.copyfile(continuation_of / "scene_identity.json", run_dir / "scene_identity.json")
        # One initial full read confirms the scene, request binding and sealed frontier.
        call_index += 1
        initial_args = {"scene_id": scene_id}
        _write_once(run_dir / f"rpc-{call_index:04d}-get_trace-request.json", initial_args)
        initial = rpc("get_trace", initial_args)
        if not isinstance(initial, Mapping):
            raise RuntimeError("initial get_trace response must be an object")
        _write_once(run_dir / "initial-observation.json", _compact_trace_identity(initial))
        required_minute = 0 if expected_minute is None else expected_minute
        if initial.get("scene_id") != scene_id or initial.get("now") != required_minute:
            raise RuntimeError("native story scene does not match the required sealed continuation frontier")
        live_story = initial.get("story_process")
        if not isinstance(live_story, Mapping):
            raise RuntimeError("native P5 trace omitted opt-in story_process evidence")
        if live_story.get("request", {}).get("scenario_id") != scene_id:
            raise RuntimeError("native story request was not bound to its generated scene")
        if live_story.get("request", {}).get("task_control_grant", {}).get("scenario_id") != scene_id:
            raise RuntimeError("native story grant was not bound to its generated scene")
        if existing_scene_id is not None:
            expected_request = _expected_continuation_request(story_request, existing_scene_id,
                                                              prior_trace)
            if live_story.get("request") != expected_request:
                raise RuntimeError("continued scene request differs from its preserved predecessor")
            observed_bundle = initial.get("bundle_identity", {})
            original_bundle = old_scene.get("active_bundle", {})
            if (not isinstance(observed_bundle, Mapping)
                    or any(observed_bundle.get(key) != original_bundle.get(key)
                           for key in ("bundle_id", "version"))):
                raise RuntimeError("continued scene active bundle identity differs from original reset")
            observed_bundle_sha = observed_bundle.get("sha256")
            if not isinstance(observed_bundle_sha, str) or len(observed_bundle_sha) != 64:
                raise RuntimeError("continued scene trace omitted the live bundle content hash")
            if prior_bundle_pin is not None and observed_bundle_sha != prior_bundle_pin:
                raise RuntimeError("continued scene live bundle hash differs from its prior sealed observation")
            if prior_trace is not None:
                prior_bundle = prior_trace.get("bundle_identity", {})
                prior_story = prior_trace.get("story_process", {})
                if (not isinstance(prior_bundle, Mapping)
                        or prior_bundle.get("sha256") != observed_bundle_sha
                        or prior_story.get("request") != live_story.get("request")
                        or prior_story.get("controller_decisions") != live_story.get("controller_decisions")
                        or prior_story.get("actor_tasks") != live_story.get("actor_tasks")
                        or prior_story.get("bound_note_id") != live_story.get("bound_note_id")
                        or prior_story.get("receipts") != live_story.get("receipts")):
                    raise RuntimeError("continued active task prefix differs from the preserved failure trace")
            _write_once(run_dir / "continuation-prefix-verification.json", {
                "scene_id": scene_id, "expected_minute": expected_minute,
                "observed_minute": initial.get("now"),
                "sealed_frontier": deepcopy(initial.get("complete_through")),
                "request_sha256": _sha(json.dumps(live_story.get("request"), sort_keys=True,
                                                  separators=(",", ":")).encode()),
                "bundle_id": observed_bundle.get("bundle_id"),
                "bundle_version": observed_bundle.get("version"),
                "prior_live_bundle_sha256_pin": prior_bundle_pin,
                "observed_bundle_sha256": observed_bundle_sha,
                "bundle_sha256_pin_status": "VERIFIED" if prior_bundle_pin else "ESTABLISHED"})
            frontier = initial.get("complete_through", {})
            if (frontier.get("events") != expected_minute
                    or frontier.get("values") != expected_minute):
                raise RuntimeError("continued scene does not expose the expected sealed event/value frontier")
            if expected_minute == 0:
                for key in ("controller_decisions", "receipts"):
                    if live_story.get(key) != []:
                        raise RuntimeError(f"t0 continuation prefix unexpectedly contains {key}")
                initial_verdicts = live_story.get("real_verdicts", [])
                if not isinstance(initial_verdicts, list) or any(
                    not isinstance(row, Mapping)
                    or row.get("status") != "NO_NATIVE_NOTE_EVIDENCE"
                    or row.get("verdict") != "NOT_SATISFIED"
                    or row.get("sealed_frontier") != 0
                    for row in initial_verdicts
                ):
                    raise RuntimeError("t0 continuation prefix contains a non-initial or successful goal verdict")
        active_request = deepcopy(dict(live_story["request"]))

        if existing_scene_id is not None and export_db:
            db_evidence, db_export = export_db_evidence(scene_id)
            evidence_name = ("t0-db-export-reference.json" if expected_minute == 0
                             else "continuation-prefix-db-export-reference.json")
            _write_once(run_dir / evidence_name, db_export)
            if not isinstance(db_evidence, Mapping):
                raise RuntimeError("continuation requires an independent persisted DB prefix readback")
            if expected_minute != 0:
                if case_id == "locked-fragment":
                    prefix = _validate_locked_fragment_db_prefix(db_evidence, scene_id, old_scene,
                                                                  prior_trace, expected_minute)
                else:
                    prefix = _validate_active_db_prefix(db_evidence, scene_id, old_scene,
                                                        prior_trace, expected_minute)
                artifact_path = db_export.get("artifact_path")
                if not isinstance(artifact_path, str) or not Path(artifact_path).is_file():
                    raise RuntimeError("continuation DB exporter omitted the raw prefix artifact")
                raw_target = run_dir / "continuation-prefix-db-evidence.json"
                shutil.copyfile(artifact_path, raw_target)
                raw_hash = _sha(raw_target.read_bytes())
                if raw_hash != db_export.get("artifact_sha256"):
                    raise RuntimeError("copied continuation DB prefix hash differs from independent exporter")
                prefix["raw_artifact_relative_path"] = raw_target.name
                prefix["raw_artifact_sha256"] = raw_hash
                _write_once(run_dir / "continuation-prefix-readback-summary.json", prefix)
                prior_t0_path = continuation_of / "t0-prefix-readback-summary.json"
                if prior_t0_path.is_file():
                    prior_t0 = _read_json(prior_t0_path)
                    source_artifact = prior_t0.get("export_artifact_path")
                    if isinstance(source_artifact, str) and Path(source_artifact).is_file():
                        t0_target = run_dir / "t0-prefix-db-evidence.json"
                        shutil.copyfile(source_artifact, t0_target)
                        t0_hash = _sha(t0_target.read_bytes())
                        if t0_hash != prior_t0.get("export_artifact_sha256"):
                            raise RuntimeError("copied predecessor t0 DB prefix hash mismatch")
                        _write_once(run_dir / "t0-prefix-db-evidence-reference.json", {
                            "source_run_directory": str(continuation_of),
                            "raw_artifact_relative_path": t0_target.name,
                            "raw_artifact_sha256": t0_hash})
            else:
                exact = next((row for row in db_evidence.get("scenes", [])
                              if isinstance(row, Mapping) and row.get("scene_id") == scene_id), None)
                if not isinstance(exact, Mapping):
                    raise RuntimeError("t0 DB readback omitted the exact original scene")
                objects = {row.get("id"): row for row in exact.get("objects", [])
                           if isinstance(row, Mapping)}
                expected_ids = [old_scene.get("player", {}).get("id"),
                                *[row.get("id") for row in old_scene.get("items", {}).values()
                                  if isinstance(row, Mapping)]]
                if any(type(object_id) is not int or object_id not in objects
                       for object_id in expected_ids):
                    raise RuntimeError("t0 DB readback entity IDs differ from the original reset response")
                controller = next((row for row in exact.get("objects", [])
                                   if isinstance(row, Mapping) and
                                   "p5_story_request" in row.get("attributes", {}).get("native_p5", {})), None)
                p5 = controller.get("attributes", {}).get("native_p5", {}) if isinstance(controller, Mapping) else {}
                if (p5.get("p5_completed_minutes") != [0]
                        or p5.get("p5_event_coverage_minute") != 0
                        or p5.get("p5_snapshot_coverage_minute") != 0
                        or p5.get("p5_story_meta", {}).get("controller_authored_npc_commands") != 0
                        or p5.get("p5_story_meta", {}).get("controller_authored_npc_task_requests") != 0):
                    raise RuntimeError("persisted t0 prefix is not pristine: minute, callbacks, or task requests differ")
                _write_once(run_dir / "t0-prefix-readback-summary.json", {
                    "scene_id": scene_id, "object_count": len(objects),
                    "entity_ids_verified": expected_ids, "completed_minutes": [0],
                    "event_coverage_minute": 0, "snapshot_coverage_minute": 0,
                    "controller_authored_npc_commands": 0,
                    "controller_authored_npc_task_requests": 0,
                    "export_artifact_path": db_export.get("artifact_path"),
                    "export_artifact_sha256": db_export.get("artifact_sha256")})
                t0_raw = _copy_db_artifact(db_export, run_dir, "t0-prefix-db-evidence.json")
                _write_once(run_dir / "t0-prefix-db-evidence-reference.json", t0_raw)

        horizon = int(suite["common"]["horizon"])
        previous_observation: Mapping[str, Any] = {"story_process": live_story}
        for minute in range(required_minute + 1, horizon + 1):
            matched = _matching_actions(case.get("reactive_actions", []),
                                        previous_observation, fired, minute=minute)
            if len(matched) > 1:
                raise RuntimeError(f"more than one reactive intervention became eligible before minute {minute}")
            interventions: list[dict[str, Any]] = []
            for match in matched:
                action = dict(match["action"])
                kind = action.pop("kind")
                if kind == "author_story_edit":
                    current = active_request
                    expected_version = action.get("expected_version")
                    if expected_version != current.get("version"):
                        raise RuntimeError("declared story edit version does not match the last observed live request")
                    proposed = _patch_request(current, action.get("patch", {}),
                                              new_version=int(current["version"]) + 1)
                    interventions.append({"at": minute, "kind": kind,
                                          "expected_version": expected_version,
                                          "request": proposed})
                elif kind == "player_command":
                    interventions.append({"at": minute, "kind": kind,
                                          "operation": action["operation"],
                                          "item_alias": action["item_alias"]})
                else:
                    raise ValueError(f"unsupported reactive intervention kind: {kind}")
            call_index += 1
            step = _rpc_step_record(rpc, run_dir, call_index, {
                "scene_id": scene_id, "rounds": 1,
                "interventions": interventions, "edits": []}, minute)
            rounds = step.get("rounds") if isinstance(step, Mapping) else None
            if not isinstance(rounds, list) or len(rounds) != 1:
                raise RuntimeError("native story step must return exactly one observed minute")
            delta = rounds[0]
            if delta.get("minute") != minute or delta.get("minute_complete") is not True:
                raise RuntimeError("native step response does not match the expected completed minute")
            story_delta = delta.get("story_process")
            if story_delta is not None and not isinstance(story_delta, Mapping):
                raise RuntimeError("native step story_process delta must be an object or null")
            if story_delta is None:
                # Before the real, settled social request, there is no note to bind
                # and the native planner correctly has no story task to propose.
                story_delta = {"status": "WAITING_FOR_NATIVE_NOTE_RESPONSE",
                               "effects_applied": False,
                               "sealed_frontier": delta.get("trace_frontier")}
            bound_note_id = story_delta.get("bound_note_id")
            if type(bound_note_id) is int and active_request["objective"].get("note_id") is None:
                active_request["objective"]["note_id"] = bound_note_id
            if interventions and interventions[0].get("kind") == "author_story_edit":
                edit_result = next((row for row in delta.get("interventions", [])
                                    if isinstance(row, Mapping)), None)
                proposed = interventions[0]["request"]
                if isinstance(edit_result, Mapping) and edit_result.get("status") == "UPDATED":
                    active_request = deepcopy(proposed)
            for match in matched:
                fired.add(match["rule_index"])
            record = {"minute": minute, "interventions": interventions,
                      "intervention_results": delta.get("interventions"),
                      "trace_frontier": delta.get("trace_frontier"),
                      "story_process": story_delta,
                      "actor_steps": delta.get("actor_steps"),
                      "typed_trace": _compact_typed_delta(delta.get("typed_trace"), minute),
                      "verdicts": delta.get("verdicts")}
            steps.append(record)
            previous_observation = {"story_process": story_delta}
            if story_delta.get("terminal") is True:
                status = "TERMINAL"
                break

        # Exactly one full final trace and a separate committed DB readback.
        call_index += 1
        final_args = {"scene_id": scene_id}
        _write_once(run_dir / f"rpc-{call_index:04d}-get_trace-request.json", final_args)
        final_trace = rpc("get_trace", final_args)
        if not isinstance(final_trace, Mapping):
            raise RuntimeError("final get_trace response must be an object")
        _write_once(run_dir / "final-native-trace.json", final_trace)
        status = final_trace.get("run_status", status)
        if export_db:
            db_evidence, db_export = export_db_evidence(scene_id)
            _write_once(run_dir / "db-export-reference.json", db_export)
            if db_evidence is not None:
                raw_db = _copy_db_artifact(db_export, run_dir, "final-db-evidence.json")
                cost = _db_cost_metrics(db_evidence, scene_id,
                                        final_trace.get("story_process", {}))
                _write_once(run_dir / "db-readback-summary.json", {
                    "scene_id": scene_id, **raw_db, **cost})
    except Exception as exc:
        expected_reset_rejection = (
            scene_id is None
            and case.get("expected", {}).get("reset") == "REJECTED_BEFORE_SCENE_CREATE"
            and type(exc) is RuntimeError
            and "P3 control rejected operation (ValueError)" in str(exc))
        returned_reset_rejection = (
            scene_id is None
            and case.get("expected", {}).get("reset") == "REJECTED_BEFORE_SCENE_CREATE"
            and isinstance(reset_result, Mapping)
            and reset_result.get("ok") is False
            and reset_result.get("scene_created") is False
            and isinstance(reset_result.get("error"), Mapping)
            and reset_result["error"].get("code") == "INVALID_STORY_PROCESS_REQUEST")
        if expected_reset_rejection or returned_reset_rejection:
            status = "EXPECTED_RESET_REJECTION"
            error = None
            _write_once(run_dir / "reset-rejection-evidence.json", {
                "operation": "reset_p5_scenario", "result": status,
                "native_error": (reset_result.get("error") if returned_reset_rejection
                                 else str(exc)), "scene_created": False,
                "expected": case["expected"]})
        else:
            error = {"stage": "native_story_run", "error_type": type(exc).__name__,
                     "error_message": str(exc)[:500], "scene_id": scene_id}
            _write_once(run_dir / "failure.json", error)
        if scene_id is not None and final_trace is None:
            # Preserve failure state once; never reset/replay this scene.
            try:
                call_index += 1
                final_args = {"scene_id": scene_id}
                _write_once(run_dir / f"rpc-{call_index:04d}-get_trace-request.json", final_args)
                final_trace = rpc("get_trace", final_args)
                if not isinstance(final_trace, Mapping):
                    raise RuntimeError("failure get_trace response must be an object")
                _write_once(run_dir / "failure-final-native-trace.json", final_trace)
                if export_db:
                    db_evidence, db_export = export_db_evidence(scene_id)
                    _write_once(run_dir / "failure-db-export-reference.json", db_export)
                    if isinstance(db_evidence, Mapping):
                        raw_db = _copy_db_artifact(db_export, run_dir, "failure-db-evidence.json")
                        cost = _db_cost_metrics(db_evidence, scene_id,
                                                final_trace.get("story_process", {}))
                        _write_once(run_dir / "failure-db-readback-summary.json", {
                            "scene_id": scene_id, **raw_db, **cost})
            except Exception as capture_exc:
                _write_once(run_dir / "failure-capture-error.json", {
                    "error_type": type(capture_exc).__name__, "error_message": str(capture_exc)[:300]})
    assessment = _assess_case(case, final_trace, steps, run_dir)
    wall_seconds = round(monotonic() - run_started, 6)
    controller_decisions = (final_trace.get("story_process", {}).get("controller_decisions", [])
                            if isinstance(final_trace, Mapping) else [])
    actual_callbacks = [row for decision in controller_decisions if isinstance(decision, Mapping)
                        for row in decision.get("attempted_methods", []) if isinstance(row, Mapping)]
    diagnostics = [row for decision in controller_decisions if isinstance(decision, Mapping)
                   for row in decision.get("alternative_guard_diagnostics", []) if isinstance(row, Mapping)]
    summary = {"schema": "native-story-process-run-summary-v1", "case_id": case_id,
               "scene_id": scene_id, "status": status, "steps_recorded": len(steps),
               "reactive_rules_fired": sorted(fired), "error": error,
               "assessment": assessment,
               "final_story_process": final_trace.get("story_process") if isinstance(final_trace, Mapping) else None,
               "cost_metrics": {"controller_decision_count": len(controller_decisions),
                                "actual_method_callback_count": len(actual_callbacks),
                                "actual_method_callbacks_by_id": {
                                    method: sum(row.get("method_id") == method for row in actual_callbacks)
                                    for method in sorted({str(row.get("method_id")) for row in actual_callbacks})},
                                "alternative_guard_diagnostics_not_execution": len(diagnostics),
                                "runner_wall_seconds_excluding_service_lifecycle": wall_seconds,
                                "native_world_costs": (db_readback if isinstance(db_evidence, Mapping)
                                                       and (db_readback := _db_cost_metrics(
                                                           db_evidence, scene_id, final_trace.get("story_process", {})))
                                                       else None)},
               "db_export": db_export, "run_directory": str(run_dir),
               "source_manifest": identity["source_manifest"]}
    _write_once(run_dir / "summary.json", summary)
    return summary, run_dir


def _assess_case(case: Mapping[str, Any], trace: Any, steps: list[Mapping[str, Any]],
                 run_dir: Path) -> dict[str, Any] | None:
    """Emit narrow, evidence-backed outcomes for cases with explicit postconditions."""
    if not isinstance(trace, Mapping):
        return None
    if case.get("case_id") == "resource-held-by-player":
        scene_identity = _read_json(run_dir / "scene_identity.json")
        item_id = (scene_identity.get("items", {}).get("courier_supply", {})
                   if isinstance(scene_identity.get("items"), Mapping) else {})
        item_id = item_id.get("id") if isinstance(item_id, Mapping) else None
        player_id = scene_identity.get("player", {}).get("id") if isinstance(scene_identity.get("player"), Mapping) else None
        minute_two = next((row for row in steps if row.get("minute") == 2), {})
        results = minute_two.get("intervention_results") or []
        result = results[0] if results and isinstance(results[0], Mapping) else {}
        receipt = result.get("receipt") if isinstance(result.get("receipt"), Mapping) else {}
        snapshots = trace.get("world_snapshots", [])
        last_snapshot = snapshots[-1] if snapshots and isinstance(snapshots[-1], Mapping) else {}
        player_holds_item = (type(item_id) is int and type(player_id) is int
                             and last_snapshot.get("item_locations", {}).get("courier_supply") == player_id)
        binding = (trace.get("world_capability_projection", {}).get("task_bindings", {}).get("A", {})
                   if isinstance(trace.get("world_capability_projection"), Mapping) else {})
        actor_a = next((row for row in trace.get("actor_evidence", [])
                        if isinstance(row, Mapping) and row.get("actor_alias") == "A"), {})
        receipts = actor_a.get("native_receipts", []) if isinstance(actor_a, Mapping) else []
        a_lacks_resource = (binding.get("item_alias") == "courier_supply"
                            and binding.get("item_id") == item_id
                            and not any(isinstance(row, Mapping) and row.get("item_id") == item_id
                                        and row.get("kind") == "drop" and row.get("settled") is True
                                        for row in receipts))
        story = trace.get("story_process", {})
        verdicts = story.get("real_verdicts", []) if isinstance(story, Mapping) else []
        no_native_note = (story.get("bound_note_id") is None and any(
            isinstance(row, Mapping) and row.get("status") == "NO_NATIVE_NOTE_EVIDENCE"
            and row.get("verdict") == "NOT_SATISFIED" for row in verdicts))
        assessment = {"resource_get_settled": result.get("status") == "SETTLED"
                      and receipt.get("settled") is True and receipt.get("item_id") == item_id
                      and receipt.get("actor_alias") == "player",
                      "resource_held_through_final_snapshot": player_holds_item,
                      "A_task_binding_is_same_item_and_unsettled": a_lacks_resource,
                      "story_result": "UNBOUND_NO_NATIVE_NOTE" if no_native_note else "NATIVE_NOTE_EVIDENCE_PRESENT_OR_UNCERTAIN",
                      "goal_result": "NOT_SATISFIED" if no_native_note else "NOT_CERTIFIED",
                      "sealed_horizon_reached": trace.get("now") == trace.get("horizon")
                      and trace.get("complete_through", {}).get("events") == trace.get("horizon")
                      and trace.get("complete_through", {}).get("values") == trace.get("horizon"),
                      "causal_chain": case.get("resource_causal_chain")}
        assessment["pass"] = bool(assessment["resource_get_settled"]
                                  and player_holds_item and a_lacks_resource and no_native_note
                                  and assessment["sealed_horizon_reached"])
        return assessment
    if case.get("case_id") == "locked-refusal-abort":
        story = trace.get("story_process", {})
        events = story.get("controller_events", []) if isinstance(story, Mapping) else []
        expected_hash = case.get("locked_fragment_template", {}).get("sequence_sha256")
        abort = next((row for row in events if isinstance(row, Mapping)
                      and row.get("event_type") == "P5_STORY_LOCKED_FRAGMENT_ABORTED"
                      and row.get("sealed") is True), None)
        reason = abort.get("reason", []) if isinstance(abort, Mapping) else []
        decisions = story.get("controller_decisions", []) if isinstance(story, Mapping) else []
        locked_aborted = any(isinstance(row, Mapping)
                             and row.get("status") == "LOCKED_ABORTED"
                             for row in decisions)
        def strings(value: Any) -> list[str]:
            if isinstance(value, str):
                return [value]
            if isinstance(value, Mapping):
                return [entry for child in value.values() for entry in strings(child)]
            if isinstance(value, list):
                return [entry for child in value for entry in strings(child)]
            return []
        verdict_rows = story.get("real_verdicts", []) if isinstance(story, Mapping) else []
        violated = any(isinstance(verdict, Mapping) and verdict.get("verdict") == "VIOLATED"
                       for row in verdict_rows if isinstance(row, Mapping)
                       for verdict in row.get("verdicts", []) if isinstance(row.get("verdicts"), list))
        if not violated:
            violated = any(isinstance(row, Mapping)
                           and (row.get("status") == "VIOLATED" or row.get("verdict") == "VIOLATED")
                           for row in verdict_rows)
        assessment = {"abort_event_sealed": abort is not None,
                      "abort_reason": reason,
                      "expected_guard_mismatch_observed": (
                          case.get("expected", {}).get("abort_reason") in strings(reason)),
                      "locked_core_hash_unchanged": isinstance(abort, Mapping)
                      and abort.get("immutable_sequence_sha256") == expected_hash,
                      "decision_locked_aborted": locked_aborted,
                      "goal_result": "VIOLATED" if violated else "NOT_CERTIFIED",
                      "no_locked_task_requests": all(not row.get("task_requests")
                                                       for row in decisions if isinstance(row, Mapping))}
        assessment["pass"] = all((assessment["abort_event_sealed"],
                                  assessment["expected_guard_mismatch_observed"],
                                  assessment["locked_core_hash_unchanged"],
                                  assessment["decision_locked_aborted"],
                                  assessment["goal_result"] == "VIOLATED",
                                  assessment["no_locked_task_requests"]))
        return assessment
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="run exactly one case from story_cases/suite.json")
    parser.add_argument("--suite", type=Path, default=SUITE_PATH)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--no-db-export", action="store_true")
    parser.add_argument("--reload-existing-evennia", action="store_true",
                        help="stop/start only the configured local Evennia service and retain lifecycle logs")
    parser.add_argument("--resume-existing-scene", metavar="SCENE_ID",
                        help="continue this exact existing native scene without reset")
    parser.add_argument("--expected-minute", type=int,
                        help="required sealed frontier for --resume-existing-scene")
    parser.add_argument("--prior-run-dir", type=Path,
                        help="preserved original run directory containing scene_identity.json")
    parser.add_argument("--run-purpose", choices=("BUGFIX_REGRESSION", "BUGFIX_REGRESSION_RENDEZVOUS"),
                        help="mark an authorized task-refusal repair regression")
    parser.add_argument("--predecessor-run-dir", type=Path, action="append",
                        help="preserved failed run cited by the repair regression; repeat for two predecessors")
    args = parser.parse_args()
    if (args.run_purpose is None) != (args.predecessor_run_dir is None):
        parser.error("--run-purpose and --predecessor-run-dir must be supplied together")
    continuation_args = (args.resume_existing_scene, args.expected_minute, args.prior_run_dir)
    if any(value is not None for value in continuation_args) and not all(value is not None for value in continuation_args):
        parser.error("--resume-existing-scene requires --expected-minute and --prior-run-dir")
    lifecycle_dir = None
    if args.reload_existing_evennia:
        lifecycle_dir = _allocate_run_dir(args.runs_dir, f"{args.case_id}-service-lifecycle")
        stop = rpc_call("stop_world", {})
        _write_once(lifecycle_dir / "stop-result.json", stop)
        if not isinstance(stop, Mapping) or stop.get("status") != "STOPPED":
            raise RuntimeError("scoped Evennia stop helper did not report STOPPED; lifecycle evidence retained")
        start = rpc_call("start_world", {})
        _write_once(lifecycle_dir / "start-result.json", start)
        if not isinstance(start, Mapping) or start.get("status") != "STARTED":
            raise RuntimeError("scoped Evennia start helper did not report STARTED; lifecycle evidence retained")
        health = rpc_call("health", {})
        _write_once(lifecycle_dir / "health-result.json", health)
        if not isinstance(health, Mapping) or health.get("status") != "READY":
            raise RuntimeError("authenticated P3 health did not return READY after reload; lifecycle evidence retained")
    result, run_dir = run_case(args.case_id, suite_path=args.suite,
                               runs_dir=args.runs_dir, export_db=not args.no_db_export,
                               lifecycle_dir=lifecycle_dir,
                               existing_scene_id=args.resume_existing_scene,
                               expected_minute=args.expected_minute,
                               continuation_of=args.prior_run_dir,
                               run_purpose=args.run_purpose,
                               predecessor_run_dirs=args.predecessor_run_dir)
    print(json.dumps({"summary": result, "run_directory": str(run_dir)},
                     ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0 if result.get("error") is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
