#!/usr/bin/env python3
"""Read-only audit of LIGHT actor-unit versus episode-grouped splits.

Only trajectory_id and actor are used from each JSONL record. This script
does not fit models, modify source rows, or overwrite historical artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


DEFAULT_INPUT = Path(__file__).parents[1] / "02_实验/T0c_LIGHT/light_actor_local_full_v0.jsonl"
DEFAULT_OUTPUT = Path(__file__).parents[1] / "outputs/research_reset_audit_20261006/split_audit.json"


def bucket(key: str) -> int:
    """Match the historical runners: first 32 SHA-256 bits modulo ten."""
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 10


def split_for_bucket(value: int) -> str:
    if value < 7:
        return "train"
    if value < 9:
        return "validation"
    return "test"


def old_actor_unit_split(trajectory_id: str, actor: str) -> str:
    # Historical key used in both H0b and compression benchmark runners.
    return split_for_bucket(bucket(f"{trajectory_id}::{actor}"))


def episode_split(trajectory_id: str) -> str:
    # Proposed repair: all actors/rows from a trajectory stay in one split.
    return split_for_bucket(bucket(trajectory_id))


def read_keys(path: Path) -> tuple[list[tuple[str, str]], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    rows: list[tuple[str, str]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL record must be an object at line {line_number}")
        trajectory_id = record.get("trajectory_id")
        actor = record.get("actor")
        if not isinstance(trajectory_id, str) or not trajectory_id:
            raise ValueError(f"missing/non-string trajectory_id at line {line_number}")
        if not isinstance(actor, str) or not actor:
            raise ValueError(f"missing/non-string actor at line {line_number}")
        rows.append((trajectory_id, actor))
    if not rows:
        raise ValueError("input contains no nonblank JSONL records")
    return rows, digest


def summarize(rows: Iterable[tuple[str, str]], assign) -> dict:
    row_counts: Counter[str] = Counter()
    units_by_split: dict[str, set[tuple[str, str]]] = defaultdict(set)
    episodes_by_split: dict[str, set[str]] = defaultdict(set)
    for trajectory_id, actor in rows:
        split = assign(trajectory_id, actor) if assign is old_actor_unit_split else assign(trajectory_id)
        row_counts[split] += 1
        units_by_split[split].add((trajectory_id, actor))
        episodes_by_split[split].add(trajectory_id)

    split_counts = {}
    for split in ("train", "validation", "test"):
        split_counts[split] = {
            "rows": row_counts[split],
            "actor_units": len(units_by_split[split]),
            "episodes": len(episodes_by_split[split]),
        }
    overlap = {}
    split_pairs = (("train", "validation"), ("train", "test"), ("validation", "test"))
    for left, right in split_pairs:
        shared = episodes_by_split[left] & episodes_by_split[right]
        overlap[f"{left}__{right}"] = {"shared_episode_count": len(shared)}
    return {"counts_by_split": split_counts, "pairwise_episode_overlap": overlap}


def self_test() -> None:
    """Independent tiny fixture: two actors from one episode cross old splits."""
    episode = "fixture-shared-episode"
    actor_train = next(f"actor-{i}" for i in range(10000)
                       if old_actor_unit_split(episode, f"actor-{i}") == "train")
    actor_test = next(f"actor-{i}" for i in range(10000)
                      if old_actor_unit_split(episode, f"actor-{i}") == "test")
    fixture = [(episode, actor_train), (episode, actor_test),
               ("fixture-train-only", "actor-a"), ("fixture-test-only", "actor-b")]
    old = summarize(fixture, old_actor_unit_split)
    grouped = summarize(fixture, episode_split)
    old_shared = old["pairwise_episode_overlap"]["train__test"]["shared_episode_count"]
    grouped_shared = grouped["pairwise_episode_overlap"]["train__test"]["shared_episode_count"]
    assert old_shared == 1, f"expected fixture episode to cross old train/test, got {old_shared}"
    assert grouped_shared == 0, f"episode split leaked fixture episode: {grouped_shared}"
    with tempfile.TemporaryDirectory(prefix="research-split-audit-") as temp_dir:
        root = Path(temp_dir)
        input_path = root / "input.jsonl"
        input_path.write_text('{"trajectory_id":"ep","actor":"A"}\n', encoding="utf-8")
        existing = root / "existing.json"
        sentinel = b"preserve-this-existing-output\n"
        existing.write_bytes(sentinel)
        try:
            write_new_json(existing, {}, input_path)
        except FileExistsError:
            pass
        else:
            raise AssertionError("existing output was not rejected")
        assert existing.read_bytes() == sentinel, "existing output bytes changed"
        try:
            write_new_json(input_path, {}, input_path)
        except ValueError:
            pass
        else:
            raise AssertionError("output path equal to input was not rejected")
        assert input_path.read_text(encoding="utf-8") == '{"trajectory_id":"ep","actor":"A"}\n'
        for name, content in (("blank.jsonl", "\n  \n"), ("bad.jsonl", "{bad json}\n"),
                              ("array.jsonl", "[]\n"), ("null.jsonl", "null\n"),
                              ("missing-fields.jsonl", "{}\n")):
            bad_input = root / name
            bad_input.write_text(content, encoding="utf-8")
            try:
                read_keys(bad_input)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{name} was not rejected")
    print(json.dumps({"fixture": "PASS", "old_train_test_shared_episodes": old_shared,
                      "episode_grouped_train_test_shared_episodes": grouped_shared,
                      "exclusive_output_and_invalid_input_checks": "PASS"}, indent=2))


def write_new_json(output: Path, result: dict, input_path: Path) -> None:
    if output.resolve() == input_path.resolve():
        raise ValueError("output path resolves to the input; refusing to overwrite input")
    if output.exists():
        raise FileExistsError(f"output already exists; refusing to overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT,
                        help="full-view JSONL; only trajectory_id and actor are consumed")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="new audit JSON path (default is the dated research reset audit directory)")
    parser.add_argument("--self-test", action="store_true",
                        help="run the tiny deterministic fixture without reading/writing project data")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    if args.output.resolve() == args.input.resolve():
        print("audit error: output path resolves to the input; refusing to overwrite input", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"audit error: output already exists; refusing to overwrite: {args.output}", file=sys.stderr)
        return 1

    try:
        rows, input_sha256 = read_keys(args.input)
    except (OSError, ValueError) as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 1

    old = summarize(rows, old_actor_unit_split)
    grouped = summarize(rows, episode_split)
    old_overlap = sum(v["shared_episode_count"]
                      for v in old["pairwise_episode_overlap"].values())
    grouped_overlap = sum(v["shared_episode_count"]
                          for v in grouped["pairwise_episode_overlap"].values())
    source = Path(__file__).resolve()
    result = {
        "schema_version": "research_split_audit_v1",
        "interpretation": "audit, not a model test; old actor-unit overlap is an expected defect reproduction, not a passing split",
        "input": {
            "path": str(args.input.resolve()),
            "sha256": input_sha256,
            "rows_read": len(rows),
            "fields_consumed": ["trajectory_id", "actor"],
        },
        "script": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "split_rules": {
            "historical_actor_unit": "bucket(trajectory_id + '::' + actor); train < 7, validation 7-8, test >= 9",
            "proposed_episode_grouped": "bucket(trajectory_id); train < 7, validation 7-8, test >= 9",
            "bucket": "int(sha256(key).hexdigest()[:8], 16) % 10",
        },
        "historical_actor_unit_split": {**old, "total_pairwise_shared_episode_counts": old_overlap},
        "proposed_episode_grouped_split": {**grouped, "total_pairwise_shared_episode_counts": grouped_overlap},
        "exit_code_meaning": {
            "0": "no pairwise episode overlap in the historical actor-unit split",
            "2": "historical actor-unit split has episode overlap; expected defect reproduced",
            "3": "proposed episode-grouped split unexpectedly has episode overlap",
            "1": "input or audit error",
        },
    }
    try:
        write_new_json(args.output, result, args.input)
    except (OSError, ValueError) as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output.resolve()),
                      "old_shared_episodes": old_overlap,
                      "episode_grouped_shared_episodes": grouped_overlap,
                      "meaning": "expected old-split defect reproduced" if old_overlap else "no old-split overlap",
                      "exit_code": 3 if grouped_overlap else (2 if old_overlap else 0)}, indent=2))
    if grouped_overlap:
        return 3
    return 2 if old_overlap else 0


if __name__ == "__main__":
    raise SystemExit(main())
