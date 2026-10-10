"""Run a bounded native P3 scenario and save its full non-secret response."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.mcp_stdio import rpc_call


RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_v0/runs"
SCENARIOS = {"Aclean", "Asteal-return", "Bclean", "Bsteal-resident-parcel"}
PROVENANCE_FILES = (
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/planning.py",
    "tools/native_platform_v0/p3/commands.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/bridge/social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
)


def source_hashes() -> dict[str, str]:
    hashes = {}
    for relative in PROVENANCE_FILES:
        path = PROJECT_ROOT / relative
        if path.is_file():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            hashes[relative] = "missing"
    return hashes


def write_result(result: dict, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scenario = result["request"]["scenario"]
    seed = result["request"]["seed"]
    for _ in range(8):
        target = runs_dir / f"p3-headless-{scenario}-seed{seed}-{timestamp}-{secrets.token_hex(3)}.json"
        try:
            with target.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return target
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a fresh P3 run output after eight attempts")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    if not 0 <= args.seed <= 2**31 - 1:
        parser.error("--seed must be in 0..2147483647")
    request = {"scenario": args.scenario, "seed": args.seed}
    result = rpc_call("run_scenario", request)
    document = {"schema": "native-p3-headless-run-v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "request": request, "source_sha256": source_hashes(), "response": result}
    output = write_result(document)
    print(json.dumps({"status": "COMPLETED" if result.get("completed") else "INCOMPLETE",
                      "path": str(output), "scene_id": result.get("scene", {}).get("scene_id"),
                      "scenario": args.scenario, "seed": args.seed}, ensure_ascii=False))
    return 0 if result.get("completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
