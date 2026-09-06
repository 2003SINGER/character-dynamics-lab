#!/usr/bin/env python3
"""Run a deterministic, read-only T0d feasibility audit against OPeRA.

The script reads only Hugging Face's dataset-server API. It never downloads
images, trains a model, alters OPeRA, or writes raw user/browser content. Its
JSON output is limited to hashed IDs and structural diagnostics.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from statistics import mean, median
import time
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


DATASET = "NEU-HAI/OPeRA"
DATASET_REVISION = "6f26a2c5cc69084f1714e39db9776e61791344d6"
BASE = "https://datasets-server.huggingface.co"
CONFIG = "filtered_action"
SESSION_CONFIG = "filtered_session"


def request_json(url: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urlopen(url, timeout=90) as response:  # nosec B310: fixed HTTPS API
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # transient public API/TLS failures
            last_error = error
            if attempt < 3:
                time.sleep(1 + attempt)
    raise RuntimeError(f"datasets-server request failed after four attempts: {url}") from last_error


def rows(config: str, split: str, offset: int, length: int) -> list[dict[str, Any]]:
    url = f"{BASE}/rows?dataset={quote(DATASET, safe='')}&config={config}&split={split}&offset={offset}&length={length}"
    return [item["row"] for item in request_json(url).get("rows", [])]


def all_sessions(split: str) -> list[dict[str, Any]]:
    first = request_json(
        f"{BASE}/rows?dataset={quote(DATASET, safe='')}&config={SESSION_CONFIG}&split={split}&offset=0&length=100"
    )
    total = int(first["num_rows_total"])
    result = [item["row"] for item in first["rows"]]
    for offset in range(100, total, 100):
        result.extend(rows(SESSION_CONFIG, split, offset, min(100, total - offset)))
    if len(result) != total:
        raise RuntimeError(f"{split}: fetched {len(result)} session records, expected {total}")
    return result


def session_actions(split: str, session_id: str) -> list[dict[str, Any]]:
    where = quote(f'"session_id" = \'{session_id}\'', safe="")
    url = (
        f"{BASE}/filter?dataset={quote(DATASET, safe='')}&config={CONFIG}&split={split}"
        f"&where={where}&offset=0&length=100"
    )
    return [item["row"] for item in request_json(url).get("rows", [])]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def audit_session(split: str, session: dict[str, Any]) -> dict[str, Any]:
    actions = session_actions(split, session["session_id"])
    timestamps = [action.get("timestamp") for action in actions]
    action_types = Counter(str(action.get("action_type", "")) for action in actions)
    click_types = Counter(
        str(action.get("click_type")) for action in actions
        if nonempty(action.get("click_type"))
    )
    semantic_ids = Counter(
        str(action.get("semantic_id")) for action in actions
        if nonempty(action.get("semantic_id"))
    )
    rationales = [index for index, action in enumerate(actions) if nonempty(action.get("rationale"))]
    observation_complete = [
        nonempty(action.get("simplified_html")) and nonempty(action.get("url"))
        for action in actions
    ]
    # ISO-8601 timestamps sort lexically. Equal timestamps are retained: their
    # order needs an explicit audit flag rather than an invented reordering.
    ordered = timestamps == sorted(timestamps)
    unique_action_ids = len({action.get("action_id") for action in actions}) == len(actions)
    return {
        "split": split,
        "session_sha256_16": digest(session["session_id"]),
        "user_sha256_16": digest(session["user_id"]),
        "declared_action_count": session.get("action_count"),
        "retrieved_action_count": len(actions),
        "count_matches_session_table": len(actions) == session.get("action_count"),
        "timestamps_non_decreasing": ordered,
        "unique_action_ids": unique_action_ids,
        "nonempty_html_and_url_count": sum(observation_complete),
        "action_type_counts": dict(sorted(action_types.items())),
        "click_type_counts": dict(sorted(click_types.items())),
        "semantic_id_count": len(semantic_ids),
        "rationale_step_indices": rationales,
        "rationale_count": len(rationales),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()
    if args.count < 1:
        raise ValueError("--count must be positive")

    sessions_by_split = {split: all_sessions(split) for split in ("train", "test")}
    all_session_rows = [
        {**row, "split": split} for split, split_rows in sessions_by_split.items() for row in split_rows
    ]
    if len(all_session_rows) < args.count:
        raise RuntimeError("not enough sessions for requested audit")
    selected = sorted(
        all_session_rows,
        key=lambda row: (hashlib.sha256(row["session_id"].encode("utf-8")).hexdigest(), row["session_id"]),
    )[:args.count]
    # The public API is read-only but a per-session request can be slow. Keep
    # bounded parallelism so the sample remains deterministic while avoiding a
    # half-hour sequential audit.
    with ThreadPoolExecutor(max_workers=6) as executor:
        records = list(executor.map(lambda row: audit_session(row["split"], row), selected))

    train_users = {row["user_id"] for row in sessions_by_split["train"]}
    test_users = {row["user_id"] for row in sessions_by_split["test"]}
    all_action_types = Counter()
    all_click_types = Counter()
    action_counts = []
    observation_complete_sessions = 0
    count_match_sessions = 0
    ordered_sessions = 0
    unique_id_sessions = 0
    for record in records:
        all_action_types.update(record["action_type_counts"])
        all_click_types.update(record["click_type_counts"])
        action_counts.append(record["retrieved_action_count"])
        observation_complete_sessions += record["nonempty_html_and_url_count"] == record["retrieved_action_count"]
        count_match_sessions += record["count_matches_session_table"]
        ordered_sessions += record["timestamps_non_decreasing"]
        unique_id_sessions += record["unique_action_ids"]

    manifest = {
        "purpose": "T0d OPeRA 30-session data feasibility audit; not a model run or Paper-0 result",
        "source": {
            "dataset": DATASET,
            "dataset_revision": DATASET_REVISION,
            "license": "CC-BY-4.0",
            "access_method": "Hugging Face datasets-server API; filtered_session and filtered_action configs",
        },
        "sample_method": "lowest SHA-256 rank of session_id across filtered train/test session tables; deterministic, not stratified",
        "session_table": {
            "train_sessions": len(sessions_by_split["train"]),
            "test_sessions": len(sessions_by_split["test"]),
            "train_users": len(train_users),
            "test_users": len(test_users),
            "cross_split_user_overlap": len(train_users & test_users),
        },
        "sample_summary": {
            "session_count": len(records),
            "action_count_min": min(action_counts),
            "action_count_median": median(action_counts),
            "action_count_mean": mean(action_counts),
            "action_count_max": max(action_counts),
            "session_count_matches": count_match_sessions,
            "session_timestamps_non_decreasing": ordered_sessions,
            "session_unique_action_ids": unique_id_sessions,
            "session_complete_html_and_url": observation_complete_sessions,
            "action_type_counts": dict(sorted(all_action_types.items())),
            "click_type_counts": dict(sorted(all_click_types.items())),
            "rationale_step_count": sum(record["rationale_count"] for record in records),
            "sessions_with_rationale": sum(bool(record["rationale_count"]) for record in records),
        },
        "interpretation_boundary": {
            "finite_label_space": "action_type and click_type are finite observed label spaces in this slice; exact UI targets are open-world strings/semantic IDs, not a per-step enumerated candidate set.",
            "rationale_timing": "rationale shares an action row but the release does not expose a separately timestamped pre-action elicitation event; do not feed it into next-action prediction without an explicit causal protocol.",
            "leakage": "timestamps and train/test session membership can be checked here; user overlap and any within-user split require an explicit split policy before formal evaluation.",
        },
        "records": records,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
