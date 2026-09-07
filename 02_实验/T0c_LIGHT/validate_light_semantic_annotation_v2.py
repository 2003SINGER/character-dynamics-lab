#!/usr/bin/env python3
"""Strict validator for the isolated LIGHT v2 reviewer protocol."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


INPUT_FIELDS = {"review_id", "actor", "source_O", "source_action_A_star", "candidate_set_factual"}
OUTPUT_FIELDS = {"review_id", "label", "a_star_alignment", "candidate_usability", "reasons", "note"}
LABELS = {"ADMIT", "REJECT", "AMBIGUOUS"}
ALIGNMENTS = {"YES", "NO", "UNCLEAR"}
USABILITY = {"USABLE", "NOT_USABLE", "UNCLEAR"}
REASONS = {"ACTION_CANDIDATE_MISMATCH", "ACTOR_ACTION_CONTRADICTION", "MALFORMED_ACTION", "CANDIDATE_SEMANTIC_CONTRADICTION", "CANDIDATE_SET_MALFORMED", "ENTITY_RELATION_UNCLEAR", "ACTOR_VISIBILITY_OR_OWNERSHIP_UNCLEAR", "OBSERVATION_INSUFFICIENT", "ACTION_ENTITY_OR_RELATION_UNOBSERVED"}


def read_jsonl(path: Path):
    with path.open(encoding="utf8") as fh:
        for line_number, text in enumerate(fh, 1):
            if text.strip():
                yield line_number, json.loads(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("v2_dir", type=Path)
    ap.add_argument("annotations", type=Path)
    ap.add_argument("--completed-tasks", type=int, required=True)
    args = ap.parse_args()
    manifest = json.loads((args.v2_dir / "manifest_v2.json").read_text(encoding="utf8"))
    mapping = list(read_jsonl(args.v2_dir / manifest["private_mapping"]))
    errors = []
    if manifest.get("reviewer_input_fields") != ["review_id", "actor", "source_O", "source_action_A_star", "candidate_set_factual"]:
        errors.append("manifest reviewer input fields violate isolation schema")
    tasks = manifest["tasks"]
    if not 0 <= args.completed_tasks <= len(tasks):
        errors.append("completed task count out of range")
    expected_mapping = [row for _, row in mapping if row["shard"] in set(tasks[:args.completed_tasks])]
    expected = [row["review_id"] for row in expected_mapping]
    if len(expected) != len(set(expected)):
        errors.append("private mapping contains duplicate opaque IDs")
    for task in tasks[:args.completed_tasks]:
        payload = list(read_jsonl(args.v2_dir / "reviewer_input_shards" / task))
        payload_rows = [r for _, r in payload]
        if any(set(r) != INPUT_FIELDS for r in payload_rows):
            errors.append(f"{task}: reviewer payload has missing or leaked fields")
        task_ids = {r["review_id"] for r in payload_rows}
        task_trajectories = {r["trajectory_id"] for r in expected_mapping if r["review_id"] in task_ids}
        if len(task_ids) != len(task_trajectories):
            errors.append(f"{task}: trajectory isolation violated")
    rows = list(read_jsonl(args.annotations))
    ids, counts = [], Counter()
    for line_number, row in rows:
        ids.append(row.get("review_id"))
        if set(row) != OUTPUT_FIELDS:
            errors.append(f"line {line_number}: output fields must be exact")
            continue
        if row["label"] not in LABELS or row["a_star_alignment"] not in ALIGNMENTS or row["candidate_usability"] not in USABILITY:
            errors.append(f"line {line_number}: invalid enum")
        if not isinstance(row["reasons"], list) or not all(isinstance(x, str) and x in REASONS for x in row["reasons"]):
            errors.append(f"line {line_number}: invalid controlled reason codes")
        if not isinstance(row["note"], str):
            errors.append(f"line {line_number}: note must be string")
        if row["label"] == "REJECT" and not row["reasons"]:
            errors.append(f"line {line_number}: reject requires reason code")
        if row["label"] == "AMBIGUOUS" and not any(x in {"ENTITY_RELATION_UNCLEAR", "ACTOR_VISIBILITY_OR_OWNERSHIP_UNCLEAR", "OBSERVATION_INSUFFICIENT", "ACTION_ENTITY_OR_RELATION_UNOBSERVED"} for x in row["reasons"]):
            errors.append(f"line {line_number}: ambiguous requires uncertainty reason")
        counts[row["label"]] += 1
    if ids != expected:
        errors.append("outputs are not the exact ordered sequence for completed whole tasks")
    report = {"expected_rows": len(expected), "annotated_rows": len(rows), "completed_tasks": args.completed_tasks, "label_counts": dict(counts), "valid": not errors, "errors": errors[:100]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
