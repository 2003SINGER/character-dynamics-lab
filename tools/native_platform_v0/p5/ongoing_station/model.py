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
    if len(archive_goals) != 1:
        raise ValueError("station AuthorBundle must author exactly one same-note archive-by-deadline goal")
    archive = archive_goals[0]
    if (archive.get("hard") is not True or type(archive.get("deadline")) is not int
            or not 1 <= archive["deadline"] <= profile.horizon
            or type(archive.get("start")) is not int
            or not 0 <= archive["start"] <= archive["deadline"]):
        raise ValueError("station archive goal must be a hard absolute-deadline constraint inside the profile horizon")
    # A native response is a domain precondition, not an additional author goal.
    # If the bundle does author the old response-before-archive order, retain and
    # monitor it; do not require authors to duplicate that domain fact.
    if len(response_order) > 1:
        raise ValueError("station AuthorBundle supports at most one response-before-archive constraint")
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


def derive_story_requirements(projection: AuthorProjection, archive_constraint: Mapping[str, Any],
                              note_id: int) -> dict[str, Any]:
    """Project the narrow same-note handover occurrence/order pair for M4.

    The AuthorBundle remains the source of truth. This projection is planner input,
    not another editable goal schema.
    """
    if not isinstance(projection, AuthorProjection) or type(note_id) is not int or note_id <= 0:
        raise ValueError("a bound author projection and exact native note ID are required")
    archive_source = archive_constraint.get("source_constraint", {})
    if (archive_source.get("kind") != "event_by_deadline"
            or archive_source.get("event") != "note_archived"
            or archive_source.get("filters", {}).get("item") != "note"):
        raise ValueError("story requirements must be anchored to the registered same-note archive goal")
    archive_deadline = archive_source.get("deadline")
    archive_start = archive_source.get("start")
    if (type(archive_deadline) is not int or not 1 <= archive_deadline <= 24
            or type(archive_start) is not int or not 0 <= archive_start <= archive_deadline):
        raise ValueError("archive deadline must be an absolute native scenario minute")

    sources = [row.get("source_constraint", {}) for row in projection.constraints]
    handovers = [row for row in sources if row.get("kind") == "event_by_deadline"
                 and row.get("event") == "note_handed_over"
                 and row.get("filters", {}).get("item") == "note"]
    orders = [row for row in sources if row.get("kind") == "event_order"
              and row.get("before", {}).get("event") == "note_handed_over"
              and row.get("after", {}).get("event") == "note_archived"
              and row.get("before", {}).get("filters", {}).get("item") == "note"
              and row.get("after", {}).get("filters", {}).get("item") == "note"]
    if len(handovers) != len(orders) or len(handovers) > 1:
        raise ValueError("a handover plot point requires one registered occurrence goal and one strict before-archive constraint")
    handover = None
    if handovers:
        count = handovers[0]
        order = orders[0]
        expected_handover_filter = {"actor": "B", "recipient": "A", "item": "note"}
        order_window = order.get("start"), order.get("deadline")
        if (count.get("filters") != expected_handover_filter
                or order.get("before", {}).get("filters") != expected_handover_filter
                or order.get("after", {}).get("filters") != {"item": "note"}
                or order.get("order") != "EVENT_KEY"
                or type(count.get("start")) is not int or type(count.get("deadline")) is not int
                or order_window != (count.get("start"), count.get("deadline"))
                or count.get("deadline") > archive_deadline
                or count.get("hard") is not True or order.get("hard") is not True):
            raise ValueError("handover requirements must force B→A of the same note strictly before archive within the goal deadline")
        handover_row = next(row for row in projection.constraints
                            if row.get("source_constraint") == count)
        order_row = next(row for row in projection.constraints
                         if row.get("source_constraint") == order)
        handover = {"event_count_constraint_id": handover_row["constraint_id"],
                    "order_constraint_id": order_row["constraint_id"],
                    "event_type": "p5_note_handed_over", "actor_alias": "B",
                    "recipient_alias": "A", "before_event_type": "p5_note_archived",
                    "start_minute": int(count["start"]),
                    "deadline_minute": int(count["deadline"])}
    recognized_ids = {archive_constraint["constraint_id"]}
    for row in projection.constraints:
        source = row.get("source_constraint", {})
        if (source.get("kind") == "event_order"
                and source.get("before", {}).get("event") == "note_response"
                and source.get("before", {}).get("filters", {}).get("item") == "note"
                and source.get("after", {}).get("event") == "note_archived"
                and source.get("after", {}).get("filters", {}).get("item") == "note"):
            recognized_ids.add(row["constraint_id"])
    if handovers:
        recognized_ids.update((handover["event_count_constraint_id"], handover["order_constraint_id"]))
    residual = [{"constraint_id": row["constraint_id"], "kind": row["kind"],
                 "source_constraint_sha256": row["source_constraint_sha256"]}
                for row in projection.constraints if row["constraint_id"] not in recognized_ids]
    return {"source_bundle_id": projection.bundle_id, "source_version": projection.version,
            "source_sha256": projection.source_sha256,
            "archive_constraint_id": archive_constraint["constraint_id"],
            "archive_start_minute": archive_start,
            "archive_deadline_minute": archive_deadline, "note_id": note_id,
            "required_handover": handover, "residual_constraints": residual}


def _plain(value):
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


__all__ = ["PROFILE_SCHEMA", "AUTHOR_SCHEMA", "StationProfile", "AuthorProjection",
           "load_profile", "validate_author", "compile_projection", "derive_story_requirements"]
