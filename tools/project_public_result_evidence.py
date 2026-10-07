#!/usr/bin/env python3
"""Create source-stripped, non-reconstructive public result projections.

This tool never edits source artifacts. It recursively preserves numeric,
boolean, and null result values, a narrow set of identifiers/hashes, and
explicitly allowlisted categorical labels. Unknown strings and source-like
payloads are omitted. Outputs are projections, not raw traces or input data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = Path("outputs/public_result_projections_20261007_v2")
SCHEMA = "SOURCE_STRIPPED_RESULT_PROJECTION"

RAW_KEYS = {
    "source_o", "source_action_a_star", "previous_source_o",
    "previous_source_action_a_star", "previous2_source_o",
    "previous2_source_action_a_star", "candidate_set_factual",
    "previous_action", "scene", "candidate_scene_bindings",
    "scene_snapshot", "description", "target_description", "target_text",
    "target_attrs", "aria-label", "href", "name", "title", "value",
    "input", "raw_answer", "raw_answers", "reviewer_notes", "request",
    "request_json", "messages", "content", "prompt", "observation",
    "actor_observation", "affordance_evidence", "source_candidates",
    "evidence", "behavior", "relation", "reasoning", "reason",
    "model_output", "recent_history", "recent_factual_summary",
    "positive_conduciveness_trace", "negative_conduciveness_trace",
    "relevance_trace", "x", "source", "path", "input_path",
    "protocol_path", "candidate_path", "gold_path", "blind_input_path",
}

IDENTIFIER_KEYS = {
    "source_record_id", "record_id", "trajectory_id", "candidate_id",
    "fixture_id", "row_id", "semantic_id", "matched_candidate_ids",
}

CATEGORICAL_KEYS = {
    "semantic_rules_version", "candidate_semantic_groups",
    "human_semantic_judgment", "human_admission_status", "review_scope",
    "split", "bucket", "structural_stratum", "status", "verdict",
    "decision", "outcome", "outcome_counts", "protocol",
    "protocol_version", "report_version", "artifact_kind", "type",
    "check", "checks", "stopping_rule", "matching_rule",
    "candidate_identity_source", "gold_identity_source",
    "identity_match", "identity_mismatch_semantic",
}

DYNAMIC_MAP_KEYS = {
    "candidate_probabilities", "probabilities", "candidate_scores",
    "scores", "candidate_counts",
}

SAFE_LOSS_CONDITIONS = frozenset("""
fixed_mean_seed19 fixed_mean_seed31 fixed_mean_seed7
gru_permuted_state_seed19 gru_permuted_state_seed31 gru_permuted_state_seed7
gru_seed19 gru_seed31 gru_seed7
gru_state_zero_seed19 gru_state_zero_seed31 gru_state_zero_seed7
last2_seed19 last2_seed31 last2_seed7
last_action_seed19 last_action_seed31 last_action_seed7
learned_last2_seed19 learned_last2_seed31 learned_last2_seed7
learned_mean_seed19 learned_mean_seed31 learned_mean_seed7
o_only_seed19 o_only_seed31 o_only_seed7
uniform
""".split())

# Structural object labels observed in the scoped source schemas. A mapping
# whose keys are all outside this set is treated as a dynamic map: its keys
# are omitted and insertion order is preserved as ordinal/value entries.
SCHEMA_KEYS = frozenset("""
S_after S_before a_star_in_source_candidates action actor actor_history_depth
actor_key_sha256 affordance_source after all_candidates ambiguity ambiguous
ambiguous_candidates ambiguous_gold_match_rate ambiguous_passes ambiguous_threshold
anxiety aria-label artifact_kind artifacts bathroom_relief bathroom_urge before
behavior blind_input_path blind_input_sha256 boredom bucket candidate_ambiguity_rate
candidate_artifact_hash_stable candidate_count candidate_generator_gold_access_false
candidate_id candidate_identity_source candidate_input_field_allowlist candidate_inputs
candidate_path candidate_probabilities candidate_provenance_present candidate_raw_binding_valid
candidate_records candidate_scene_bindings candidate_semantic_groups candidate_semantics
candidate_set_factual candidate_sha256 candidate_sha256_read_1 candidate_sha256_read_2
candidate_source_index candidates check context_relevance counterfactual_remove decision
declared_fields definition delta_gold_probability_counter_minus_factual
delta_nll_counter_minus_factual delta_state_counter_minus_factual denominator
duplicate_candidate_ids duplicate_identity duplicate_identity_check duplicate_rate
duplicate_target_source_indices_within_record effect_kind entity_id environment_control
episode_key_sha256 evaluation evidence exact exact_previous_pair excluded_from_matching
expected_effect factual family_support_diagnostic_only fatigue fixture_id fixture_ids_unique
frozen_at generator generator_metadata goal_progress goal_relevance gold_access
gold_blind_invariants gold_class gold_evaluator_only_accessed gold_identity_source gold_index
gold_inputs gold_path gold_probability gold_records gold_semantic_id gold_sha256 hash_stable
href html_sha256 human_admission_status human_semantic_judgment hunger hunger_relief id
identity_match identity_mismatch_semantic input input_path input_sha256 interpretation
intervention keys_checked kind latest_update_semantics matched_candidate_ids
matched_effect_events matching_rule max mean median metrics min miss model model_input_fields
model_output model_sha256 name negative_conduciveness negative_conduciveness_trace nll
no_candidate no_candidate_check no_candidate_rate no_history normalization note numerator
numerator_definition outcome outcome_counts outcomes p25 p50 p75 p90
paired_no_history_minus_stateful_nll per_record positive_conduciveness
positive_conduciveness_trace previous2_source_O previous2_source_action_A_star
previous_a_star_in_current_candidates previous_action previous_action_semantics_used_for_S
previous_source_O previous_source_action_A_star prohibited_gold_keys_absent_from_candidate
prohibited_shortcut protocol_path protocol_sha256 protocol_version provenance
provenance_encoding purchase_urge quantiles_linear_interpolation rank raw_action_repeat
raw_element_source_index_ranges raw_elements_sha256 reason reasoning_mode record_count
record_count_matches_gold records records_with_any_ambiguous_candidate
records_with_zero_candidates recovery relation relevance_trace remove_t removed_action
report_version reproducibility rerun_performed reveal_order_from_filesystem_mtime review_scope
reviewer_notes row_key_sha256 satisfaction scene scene_aware scene_bias screen_strain
semantic semantic_id semantic_method semantic_rules_version semantic_update_ablation
session_sha256_16 short_term_reward snapshot_current_ref snapshot_prev_ref source source_O
source_action_A_star source_record_id split state_at_decision stateful status step_index
stimulation stopping_rule strict_support strict_support_passes strict_support_recall
strict_support_threshold structural_stratum support_recall support_recall_including_ambiguous
support_recall_strict t target_A_star target_attrs target_description target_entity
target_entity_id target_in_inventory target_in_scene target_source_index target_step_index
target_text target_t target_visible_in_O task_pressure temperature temperature_sha256 title
total trajectory_id transition_events uniform_nll value verb verdict losses_nats
""".lower().split())


class ProjectionError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _key_allowed_string(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in IDENTIFIER_KEYS
        or normalized in CATEGORICAL_KEYS
        or normalized.endswith("_sha256")
        or normalized.endswith("_hash")
    )


def _record_removed(counts: Counter[str], key: str) -> None:
    normalized = key.lower()
    if normalized in RAW_KEYS or normalized in SCHEMA_KEYS or normalized in CATEGORICAL_KEYS:
        safe_key = key
    else:
        safe_key = "unknown_key_sha256_" + _sha256(key.encode("utf-8"))[:16]
    counts[safe_key or "<root>"] += 1


def _record_dynamic_map_key(counts: Counter[str], key: str) -> None:
    normalized = key.lower()
    if normalized in SCHEMA_KEYS or normalized in DYNAMIC_MAP_KEYS:
        counts[f"{key}::<map-key>"] += 1
    else:
        _record_removed(counts, key)


def project_value(value: Any, key: str = "", counts: Counter[str] | None = None) -> Any:
    """Return safe projected value; omit unsupported strings with parent key tally."""
    if counts is None:
        counts = Counter()
    normalized = key.lower()

    if normalized in RAW_KEYS:
        _record_removed(counts, key or "<root>")
        return _OMIT
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if _key_allowed_string(key):
            return value
        _record_removed(counts, key or "<root>")
        return _OMIT
    if isinstance(value, list):
        result = []
        for item in value:
            projected = project_value(item, key, counts)
            if projected is not _OMIT:
                result.append(projected)
        return result
    if isinstance(value, dict):
        if normalized == "losses_nats":
            result = {}
            unknown_entries = []
            for ordinal, (child_key, child_value) in enumerate(value.items()):
                if str(child_key) in SAFE_LOSS_CONDITIONS:
                    projected = project_value(child_value, "loss_value", counts)
                    if projected is not _OMIT:
                        result[str(child_key)] = projected
                else:
                    _record_dynamic_map_key(counts, key)
                    projected = project_value(child_value, "map_value", counts)
                    if projected is not _OMIT:
                        unknown_entries.append({"ordinal": ordinal, "value": projected})
            if unknown_entries:
                result["unknown_map_entries"] = unknown_entries
            return result
        if normalized in DYNAMIC_MAP_KEYS:
            # Preserve source insertion order and numeric outputs without
            # publishing arbitrary candidate/category labels as JSON keys.
            result = []
            for ordinal, (_map_key, map_value) in enumerate(value.items()):
                _record_dynamic_map_key(counts, key)
                projected = project_value(map_value, "map_value", counts)
                if projected is not _OMIT:
                    result.append({"ordinal": ordinal, "value": projected})
            return result
        if value and all(str(map_key).lower() not in SCHEMA_KEYS for map_key in value):
            result = []
            for ordinal, (_map_key, map_value) in enumerate(value.items()):
                _record_dynamic_map_key(counts, key)
                projected = project_value(map_value, "map_value", counts)
                if projected is not _OMIT:
                    result.append({"ordinal": ordinal, "value": projected})
            return result
        result = {}
        unknown_entries = []
        for ordinal, (child_key, child_value) in enumerate(value.items()):
            if str(child_key).lower() in SCHEMA_KEYS:
                projected = project_value(child_value, str(child_key), counts)
                if projected is not _OMIT:
                    result[child_key] = projected
            else:
                _record_dynamic_map_key(counts, key)
                projected = project_value(child_value, "map_value", counts)
                if projected is not _OMIT:
                    unknown_entries.append({"ordinal": ordinal, "value": projected})
        if unknown_entries:
            result["unknown_map_entries"] = unknown_entries
        return result
    _record_removed(counts, key or "<root>")
    return _OMIT


class _Omit:
    pass


_OMIT = _Omit()


def _relative_source(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _output_path(source: Path) -> Path:
    rel = Path(_relative_source(source))
    if rel.parts[0] != "outputs":
        raise ProjectionError(f"source is outside outputs/: {rel}")
    return REPO_ROOT / OUTPUT_ROOT / Path(*rel.parts[1:])


def _row_count(path: Path, payload: Any) -> int:
    if path.suffix == ".jsonl":
        return len(payload)
    records = payload.get("records") if isinstance(payload, dict) else None
    return len(records) if isinstance(records, list) else 1


def project_file(source: Path) -> tuple[bytes, int, dict[str, int]]:
    counts: Counter[str] = Counter()
    if source.suffix == ".jsonl":
        rows = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProjectionError(f"invalid JSONL at {source}:{line_number}") from exc
            projected = project_value(row, counts=counts)
            rows.append({} if projected is _OMIT else projected)
        body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
        return body.encode("utf-8"), len(rows), dict(sorted(counts.items()))

    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"invalid JSON: {source}") from exc
    projected = project_value(raw, counts=counts)
    body = json.dumps(projected, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return body.encode("utf-8"), _row_count(source, raw), dict(sorted(counts.items()))


def discover_inputs() -> tuple[list[Path], list[Path]]:
    sources = set(REPO_ROOT.glob("outputs/experiments/LIGHT*/*.trace.jsonl"))
    sources.update(REPO_ROOT.glob("outputs/T0c_LIGHT_batch4/*.trace.jsonl"))
    sources.update(REPO_ROOT.glob("outputs/prediction_baseline_v1_20261006/run_v1/validation_row_losses.jsonl"))
    sources.update(REPO_ROOT.glob("outputs/prediction_baseline_v1_20261006/reproduction_seed7_v1/validation_row_losses.jsonl"))
    sources.update(REPO_ROOT.glob("outputs/light_prediction_admission_20261006/run_v*/review_24.jsonl"))
    sources.update(REPO_ROOT.glob("outputs/opera_t0d_2026-09-08/terra_candidate_spike_v*/candidate_artifact.json"))
    sources.update(REPO_ROOT.glob("outputs/opera_t0d_2026-09-08/terra_candidate_spike_v*/evaluator_report.json"))
    excluded = list(REPO_ROOT.glob("outputs/experiments/LIGHT*/LIGHT_scene_snapshot_v0.jsonl"))
    return sorted(sources), sorted(excluded)


def _manifest_entry(source: Path, output: Path, output_bytes: bytes, rows: int,
                    removed: dict[str, int]) -> dict[str, Any]:
    source_bytes = source.read_bytes()
    return {
        "sourcepath": _relative_source(source),
        "source_sha256": _sha256(source_bytes),
        "outputpath": output.relative_to(REPO_ROOT).as_posix(),
        "output_sha256": _sha256(output_bytes),
        "rows": rows,
        "removedkey_counts": removed,
    }


def _excluded_entry(source: Path) -> dict[str, Any]:
    return {
        "sourcepath": _relative_source(source),
        "source_sha256": _sha256(source.read_bytes()),
        "reason": "source-bearing scene snapshot excluded as input, not projected",
    }


def build_bundle() -> tuple[dict[Path, bytes], dict[str, Any]]:
    sources, excluded = discover_inputs()
    outputs: dict[Path, bytes] = {}
    entries = []
    for source in sources:
        output = _output_path(source)
        data, rows, removed = project_file(source)
        outputs[output] = data
        entries.append(_manifest_entry(source, output, data, rows, removed))
    manifest = {
        "schema": SCHEMA,
        "projection_version": 1,
        "disclaimer": "Lossy result projection only; not rawtrace, dataset, or input reconstruction.",
        "preserved_value_policy": "numbers, booleans, nulls, selected IDs/hashes, and allowlisted categorical labels",
        "losses_nats_key_policy": "only explicit non-source condition labels are retained as keys; unknown labels become ordinal/value entries",
        "ordered_map_policy": "dynamic maps and objects with only unrecognized keys are represented as insertion-ordered ordinal/value arrays; original keys are omitted and order is not sorted",
        "mixed_object_policy": "known schema keys are retained; every unknown child key is omitted and represented by its original ordinal and projected value",
        "removedkey_count_policy": "unrecognized removed field names are represented by truncated SHA-256 labels in the count map",
        "superseded_unpublished_projection": "outputs/public_result_projections_20261007/ (development v1; use this v2 root only)",
        "sources": entries,
        "excluded_inputs": [_excluded_entry(path) for path in excluded],
    }
    manifest_path = REPO_ROOT / OUTPUT_ROOT / "manifest.json"
    outputs[manifest_path] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return outputs, manifest


def _write_new_or_identical(outputs: dict[Path, bytes]) -> None:
    conflicts = []
    for path, data in outputs.items():
        if path.exists() and path.read_bytes() != data:
            conflicts.append(path)
    if conflicts:
        joined = ", ".join(
            p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else p.name
            for p in conflicts
        )
        raise ProjectionError(f"refusing to overwrite differing output(s): {joined}")
    for path, data in outputs.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)


def check_bundle() -> dict[str, Any]:
    sources, _excluded = discover_inputs()
    manifest_path = REPO_ROOT / OUTPUT_ROOT / "manifest.json"
    if not manifest_path.is_file():
        raise ProjectionError(f"missing projection manifest: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectionError("projection manifest is invalid JSON") from exc
    if manifest.get("schema") != SCHEMA:
        raise ProjectionError("projection manifest schema mismatch")

    source_map = {_relative_source(path): path for path in sources}
    manifest_sources = {entry.get("sourcepath") for entry in manifest.get("sources", [])}
    source_available = bool(manifest_sources) and manifest_sources.issubset(source_map)
    if source_available and set(source_map) != manifest_sources:
        raise ProjectionError("source inventory differs from projection manifest")
    checked = 0
    allowed_output_root = (REPO_ROOT / OUTPUT_ROOT).resolve()
    for entry in manifest.get("sources", []):
        output = (REPO_ROOT / entry["outputpath"]).resolve()
        if not output.is_relative_to(allowed_output_root) or output == allowed_output_root:
            raise ProjectionError(f"projection path escapes output root: {entry.get('outputpath')}")
        source_name = entry.get("sourcepath", "")
        source_relative = Path(source_name)
        if not source_relative.parts or source_relative.parts[0] != "outputs" or ".." in source_relative.parts:
            raise ProjectionError("invalid sourcepath in projection manifest")
        expected_output = (OUTPUT_ROOT / Path(*source_relative.parts[1:])).as_posix()
        if entry.get("outputpath") != expected_output:
            raise ProjectionError("manifest source/output path mapping mismatch")
        if not output.is_file():
            raise ProjectionError(f"missing projection: {entry['outputpath']}")
        out_bytes = output.read_bytes()
        if _sha256(out_bytes) != entry.get("output_sha256"):
            raise ProjectionError(f"projection hash mismatch: {entry['outputpath']}")
        source = source_map.get(entry.get("sourcepath"))
        if source is not None:
            source_bytes = source.read_bytes()
            if _sha256(source_bytes) != entry.get("source_sha256"):
                raise ProjectionError(f"source hash mismatch: {entry['sourcepath']}")
            expected, rows, removed = project_file(source)
            if expected != out_bytes:
                raise ProjectionError(f"projection bytes differ from source oracle: {entry['outputpath']}")
            if rows != entry.get("rows") or removed != entry.get("removedkey_counts"):
                raise ProjectionError(f"row count or removal-count mismatch: {entry['outputpath']}")
        else:
            if output.suffix == ".jsonl":
                rows = sum(1 for line in out_bytes.splitlines() if line.strip())
            else:
                obj = json.loads(out_bytes)
                rows = _row_count(output, obj)
            if rows != entry.get("rows"):
                raise ProjectionError(f"projection row count mismatch without source: {entry['outputpath']}")
        checked += 1
    return {"checked_outputs": checked, "source_oracle_available": source_available}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify projection bytes against source when present")
    args = parser.parse_args()
    try:
        if args.check:
            result = check_bundle()
            print(f"checked {result['checked_outputs']} projections; source oracle available={result['source_oracle_available']}")
        else:
            outputs, manifest = build_bundle()
            _write_new_or_identical(outputs)
            print(f"projected {len(manifest['sources'])} source artifacts; excluded {len(manifest['excluded_inputs'])} source-bearing input(s)")
    except (OSError, ProjectionError, ValueError) as exc:
        raise SystemExit(f"projection failed: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
