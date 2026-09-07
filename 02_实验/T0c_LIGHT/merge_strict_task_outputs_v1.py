#!/usr/bin/env python3
"""Merge only contiguous fresh-session task outputs into a strict v2 prefix."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_v2_dir", type=Path)
    ap.add_argument("strict_output_dir", type=Path)
    args = ap.parse_args()
    manifest = json.loads((args.input_v2_dir / "manifest_v2.json").read_text(encoding="utf8"))
    args.strict_output_dir.mkdir(parents=True, exist_ok=True)
    task_dir = args.strict_output_dir / "task_outputs"
    merged_tmp = args.strict_output_dir / "annotations.jsonl.tmp"
    merged = args.strict_output_dir / "annotations.jsonl"
    completed = []
    rows = 0
    with merged_tmp.open("w", encoding="utf8") as out:
        for index, task_name in enumerate(manifest["tasks"], 1):
            path = task_dir / task_name
            if not path.exists():
                break
            lines = [line for line in path.read_text(encoding="utf8").splitlines() if line.strip()]
            if len(lines) != min(manifest["rows_per_task"], manifest["row_count"] - rows):
                raise SystemExit(f"{task_name}: expected a complete task, got {len(lines)} rows")
            for line in lines:
                json.loads(line)
                out.write(line + "\n")
            completed.append(task_name)
            rows += len(lines)
    os.replace(merged_tmp, merged)
    checkpoint = {
        "schema_version": "character_dynamics_light_semantic_annotation_v2_strict_checkpoint_v1",
        "input_manifest": str(args.input_v2_dir / "manifest_v2.json"),
        "completed_tasks": completed,
        "completed_rows": rows,
        "next_task": manifest["tasks"][len(completed)] if len(completed) < len(manifest["tasks"]) else None,
        "fresh_session_required": True,
    }
    (args.strict_output_dir / "checkpoint.json").write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(checkpoint, ensure_ascii=False))


if __name__ == "__main__":
    main()
