#!/usr/bin/env python3
"""Build a source-preserving LIGHT before-turn feasibility artifact.

This is a structural candidate-input builder, not an admission decision or
training protocol. Candidate channels remain explicitly unauthorized.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pickle
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PICKLE = ROOT / "outputs/external_assets_2026-09-06/LIGHT/light_data.pkl"
VIEW = ROOT / "02_实验/T0c_LIGHT/light_actor_local_full_v0.jsonl"
LINEAGE = ROOT / "tools/audit_light_source_lineage_v1.py"
TRAINER = ROOT / "02_实验/PredictionBaselineV1/train.py"
TRAINER_README = ROOT / "02_实验/PredictionBaselineV1/README.md"
DEFAULT_OUTPUT = ROOT / "outputs/light_before_turn_20261006/run_v1"
EXPECTED_PICKLE_SHA256 = "7c83cf49818586db9999ea67a4a6ad087afbd91c26ed629a9f00e21d0b84058f"
EXPECTED_VIEW_SHA256 = "e6f214b91ed644b60543cf442fdae4255ff177d26a25fccd750ab5c7381ba195"
EXPECTED_ROWS = 13_463
PER_TURN_KEYS = ("action", "context", "available_actions", "character", "speech", "emote",
                 "room_objects", "room_agents", "carrying", "wearing", "wielding")
CHANNELS = ("speech", "action", "emote")
EPISODE_ID_RE = re.compile(r"^light::episode-(\d+)$")
INPUT_CONTRACT = {
    "schema": "light_before_turn_candidate_input_contract_v1",
    "unit": "one existing actor-local physical-action target row",
    "target_join": "exact legacy context/action/available_actions/normalized-character check plus raw-turn mapping",
    "history": "all source turns with raw_turn_index < target raw turn; group channels by turn; do not assume an intra-turn channel order",
    "history_channels": ["speech", "action", "emote"],
    "history_roles": "self or partner derived from character field; nonempty speaker must uniquely match episode agents",
    "candidate_model_payload_fields": ["self_persona", "prior_interaction_history", "recorded_environment_snapshot"],
    "candidate_surface_fields": ["recorded_support"],
    "supervision_field": "recorded_action; separate from candidate inputs",
    "provenance": "source ids, raw/physical indices, names, refs, split are metadata and not model features",
    "excluded": ["same-turn speech/action/emote", "future turns", "partner persona", "all_descriptions"],
    "split": "int(SHA256(trajectory_id UTF-8).hexdigest()[:8],16) modulo 10; buckets 0-6 train, 7-8 validation, 9 excluded",
    "admission": "all channels PENDING; training_authorized=false; time-safe does not imply authorized or complete O",
}


def input_contract_sha256() -> str:
    encoded = json.dumps(INPUT_CONTRACT, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def _load_lineage_module():
    spec = importlib.util.spec_from_file_location("light_lineage_checker", LINEAGE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load lineage checker: {LINEAGE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_LINEAGE_MODULE = _load_lineage_module()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def nonempty(value: Any) -> bool:
    return value is not None and bool(str(value).strip())


def bucket_for_episode(trajectory_id: str) -> int:
    return int(hashlib.sha256(trajectory_id.encode("utf-8")).hexdigest()[:8], 16) % 10


def split_for_episode(trajectory_id: str) -> tuple[int, str]:
    bucket = bucket_for_episode(trajectory_id)
    return bucket, "train" if bucket < 7 else "validation" if bucket < 9 else "excluded_bucket9"


def episode_index_from_trajectory(trajectory_id: str) -> int:
    match = EPISODE_ID_RE.fullmatch(trajectory_id)
    if not match:
        raise ValueError(f"unexpected trajectory_id format: {trajectory_id!r}")
    return int(match.group(1))


def validate_episode_arrays(episode: dict[str, Any]) -> int:
    missing = [key for key in PER_TURN_KEYS if key not in episode]
    if missing:
        raise ValueError(f"missing per-turn source arrays: {missing}")
    lengths = {key: len(episode[key]) if isinstance(episode[key], (list, tuple)) else None
               for key in PER_TURN_KEYS}
    if any(value is None for value in lengths.values()) or len(set(lengths.values())) != 1:
        raise ValueError(f"per-turn arrays are absent, non-sequences, or misaligned: {lengths}")
    return next(iter(lengths.values()))


def unique_self_persona(episode: dict[str, Any], actor: str) -> tuple[str, int, str]:
    agents = episode.get("agents")
    if not isinstance(agents, list):
        raise ValueError("agents must be a list for unique self-persona matching")
    matches: list[tuple[int, dict[str, Any]]] = []
    for i, agent in enumerate(agents):
        if not isinstance(agent, dict) or not isinstance(agent.get("name"), str):
            continue
        if norm(agent["name"]) == norm(actor):
            matches.append((i, agent))
    if len(matches) != 1:
        raise ValueError(f"self persona match must be unique; found {len(matches)} for actor {actor!r}")
    index, agent = matches[0]
    persona = agent.get("persona")
    if not isinstance(persona, str) or not persona.strip():
        raise ValueError(f"unique self persona is absent or blank for actor {actor!r}")
    return persona, index, str(agent["name"])


def physical_raw_turns(episode: dict[str, Any]) -> list[int]:
    validate_episode_arrays(episode)
    return [i for i, action in enumerate(episode["action"]) if nonempty(action)]


def validate_target_and_history(row: dict[str, Any], episode: dict[str, Any]) -> tuple[int, str, list[dict[str, Any]]]:
    """Use legacy exact row checks, then verify flattened same-actor history against raw indices."""
    validate_episode_arrays(episode)
    raw_turn = _LINEAGE_MODULE.check_row(row, episode)
    actor = episode["character"][raw_turn]
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("target character must be a nonempty string")
    trajectory_id = row.get("trajectory_id")
    if not isinstance(trajectory_id, str):
        raise ValueError("trajectory_id must be a string")
    physical = physical_raw_turns(episode)
    physical_index = int(row["target_step_index"])
    if physical_index < 0 or physical_index >= len(physical) or physical[physical_index] != raw_turn:
        raise ValueError("target physical index does not map to legacy raw turn")

    prior_same_actor: list[tuple[int, int]] = []
    for pos, turn in enumerate(physical[:physical_index]):
        if norm(episode["character"][turn]) == norm(actor):
            prior_same_actor.append((pos, turn))
    if not prior_same_actor:
        raise ValueError("target has no prior same-actor physical action; expected eligible history row")
    expected_prev = prior_same_actor[-1]
    expected_prev2 = prior_same_actor[-2] if len(prior_same_actor) > 1 else None
    checks = (
        (int(row.get("previous_same_actor_t", -1)) == expected_prev[0], "previous_same_actor_t mapping mismatch"),
        (row.get("previous_source_O") == episode["context"][expected_prev[1]], "previous source O mismatch"),
        (row.get("previous_source_action_A_star") == episode["action"][expected_prev[1]], "previous source action mismatch"),
        (int(row.get("actor_history_depth", -1)) == len(prior_same_actor), "actor_history_depth mismatch"),
        (row.get("previous2_same_actor_t") == (expected_prev2[0] if expected_prev2 else None), "previous2_same_actor_t mapping mismatch"),
        (row.get("previous2_source_O") == (episode["context"][expected_prev2[1]] if expected_prev2 else None), "previous2 source O mismatch"),
        (row.get("previous2_source_action_A_star") == (episode["action"][expected_prev2[1]] if expected_prev2 else None), "previous2 source action mismatch"),
    )
    for passed, message in checks:
        if not passed:
            raise ValueError(message)
    if expected_prev[1] >= raw_turn or (expected_prev2 and expected_prev2[1] >= raw_turn):
        raise ValueError("same-actor physical history is not strictly earlier than target raw turn")
    return raw_turn, actor, [{"physical_index": p, "raw_turn_index": t} for p, t in prior_same_actor]


def build_candidate_inputs(episode: dict[str, Any], target_raw_turn: int, target_actor: str) -> dict[str, Any]:
    """Build candidate channels from source fields; caller separately validates joins."""
    turn_count = validate_episode_arrays(episode)
    if not isinstance(target_raw_turn, int) or not 0 <= target_raw_turn < turn_count:
        raise ValueError("target raw turn is out of range")
    raw_actor = episode["character"][target_raw_turn]
    if not isinstance(raw_actor, str) or norm(raw_actor) != norm(target_actor):
        raise ValueError("target actor does not match raw character field")
    persona, _, _ = unique_self_persona(episode, target_actor)
    history: list[dict[str, Any]] = []
    history_provenance: list[dict[str, Any]] = []
    # Feature projection may inspect only strict-past actions; join validation is
    # a separate audit path that may read the full source episode.
    prior_physical_index = 0
    physical_to_index: dict[int, int] = {}
    for turn in range(target_raw_turn):
        if nonempty(episode["action"][turn]):
            physical_to_index[turn] = prior_physical_index
            prior_physical_index += 1
    agents = episode.get("agents")
    if not isinstance(agents, list):
        raise ValueError("agents must be a list for history speaker matching")
    agent_names = [agent.get("name") for agent in agents if isinstance(agent, dict)
                   and isinstance(agent.get("name"), str) and agent.get("name").strip()]
    for turn in range(target_raw_turn):
        speaker = episode["character"][turn]
        channels = {channel: episode[channel][turn] if nonempty(episode[channel][turn]) else None
                    for channel in CHANNELS}
        if not any(value is not None for value in channels.values()):
            continue
        if not isinstance(speaker, str) or not speaker.strip():
            raise ValueError(f"nonempty prior interaction has no character/speaker at raw turn {turn}")
        matches = [name for name in agent_names if norm(name) == norm(speaker)]
        if len(matches) != 1:
            raise ValueError(f"prior interaction speaker must uniquely match an agent at raw turn {turn}; found {len(matches)}")
        role = "self" if norm(speaker) == norm(target_actor) else "partner"
        ref = {"raw_turn_index": turn, "physical_index": physical_to_index.get(turn),
               "role": role, "speaker": speaker,
               "source_ref": f"episode:{episode['_source_episode_index']}:turn:{turn}"}
        history.append({"role": role, **channels})
        history_provenance.append(ref)

    inputs = {
        "candidate_model_payload": {
            "self_persona": persona,
            "prior_interaction_history": history,
            "recorded_environment_snapshot": episode["context"][target_raw_turn],
        },
        "candidate_surface": {"recorded_support": episode["available_actions"][target_raw_turn]},
        "provenance": {
            "payload_history_turn_refs": history_provenance,
            "persona_source_ref": f"episode:{episode['_source_episode_index']}:agents",
        },
        "source_history_holdback": {
            "partner_persona": "EXCLUDED_FROM_CANDIDATE_MODEL_PAYLOAD",
            "all_descriptions": "EXCLUDED_FROM_CANDIDATE_MODEL_PAYLOAD",
            "future_turns": "EXCLUDED_FROM_CANDIDATE_MODEL_PAYLOAD",
            "same_turn_speech_action_emote": "EXCLUDED_FROM_CANDIDATE_MODEL_PAYLOAD",
        },
        "admission": {
            "overall": "PENDING",
            "training_authorized": False,
            "self_persona": "PENDING_EXACT_INTERFACE_EVIDENCE",
            "prior_self_speech": "PENDING_EXACT_INTERFACE_EVIDENCE",
            "prior_self_action": "PENDING_EXACT_INTERFACE_EVIDENCE",
            "prior_self_emote": "PENDING_EXACT_INTERFACE_EVIDENCE",
            "prior_partner_speech": "PENDING_EXACT_SOURCE_INTERFACE_EVIDENCE",
            "prior_partner_emote": "PENDING_EXACT_SOURCE_INTERFACE_EVIDENCE",
            "prior_partner_action": "PENDING_SOURCE_HISTORY_EVIDENCE",
            "recorded_environment_snapshot": "PENDING_EXACT_INTERFACE_EVIDENCE",
            "recorded_support": "PENDING_NOT_A_O_ADMISSION",
            "time_safe_does_not_imply_information_authorized": True,
            "not_claimed": ["legal observation", "complete O", "A^O", "full actor-visible history"],
        },
    }
    return inputs


def validate_row_and_build(row: dict[str, Any], episode: dict[str, Any]) -> dict[str, Any]:
    target_raw, actor, prior_physical = validate_target_and_history(row, episode)
    inputs = build_candidate_inputs(episode, target_raw, actor)
    _, persona_index, persona_name = unique_self_persona(episode, actor)
    episode_index = episode["_source_episode_index"]
    trajectory_id = row["trajectory_id"]
    bucket, split = split_for_episode(trajectory_id)
    if episode_index != episode_index_from_trajectory(trajectory_id):
        raise ValueError("trajectory_id episode index does not match source episode")
    current_physical_index = int(row["target_step_index"])
    record = {
        "schema": "light_before_turn_feasibility_v1",
        "candidate_model_payload": inputs["candidate_model_payload"],
        "candidate_surface": inputs["candidate_surface"],
        "supervision": {"recorded_action": row["source_action_A_star"],
                        "admission": "SOURCE_LABEL_NOT_INPUT"},
        "source_history_holdback": inputs["source_history_holdback"],
        "admission": inputs["admission"],
        "provenance": {
            "trajectory_id": trajectory_id,
            "episode_index": episode_index,
            "actor": actor,
            "target_raw_turn_index": target_raw,
            "target_physical_index": current_physical_index,
            "target_source_ref": f"episode:{episode_index}:turn:{target_raw}",
            "split_bucket": bucket,
            "split": split,
            "prior_same_actor_physical_turns": prior_physical,
            "payload_history_turn_refs": inputs["provenance"]["payload_history_turn_refs"],
            "self_persona_agent_index": persona_index,
            "self_persona_matched_name": persona_name,
            "self_persona_source_ref": inputs["provenance"]["persona_source_ref"],
            "source_fields": {
                "recorded_environment_snapshot": f"episode:{episode_index}:turn:{target_raw}:context",
                "recorded_support": f"episode:{episode_index}:turn:{target_raw}:available_actions",
                "recorded_action": f"episode:{episode_index}:turn:{target_raw}:action",
            },
            "model_must_not_read": ["provenance", "supervision", "admission", "source_history_holdback"],
        },
    }
    return record


def candidate_features(inputs: dict[str, Any]) -> bytes:
    """Canonical bytes for temporal noninterference checks; excludes labels/provenance."""
    value = {"candidate_model_payload": inputs["candidate_model_payload"],
             "candidate_surface": inputs["candidate_surface"]}
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _synthetic_episode() -> dict[str, Any]:
    return {
        "_source_episode_index": 17,
        "action": ["self-old-0", "partner-old-1", "self-old-2", "partner-old-3", "gold-target", "future-action"],
        "context": [f"environment-{i}" for i in range(6)],
        "available_actions": [[f"support-{i}"] for i in range(6)],
        "character": ["Ada", "Bert", "Ada", "Bert", "Ada", "Bert"],
        "speech": ["self speech old 0", "partner speech old 1", "self speech old 2",
                   "partner speech old 3", "CURRENT_SPEECH_POISON", "FUTURE_SPEECH_POISON"],
        "emote": ["self emote old 0", "partner emote old 1", "self emote old 2",
                  "partner emote old 3", "CURRENT_EMOTE_POISON", "FUTURE_EMOTE_POISON"],
        "room_objects": [["object"] for _ in range(6)],
        "room_agents": [["Ada", "Bert"] for _ in range(6)],
        "carrying": [[] for _ in range(6)],
        "wearing": [[] for _ in range(6)],
        "wielding": [[] for _ in range(6)],
        "agents": [{"name": "Ada", "persona": "Ada persona"},
                   {"name": "Bert", "persona": "BERT_PERSONA_POISON"}],
        "all_descriptions": "ALL_DESCRIPTIONS_POISON",
    }


def run_functional_negative_controls() -> dict[str, Any]:
    """Executable synthetic noninterference checks, separate from source-join failures."""
    import copy as _copy

    episode = _synthetic_episode()
    baseline = build_candidate_inputs(episode, 4, "Ada")
    baseline_features = candidate_features(baseline)

    current_mutated = _copy.deepcopy(episode)
    for key, poison in (("action", "CURRENT_ACTION_POISON"),
                        ("speech", "CURRENT_SPEECH_POISON_2"),
                        ("emote", "CURRENT_EMOTE_POISON_2")):
        current_mutated[key][4] = poison
    current_inputs = build_candidate_inputs(current_mutated, 4, "Ada")

    future_mutated = _copy.deepcopy(episode)
    future_poisons = []
    for key in PER_TURN_KEYS:
        poison = f"FUTURE_POISON_{key.upper()}"
        future_poisons.append(poison)
        future_mutated[key][5] = [poison] if key in ("available_actions", "room_objects", "room_agents",
                                                     "carrying", "wearing", "wielding") else poison
    future_inputs = build_candidate_inputs(future_mutated, 4, "Ada")

    persona_mutated = _copy.deepcopy(episode)
    persona_mutated["agents"][1]["persona"] = "PARTNER_PERSONA_MUTATION_POISON"
    persona_mutated["all_descriptions"] = "FUTURE_DESCRIPTION_MUTATION_POISON"
    persona_inputs = build_candidate_inputs(persona_mutated, 4, "Ada")

    past_channel_changes: dict[str, bool] = {}
    for channel in CHANNELS:
        changed = _copy.deepcopy(episode)
        changed[channel][2] = f"CHANGED_PAST_SELF_{channel.upper()}"
        past_channel_changes[channel] = candidate_features(build_candidate_inputs(changed, 4, "Ada")) != baseline_features

    current_text = candidate_features(current_inputs).decode("utf-8")
    future_text = candidate_features(future_inputs).decode("utf-8")
    persona_text = candidate_features(persona_inputs).decode("utf-8")
    checks = {
        "current_action_speech_emote_mutation_does_not_change_candidate_features":
            candidate_features(current_inputs) == baseline_features,
        "future_per_turn_mutation_does_not_change_candidate_features":
            candidate_features(future_inputs) == baseline_features,
        "partner_persona_and_all_descriptions_mutation_does_not_change_candidate_features":
            candidate_features(persona_inputs) == baseline_features,
        "all_strictly_past_self_channels_change_candidate_features": all(past_channel_changes.values()),
        "current_poison_values_absent_from_serialized_candidate_features": all(
            poison not in current_text for poison in (
                "CURRENT_ACTION_POISON", "CURRENT_SPEECH_POISON_2", "CURRENT_EMOTE_POISON_2")),
        "future_per_turn_poison_values_absent_from_serialized_candidate_features":
            all(poison not in future_text for poison in future_poisons),
        "partner_persona_and_description_poison_absent_from_serialized_candidate_features":
            all(poison not in persona_text for poison in (
                "PARTNER_PERSONA_MUTATION_POISON", "FUTURE_DESCRIPTION_MUTATION_POISON")),
        "original_partner_persona_and_description_absent_from_serialized_candidate_features":
            all(poison not in baseline_features.decode("utf-8") for poison in (
                "BERT_PERSONA_POISON", "ALL_DESCRIPTIONS_POISON")),
        "partner_history_is_present_but_still_pending":
            any(turn["role"] == "partner" for turn in baseline["candidate_model_payload"]["prior_interaction_history"])
            and baseline["admission"]["prior_partner_action"] == "PENDING_SOURCE_HISTORY_EVIDENCE",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"synthetic noninterference controls failed: {failed}; past channel changes={past_channel_changes}")
    return {"status": "PASS_SYNTHETIC_ONLY", "checks": checks,
            "past_channel_changes_payload": past_channel_changes,
            "scope": "functional candidate-feature comparisons; separate from reference-join rejection tests"}


def review_invariants(record: dict[str, Any]) -> None:
    if record["admission"].get("training_authorized") is not False:
        raise AssertionError("feasibility artifact must never authorize training")
    payload = record["candidate_model_payload"]
    allowed = {"self_persona", "prior_interaction_history", "recorded_environment_snapshot"}
    if set(payload) != allowed:
        raise AssertionError(f"unexpected candidate payload keys: {set(payload)}")
    history = payload["prior_interaction_history"]
    refs = record["provenance"]["payload_history_turn_refs"]
    if len(history) != len(refs):
        raise AssertionError("history items and provenance refs must be parallel")
    previous_turn = -1
    for item, ref in zip(history, refs):
        if set(item) != {"role", "speech", "action", "emote"}:
            raise AssertionError(f"unexpected history item keys: {set(item)}")
        if item.get("role") not in ("self", "partner") or ref.get("role") != item.get("role"):
            raise AssertionError("history role must be explicit and match provenance")
        if ref["raw_turn_index"] <= previous_turn:
            raise AssertionError("history turns must be strictly increasing")
        previous_turn = ref["raw_turn_index"]
        if ref["raw_turn_index"] >= record["provenance"]["target_raw_turn_index"]:
            raise AssertionError("history provenance is not strictly prior")


def parse_jsonl_bytes(data: bytes, source_name: str) -> list[dict[str, Any]]:
    rows = []
    for line_no, raw_line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not raw_line.strip():
            raise ValueError(f"blank JSONL line at {source_name}:{line_no}")
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {source_name}:{line_no}")
        rows.append(value)
    return rows


def load_pinned_sources(pickle_path: Path, view_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bytes, bytes]:
    pickle_bytes = pickle_path.read_bytes()
    pickle_hash = sha256_bytes(pickle_bytes)
    if pickle_hash != EXPECTED_PICKLE_SHA256:
        raise ValueError(f"unexpected pickle SHA-256: {pickle_hash}")
    view_bytes = view_path.read_bytes()
    view_hash = sha256_bytes(view_bytes)
    if view_hash != EXPECTED_VIEW_SHA256:
        raise ValueError(f"unexpected actor-local view SHA-256: {view_hash}")
    # Crucially, unpickle exactly the byte buffer whose expected digest was verified.
    episodes = pickle.loads(pickle_bytes)
    if not isinstance(episodes, list):
        raise ValueError("pinned pickle must decode to a list of episodes")
    rows = parse_jsonl_bytes(view_bytes, str(view_path))
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} view rows; got {len(rows)}")
    return episodes, rows, pickle_bytes, view_bytes


def output_path_guard(input_paths: tuple[Path, ...], output: Path) -> None:
    resolved_output = output.resolve()
    for source in input_paths:
        resolved_source = source.resolve()
        if resolved_output == resolved_source or resolved_output in resolved_source.parents or resolved_source in resolved_output.parents:
            raise ValueError(f"input/output paths overlap: {resolved_source} and {resolved_output}")
    if output.exists():
        raise FileExistsError(f"refusing existing output path: {output}")


def build_all(rows: list[dict[str, Any]], episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for line_no, row in enumerate(rows, 1):
        trajectory_id = row.get("trajectory_id")
        if not isinstance(trajectory_id, str):
            raise ValueError(f"trajectory_id missing at view line {line_no}")
        episode_index = episode_index_from_trajectory(trajectory_id)
        if not 0 <= episode_index < len(episodes):
            raise ValueError(f"episode index out of range at view line {line_no}")
        episode = episodes[episode_index]
        if not isinstance(episode, dict):
            raise ValueError(f"episode {episode_index} is not an object")
        episode = dict(episode)
        episode["_source_episode_index"] = episode_index
        record = validate_row_and_build(row, episode)
        key = (trajectory_id, int(row["target_step_index"]), norm(row["actor"]))
        if key in seen:
            raise ValueError(f"duplicate source-view key at line {line_no}: {key}")
        seen.add(key)
        review_invariants(record)
        output.append(record)
    return output


def run_build(pickle_path: Path, view_path: Path, output: Path) -> dict[str, Any]:
    inputs = (pickle_path, view_path, LINEAGE, TRAINER, TRAINER_README)
    output_path_guard(inputs, output)
    episodes, rows, pickle_bytes, view_bytes = load_pinned_sources(pickle_path, view_path)
    negative_controls = run_functional_negative_controls()
    records = build_all(rows, episodes)
    if len(records) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} built records; got {len(records)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    payload_path = output / "before_turn_candidates.jsonl"
    with payload_path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    split_counts: dict[str, dict[str, int]] = {}
    for split_name in ("train", "validation", "excluded_bucket9"):
        subset = [record for record in records if record["provenance"]["split"] == split_name]
        split_counts[split_name] = {
            "rows": len(subset),
            "episodes": len({record["provenance"]["trajectory_id"] for record in subset}),
            "actor_trajectory_units": len({(record["provenance"]["trajectory_id"],
                                              norm(record["provenance"]["actor"])) for record in subset}),
        }
    channel_counts = {role: {channel: 0 for channel in CHANNELS} for role in ("self", "partner")}
    for record in records:
        for item in record["candidate_model_payload"]["prior_interaction_history"]:
            for channel in CHANNELS:
                channel_counts[item["role"]][channel] += int(item[channel] is not None)
    manifest = {
        "schema": "light_before_turn_feasibility_manifest_v1",
        "status": "FEASIBILITY_CANDIDATES_ONLY",
        "training_authorized": False,
        "input_pickle_path": str(pickle_path.resolve()),
        "input_pickle_sha256": sha256_bytes(pickle_bytes),
        "input_view_path": str(view_path.resolve()),
        "input_view_sha256": sha256_bytes(view_bytes),
        "input_rows": len(rows),
        "output_rows": len(records),
        "lineage_checker_path": str(LINEAGE.resolve()),
        "lineage_checker_sha256": sha256_file(LINEAGE),
        "trainer_path": str(TRAINER.resolve()),
        "trainer_sha256": sha256_file(TRAINER),
        "trainer_protocol_readme_path": str(TRAINER_README.resolve()),
        "trainer_protocol_readme_sha256": sha256_file(TRAINER_README),
        "input_contract": INPUT_CONTRACT,
        "input_contract_sha256": input_contract_sha256(),
        "functional_noninterference_controls": negative_controls,
        "split_counts": split_counts,
        "prior_history_channel_item_counts": channel_counts,
        "builder_path": str(Path(__file__).resolve()),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "test_path": str(Path(__file__).with_name("test_build_light_before_turn_v1.py").resolve()),
        "test_sha256": sha256_file(Path(__file__).with_name("test_build_light_before_turn_v1.py")),
        "split": {"method": "int(SHA256(trajectory_id UTF-8).hexdigest()[:8],16) modulo 10",
                  "buckets": {"train": "0-6", "validation": "7-8", "excluded_bucket9": "9"}},
        "output_files_sha256": {"before_turn_candidates.jsonl": sha256_file(payload_path)},
        "output_role": "source-preserving feasibility artifact; channel admission remains pending",
    }
    with (output / "artifact_manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pickle", type=Path, default=PICKLE)
    parser.add_argument("--view", type=Path, default=VIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        manifest = run_build(args.pickle, args.view, args.output)
    except (OSError, ValueError, AssertionError, pickle.UnpicklingError) as exc:
        print(f"before-turn feasibility build failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
