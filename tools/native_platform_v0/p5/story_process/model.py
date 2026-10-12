"""Strict author request schema for the bounded native story-process slice."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "story-process-request-v1"
METHODS = {"file_by_B", "return_then_file_by_A"}
TASK_KINDS = {"handover_note", "archive_note"}
MODES = {"zero", "result_only", "process", "direct", "locked_fragment"}
GRANT_KEYS = {"grant_id", "scenario_id", "actor_aliases", "task_kinds", "valid_until_minute"}


def default_actor_postresponse() -> dict[str, dict[str, str]]:
    """Shared initial content law; romance response and task disposition stay distinct."""
    return {"accepted": {"B_archive": "WILLING", "B_return": "WILLING", "A_archive": "WILLING"},
            "rejected": {"B_archive": "UNWILLING", "B_return": "WILLING", "A_archive": "WILLING"}}


@dataclass(frozen=True)
class StoryProcessRequest:
    raw: Mapping[str, Any]
    request_id: str
    version: int
    scenario_id: str | None
    objective: Mapping[str, Any]
    control: Mapping[str, Any]
    actor_postresponse: Mapping[str, Any]
    task_control_grant: Mapping[str, Any]
    edit_policy: Mapping[str, Any]
    locked_fragment: Mapping[str, Any] | None


def _exact(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{label} requires exact keys {sorted(keys)}")
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def story_event_registry():
    """Return the existing P5 TypedIR registry plus this slice's native ledger events."""
    from tools.native_platform_v0.p5.bundle import p5_registry
    from tools.trajectory_constraints_v0.types import (
        Owner, Registry, RegistryEntry, TimeMode, TypeSpec, ValueKind,
    )
    additions = (
        RegistryEntry("p5_note_handed_over", "1", Owner.LEDGER, "NoteHandover",
                      {"actor": "Actor", "recipient": "Actor", "item": "Item"},
                      TypeSpec(ValueKind.EVENT), "ledger_event_v1", ("native_note_handover_receipt",), TimeMode.EVENT),
        RegistryEntry("p5_note_archived", "1", Owner.LEDGER, "NoteArchived",
                      {"actor": "Actor", "item": "Item"}, TypeSpec(ValueKind.EVENT),
                      "ledger_event_v1", ("native_note_archive_receipt",), TimeMode.EVENT),
    )
    return Registry(p5_registry().entries() + additions)


def load_request(raw: Mapping[str, Any], *, allow_template: bool = False) -> StoryProcessRequest:
    """Validate only the authored, bounded note-archiving request; fail closed."""
    keys = {"schema", "request_id", "version", "scenario_id", "objective", "control", "actor_postresponse",
            "task_control_grant", "edit_policy", "locked_fragment"}
    raw = _exact(raw, keys, "request")
    if raw["schema"] != SCHEMA:
        raise ValueError("unsupported story-process request schema")
    request_id = _nonempty(raw["request_id"], "request_id")
    if raw["scenario_id"] is None and allow_template:
        scenario_id = None
    else:
        scenario_id = _nonempty(raw["scenario_id"], "scenario_id")
    if type(raw["version"]) is not int or raw["version"] < 1:
        raise ValueError("version must be a positive integer")
    objective = _exact(raw["objective"], {"kind", "note_id", "by_minute", "deadline_basis",
                                          "response_event_type", "archive_event_type"}, "objective")
    note_id = objective["note_id"]
    if (objective["kind"] != "archive_same_note_after_response"
            or (note_id is not None and (type(note_id) is not int or note_id <= 0))
            or type(objective["by_minute"]) is not int or not 1 <= objective["by_minute"] <= 24
            or objective["deadline_basis"] != "absolute_scenario_minute"
            or objective["response_event_type"] != "p5_note_response"
            or objective["archive_event_type"] != "p5_note_archived"):
        raise ValueError("objective must require this exact note archived after native response by an absolute minute in [1,24]")
    control = _exact(raw["control"], {"mode", "file_actor", "allowed_methods", "source"}, "control")
    if control["mode"] not in MODES:
        raise ValueError("unsupported control mode")
    if control["source"] not in {"AUTHORED", "SYSTEM"}:
        raise ValueError("control source must be AUTHORED or SYSTEM")
    if control["mode"] == "direct" and control["source"] != "AUTHORED":
        raise ValueError("direct control requires AUTHORED provenance")
    if control["mode"] != "direct" and control["source"] == "AUTHORED":
        raise ValueError("AUTHORED source is reserved for direct control")
    if control["file_actor"] not in {None, "A", "B"}:
        raise ValueError("file_actor must be A, B, or null")
    methods = control["allowed_methods"]
    if not isinstance(methods, list) or not methods or any(m not in METHODS for m in methods) or len(set(methods)) != len(methods):
        raise ValueError("allowed_methods must be a nonempty unique subset of registered methods")
    postresponse = _exact(raw["actor_postresponse"], {"accepted", "rejected"}, "actor_postresponse")
    for outcome, row in postresponse.items():
        row = _exact(row, {"B_archive", "B_return", "A_archive"}, f"actor_postresponse.{outcome}")
        if any(value not in {"WILLING", "UNWILLING", "LOCAL_CHOICE"} for value in row.values()):
            raise ValueError("postresponse role dispositions must be WILLING, UNWILLING, or LOCAL_CHOICE")
    if (postresponse["rejected"]["B_archive"] != "UNWILLING"
            or postresponse["rejected"]["B_return"] == "UNWILLING"
            or postresponse["rejected"]["A_archive"] == "UNWILLING"
            or any(postresponse["accepted"][key] == "UNWILLING"
                   for key in ("B_archive", "B_return", "A_archive"))):
        raise ValueError("authored role law requires rejection→return/filer-A and both accepted-response methods to remain legal candidates")
    grant = _exact(raw["task_control_grant"], GRANT_KEYS, "task_control_grant")
    template_scenario = scenario_id is None and allow_template and grant["scenario_id"] is None
    if ((grant["scenario_id"] != scenario_id and not template_scenario) or not isinstance(grant["grant_id"], str)
            or not grant["grant_id"] or grant["actor_aliases"] != ["A", "B"]
            or grant["task_kinds"] != ["handover_note", "archive_note"]
            or grant["valid_until_minute"] != 24):
        raise ValueError("scenario task grant is not the fixed native archive-slice grant")
    policy = _exact(raw["edit_policy"], {"editable_future_fields", "settled_fields_immutable", "grant_immutable"}, "edit_policy")
    if (policy["editable_future_fields"] != ["control.file_actor", "control.allowed_methods"]
            or policy["settled_fields_immutable"] is not True or policy["grant_immutable"] is not True):
        raise ValueError("future-edit policy must preserve settled history and the original task grant")
    fragment = raw["locked_fragment"]
    if control["mode"] == "locked_fragment":
        fragment = _exact(fragment, {"sequence", "sequence_sha256", "entry_guard", "abort_policy"}, "locked_fragment")
        sequence = fragment["sequence"]
        if not isinstance(sequence, list) or not sequence:
            raise ValueError("locked fragment sequence must be nonempty")
        for row in sequence:
            _exact(row, {"actor_alias", "task_kind", "item_ref", "destination_ref"}, "locked task")
            if row["actor_alias"] not in {"A", "B"} or row["task_kind"] not in TASK_KINDS:
                raise ValueError("locked task actor or kind is unsupported")
            if row["item_ref"] != "objective.note" or row["destination_ref"] not in {"archive", "handover"}:
                raise ValueError("locked task must use registered note and destination aliases")
        digest = sha256(json.dumps(sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if fragment["sequence_sha256"] != digest:
            raise ValueError("locked fragment sequence hash mismatch")
        guard = _exact(fragment["entry_guard"], {"response_required", "note_holder_alias"}, "locked entry guard")
        if guard["response_required"] is not True or guard["note_holder_alias"] not in {"A", "B"}:
            raise ValueError("locked entry guard is unsupported")
        if fragment["abort_policy"] != "ABORT_LOCKED_CORE":
            raise ValueError("locked fragments must abort without rewriting their core")
    elif fragment is not None:
        raise ValueError("locked_fragment must be null outside locked_fragment mode")
    return StoryProcessRequest(deepcopy(dict(raw)), request_id, raw["version"], scenario_id,
                              deepcopy(dict(objective)), deepcopy(dict(control)),
                              deepcopy(dict(postresponse)), deepcopy(dict(grant)),
                              deepcopy(dict(policy)), deepcopy(dict(fragment)) if fragment else None)


def bind_note_id(previous: StoryProcessRequest, note_id: int) -> StoryProcessRequest:
    """Bind the authored note alias to its ID only after native creation is sealed."""
    if not isinstance(previous, StoryProcessRequest):
        raise TypeError("previous must be a validated StoryProcessRequest")
    if previous.objective["note_id"] is not None:
        raise ValueError("authored note identity has already been bound")
    if type(note_id) is not int or note_id <= 0:
        raise ValueError("native note ID must be a positive integer")
    raw = deepcopy(dict(previous.raw))
    raw["objective"]["note_id"] = note_id
    return load_request(raw, allow_template=previous.scenario_id is None)


def bind_scene(previous: StoryProcessRequest, scenario_id: str) -> StoryProcessRequest:
    """Bind the template to a real scene and bind its immutable task grant."""
    if not isinstance(previous, StoryProcessRequest):
        raise TypeError("previous must be a validated StoryProcessRequest")
    if previous.scenario_id is not None or previous.task_control_grant["scenario_id"] is not None:
        raise ValueError("request scenario has already been bound")
    value = _nonempty(scenario_id, "scenario_id")
    raw = deepcopy(dict(previous.raw))
    raw["scenario_id"] = value
    raw["task_control_grant"]["scenario_id"] = value
    return load_request(raw, allow_template=previous.objective["note_id"] is None)


def validate_future_edit(previous: StoryProcessRequest, proposed: Mapping[str, Any]) -> StoryProcessRequest:
    """Allow only the explicitly editable future controller fields."""
    updated = load_request(proposed)
    if (updated.request_id != previous.request_id or updated.version != previous.version + 1
            or updated.scenario_id != previous.scenario_id
            or updated.objective != previous.objective
            or updated.raw["actor_postresponse"] != previous.raw["actor_postresponse"]
            or updated.task_control_grant != previous.task_control_grant
            or updated.edit_policy != previous.edit_policy
            or updated.locked_fragment != previous.locked_fragment
            or updated.control["mode"] != previous.control["mode"]
            or updated.control["source"] != previous.control["source"]):
        raise ValueError("edit may change only file_actor/allowed_methods for future unsettled requirements")
    return updated


__all__ = ["StoryProcessRequest", "load_request", "bind_scene", "bind_note_id",
           "validate_future_edit", "story_event_registry", "default_actor_postresponse", "SCHEMA", "METHODS"]
