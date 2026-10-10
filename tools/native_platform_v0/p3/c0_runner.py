"""Run one exact P3-C0 development case through the live Evennia callback service."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.mcp_stdio import rpc_call


RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_C0_v0/runs"
SCENARIOS = ("C0-no-delivery", "C0-delivery-priority", "C0-after-delivery")
SOURCE_FILES = (
    "tools/native_platform_v0/p3/c0_runner.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/export_evidence.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/planning.py",
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/commands.py",
    "tools/native_platform_v0/bridge/social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
)


def source_manifest() -> dict:
    hashes = {}
    for relative in SOURCE_FILES:
        path = PROJECT_ROOT / relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              text=True, capture_output=True, check=False)
    return {"git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "hash_scope": "sha256 of actual working-tree source bytes; git revision is base commit only",
            "source_sha256": hashes,
            "source_snapshot_sha256": hashlib.sha256(canonical).hexdigest()}


def write_run(document: dict, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scenario = document["configuration"]["scenario"]
    seed = document["configuration"]["seed"]
    for _ in range(8):
        path = runs_dir / f"p3-c0-{scenario}-seed{seed}-{now}-{secrets.token_hex(3)}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique P3-C0 run output")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args(argv)
    if not 0 <= args.seed <= 2**31 - 1:
        parser.error("--seed must be in 0..2147483647")
    configuration = {"scenario": args.scenario, "seed": args.seed,
                     "activity_profile": "delivery_patrol_v0", "drive_mode": "manual",
                     "controller_authored_commands": 0,
                     "callback_limits": {"C0-no-delivery": {"primary": 12, "locked_exit_negative_control": 10},
                                         "C0-delivery-priority": 12, "C0-after-delivery": 20}[args.scenario]}
    response = rpc_call("run_c0_scenario", {"scenario": args.scenario, "seed": args.seed})
    document = {"schema": "native-p3-c0-run-artifact-v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "configuration": configuration, "manifest": source_manifest(),
                "response": response}
    output = write_run(document)
    print(json.dumps({"status": "RECORDED" if response.get("callbacks_completed") else "INCOMPLETE",
                      "semantic_acceptance": "not_evaluated_by_runner",
                      "scenario": args.scenario, "seed": args.seed,
                      "scene_ids": [scene["trace"]["scene_id"] for scene in response.get("scenes", [])]
                                   or [response.get("trace", {}).get("scene_id")],
                      "path": str(output)}, ensure_ascii=False))
    return 0 if response.get("callbacks_completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
