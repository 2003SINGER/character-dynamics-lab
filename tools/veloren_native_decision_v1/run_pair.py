#!/usr/bin/env python3
"""Supervise one frozen OFF/ON pair; only runs when explicitly invoked."""

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
import sys
import time
from collections import defaultdict
from datetime import datetime

from tools.veloren_native_decision_v1.adapter import RecruitmentController


DISK_FLOOR_BYTES = 6 * 1024**3
TRIAL_WALL_CAP_SECONDS = 360.0
TELEMETRY_RECORD_CAP = 10_000
TELEMETRY_BYTE_CAP = 16 * 1024**2
TELEMETRY_SECONDS_CAP = 1_800
POST_NATIVE_HANDOFF_SECONDS = 20.0
SERVER_GRACE_SECONDS = 1.0
CLEARED_INHERITED_ENV = (
    "VELOREN_NATIVE_REQUESTS", "VELOREN_RTSIM", "VELOREN_TERRAIN",
    "RTSIM_NOLOAD", "RTSIM_IGNORE_VERSION",
)
RUN_ROOT = Path("_local_data/external_games/veloren_0_18_0/evidence/native_decision_v1/runs")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_jsonl_once(path: Path, row: dict) -> int:
    payload = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        written = os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    if written != len(payload):
        raise OSError(f"single JSONL append was partial: {written}/{len(payload)}; not retried")
    return written


class JsonlTail:
    """Incremental tail retaining incomplete bytes until their newline arrives."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.pending = b""

    def read_rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        size = self.path.stat().st_size
        if size < self.offset:
            self.offset = 0
            self.pending = b""
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            chunk = stream.read()
        self.offset += len(chunk)
        self.pending += chunk
        complete, self.pending = self.pending.rsplit(b"\n", 1) if b"\n" in self.pending else (b"", self.pending)
        rows = []
        for line in complete.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows


class LoadedPrefixGate:
    """Require a short native-only prefix before the first ON proposal."""

    def __init__(self, leader_uid: int = 476):
        self.leader_uid = leader_uid
        self.snapshots: dict[float, dict[int, tuple[dict, float]]] = defaultdict(dict)
        self.latest: dict[int, tuple[dict, float]] = {}

    @staticmethod
    def _valid_loaded_baseline(row: dict) -> bool:
        world = row.get("actual_world_state")
        position = world.get("ecs_position") if isinstance(world, dict) else None
        return (
            row.get("event") == "native_npc_baseline"
            and row.get("mode") == "loaded"
            and row.get("alive") is True
            and isinstance(world, dict)
            and isinstance(position, list) and len(position) == 3
            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) for value in position)
        )

    def observe(self, row: dict, observed_mono: float) -> None:
        uid, game_time = row.get("npc_uid"), row.get("time")
        if (not isinstance(uid, int) or isinstance(uid, bool)
                or not isinstance(game_time, (int, float)) or isinstance(game_time, bool)):
            return
        self.latest[uid] = (row, observed_mono)
        if self._valid_loaded_baseline(row):
            self.snapshots[round(float(game_time), 6)][uid] = (row, observed_mono)

    def check(self, actor_view: dict, now_mono: float) -> dict | None:
        if actor_view.get("npc_uid") != self.leader_uid or actor_view.get("mode") != "loaded":
            return None
        leader_latest = self.latest.get(self.leader_uid)
        if not leader_latest or not self._valid_loaded_baseline(leader_latest[0]):
            return None
        if now_mono - leader_latest[1] > 1.5:
            return None
        candidate_rows = actor_view.get("eligible_recruits")
        if not isinstance(candidate_rows, list):
            return None
        loaded_uids = []
        for candidate in candidate_rows:
            if not isinstance(candidate, dict) or candidate.get("mode") != "loaded":
                continue
            uid = candidate.get("npc_uid")
            latest = self.latest.get(uid)
            if (isinstance(uid, int) and not isinstance(uid, bool) and latest
                    and self._valid_loaded_baseline(latest[0]) and now_mono - latest[1] <= 1.5):
                loaded_uids.append(uid)
        if len(set(loaded_uids)) < 2:
            return None
        selected = sorted(set(loaded_uids))[:2]
        required = {self.leader_uid, *selected}
        ready_snapshots = [
            (game_time, rows)
            for game_time, rows in sorted(self.snapshots.items())
            if required.issubset(rows)
        ]
        if len(ready_snapshots) < 3:
            return None
        ready_snapshots = ready_snapshots[-3:]
        first_time, first_rows = ready_snapshots[0]
        last_time, last_rows = ready_snapshots[-1]
        wall_span = last_rows[self.leader_uid][1] - first_rows[self.leader_uid][1]
        if wall_span < 2.0 or now_mono - last_rows[self.leader_uid][1] > 1.5:
            return None
        return {"leader_uid": self.leader_uid, "loaded_candidate_uids": selected,
                "distinct_game_times": [entry[0] for entry in ready_snapshots],
                "prefix_wall_span_seconds": wall_span,
                "first_game_time": first_time, "last_game_time": last_time,
                "qualification": "alive_loaded_finite_ecs_positions_only; no SPEAK gate"}


def _required(obj: dict, key: str, parent: str) -> dict:
    value = obj.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"freeze.{parent}.{key} must be an object")
    return value


def _validate_userdata_manifest(userdata: Path, manifest_path: Path) -> None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read userdata manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("userdata manifest schema_version must be 1")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 8:
        raise ValueError("userdata manifest must pin exactly six world and two settings files")
    seen: set[str] = set()
    roles = {"world": 0, "settings": 0}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("userdata manifest files entries must be objects")
        relative = entry.get("path")
        role = entry.get("role")
        size = entry.get("size_bytes")
        expected_hash = entry.get("sha256")
        if (not isinstance(relative, str) or not relative or Path(relative).is_absolute()
                or any(part in ("", ".", "..") for part in Path(relative).parts)):
            raise ValueError("userdata manifest paths must be clean relative paths")
        if relative in seen:
            raise ValueError("userdata manifest contains a duplicate path")
        seen.add(relative)
        if role not in roles:
            raise ValueError("userdata manifest role must be world or settings")
        roles[role] += 1
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("userdata manifest size_bytes must be a non-negative integer")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError("userdata manifest file SHA-256 must be complete")
        path = (userdata / relative).resolve()
        if not path.is_relative_to(userdata) or not path.is_file():
            raise ValueError("userdata manifest file is missing or escapes the userdata root")
        stat = path.stat()
        if stat.st_size != size or sha256_file(path) != expected_hash:
            raise ValueError(f"userdata input mismatch for {relative}")
    if roles != {"world": 6, "settings": 2}:
        raise ValueError("userdata manifest must contain exactly six world and two settings files")


def validate_freeze(freeze: dict) -> tuple[dict, dict, Path, Path]:
    if freeze.get("schema_version") != 1:
        raise ValueError("freeze schema_version must be 1")
    source = _required(freeze, "source", "root")
    world = _required(freeze, "world", "root")
    trials = _required(freeze, "trials", "root")
    runtime = _required(freeze, "runtime", "root")
    if source.get("commit") != "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248":
        raise ValueError("freeze must pin the reviewed Veloren v0.18.0 source commit")
    for key in ("source_patch_sha256", "cargo_lock_sha256", "binary_sha256"):
        value = source.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"freeze.source.{key} must be a full SHA-256")
    for path_key, hash_key in (("source_patch_path", "source_patch_sha256"),
                               ("cargo_lock_path", "cargo_lock_sha256")):
        path_value = source.get(path_key)
        if not isinstance(path_value, str) or not path_value:
            raise ValueError(f"freeze.source.{path_key} must identify the pinned input file")
        pinned_file = Path(path_value).expanduser().resolve()
        if not pinned_file.is_file() or sha256_file(pinned_file) != source[hash_key]:
            raise ValueError(f"pinned {path_key} is missing or does not match its frozen SHA-256")
    binary = Path(source.get("binary_path", "")).expanduser().resolve()
    assets = Path(source.get("assets_path", "")).expanduser().resolve()
    if not binary.is_file() or sha256_file(binary) != source["binary_sha256"]:
        raise ValueError("pinned server binary is missing or does not match its frozen SHA-256")
    if not assets.is_dir():
        raise ValueError("pinned official assets directory is missing")
    if world.get("world_seed") != 130626853:
        raise ValueError("world seed differs from the approved source-world copy")
    if not isinstance(world.get("source_world_sha256"), str) or len(world["source_world_sha256"]) != 64:
        raise ValueError("freeze.world.source_world_sha256 must pin the source world")
    if not isinstance(world.get("settings_contract_sha256"), str) or len(world["settings_contract_sha256"]) != 64:
        raise ValueError("freeze.world.settings_contract_sha256 must pin equivalent world settings")
    if runtime.get("loopback_only") is not True or runtime.get("query_address") is not None:
        raise ValueError("freeze must use loopback-only networking and no query address")
    if runtime.get("max_trial_wall_seconds") != int(TRIAL_WALL_CAP_SECONDS):
        raise ValueError("freeze trial wall cap must be 360 seconds")
    if runtime.get("disk_free_floor_bytes") != DISK_FLOOR_BYTES:
        raise ValueError("freeze disk floor must be 6 GiB")
    if (runtime.get("telemetry_record_cap") != TELEMETRY_RECORD_CAP
            or runtime.get("telemetry_byte_cap") != TELEMETRY_BYTE_CAP
            or runtime.get("telemetry_seconds_cap") != TELEMETRY_SECONDS_CAP):
        raise ValueError("freeze must pin the approved 10000-record/16-MiB/1800-second telemetry limits")
    if runtime.get("max_requests") != 8 or runtime.get("request_ttl_seconds") != 60:
        raise ValueError("freeze must pin the eight-request budget and 60-second TTL")
    if (runtime.get("loaded_prefix_min_game_times") != 3
            or runtime.get("loaded_prefix_min_wall_seconds") != 2.0
            or runtime.get("loaded_candidates_required") != 2):
        raise ValueError("freeze must pin the reviewed Loaded-prefix qualification")
    if runtime.get("leader_uid") != 476:
        raise ValueError("freeze must pin the single configured leader UID 476")
    for key in ("observe_npc_uids", "native_persister_npc_uids"):
        if not isinstance(runtime.get(key), list) or not runtime[key]:
            raise ValueError(f"freeze.runtime.{key} must be a non-empty UID list")
        if any(not isinstance(uid, int) or isinstance(uid, bool) or uid < 0 for uid in runtime[key]):
            raise ValueError(f"freeze.runtime.{key} must contain non-negative integer UIDs")
    if 476 not in runtime["observe_npc_uids"] or 476 not in runtime["native_persister_npc_uids"]:
        raise ValueError("both observer lists must include the configured leader 476")
    if runtime["observe_npc_uids"] != runtime["native_persister_npc_uids"]:
        raise ValueError("OFF and ON must use one identical observer/persister UID list")
    expected_observers = [476, 433, 450, 451, 452, 459, 469, 472, 475]
    if runtime["observe_npc_uids"] != expected_observers:
        raise ValueError("freeze must pin the approved leader plus eight candidate observer UIDs")
    if not isinstance(runtime.get("native_persister_view_distance_chunks"), int) or runtime["native_persister_view_distance_chunks"] <= 0:
        raise ValueError("freeze.runtime.native_persister_view_distance_chunks must be an integer")

    resolved_userdata = {}
    for mode in ("off", "on"):
        trial = _required(trials, mode, "trials")
        userdata = Path(trial.get("userdata_path", "")).expanduser().resolve()
        if not userdata.is_dir() or not (userdata / "server").is_dir():
            raise ValueError(f"prebuilt {mode} userdata must exist and contain server/")
        if trial.get("source_world_sha256") != world["source_world_sha256"]:
            raise ValueError(f"{mode} trial does not derive from the frozen source world")
        if trial.get("settings_contract_sha256") != world["settings_contract_sha256"]:
            raise ValueError(f"{mode} trial settings do not match the shared settings contract")
        manifest_path_value = trial.get("userdata_manifest_path")
        manifest_hash = trial.get("userdata_manifest_sha256")
        if not isinstance(manifest_path_value, str) or not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
            raise ValueError(f"{mode} userdata manifest path and SHA-256 must be pinned")
        manifest_path = Path(manifest_path_value).expanduser().resolve()
        if not manifest_path.is_relative_to(userdata) or not manifest_path.is_file():
            raise ValueError(f"{mode} userdata manifest must be an existing file inside userdata_path")
        if sha256_file(manifest_path) != manifest_hash:
            raise ValueError(f"{mode} userdata manifest does not match its frozen SHA-256")
        _validate_userdata_manifest(userdata, manifest_path)
        resolved_userdata[mode] = userdata
    if resolved_userdata["off"] == resolved_userdata["on"]:
        raise ValueError("OFF and ON userdata copies must be independent paths")
    if not isinstance(trials["off"].get("userdata_manifest_sha256"), str) or (
            trials["off"]["userdata_manifest_sha256"] == trials["on"]["userdata_manifest_sha256"]):
        raise ValueError("independent userdata copies must have separately frozen manifests")
    return source, runtime, resolved_userdata["off"], resolved_userdata["on"]


def run_trial(mode: str, binary: Path, assets: Path, userdata: Path, run_dir: Path,
              runtime: dict, *, wall_cap: float = TRIAL_WALL_CAP_SECONDS) -> dict:
    run_dir.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
        raise RuntimeError("free disk is below the 6 GiB safety floor before launch")
    if not userdata.is_dir() or not (userdata / "server").is_dir():
        raise ValueError("refusing to launch without a prebuilt isolated userdata copy")

    paths = {
        "native_events": run_dir / "native-events.jsonl",
        "recruit_events": run_dir / "recruit-events.jsonl",
        "requests": run_dir / "recruit-requests.jsonl",
        "controller": run_dir / "controller.jsonl",
    }
    for path in paths.values():
        path.touch(exist_ok=False)
    server_out_path, server_err_path = run_dir / "server.stdout.log", run_dir / "server.stderr.log"
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in run_dir.name)
    controller = RecruitmentController(mode, safe_run_id, leader_uid=476,
                                       ttl_seconds=float(runtime["request_ttl_seconds"]))
    env = os.environ.copy()
    for key in CLEARED_INHERITED_ENV:
        env.pop(key, None)
    env.update({
        "VELOREN_USERDATA": str(userdata),
        "VELOREN_ASSETS": str(assets),
        "VELOREN_NATIVE_EVENTS": str(paths["native_events"]),
        "VELOREN_NATIVE_OBSERVE": "1",
        "VELOREN_NATIVE_OBSERVE_UIDS": ",".join(str(uid) for uid in runtime["observe_npc_uids"]),
        "VELOREN_NATIVE_PERSISTER_NPC_UIDS": ",".join(str(uid) for uid in runtime["native_persister_npc_uids"]),
        "VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE": str(runtime["native_persister_view_distance_chunks"]),
        "VELOREN_NATIVE_MAX_RECORDS": str(TELEMETRY_RECORD_CAP),
        "VELOREN_NATIVE_MAX_BYTES": str(TELEMETRY_BYTE_CAP),
        "VELOREN_NATIVE_MAX_SECONDS": str(TELEMETRY_SECONDS_CAP),
        "VELOREN_NATIVE_RECRUIT_REQUESTS": str(paths["requests"]),
        "VELOREN_NATIVE_RECRUIT_EVENTS": str(paths["recruit_events"]),
        "VELOREN_NATIVE_RECRUIT_LEADER_UID": str(runtime["leader_uid"]),
    })
    tail = JsonlTail(paths["recruit_events"])
    native_tail = JsonlTail(paths["native_events"])
    readiness_gate = LoadedPrefixGate(int(runtime["leader_uid"]))
    started_local, started_mono = local_now(), time.monotonic()
    server_started_local = None
    stop_reason = "supervisor_error"
    request_rows = 0
    recruitment_handoff_mono = None
    telemetry_records = 0
    native_records = 0
    controller_records = 0
    latest_actor_view = None
    latest_actor_view_mono = None
    planning_enabled = mode == "off"
    loaded_prefix = None
    server = None
    spawn_error = None

    def append_controller_record(record):
        nonlocal controller_records
        append_jsonl_once(paths["controller"], record)
        controller_records += 1

    def consume_recruit_rows(rows):
        nonlocal request_rows, recruitment_handoff_mono, telemetry_records, stop_reason
        for row in rows:
            telemetry_records += 1
            for record in controller.feed(row):
                append_controller_record(record)
                if record.get("event") == "native_request_proposed":
                    append_jsonl_once(paths["requests"], record["request"])
                    request_rows += 1
                elif record.get("event") == "planner_control_returned_to_native":
                    recruitment_handoff_mono = time.monotonic()

    with server_out_path.open("xb") as server_out, server_err_path.open("xb") as server_err:
        try:
            try:
                server = subprocess.Popen([str(binary), "--non-interactive"], env=env,
                                          stdout=server_out, stderr=server_err)
            except OSError as exc:
                spawn_error = f"{type(exc).__name__}: {exc}"
                stop_reason = "spawn_failed"
            if server is None:
                pass
            else:
                server_started_local = local_now()
                stop_reason = "wall_cap"
            while server is not None and server.poll() is None:
                now_mono = time.monotonic()
                if now_mono - started_mono >= wall_cap:
                    stop_reason = ("loaded_prefix_not_satisfied_at_trial_wall_cap"
                                   if mode == "on" and not planning_enabled else "wall_cap")
                    break
                if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
                    stop_reason = "disk_floor"
                    break
                recruit_rows = tail.read_rows()
                native_rows = native_tail.read_rows()
                observed_mono = time.monotonic()
                native_records += len(native_rows)
                for native_row in native_rows:
                    readiness_gate.observe(native_row, observed_mono)
                if mode == "off" or planning_enabled:
                    consume_recruit_rows(recruit_rows)
                else:
                    for recruit_row in recruit_rows:
                        telemetry_records += 1
                        if recruit_row.get("event") == "native_recruit_actor_view":
                            latest_actor_view = recruit_row
                            latest_actor_view_mono = observed_mono
                    if (latest_actor_view is not None and latest_actor_view_mono is not None
                            and observed_mono - latest_actor_view_mono <= 1.25):
                        loaded_prefix = readiness_gate.check(latest_actor_view, observed_mono)
                        if loaded_prefix is not None:
                            planning_enabled = True
                            append_controller_record({
                                "event": "loaded_native_prefix_satisfied",
                                "observed_local": local_now(), **loaded_prefix,
                            })
                            consume_recruit_rows([latest_actor_view])
                total_records = telemetry_records + native_records + controller_records + request_rows
                total_bytes = sum(path.stat().st_size for path in run_dir.iterdir() if path.is_file())
                if total_records >= TELEMETRY_RECORD_CAP or total_bytes >= TELEMETRY_BYTE_CAP:
                    stop_reason = "telemetry_cap"
                    break
                if mode == "on" and recruitment_handoff_mono is not None and (
                        time.monotonic() - recruitment_handoff_mono >= POST_NATIVE_HANDOFF_SECONDS):
                    stop_reason = "four_hires_then_native_continuation_observed"
                    break
                if server.poll() is not None:
                    stop_reason = "server_exited"
                    break
                time.sleep(0.1)
            if server is not None and server.poll() is not None and stop_reason == "wall_cap":
                stop_reason = "server_exited"
        finally:
            sigusr1_local = None
            if server is not None and server.poll() is None:
                sigusr1_local = local_now()
                server.send_signal(signal.SIGUSR1)
                try:
                    server.wait(timeout=SERVER_GRACE_SECONDS + 15)
                except subprocess.TimeoutExpired:
                    stop_reason += ";sigterm_fallback"
                    server.terminate()
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        stop_reason += ";sigkill_fallback"
                        server.kill()
                        server.wait()
            else:
                sigusr1_local = None
            # Drain complete records written immediately before process exit;
            # JsonlTail keeps any final partial line for honest omission.
            consume_recruit_rows(tail.read_rows())
            native_records += len(native_tail.read_rows())

    manifest = {
        "mode": mode,
        "run_started_local": started_local,
        "server_started_local": server_started_local,
        "sigusr1_sent_local": sigusr1_local,
        "run_finished_local": local_now(),
        "run_elapsed_seconds": time.monotonic() - started_mono,
        "server_pid": server.pid if server else None,
        "server_exit_code": server.returncode if server else None,
        "stop_reason": stop_reason,
        "spawn_error": spawn_error,
        "request_rows_written": request_rows,
        "telemetry_records_observed": telemetry_records,
        "native_observer_records_observed": native_records,
        "controller_records_written": controller_records,
        "combined_records_observed": telemetry_records + native_records + controller_records + request_rows,
        "telemetry_record_cap": TELEMETRY_RECORD_CAP,
        "telemetry_byte_cap": TELEMETRY_BYTE_CAP,
        "telemetry_seconds_cap": TELEMETRY_SECONDS_CAP,
        "on_planning_enabled": planning_enabled if mode == "on" else None,
        "loaded_prefix": loaded_prefix,
        "trial_wall_cap_seconds": wall_cap,
        "disk_floor_bytes": DISK_FLOOR_BYTES,
        "disk_free_bytes_at_end": shutil.disk_usage(run_dir).free,
        "input_paths": {key: str(value) for key, value in paths.items()},
        "input_sha256": {key: sha256_file(value) for key, value in paths.items()},
        "server_command": [str(binary), "--non-interactive"],
        "recruit_environment": {
            "VELOREN_NATIVE_RECRUIT_REQUESTS": str(paths["requests"]),
            "VELOREN_NATIVE_RECRUIT_EVENTS": str(paths["recruit_events"]),
            "VELOREN_NATIVE_RECRUIT_LEADER_UID": str(runtime["leader_uid"]),
        },
        "cleared_inherited_environment_variables": list(CLEARED_INHERITED_ENV),
    }
    (run_dir / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True, help="parent-reviewed immutable input freeze JSON")
    parser.add_argument("--pair-dir", type=Path, required=True, help="new ignored output directory; must not exist")
    args = parser.parse_args(argv)
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    source, runtime, userdata_off, userdata_on = validate_freeze(freeze)
    root = Path.cwd().resolve()
    allowed_root = (root / RUN_ROOT).resolve()
    pair_dir = args.pair_dir.expanduser().resolve()
    if not pair_dir.is_relative_to(allowed_root):
        raise ValueError(f"pair-dir must be under {allowed_root}")
    if pair_dir.exists():
        raise FileExistsError("pair-dir already exists; run outputs are never overwritten")
    pair_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.freeze, pair_dir / "input-freeze.json")
    (pair_dir / "input-freeze.sha256").write_text(sha256_file(args.freeze) + "\n", encoding="ascii")
    source_binary = Path(source["binary_path"]).expanduser().resolve()
    assets = Path(source["assets_path"]).expanduser().resolve()
    start = local_now()
    results = {"pair_started_local": start, "server_launch_limit": 2, "server_launches": []}
    try:
        for mode, userdata in (("off", userdata_off), ("on", userdata_on)):
            trial_manifest = run_trial(mode, source_binary, assets, userdata,
                                       pair_dir / mode, runtime)
            results["server_launches"].append(trial_manifest)
            (pair_dir / "pair-manifest.json").write_text(json.dumps(results, indent=2) + "\n",
                                                          encoding="utf-8")
            if trial_manifest["server_exit_code"] is None or trial_manifest["server_exit_code"] != 0:
                break
    finally:
        results["pair_finished_local"] = local_now()
        results["server_launches_started"] = len(results["server_launches"])
        results["native_rng_controlled"] = False
        (pair_dir / "pair-manifest.json").write_text(json.dumps(results, indent=2) + "\n",
                                                      encoding="utf-8")
    return 0 if len(results["server_launches"]) == 2 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"recruitment pair supervisor refused or stopped: {exc}", file=sys.stderr)
        raise SystemExit(2)

