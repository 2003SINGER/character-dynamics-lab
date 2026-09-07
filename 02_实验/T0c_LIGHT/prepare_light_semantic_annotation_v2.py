#!/usr/bin/env python3
"""Build blinded, trajectory-isolated source-only LIGHT annotation inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path


SCHEMA = "character_dynamics_light_semantic_annotation_v2"
SEED = 20260907
ALLOWED_INPUT_FIELDS = (
    "review_id", "actor", "source_O", "source_action_A_star", "candidate_set_factual",
)


def load_rows(path: Path):
    grouped: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf8") as fh:
        for rec in map(json.loads, fh):
            if (rec.get("source_episode_context") or {}).get("quarantine"):
                continue
            trajectory_id = str(rec["trajectory_id"])
            for ordinal, step in enumerate(rec.get("steps") or []):
                step_ctx = step.get("source_step_context") or {}
                actor = step_ctx.get("actor")
                action = step.get("source_action_A_star")
                candidates = step.get("candidate_set_factual")
                if not actor or not action or not isinstance(candidates, list) or not candidates:
                    continue
                source_id = f"{trajectory_id}::i{ordinal}"
                grouped[trajectory_id].append({
                    "source_id": source_id,
                    "trajectory_id": trajectory_id,
                    "source_ordinal": ordinal,
                    "actor": actor,
                    "source_O": step.get("source_O") or "",
                    "source_action_A_star": action,
                    "candidate_set_factual": candidates,
                })
    return grouped


def isolate_into_shards(grouped, rows_per_shard: int, seed: int):
    """Each returned shard has at most one row from any trajectory."""
    rng = random.Random(seed)
    queues = {tid: list(rows) for tid, rows in grouped.items()}
    for queue in queues.values():
        rng.shuffle(queue)
    shards = []
    while any(queues.values()):
        active = [tid for tid, queue in queues.items() if queue]
        rng.shuffle(active)
        chosen = []
        for tid in active[:rows_per_shard]:
            chosen.append(queues[tid].pop())
        if len({row["trajectory_id"] for row in chosen}) != len(chosen):
            raise AssertionError("trajectory collision in reviewer task")
        shards.append(chosen)
    return shards


def opaque_id(source_id: str, secret: str):
    return "r2-" + hashlib.sha256((secret + "\0" + source_id).encode()).hexdigest()[:24]


def direct_object(action: str):
    """Conservative lexical selector for calibration rows, never shown to reviewer."""
    action = action.strip().casefold()
    for verb, delimiter in (("steal ", " from "), ("give ", " to "), ("put ", " in ")):
        if action.startswith(verb) and delimiter in action:
            return action[len(verb):].split(delimiter, 1)[0].strip()
    for verb in ("get ", "drop ", "wear ", "remove ", "drink ", "eat "):
        if action.startswith(verb):
            return action[len(verb):].strip()
    return ""


def calibration_rows(grouped, total: int, unobserved_count: int, seed: int):
    rng = random.Random(seed)
    flat = [row for rows in grouped.values() for row in rows]
    likely = [row for row in flat if (obj := direct_object(str(row["source_action_A_star"]))) and obj not in str(row["source_O"]).casefold()]
    rng.shuffle(likely)
    selected, selected_trajectories = [], set()
    for row in likely:
        if row["trajectory_id"] not in selected_trajectories:
            selected.append(row)
            selected_trajectories.add(row["trajectory_id"])
            if len(selected) == unobserved_count:
                break
    if len(selected) != unobserved_count:
        raise ValueError("not enough trajectory-distinct lexical calibration rows")
    remainder = [row for row in flat if row["trajectory_id"] not in selected_trajectories]
    rng.shuffle(remainder)
    for row in remainder:
        if row["trajectory_id"] not in selected_trajectories:
            selected.append(row)
            selected_trajectories.add(row["trajectory_id"])
            if len(selected) == total:
                break
    if len(selected) != total:
        raise ValueError("not enough trajectory-distinct calibration rows")
    rng.shuffle(selected)
    return [selected[start:start + 20] for start in range(0, total, 20)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--rows-per-shard", type=int, default=20)
    ap.add_argument("--limit-shards", type=int, default=None)
    ap.add_argument("--calibration-unobserved-rows", type=int, default=0, help="build a 3x20 lexical support calibration set")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--opaque-secret", required=True, help="kept out of reviewer-visible files")
    args = ap.parse_args()
    if args.rows_per_shard < 1:
        raise SystemExit("rows-per-shard must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    shards_dir = args.output_dir / "reviewer_input_shards"
    shards_dir.mkdir(exist_ok=True)
    grouped = load_rows(args.replay)
    if args.calibration_unobserved_rows:
        if args.rows_per_shard != 20 or args.limit_shards not in (None, 3) or not 0 < args.calibration_unobserved_rows < 60:
            raise SystemExit("calibration mode requires --rows-per-shard 20, exactly 3 tasks, and 1..59 unobserved rows")
        shards = calibration_rows(grouped, 60, args.calibration_unobserved_rows, args.seed)
    else:
        shards = isolate_into_shards(grouped, args.rows_per_shard, args.seed)
    if args.limit_shards is not None:
        shards = shards[:args.limit_shards]
    mapping, review_ids = [], set()
    for index, source_rows in enumerate(shards, 1):
        payload_rows = []
        task_trajectories = set()
        for row in source_rows:
            review_id = opaque_id(row["source_id"], args.opaque_secret)
            if review_id in review_ids:
                raise AssertionError("opaque ID collision")
            review_ids.add(review_id)
            task_trajectories.add(row["trajectory_id"])
            payload_rows.append({field: row[field] if field != "review_id" else review_id for field in ALLOWED_INPUT_FIELDS})
            mapping.append({"review_id": review_id, **row, "shard": f"task-{index:04d}.jsonl"})
        if len(task_trajectories) != len(payload_rows):
            raise AssertionError("trajectory repeated in task")
        task_path = shards_dir / f"task-{index:04d}.jsonl"
        with task_path.open("w", encoding="utf8") as fh:
            for payload in payload_rows:
                if tuple(payload) != ALLOWED_INPUT_FIELDS:
                    raise AssertionError("reviewer payload leaked a disallowed field")
                fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    # Mapping is explicitly local-only and must never be supplied to a reviewer.
    mapping_path = args.output_dir / "private_review_mapping.jsonl"
    with mapping_path.open("w", encoding="utf8") as fh:
        for row in mapping:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    protocol_path = args.output_dir / "protocol_v2.md"
    protocol_path.write_text(PROTOCOL, encoding="utf8")
    source_hash = hashlib.sha256(args.replay.read_bytes()).hexdigest()
    task_names = [f"task-{i:04d}.jsonl" for i in range(1, len(shards) + 1)]
    manifest = {
        "schema_version": SCHEMA,
        "source_replay_sha256": source_hash,
        "selection_seed": args.seed,
        "reviewer_input_fields": list(ALLOWED_INPUT_FIELDS),
        "opaque_id": True,
        "private_mapping": mapping_path.name,
        "rows_per_task": args.rows_per_shard,
        "task_count": len(task_names),
        "row_count": len(mapping),
        "tasks": task_names,
        "trajectory_unique_per_task": True,
        "calibration_unobserved_rows": args.calibration_unobserved_rows,
        "excluded_from_reviewer_input": ["trajectory_id", "episode_id", "step_index", "t", "previous_step", "future_step", "source_episode_context", "model_results", "other_reviewer_outputs"],
    }
    (args.output_dir / "manifest_v2.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"rows": len(mapping), "tasks": len(task_names), "output_dir": str(args.output_dir)}, ensure_ascii=False))


PROTOCOL = r'''# LIGHT v2 row-level source semantic consistency annotation

## Isolation rule

You may use only the fields on the current JSONL row: opaque `review_id`,
`actor`, `source_O`, `source_action_A_star`, and `candidate_set_factual`.
Do not infer a trajectory, time, previous/future state, hidden world state,
model result, or another reviewer’s judgment. A target absent from `source_O`
is not evidence that it is impossible: ownership, visibility, and inventory may
be unobserved.

## Axes and row label

First label the three required axes. Then choose the row label by the rule
below; do not use personal or narrative plausibility to create extra evidence.

- `a_star_alignment = YES`: A* has the same action semantics as one candidate
  **and** its required visible actor, entity, possession, and relation are
  directly supported by `source_O`. `NO`: no candidate has that action
  semantics or the row explicitly contradicts it. `UNCLEAR`: A* is a candidate
  but `source_O` does not establish a needed entity, possession, target, or
  relation. Do not infer another character's inventory.
- `candidate_usability = USABLE`: visible evidence supports comparing the
  candidates as an observed-source candidate task. `NOT_USABLE`: the list is
  explicitly malformed, self-contradictory, or cannot define alternatives.
  `UNCLEAR`: material candidates depend on entities, ownership, visibility, or
  relations not established by `source_O`.
- `ADMIT`: `a_star_alignment = YES`, `candidate_usability = USABLE`, and no
  explicit actor, action, or source contradiction.
- `REJECT`: only for explicit contradiction, malformed action, explicit
  actor-action impossibility, action/candidate semantic mismatch, or clearly
  unusable candidates. Absence from `source_O` alone is never a rejection.
- `AMBIGUOUS`: either axis is `UNCLEAR`, including entity absence,
  underspecified relation, unclear actor ownership/visibility, or uncertain
  semantic equivalence. If in doubt between `REJECT` and `AMBIGUOUS`, choose
  `AMBIGUOUS`.

## Controlled reason codes

Use zero or more of only:

`ACTION_CANDIDATE_MISMATCH`, `ACTOR_ACTION_CONTRADICTION`,
`MALFORMED_ACTION`, `CANDIDATE_SEMANTIC_CONTRADICTION`,
`CANDIDATE_SET_MALFORMED`, `ENTITY_RELATION_UNCLEAR`,
`ACTOR_VISIBILITY_OR_OWNERSHIP_UNCLEAR`, `OBSERVATION_INSUFFICIENT`,
`ACTION_ENTITY_OR_RELATION_UNOBSERVED`.

## Output JSONL

Return exactly one JSON object per input row, with exactly these fields:

```json
{"review_id":"r2-...","label":"ADMIT|REJECT|AMBIGUOUS","a_star_alignment":"YES|NO|UNCLEAR","candidate_usability":"USABLE|NOT_USABLE|UNCLEAR","reasons":["CONTROLLED_CODE"],"note":"brief source-grounded explanation"}
```

Do not add fields. Process one task at a time and checkpoint after each task.
'''


if __name__ == "__main__":
    main()
