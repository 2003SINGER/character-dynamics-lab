#!/usr/bin/env python3
"""Build a deterministic blind semantic-audit sample from the full ClubFloyd replay."""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path

TARGETS = {"command-like": 100, "ambiguous": 100, "chat/commentary-like": 100, "meta-command": 100}

def rank(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("replay", type=Path); ap.add_argument("out", type=Path)
    args = ap.parse_args(); buckets = defaultdict(list); total = defaultdict(int); traj = set()
    with args.replay.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line); tid = rec.get("trajectory_id") or rec.get("source_record_id")
            for i, step in enumerate(rec.get("steps", [])):
                q = step.get("source_step_context", {}).get("source_action_quality", "ambiguous")
                total[q] += 1; traj.add(tid)
                key = f"{tid}::{step.get('t', i)}::{i}"
                buckets[q].append((rank(key), key, {"audit_id": f"clubfloyd-audit::{key}", "trajectory_id": tid,
                    "step_index": i, "quality_stratum": q, "raw_action": step.get("source_action_A_star", ""),
                    "pre_action_state": step.get("source_O", "")}))
    selected=[]
    for q, target in TARGETS.items():
        rows = sorted(buckets[q])[:min(target, len(buckets[q]))]
        selected.extend(x[2] for x in rows)
    selected.sort(key=lambda x: x["audit_id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as fh:
        for row in selected: fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    manifest = {"schema_version":"command_admission_audit_sample_v0", "source":"clubfloyd_full.replay.jsonl",
        "selection":"sha256 rank within fixed quality strata", "targets":TARGETS, "selected_counts":{q:sum(r['quality_stratum']==q for r in selected) for q in TARGETS},
        "total_counts":dict(total), "trajectory_count":len(traj), "sample_count":len(selected),
        "blind_fields":["raw_action","pre_action_state"], "forbidden_fields":["post_action_state","reward","future_action","parsed"],
        "sample_sha256":hashlib.sha256(args.out.read_bytes()).hexdigest()}
    args.out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
