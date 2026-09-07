#!/usr/bin/env python3
"""Validate one resumable source-only LIGHT reviewer JSONL against prepared shards."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


LABELS = {"ADMIT", "REJECT", "AMBIGUOUS"}
ALIGNMENTS = {"YES", "NO", "UNCLEAR"}
USABILITY = {"USABLE", "NOT_USABLE", "UNCLEAR"}
REQUIRED = {"review_id", "label", "a_star_alignment", "candidate_usability", "reasons", "note"}


def read_jsonl(path: Path):
    with path.open(encoding="utf8") as fh:
        for line_no, line in enumerate(fh, 1):
            if line.strip():
                try:
                    yield line_no, json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("shard_dir", type=Path)
    ap.add_argument("annotations", type=Path)
    ap.add_argument("--allow-partial", action="store_true")
    args = ap.parse_args()
    expected = set()
    for shard in sorted(args.shard_dir.glob("shard-*.jsonl")):
        expected.update(row["review_id"] for _, row in read_jsonl(shard))
    if not expected:
        raise SystemExit("no input rows found")
    seen, errors, labels = set(), [], Counter()
    for line_no, row in read_jsonl(args.annotations):
        missing = REQUIRED - row.keys()
        if missing:
            errors.append(f"line {line_no}: missing fields {sorted(missing)}")
            continue
        rid = row["review_id"]
        if rid in seen:
            errors.append(f"line {line_no}: duplicate review_id {rid}")
        seen.add(rid)
        if rid not in expected:
            errors.append(f"line {line_no}: review_id is not in input {rid}")
        if row["label"] not in LABELS:
            errors.append(f"line {line_no}: invalid label")
        if row["a_star_alignment"] not in ALIGNMENTS:
            errors.append(f"line {line_no}: invalid a_star_alignment")
        if row["candidate_usability"] not in USABILITY:
            errors.append(f"line {line_no}: invalid candidate_usability")
        if not isinstance(row["reasons"], list) or not all(isinstance(x, str) for x in row["reasons"]):
            errors.append(f"line {line_no}: reasons must be a string list")
        if not isinstance(row["note"], str):
            errors.append(f"line {line_no}: note must be a string")
        labels[row["label"]] += 1
    missing = expected - seen
    if missing and not args.allow_partial:
        errors.append(f"missing {len(missing)} input IDs")
    report = {
        "expected_rows": len(expected),
        "annotated_rows": len(seen),
        "missing_rows": len(missing),
        "label_counts": dict(labels),
        "valid": not errors,
        "errors": errors[:100],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
