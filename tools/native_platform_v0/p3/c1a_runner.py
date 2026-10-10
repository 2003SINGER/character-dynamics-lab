"""Run one bounded P3-C1a recovery case through the live Evennia callback service."""

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


RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_C1a_v0/runs"
SCENARIOS = ("C1a-blocked-switch", "C1a-observed-resume")
SOURCE_FILES = (
    "tools/native_platform_v0/p3/c1a_runner.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/export_evidence.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/planning.py",
    "tools/native_platform_v0/p3/commands.py",
    "tools/native_platform_v0/bridge/social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
)


def source_manifest() -> dict:
    hashes = {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
              if (PROJECT_ROOT / name).is_file() else "missing" for name in SOURCE_FILES}
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              text=True, capture_output=True, check=False)
    return {"git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "hash_scope": "sha256 of actual working-tree source bytes; revision is base commit only",
            "source_sha256": hashes,
            "source_snapshot_sha256": hashlib.sha256(packed).hexdigest()}


def write_run(document: dict, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        target = runs_dir / (f"p3-c1a-{document['configuration']['scenario']}-"
                             f"seed{document['configuration']['seed']}-{timestamp}-"
                             f"{secrets.token_hex(3)}.json")
        try:
            with target.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return target
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique P3-C1a run output")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args(argv)
    if not 0 <= args.seed <= 2**31 - 1:
        parser.error("--seed must be in 0..2147483647")
    response = rpc_call("run_c1a_scenario", {"scenario": args.scenario, "seed": args.seed})
    configuration = {"scenario": args.scenario, "seed": args.seed,
                     "activity_profile": "delivery_patrol_recovery_v0", "drive_mode": "manual",
                     "callback_count": 12 if args.scenario == "C1a-blocked-switch" else 16,
                     "controller_authored_npc_commands": 0}
    document = {"schema": "native-p3-c1a-run-artifact-v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "configuration": configuration, "manifest": source_manifest(),
                "response": response}
    output = write_run(document)
    complete = response.get("callbacks_completed") is True
    print(json.dumps({"status": "RECORDED" if complete else "INCOMPLETE",
                      "semantic_acceptance": "not_evaluated_by_runner",
                      "scenario": args.scenario, "seed": args.seed,
                      "scene_ids": response.get("scene_ids", []), "path": str(output)},
                     ensure_ascii=False))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
