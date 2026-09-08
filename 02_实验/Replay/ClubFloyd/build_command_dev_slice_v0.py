"""Build a small, trajectory-disjoint ClubFloyd Stage-A protocol fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from command_schema_v0 import canonicalize


def split_for(source_file: str) -> str:
    rank = int(hashlib.sha256(source_file.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "train" if rank < 0.7 else "validation" if rank < 0.85 else "development_holdout"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_jsonl", type=Path)
    parser.add_argument("out_jsonl", type=Path)
    parser.add_argument("--trajectory-limit", type=int, default=30)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.review_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    source_files = sorted({row["raw"]["source_file"] for row in rows})[: args.trajectory_limit]
    selected = [row for row in rows if row["raw"]["source_file"] in source_files]
    output: list[dict[str, Any]] = []
    for row in selected:
        source_file = row["raw"]["source_file"]
        quality = row["transformed"]["source_step_context"].get("source_action_quality")
        parsed = canonicalize(row["raw"]["raw_action"], quality)
        if quality != "command-like" or parsed["parse_status"] != "parsed":
            continue
        output.append({
            "trajectory_id": source_file,
            "split": split_for(source_file),
            "step": row["transformed"]["t"],
            "source_O": row["raw"]["raw_state"],
            "source_action_A_star": row["raw"]["raw_action"],
            "canonical_action": parsed,
            "source_record_ref": row["source_record_ref"],
            "future_state_in_input": False,
        })
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in output), encoding="utf-8")
    manifest = {
        "protocol": "ClubFloyd-source-command-v0",
        "source_review_fixture": str(args.review_jsonl),
        "trajectory_limit": args.trajectory_limit,
        "selected_trajectories": len(source_files),
        "verified_command_like_steps": len(output),
        "split_counts": {name: sum(item["split"] == name for item in output) for name in ("train", "validation", "development_holdout")},
        "trajectory_disjoint": len({(item["trajectory_id"], item["split"]) for item in output}) == len({item["trajectory_id"] for item in output}),
        "future_state_in_input_all_false": all(not item["future_state_in_input"] for item in output),
    }
    (args.out_jsonl.with_suffix(".manifest.json")).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()

