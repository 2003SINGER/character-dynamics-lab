"""Bounded headless Veloren runner for Character Dynamics Online v0.

The controller remains a pure in-process decision function. This module only
tails the frozen native JSONL interfaces, appends validated RecruitMember
requests, and preserves the raw evidence for three sequential trials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from datetime import datetime
from typing import Any

from tools.character_dynamics_online_v0 import new_session, step
from tools.veloren_native_decision_v1.loaded_msg_pair import (
    DISK_FLOOR_BYTES, TELEMETRY_BYTE_CAP, TELEMETRY_RECORD_CAP,
    LoadedMsgChain, _validate_userdata_manifest, assets_tree_sha256,
    sha256_file,
)
from tools.veloren_native_decision_v1.run_pair import LoadedPrefixGate

LEADER_UID = 476
TRIALS = ("NATIVE_ONLY", "ACTOR_DIRECTOR_OFF", "ACTOR_DIRECTOR_ON")
MAX_WALL_SECONDS = 360.0
TRIAL_WALL_CAPS = {"NATIVE_ONLY": 60.0, "ACTOR_DIRECTOR_OFF": 120.0,
                   "ACTOR_DIRECTOR_ON": 120.0}
MAX_REQUESTS = 3
REQUEST_TTL_SECONDS = 60.0
POST_COMPLETION_SECONDS = 15.0
SERVER_GRACE_SECONDS = 1.0
CLEARED_ENV = (
    "VELOREN_NATIVE_REQUESTS", "VELOREN_RTSIM", "VELOREN_TERRAIN",
    "RTSIM_NOLOAD", "RTSIM_IGNORE_VERSION",
)
RUN_ROOT = Path("_local_data/veloren_online_integration_v0")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def append_jsonl_once(path: Path, row: dict[str, Any]) -> int:
    payload = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        written = os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    if written != len(payload):
        raise OSError(f"partial append to {path}: {written}/{len(payload)}; not retried")
    return written


class JsonlTail:
    """Incremental JSONL reader that retains an incomplete final line."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.pending = b""

    def read_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        size = self.path.stat().st_size
        if size < self.offset:
            raise RuntimeError(f"native telemetry was truncated during the run: {self.path}")
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            chunk = stream.read()
        self.offset += len(chunk)
        self.pending += chunk
        if b"\n" not in self.pending:
            return []
        complete, self.pending = self.pending.rsplit(b"\n", 1)
        rows: list[dict[str, Any]] = []
        for line in complete.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("native JSONL row must be an object")
            rows.append(row)
        return rows


def _read_manifest(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"manifest must be an object: {path}")
    return obj


def validate_freeze(freeze: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    """Validate pinned inputs and exactly three independent prebuilt saves."""
    if freeze.get("schema_version") != 1:
        raise ValueError("freeze schema_version must be 1")
    source, world, runtime, trials = (freeze.get(k) for k in ("source", "world", "runtime", "trials"))
    if not all(isinstance(x, dict) for x in (source, world, runtime, trials)):
        raise ValueError("freeze source/world/runtime/trials must be objects")
    if source.get("commit") != "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248":
        raise ValueError("source must pin Veloren v0.18.0 commit 1d12f35e")
    for path_key, hash_key in (("source_patch_path", "source_patch_sha256"),
                               ("cargo_lock_path", "cargo_lock_sha256"),
                               ("binary_path", "binary_sha256")):
        path = Path(source.get(path_key, "")).expanduser().resolve()
        if not path.is_file() or sha256_file(path) != source.get(hash_key):
            raise ValueError(f"frozen input mismatch: {path_key}")
    assets = Path(source.get("assets_path", "")).expanduser().resolve()
    assets_manifest = Path(source.get("assets_manifest_path", "")).expanduser().resolve()
    if (not assets.is_dir() or not assets_manifest.is_file()
            or sha256_file(assets_manifest) != source.get("assets_manifest_sha256")
            or assets_tree_sha256(assets, assets_manifest) != source.get("assets_tree_sha256")):
        raise ValueError("official asset tree or its complete manifest does not match the freeze")
    if (world.get("world_seed") != 130626853
            or any(not isinstance(world.get(k), str) or len(world[k]) != 64
                   for k in ("source_world_sha256", "settings_contract_sha256"))):
        raise ValueError("world seed or source hashes are not the approved frozen values")
    if (runtime.get("leader_uid") != LEADER_UID or runtime.get("loopback_only") is not True
            or runtime.get("query_address") is not None):
        raise ValueError("leader and loopback-only server boundary must match the freeze")
    if (runtime.get("max_trial_wall_seconds") != MAX_WALL_SECONDS
            or runtime.get("disk_free_floor_bytes") != DISK_FLOOR_BYTES
            or runtime.get("max_requests") != MAX_REQUESTS
            or runtime.get("request_ttl_seconds") != REQUEST_TTL_SECONDS):
        raise ValueError("runtime limits must be <=360s, 3 requests, 60s TTL, and 6GiB disk floor")
    if (runtime.get("telemetry_record_cap") != TELEMETRY_RECORD_CAP
            or runtime.get("telemetry_byte_cap") != TELEMETRY_BYTE_CAP):
        raise ValueError("telemetry caps differ from the reviewed native interface")
    if runtime.get("observe_npc_uids") != runtime.get("native_persister_npc_uids"):
        raise ValueError("all three runs must use identical observer and persister UID lists")
    if LEADER_UID not in runtime["observe_npc_uids"]:
        raise ValueError("observer list must include the leader")
    if set(trials) != set(TRIALS):
        raise ValueError(f"freeze trials must be exactly {TRIALS}")

    resolved: dict[str, tuple[Path, Path, str]] = {}
    roots: set[Path] = set()
    world_files: dict[str, tuple[int, str]] | None = None
    for name in TRIALS:
        trial = trials[name]
        if not isinstance(trial, dict):
            raise ValueError(f"trials.{name} must be an object")
        userdata = Path(trial.get("userdata_path", "")).expanduser().resolve()
        manifest_path = Path(trial.get("userdata_manifest_path", "")).expanduser().resolve()
        if (not userdata.is_dir() or not (userdata / "server").is_dir()
                or not manifest_path.is_relative_to(userdata) or not manifest_path.is_file()):
            raise ValueError(f"trials.{name} must point at an existing isolated server userdata and manifest")
        if userdata in roots:
            raise ValueError("each trial must have its own userdata root")
        roots.add(userdata)
        manifest = _read_manifest(manifest_path)
        if sha256_file(manifest_path) != trial.get("userdata_manifest_sha256"):
            raise ValueError(f"trials.{name} manifest hash mismatch")
        _validate_userdata_manifest(userdata, manifest_path)
        if (trial.get("source_world_sha256") != world["source_world_sha256"]
                or trial.get("settings_contract_sha256") != world["settings_contract_sha256"]):
            raise ValueError(f"trials.{name} does not match the frozen source world/settings")
        current_world = {row["path"]: (row["size_bytes"], row["sha256"])
                         for row in manifest["files"] if row.get("role") == "world"}
        if len(current_world) != 6:
            raise ValueError(f"trials.{name} must pin exactly six source world files")
        if world_files is None:
            world_files = current_world
        elif current_world != world_files:
            raise ValueError("three userdata copies do not contain identical frozen world payloads")
        resolved[name] = (userdata, manifest_path, trial["userdata_manifest_sha256"])
    source = {**source, "source_world_sha256": world["source_world_sha256"],
              "settings_contract_sha256": world["settings_contract_sha256"]}
    return source, runtime, resolved


def actor_goal_targets(view: dict[str, Any], excluded: int) -> list[int]:
    rows = view.get("eligible_recruits", [])
    valid = [r for r in rows if isinstance(r, dict) and type(r.get("npc_uid")) is int
             and r["npc_uid"] != excluded]
    valid.sort(key=lambda r: (float(r.get("distance_3d", float("inf"))), r["npc_uid"]))
    return [r["npc_uid"] for r in valid[:2]]


def native_job_witness(row: dict[str, Any]) -> dict[str, Any] | None:
    """Only explicit native Job receipts become global historical evidence."""
    if row.get("event") not in ("native_recruit_job_observed",
                                 "native_recruit_unattributed_hire_observed"):
        return None
    target = row.get("target_uid")
    hired_by = row.get("hired_by_uid")
    game_time = row.get("time")
    request_id = row.get("request_id")
    if (type(target) is not int or type(hired_by) is not int
            or not isinstance(game_time, (int, float)) or isinstance(game_time, bool)
            or (row.get("event") == "native_recruit_job_observed"
                and (not isinstance(request_id, str) or not request_id))):
        return None
    return dict(row)


def _recruit_payload(request: dict[str, Any], observed_time: float) -> dict[str, Any]:
    if request.get("task") != "RecruitMember" or request.get("leader_uid") != LEADER_UID:
        raise ValueError("controller produced an unsupported native task")
    return {"version": 1, "kind": "RecruitMember", "request_id": request["request_id"],
            "source": request["source"], "leader_uid": LEADER_UID,
            "target_uid": request["target_uid"], "observed_time": float(observed_time),
            "ttl_seconds": REQUEST_TTL_SECONDS}


def normalize_rejected_feedback(row: dict[str, Any], provenance: LoadedMsgChain) -> dict[str, Any] | None:
    """Enrich the native minimal reject schema only from this run's registry.

    An unknown request id stays raw evidence only; it is not allowed to clear a
    controller in-flight request or be represented as a terminal.
    """
    request_id = row.get("request_id")
    registered = provenance.requests.get(request_id) if isinstance(request_id, str) else None
    if row.get("event") != "native_recruit_request_rejected" or registered is None:
        return None
    request = registered["request"]
    return {**row, "leader_uid": row.get("leader_uid", registered["leader_uid"]),
            "target_uid": row.get("target_uid", request["target_uid"]),
            "runner_context_enriched_from_registered_request": True}


def classify_outcome(name: str, *, started: bool, return_code: int | None,
                     native_rows: int, requests: int, trusted_targets: set[int],
                     stop_reason: str, violations: list[dict[str, Any]]) -> str:
    if name == "NATIVE_ONLY":
        baseline_observed = (started and return_code == 0 and native_rows > 0
                             and requests == 0 and not violations)
        return "BASELINE_OBSERVED" if baseline_observed else "PARTIAL"
    complete = (len(trusted_targets) >= 2
                and stop_reason == "two_native_jobs_plus_continuation"
                and not violations)
    return "COMPLETE_TWO_ATTRIBUTED_NATIVE_JOBS" if complete else "PARTIAL"


def parse_author_input(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Accept one structured local-author row; preserve malformed rows as data."""
    if row.get("source") not in ("LOCAL_AUTHOR", "RUNNER_DEMO"):
        return None, "source_not_allowlisted"
    command = row.get("command")
    required = {"op", "goal_id", "version", "target_uid", "hired_by_uid", "deadline"}
    if not isinstance(command, dict) or set(command) != required:
        return None, "command_fields_mismatch"
    if command.get("op") not in ("append", "edit"):
        return None, "unsupported_operation"
    if (not isinstance(command.get("goal_id"), str) or not command["goal_id"].strip()
            or type(command.get("version")) is not int or command["version"] < 1
            or type(command.get("target_uid")) is not int or command["target_uid"] < 0
            or command.get("hired_by_uid") != LEADER_UID
            or not isinstance(command.get("deadline"), (int, float))
            or isinstance(command.get("deadline"), bool)
            or not math.isfinite(command["deadline"]) or command["deadline"] < 0):
        return None, "invalid_goal_values"
    return dict(command), None


def _environment(source: dict[str, Any], runtime: dict[str, Any], userdata: Path,
                 run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in CLEARED_ENV:
        env.pop(key, None)
    env["VELOREN_USERDATA"] = str(userdata)
    env["VELOREN_ASSETS"] = str(Path(source["assets_path"]).expanduser().resolve())
    env["VELOREN_NATIVE_EVENTS"] = str(run_dir / "native-events.jsonl")
    env["VELOREN_NATIVE_OBSERVE"] = "1"
    env["VELOREN_NATIVE_OBSERVE_UIDS"] = ",".join(map(str, runtime["observe_npc_uids"]))
    env["VELOREN_NATIVE_PERSISTER_NPC_UIDS"] = ",".join(map(str, runtime["native_persister_npc_uids"]))
    env["VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE"] = str(runtime["native_persister_view_distance_chunks"])
    env["VELOREN_NATIVE_MAX_RECORDS"] = str(TELEMETRY_RECORD_CAP)
    env["VELOREN_NATIVE_MAX_BYTES"] = str(TELEMETRY_BYTE_CAP)
    env["VELOREN_NATIVE_MAX_SECONDS"] = "1800"
    env["VELOREN_NATIVE_RECRUIT_REQUESTS"] = str(run_dir / "recruit-requests.jsonl")
    env["VELOREN_NATIVE_RECRUIT_EVENTS"] = str(run_dir / "recruit-events.jsonl")
    env["VELOREN_NATIVE_RECRUIT_LEADER_UID"] = str(LEADER_UID)
    return env


def run_trial(name: str, source: dict[str, Any], runtime: dict[str, Any],
              userdata_entry: tuple[Path, Path, str], run_dir: Path,
              wall_cap: float) -> dict[str, Any]:
    if not 0 < wall_cap <= TRIAL_WALL_CAPS[name]:
        raise ValueError(f"wall cap for {name} must be in (0, {TRIAL_WALL_CAPS[name]}]")
    userdata, userdata_manifest, userdata_manifest_hash = userdata_entry
    run_dir.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
        raise RuntimeError("free disk below the 6 GiB prelaunch floor")
    filenames = ("native-events.jsonl", "recruit-events.jsonl", "recruit-requests.jsonl",
                 "author-input.jsonl",
                 "decisions.jsonl", "sessions.jsonl", "author-versions.jsonl", "status.jsonl")
    paths = {filename: run_dir / filename for filename in filenames}
    for path in paths.values():
        path.touch(exist_ok=False)
    env = _environment(source, runtime, userdata, run_dir)
    native_tail, recruit_tail = JsonlTail(paths["native-events.jsonl"]), JsonlTail(paths["recruit-events.jsonl"])
    author_tail = JsonlTail(paths["author-input.jsonl"])
    prefix_gate = LoadedPrefixGate(LEADER_UID)
    prefix_qualified = name == "NATIVE_ONLY"
    prefix_pending_logged = False
    latest_view_mono: float | None = None
    mode_actor = name != "NATIVE_ONLY"
    director = name == "ACTOR_DIRECTOR_ON"
    session = new_session(LEADER_UID, hire_quota=2, director_enabled=director) if mode_actor else None
    provenance = LoadedMsgChain(LEADER_UID)
    latest_view: dict[str, Any] | None = None
    last_view_fingerprint: str | None = None
    pending_feedback: list[dict[str, Any]] = []
    pending_evidence: list[dict[str, Any]] = []
    all_world_job_facts: list[dict[str, Any]] = []
    trusted_job_receipts: list[dict[str, Any]] = []
    author_targets: list[int] = []
    first_actor_request_time: float | None = None
    issued_author_version = 0
    pending_author_commands: list[dict[str, Any]] = []
    pending_author_metadata: list[dict[str, Any]] = []
    author_pool_blocked = False
    request_count = 0
    native_rows_count = recruit_rows_count = controller_rows_count = 0
    start_mono = time.monotonic()
    server: subprocess.Popen | None = None
    stop_reason = "supervisor_error"
    stop_requested_at = None
    sigusr1_sent_at = None
    signal_exit_code = None
    last_job_mono: float | None = None
    trusted_job_targets: set[int] = set()
    latest_native_game_time: float | None = None
    started_local: str | None = None
    post_job_deadline: float | None = None
    out_path, err_path = run_dir / "server.stdout.log", run_dir / "server.stderr.log"

    def log(path_name: str, row: dict[str, Any]) -> None:
        append_jsonl_once(paths[path_name], row)

    def queue_due_author_commands(game_time: float) -> None:
        nonlocal issued_author_version, author_pool_blocked
        if not director or first_actor_request_time is None or issued_author_version >= 2:
            return
        if len(author_targets) < 2:
            if not author_pool_blocked:
                log("author-versions.jsonl", {"event": "author_target_pool_insufficient",
                                               "first_actor_target_uid": session.get("inflight_request", {}).get("target_uid") if session else None,
                                               "candidate_author_targets": author_targets,
                                               "required_distinct_targets": 2})
                author_pool_blocked = True
            return
        deadline = first_actor_request_time + 90.0
        if issued_author_version == 0 and game_time >= first_actor_request_time + 0.4:
            command = {"op": "append", "goal_id": "online-author-goal", "version": 1,
                       "target_uid": author_targets[0], "hired_by_uid": LEADER_UID,
                       "deadline": deadline}
            append_jsonl_once(paths["author-input.jsonl"],
                              {"source": "RUNNER_DEMO", "issued_at_game_time": game_time,
                               "command": command})
            issued_author_version = 1
            log("author-versions.jsonl", {"event": "author_command_queued",
                                           "scheduled_threshold_game_time": first_actor_request_time + 0.4,
                                           "observed_game_time": game_time, "command": command,
                                           "input_path": str(paths["author-input.jsonl"])})
        if issued_author_version == 1 and game_time >= first_actor_request_time + 0.8:
            command = {"op": "edit", "goal_id": "online-author-goal", "version": 2,
                       "target_uid": author_targets[1], "hired_by_uid": LEADER_UID,
                       "deadline": deadline}
            append_jsonl_once(paths["author-input.jsonl"],
                              {"source": "RUNNER_DEMO", "issued_at_game_time": game_time,
                               "command": command})
            issued_author_version = 2
            log("author-versions.jsonl", {"event": "author_command_queued",
                                           "scheduled_threshold_game_time": first_actor_request_time + 0.8,
                                           "observed_game_time": game_time, "command": command,
                                           "input_path": str(paths["author-input.jsonl"])})

    def control_on_view(view: dict[str, Any], decision_time: float) -> None:
        nonlocal session, last_view_fingerprint, first_actor_request_time, author_targets
        nonlocal prefix_qualified
        nonlocal request_count, controller_rows_count
        fingerprint = hashlib.sha256(json.dumps(view, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if fingerprint == last_view_fingerprint:
            return
        last_view_fingerprint = fingerprint
        now = max(float(view["time"]), decision_time)
        queue_due_author_commands(now)
        commands = pending_author_commands[:]
        command_metadata = pending_author_metadata[:]
        pending_author_commands.clear()
        pending_author_metadata.clear()
        result = step(session, view, game_time=now,
                      native_evidence={"events": pending_evidence,
                                       "source_id": f"native-recruit-events:{run_dir.name}"},
                      author_commands=commands, feedback=pending_feedback)
        pending_evidence.clear()
        pending_feedback.clear()
        session = result["session"]
        decision = result["decision"]
        log("decisions.jsonl", {"event": "controller_decision", "run": name,
                                "observed_local": local_now(), "decision": decision})
        log("sessions.jsonl", {"event": "session_snapshot", "game_time": now, "session": session})
        controller_rows_count += 2
        for command, metadata in zip(commands, command_metadata):
            log("author-versions.jsonl", {"event": "author_version_submitted",
                                           "scheduled_threshold_game_time": first_actor_request_time + (0.4 if command["op"] == "append" else 0.8),
                                           "applied_on_actor_view_time": float(view["time"]),
                                           "controller_game_time": now, "command": command,
                                           "input_source": metadata["source"],
                                           "input_issued_at_game_time": metadata.get("issued_at_game_time"),
                                           "inflight_request": session.get("inflight_request"),
                                           "same_controller_batch": len(commands) > 1})
            controller_rows_count += 1
        request = decision.get("request")
        if request is not None:
            if request_count >= MAX_REQUESTS:
                log("status.jsonl", {"event": "request_budget_blocked", "request": request})
                return
            if first_actor_request_time is None and request.get("source") == "ACTOR":
                first_actor_request_time = float(view["time"])
                author_targets = actor_goal_targets(view, int(request["target_uid"]))
                log("author-versions.jsonl", {"event": "author_target_pool_frozen_from_live_view",
                                               "first_actor_target_uid": request["target_uid"],
                                               "candidate_author_targets": author_targets,
                                               "view_time": now})
                controller_rows_count += 1
            payload = _recruit_payload(request, float(view["time"]))
            provenance.register_request(payload)
            append_jsonl_once(paths["recruit-requests.jsonl"], payload)
            log("decisions.jsonl", {"event": "request_submitted", "run": name,
                                    "observed_local": local_now(), "decision_request": request,
                                    "native_request": payload})
            request_count += 1
            controller_rows_count += 1
            pending_feedback.append({"request_id": request["request_id"], "status": "SENT",
                                     "source": "runner:append-only-native-request"})

    try:
        with out_path.open("xb") as out, err_path.open("xb") as err:
            started_local = local_now()
            start_mono = time.monotonic()
            server = subprocess.Popen([str(Path(source["binary_path"]).expanduser().resolve()),
                                       "--non-interactive"], env=env, stdout=out, stderr=err)
            stop_reason = "wall_cap"
            while server.poll() is None:
                now_mono = time.monotonic()
                if now_mono - start_mono >= wall_cap:
                    stop_reason = "trial_wall_cap"
                    break
                if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
                    stop_reason = "disk_floor"
                    break
                for row in native_tail.read_rows():
                    native_rows_count += 1
                    prefix_gate.observe(row, now_mono)
                    native_game_time = row.get("time")
                    if isinstance(native_game_time, (int, float)) and not isinstance(native_game_time, bool):
                        latest_native_game_time = max(float(native_game_time), latest_native_game_time or 0.0)
                        queue_due_author_commands(float(native_game_time))
                fresh_views: list[dict[str, Any]] = []
                for row in recruit_tail.read_rows():
                    recruit_rows_count += 1
                    trusted = provenance.observe(row)
                    witness = native_job_witness(row)
                    if witness:
                        all_world_job_facts.append(witness)
                        pending_evidence.append(witness)
                        last_job_mono = now_mono
                        if row.get("event") == "native_recruit_unattributed_hire_observed":
                            pass
                        elif trusted is not None:
                            trusted_job_receipts.append(witness)
                            trusted_job_targets.add(witness["target_uid"])
                        if len(trusted_job_targets) >= 2 and post_job_deadline is None:
                            post_job_deadline = now_mono + POST_COMPLETION_SECONDS
                    request_id = row.get("request_id")
                    if isinstance(request_id, str):
                        if row.get("event") == "native_recruit_request_rejected":
                            # The pinned server rejection schema may carry only
                            # request_id/time/reason. The exact in-run request
                            # registry supplies identity context; the raw row
                            # remains unchanged in recruit-events.jsonl.
                            enriched = normalize_rejected_feedback(row, provenance)
                            if enriched is not None:
                                pending_feedback.append(enriched)
                        elif row.get("event") == "native_recruit_terminal":
                            pending_feedback.append(row)
                        elif row.get("event") in ("native_recruit_message_sent", "native_recruit_request_accepted"):
                            pending_feedback.append({"request_id": request_id, "status": "SENT",
                                                     "source": row.get("event"), "native_event": row})
                    if row.get("event") == "native_recruit_actor_view":
                        latest_view = row
                        latest_view_mono = now_mono
                        queue_due_author_commands(float(row["time"]))
                        fresh_views.append(row)
                if director:
                    for author_row in author_tail.read_rows():
                        command, error = parse_author_input(author_row)
                        if error:
                            log("author-versions.jsonl", {"event": "author_input_rejected",
                                                           "reason": error, "raw": author_row})
                            continue
                        pending_author_commands.append(command)
                        pending_author_metadata.append({"source": author_row["source"],
                                                        "issued_at_game_time": author_row.get("issued_at_game_time")})
                        log("author-versions.jsonl", {"event": "author_input_accepted",
                                                       "source": author_row["source"],
                                                       "command": command,
                                                       "issued_at_game_time": author_row.get("issued_at_game_time")})
                if latest_view and mode_actor:
                    for view in fresh_views[-1:]:
                        if not prefix_qualified:
                            prefix_qualified = (prefix_gate.check(view, now_mono) is not None)
                            if prefix_qualified:
                                log("status.jsonl", {"event": "loaded_prefix_satisfied",
                                                      "game_time": view["time"],
                                                      "qualification": "3 distinct game times, >=2s wall span, leader+2 loaded candidates with finite positions"})
                            elif not prefix_pending_logged:
                                log("status.jsonl", {"event": "loaded_prefix_pending",
                                                      "game_time": view["time"],
                                                      "qualification": "waiting for native loaded-position samples"})
                                prefix_pending_logged = True
                        if (prefix_qualified and latest_view_mono is not None
                                and now_mono - latest_view_mono <= 1.5):
                            decision_time = max(float(view["time"]), latest_native_game_time or 0.0)
                            inflight = session.get("inflight_request")
                            terminal_for_inflight = bool(inflight and any(
                                row.get("request_id") == inflight.get("request_id")
                                and row.get("event") in ("native_recruit_terminal", "native_recruit_request_rejected")
                                for row in pending_feedback))
                            if request_count >= MAX_REQUESTS and terminal_for_inflight:
                                stop_reason = "request_budget_exhausted_after_native_terminal"
                                break
                            if request_count >= MAX_REQUESTS and inflight is None:
                                stop_reason = "request_budget_exhausted"
                                break
                            control_on_view(view, decision_time)
                if stop_reason in ("request_budget_exhausted", "request_budget_exhausted_after_native_terminal"):
                    break
                total_bytes = sum(p.stat().st_size for p in paths.values())
                total_records = native_rows_count + recruit_rows_count + controller_rows_count
                if total_records >= TELEMETRY_RECORD_CAP or total_bytes >= TELEMETRY_BYTE_CAP:
                    stop_reason = "telemetry_cap"
                    break
                if post_job_deadline is not None and now_mono >= post_job_deadline:
                    stop_reason = "two_native_jobs_plus_continuation"
                    break
                time.sleep(0.1)
            if server.poll() is not None and stop_reason == "wall_cap":
                stop_reason = "server_exited"
    except Exception as exc:
        stop_reason = f"runner_error:{type(exc).__name__}:{exc}"
    finally:
        stop_requested_at = local_now()
        if server is not None and server.poll() is None:
            sigusr1_sent_at = local_now()
            server.send_signal(signal.SIGUSR1)
            try:
                server.wait(timeout=SERVER_GRACE_SECONDS + 15.0)
            except subprocess.TimeoutExpired:
                server.terminate()
                try:
                    server.wait(timeout=SERVER_GRACE_SECONDS + 15.0)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
            signal_exit_code = server.returncode
        # The server owns both raw event files. Drain unread rows only for
        # accounting/provenance; never append them back into their source file.
        native_rows_count += len(native_tail.read_rows())
        pending_native_events = []
        for row in recruit_tail.read_rows():
            recruit_rows_count += 1
            trusted = provenance.observe(row)
            if row.get("event") in ("native_recruit_terminal", "native_recruit_request_rejected"):
                pending_native_events.append(row.get("event"))
            witness = native_job_witness(row)
            if witness and (row.get("event") == "native_recruit_unattributed_hire_observed" or trusted is not None):
                all_world_job_facts.append(witness)
            if witness and row.get("event") == "native_recruit_job_observed" and trusted is not None:
                trusted_job_receipts.append(witness)
                trusted_job_targets.add(witness["target_uid"])
        if server is not None and signal_exit_code is None:
            signal_exit_code = server.returncode
        outcome = classify_outcome(
            name, started=started_local is not None, return_code=signal_exit_code,
            native_rows=native_rows_count, requests=request_count,
            trusted_targets=trusted_job_targets, stop_reason=stop_reason,
            violations=provenance.violations)
        manifest = {"schema_version": 1, "run": name, "started_local": started_local,
                    "stop_requested_local": stop_requested_at, "sigusr1_sent_local": sigusr1_sent_at,
                    "server_return_code": signal_exit_code, "stop_reason": stop_reason,
                    "outcome": outcome, "wall_seconds": time.monotonic() - start_mono,
                    "disk_free_bytes_at_stop": shutil.disk_usage(run_dir).free,
                    "request_rows": request_count, "native_rows": native_rows_count,
                    "recruit_rows": recruit_rows_count,
                    "trusted_job_target_uids": sorted(trusted_job_targets),
                    "trusted_job_receipts": trusted_job_receipts,
                    "native_world_job_facts": all_world_job_facts,
                    "raw_terminal_events_not_consumed_by_controller": pending_native_events,
                    "controller_inflight_at_shutdown": session.get("inflight_request") if session else None,
                    "loaded_msg_chain_violations": provenance.violations,
                    "source_binary_sha256": sha256_file(Path(source["binary_path"]).expanduser().resolve()),
                    "source_world_sha256": source.get("source_world_sha256"),
                    "settings_contract_sha256": source.get("settings_contract_sha256"),
                    "user_data": str(userdata), "user_data_manifest": str(userdata_manifest),
                    "user_data_manifest_sha256": userdata_manifest_hash}
        (run_dir / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def run(freeze_path: Path, run_id: str, wall_cap: float = MAX_WALL_SECONDS) -> Path:
    freeze = _read_manifest(freeze_path)
    source, runtime, userdata = validate_freeze(freeze)
    run_id = run_id.strip()
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
        raise ValueError("run_id must contain only letters, digits, hyphen, or underscore")
    root = RUN_ROOT / run_id
    root.mkdir(parents=True, exist_ok=False)
    manifests = []
    for name in TRIALS:
        effective_cap = min(TRIAL_WALL_CAPS[name], wall_cap)
        manifest = run_trial(name, source, runtime, userdata[name], root / name.lower(), effective_cap)
        manifests.append(manifest)
    expected_outcomes = {"NATIVE_ONLY": "BASELINE_OBSERVED",
                         "ACTOR_DIRECTOR_OFF": "COMPLETE_TWO_ATTRIBUTED_NATIVE_JOBS",
                         "ACTOR_DIRECTOR_ON": "COMPLETE_TWO_ATTRIBUTED_NATIVE_JOBS"}
    summary = {"schema_version": 1, "run_id": run_id, "freeze_path": str(freeze_path.resolve()),
               "runs": manifests, "native_rng_controlled": False,
               "expected_outcomes": expected_outcomes,
               "outcome": "COMPLETE" if all(x["outcome"] == expected_outcomes[x["run"]]
                                              for x in manifests) else "PARTIAL"}
    (root / "integration-manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--wall-cap", type=float, default=MAX_WALL_SECONDS,
                        help="optional shared ceiling; per-trial defaults are 60/120/120 seconds")
    args = parser.parse_args()
    root = run(args.freeze, args.run_id, args.wall_cap)
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
