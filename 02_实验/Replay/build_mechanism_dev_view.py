#!/usr/bin/env python3
"""Build an explicitly filtered mechanism-dev view from full ReplayRecord JSONL.

Quarantined source episodes are excluded by code, never by README convention.
The full derived asset remains untouched.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    kept = quarantined = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open(encoding="utf-8") as src, args.output.open("w", encoding="utf-8", newline="\n") as dst:
        for line in src:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("source_episode_context", {}).get("quarantine"):
                quarantined += 1
                continue
            dst.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            kept += 1
    manifest = {
        "schema_version": "mechanism_dev_view_manifest_v0",
        "source_input": str(args.input),
        "output": str(args.output),
        "kept_trajectory_count": kept,
        "quarantined_trajectory_count": quarantined,
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "filter": "exclude when source_episode_context.quarantine == true",
        "not_a_semantic_admission_filter": True,
        "does_not_use_source_action_quality": True,
        "mechanism_use": "dev_only; semantic admission remains pending",
    }
    manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
