"""Non-overwriting runner for the ongoing-station native development cases.

The runner advances the existing P5 scene one native minute at a time. It
does not issue NPC commands, observe actors, select their goals, or simulate
receipts. Native scene creation is disabled unless ``--execute`` is explicit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import shutil
import subprocess
from typing import Any, Callable, Mapping

from tools.native_platform_v0.p3.mcp_stdio import PROJECT_ROOT, rpc_call

HERE = Path(__file__).resolve().parent
SUITE_PATH = HERE / "cases/suite.json"
RUNS_DIR = PROJECT_ROOT / "02_实验/Mature_Methods_Integration_v1/runs"
SOURCE_PATHS = (
    "tools/native_platform_v0/p5/ongoing_station/__init__.py",
    "tools/native_platform_v0/p5/ongoing_station/README.md",
    "tools/native_platform_v0/p5/ongoing_station/runner.py",
    "tools/native_platform_v0/p5/ongoing_station/audit.py",
    "tools/native_platform_v0/p5/ongoing_station/replay.py",
    "tools/native_platform_v0/p5/ongoing_station/cases/suite.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/system-work-suite.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/system-work-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/system-work-v2-store-lock.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/system-work-v2-order-store-lock.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/m5-e1-e4-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/m5-e1-archive-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/m5-e3-handover-v2.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/m5-e4-handover-deadline-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/empty-author-bundle-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/author-pair-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/author-pair-v2.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/author-t4-result-only-v1.json",
    "tools/native_platform_v0/p5/ongoing_station/cases/author-t4-result-only-v2.json",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_runner.py",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_native.py",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_work.py",
    "tools/native_platform_v0/p5/tests/test_story_process_planning.py",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_actor.py",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_controller.py",
    "tools/native_platform_v0/p5/tests/test_ongoing_station_model.py",
    "tools/native_platform_v0/p5/tests/test_system_work_audit.py",
    "tools/native_platform_v0/p5/ongoing_station/model.py",
    "tools/native_platform_v0/p5/ongoing_station/native.py",
    "tools/native_platform_v0/p5/ongoing_station/controller.py",
    "tools/native_platform_v0/p5/ongoing_station/actor.py",
    "tools/native_platform_v0/p5/ongoing_station/goals.py",
    "tools/native_platform_v0/p5/ongoing_station/commands.py",
    "tools/native_platform_v0/p5/ongoing_station/work.py",
    "tools/native_platform_v0/p5/ongoing_station/system_work_audit.py",
    "tools/native_platform_v0/p5/story_process/planning.py",
    "tools/native_platform_v0/p5/story_process/native.py",
    "tools/native_platform_v0/p5/story_process/model.py",
    "tools/native_platform_v0/p5/agency.py",
    "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p5/world.py",
    "tools/native_platform_v0/p5/bundle.py",
    "tools/native_platform_v0/p5/runner.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/planning.py",
    "tools/native_platform_v0/p3/tests/test_p3_station_task_planning.py",
    "tools/native_platform_v0/p3/p4_world.py",
    "tools/native_platform_v0/p3/p4_social.py",
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/export_evidence.py",
    "tools/native_platform_v0/p3/tests/test_headless_control.py",
    "tools/trajectory_constraints_v0/trace.py",
)


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        stream.write("\n")


def _allocate_run_dir(root: Path, case_id: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in case_id)[:48]
    for _ in range(24):
        path = root / f"story-ongoing-station-{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique ongoing-station run directory")


def _source_manifest(snapshot_root: Path) -> dict[str, Any]:
    snapshot_root.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    copied: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        source = PROJECT_ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(f"required source snapshot input is missing: {relative}")
        raw = source.read_bytes()
        digest = _sha(raw)
        target = snapshot_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if _sha(target.read_bytes()) != digest:
            raise RuntimeError(f"source snapshot hash mismatch: {relative}")
        hashes[relative] = digest
        copied[relative] = str(target.relative_to(snapshot_root))
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    def git(*args: str) -> str | None:
        result = subprocess.run(["git", *args], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    branch = git("branch", "--show-current")
    return {"head": git("rev-parse", "HEAD"),
            "branch": branch,
            "local_branch_ref": git("rev-parse", f"refs/heads/{branch}") if branch else None,
            "base_review_ref": "refs/remotes/origin/webgpt-sync",
            "base_review_ref_oid": git("rev-parse", "refs/remotes/origin/webgpt-sync"),
            "working_tree_file_sha256": hashes,
            "working_tree_file_set_sha256": _sha(packed),
            "copied_source_paths": copied,
            "snapshot_semantics": "exact copied working-tree bytes; base review ref is context only"}


def load_case(case_id: str, suite_path: Path = SUITE_PATH) -> tuple[dict[str, Any], dict[str, Any]]:
    suite = _read_json(suite_path)
    if suite.get("schema") not in {"ongoing-station-case-suite-v1",
                                    "ongoing-station-system-work-suite-v1"}:
        raise ValueError("unsupported ongoing-station case suite")
    matches = [row for row in suite.get("cases", []) if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise ValueError("case_id must identify exactly one fixed case")
    case, common = matches[0], suite["common"]
    if case_id == "t1-no-author-autonomy" and (
            common["ongoing_station"].get("author", False) is not None
            or case.get("expected", {}).get("author", False) is not None):
        raise ValueError("T1 requires a genuinely null ongoing-station author package")
    if suite.get("suite_id") == "ongoing-station-m5-e1-e4-v1":
        if len(suite.get("cases", [])) != 8 or suite.get("run_policy", {}).get("max_scenes") != 8:
            raise ValueError("M5 E1-E4 suite must remain within its fixed eight-scene bound")
        if case.get("strategy") not in {"gtpyhop", "event_driven"}:
            raise ValueError("M5 case has an unsupported strategy arm")
    if suite.get("schema") == "ongoing-station-system-work-suite-v1":
        if (suite.get("suite_id") != "ongoing-station-system-work-v1"
                or len(suite.get("cases", [])) != 4
                or suite.get("run_policy", {}).get("max_scenes") != 4):
            raise ValueError("station work suite must contain exactly its fixed four native scenes")
        if case.get("strategy") not in {"gtpyhop", "event_driven"}:
            raise ValueError("station work case has an unsupported strategy arm")
        if common.get("ongoing_station", {}).get("game_content") != "station_work_v1":
            raise ValueError("station work cases require explicit registered station_work_v1 content")
    return suite, case


def _compact_step(result: Any) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise RuntimeError("step_world returned a non-object response")
    rounds = result.get("rounds")
    if not isinstance(rounds, list) or len(rounds) != 1 or not isinstance(rounds[0], Mapping):
        raise RuntimeError("one-minute step must return exactly one native round")
    row = rounds[0]
    # Keep the minute delta, never duplicate the cumulative final trace.
    keep = ("minute", "completed", "event_complete", "unsealed_event_ids", "trace_frontier",
            "actor_steps", "interventions", "ongoing_station", "verdicts")
    return {"scene_id": result.get("scene_id"),
            "round": {key: row[key] for key in keep if key in row},
            "omitted_cumulative_fields": ["final"]}


def _resolve_case_intervention(row: Mapping[str, Any], scene: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a stable case alias to the exact generated-scene item ID."""
    resolved = dict(row)
    if resolved.get("kind") == "station_request_tool_loan":
        if set(resolved) != {"at", "kind", "tool_alias", "lender_alias",
                             "borrower_alias", "due_minute"}:
            raise ValueError("station loan case row must name one registered tool alias")
        if resolved.get("tool_alias") != "station_tool":
            raise ValueError("station loan request must use the registered station_tool alias")
        items = scene.get("items") if isinstance(scene.get("items"), Mapping) else {}
        item = items.get("station_tool")
        if not isinstance(item, Mapping) or type(item.get("id")) is not int:
            raise ValueError("reset response omitted the exact registered station tool ID")
        resolved.pop("tool_alias")
        resolved["tool_id"] = item["id"]
    return resolved


def _copy_db_artifact(export_meta: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    source = export_meta.get("artifact_path")
    if not isinstance(source, str) or not Path(source).is_file():
        raise RuntimeError("independent DB exporter omitted its readable raw artifact")
    raw = Path(source).read_bytes()
    digest = _sha(raw)
    if export_meta.get("artifact_sha256") != digest:
        raise RuntimeError("DB export artifact hash does not match exporter metadata")
    destination = run_dir / "db-readback.json"
    with destination.open("xb") as stream:
        stream.write(raw)
    if _sha(destination.read_bytes()) != digest:
        raise RuntimeError("copied DB readback hash mismatch")
    return {"relative_path": destination.name, "sha256": digest,
            "bytes": len(raw)}


def _run_player_action_batch(scene_id: str, scene: Mapping[str, Any], batch: Mapping[str, Any],
                             rpc: Callable, run_dir: Path) -> dict[str, Any]:
    """Execute only registered generated-player commands and preserve each receipt.

    These commands form physical history interventions; they never target an NPC
    and do not advance the simulation clock or seed actor commitments.
    """
    required = {"batch_id", "at_minute", "phase", "actions"}
    if set(batch) != required or batch.get("phase") not in {"before_step", "after_step"}:
        raise ValueError("player action batch requires batch_id/at_minute/phase/actions")
    if not isinstance(batch.get("actions"), list) or not batch["actions"]:
        raise ValueError("player action batch must contain at least one action")
    item_map = scene.get("items") if isinstance(scene.get("items"), Mapping) else {}
    record: dict[str, Any] = {"batch_id": batch["batch_id"],
        "scene_id": scene_id, "at_minute": batch["at_minute"],
        "phase": batch["phase"], "actor_role": "player", "actions": [],
        "clock_effect": "none; actions occur between native minute callbacks"}
    try:
        for index, action in enumerate(batch["actions"]):
            if not isinstance(action, Mapping) or action.get("operation") not in {
                    "move", "get", "drop"}:
                raise ValueError("player history actions must be native move/get/drop")
            operation = action["operation"]
            args: dict[str, Any] = {"scene_id": scene_id, "actor_role": "player",
                                    "operation": operation}
            if operation == "move":
                if set(action) != {"operation", "direction"}:
                    raise ValueError("player move requires exactly operation/direction")
                args["direction"] = action["direction"]
            else:
                if set(action) != {"operation", "item_alias"}:
                    raise ValueError("player get/drop requires exactly operation/item_alias")
                item = item_map.get(action["item_alias"])
                if not isinstance(item, Mapping) or type(item.get("id")) is not int:
                    raise ValueError("player item alias is not a registered generated scene item")
                args["item_id"] = item["id"]
            response = rpc("inject_action", args)
            row = {"action_index": index, "action": dict(action),
                   "rpc_arguments": args, "receipt": response}
            record["actions"].append(row)
            if not isinstance(response, Mapping) or response.get("settled") is not True:
                raise RuntimeError(f"player history action {index} did not settle")
        record["status"] = "ALL_ACTIONS_SETTLED"
    except Exception as exc:
        record["status"] = "FAILED"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)[:400]}
        target = run_dir / f"player-actions-{batch['batch_id']}.json"
        _write_once(target, record)
        raise
    target = run_dir / f"player-actions-{batch['batch_id']}.json"
    _write_once(target, record)
    return record


def run_case(case_id: str, *, suite_path: Path = SUITE_PATH,
             runs_dir: Path = RUNS_DIR, call_rpc: Callable | None = None,
             db_exporter: Callable | None = None, execute: bool = False) -> tuple[dict[str, Any], Path]:
    suite, case = load_case(case_id, suite_path)
    common = suite["common"]
    from .model import load_profile
    for author_key in ("author_file", "edit_author_file"):
        author_file = case.get(author_key)
        author = (_read_json(suite_path.parent / author_file)
                  if author_file is not None else common["ongoing_station"].get("author"))
        load_profile({**common["ongoing_station"], "author": author})
    if not execute:
        raise PermissionError("native scene creation requires the explicit --execute flag")
    rpc = call_rpc or rpc_call
    health = rpc("health", {})
    if not isinstance(health, Mapping) or health.get("status") != "READY":
        raise RuntimeError("authenticated P3 health did not return READY")

    run_dir = _allocate_run_dir(runs_dir, case_id)
    source_manifest = _source_manifest(run_dir / "source-snapshot")
    bundle_path = suite_path.parent / common["bundle"]
    bundle = _read_json(bundle_path)
    station_profile = dict(common["ongoing_station"])
    author_file = case.get("author_file")
    if author_file is not None:
        station_profile["author"] = _read_json(suite_path.parent / author_file)
    edit_author_file = case.get("edit_author_file")
    edit_author = (_read_json(suite_path.parent / edit_author_file)
                   if edit_author_file is not None else None)
    interventions = []
    for row in case.get("interventions", []):
        resolved = dict(row)
        if resolved.pop("author_file", None) is not None:
            if edit_author is None:
                raise ValueError("edit intervention references no edit_author_file")
            resolved["author"] = edit_author
        interventions.append(resolved)
    reset_args = {"bundle": bundle,
                  "initial_social_preset": common["initial_social_preset"],
                  "horizon": common["horizon"], "seed": common["seed"],
                  "director_enabled": common["director_enabled"],
                  "shared_supply": common["shared_supply"],
                  "initial_main_open": common["initial_main_open"],
                  "story_strategy": case["strategy"],
                  "ongoing_station": station_profile}
    identity = {"schema": "ongoing-station-run-identity-v1",
                "case_id": case_id, "strategy": case["strategy"],
                "suite_sha256": _sha(suite_path.read_bytes()),
                "bundle_sha256": _sha(bundle_path.read_bytes()),
                "profile": station_profile,
                "edit_author": edit_author,
                "interventions": interventions,
                "player_action_batches": case.get("player_action_batches", []),
                "seed": common["seed"], "horizon": common["horizon"],
                "source_manifest": source_manifest,
                "native_execution": "one P5/Evennia instance; no NPC commands or external actor observations"}
    _write_once(run_dir / "identity.json", identity)
    _write_once(run_dir / "case-input.json", {"reset_args": reset_args,
                                               "interventions": interventions,
                                               "player_action_batches": case.get("player_action_batches", []),
                                               "expected": case.get("expected")})
    summary: dict[str, Any] = {"case_id": case_id, "status": "INCOMPLETE",
                               "scene_id": None, "steps_recorded": 0,
                               "db_readback": None, "error": None}
    try:
        created = rpc("reset_p5_scenario", reset_args)
        _write_once(run_dir / "reset-response.json", created)
        if not isinstance(created, Mapping) or created.get("ok") is not True:
            raise RuntimeError("reset_p5_scenario did not create the authorized opt-in scene")
        scene = created.get("scene")
        scene_id = scene.get("scene_id") if isinstance(scene, Mapping) else None
        if not isinstance(scene_id, str) or not scene_id:
            raise RuntimeError("reset result omitted exact native scene_id")
        summary["scene_id"] = scene_id
        _write_once(run_dir / "scene-identity.json", scene)
        for minute in range(1, int(common["horizon"]) + 1):
            for batch in case.get("player_action_batches", []):
                if batch.get("at_minute") == minute and batch.get("phase") == "before_step":
                    _run_player_action_batch(scene_id, scene, batch, rpc, run_dir)
            if case.get("stop_before_edit_if_archive") is True and any(
                    row.get("kind") == "edit_ongoing_station_author" and row.get("at") == minute
                    for row in interventions):
                prefix_minute = int(case.get("capture_prefix_after_minute", minute - 1))
                prefix_path = run_dir / f"prefix-after-minute-{prefix_minute:02d}.json"
                pre_edit_trace = _read_json(prefix_path) if prefix_path.is_file() else rpc(
                    "get_trace", {"scene_id": scene_id})
                station_prefix = pre_edit_trace.get("ongoing_station", {})
                station_prefix = station_prefix if isinstance(station_prefix, Mapping) else {}
                note_id = station_prefix.get("bound_note_id")
                note_archived = any(row.get("event_type") == "p5_note_archived"
                    and row.get("args", {}).get("item", {}).get("stable_id") == str(note_id)
                    for row in station_prefix.get("typed_events", [])
                    if isinstance(row, Mapping)) if note_id is not None else False
                if note_archived:
                    _write_once(run_dir / "pre-edit-stop.json", {
                        "status": "STOPPED_BEFORE_EDIT",
                        "reason": "exact objective note was already physically archived before the scheduled future edit",
                        "note_id": note_id, "edit_minute_not_executed": minute,
                        "prefix_artifact": prefix_path.name})
                    summary["pre_edit_stop"] = "objective_already_archived"
                    break
            at_minute = [_resolve_case_intervention(row, scene) for row in interventions
                         if isinstance(row, Mapping) and row.get("at") == minute]
            step_args = {"scene_id": scene_id, "rounds": 1}
            if at_minute:
                step_args["interventions"] = at_minute
            step = rpc("step_world", step_args)
            try:
                compact = _compact_step(step)
            except Exception:
                _write_once(run_dir / f"minute-{minute:02d}-invalid-response.json", step)
                raise
            _write_once(run_dir / f"minute-{minute:02d}.json", compact)
            summary["steps_recorded"] = minute
            for batch in case.get("player_action_batches", []):
                if batch.get("at_minute") == minute and batch.get("phase") == "after_step":
                    _run_player_action_batch(scene_id, scene, batch, rpc, run_dir)
            if minute == case.get("capture_prefix_after_minute"):
                prefix = rpc("get_trace", {"scene_id": scene_id})
                _write_once(run_dir / f"prefix-after-minute-{minute:02d}.json", prefix)
        trace = rpc("get_trace", {"scene_id": scene_id})
        _write_once(run_dir / "final-trace.json", trace)
        if db_exporter is None:
            from tools.native_platform_v0.p5.runner import export_db_evidence
            db_exporter = export_db_evidence
        db_evidence, export_meta = db_exporter(scene_id)
        if not isinstance(db_evidence, Mapping) or not isinstance(export_meta, Mapping):
            raise RuntimeError("DB exporter returned no independent evidence record")
        db_copy = _copy_db_artifact(export_meta, run_dir)
        summary["db_readback"] = db_copy
        from .audit import (audit_actor_deferral, audit_author_pair, audit_handover_deadline_stress,
                            audit_history_prefix,
                            audit_mid_episode_resource, audit_required_story_events,
                            audit_resource_negative, audit_t1)
        from .system_work_audit import audit_station_episode, audit_station_work
        scene_identity = _read_json(run_dir / "scene-identity.json")
        db_readback = _read_json(run_dir / db_copy["relative_path"])
        audit_kind = case.get("audit", "t1" if author_file is None else "author_pair")
        if audit_kind == "t1":
            assessment = audit_t1(trace, scene_identity, db_readback)
        elif audit_kind == "author_pair":
            assessment = audit_author_pair(
                trace, scene_identity, db_readback, station_profile["author"],
                edit_author=edit_author,
                activation_minute=int(next(row["at"] for row in interventions
                                           if row.get("kind") == "activate_ongoing_station")))
        elif audit_kind == "actor_deferral":
            assessment = audit_actor_deferral(
                trace, scene_identity, db_readback,
                expected_author=station_profile["author"], edit_author=edit_author,
                activation_minute=5, edit_minute=8)
        elif audit_kind == "resource_negative":
            assessment = audit_resource_negative(trace, scene_identity, db_readback,
                                                 expected_intervention=interventions[0])
        elif audit_kind == "history_prefix":
            prefix_minute = int(case["capture_prefix_after_minute"])
            prefix_trace = _read_json(run_dir / f"prefix-after-minute-{prefix_minute:02d}.json")
            assessment = audit_history_prefix(prefix_trace, trace, scene_identity, db_readback,
                                               history_condition=case["history_condition"])
        elif audit_kind == "required_story_events":
            prefix_minute = int(case["capture_prefix_after_minute"])
            prefix_trace = _read_json(run_dir / f"prefix-after-minute-{prefix_minute:02d}.json")
            assessment = audit_required_story_events(trace, scene_identity, db_readback,
                initial_author=station_profile["author"], edit_author=edit_author,
                edit_minute=int(next(row["at"] for row in interventions
                                     if row.get("kind") == "edit_ongoing_station_author")),
                prefix=prefix_trace)
        elif audit_kind == "mid_episode_resource":
            assessment = audit_mid_episode_resource(trace, scene_identity, db_readback,
                expected_intervention=next(row for row in interventions
                    if row.get("kind") == "player_command"))
        elif audit_kind == "handover_deadline_stress":
            assessment = audit_handover_deadline_stress(trace, scene_identity, db_readback,
                author=station_profile["author"], deadline_minute=8)
        elif audit_kind == "station_work_episode":
            assessment = audit_station_episode(
                trace, db_readback,
                expected_constraint_statuses=case.get("expected", {}).get(
                    "constraint_statuses", {}),
                required_outcomes=tuple(case.get("expected", {}).get(
                    "required_outcomes", ())))
        elif audit_kind == "station_work_physical":
            assessment = audit_station_work(
                trace, db_readback,
                required_outcomes=tuple(case.get("expected", {}).get(
                    "required_outcomes", ())))
        elif audit_kind == "station_history_capture":
            physical = audit_station_work(
                trace, db_readback,
                required_outcomes=tuple(case.get("expected", {}).get(
                    "required_outcomes", ())))
            assessment = {"schema": "ongoing-station-history-capture-v1",
                "status": "PARTIAL", "pass": False,
                "history_condition": case.get("history_condition"),
                "physical_work_audit": physical,
                "causal_claim_allowed": False,
                "causal_claim_blocker": "requires paired post-run comparison of receipt-backed local history and the later same request/frontier",
                "note": "This per-scene capture is not a history-causality result."}
        else:
            raise ValueError(f"unsupported audit kind {audit_kind!r}")
        from .replay import write_replay_once
        _write_once(run_dir / "audit.json", assessment)
        write_replay_once(run_dir / "readable-replay.md", trace)
        summary["assessment"] = assessment
        summary["status"] = ("PASS" if assessment.get("pass") is True else
                             assessment.get("status") if assessment.get("status") in {
                                 "PARTIAL", "VERIFIED_NEGATIVE"} else
                             "NOT_CERTIFIED")
    except Exception as exc:
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)[:600]}
        _write_once(run_dir / "failure.json", summary)
        raise
    finally:
        _write_once(run_dir / "summary.json", summary)
    return summary, run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--suite", type=Path, default=SUITE_PATH)
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--execute", action="store_true",
                        help="create and advance one native scene; requires separate run authorization")
    args = parser.parse_args()
    if not args.execute:
        suite, case = load_case(args.case_id, args.suite)
        author_path = args.suite.parent / case["author_file"] if case.get("author_file") else None
        preflight_author = _read_json(author_path) if author_path else suite["common"]["ongoing_station"].get("author")
        if preflight_author is not None:
            from .model import load_profile
            load_profile({**suite["common"]["ongoing_station"], "author": preflight_author})
        edit_path = args.suite.parent / case["edit_author_file"] if case.get("edit_author_file") else None
        if edit_path:
            from .model import load_profile
            load_profile({**suite["common"]["ongoing_station"],
                          "author": _read_json(edit_path)})
        print(json.dumps({"status": "PREFLIGHT_ONLY", "case_id": case["case_id"],
                          "seed": suite["common"]["seed"],
                          "horizon": suite["common"]["horizon"],
                          "author_bundle_id": (preflight_author.get("bundle", {}).get("bundle_id")
                                               if isinstance(preflight_author, Mapping) else None),
                          "author_version": (preflight_author.get("bundle", {}).get("version")
                                             if isinstance(preflight_author, Mapping) else None),
                          "strategy": case.get("strategy"),
                          "interventions": case.get("interventions", []),
                          "native_execution": False},
                         ensure_ascii=False, indent=2))
        return 0
    summary, run_dir = run_case(args.case_id, suite_path=args.suite,
                                runs_dir=args.runs_dir, execute=True)
    print(json.dumps({"summary": summary, "run_directory": str(run_dir)},
                     ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0 if summary.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
