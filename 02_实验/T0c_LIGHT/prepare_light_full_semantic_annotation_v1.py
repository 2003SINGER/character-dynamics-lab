#!/usr/bin/env python3
"""Prepare source-only, resumable LIGHT full semantic-annotation shards.

The reviewer receives only compact current-step evidence. Previous/future steps,
model results, and old reviewer outputs are deliberately excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "character_dynamics_light_full_semantic_annotation_input_v1"


def rows_from_replay(path: Path):
    with path.open(encoding="utf8") as fh:
        for rec in map(json.loads, fh):
            episode_ctx = rec.get("source_episode_context") or {}
            if episode_ctx.get("quarantine"):
                continue
            for index, step in enumerate(rec.get("steps") or []):
                sc = step.get("source_step_context") or {}
                action = step.get("source_action_A_star")
                candidates = step.get("candidate_set_factual")
                actor = sc.get("actor")
                if not actor or not action or not isinstance(candidates, list) or not candidates:
                    continue
                yield {
                    "review_id": f"{rec['trajectory_id']}::t{index}",
                    "trajectory_id": str(rec["trajectory_id"]),
                    "episode_id": str(rec.get("source_record_id", rec["trajectory_id"])),
                    "step_index": index,
                    "t": step.get("t"),
                    "actor": actor,
                    "source_O": step.get("source_O") or "",
                    "source_action_A_star": action,
                    "candidate_set_factual": candidates,
                    "deterministic_checks": {
                        "actor_present": True,
                        "candidate_nonempty": True,
                        "a_star_exact_membership": action in candidates,
                        "a_star_casefold_membership": any(str(action).casefold() == str(c).casefold() for c in candidates),
                        "quarantine": False,
                    },
                }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--rows-per-shard", type=int, default=50)
    ap.add_argument("--limit", type=int, default=None, help="optional smoke-test row limit")
    args = ap.parse_args()
    if args.rows_per_shard < 1:
        raise SystemExit("--rows-per-shard must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    shard_dir = args.output_dir / "shards"
    shard_dir.mkdir(exist_ok=True)
    rows = []
    for row in rows_from_replay(args.replay):
        rows.append(row)
        if args.limit and len(rows) >= args.limit:
            break
    if not rows:
        raise SystemExit("no eligible rows")
    # Fail closed on duplicate IDs before writing any shard.
    ids = [r["review_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate review_id")
    for old in shard_dir.glob("shard-*.jsonl"):
        old.unlink()
    shard_names = []
    for start in range(0, len(rows), args.rows_per_shard):
        chunk = rows[start:start + args.rows_per_shard]
        name = f"shard-{start // args.rows_per_shard + 1:04d}.jsonl"
        with (shard_dir / name).open("w", encoding="utf8") as fh:
            for row in chunk:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        shard_names.append(name)
    protocol = args.output_dir / "protocol.md"
    protocol.write_text(PROTOCOL, encoding="utf8")
    manifest = {
        "schema_version": SCHEMA,
        "source_replay": str(args.replay),
        "source_sha256": hashlib.sha256(args.replay.read_bytes()).hexdigest(),
        "eligible_row_count": len(rows),
        "rows_per_shard": args.rows_per_shard,
        "shard_count": len(shard_names),
        "shards": shard_names,
        "input_excludes": ["previous_step", "future_step", "model_results", "other_reviewer_outputs", "old_reviewed_50"],
        "output_schema": {"review_id": "string", "label": "ADMIT|REJECT|AMBIGUOUS", "a_star_alignment": "YES|NO|UNCLEAR", "candidate_usability": "USABLE|NOT_USABLE|UNCLEAR", "reasons": "array[string]", "note": "string"},
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"rows": len(rows), "shards": len(shard_names), "output_dir": str(args.output_dir)}, ensure_ascii=False))


PROTOCOL = r'''# LIGHT full semantic annotation — independent reviewer protocol

This is a source-only annotation task over sharded LIGHT rows. Process one input
shard per isolated task. Do not open the repository or any other reviewer’s
directory. Do not use Run 1–4 results, model outputs, old blind-50 reviews, or
future/previous step context.

## Input boundary

Use only the current row’s `actor`, `source_O`, `source_action_A_star`, and
`candidate_set_factual`. `deterministic_checks` are mechanical facts, not a
semantic verdict. The candidate list is an observed source list; do not assume
it is the actor-known set `A^O`.

## Required output

Append exactly one compact JSON object per input row to the reviewer’s output
JSONL, preserving `review_id` exactly:

```json
{"review_id":"...","label":"ADMIT|REJECT|AMBIGUOUS","a_star_alignment":"YES|NO|UNCLEAR","candidate_usability":"USABLE|NOT_USABLE|UNCLEAR","reasons":[],"note":"..."}
```

Use `AMBIGUOUS` or `UNCLEAR` when the source evidence is insufficient; never
force a decision. Reasons should identify only observed problems, such as actor
or turn mismatch, action/candidate mismatch, unclear actor action, observation
boundary uncertainty, or malformed/underspecified action semantics.

## Checkpointing

Validate that every input `review_id` appears exactly once before marking a
shard complete. Append the shard result to durable storage immediately; a
failed later shard must not erase earlier output. The merge step must reject
duplicate or missing IDs.

No aggregate admission claim is valid until all shards and all independent
reviewers have been merged and disagreements queued for adjudication.
'''


if __name__ == "__main__":
    main()
