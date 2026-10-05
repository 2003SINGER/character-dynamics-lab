#!/usr/bin/env python3
"""Read-only, development-only source/O/support audit for LIGHT.

This script does not train a model and does not adjudicate semantic validity.
See its JSON output for the explicit cohort and split gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "02_实验/T0c_LIGHT/light_actor_local_full_v0.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs/light_prediction_admission_20261006/run_v1"
SPLIT_PROTOCOL = ROOT / "02_实验/PredictionBaselineV1/train.py"
EXPECTED_ROWS = 13_463
EXPECTED_INPUT_SHA256 = "e6f214b91ed644b60543cf442fdae4255ff177d26a25fccd750ab5c7381ba195"
REQUIRED = (
    "trajectory_id", "actor", "target_step_index", "source_O",
    "source_action_A_star", "candidate_set_factual",
    "previous_source_O", "previous_source_action_A_star",
    "actor_history_depth", "exact_previous_pair", "raw_action_repeat",
    "a_star_in_source_candidates",
)
SPEECH_LINE_RE = re.compile(
    r"(?im)^\s*(?:[A-Z][\w' -]{0,35})\s+(?:says|said|asks|asked|replies| replied|exclaims|tells you)\b"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_action(value: Any) -> str:
    return str(value or "").strip().casefold()


def bucket_for_episode(trajectory_id: str) -> int:
    return int(hashlib.sha256(trajectory_id.encode("utf-8")).hexdigest()[:8], 16) % 10


def split_for_episode(trajectory_id: str) -> tuple[str, int]:
    bucket = bucket_for_episode(trajectory_id)
    return ("train" if bucket < 7 else "validation" if bucket < 9 else "excluded_bucket9", bucket)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                raise ValueError(f"blank JSONL line at {path}:{line_no}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"expected JSON object at {path}:{line_no}")
            missing = [key for key in REQUIRED if key not in row]
            if missing:
                raise ValueError(f"missing required fields at {path}:{line_no}: {missing}")
            rows.append(row)
    return rows


def candidate_info(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("candidate_set_factual")
    if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
        return {"valid": False, "items": [], "raw_unique": 0, "normalized_unique": 0,
                "matches": [], "gold_norm": norm_action(row.get("source_action_A_star"))}
    items = raw
    gold = norm_action(row.get("source_action_A_star"))
    matches = [i for i, value in enumerate(items) if norm_action(value) == gold and gold]
    return {"valid": True, "items": items, "raw_unique": len(set(items)),
            "normalized_unique": len({norm_action(x) for x in items}),
            "matches": matches, "gold_norm": gold}


def row_identity(row: dict[str, Any]) -> str:
    raw = "\x1f".join(str(row.get(k, "")) for k in ("trajectory_id", "actor", "target_step_index"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def review_stratum(row: dict[str, Any]) -> str:
    info = candidate_info(row)
    support = ("invalid_or_empty" if not info["valid"] or not info["items"] else
               "miss" if not info["matches"] else "ambiguous" if len(info["matches"]) > 1 else "unique")
    depth = "shallow" if int(row.get("actor_history_depth", 0)) <= 1 else "deeper"
    pair = "pair_repeat" if row.get("exact_previous_pair") is True else "pair_other"
    return f"{support}|{depth}|{pair}"


def select_review_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    """Deterministic structural sample; intentionally not a population estimate."""
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("_split") == "excluded_bucket9":
            continue
        strata[review_stratum(row)].append(row)
    for values in strata.values():
        values.sort(key=row_identity)
    selected: list[dict[str, Any]] = []
    # Fixed round-robin over lexical stratum order prevents dense cells dominating.
    keys = sorted(strata)
    depth = 0
    while len(selected) < min(limit, len(rows)):
        added = False
        for key in keys:
            if depth < len(strata[key]):
                selected.append(strata[key][depth])
                added = True
                if len(selected) == min(limit, len(rows)):
                    break
        if not added:
            break
        depth += 1
    return selected


def _count_split(rows: list[dict[str, Any]], split: str) -> dict[str, Any]:
    subset = [r for r in rows if r["_split"] == split]
    return {
        "rows": len(subset),
        "actor_trajectory_units": len({(r["trajectory_id"], r["actor"]) for r in subset}),
        "episodes": len({r["trajectory_id"] for r in subset}),
    }


def analyze_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prepared: list[dict[str, Any]] = []
    for original in rows:
        row = dict(original)
        split, bucket = split_for_episode(str(row["trajectory_id"]))
        row["_split"], row["_bucket"] = split, bucket
        row["_candidate"] = candidate_info(row)
        prepared.append(row)

    split_counts = {name: _count_split(prepared, name)
                    for name in ("train", "validation", "excluded_bucket9")}
    shortcut: dict[str, Any] = {"development_only": True,
                                "excluded_bucket9_used": False,
                                "eligible_definition": "valid nonempty candidate list with exactly one normalized gold match"}
    train = [r for r in prepared if r["_split"] == "train" and len(r["_candidate"]["matches"]) == 1]
    val = [r for r in prepared if r["_split"] == "validation" and len(r["_candidate"]["matches"]) == 1]
    position_counts = Counter(r["_candidate"]["matches"][0] for r in train)
    majority_position = min(position_counts, key=lambda p: (-position_counts[p], p)) if position_counts else None
    def position_eval(which: str) -> dict[str, Any]:
        correct = total = out_of_range = 0
        for r in val:
            items, actual = r["_candidate"]["items"], r["_candidate"]["matches"][0]
            guess = 0 if which == "first" else len(items) - 1 if which == "last" else majority_position
            total += 1
            if guess is None or guess < 0 or guess >= len(items):
                out_of_range += 1
            elif guess == actual:
                correct += 1
        return {"eligible_validation_rows": total, "correct": correct,
                "accuracy_over_all_eligible": correct / total if total else None,
                "out_of_range_miss": out_of_range}

    val_pos = Counter(r["_candidate"]["matches"][0] for r in val)
    shortcut.update({
        "train_gold_absolute_position_counts": dict(sorted(position_counts.items())),
        "validation_gold_absolute_position_counts": dict(sorted(val_pos.items())),
        "train_gold_normalized_position_counts": _normalized_position_counts(train),
        "validation_gold_normalized_position_counts": _normalized_position_counts(val),
        "train_majority_position": majority_position,
        "validation_guess_accuracy": {
            "train_majority_position": position_eval("majority"),
            "first_candidate": position_eval("first"),
            "last_candidate": position_eval("last"),
        },
        "all_scores_are_development_diagnostics_not_confirmatory_evidence": True,
    })

    support = {}
    for split in ("train", "validation", "excluded_bucket9"):
        subset = [r for r in prepared if r["_split"] == split]
        invalid = [r for r in subset if not r["_candidate"]["valid"]]
        empty = [r for r in subset if r["_candidate"]["valid"] and not r["_candidate"]["items"]]
        miss = [r for r in subset if r["_candidate"]["valid"] and r["_candidate"]["items"] and not r["_candidate"]["matches"]]
        amb = [r for r in subset if len(r["_candidate"]["matches"]) > 1]
        unique = [r for r in subset if len(r["_candidate"]["matches"]) == 1]
        support[split] = {"invalid_candidate_rows": len(invalid), "empty_candidate_rows": len(empty),
                          "gold_support_miss_rows": len(miss), "normalized_gold_ambiguous_rows": len(amb),
                          "unique_gold_support_rows": len(unique),
                          "candidate_raw_unique_count_distribution": dict(sorted(Counter(
                              r["_candidate"]["raw_unique"] for r in subset if r["_candidate"]["valid"]).items())),
                          "candidate_normalized_unique_count_distribution": dict(sorted(Counter(
                              r["_candidate"]["normalized_unique"] for r in subset if r["_candidate"]["valid"]).items()))}

    exact_o = {}
    candidate_order = {}
    for split in ("train", "validation", "excluded_bucket9"):
        groups: dict[str, set[str]] = defaultdict(set)
        group_rows: Counter[str] = Counter()
        for r in prepared:
            if r["_split"] != split:
                continue
            o = r.get("source_O")
            if isinstance(o, str):
                groups[o].add(r["_candidate"]["gold_norm"])
                group_rows[o] += 1
        varying = {o for o, labels in groups.items() if len(labels) > 1}
        exact_o[split] = {"distinct_exact_O_groups": len(groups),
                          "groups_with_multiple_normalized_gold": len(varying),
                          "rows_in_multiple_gold_groups": sum(group_rows[o] for o in varying),
                          "group_rate": len(varying) / len(groups) if groups else None}

        ordered_groups: dict[tuple[str, ...], set[str]] = defaultdict(set)
        unordered_groups: dict[tuple[str, ...], set[tuple[str, ...]]] = defaultdict(set)
        order_rows: Counter[tuple[str, ...]] = Counter()
        for r in prepared:
            if r["_split"] != split or not r["_candidate"]["valid"]:
                continue
            normalized = tuple(norm_action(x) for x in r["_candidate"]["items"])
            ordered_groups[normalized].add(r["_candidate"]["gold_norm"])
            unordered_groups[tuple(sorted(normalized))].add(normalized)
            order_rows[normalized] += 1
        multi_ordered = {items for items, labels in ordered_groups.items() if len(labels) > 1}
        multi_order_variants = {items for items, variants in unordered_groups.items() if len(variants) > 1}
        candidate_order[split] = {
            "distinct_normalized_ordered_candidate_lists": len(ordered_groups),
            "ordered_lists_with_multiple_normalized_gold": len(multi_ordered),
            "rows_in_ordered_lists_with_multiple_gold": sum(order_rows[items] for items in multi_ordered),
            "unordered_support_sets_seen_in_multiple_orders": len(multi_order_variants),
            "interpretation": "exact-list repetition/order diagnostics; not an independence or semantic test",
        }

    previous = {}
    for split in ("train", "validation", "excluded_bucket9"):
        subset = [r for r in prepared if r["_split"] == split]
        pair_eq = [r for r in subset if r.get("source_O") == r.get("previous_source_O") and
                   r.get("source_action_A_star") == r.get("previous_source_action_A_star")]
        repeat = [r for r in subset if r.get("source_action_A_star") == r.get("previous_source_action_A_star")]
        previous[split] = {
            "exact_previous_O_action_pair_rows_recomputed": len(pair_eq),
            "exact_previous_action_repeat_rows_recomputed": len(repeat),
            "exact_previous_pair_metadata_mismatches": sum(
                bool(r.get("exact_previous_pair")) != (r.get("source_O") == r.get("previous_source_O") and
                    r.get("source_action_A_star") == r.get("previous_source_action_A_star")) for r in subset),
            "raw_action_repeat_metadata_mismatches": sum(
                bool(r.get("raw_action_repeat")) != (r.get("source_action_A_star") == r.get("previous_source_action_A_star"))
                for r in subset),
        }

    text_presence = {}
    tag_scan = {}
    for split in ("train", "validation", "excluded_bucket9"):
        subset = [r for r in prepared if r["_split"] == split]
        valid_text = [r for r in subset if isinstance(r.get("source_O"), str) and isinstance(r.get("source_action_A_star"), str)]
        exact = [r for r in valid_text if r["source_action_A_star"] and r["source_action_A_star"] in r["source_O"]]
        folded = [r for r in valid_text if norm_action(r["source_action_A_star"]) and
                  norm_action(r["source_action_A_star"]) in norm_action(r["source_O"])]
        text_presence[split] = {"rows_with_action_literal_in_current_O": len(exact),
                                "rows_with_casefolded_action_literal_in_current_O": len(folded),
                                "denominator": len(valid_text),
                                "rows_with_any_candidate_literal_in_current_O": sum(any(
                                    item and item in r["source_O"] for item in r["_candidate"]["items"])
                                    for r in valid_text if r["_candidate"]["valid"]),
                                "rows_with_casefolded_any_candidate_literal_in_current_O": sum(any(
                                    norm_action(item) and norm_action(item) in norm_action(r["source_O"])
                                    for item in r["_candidate"]["items"])
                                    for r in valid_text if r["_candidate"]["valid"]),
                                "interpretation": "strict textual-presence proxy only; not a leakage verdict or semantic verifier"}
        matched_speech = sum(bool(SPEECH_LINE_RE.search(r.get("source_O", ""))) for r in valid_text)
        actor_literal = sum(bool(str(r["actor"]).strip()) and str(r["actor"]).casefold() in r.get("source_O", "").casefold()
                            for r in valid_text)
        tag_scan[split] = {"speech_verb_line_prefix_matches": matched_speech,
                           "actor_literal_in_O_rows": actor_literal,
                           "interpretation": "mechanical text heuristics only; no self/partner action-tag semantics inferred"}

    metadata = {}
    for key in ("a_star_in_source_candidates", "previous_a_star_in_current_candidates"):
        metadata[key] = {split: {"true": sum(r.get(key) is True for r in prepared if r["_split"] == split),
                                 "false": sum(r.get(key) is False for r in prepared if r["_split"] == split),
                                 "other": sum(not isinstance(r.get(key), bool) for r in prepared if r["_split"] == split)}
                         for split in ("train", "validation", "excluded_bucket9")}

    summary = {
        "audit": "LIGHT source/O/support admission diagnostics v1",
        "status": "STRUCTURAL_DEVELOPMENT_AUDIT_ONLY",
        "human_admission": "PENDING",
        "golden_semantic_verifier": False,
        "input_rows": len(prepared),
        "split_protocol": {"method": "int(SHA256(trajectory_id UTF-8).hexdigest()[:8],16) modulo 10",
                           "buckets": {"train": "0-6", "validation": "7-8", "excluded_bucket9": "9"}},
        "split_counts": split_counts,
        "support": support,
        "shortcut_diagnostics": shortcut,
        "same_exact_O_different_gold": exact_o,
        "candidate_list_order_repetition": candidate_order,
        "previous_pair_and_repeat": previous,
        "target_text_in_current_O": text_presence,
        "mechanical_O_tag_proxies": tag_scan,
        "source_flags": metadata,
        "limitations": [
            "Bucket 9 is excluded from shortcut scoring and model conclusions; its exact-O, repeat, and text-presence fields are structural diagnostics only, not future-target optimization evidence.",
            "The 24-row sample is deterministic and stratified, not a random population estimate.",
            "AUDIT_ONLY/PENDING fields are placeholders; no human admission was performed.",
            "The flattened actor-local view cannot recover complete episode observations or reliably identify self/partner action tags.",
            "The 24-row package contains only this flattened source view; it does not include full-source future turns or complete semantic-review context.",
            "Literal action text in O is a text-presence proxy only, not proof of target leakage.",
        ],
    }
    return summary, prepared


def _normalized_position_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        cand = row["_candidate"]
        if len(cand["matches"]) != 1:
            continue
        n = len(cand["items"])
        if n > 1:
            counts[f"{cand['matches'][0]}/{n - 1}"] += 1
        else:
            counts["single_candidate"] += 1
    return dict(sorted(counts.items()))


def make_review_record(row: dict[str, Any]) -> dict[str, Any]:
    keys = ("source_O", "source_action_A_star", "candidate_set_factual",
            "previous_source_O", "previous_source_action_A_star",
            "previous2_source_O", "previous2_source_action_A_star",
            "actor_history_depth", "exact_previous_pair", "raw_action_repeat",
            "a_star_in_source_candidates", "previous_a_star_in_current_candidates")
    record = {key: row.get(key) for key in keys}
    record.update({
        "trajectory_id": row["trajectory_id"],
        "actor": row["actor"],
        "target_step_index": row["target_step_index"],
        "row_key_sha256": row_identity(row),
        "episode_key_sha256": sha256_bytes(str(row["trajectory_id"]).encode("utf-8")),
        "actor_key_sha256": sha256_bytes(str(row["actor"]).encode("utf-8")),
        "split": row["_split"],
        "bucket": row["_bucket"],
        "structural_stratum": review_stratum(row),
        "review_scope": "AUDIT_ONLY",
        "model_output": "NOT_AVAILABLE",
        "human_admission_status": "PENDING",
        "human_semantic_judgment": "PENDING",
        "reviewer_notes": "",
    })
    return record


def write_exclusive(path: Path, data: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(data)


def run_audit(input_path: Path, output_dir: Path, enforce_cohort: bool = True) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    if input_path == output_dir or input_path in output_dir.parents or output_dir in input_path.parents:
        raise ValueError("input and output paths must not overlap")
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    raw_bytes = input_path.read_bytes()
    input_sha = sha256_bytes(raw_bytes)
    if enforce_cohort and input_sha != EXPECTED_INPUT_SHA256:
        raise ValueError(f"input SHA-256 mismatch: expected {EXPECTED_INPUT_SHA256}, got {input_sha}")
    rows = read_jsonl(input_path)
    if enforce_cohort and len(rows) != EXPECTED_ROWS:
        raise ValueError(f"input row-count mismatch: expected {EXPECTED_ROWS}, got {len(rows)}")
    summary, prepared = analyze_rows(rows)
    review = [make_review_record(r) for r in select_review_rows(prepared, 24)]
    if len(review) != min(24, sum(r["_split"] != "excluded_bucket9" for r in prepared)):
        raise AssertionError("review sample count mismatch")
    summary["review_sample"] = {"rows": len(review), "selection": "train/validation only; fixed round-robin across lexical structural strata; SHA256 row identity within stratum",
                                "excluded_bucket9_sampled": False,
                                "not_population_estimate": True, "all_human_admission_pending": True}
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()  # exclusive: fails if another process created it
    summary_path = output_dir / "summary.json"
    review_path = output_dir / "review_24.jsonl"
    summary_text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    review_text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in review)
    write_exclusive(summary_path, summary_text)
    write_exclusive(review_path, review_text)
    manifest = {
        "input_path": str(input_path), "input_sha256": input_sha,
        "input_rows": len(rows), "expected_cohort_enforced": enforce_cohort,
        "audit_code_path": str(Path(__file__).resolve()), "audit_code_sha256": sha256_file(Path(__file__).resolve()),
        "split_protocol_path": str(SPLIT_PROTOCOL), "split_protocol_code_sha256": sha256_file(SPLIT_PROTOCOL),
        "test_code_path": str(Path(__file__).with_name("test_audit_light_prediction_admission_v1.py").resolve()),
        "test_code_sha256": sha256_file(Path(__file__).with_name("test_audit_light_prediction_admission_v1.py")),
        "output_files_sha256": {"summary.json": sha256_file(summary_path),
                                "review_24.jsonl": sha256_file(review_path)},
        "output_role": "new read-only structural audit; does not overwrite source or prior artifacts",
    }
    write_exclusive(output_dir / "artifact_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-noncanonical-cohort", action="store_true",
                        help="for synthetic/private fixtures only; never use for the canonical report")
    args = parser.parse_args(argv)
    try:
        result = run_audit(args.input, args.output, enforce_cohort=not args.allow_noncanonical_cohort)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
