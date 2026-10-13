"""Strict author/profile adapters for the opt-in ongoing station.

The nested AuthorBundle remains the sole author source for goals. Bindings add
only the execution-control provenance that the legacy strict bundle schema
does not represent; runtime projections always identify their source bundle.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

PROFILE_SCHEMA = "ongoing-station-profile-v1"
AUTHOR_SCHEMA = "ongoing-station-author-v1"
MODES = {"zero", "result_only", "process", "direct", "locked_fragment"}
METHODS = {"file_by_B", "return_then_file_by_A"}


def _exact(value, keys, label):
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise ValueError(f"{label} requires exact keys {sorted(keys)}")
    return value


def _hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StationProfile:
    raw: Mapping[str, Any]
    station_id: str
    version: int
    horizon: int
    author: Mapping[str, Any] | None


@dataclass(frozen=True)
class AuthorProjection:
    station_id: str
    bundle_id: str
    version: int
    source_sha256: str
    constraints: tuple[Mapping[str, Any], ...]
    bindings: Mapping[str, Any]


def load_profile(raw: Mapping[str, Any] | None, *, max_horizon: int = 48) -> StationProfile | None:
    if raw is None:
        return None
    row = _exact(raw, {"schema", "station_id", "profile_version", "horizon", "author"},
                 "ongoing_station")
    if row["schema"] != PROFILE_SCHEMA:
        raise ValueError("unsupported ongoing station profile schema")
    if not isinstance(row["station_id"], str) or not row["station_id"].strip():
        raise ValueError("station_id must be a nonempty identifier")
    if type(row["profile_version"]) is not int or row["profile_version"] != 1:
        raise ValueError("profile_version must be 1")
    if type(row["horizon"]) is not int or not 1 <= row["horizon"] <= max_horizon:
        raise ValueError(f"ongoing station horizon must be in [1,{max_horizon}]")
    author = row["author"]
    if author is not None:
        author = validate_author(author)
    return StationProfile(deepcopy(dict(row)), row["station_id"], 1, row["horizon"], author)


def validate_author(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    row = _exact(raw, {"schema", "bundle", "bindings"}, "ongoing station author")
    if row["schema"] != AUTHOR_SCHEMA:
        raise ValueError("unsupported ongoing station author schema")
    if not isinstance(row["bundle"], Mapping):
        raise ValueError("author bundle must be an object")
    if not isinstance(row["bindings"], list):
        raise ValueError("bindings must be an array")
    ids = set()
    for index, item in enumerate(row["bindings"]):
        item = _exact(item, {"constraint_id", "control", "locked_fragment"},
                      f"bindings[{index}]")
        cid = item["constraint_id"]
        if not isinstance(cid, str) or not cid.strip() or cid in ids:
            raise ValueError("binding constraint IDs must be unique nonempty strings")
        ids.add(cid)
        control = _exact(item["control"], {"mode", "file_actor", "allowed_methods", "source"},
                         f"bindings[{index}].control")
        if control["mode"] not in MODES:
            raise ValueError("unsupported station control mode")
        if control["file_actor"] not in {None, "A", "B"}:
            raise ValueError("file_actor must be A, B, or null")
        methods = control["allowed_methods"]
        if (not isinstance(methods, list) or not methods or len(methods) != len(set(methods))
                or any(method not in METHODS for method in methods)):
            raise ValueError("allowed_methods must be unique registered methods")
        expected_source = "AUTHORED" if control["mode"] == "direct" else "SYSTEM"
        if control["source"] != expected_source:
            raise ValueError("control source is inconsistent with the selected mode")
        fragment = item["locked_fragment"]
        if control["mode"] == "locked_fragment":
            fragment = _exact(fragment, {"sequence", "sequence_sha256", "entry_guard", "abort_policy"},
                              f"bindings[{index}].locked_fragment")
            sequence = fragment["sequence"]
            if not isinstance(sequence, list) or not sequence:
                raise ValueError("locked sequence must be nonempty")
            digest = _hash(sequence)
            if fragment["sequence_sha256"] != digest:
                raise ValueError("locked sequence hash mismatch")
            for task in sequence:
                task = _exact(task, {"actor_alias", "task_kind", "item_ref", "destination_ref"},
                              "locked sequence task")
                if (task["actor_alias"] not in {"A", "B"}
                        or task["task_kind"] not in {"archive_note", "handover_note"}
                        or task["item_ref"] != "objective.note"
                        or task["destination_ref"] not in {"archive", "handover"}):
                    raise ValueError("locked sequence contains an unsupported registered task")
            guard = _exact(fragment["entry_guard"], {"response_required", "note_holder_alias"},
                           "locked entry guard")
            if guard["response_required"] is not True or guard["note_holder_alias"] not in {"A", "B"}:
                raise ValueError("locked entry guard is unsupported")
            if fragment["abort_policy"] != "ABORT_LOCKED_CORE":
                raise ValueError("locked sequence must use ABORT_LOCKED_CORE")
        elif fragment is not None:
            raise ValueError("locked_fragment must be null outside locked mode")
    return deepcopy(dict(row))


def compile_projection(profile: StationProfile, *, entities=None) -> AuthorProjection | None:
    if profile.author is None:
        return None
    from tools.native_platform_v0.p5.bundle import load_bundle
    from tools.native_platform_v0.p5.story_process.model import story_event_registry

    raw_bundle = deepcopy(dict(profile.author["bundle"]))
    bundle = load_bundle(raw_bundle, registry=story_event_registry(), entities=entities)
    binding_map = {row["constraint_id"]: deepcopy(dict(row))
                   for row in profile.author["bindings"]}
    goal_ids = {goal.constraint_id for goal in bundle.goals}
    if set(binding_map) != goal_ids:
        raise ValueError("every AuthorBundle constraint requires exactly one control binding")
    raw_constraints = {row["id"]: row for row in raw_bundle["constraints"]}
    archive_goals = [row for row in raw_constraints.values()
                     if row.get("kind") == "event_by_deadline"
                     and row.get("event") == "note_archived"
                     and row.get("filters", {}).get("item") == "note"]
    response_order = [row for row in raw_constraints.values()
                      if row.get("kind") == "event_order"
                      and row.get("before", {}).get("event") == "note_response"
                      and row.get("before", {}).get("filters", {}).get("item") == "note"
                      and row.get("after", {}).get("event") == "note_archived"
                      and row.get("after", {}).get("filters", {}).get("item") == "note"]
    if not archive_goals or not response_order:
        raise ValueError("station AuthorBundle must author same-note archive-by-deadline and response-before-archive constraints")
    projection_constraints = []
    for goal in bundle.goals:
        binding = binding_map[goal.constraint_id]
        projection_constraints.append({
            "constraint_id": goal.constraint_id,
            "kind": goal.kind,
            "source_bundle_id": bundle.bundle_id,
            "source_version": bundle.version,
            "source_constraint_sha256": _hash(_plain(goal.source)),
            "control": deepcopy(binding["control"]),
            "locked_fragment": deepcopy(binding["locked_fragment"]),
            "source_constraint": _plain(goal.source),
        })
    return AuthorProjection(profile.station_id, bundle.bundle_id, bundle.version,
                            _hash(_plain(profile.author)), tuple(projection_constraints), binding_map)


def _plain(value):
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


__all__ = ["PROFILE_SCHEMA", "AUTHOR_SCHEMA", "StationProfile", "AuthorProjection",
           "load_profile", "validate_author", "compile_projection"]
