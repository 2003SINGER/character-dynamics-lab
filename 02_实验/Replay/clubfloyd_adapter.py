#!/usr/bin/env python3
"""Deterministically adapt the CALM ClubFloyd transcript files to ReplayRecord v0.

The source files are line-oriented ``[STATE] ... [ACTION] ...`` transcripts.
This adapter only copies observed strings; it does not infer persona, world state,
candidate actions, or hidden outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PAIR = re.compile(r"\[STATE\](.*?)\[ACTION\](.*?)(?=\[STATE\]|\Z)", re.S)


def parse_file(path: Path, split_id: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    pairs = [(s.strip(), a.strip()) for s, a in PAIR.findall(text)]
    pairs = [(s, a) for s, a in pairs if a]
    steps = []
    for t, (state, action) in enumerate(pairs):
        steps.append({
            "t": t,
            "source_O": state,
            "source_event": None,
            "source_action_A_star": action,
            "source_step_context": {"format": "CALM_markers", "raw_state": state, "raw_action": action},
            "W": None,
            "state_label": None,
            "candidate_set_factual": None,
            "candidate_set_expanded": None,
            "timestamp": None,
            "provenance": "observed",
            "provenance_detail": "ClubFloyd human gameplay transcript; state is the game response preceding the recorded command.",
            "field_provenance": {
                "source_O": {"kind": "observed", "source_ref": path.name},
                "source_action_A_star": {"kind": "observed", "source_ref": path.name},
            },
        })
    return {
        "trajectory_id": f"clubfloyd::{path.stem}",
        "subject_id": None,
        "group_id": None,
        "split_id": split_id,
        "source_dataset": "ClubFloyd",
        "source_revision": "calm-textgame@3c111c0102c27e258f596ace18540db22f97f1da",
        "source_record_id": path.name,
        "source_license": "See CALM repository acknowledgement; transcript redistribution terms require separate review.",
        "persona_P": None,
        "source_episode_context": {"source_file": path.name, "marker_format": "[STATE]/[ACTION]"},
        "steps": steps,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--split-id", default="clubfloyd_dev_2026-09-06")
    args = ap.parse_args()
    files = sorted(args.raw_dir.glob("*.html"))[: args.limit]
    records = [parse_file(p, args.split_id) for p in files]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"records": len(records), "steps": sum(len(r["steps"]) for r in records), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
