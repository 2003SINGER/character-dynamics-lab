"""Bounded supervisor for one continuous G1 multi-actor process.

This adapter keeps native actor views separate, feeds one shared persistent
controller, and advances plans only from correlated native terminal receipts.
It intentionally does not reuse the three-trial v0 runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
from typing import Any, Mapping, Sequence

from tools.character_dynamics_online_v0.process_controller import (
    new_process_session, step_process,
)
from tools.character_dynamics_online_v0.runner import JsonlTail, append_jsonl_once, local_now
from tools.veloren_native_decision_v1.loaded_msg_pair import (
    DISK_FLOOR_BYTES, TELEMETRY_BYTE_CAP, TELEMETRY_RECORD_CAP,
    LoadedMsgChain, _validate_userdata_manifest, assets_tree_sha256, sha256_file,
)

SCHEMA = "character_dynamics_g1_observation_v0"
RULE_VERSION = "recon-v1"
LEADER_UID = 476
SCOUT_UID = 433
DEFAULT_ACTORS = (SCOUT_UID, LEADER_UID)
MAX_WALL_SECONDS = 720.0
MAX_REQUESTS = 30
MAX_RECORDS = 20_000
MAX_BYTES = 64 * 1024 * 1024
MAX_NATIVE_SECONDS = 720
SHUTDOWN_GRACE_SECONDS = 5
SUPERVISOR_EXIT_WAIT_SECONDS = 25.0
DELIVERY_DISPATCH_RADIUS = 24.0
G1_ACTIONS = {"survey_marker", "deliver_report", "rally_marker"}
ACTION_COST = {"survey_marker": 1.0, "deliver_report": 1.0,
               "RecruitMember": 2.0, "rally_marker": 1.0}
RUN_ROOT = Path("_local_data/veloren_online_integration_v0")
CLEARED_ENV = (
    "VELOREN_NATIVE_REQUESTS", "VELOREN_RTSIM", "VELOREN_TERRAIN",
    "RTSIM_NOLOAD", "RTSIM_IGNORE_VERSION", "VELOREN_NATIVE_EVENTS",
    "VELOREN_NATIVE_OBSERVE", "VELOREN_NATIVE_OBSERVE_UIDS",
    "VELOREN_NATIVE_PERSISTER_NPC_UIDS", "VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE",
    "VELOREN_NATIVE_MAX_RECORDS", "VELOREN_NATIVE_MAX_BYTES", "VELOREN_NATIVE_MAX_SECONDS",
    "VELOREN_G1_REQUESTS", "VELOREN_G1_EVENTS", "VELOREN_G1_ACTOR_UIDS",
    "VELOREN_NATIVE_RECRUIT_REQUESTS", "VELOREN_NATIVE_RECRUIT_EVENTS",
    "VELOREN_NATIVE_RECRUIT_LEADER_UID",
)


def _fact(predicate: str, args: Sequence[Any], value: bool | None) -> dict[str, Any]:
    return {"predicate": predicate, "args": list(args), "value": value}


def _descriptor(predicate: str, args: Sequence[Any]) -> dict[str, Any]:
    return {"predicate": predicate, "args": list(args)}


def _model(primitive: str, args: Mapping[str, Any], preconditions: Sequence[Mapping[str, Any]],
           effects: Sequence[Mapping[str, Any]], provenance: str,
           estimated_cost: float | None = None,
           dispatch_preconditions: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    model = {"primitive": primitive, "args": dict(args),
             "preconditions": [dict(item) for item in preconditions],
             "effects": [dict(item) for item in effects],
             "estimated_cost": ACTION_COST[primitive] if estimated_cost is None else float(estimated_cost),
             "provenance": {"source": provenance, "rule_version": RULE_VERSION}}
    if dispatch_preconditions is not None:
        model["dispatch_preconditions"] = [dict(item) for item in dispatch_preconditions]
    return model


def _finite(value: object) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _distance3(left: object, right: object) -> float | None:
    if (not isinstance(left, list) or not isinstance(right, list) or len(left) != 3
            or len(right) != 3 or any(not _finite(value) for value in left + right)):
        return None
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def _distance_actor_to_marker(actor_position: object, marker_position: object) -> float | None:
    """Estimate native marker travel in XY; G1 marker positions are 2D."""
    if (not isinstance(actor_position, list) or len(actor_position) != 3
            or not isinstance(marker_position, list) or len(marker_position) != 2
            or any(not _finite(value) for value in actor_position + marker_position)):
        return None
    return math.hypot(float(actor_position[0]) - float(marker_position[0]),
                      float(actor_position[1]) - float(marker_position[1]))


def project_actor_view(view: Mapping[str, Any], *, recruit_view: Mapping[str, Any] | None = None,
                       observation_id: str | None = None,
                       other_actor_uids: Sequence[int] = DEFAULT_ACTORS,
                       native_follower_uid: int | None = None) -> dict[str, Any]:
    """Project one actor-local native G1 view into typed facts/action schemas.

    Report instances are never guessed: delivery/rally models are instantiated
    from stable marker semantics; actual report IDs are late-bound at dispatch.
    """
    if view.get("event") != "g1_actor_view" or view.get("schema_version") != 1:
        raise ValueError("unsupported G1 actor-view event")
    if view.get("rule_version") != RULE_VERSION:
        raise ValueError("unsupported G1 rule version")
    uid = view.get("actor_uid")
    game_time = view.get("time")
    if type(uid) is not int or uid < 0 or not _finite(game_time) or game_time < 0:
        raise ValueError("G1 actor view needs a non-negative UID and absolute game time")
    markers = view.get("markers")
    own_reports = view.get("own_reports")
    known_reports = view.get("known_reports")
    own_report_deliveries = view.get("own_report_deliveries", [])
    completed_rallies = view.get("completed_rallies", [])
    nearby = view.get("nearby")
    if not all(isinstance(rows, list) for rows in
               (markers, own_reports, known_reports, own_report_deliveries,
                completed_rallies, nearby)):
        raise ValueError("G1 actor view marker/report/nearby fields must be arrays")

    facts: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    marker_ids: set[str] = set()
    marker_positions: dict[str, object] = {}
    actor_position = view.get("wpos")
    nearby_by_uid = {row.get("uid"): row for row in nearby
                     if isinstance(row, dict) and type(row.get("uid")) is int}
    peer_distance = {peer_uid: row.get("distance")
                     for peer_uid, row in nearby_by_uid.items()}
    if uid == SCOUT_UID:
        for peer_uid in other_actor_uids:
            if peer_uid == uid:
                continue
            peer = nearby_by_uid.get(peer_uid)
            distance = peer.get("distance") if peer is not None else None
            in_delivery_contact = bool(
                peer is not None and peer.get("alive") is True and peer.get("loaded") is True
                and _finite(distance) and 0.0 <= float(distance) <= DELIVERY_DISPATCH_RADIUS)
            # This is a local dispatch-eligibility fact, not a planner effect or a
            # global claim about the receiver. Missing peers are not dispatchable.
            facts.append(_fact("receiver_contact", [peer_uid], in_delivery_contact))
    for marker in markers:
        if not isinstance(marker, dict) or not isinstance(marker.get("marker_id"), str):
            raise ValueError("G1 marker rows need marker_id")
        marker_id = marker["marker_id"]
        if marker_id in marker_ids:
            raise ValueError("duplicate marker_id in actor-local view")
        marker_ids.add(marker_id)
        marker_positions[marker_id] = marker.get("wpos")
        facts.append(_fact("marker_known", [marker_id], True))
        travel = _distance_actor_to_marker(actor_position, marker.get("wpos"))
        survey_cost = (travel if travel is not None else 1_000_000.0) + float(marker.get("survey_seconds", 0.0))
        models.append(_model("survey_marker", {"marker_id": marker_id},
                             [_descriptor("marker_known", [marker_id])],
                             [_descriptor("survey_completed", [marker_id]),
                              _descriptor("own_report", [marker_id]),
                              _descriptor(f"event:g1_survey_completed", [uid, marker_id])],
                             "native:g1_actor_view.markers+wpos", survey_cost))

    for row in own_reports:
        if not isinstance(row, dict) or not isinstance(row.get("marker_id"), str) \
                or not isinstance(row.get("report_id"), str):
            raise ValueError("own_reports rows need marker_id and report_id")
        marker_id, report_id = row["marker_id"], row["report_id"]
        facts.append(_fact("survey_completed", [marker_id], True))
        facts.append(_fact("owns_report", [marker_id, report_id], True))
        facts.append(_fact("own_report", [marker_id], True))
        facts.append(_fact("report_known", [marker_id, uid], True))

    # Stable marker keys let HTN plan survey -> deliver before the native
    # report_id exists. The G1 adapter resolves the real ID at dispatch.
    for marker_id in sorted(marker_ids):
        if uid == SCOUT_UID:
            for receiver in other_actor_uids:
                if receiver == uid:
                    continue
                models.append(_model("deliver_report",
                                     {"marker_id": marker_id, "receiver_uid": receiver},
                                     [_descriptor("own_report", [marker_id])],
                                     [_descriptor("report_delivered", [marker_id, receiver]),
                                      _descriptor("report_known", [marker_id, receiver]),
                                      _descriptor("event:g1_report_delivered",
                                                  [uid, marker_id, receiver])],
                                     "native:g1_actor_view.markers+authorized-peer",
                                     float(peer_distance.get(receiver, 1_000_000.0)),
                                     dispatch_preconditions=[
                                         _descriptor("receiver_contact", [receiver])]))
    for row in known_reports:
        if not isinstance(row, dict) or not isinstance(row.get("marker_id"), str) \
                or not isinstance(row.get("report_id"), str):
            raise ValueError("known_reports rows need marker_id and report_id")
        marker_id, report_id = row["marker_id"], row["report_id"]
        facts.append(_fact("report_known", [marker_id, uid], True))
        owner_uid = row.get("owner_uid")
        if type(owner_uid) is int and owner_uid >= 0:
            facts.append(_fact("known_report_from", [marker_id, owner_uid, uid], True))
    for row in own_report_deliveries:
        if (not isinstance(row, dict) or not isinstance(row.get("marker_id"), str)
                or not isinstance(row.get("report_id"), str)
                or type(row.get("from_uid")) is not int
                or type(row.get("to_uid")) is not int
                or uid not in (row["from_uid"], row["to_uid"])):
            raise ValueError("own_report_deliveries rows must be actor-local durable delivery facts")
        marker_id, from_uid, to_uid = row["marker_id"], row["from_uid"], row["to_uid"]
        if uid == from_uid:
            facts.append(_fact("report_delivered", [marker_id, to_uid], True))
        if uid == to_uid:
            facts.append(_fact("known_report_from", [marker_id, from_uid, to_uid], True))
    for row in completed_rallies:
        if (not isinstance(row, dict) or not isinstance(row.get("marker_id"), str)
                or type(row.get("leader_uid")) is not int
                or type(row.get("follower_uid")) is not int
                or row["leader_uid"] != uid):
            raise ValueError("completed_rallies rows must belong to the actor-local leader")
        marker_id, follower = row["marker_id"], row["follower_uid"]
        facts.append(_fact("rally_completed", [marker_id, follower], True))
        facts.append(_fact("party_rallied", [uid, follower], True))
    if uid == LEADER_UID:
        for marker_id in sorted(marker_ids):
            for follower in ([native_follower_uid] if native_follower_uid is not None else []):
                marker_travel = _distance_actor_to_marker(actor_position, marker_positions[marker_id])
                rally_cost = (marker_travel if marker_travel is not None else 1_000_000.0)
                rally_cost += float(peer_distance.get(follower, 1_000_000.0))
                models.append(_model("rally_marker",
                                     {"marker_id": marker_id, "follower_uid": follower},
                                     [_descriptor("known_report_from", [marker_id, SCOUT_UID, uid]),
                                      _descriptor("hired_follower", [uid, follower])],
                                     [_descriptor("rally_completed", [marker_id, follower]),
                                      _descriptor("party_rallied", [uid, follower]),
                                      _descriptor("event:g1_rally_completed",
                                                  [uid, marker_id, follower])],
                                     "native:g1_actor_view.markers+authorized-peer",
                                     rally_cost))
        for peer in nearby:
            if isinstance(peer, dict) and type(peer.get("uid")) is int \
                    and peer["uid"] != uid and peer.get("hired_by_uid") == uid:
                facts.append(_fact("hired_follower", [uid, peer["uid"]], True))

    if recruit_view is not None and uid == LEADER_UID:
        if (recruit_view.get("event") != "native_recruit_actor_view"
                or recruit_view.get("version") != 1
                or recruit_view.get("npc_uid") != uid):
            raise ValueError("leader recruitment view does not match native v1 actor-view schema")
        if recruit_view.get("leader_at_home") is True:
            facts.append(_fact("leader_home", [uid], True))
        excluded = set(other_actor_uids)
        for row in recruit_view.get("eligible_recruits", []):
            if not isinstance(row, dict) or type(row.get("npc_uid")) is not int:
                continue
            follower = row["npc_uid"]
            if follower == uid or follower in excluded:
                continue
            facts.append(_fact("recruit_eligible", [uid, follower], True))
            models.append(_model("RecruitMember", {"target_uid": follower},
                                 [_descriptor("recruit_eligible", [uid, follower]),
                                  _descriptor("leader_home", [uid])],
                                 [_descriptor("hired_follower", [uid, follower])],
                                 "native:native_recruit_actor_view.eligible_recruits",
                                 float(row["distance_3d"])))
        for row in recruit_view.get("hired_members", []):
            if isinstance(row, dict) and type(row.get("npc_uid")) is int:
                facts.append(_fact("hired_follower", [uid, row["npc_uid"]], True))

    # Deduplicate stable facts and models; retain false/unknown only when the
    # native API explicitly supplies them in future schema revisions.
    fact_map = {(item["predicate"], json.dumps(item["args"], sort_keys=True)): item
                for item in facts}
    model_map = {(item["primitive"], json.dumps(item["args"], sort_keys=True)): item
                 for item in models}
    fingerprint = hashlib.sha256(json.dumps(view, sort_keys=True, separators=(",", ":"),
                                            ensure_ascii=False).encode()).hexdigest()
    return {"actor_uid": uid,
            "observation_id": observation_id or f"{uid}:{game_time:.9f}:{fingerprint}",
            "facts": list(fact_map.values()), "action_models": list(model_map.values()),
            "native_view_time": float(game_time), "native_view": dict(view)}


def g1_feedback(row: Mapping[str, Any]) -> dict[str, Any] | None:
    """Normalize native G1 receipts without treating dispatch acceptance as effect."""
    event = row.get("event")
    if event == "g1_action_accepted":
        required = ("request_id", "actor_uid", "action", "node_id", "game_time")
        if any(key not in row for key in required):
            raise ValueError("G1 accepted receipt is missing correlation fields")
        return {"event": "g1_action_dispatch_accepted", "request_id": row["request_id"],
                "actor_uid": row["actor_uid"], "node_id": row["node_id"],
                "game_time": row["game_time"]}
    if event in ("g1_action_settled", "g1_action_failed"):
        required = ("request_id", "actor_uid", "node_id", "action", "args", "game_time", "effects")
        if any(key not in row for key in required):
            raise ValueError("G1 terminal receipt is missing typed settlement fields")
        return dict(row)
    if event == "g1_action_rejected":
        required = ("request_id", "actor_uid", "game_time")
        if any(key not in row for key in required):
            raise ValueError("G1 rejection receipt is missing correlation fields")
        # The native reject is intentionally minimal; exact request identity is
        # restored only from this run's immutable request registry.
        return {"event": "g1_action_rejected", "request_id": row["request_id"],
                "actor_uid": row["actor_uid"], "game_time": row["game_time"],
                "reason": row.get("reason", "native rejection")}
    return None


def normalize_registered_g1_receipt(row: Mapping[str, Any],
                                    registered: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    """Project a native receipt only after strict identity/effect validation.

    Native terminal args may add the real report_id late-bound by Rust and
    action-irrelevant null fields from the fixed Rust envelope. Only those
    declared null fields are removed before matching stable semantic args.
    """
    request_id = row.get("request_id")
    request = registered.get(request_id) if isinstance(request_id, str) else None
    if request is None:
        return None, "unregistered_request_id"
    event = row.get("event")
    if event == "g1_action_rejected":
        if row.get("actor_uid") != request.get("actor_uid"):
            return None, "rejection_actor_mismatch"
        return ({"event": "g1_action_failed", "request_id": request_id,
                 "actor_uid": request["actor_uid"], "node_id": request["node_id"],
                 "action": request["primitive"], "args": dict(request["args"]),
                 "game_time": row["game_time"], "reason": row.get("reason", "native rejection"),
                 "effects": [], "source": request["source"], "goal_id": request["goal_id"],
                 "author_version": request.get("author_version"),
                 "provenance": {"native_event": "g1_action_rejected",
                                "native_actor_uid": row["actor_uid"]}}, None)
    if event == "g1_action_accepted":
        identity = (row.get("actor_uid") == request.get("actor_uid")
                    and row.get("node_id") == request.get("node_id")
                    and row.get("action") == request.get("primitive")
                    and row.get("source") == request.get("source")
                    and row.get("goal_id") == request.get("goal_id")
                    and row.get("author_version") == request.get("author_version"))
        if not identity:
            return None, "acceptance_identity_mismatch"
        return ({"event": "g1_action_dispatch_accepted", "request_id": request_id,
                 "actor_uid": request["actor_uid"], "node_id": request["node_id"],
                 "game_time": row["game_time"]}, None)
    if event not in ("g1_action_settled", "g1_action_failed"):
        return None, "not_a_g1_receipt"
    identity = (row.get("actor_uid") == request.get("actor_uid")
                and row.get("node_id") == request.get("node_id")
                and row.get("action") == request.get("primitive")
                and row.get("source") == request.get("source")
                and row.get("goal_id") == request.get("goal_id")
                and row.get("author_version") == request.get("author_version"))
    if not identity:
        return None, "terminal_identity_mismatch"
    native_args = row.get("args")
    if not isinstance(native_args, dict):
        return None, "terminal_args_not_object"
    optional_nulls = {
        "survey_marker": {"receiver_uid", "follower_uid"},
        "deliver_report": {"follower_uid"},
        "rally_marker": {"receiver_uid"},
    }.get(request.get("primitive"), set())
    if any(key in native_args and native_args[key] is not None for key in optional_nulls):
        return None, "terminal_irrelevant_argument_not_null"
    stable_args = {key: value for key, value in native_args.items()
                   if key != "report_id" and key not in optional_nulls}
    if stable_args != request.get("args"):
        return None, "terminal_semantic_args_mismatch"
    actual_report_id = native_args.get("report_id")
    expected_report_id = request.get("_late_bound_report_id")
    if expected_report_id is not None and actual_report_id != expected_report_id:
        return None, "late_bound_report_id_mismatch"
    if event == "g1_action_failed":
        return ({"event": event, "request_id": request_id, "actor_uid": request["actor_uid"],
                 "node_id": request["node_id"], "action": request["primitive"],
                 "args": dict(request["args"]), "game_time": row["game_time"],
                 "reason": row.get("reason", "native action failed"), "effects": [],
                 "source": request["source"], "goal_id": request["goal_id"],
                 "author_version": request.get("author_version"),
                 "provenance": {"native_args": native_args}}, None)
    effects = row.get("effects")
    if not isinstance(effects, list) or len(effects) != 1 or not isinstance(effects[0], dict):
        return None, "settled_effect_shape_invalid"
    effect = effects[0]
    marker_id = request["args"].get("marker_id")
    if request["primitive"] == "survey_marker":
        # The report is created only when the survey settles, so the native
        # lease/terminal args still carry report_id=null. Trust its terminal
        # effect only when the emitted G1 rule's owner-qualified ID matches.
        settled_report_id = f"g1:{marker_id}:{request['actor_uid']}"
        if (actual_report_id is not None
                or effect.get("event") != "g1_survey_completed"
                or effect.get("marker_id") != marker_id
                or effect.get("report_id") != settled_report_id
                or not _finite(effect.get("continuous_stay_seconds"))
                or effect["continuous_stay_seconds"] < 2.0):
            return None, "survey_settlement_witness_invalid"
        canonical_effects = [_descriptor("survey_completed", [marker_id]),
                             _descriptor("own_report", [marker_id])]
    elif request["primitive"] == "deliver_report":
        receiver = request["args"].get("receiver_uid")
        if (effect.get("event") != "g1_report_delivered"
                or effect.get("report_id") != actual_report_id
                or effect.get("from_uid") != request["actor_uid"]
                or effect.get("to_uid") != receiver
                or effect.get("native_interaction") != "native_speech_emitted"
                or effect.get("interaction_request_id") != request_id
                or not _finite(effect.get("speech_emitted_at"))
                or effect["speech_emitted_at"] < 0
                or not _finite(row.get("game_time"))
                or effect["speech_emitted_at"] > row["game_time"]
                or not _finite(effect.get("distance"))
                or effect["distance"] > 8.0):
            return None, "delivery_settlement_witness_invalid"
        canonical_effects = [_descriptor("report_delivered", [marker_id, receiver]),
                             _descriptor("report_known", [marker_id, receiver])]
    elif request["primitive"] == "rally_marker":
        follower = request["args"].get("follower_uid")
        if (effect.get("event") != "g1_rally_completed"
                or effect.get("marker_id") != marker_id
                or effect.get("report_id") != actual_report_id
                or effect.get("report_owner_uid") != SCOUT_UID
                or effect.get("from_uid") != SCOUT_UID
                or effect.get("leader_uid") != request["actor_uid"]
                or effect.get("follower_uid") != follower
                or effect.get("leader_hired_follower") is not True
                or effect.get("leader_knows_report") is not True):
            return None, "rally_settlement_witness_invalid"
        canonical_effects = [_descriptor("rally_completed", [marker_id, follower])]
    else:
        return None, "unsupported_g1_action"
    return ({"event": "g1_action_settled", "request_id": request_id,
             "actor_uid": request["actor_uid"], "node_id": request["node_id"],
             "action": request["primitive"], "args": dict(request["args"]),
             "game_time": row["game_time"], "effects": canonical_effects,
             "source": request["source"], "goal_id": request["goal_id"],
             "author_version": request.get("author_version"),
             "provenance": {"native_event": event, "native_args": native_args,
                            "native_effect": effect}}, None)


def g1_request_payload(request: Mapping[str, Any],
                       actor_views: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    primitive = request.get("primitive")
    if primitive not in G1_ACTIONS:
        raise ValueError(f"not a G1 request primitive: {primitive}")
    args = request.get("args")
    if not isinstance(args, dict):
        raise ValueError("G1 action args must be a JSON object")
    marker_id = args.get("marker_id")
    late_bound_report_id = None
    if primitive == "deliver_report":
        rows = actor_views[request["actor_uid"]].get("own_reports", [])
        candidates = [row for row in rows if isinstance(row, dict)
                      and row.get("marker_id") == marker_id
                      and isinstance(row.get("report_id"), str) and row["report_id"]]
        if not candidates:
            raise ValueError("delivery dispatch has no observed own report for its marker")
        late_bound_report_id = sorted(candidates, key=lambda row: row["report_id"])[0]["report_id"]
    elif primitive == "rally_marker":
        rows = actor_views[request["actor_uid"]].get("known_reports", [])
        candidates = [row for row in rows if isinstance(row, dict)
                      and row.get("marker_id") == marker_id
                      and row.get("owner_uid") == SCOUT_UID
                      and isinstance(row.get("report_id"), str) and row["report_id"]]
        if not candidates:
            raise ValueError("rally dispatch has no observed scout-owned report for its marker")
        late_bound_report_id = sorted(candidates, key=lambda row: row["report_id"])[0]["report_id"]
    native_args = dict(args)
    if late_bound_report_id is not None:
        native_args["report_id"] = late_bound_report_id
    return {"request_id": request["request_id"], "rule_version": RULE_VERSION,
            "observed_time": float(request["observed_time"]), "action": primitive,
            "actor_uid": request["actor_uid"], "node_id": request["node_id"],
            "source": request["source"], "goal_id": request["goal_id"],
            "author_version": request.get("author_version"), "args": native_args,
            "ttl_seconds": min(120.0, float(request.get("ttl_seconds", 120.0)))}


def author_monitor_world_facts(leader_view: Mapping[str, Any],
                               trusted_deliveries: set[tuple[str, int, int, str]]) -> list[dict[str, Any]]:
    """Expose only owner-qualified reports corroborated by a matched delivery."""
    facts = []
    for row in leader_view.get("known_reports", []):
        if not isinstance(row, dict):
            continue
        marker_id, report_id, owner_uid = (row.get("marker_id"), row.get("report_id"),
                                           row.get("owner_uid"))
        if (isinstance(marker_id, str) and isinstance(report_id, str)
                and type(owner_uid) is int
                and (marker_id, owner_uid, LEADER_UID, report_id) in trusted_deliveries):
            facts.append(_fact("known_report_from", [marker_id, owner_uid, LEADER_UID], True))
    return facts


def process_completion_satisfied(session: Mapping[str, Any], decision: Mapping[str, Any],
                                 applied_demo_versions: set[tuple[str, int]]) -> bool:
    expected_demo = {("g1-scout-handoff-witness", 1),
                     ("g2-leader-rally-deadline", 1),
                     ("g2-leader-rally-deadline", 2)}
    if not expected_demo.issubset(applied_demo_versions):
        return False
    role_plans = [row for row in decision.get("plans", [])
                  if ":ACTOR:" in row.get("plan_key", "")]
    if len(role_plans) < 3 or any(row.get("status") != "SATISFIED" for row in role_plans):
        return False
    author_goals = decision.get("author_obligations", [])
    if len(author_goals) != 2 or any(row.get("status") != "SATISFIED" for row in author_goals):
        return False
    inflight = session.get("inflight_by_actor", {})
    return isinstance(inflight, dict) and not inflight


def loaded_process_readiness(views: Mapping[int, Mapping[str, Any]],
                             recruit_view: Mapping[str, Any] | None,
                             native_follower_uid: int, *,
                             recruit_view_observed: bool,
                             game_time: float,
                             warmup_completed: bool = False,
                             native_follower_hired: bool = False) -> tuple[bool, str]:
    """Do not start G1/recruit dispatch from simulated or stale actor state."""
    if set(views) != set(DEFAULT_ACTORS):
        return False, "PRECONDITION_UNKNOWN:both_actor_views_not_observed"
    for uid in DEFAULT_ACTORS:
        view = views[uid]
        view_time = view.get("time")
        if str(view.get("mode", "")).lower() != "loaded":
            return False, f"PRECONDITION_UNKNOWN:actor_{uid}_loaded_mode_unconfirmed"
        if (not _finite(view_time) or view_time > game_time or game_time - view_time > 2.0):
            return False, f"PRECONDITION_UNKNOWN:actor_{uid}_view_stale_or_future"
    if not recruit_view_observed or recruit_view is None:
        return False, "PRECONDITION_UNKNOWN:leader_recruit_view_not_fresh"
    if (recruit_view.get("event") != "native_recruit_actor_view"
            or recruit_view.get("version") != 1
            or recruit_view.get("npc_uid") != LEADER_UID
            or str(recruit_view.get("mode", "")).lower() != "loaded"):
        return False, "PRECONDITION_UNKNOWN:leader_recruit_loaded_mode_unconfirmed"
    recruit_time = recruit_view.get("time")
    if (not _finite(game_time) or not _finite(recruit_time)
            or recruit_time > game_time or game_time - recruit_time > 2.0):
        return False, "PRECONDITION_UNKNOWN:leader_recruit_view_stale_or_future"
    if native_follower_uid in DEFAULT_ACTORS:
        return False, "PRECONDITION_UNKNOWN:follower_is_session_actor"
    if not warmup_completed:
        candidates = recruit_view.get("eligible_recruits")
        if not isinstance(candidates, list):
            return False, "PRECONDITION_UNKNOWN:eligible_native_candidates_missing"
        if not any(isinstance(row, dict) and row.get("npc_uid") == native_follower_uid
                   for row in candidates):
            return False, "PRECONDITION_UNKNOWN:frozen_follower_not_native_eligible_candidate"
    elif native_follower_hired:
        members = recruit_view.get("hired_members")
        if not isinstance(members, list) or not any(
                isinstance(row, dict) and row.get("npc_uid") == native_follower_uid
                for row in members):
            return False, "PRECONDITION_UNKNOWN:correlated_hire_not_in_fresh_native_roster"
    return True, "loaded_native_inputs_ready"


def build_process_environment(base_env: Mapping[str, str], source: Mapping[str, Any],
                              runtime: Mapping[str, Any], paths: Mapping[str, Path],
                              userdata: Path, actor_uids: Sequence[int],
                              native_follower_uid: int) -> dict[str, str]:
    observers = runtime.get("observe_npc_uids")
    persisters = runtime.get("native_persister_npc_uids")
    distance = runtime.get("native_persister_view_distance_chunks")
    expected_uids = set(actor_uids) | {native_follower_uid}
    if (not isinstance(observers, list) or not isinstance(persisters, list)
            or observers != persisters or len(set(observers)) != len(observers)
            or not expected_uids.issubset(observers)):
        raise ValueError("native observer/persister lists must match and include actors plus follower")
    if distance != 2:
        raise ValueError("native persister view distance must reuse the frozen two-chunk contract")
    env = dict(base_env)
    for key in CLEARED_ENV:
        env.pop(key, None)
    env.update({
        "VELOREN_USERDATA": str(userdata),
        "VELOREN_ASSETS": str(Path(source["assets_path"]).expanduser().resolve()),
        "VELOREN_NATIVE_EVENTS": str(paths["native-events.jsonl"]),
        "VELOREN_NATIVE_OBSERVE": "1",
        "VELOREN_NATIVE_OBSERVE_UIDS": ",".join(map(str, observers)),
        "VELOREN_NATIVE_PERSISTER_NPC_UIDS": ",".join(map(str, persisters)),
        "VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE": str(distance),
        "VELOREN_NATIVE_MAX_RECORDS": str(MAX_RECORDS),
        "VELOREN_NATIVE_MAX_BYTES": str(MAX_BYTES),
        "VELOREN_NATIVE_MAX_SECONDS": str(MAX_NATIVE_SECONDS),
        "VELOREN_G1_REQUESTS": str(paths["g1-requests.jsonl"]),
        "VELOREN_G1_EVENTS": str(paths["g1-events.jsonl"]),
        "VELOREN_G1_ACTOR_UIDS": ",".join(map(str, actor_uids)),
        "VELOREN_NATIVE_RECRUIT_REQUESTS": str(paths["recruit-requests.jsonl"]),
        "VELOREN_NATIVE_RECRUIT_EVENTS": str(paths["recruit-events.jsonl"]),
        "VELOREN_NATIVE_RECRUIT_LEADER_UID": str(LEADER_UID),
    })
    return env


def recruitment_request_payload(request: Mapping[str, Any], game_time: float) -> dict[str, Any]:
    if request.get("primitive") != "RecruitMember" or request.get("actor_uid") != LEADER_UID:
        raise ValueError("only the leader may dispatch native RecruitMember")
    args = request.get("args")
    if not isinstance(args, dict) or type(args.get("target_uid")) is not int:
        raise ValueError("RecruitMember needs target_uid args")
    return {"version": 1, "kind": "RecruitMember", "request_id": request["request_id"],
            "source": request["source"], "leader_uid": LEADER_UID,
            "target_uid": args["target_uid"], "observed_time": float(game_time),
            "ttl_seconds": 120.0}


def parse_author_input(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Keep human/demo input provenance and validate the runner envelope only."""
    if row.get("source") not in ("LOCAL_AUTHOR", "RUNNER_DEMO"):
        return None, "source_not_allowlisted"
    command = row.get("command")
    if not isinstance(command, dict):
        return None, "command_must_be_object"
    if command.get("op") not in ("append", "edit"):
        return None, "unsupported_operation"
    return dict(command), None


def _event_time(row: Mapping[str, Any]) -> float | None:
    value = row.get("time", row.get("game_time"))
    return float(value) if _finite(value) and value >= 0 else None


def recruit_pair_feedback(request_id: str, request: Mapping[str, Any],
                          terminal: Mapping[str, Any] | None,
                          trusted_job: Mapping[str, Any] | None
                          ) -> tuple[dict[str, Any] | None, str | None]:
    """Join two native hire witnesses before allowing controller progress."""
    if terminal is None:
        return None, None
    target = request["args"]["target_uid"]
    if (terminal.get("request_id") != request_id
            or terminal.get("leader_uid") != LEADER_UID
            or terminal.get("target_uid") != target):
        return None, "leader_or_target_mismatch"
    outcome = terminal.get("outcome")
    terminal_time = _event_time(terminal)
    if outcome == "hired_observed":
        if trusted_job is None:
            return None, "awaiting_trusted_job_witness"
        job_time = _event_time(trusted_job)
        if job_time is None or terminal_time is None:
            return None, "successful_recruit_receipt_missing_time"
        return ({"event": "g1_action_settled", "request_id": request_id,
                 "actor_uid": LEADER_UID, "node_id": request["node_id"],
                 "action": "RecruitMember", "args": request["args"],
                 "game_time": max(float(job_time), float(terminal_time)),
                 "effects": [_descriptor("hired_follower", [LEADER_UID, target])],
                 "source": request["source"], "goal_id": request["goal_id"],
                 "author_version": request.get("author_version"),
                 "provenance": {"native_job_time": float(job_time),
                                "native_terminal_time": float(terminal_time),
                                "job_receipt": dict(trusted_job),
                                "terminal_receipt": dict(terminal)}}, None)
    if outcome in {"request_rejected", "expired_before_native_action",
                   "expired_after_native_action_before_message", "expired_after_message",
                   "leader_invalidated", "target_invalidated"}:
        if terminal_time is None:
            return None, "failure_terminal_missing_time"
        return ({"event": "g1_action_failed", "request_id": request_id,
                 "actor_uid": LEADER_UID, "node_id": request["node_id"],
                 "action": "RecruitMember", "args": request["args"],
                 "game_time": float(terminal_time), "reason": outcome, "effects": [],
                 "source": request["source"], "goal_id": request["goal_id"],
                 "author_version": request.get("author_version"),
                 "provenance": {"native_terminal_time": float(terminal_time),
                                "terminal_receipt": dict(terminal)}}, None)
    return None, "unknown_recruit_terminal_outcome"


def validate_process_settings(userdata: Path, manifest_path: Path) -> None:
    """Read back the two RON settings files that bound shutdown and networking."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(rows, list):
        raise ValueError("userdata manifest has no files array")
    settings = {row.get("path"): userdata / row.get("path", "")
                for row in rows if isinstance(row, dict) and row.get("role") == "settings"}
    if set(settings) != {"server-cli/settings.ron", "server/server_config/settings.ron"}:
        raise ValueError("userdata must pin exactly both native settings files")
    cli_text = settings["server-cli/settings.ron"].read_text(encoding="utf-8")
    server_text = settings["server/server_config/settings.ron"].read_text(encoding="utf-8")
    if not re.search(r"\bupdate_shutdown_grace_period_secs\s*:\s*5\s*,", cli_text):
        raise ValueError("native update shutdown grace must be exactly five seconds")
    if not re.search(r"\bshutdown_signals\s*:\s*\[\s*SIGUSR1\s*\]", cli_text):
        raise ValueError("native settings must retain SIGUSR1 shutdown")
    if not re.search(r"\bquery_address\s*:\s*None\b", server_text):
        raise ValueError("server query_address must remain None")
    if not re.search(r'\baddress\s*:\s*"127\.0\.0\.1:[0-9]+"', server_text):
        raise ValueError("server game protocol must bind to loopback only")


def _actor_goal_specs(markers: Sequence[str], native_follower_uid: int) -> list[dict[str, Any]]:
    if len(markers) != 2 or any(not isinstance(marker, str) or not marker for marker in markers):
        raise ValueError("scenario needs two frozen marker IDs from the accepted process design")
    if type(native_follower_uid) is not int or native_follower_uid < 0 \
            or native_follower_uid in DEFAULT_ACTORS:
        raise ValueError("native follower must be a non-session actor UID")
    scout_goals = []
    for marker in markers:
        scout_goals.extend([
            {"predicate": "survey_completed", "args": [marker]},
            {"predicate": "report_delivered", "args": [marker, LEADER_UID]},
        ])
    leader_hire = {"predicate": "hired_follower", "args": [LEADER_UID, native_follower_uid]}
    leader_rallies = [{"predicate": "party_rallied", "args": [LEADER_UID, native_follower_uid]}]
    return [{"goal_id": "scout-patrol-and-handoff", "actor_uid": SCOUT_UID,
             "goals": scout_goals},
            {"goal_id": "leader-hire-native-follower", "actor_uid": LEADER_UID,
             "goals": [leader_hire]},
            {"goal_id": "leader-rally-at-reported-sites", "actor_uid": LEADER_UID,
             "goals": leader_rallies}]


def _author_demo_schedule(markers: Sequence[str], native_follower_uid: int,
                          trigger_game_time: float) -> list[dict[str, Any]]:
    """Three cycle-separated author inputs for the reviewed RUNNER_DEMO fixture."""
    marker_a, marker_b = markers
    deadline = float(trigger_game_time) + 240.0
    return [
        {"source": "RUNNER_DEMO", "command": {
            "op": "append", "goal_id": "g1-scout-handoff-witness", "version": 1,
            "actor_uid": SCOUT_UID,
            "ast": {"op": "and", "children": [
                {"op": "state", "predicate": "known_report_from",
                 "args": [marker_a, SCOUT_UID, LEADER_UID]},
                {"op": "event_before",
                 "first": {"event": "g1_survey_completed", "args": [SCOUT_UID, marker_a]},
                 "second": {"event": "g1_report_delivered",
                            "args": [SCOUT_UID, marker_a, LEADER_UID]}}]}}},
        {"source": "RUNNER_DEMO", "command": {
            "op": "append", "goal_id": "g2-leader-rally-deadline", "version": 1,
            "actor_uid": LEADER_UID,
            "ast": {"op": "deadline",
                    "event": {"event": "g1_rally_completed",
                              "args": [LEADER_UID, marker_a, native_follower_uid]},
                    "at": deadline}}},
        {"source": "RUNNER_DEMO", "command": {
            "op": "edit", "goal_id": "g2-leader-rally-deadline", "version": 2,
            "actor_uid": LEADER_UID,
            "ast": {"op": "deadline",
                    "event": {"event": "g1_rally_completed",
                              "args": [LEADER_UID, marker_b, native_follower_uid]},
                    "at": deadline}}},
    ]


def build_observations(latest_views: Mapping[int, Mapping[str, Any]],
                       latest_recruit_view: Mapping[str, Any] | None,
                       native_follower_uid: int,
                       world_facts: Sequence[Mapping[str, Any]] = (),
                       event_coverage_through: float | None = None) -> dict[str, Any]:
    actors = []
    times = []
    for uid in DEFAULT_ACTORS:
        view = latest_views[uid]
        recruit = latest_recruit_view if uid == LEADER_UID else None
        projected = project_actor_view(view, recruit_view=recruit,
                                       observation_id=view.get("_runner_observation_id"),
                                       native_follower_uid=native_follower_uid)
        times.append(projected["native_view_time"])
        actors.append({key: projected[key] for key in
                       ("actor_uid", "observation_id", "facts", "action_models")})
    # Game time remains absolute; actor-specific source timestamps stay with
    # their raw views and are logged by the caller rather than collapsed away.
    game_time = max(times)
    return {"schema": SCHEMA, "game_time": game_time, "actors": actors,
            "world_facts": list(world_facts), "event_coverage_through": event_coverage_through}


def run_process(freeze_path: Path, run_id: str, wall_cap: float = MAX_WALL_SECONDS,
                author_input_path: Path | None = None) -> Path:
    """Launch one process from a reviewed freeze; this function is not called in unit tests."""
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "READY":
        raise ValueError("process freeze is not READY; native source/build inputs are still pending review")
    source, runtime, scenario = freeze.get("source"), freeze.get("runtime"), freeze.get("scenario")
    if not all(isinstance(value, dict) for value in (source, runtime, scenario)):
        raise ValueError("freeze requires source, runtime, and scenario objects")
    if source.get("commit") != "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248":
        raise ValueError("source must pin the reviewed Veloren v0.18.0 commit")
    source_files = (("source_patch_path", "source_patch_sha256"),
                    ("g1_patch_path", "g1_patch_sha256"),
                    ("cargo_lock_path", "cargo_lock_sha256"),
                    ("binary_path", "binary_sha256"))
    for path_key, hash_key in source_files:
        candidate = Path(source.get(path_key, "")).expanduser().resolve()
        expected = source.get(hash_key)
        if (not candidate.is_file() or not isinstance(expected, str) or len(expected) != 64
                or sha256_file(candidate) != expected):
            raise ValueError(f"frozen source input mismatch: {path_key}")
    binary = Path(source["binary_path"]).expanduser().resolve()
    assets = Path(source["assets_path"]).expanduser().resolve()
    assets_manifest = Path(source.get("assets_manifest_path", "")).expanduser().resolve()
    userdata = Path(runtime["userdata_path"]).expanduser().resolve()
    manifest = Path(runtime["userdata_manifest_path"]).expanduser().resolve()
    if (not assets.is_dir() or not assets_manifest.is_file()
            or sha256_file(assets_manifest) != source.get("assets_manifest_sha256")
            or assets_tree_sha256(assets, assets_manifest) != source.get("assets_tree_sha256")):
        raise ValueError("frozen official assets tree or path-ordered manifest mismatch")
    if not userdata.is_dir() or not manifest.is_file():
        raise ValueError("frozen assets or userdata are missing")
    if sha256_file(manifest) != runtime.get("userdata_manifest_sha256"):
        raise ValueError("frozen userdata manifest hash mismatch")
    _validate_userdata_manifest(userdata, manifest)
    validate_process_settings(userdata, manifest)
    if (runtime.get("actor_uids") != list(DEFAULT_ACTORS)
            or runtime.get("max_wall_seconds") != MAX_WALL_SECONDS
            or runtime.get("max_requests") != MAX_REQUESTS
            or runtime.get("disk_free_floor_bytes") != DISK_FLOOR_BYTES
            or runtime.get("telemetry_record_cap") != MAX_RECORDS
            or runtime.get("telemetry_byte_cap") != MAX_BYTES
            or runtime.get("shutdown_grace_seconds") != SHUTDOWN_GRACE_SECONDS):
        raise ValueError("runtime freeze differs from the reviewed process limits")
    if runtime.get("loopback_only") is not True or runtime.get("query_address") is not None:
        raise ValueError("native process must remain loopback-only")
    if runtime.get("update_shutdown_grace_period_secs") != SHUTDOWN_GRACE_SECONDS:
        raise ValueError("userdata must pin native update_shutdown_grace_period_secs=5")
    if not 0 < wall_cap <= MAX_WALL_SECONDS:
        raise ValueError("wall cap must be in (0, 720] seconds")
    run_id = run_id.strip()
    if not run_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in run_id):
        raise ValueError("run_id must contain only letters, digits, hyphen, or underscore")
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
        raise RuntimeError("free disk below 6 GiB before launch")

    markers = scenario.get("marker_ids")
    native_follower_uid = scenario.get("native_follower_uid")
    if type(native_follower_uid) is not int or native_follower_uid in DEFAULT_ACTORS:
        raise ValueError("scenario.native_follower_uid must identify a non-session native NPC")
    session = new_process_session(DEFAULT_ACTORS,
                                  goal_specs=_actor_goal_specs(markers, native_follower_uid),
                                  director_enabled=True)
    paths = {name: run_dir / name for name in (
        "native-events.jsonl", "g1-events.jsonl", "g1-requests.jsonl", "recruit-events.jsonl",
        "recruit-requests.jsonl", "author-input.jsonl", "decisions.jsonl",
        "session-checkpoints.jsonl", "author-versions.jsonl", "status.jsonl",
        "server.stdout.log", "server.stderr.log")}
    for name, path in paths.items():
        if name.endswith(".jsonl"):
            path.touch(exist_ok=False)
    native_events = JsonlTail(paths["native-events.jsonl"])
    g1_events = JsonlTail(paths["g1-events.jsonl"])
    recruit_events = JsonlTail(paths["recruit-events.jsonl"])
    author_tails = [JsonlTail(paths["author-input.jsonl"])]
    if author_input_path is not None:
        author_tails.append(JsonlTail(author_input_path))
    views: dict[int, dict[str, Any]] = {}
    view_sequences = {uid: 0 for uid in DEFAULT_ACTORS}
    recruit_view: dict[str, Any] | None = None
    recruit_view_observed = False
    pending_feedback: list[dict[str, Any]] = []
    loaded_chain = LoadedMsgChain(LEADER_UID)
    registered: dict[str, dict[str, Any]] = {}
    pending_author: list[dict[str, Any]] = []
    held_author: list[dict[str, Any]] = []
    author_source_by_id: dict[str, str] = {}
    request_total = record_total = 0
    start = time.monotonic()
    server: subprocess.Popen | None = None
    stop_reason = "supervisor_error"
    started_local = None
    signal_exit_code = None
    issued_auto_author = 0
    applied_demo_versions: set[tuple[str, int]] = set()
    first_settlement_seen = False
    last_settlement_time: float | None = None
    survey_trigger_time: float | None = None
    demo_schedule = None
    fresh_since_cycle: set[int] = set()
    latest_game_time = 0.0
    warmup_baseline_logged = False
    last_readiness_note: str | None = None
    native_follower_hired = False
    completion_observation_started: float | None = None
    trusted_deliveries: set[tuple[str, int, int, str]] = set()
    recruit_job_by_id: dict[str, dict[str, Any]] = {}
    recruit_terminal_by_id: dict[str, dict[str, Any]] = {}
    recruit_settled_ids: set[str] = set()
    wall_cap = min(wall_cap, MAX_WALL_SECONDS)

    def append_checked(path: Path, row: dict[str, Any]) -> None:
        nonlocal record_total
        if record_total >= MAX_RECORDS:
            raise RuntimeError("process record cap reached")
        if path.exists() and path.stat().st_size >= MAX_BYTES:
            raise RuntimeError("process JSONL byte cap reached")
        append_jsonl_once(path, row)
        record_total += 1

    env = build_process_environment(os.environ, source, runtime, paths, userdata,
                                   DEFAULT_ACTORS, native_follower_uid)
    stdout, stderr = paths["server.stdout.log"], paths["server.stderr.log"]
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            started_local = local_now()
            server = subprocess.Popen([str(binary), "--non-interactive"], env=env,
                                      stdout=out, stderr=err)
            append_checked(paths["status.jsonl"], {"event": "process_started",
                           "started_local": started_local, "binary_sha256": source["binary_sha256"],
                           "wall_cap_seconds": wall_cap, "actor_uids": list(DEFAULT_ACTORS)})
            append_checked(paths["session-checkpoints.jsonl"], {"event": "session_start",
                           "game_time": 0.0, "session": session})
            while server.poll() is None:
                now = time.monotonic()
                if now - start >= wall_cap:
                    stop_reason = "wall_cap"
                    break
                if shutil.disk_usage(run_dir).free < DISK_FLOOR_BYTES:
                    stop_reason = "disk_floor"
                    break
                if sum(p.stat().st_size for p in paths.values() if p.exists()) >= MAX_BYTES:
                    stop_reason = "process_byte_cap"
                    break

                # Keep bounded native persister telemetry in the same record
                # budget as G1/recruit receipts and controller output.
                for _row in native_events.read_rows():
                    record_total += 1

                for row in g1_events.read_rows():
                    record_total += 1
                    if row.get("event") == "g1_actor_view":
                        projected_uid = row.get("actor_uid")
                        if projected_uid not in DEFAULT_ACTORS:
                            continue
                        view_sequences[projected_uid] += 1
                        row = dict(row)
                        row["_runner_observation_id"] = f"{projected_uid}:{view_sequences[projected_uid]}"
                        views[projected_uid] = row
                        fresh_since_cycle.add(projected_uid)
                        latest_game_time = max(latest_game_time, float(row["time"]))
                    feedback, issue = normalize_registered_g1_receipt(row, registered)
                    if feedback is not None:
                        pending_feedback.append(feedback)
                        if feedback["event"] in ("g1_action_settled", "g1_action_failed"):
                            first_settlement_seen = first_settlement_seen or feedback["event"] == "g1_action_settled"
                            last_settlement_time = max(float(feedback["game_time"]),
                                                       last_settlement_time or 0.0)
                            if (feedback["event"] == "g1_action_settled"
                                    and feedback["action"] == "survey_marker"
                                    and feedback["actor_uid"] == SCOUT_UID
                                    and feedback["args"].get("marker_id") == scenario["marker_ids"][0]
                                    and survey_trigger_time is None):
                                survey_trigger_time = float(feedback["game_time"])
                            if (feedback["event"] == "g1_action_settled"
                                    and feedback["action"] == "deliver_report"):
                                effect = feedback.get("provenance", {}).get("native_effect", {})
                                report_id = effect.get("report_id")
                                if isinstance(report_id, str) and report_id:
                                    trusted_deliveries.add((feedback["args"]["marker_id"],
                                                            feedback["actor_uid"],
                                                            feedback["args"]["receiver_uid"],
                                                            report_id))
                            append_checked(paths["session-checkpoints.jsonl"], {
                                "event": "native_terminal_checkpoint", "game_time": feedback["game_time"],
                                "receipt": feedback})
                    elif issue and issue not in ("not_a_g1_receipt",):
                        append_checked(paths["status.jsonl"], {"event": "native_receipt_not_applied",
                                                               "request_id": row.get("request_id"),
                                                               "reason": issue})

                for row in recruit_events.read_rows():
                    record_total += 1
                    if row.get("event") == "native_recruit_actor_view" and row.get("npc_uid") == LEADER_UID:
                        recruit_view = row
                        recruit_view_observed = True
                    accepted = row.get("event") == "native_recruit_request_accepted"
                    request_id = row.get("request_id")
                    request = registered.get(request_id) if isinstance(request_id, str) else None
                    if accepted and request:
                        pending_feedback.append({"event": "g1_action_dispatch_accepted",
                                                 "request_id": request_id, "actor_uid": LEADER_UID,
                                                 "node_id": request["node_id"],
                                                 "game_time": float(row.get("time", request["observed_time"]))})
                    trusted = loaded_chain.observe(row)
                    if trusted is not None and request:
                        recruit_job_by_id[request_id] = trusted
                    if row.get("event") == "native_recruit_terminal" and request:
                        recruit_terminal_by_id[request_id] = dict(row)
                    if (row.get("event") == "native_recruit_request_rejected"
                            and request is not None and row.get("leader_uid", LEADER_UID) == LEADER_UID):
                        recruit_terminal_by_id[request_id] = {
                            "event": "native_recruit_request_rejected", "request_id": request_id,
                            "leader_uid": LEADER_UID, "target_uid": request["args"]["target_uid"],
                            "outcome": "request_rejected", "time": row.get("time", latest_game_time),
                            "reason": row.get("reason", "native request rejected")}
                    terminal = recruit_terminal_by_id.get(request_id) if isinstance(request_id, str) else None
                    job = recruit_job_by_id.get(request_id) if isinstance(request_id, str) else None
                    if request is not None and request_id not in recruit_settled_ids:
                        feedback, issue = recruit_pair_feedback(request_id, request, terminal, job)
                        if issue and issue != "awaiting_trusted_job_witness":
                            append_checked(paths["status.jsonl"], {
                                "event": "native_recruit_terminal_not_applied",
                                "request_id": request_id, "reason": issue})
                        if feedback is not None:
                            pending_feedback.append(feedback)
                            recruit_settled_ids.add(request_id)
                            is_success = feedback["event"] == "g1_action_settled"
                            if is_success:
                                first_settlement_seen = True
                                if (feedback.get("action") == "RecruitMember"
                                        and feedback.get("args", {}).get("target_uid")
                                        == native_follower_uid):
                                    native_follower_hired = True
                                last_settlement_time = max(float(feedback["game_time"]),
                                                           last_settlement_time or 0.0)
                                latest_game_time = max(latest_game_time, float(feedback["game_time"]))
                            append_checked(paths["session-checkpoints.jsonl"], {
                                "event": "native_recruit_job_and_terminal_checkpoint"
                                if is_success else "native_recruit_terminal_failure_checkpoint",
                                "native_job_time": _event_time(job) if job is not None else None,
                                "native_terminal_time": _event_time(terminal),
                                "receipt": feedback})

                # Read author input only after an actual native terminal. A
                # single command is applied per fresh all-actor controller cycle.
                if set(views) == set(DEFAULT_ACTORS) and fresh_since_cycle == set(DEFAULT_ACTORS):
                    if demo_schedule is None and survey_trigger_time is not None and author_input_path is None:
                        demo_schedule = _author_demo_schedule(scenario["marker_ids"],
                                                              native_follower_uid,
                                                              survey_trigger_time)
                    if demo_schedule is not None and issued_auto_author < len(demo_schedule):
                        scheduled = demo_schedule[issued_auto_author]
                        append_checked(paths["author-input.jsonl"], {
                            **scheduled, "issued_at_game_time": latest_game_time,
                            "trigger_survey_settled_at": survey_trigger_time})
                        issued_auto_author += 1
                    for tail in author_tails:
                        for input_row in tail.read_rows():
                            command, error = parse_author_input(input_row)
                            if error:
                                append_checked(paths["author-versions.jsonl"],
                                               {"event": "author_input_rejected", "reason": error})
                            else:
                                held_author.append({"command": command, "source": input_row["source"],
                                                    "issued_at_game_time": input_row.get("issued_at_game_time")})
                    if first_settlement_seen and held_author:
                        queued = held_author.pop(0)
                        pending_author.append(queued["command"])
                        author_source_by_id[queued["command"]["goal_id"]] = queued["source"]
                        append_checked(paths["author-versions.jsonl"], {
                            "event": "author_input_accepted", "source": queued["source"],
                            "command": queued["command"],
                            "issued_at_game_time": queued["issued_at_game_time"]})
                    monitor_facts = author_monitor_world_facts(views[LEADER_UID],
                                                               trusted_deliveries)
                    observations = build_observations(views, recruit_view, native_follower_uid,
                                                      world_facts=monitor_facts)
                    latest_game_time = float(observations["game_time"])
                    game_time = float(observations["game_time"])
                    ready, readiness_reason = loaded_process_readiness(
                        views, recruit_view, native_follower_uid,
                        recruit_view_observed=recruit_view_observed, game_time=game_time,
                        warmup_completed=warmup_baseline_logged,
                        native_follower_hired=native_follower_hired)
                    if not ready:
                        if readiness_reason != last_readiness_note:
                            append_checked(paths["status.jsonl"], {
                                "event": "warmup_precondition_unknown",
                                "reason": readiness_reason,
                                "game_time": game_time,
                                "actor_modes": {str(uid): views[uid].get("mode")
                                                for uid in DEFAULT_ACTORS},
                                "leader_recruit_view": recruit_view})
                            last_readiness_note = readiness_reason
                        fresh_since_cycle.clear()
                        time.sleep(0.1)
                        continue
                    last_readiness_note = None
                    if not warmup_baseline_logged:
                        append_checked(paths["status.jsonl"], {
                            "event": "pre_request_loaded_native_baseline",
                            "game_time": game_time,
                            "actor_views": {str(uid): views[uid] for uid in DEFAULT_ACTORS},
                            "leader_recruit_view": recruit_view,
                            "native_follower_uid": native_follower_uid})
                        warmup_baseline_logged = True
                    author_commands = pending_author[:1]
                    del pending_author[:len(author_commands)]
                    result = step_process(session, observations, game_time=game_time,
                                          author_commands=author_commands,
                                          feedback=pending_feedback,
                                          request_budget_remaining=max(0, MAX_REQUESTS - request_total))
                    pending_feedback.clear()
                    session, decision = result["session"], result["decision"]
                    fresh_since_cycle.clear()
                    if any(item.get("matched") and item.get("event") in
                           ("g1_action_settled", "g1_action_failed")
                           for item in decision.get("feedback_applied", [])):
                        append_checked(paths["session-checkpoints.jsonl"], {
                            "event": "session_after_native_terminal", "game_time": game_time,
                            "session": session})
                    append_checked(paths["decisions.jsonl"], {
                        "event": "controller_decision", "local_time": local_now(),
                        "game_time": game_time,
                        "actor_view_times": {str(uid): views[uid]["time"] for uid in DEFAULT_ACTORS},
                        "author_sources": [author_source_by_id.get(cmd.get("goal_id"))
                                           for cmd in author_commands],
                        "decision": decision})
                    for cmd in decision.get("author_commands_applied", []):
                        if author_source_by_id.get(cmd.get("goal_id")) == "RUNNER_DEMO":
                            applied_demo_versions.add((cmd["goal_id"], cmd["version"]))
                        append_checked(paths["session-checkpoints.jsonl"], {
                            "event": "author_version_checkpoint", "game_time": game_time,
                            "command": cmd, "session": session})
                    for request in decision.get("requests", []):
                        if request_total >= MAX_REQUESTS:
                            raise RuntimeError("controller produced a request with zero remaining dispatch budget")
                        if request["primitive"] == "RecruitMember":
                            payload = recruitment_request_payload(request, game_time)
                            loaded_chain.register_request(payload)
                            registered[request["request_id"]] = request
                            append_checked(paths["recruit-requests.jsonl"], payload)
                        else:
                            payload = g1_request_payload(request, views)
                            registered[request["request_id"]] = {
                                **request,
                                "_late_bound_report_id": payload["args"].get("report_id")}
                            append_checked(paths["g1-requests.jsonl"], payload)
                        request_total += 1
                    if request_total >= MAX_REQUESTS:
                        inflight = session.get("inflight_by_actor", {})
                        active_inflight = isinstance(inflight, Mapping) and any(inflight.values())
                        if not active_inflight and not process_completion_satisfied(
                                session, decision, applied_demo_versions):
                            stop_reason = "request_budget_exhausted"
                            break

                total_bytes = sum(path.stat().st_size for path in paths.values() if path.exists())
                if record_total >= MAX_RECORDS or total_bytes >= MAX_BYTES:
                    stop_reason = "process_output_cap"
                    break
                if stdout.stat().st_size + stderr.stat().st_size >= MAX_BYTES // 4:
                    stop_reason = "subprocess_output_cap"
                    break
                latest_decision = session.get("history", [])[-1] if session.get("history") else {}
                if process_completion_satisfied(session, latest_decision,
                                                applied_demo_versions):
                    if completion_observation_started is None:
                        completion_observation_started = latest_game_time
                    elif latest_game_time - completion_observation_started >= 15.0:
                        stop_reason = "all_process_goals_satisfied_plus_15s_native_observation"
                        break
                else:
                    completion_observation_started = None
                time.sleep(0.1)
            if server.poll() is not None and stop_reason == "supervisor_error":
                stop_reason = "server_exited"
    except Exception as exc:
        stop_reason = f"runner_error:{type(exc).__name__}:{exc}"
    finally:
        if server is not None and server.poll() is None:
            server.send_signal(signal.SIGUSR1)
            try:
                server.wait(timeout=SUPERVISOR_EXIT_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                stop_reason += ":native_exit_timeout"
                server.terminate()
                try:
                    server.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        signal_exit_code = server.returncode if server else None
        final = {"event": "process_end", "started_local": started_local,
                 "ended_local": local_now(), "stop_reason": stop_reason,
                 "return_code": signal_exit_code, "wall_seconds": time.monotonic() - start,
                 "requests": request_total, "records": record_total,
                 "output_bytes": sum(p.stat().st_size for p in paths.values() if p.exists()),
                 "actors": list(DEFAULT_ACTORS), "inflight_by_actor": session.get("inflight_by_actor")}
        append_checked(paths["status.jsonl"], final)
        append_checked(paths["session-checkpoints.jsonl"], {
            "event": "session_end", "session": session, "status": final})
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--author-input", type=Path)
    parser.add_argument("--wall-cap", type=float, default=MAX_WALL_SECONDS)
    args = parser.parse_args()
    print(run_process(args.freeze, args.run_id, args.wall_cap, args.author_input))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
