#!/usr/bin/env python3
"""Bounded OFF/ON supervisor for the Loaded RequestHire message-repair check.

This is a separate revision: the frozen decision-v1 runner and adapter remain
untouched. A hire is attributed only when the exact request provenance reaches
the recipient inbox, is consumed, produces the native setter receipt, and is
then observed as the recipient's real Job::Hired state.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime

from tools.veloren_native_decision_v1.adapter import RecruitmentController
from tools.veloren_native_decision_v1.run_pair import (
    CLEARED_INHERITED_ENV, DISK_FLOOR_BYTES, JsonlTail, LoadedPrefixGate,
    SERVER_GRACE_SECONDS, TELEMETRY_BYTE_CAP, TELEMETRY_RECORD_CAP,
    TELEMETRY_SECONDS_CAP, _validate_userdata_manifest, append_jsonl_once,
    local_now, sha256_file,
)


MAX_REQUESTS = 6
TRIAL_WALL_CAP_SECONDS = 360.0
POST_HIRE_OBSERVATION_SECONDS = 30.0
LEADER_UID = 476
FOLLOW_DISTANCE_METERS = 8.0
EVENT_CHAIN = (
    "native_recruit_msg_retained_rtsim",
    "native_recruit_msg_delivered_to_inbox",
    "native_recruit_hire_input_consumed",
    "native_recruit_hire_effect_applied",
    "native_recruit_job_observed",
)


def assets_tree_sha256(assets_root: Path, manifest_path: Path) -> str:
    """Verify every official asset file and the canonical tree digest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "veloren-assets-tree-v1":
        raise ValueError("unsupported official-assets manifest schema")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("assets manifest files must be a non-empty array")
    actual_paths = set()
    for item in assets_root.rglob("*"):
        if item.is_file():
            resolved = item.resolve()
            if not resolved.is_relative_to(assets_root.resolve()):
                raise ValueError("official asset tree contains a file escaping its root")
            actual_paths.add(item.relative_to(assets_root).as_posix())
    manifest_paths = {row.get("path") for row in files if isinstance(row, dict)}
    if len(manifest_paths) != len(files) or actual_paths != manifest_paths:
        raise ValueError("assets manifest must list exactly every actual file in the assets tree")
    previous = None
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("assets manifest entries must be objects")
        rel = row.get("path")
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError("asset manifest path must be a contained relative path")
        if previous is not None and rel <= previous:
            raise ValueError("assets manifest paths must be unique and sorted")
        previous = rel
        path = (assets_root / rel).resolve()
        if not path.is_relative_to(assets_root.resolve()) or not path.is_file():
            raise ValueError(f"missing or escaping official asset: {rel}")
        if path.stat().st_size != row.get("size_bytes") or sha256_file(path) != row.get("sha256"):
            raise ValueError(f"official asset hash mismatch: {rel}")
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tree_hash = hashlib.sha256(canonical).hexdigest()
    if tree_hash != manifest.get("tree_sha256"):
        raise ValueError("assets tree digest does not match manifest")
    return tree_hash


def validate_loaded_msg_freeze(freeze: dict) -> tuple[dict, dict, Path, Path]:
    """Validate the new revision's stricter runtime contract without launching."""
    if freeze.get("schema_version") != 1:
        raise ValueError("freeze schema_version must be 1")
    source, world = freeze.get("source"), freeze.get("world")
    runtime, trials = freeze.get("runtime"), freeze.get("trials")
    if not all(isinstance(value, dict) for value in (source, world, runtime, trials)):
        raise ValueError("freeze source/world/runtime/trials must be objects")
    if source.get("commit") != "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248":
        raise ValueError("source commit is not the pinned Veloren release")
    for key in ("source_patch_sha256", "cargo_lock_sha256", "binary_sha256"):
        if not isinstance(source.get(key), str) or len(source[key]) != 64:
            raise ValueError(f"source.{key} must be a full SHA-256")
    for path_key, hash_key in (("source_patch_path", "source_patch_sha256"),
                               ("cargo_lock_path", "cargo_lock_sha256"),
                               ("binary_path", "binary_sha256")):
        path = Path(source.get(path_key, "")).expanduser().resolve()
        if not path.is_file() or sha256_file(path) != source[hash_key]:
            raise ValueError(f"pinned source input mismatch: {path_key}")
    assets = Path(source.get("assets_path", "")).expanduser().resolve()
    manifest_path = Path(source.get("assets_manifest_path", "")).expanduser().resolve()
    if not assets.is_dir() or not manifest_path.is_file():
        raise ValueError("official assets and their full content manifest are required")
    if sha256_file(manifest_path) != source.get("assets_manifest_sha256"):
        raise ValueError("assets manifest SHA-256 mismatch")
    if assets_tree_sha256(assets, manifest_path) != source.get("assets_tree_sha256"):
        raise ValueError("assets tree SHA-256 mismatch")
    if world.get("world_seed") != 130626853:
        raise ValueError("world seed differs from the approved source world")
    for key in ("source_world_sha256", "settings_contract_sha256"):
        if not isinstance(world.get(key), str) or len(world[key]) != 64:
            raise ValueError(f"world.{key} must be a full SHA-256")
    if runtime.get("leader_uid") != LEADER_UID or runtime.get("loopback_only") is not True:
        raise ValueError("leader or network boundary differs from the approved contract")
    if runtime.get("query_address") is not None:
        raise ValueError("query_address must remain unset")
    if runtime.get("max_trial_wall_seconds") != 360 or runtime.get("disk_free_floor_bytes") != DISK_FLOOR_BYTES:
        raise ValueError("trial duration or disk safety floor differs from the approved contract")
    if runtime.get("max_requests") != MAX_REQUESTS or runtime.get("request_ttl_seconds") != 60:
        raise ValueError("the ON request budget must be six with a 60-second TTL")
    if runtime.get("first_trusted_hire_stops_submissions") is not True:
        raise ValueError("first trusted hire must freeze further submissions")
    if runtime.get("post_hire_observation_seconds") != POST_HIRE_OBSERVATION_SECONDS:
        raise ValueError("post-hire native observation cap must be 30 seconds")
    if (runtime.get("loaded_prefix_min_game_times") != 3
            or runtime.get("loaded_prefix_min_wall_seconds") != 2.0
            or runtime.get("loaded_candidates_required") != 2):
        raise ValueError("Loaded-prefix qualification must remain three game-time samples over two seconds with two candidates")
    expected_uids = [476, 433, 450, 451, 452, 459, 469, 472, 475, 442]
    if runtime.get("observe_npc_uids") != expected_uids or runtime.get("native_persister_npc_uids") != expected_uids:
        raise ValueError("OFF/ON must use the same approved observer/persister list including UID 442")
    if runtime.get("telemetry_record_cap") != TELEMETRY_RECORD_CAP or runtime.get("telemetry_byte_cap") != TELEMETRY_BYTE_CAP:
        raise ValueError("telemetry limits differ from the approved limits")
    if runtime.get("telemetry_seconds_cap") != TELEMETRY_SECONDS_CAP:
        raise ValueError("telemetry time limit differs from the approved limit")
    if trials.get("off", {}).get("userdata_path") == trials.get("on", {}).get("userdata_path"):
        raise ValueError("OFF and ON require distinct userdata copies")
    resolved = {}
    for mode in ("off", "on"):
        trial = trials.get(mode)
        if not isinstance(trial, dict):
            raise ValueError(f"trials.{mode} must be an object")
        userdata = Path(trial.get("userdata_path", "")).expanduser().resolve()
        manifest = Path(trial.get("userdata_manifest_path", "")).expanduser().resolve()
        if not userdata.is_dir() or not manifest.is_relative_to(userdata) or not manifest.is_file():
            raise ValueError(f"trials.{mode} userdata or manifest is invalid")
        if sha256_file(manifest) != trial.get("userdata_manifest_sha256"):
            raise ValueError(f"trials.{mode} manifest SHA-256 mismatch")
        if trial.get("source_world_sha256") != world.get("source_world_sha256"):
            raise ValueError(f"trials.{mode} source world digest mismatch")
        if trial.get("settings_contract_sha256") != world.get("settings_contract_sha256"):
            raise ValueError(f"trials.{mode} normalized settings mismatch")
        _validate_userdata_manifest(userdata, manifest)
        resolved[mode] = userdata
    return source, runtime, resolved["off"], resolved["on"]


class LoadedMsgChain:
    """Strict per-request provenance and native Job receipt verifier."""

    def __init__(self, leader_uid: int = LEADER_UID):
        self.leader_uid = leader_uid
        self.requests: dict[str, dict] = {}
        self.violations: list[dict] = []
        self.trusted_hires: list[dict] = []

    def register_request(self, request: dict) -> None:
        request_id = request.get("request_id")
        target_uid = request.get("target_uid")
        if (not isinstance(request_id, str) or not request_id
                or isinstance(target_uid, bool) or not isinstance(target_uid, int)):
            raise ValueError("request must have a non-empty id and integer target_uid")
        source = request.get("source")
        if not isinstance(source, str) or not source:
            raise ValueError("request must have a non-empty frozen source")
        if request_id in self.requests:
            raise ValueError("request_id reuse is forbidden")
        self.requests[request_id] = {
            "request": request, "target_uid": target_uid,
            "leader_uid": self.leader_uid, "decision_source": source,
            "accepted": False, "started": False, "message_sent": False,
            "stages": [], "effect_receipt": None, "trusted_job": None,
            "last_event_time": None, "tainted": False,
        }

    def observe(self, row: dict) -> dict | None:
        event = row.get("event")
        request_id = row.get("request_id")
        state = self.requests.get(request_id) if isinstance(request_id, str) else None
        if state is None:
            return None
        if state["tainted"]:
            return None
        expected = state["target_uid"]
        relevant = (event in EVENT_CHAIN or event in {
            "native_recruit_request_accepted", "native_recruit_started", "native_recruit_message_sent"})
        if relevant:
            event_time = row.get("time")
            if (not isinstance(event_time, (int, float)) or isinstance(event_time, bool)
                    or not math.isfinite(event_time)
                    or (state["last_event_time"] is not None and event_time < state["last_event_time"])):
                self._violate(request_id, "invalid_or_nonmonotonic_game_time", str(event))
                return None
            state["last_event_time"] = float(event_time)
        if event == "native_recruit_request_accepted":
            if row.get("leader_uid") == self.leader_uid and row.get("target_uid") == expected:
                state["accepted"] = True
            return None
        if event == "native_recruit_started":
            if (state["accepted"] and row.get("leader_uid") == self.leader_uid
                    and row.get("target_uid") == expected):
                state["started"] = True
            return None
        if event == "native_recruit_message_sent":
            if (state["started"] and row.get("leader_uid") == self.leader_uid
                    and row.get("target_uid") == expected):
                state["message_sent"] = True
            return None
        if event in EVENT_CHAIN[:-1]:
            if event in state["stages"]:
                self._violate(request_id, "duplicate_message_provenance_stage", event)
                return None
            required = {
                "source_uid": self.leader_uid, "leader_uid": self.leader_uid,
                "target_uid": expected, "recipient_uid": expected,
            }
            if event in EVENT_CHAIN[:3]:
                required["msg_kind"] = "RequestHire"
            if any(row.get(key) != value for key, value in required.items()):
                self._violate(request_id, "message_provenance_identity_mismatch", event)
                return None
            source = row.get("decision_source")
            if not isinstance(source, str) or not source:
                self._violate(request_id, "missing_decision_source", event)
                return None
            if source != state["decision_source"]:
                self._violate(request_id, "decision_source_changed", event)
                return None
            required_previous = {
                "native_recruit_msg_retained_rtsim": state["message_sent"],
                "native_recruit_msg_delivered_to_inbox": "native_recruit_msg_retained_rtsim" in state["stages"],
                "native_recruit_hire_input_consumed": "native_recruit_msg_delivered_to_inbox" in state["stages"],
                "native_recruit_hire_effect_applied": "native_recruit_hire_input_consumed" in state["stages"],
            }[event]
            if not required_previous or not state["accepted"] or not state["started"]:
                self._violate(request_id, "message_stage_out_of_order", event)
                return None
            if event == "native_recruit_hire_effect_applied" and row.get("hire_until") != "infinity":
                self._violate(request_id, "unexpected_native_hire_until", event)
                return None
            state["stages"].append(event)
            if event == "native_recruit_hire_effect_applied":
                state["effect_receipt"] = row
            return None
        if event != "native_recruit_job_observed":
            return None
        if (row.get("source_uid") != self.leader_uid or row.get("leader_uid") != self.leader_uid
                or row.get("target_uid") != expected or row.get("recipient_uid") != expected
                or row.get("job_actor_uid") != self.leader_uid
                or row.get("hired_by_uid") != self.leader_uid
                or row.get("hire_until") != "infinity"
                or not isinstance(row.get("leader_npc_id"), str) or not row["leader_npc_id"]
                or not isinstance(row.get("recipient_npc_id"), str) or not row["recipient_npc_id"]):
            self._violate(request_id, "job_observation_identity_or_state_mismatch", event)
            return None
        if state["stages"] != list(EVENT_CHAIN[:-1]):
            self._violate(request_id, "job_observed_without_complete_message_effect_chain", event)
            return None
        if state["decision_source"] != row.get("decision_source"):
            self._violate(request_id, "job_decision_source_mismatch", event)
            return None
        receipt = state["effect_receipt"]
        if not isinstance(receipt, dict) or any(receipt.get(key) != row.get(key)
                for key in ("request_id", "source_uid", "target_uid", "leader_uid",
                            "recipient_uid", "decision_source", "hire_until")):
            self._violate(request_id, "job_observation_does_not_match_effect_receipt", event)
            return None
        if state["trusted_job"] is not None:
            self._violate(request_id, "duplicate_job_observation", event)
            return None
        state["trusted_job"] = row
        self.trusted_hires.append(row)
        return row

    def _violate(self, request_id: str, reason: str, event: str) -> None:
        if request_id in self.requests:
            self.requests[request_id]["tainted"] = True
        self.violations.append({"request_id": request_id, "reason": reason, "source_event": event})


class OnTrialPolicy:
    """Small, testable policy for strict admission and bounded submission."""

    def __init__(self, mode: str):
        if mode not in ("off", "on"):
            raise ValueError("mode must be off or on")
        self.mode = mode
        self.qualified_prefix = mode == "off"
        self.request_count = 0
        self.insufficient_choices = False
        self.first_trusted_hire_mono: float | None = None
        self.requests_frozen = mode == "off"

    def qualify_prefix(self) -> None:
        if self.mode == "on":
            self.qualified_prefix = True

    def may_plan(self) -> bool:
        return (self.mode == "on" and self.qualified_prefix and not self.requests_frozen
                and not self.insufficient_choices and self.request_count < MAX_REQUESTS)

    def record_planner_result(self, status: str, *, submitted: bool = False) -> None:
        if self.mode != "on" or not self.qualified_prefix:
            raise RuntimeError("planner result arrived before ON prefix qualification")
        if status == "INSUFFICIENT_CHOICES":
            self.insufficient_choices = True
            self.requests_frozen = True
            return
        if submitted:
            if not self.may_plan():
                raise RuntimeError("request submitted outside the six-request live budget")
            self.request_count += 1
            if self.request_count == MAX_REQUESTS:
                self.requests_frozen = True

    def trusted_hire(self, observed_mono: float) -> None:
        if self.first_trusted_hire_mono is None:
            self.first_trusted_hire_mono = observed_mono
            self.requests_frozen = True

    def stop_reason(self, now_mono: float, started_mono: float) -> str | None:
        if self.insufficient_choices:
            return "insufficient_choices_after_qualified_prefix"
        if (self.first_trusted_hire_mono is not None
                and now_mono - self.first_trusted_hire_mono >= POST_HIRE_OBSERVATION_SECONDS):
            return "first_trusted_hire_plus_30s_native_observation"
        if now_mono - started_mono >= TRIAL_WALL_CAP_SECONDS:
            return "trial_wall_cap"
        return None


def actor_view_is_fresh(view_observed_mono: float, now_mono: float, max_age: float = 1.5) -> bool:
    return 0.0 <= now_mono - view_observed_mono <= max_age


def follow_evidence(rows: list[dict], recipient_uid: int, recipient_npc_id: str,
                    leader_npc_id: str, job_observed_time: float) -> dict:
    """Require post-hire recipient brain/controller evidence and horizontal motion."""
    leader_mapping = any(
        row.get("event") == "native_npc_baseline" and row.get("npc_uid") == LEADER_UID
        and row.get("npc_id") == leader_npc_id and row.get("mode") == "loaded"
        and row.get("alive") is True and isinstance(row.get("time"), (int, float))
        and row["time"] >= job_observed_time for row in rows
    )
    if not leader_mapping:
        return {"status": "npc_id_mapping_unverified", "samples": 0}
    selected = []
    for row in rows:
        if row.get("event") != "native_npc_baseline" or row.get("npc_uid") != recipient_uid:
            continue
        if not isinstance(row.get("time"), (int, float)) or row["time"] < job_observed_time:
            continue
        if row.get("mode") != "loaded" or row.get("alive") is not True:
            continue
        if row.get("npc_id") != recipient_npc_id:
            continue
        world = row.get("actual_world_state")
        if not isinstance(world, dict):
            continue
        pos = world.get("ecs_position")
        if not isinstance(pos, list) or len(pos) != 3 or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in pos):
            continue
        backtrace = row.get("brain_backtrace")
        frames = [frame.lower() for frame in backtrace if isinstance(frame, str)] if isinstance(backtrace, list) else []
        target = leader_npc_id.lower()
        hired_by_leader = any("hired by" in frame and target in frame for frame in frames)
        following_leader = any("following actor" in frame and target in frame for frame in frames)
        activity = row.get("controller_activity")
        native_goto = isinstance(activity, str) and "goto" in activity.lower()
        if hired_by_leader and following_leader and native_goto:
            selected.append((float(row["time"]), [float(v) for v in pos]))
    selected.sort(key=lambda item: item[0])
    if len(selected) < 2:
        return {"status": "not_observed", "samples": len(selected)}
    first, last = selected[0], selected[-1]
    displacement = math.dist(first[1], last[1])
    horizontal = math.dist(first[1][:2], last[1][:2])
    return {"status": "observed" if horizontal >= 0.5 else "follow_task_without_horizontal_progress",
            "samples": len(selected), "first_game_time": first[0], "last_game_time": last[0],
            "first_ecs_position": first[1], "last_ecs_position": last[1],
            "horizontal_displacement_meters": horizontal,
            "three_dimensional_displacement_meters": displacement,
            "recipient_native_hired_by_and_following_job_receipt_leader": True,
            "recipient_controller_goto_observed": True}


def run_trial(mode: str, binary: Path, assets: Path, userdata: Path,
              run_dir: Path, runtime: dict) -> dict:
    """Run exactly one bounded isolated trial; never retries or replaces data."""
    run_dir.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
        raise RuntimeError("free disk is below the 6 GiB prelaunch floor")
    paths = {name: run_dir / filename for name, filename in {
        "native_events": "native-events.jsonl", "recruit_events": "recruit-events.jsonl",
        "requests": "recruit-requests.jsonl", "controller": "controller.jsonl",
    }.items()}
    for path in paths.values():
        path.touch(exist_ok=False)
    controller = RecruitmentController(mode, "loaded-msg-" + run_dir.name, leader_uid=LEADER_UID,
                                       ttl_seconds=60.0)
    policy = OnTrialPolicy(mode)
    provenance = LoadedMsgChain()
    env = os.environ.copy()
    for key in CLEARED_INHERITED_ENV:
        env.pop(key, None)
    env.update({
        "VELOREN_USERDATA": str(userdata), "VELOREN_ASSETS": str(assets),
        "VELOREN_NATIVE_EVENTS": str(paths["native_events"]),
        "VELOREN_NATIVE_OBSERVE": "1",
        "VELOREN_NATIVE_OBSERVE_UIDS": ",".join(map(str, runtime["observe_npc_uids"])),
        "VELOREN_NATIVE_PERSISTER_NPC_UIDS": ",".join(map(str, runtime["native_persister_npc_uids"])),
        "VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE": str(runtime["native_persister_view_distance_chunks"]),
        "VELOREN_NATIVE_MAX_RECORDS": str(TELEMETRY_RECORD_CAP),
        "VELOREN_NATIVE_MAX_BYTES": str(TELEMETRY_BYTE_CAP),
        "VELOREN_NATIVE_MAX_SECONDS": str(TELEMETRY_SECONDS_CAP),
        "VELOREN_NATIVE_RECRUIT_REQUESTS": str(paths["requests"]),
        "VELOREN_NATIVE_RECRUIT_EVENTS": str(paths["recruit_events"]),
        "VELOREN_NATIVE_RECRUIT_LEADER_UID": str(LEADER_UID),
    })
    recruit_tail, native_tail = JsonlTail(paths["recruit_events"]), JsonlTail(paths["native_events"])
    prefix = LoadedPrefixGate(LEADER_UID)
    latest_view, latest_view_wall, prefix_result = None, None, None
    view_revision, planned_view_revision = 0, 0
    native_rows: list[dict] = []
    controller_count = recruit_count = 0
    stop_reason, server, spawn_error = "supervisor_error", None, None
    started_local, started_mono = local_now(), time.monotonic()
    server_started_local = None
    sigusr1_sent_local = None
    stop_requested_mono = None
    shutdown_grace_elapsed = None
    first_trusted_hire_mono = None

    def log_controller(record: dict) -> None:
        nonlocal controller_count
        append_jsonl_once(paths["controller"], record)
        controller_count += 1

    def feed_controller(row: dict) -> list[dict]:
        # The frozen adapter's older Job matcher intentionally predates message
        # provenance. Keep its proposal logic, but never let that legacy matcher
        # label a hire as attributable in this revision.
        if row.get("event") == "native_recruit_job_observed":
            return []
        output = controller.feed(row)
        if (row.get("event") == "native_recruit_terminal"
                and controller.pending is not None
                and row.get("request_id") == controller.pending.get("request_id")):
            # A terminal closes the request lifecycle even when this stricter
            # revision cannot attribute the Job. Preserve the Job as a native
            # fact, but do not let the old adapter's weaker matcher deadlock
            # subsequent bounded proposals.
            controller.pending = None
            controller.pending_terminal_outcome = None
            controller.pending_started = False
            controller.pending_message_sent = False
            output.append({"event": "unattributed_terminal_released_controller_pending",
                           "request_id": row.get("request_id"),
                           "outcome": row.get("outcome"),
                           "trusted_hire": False})
        return output

    def process_recruit_rows(rows: list[dict]) -> None:
        nonlocal recruit_count, first_trusted_hire_mono
        for row in rows:
            recruit_count += 1
            trusted = provenance.observe(row)
            controller_rows = ([] if mode == "on" and row.get("event") == "native_recruit_actor_view"
                               else feed_controller(row))
            for item in controller_rows:
                log_controller(item)
            if trusted is not None and first_trusted_hire_mono is None:
                first_trusted_hire_mono = time.monotonic()
                policy.trusted_hire(first_trusted_hire_mono)
                log_controller({"event": "first_trusted_hire_locked_submissions",
                                "request_id": trusted["request_id"], "target_uid": trusted["target_uid"],
                                "observed_time": trusted["time"]})

    out_path, err_path = run_dir / "server.stdout.log", run_dir / "server.stderr.log"
    with out_path.open("xb") as server_out, err_path.open("xb") as server_err:
        try:
            try:
                server = subprocess.Popen([str(binary), "--non-interactive"], env=env,
                                          stdout=server_out, stderr=server_err)
            except OSError as exc:
                spawn_error, stop_reason = f"{type(exc).__name__}: {exc}", "spawn_failed"
            if server is not None:
                server_started_local = local_now()
                stop_reason = "wall_cap"
            while server is not None and server.poll() is None:
                now = time.monotonic()
                if now - started_mono >= TRIAL_WALL_CAP_SECONDS:
                    stop_reason = "trial_wall_cap"
                    break
                if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
                    stop_reason = "disk_floor"
                    break
                fresh_native = native_tail.read_rows()
                native_rows.extend(fresh_native)
                observed_wall = time.monotonic()
                for row in fresh_native:
                    prefix.observe(row, observed_wall)
                fresh_recruit = recruit_tail.read_rows()
                for row in fresh_recruit:
                    recruit_count += 1
                    is_view = row.get("event") == "native_recruit_actor_view"
                    if is_view:
                        latest_view, latest_view_wall = row, observed_wall
                        view_revision += 1
                    trusted = provenance.observe(row)
                    # ON views are cached until the Loaded prefix is complete.
                    # After first trusted hire they are never fed to the planner.
                    event_outputs = ([] if is_view and mode == "on" else feed_controller(row))
                    for item in event_outputs:
                        if item.get("event") == "native_request_proposed":
                            proposed = item["request"]
                            if policy.may_plan():
                                provenance.register_request(proposed)
                                append_jsonl_once(paths["requests"], proposed)
                                policy.record_planner_result("SOLVED_NEXT_SUBTASK", submitted=True)
                        elif item.get("event") == "planner_proposal" and item.get("status") == "INSUFFICIENT_CHOICES":
                            if policy.qualified_prefix:
                                policy.record_planner_result("INSUFFICIENT_CHOICES")
                        log_controller(item)
                    if trusted is not None and first_trusted_hire_mono is None:
                        first_trusted_hire_mono = time.monotonic()
                        policy.trusted_hire(first_trusted_hire_mono)
                        log_controller({"event": "first_trusted_hire_locked_submissions",
                                        "request_id": trusted["request_id"],
                                        "target_uid": trusted["target_uid"], "observed_time": trusted["time"]})
                if (mode == "on" and latest_view is not None and latest_view_wall is not None
                        and planned_view_revision != view_revision):
                    view_is_fresh = actor_view_is_fresh(latest_view_wall, observed_wall)
                    prefix_result = prefix.check(latest_view, observed_wall) if view_is_fresh else None
                    if (prefix_result is not None and not policy.qualified_prefix):
                        policy.qualify_prefix()
                        log_controller({"event": "loaded_native_prefix_satisfied",
                                        "observed_local": local_now(), **prefix_result})
                    if (prefix_result is not None and policy.may_plan()
                            and first_trusted_hire_mono is None and controller.pending is None):
                        # The first planning call is now permitted. INSUFFICIENT_CHOICES
                        # is a terminal run decision, not an invitation to wait/retry.
                        proposed_rows = controller.feed(latest_view)
                        planned_view_revision = view_revision
                        for item in proposed_rows:
                            log_controller(item)
                            if item.get("event") == "planner_proposal" and item.get("status") == "INSUFFICIENT_CHOICES":
                                policy.record_planner_result("INSUFFICIENT_CHOICES")
                            elif item.get("event") == "native_request_proposed":
                                request = item["request"]
                                if policy.may_plan():
                                    provenance.register_request(request)
                                    append_jsonl_once(paths["requests"], request)
                                    policy.record_planner_result("SOLVED_NEXT_SUBTASK", submitted=True)
                total_records = recruit_count + len(native_rows) + controller_count + policy.request_count
                total_bytes = sum(path.stat().st_size for path in paths.values())
                if total_records >= TELEMETRY_RECORD_CAP or total_bytes >= TELEMETRY_BYTE_CAP:
                    stop_reason = "telemetry_record_or_byte_cap"
                    break
                if now - started_mono >= TELEMETRY_SECONDS_CAP:
                    stop_reason = "telemetry_time_cap"
                    break
                policy_stop = policy.stop_reason(now, started_mono)
                if policy_stop is not None:
                    stop_reason = policy_stop
                    break
                if (first_trusted_hire_mono is not None and provenance.trusted_hires
                        and native_rows):
                    hire = provenance.trusted_hires[0]
                    follow = follow_evidence(native_rows, int(hire["target_uid"]),
                                             hire["recipient_npc_id"], hire["leader_npc_id"],
                                             float(hire["time"]))
                    if follow["status"] == "observed":
                        stop_reason = "recipient_native_follow_evidence_observed"
                        break
                if server.poll() is not None:
                    stop_reason = "server_exited"
                    break
                time.sleep(0.1)
            if server is not None and server.poll() is not None and stop_reason == "wall_cap":
                stop_reason = "server_exited"
        finally:
            stop_requested_mono = time.monotonic()
            if server is not None and server.poll() is None:
                sigusr1_sent_local = local_now()
                server.send_signal(signal.SIGUSR1)
                try:
                    server.wait(timeout=SERVER_GRACE_SECONDS + 15)
                except subprocess.TimeoutExpired:
                    server.terminate()
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()
                shutdown_grace_elapsed = time.monotonic() - stop_requested_mono
            process_recruit_rows(recruit_tail.read_rows())
            native_rows.extend(native_tail.read_rows())

    follow = None
    if provenance.trusted_hires:
        hire = provenance.trusted_hires[0]
        follow = follow_evidence(native_rows, int(hire["target_uid"]), hire["recipient_npc_id"],
                                 hire["leader_npc_id"], float(hire["time"]))
    manifest = {
        "mode": mode, "run_started_local": started_local,
        "server_started_local": server_started_local, "sigusr1_sent_local": sigusr1_sent_local,
        "run_finished_local": local_now(),
        "elapsed_seconds": time.monotonic() - started_mono,
        "stop_requested_elapsed_seconds": (stop_requested_mono - started_mono
                                            if stop_requested_mono is not None else None),
        "shutdown_grace_elapsed_seconds": shutdown_grace_elapsed,
        "server_pid": server.pid if server else None,
        "server_exit_code": server.returncode if server else None,
        "spawn_error": spawn_error, "stop_reason": stop_reason,
        "request_rows_written": policy.request_count, "request_cap": MAX_REQUESTS if mode == "on" else 0,
        "insufficient_choices_terminal": policy.insufficient_choices,
        "first_trusted_hire": provenance.trusted_hires[0] if provenance.trusted_hires else None,
        "trusted_hire_count": len(provenance.trusted_hires),
        "follow_evidence": follow, "provenance_violations": provenance.violations,
        "loaded_prefix": prefix_result,
        "telemetry_record_cap": TELEMETRY_RECORD_CAP, "telemetry_byte_cap": TELEMETRY_BYTE_CAP,
        "telemetry_seconds_cap": TELEMETRY_SECONDS_CAP,
        "disk_free_bytes_at_end": shutil.disk_usage(run_dir).free,
        "controller_records_written": controller_count, "recruitment_events_read": recruit_count,
        "native_events_read": len(native_rows),
        "input_sha256": {name: sha256_file(path) for name, path in paths.items()},
        "unclosed_partial_jsonl_bytes": {
            "native_events": len(native_tail.pending), "recruit_events": len(recruit_tail.pending)},
        "cleared_inherited_environment_variables": list(CLEARED_INHERITED_ENV),
    }
    (run_dir / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--pair-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    source, runtime, userdata_off, userdata_on = validate_loaded_msg_freeze(freeze)
    pair_dir = args.pair_dir.expanduser().resolve()
    if pair_dir.exists():
        raise FileExistsError("pair directory already exists; outputs are never overwritten")
    pair_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.freeze, pair_dir / "input-freeze.json")
    (pair_dir / "input-freeze.sha256").write_text(sha256_file(args.freeze) + "\n", encoding="ascii")
    binary = Path(source["binary_path"]).expanduser().resolve()
    assets = Path(source["assets_path"]).expanduser().resolve()
    trials = []
    try:
        for mode, userdata in (("off", userdata_off), ("on", userdata_on)):
            trial = run_trial(mode, binary, assets, userdata, pair_dir / mode, runtime)
            trials.append(trial)
            (pair_dir / "pair-manifest.json").write_text(json.dumps({"trials": trials}, indent=2) + "\n",
                                                          encoding="utf-8")
            if trial["server_exit_code"] != 0:
                break
    finally:
        (pair_dir / "pair-manifest.json").write_text(json.dumps({
            "trial_launch_limit": 2, "trials_started": len(trials), "trials": trials,
            "native_rng_controlled": False,
        }, indent=2) + "\n", encoding="utf-8")
    return 0 if len(trials) == 2 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"loaded-msg pair refused or stopped: {exc}", file=sys.stderr)
        raise SystemExit(2)
