"""Small JSON-safe contracts for one online actor/author control session."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


class ContractError(ValueError):
    """Input is outside the versioned online integration contract."""


def finite_number(value: object) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def uid(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(f"{label} must be a non-negative integer uid")
    return value


def nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value


def validate_actor_view(view: object) -> Mapping[str, Any]:
    if not isinstance(view, Mapping):
        raise ContractError("actor_view must be an object")
    if view.get("event") != "native_recruit_actor_view" or view.get("version") != 1:
        raise ContractError("unsupported actor view event or version")
    allowed = {"event", "version", "time", "npc_uid", "mode", "role", "job",
               "home_site_id", "current_site_id", "leader_at_home", "eligible_recruits",
               "hired_members", "hired_member_count", "native_recruit_population_guard",
               "native_recruit_raid_site_available", "faction_id"}
    if set(view) != allowed:
        raise ContractError("ActorView fields must match the frozen local-observation schema")
    if not finite_number(view.get("time")) or view["time"] < 0:
        raise ContractError("actor view time must be finite and non-negative")
    leader = uid(view.get("npc_uid"), "actor_view.npc_uid")
    role = view.get("role")
    if (not isinstance(role, Mapping) or role.get("kind") != "civilised"
            or role.get("profession") != "pirate" or role.get("is_leader") is not True):
        raise ContractError("actor view must describe a civilised Pirate leader")
    if view.get("mode") not in ("loaded", "simulated"):
        raise ContractError("actor mode must be loaded or simulated")
    if view.get("job") is not None and not isinstance(view.get("job"), Mapping):
        raise ContractError("actor job must be null or an object")
    for key in ("home_site_id", "current_site_id"):
        nonempty(view.get(key), f"actor_view.{key}")
    if type(view.get("leader_at_home")) is not bool:
        raise ContractError("leader_at_home must be a boolean")
    # This is a native aggregate guard. The source contract computes it from
    # more than three eligible home-population pirates; Python does not estimate it.
    if type(view.get("native_recruit_population_guard")) is not bool:
        raise ContractError("native_recruit_population_guard must be a boolean")
    if type(view.get("native_recruit_raid_site_available")) is not bool:
        raise ContractError("native_recruit_raid_site_available must be a boolean")
    for key in ("eligible_recruits", "hired_members"):
        rows = view.get(key)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise ContractError(f"{key} must be an array")
        seen: set[int] = set()
        for row in rows:
            if not isinstance(row, Mapping):
                raise ContractError(f"{key} rows must be objects")
            target = uid(row.get("npc_uid"), f"{key}.npc_uid")
            if target == leader or target in seen:
                raise ContractError(f"{key} contains leader uid or duplicate uid")
            seen.add(target)
            if row.get("mode") not in ("loaded", "simulated"):
                raise ContractError(f"{key}.mode must be loaded or simulated")
            distance = row.get("distance_3d")
            if not finite_number(distance) or distance < 0 or distance > 24:
                raise ContractError(f"{key}.distance_3d must be within native 24m visibility")
    if view.get("hired_member_count") != len(view["hired_members"]):
        raise ContractError("hired_member_count must match ActorView hired_members")
    return view


def validate_command(command: object, actor_uid: int, obligations: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(command, Mapping):
        raise ContractError("author command must be an object")
    if set(command) != {"op", "goal_id", "version", "target_uid", "hired_by_uid", "deadline"}:
        raise ContractError("author command fields must match the structured goal contract")
    op = command.get("op")
    if op not in ("append", "edit"):
        raise ContractError("author command op must be append or edit")
    goal_id = nonempty(command.get("goal_id"), "goal_id")
    version = command.get("version")
    if type(version) is not int or version < 1:
        raise ContractError("version must be a positive integer")
    existing = obligations.get(goal_id)
    if op == "append" and existing is not None:
        raise ContractError("append cannot replace an existing goal_id")
    if op == "edit" and existing is None:
        raise ContractError("edit requires an existing goal_id")
    expected = 1 if existing is None else existing["versions"][-1]["version"] + 1
    if version != expected:
        raise ContractError(f"version must be the next immutable version ({expected})")
    target = uid(command.get("target_uid"), "target_uid")
    hired_by = uid(command.get("hired_by_uid"), "hired_by_uid")
    if hired_by != actor_uid:
        raise ContractError("this native obligation only supports hired_by_uid equal to actor uid")
    deadline = command.get("deadline")
    if not finite_number(deadline) or deadline < 0:
        raise ContractError("deadline must be an absolute non-negative game time")
    if existing is not None and deadline != existing["versions"][0]["deadline"]:
        raise ContractError("edit preserves the original absolute deadline")
    return {
        "op": op, "goal_id": goal_id, "version": version,
        "kind": "eventual_job_hired", "target_uid": target,
        "hired_by_uid": hired_by, "deadline": float(deadline),
        "source": "AUTHOR",
    }


def evidence_parts(evidence: object) -> tuple[list[dict[str, Any]], float | None, str | None]:
    """Decode separated global monitor evidence; never merge it into ActorView."""
    if evidence is None:
        return [], None, None
    if isinstance(evidence, Mapping):
        events = evidence.get("events", [])
        coverage = evidence.get("coverage_through")
        source = evidence.get("source_id")
        if coverage is not None and (not finite_number(coverage) or coverage < 0):
            raise ContractError("coverage_through must be an absolute non-negative game time")
        if source is not None:
            nonempty(source, "native evidence source_id")
            folded_source = source.casefold()
            if "planner" in folded_source or "predict" in folded_source:
                # Structurally reject obvious planner/prediction provenance;
                # the runner still owns the actual trusted file/channel.
                coverage = None
                source = None
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            raise ContractError("native evidence events must be an array")
        rows = list(events)
        through = float(coverage) if coverage is not None else None
        source_id = source
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        rows, through, source_id = list(evidence), None, None
    else:
        raise ContractError("native_evidence must be an array or monitor envelope")
    clean: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ContractError("native evidence rows must be objects")
        event_name = row.get("event")
        if event_name not in ("native_recruit_job_observed",
                              "native_recruit_unattributed_hire_observed"):
            continue
        source_label = str(row.get("source", "")).casefold()
        if (source_label == "planner" or row.get("prediction_only") is True
                or row.get("native_settlement") in ("not executed", "awaiting Veloren", "not asserted")):
            continue
        if row.get("job") != "Hired":
            continue
        event = dict(row)
        event["target_uid"] = uid(row.get("target_uid", row.get("recipient_uid")),
                                  "native event target_uid")
        hired_by = row.get("hired_by_uid", row.get("leader_uid", row.get("job_actor_uid")))
        event["hired_by_uid"] = uid(hired_by, "native event hired_by_uid")
        for identity_key in ("leader_uid", "job_actor_uid", "source_uid"):
            identity = row.get(identity_key)
            if identity is not None and identity != event["hired_by_uid"]:
                raise ContractError(f"native event {identity_key} does not match hired_by_uid")
        if row.get("recipient_uid") is not None and row["recipient_uid"] != event["target_uid"]:
            raise ContractError("native event recipient_uid does not match target_uid")
        game_time = row.get("game_time", row.get("time"))
        if not finite_number(game_time) or game_time < 0:
            raise ContractError("native job_hired event needs absolute game_time")
        event["game_time"] = float(game_time)
        event["source_id"] = row.get("source_id") or row.get("request_id") or source_id
        nonempty(event["source_id"], "native event source_id")
        if event_name == "native_recruit_job_observed" and not event.get("request_id"):
            # An unattributed global observation can still witness an author
            # condition, but request lifecycle closure requires correlation.
            event["request_id"] = None
        clean.append(event)
    return clean, through, source_id


def json_safe(value: Any) -> Any:
    """Copy the supported JSON subset and reject accidental opaque objects."""
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ContractError("JSON object keys must be strings")
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    raise ContractError(f"value is not JSON-safe: {type(value).__name__}")
