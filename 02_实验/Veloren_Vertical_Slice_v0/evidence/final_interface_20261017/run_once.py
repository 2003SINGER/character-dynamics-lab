#!/usr/bin/env python3
"""One-shot supervisor for the approved headless Veloren A run.

This file only launches when explicitly invoked. It creates fresh telemetry,
request, and log files in the caller-supplied run directory, starts the probe
before the server, enforces wall/disk limits, and signals only its own server
PID on every exit path.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


DISK_FLOOR = 6 * 1024**3
WALL_CAP = 1800
GRACE_SECONDS = 1


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--userdata", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    binary = Path(config["source"]["binary_path"])
    assets = Path(config["network_and_runtime"]["VELOREN_ASSETS"])
    probe = Path(config["harness"]["path"])
    args.run_dir.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(args.run_dir).free < DISK_FLOOR:
        raise RuntimeError("disk free space is already below the 6 GiB run floor")
    args.userdata = args.userdata.resolve()
    if not args.userdata.is_dir() or not (args.userdata / "server").is_dir():
        raise ValueError("run userdata must be an already prepared isolated server copy")
    if not binary.is_file() or not assets.is_dir() or not probe.is_file():
        raise ValueError("pinned binary, assets, or probe path is missing")
    requests = args.run_dir / "native-requests.jsonl"
    events = args.run_dir / "native-events.jsonl"
    requests.touch(exist_ok=False)
    stdout_server = (args.run_dir / "server.stdout.log").open("xb")
    stderr_server = (args.run_dir / "server.stderr.log").open("xb")
    stdout_probe = (args.run_dir / "probe.stdout.log").open("xb")
    stderr_probe = (args.run_dir / "probe.stderr.log").open("xb")

    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    base_id = f"cd-final-{stamp}"
    env = os.environ.copy()
    env.update({
        "VELOREN_USERDATA": str(args.userdata),
        "VELOREN_ASSETS": str(assets),
        "VELOREN_NATIVE_EVENTS": str(events),
        "VELOREN_NATIVE_REQUESTS": str(requests),
        "VELOREN_NATIVE_OBSERVE": "1",
        "VELOREN_NATIVE_OBSERVE_UIDS": ",".join(map(str, config["world"]["observe_npc_uids"])),
        "VELOREN_NATIVE_PERSISTER_NPC_UIDS": ",".join(map(str, config["world"]["native_persister_npc_uids"])),
        "VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE": str(config["world"]["native_persister_view_distance_chunks"]),
        "VELOREN_NATIVE_MAX_RECORDS": str(config["network_and_runtime"]["VELOREN_NATIVE_MAX_RECORDS"]),
        "VELOREN_NATIVE_MAX_BYTES": str(config["network_and_runtime"]["VELOREN_NATIVE_MAX_BYTES"]),
        "VELOREN_NATIVE_MAX_SECONDS": str(config["network_and_runtime"]["VELOREN_NATIVE_MAX_SECONDS"]),
    })
    probe_cmd = [sys.executable, str(probe), "--events", str(events),
                 "--requests", str(requests), "--npc-uid", "445", "--target-uid", "465",
                 "--source", "final-interface-a", "--cancel-id", f"{base_id}-cancel",
                 "--request-id", f"{base_id}-positive", "--max-positive", "6"]
    server = None
    controller = None
    started = local_now()
    started_mono = time.monotonic()
    signal_time = None
    first_baseline_time = None
    first_valid_loaded_baseline_time = None
    server_started = None
    result = 1
    reason = "supervisor_exception"
    telemetry_offset = 0
    telemetry_records = 0
    try:
        controller = subprocess.Popen(probe_cmd, stdout=stdout_probe, stderr=stderr_probe)
        server = subprocess.Popen([str(binary), "--non-interactive"],
                                  env=env, stdout=stdout_server, stderr=stderr_server)
        server_started = local_now()
        reason = "probe_finished"
        telemetry_pending = b""
        while controller.poll() is None:
            if server.poll() is not None:
                reason = "server_exited_before_probe"
                break
            if time.monotonic() - started_mono >= WALL_CAP:
                reason = "wall_cap"
                break
            if shutil.disk_usage(args.run_dir).free < DISK_FLOOR:
                reason = "disk_floor"
                break
            try:
                with events.open("rb") as stream:
                    stream.seek(telemetry_offset)
                    new_bytes = stream.read()
                    telemetry_offset += len(new_bytes)
                    telemetry_pending += new_bytes
                    complete_lines = telemetry_pending.split(b"\n")
                    telemetry_pending = complete_lines.pop()
                    for line in complete_lines:
                        try:
                            row = json.loads(line)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        telemetry_records += 1
                        world = row.get("actual_world_state")
                        pos = world.get("ecs_position") if isinstance(world, dict) else None
                        if row.get("event") == "native_npc_baseline":
                            observed_at = local_now()
                            if first_baseline_time is None:
                                first_baseline_time = observed_at
                            valid_position = (
                                isinstance(pos, list) and len(pos) == 3
                                and all(isinstance(value, (int, float))
                                        and math.isfinite(value) for value in pos)
                            )
                            valid_baseline = (
                                row.get("mode") == "loaded" and row.get("alive") is True
                                and isinstance(row.get("brain_backtrace"), list)
                                and isinstance(row.get("controller_activity"), str)
                                and valid_position
                            )
                            if valid_baseline and first_valid_loaded_baseline_time is None:
                                first_valid_loaded_baseline_time = observed_at
            except FileNotFoundError:
                pass
            time.sleep(0.1)
        if controller.poll() is None:
            controller.send_signal(signal.SIGTERM)
            try:
                controller.wait(timeout=5)
            except subprocess.TimeoutExpired:
                controller.kill()
                controller.wait()
        result = controller.returncode if controller is not None else 1
    finally:
        if controller is not None and controller.poll() is None:
            controller.terminate()
            try:
                controller.wait(timeout=5)
            except subprocess.TimeoutExpired:
                controller.kill()
                controller.wait()
        if server is not None and server.poll() is None:
            signal_time = local_now()
            try:
                server.send_signal(signal.SIGUSR1)
            except ProcessLookupError:
                pass
            try:
                server.wait(timeout=GRACE_SECONDS + 15)
            except subprocess.TimeoutExpired:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
                reason += ";server_sigterm_fallback"
        for stream in (stdout_probe, stderr_probe, stdout_server, stderr_server):
            stream.close()
        manifest = {
            "run_started_local": started,
            "server_started_local": server_started,
            "first_baseline_event_observed_local": first_baseline_time,
            "first_valid_loaded_baseline_observed_local": first_valid_loaded_baseline_time,
            "sigusr1_sent_local": signal_time,
            "run_finished_local": local_now(),
            "server_pid": server.pid if server else None,
            "server_exit_code": server.returncode if server else None,
            "probe_exit_code": controller.returncode if controller else None,
            "stop_reason": reason,
            "run_elapsed_seconds": time.monotonic() - started_mono,
            "telemetry_bytes_observed": telemetry_offset,
            "telemetry_file_bytes_at_end": events.stat().st_size if events.exists() else 0,
            "telemetry_records_observed": telemetry_records,
            "telemetry_record_cap": int(env["VELOREN_NATIVE_MAX_RECORDS"]),
            "telemetry_byte_cap": int(env["VELOREN_NATIVE_MAX_BYTES"]),
            "telemetry_time_cap_seconds": int(env["VELOREN_NATIVE_MAX_SECONDS"]),
            "disk_free_bytes_at_end": shutil.disk_usage(args.run_dir).free,
            "server_command": [str(binary), "--non-interactive"],
            "probe_command": probe_cmd,
            "events_file": str(events),
            "requests_file": str(requests),
        }
        (args.run_dir / "runtime-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"supervisor aborted before launch or during setup: {exc}", file=sys.stderr)
        raise SystemExit(2)
