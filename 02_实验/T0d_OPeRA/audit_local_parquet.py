#!/usr/bin/env python3
"""Audit a local, pinned OPeRA filtered release without storing browser content."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean, median

import pandas as pd


REVISION = "6f26a2c5cc69084f1714e39db9776e61791344d6"
ACTION_COLUMNS = [
    "session_id", "action_id", "timestamp", "action_type", "click_type", "semantic_id",
    "url", "simplified_html", "rationale", "input_text",
]


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def read_actions(raw: Path, split: str) -> pd.DataFrame:
    paths = sorted(raw.glob(f"{split}-*.parquet"))
    if not paths:
        raise FileNotFoundError(f"no {split} action parquet in {raw}")
    frame = pd.concat([pd.read_parquet(path, columns=ACTION_COLUMNS) for path in paths], ignore_index=True)
    frame["split"] = split
    return frame


def read_sessions(raw: Path, split: str) -> pd.DataFrame:
    path = raw / f"session-{split}.parquet"
    frame = pd.read_parquet(path, columns=["session_id", "user_id", "action_count"])
    frame["split"] = split
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()

    sessions = pd.concat([read_sessions(args.raw_dir, "train"), read_sessions(args.raw_dir, "test")])
    actions = pd.concat([read_actions(args.raw_dir, "train"), read_actions(args.raw_dir, "test")])
    sessions["rank"] = sessions.session_id.map(lambda value: hashlib.sha256(value.encode()).hexdigest())
    selected = sessions.sort_values(["rank", "session_id"]).head(args.count).copy()
    records = []
    total_types: Counter[str] = Counter()
    total_clicks: Counter[str] = Counter()

    for row in selected.itertuples(index=False):
        group = actions[(actions.session_id == row.session_id) & (actions.split == row.split)].copy()
        group = group.sort_values("timestamp", kind="stable")
        timestamps = group.timestamp.astype(str).tolist()
        type_counts = Counter(group.action_type.astype(str).tolist())
        click_values = [str(value) for value in group["click_type"].tolist()]
        click_counts = Counter(value for value in click_values if value and value.lower() != "nan")
        rationale_indices = [
            index for index, value in enumerate(group.rationale.tolist()) if present(value)
        ]
        complete_o = [present(html) and present(url) for html, url in zip(group.simplified_html, group.url)]
        records.append({
            "split": row.split,
            "session_sha256_16": short_hash(row.session_id),
            "user_sha256_16": short_hash(row.user_id),
            "declared_action_count": int(row.action_count),
            "retrieved_action_count": len(group),
            "count_matches_session_table": len(group) == int(row.action_count),
            "timestamps_non_decreasing": timestamps == sorted(timestamps),
            "unique_action_ids": group.action_id.nunique() == len(group),
            "nonempty_html_and_url_count": sum(complete_o),
            "action_type_counts": dict(sorted(type_counts.items(), key=lambda item: str(item[0]))),
            "click_type_counts": dict(sorted(click_counts.items(), key=lambda item: str(item[0]))),
            "semantic_id_count": int(sum(present(value) for value in group.semantic_id.tolist())),
            "rationale_step_indices": rationale_indices,
            "rationale_count": len(rationale_indices),
        })
        total_types.update(type_counts)
        total_clicks.update(click_counts)

    train_users = set(sessions[sessions.split == "train"].user_id)
    test_users = set(sessions[sessions.split == "test"].user_id)
    counts = [record["retrieved_action_count"] for record in records]
    summary = {
        "session_count": len(records),
        "action_count_min": min(counts), "action_count_median": median(counts),
        "action_count_mean": mean(counts), "action_count_max": max(counts),
        "session_count_matches": sum(record["count_matches_session_table"] for record in records),
        "session_timestamps_non_decreasing": sum(record["timestamps_non_decreasing"] for record in records),
        "session_unique_action_ids": sum(record["unique_action_ids"] for record in records),
        "session_complete_html_and_url": sum(
            record["nonempty_html_and_url_count"] == record["retrieved_action_count"] for record in records
        ),
        "action_type_counts": dict(sorted(total_types.items(), key=lambda item: str(item[0]))),
        "click_type_counts": dict(sorted(total_clicks.items(), key=lambda item: str(item[0]))),
        "rationale_step_count": sum(record["rationale_count"] for record in records),
        "sessions_with_rationale": sum(bool(record["rationale_count"]) for record in records),
    }
    manifest = {
        "purpose": "T0d OPeRA 30-session feasibility audit; not training, a baseline, or Paper-0 evidence",
        "source": {"dataset": "NEU-HAI/OPeRA", "revision": REVISION, "license": "CC-BY-4.0"},
        "sample_method": "lowest SHA-256 rank of filtered session_id across train/test; deterministic, not stratified",
        "session_table": {
            "train_sessions": int(sum(sessions.split == "train")), "test_sessions": int(sum(sessions.split == "test")),
            "train_users": len(train_users), "test_users": len(test_users),
            "cross_split_user_overlap": len(train_users & test_users),
        },
        "sample_summary": summary,
        "interpretation_boundary": {
            "finite_label_space": "action_type and click_type are finite observed labels; exact target/semantic_id is not a per-step enumerated candidate set.",
            "rationale_timing": "rationale is action-row-aligned but lacks a separately timestamped pre-action elicitation event; it cannot be an input without a new causal protocol.",
            "split": "existing train/test has user overlap; formal evaluation must use an explicit user/session grouping policy.",
        },
        "records": records,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
