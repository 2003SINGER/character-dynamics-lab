#!/usr/bin/env python3
"""Export development-only behavior-audit cases without scoring candidate quality.

This is failure mining, not an optimizer objective.  It reads only the frozen
``optimizer_train`` seed set, ranks descriptive screening signals, and exports
the complete selected trajectories so a reviewer can decide whether a signal
is a real pathology, a reasonable contextual behavior, or a false alarm.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


STUDY_PROBABILITY_COLUMNS = (
    "p_study_at_computer",
    "p_study_focused",
    "p_study_halfhearted",
)


def number(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, ""))
    except ValueError:
        return 0.0


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"missing CSV header: {path}")
        return list(reader), reader.fieldnames


def longest_run(rows: list[dict[str, str]], predicate) -> tuple[int, int, int, str]:
    best = (0, 0, 0, "")
    current = 0
    start = 0
    action = ""
    for index, row in enumerate(rows):
        if predicate(row):
            if current == 0:
                start, action = index, row["chosen_action"]
            current += 1
            if current > best[0]:
                best = (current, start, index, action)
        else:
            current = 0
    return best


def longest_same_action_run(rows: list[dict[str, str]]) -> tuple[int, int, int, str]:
    best = (0, 0, 0, "")
    current = 0
    start = 0
    previous = None
    for index, row in enumerate(rows):
        action = row["chosen_action"]
        if action == previous:
            current += 1
        else:
            current, start, previous = 1, index, action
        if current > best[0]:
            best = (current, start, index, action)
    return best


def longest_stagnation(rows: list[dict[str, str]]) -> tuple[int, int, int]:
    best = (0, 0, 0)
    current = 0
    start = 0
    for index, row in enumerate(rows):
        active = row.get("pre_task_status") == "active"
        gained = number(row, "outcome_task_effort_gained") > 0.0
        if active and not gained:
            if current == 0:
                start = index
            current += 1
            if current > best[0]:
                best = (current, start, index)
        else:
            current = 0
    return best


@dataclass
class Case:
    category: str
    key: tuple[str, str]
    score: float
    start: int
    end: int
    note: str
    tags: set[str] = field(default_factory=set)


def select_cases(groups: dict[tuple[str, str], list[dict[str, str]]], per_category: int,
                 need_threshold: float, pressure_threshold: float,
                 study_probability_threshold: float) -> list[Case]:
    pools: dict[str, list[Case]] = defaultdict(list)
    for key, rows in groups.items():
        zero = longest_run(rows, lambda r: number(r, "elapsed_minutes") == 0.0)
        if zero[0] >= 2:
            pools["zero_time_loop"].append(Case(
                "zero_time_loop", key, zero[0], zero[1], zero[2],
                f"{zero[0]} consecutive zero-minute decisions; action={zero[3]}",
            ))
        same = longest_same_action_run(rows)
        if same[0] >= 2:
            pools["same_action_run"].append(Case(
                "same_action_run", key, same[0], same[1], same[2],
                f"{same[0]} consecutive {same[3]} decisions; inspect elapsed time and context",
            ))
        for state, action, category in (
            ("pre_hunger", "get_meal", "high_hunger_nonmeal"),
            ("pre_bathroom_urge", "go_to_bathroom", "high_bathroom_nonvisit"),
        ):
            hits = [index for index, row in enumerate(rows)
                    if number(row, state) >= need_threshold and row["chosen_action"] != action]
            if hits:
                pools[category].append(Case(
                    category, key, len(hits), hits[0], hits[-1],
                    f"{len(hits)} screened steps where {state}>={need_threshold} without {action}; not a penalty",
                ))
        low_study = [index for index, row in enumerate(rows)
                     if row.get("pre_task_status") == "active"
                     and number(row, "pre_task_pressure") >= pressure_threshold
                     and sum(number(row, column) for column in STUDY_PROBABILITY_COLUMNS)
                     < study_probability_threshold]
        if low_study:
            pools["high_pressure_low_study"].append(Case(
                "high_pressure_low_study", key, len(low_study), low_study[0], low_study[-1],
                "task pressure is high while study probability is low; inspect information and bodily context",
            ))
        stagnation = longest_stagnation(rows)
        if stagnation[0] >= 2:
            pools["active_task_stagnation"].append(Case(
                "active_task_stagnation", key, stagnation[0], stagnation[1], stagnation[2],
                "active task has consecutive no-effort decisions; inspect whether this is recovery or a lock",
            ))
        suspended = longest_run(rows, lambda r: r.get("pre_commitment_status") == "suspended")
        if suspended[0] >= 2:
            pools["commitment_suspension"].append(Case(
                "commitment_suspension", key, suspended[0], suspended[1], suspended[2],
                "long suspended commitment segment; inspect resumption, completion, and need context",
            ))

    merged: dict[tuple[str, str], Case] = {}
    for category, candidates in pools.items():
        for candidate in sorted(candidates, key=lambda x: (-x.score, x.key))[:per_category]:
            old = merged.get(candidate.key)
            if old is None:
                candidate.tags.add(category)
                merged[candidate.key] = candidate
            else:
                old.tags.add(category)
                if candidate.score > old.score:
                    old.score, old.start, old.end, old.note = (
                        candidate.score, candidate.start, candidate.end, candidate.note)
    return sorted(merged.values(), key=lambda x: (-len(x.tags), -x.score, x.key))


def compact_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "step": int(row["step"]), "time": row["decision_time"],
        "action": row["chosen_action"], "elapsed_minutes": number(row, "elapsed_minutes"),
        "event_ids": row.get("event_ids", ""),
        "S_pre": {key.removeprefix("pre_"): number(row, key) for key in row if key.startswith("pre_")},
        "O_known_actions": {key.removeprefix("known_"): row[key] == "1" for key in row if key.startswith("known_")},
        "pi": {key.removeprefix("p_"): number(row, key) for key in row if key.startswith("p_")},
        "outcome": {
            "accepted": row.get("accepted"), "failure_reason": row.get("failure_reason"),
            "task_effort_gained": number(row, "outcome_task_effort_gained"),
            "task_status": row.get("post_task_status"),
            "commitment": row.get("post_commitment_status"),
        },
    }


def write_casebook(cases: Iterable[Case], groups: dict[tuple[str, str], list[dict[str, str]]],
                   fields: list[str], out: Path, source: Path, args) -> None:
    out.mkdir(parents=True, exist_ok=True)
    traces = out / "traces"
    traces.mkdir(exist_ok=True)
    records = []
    markdown = [
        "# Behavior audit casebook v0", "",
        "Scope: development-only failure mining. This is not a pre-registered objective,",
        "not a candidate ranking, and not evidence of naturalness or psychological validity.", "",
        f"- source: `{source}`",
        "- split: `optimizer_train` only; holdout was not read",
        f"- screeners: need >= {args.need_threshold}; task pressure >= {args.pressure_threshold}; study probability < {args.study_probability_threshold}",
        "- `deadline_remaining` is absent from this batch: no deadline-response screener is produced.", "",
        "## Cases", "",
        "| id | personality / seed | screening tags | score | highlighted span | trace |", "| --- | --- | --- | ---: | --- | --- |",
    ]
    for index, case in enumerate(cases, 1):
        rows = groups[case.key]
        case_id = f"case-{index:03d}"
        trace_name = f"{case_id}_p{case.key[0]}_s{case.key[1]}.csv"
        with (traces / trace_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        context_lo, context_hi = max(0, case.start - 3), min(len(rows) - 1, case.end + 3)
        records.append({
            "case_id": case_id, "personality_index": case.key[0], "scenario_seed": case.key[1],
            "screening_tags": sorted(case.tags), "screening_score": case.score,
            "highlighted_step_span": [int(rows[case.start]["step"]), int(rows[case.end]["step"])],
            "note": case.note, "full_trace": f"traces/{trace_name}",
            "context": [compact_row(row) for row in rows[context_lo:context_hi + 1]],
            "review_status": "unreviewed",
        })
        markdown.append(
            f"| {case_id} | {case.key[0]} / {case.key[1]} | {', '.join(sorted(case.tags))} | "
            f"{case.score:g} | {rows[case.start]['step']}–{rows[case.end]['step']} | `traces/{trace_name}` |"
        )
    (out / "cases.json").write_text(json.dumps({
        "schema_version": "behavior_audit_casebook_v0", "purpose": "development failure mining only",
        "source_trajectory_csv": str(source), "holdout_read": False,
        "deadline_response_screening": "not_available: deadline_remaining is absent", "cases": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown.extend(["", "## Reviewer rule", "", "A screening tag is not a pathology label. For every case, record whether it is a true positive, true negative, false positive, or false negative before proposing a candidate metric."])
    (out / "casebook.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-category", type=int, default=10)
    parser.add_argument("--need-threshold", type=float, default=0.8)
    parser.add_argument("--pressure-threshold", type=float, default=0.8)
    parser.add_argument("--study-probability-threshold", type=float, default=0.12)
    args = parser.parse_args()
    rows, fields = read_rows(args.trajectories)
    manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    permitted = {str(seed) for seed in manifest["optimizer_train_world_seeds"]}
    observed = {row["scenario_seed"] for row in rows}
    if not observed or not observed <= permitted:
        raise ValueError("trajectory CSV is not confined to frozen optimizer_train seeds")
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["personality_index"], row["scenario_seed"])].append(row)
    for group in groups.values():
        group.sort(key=lambda row: int(row["step"]))
    cases = select_cases(groups, args.per_category, args.need_threshold, args.pressure_threshold,
                         args.study_probability_threshold)
    write_casebook(cases, groups, fields, args.out, args.trajectories, args)
    print(json.dumps({"case_count": len(cases), "trajectory_count": len(groups), "holdout_read": False}))


if __name__ == "__main__":
    main()
