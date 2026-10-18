"""Pure persistent controller for ACTOR goals and AUTHOR future obligations."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (ContractError, evidence_parts, finite_number, json_safe,
                        validate_actor_view, validate_command)
from .planning import choose_recruit_target


def _actor_condition_signature(view: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "leader_at_home": view["leader_at_home"],
        "home_site_id": view["home_site_id"],
        "current_site_id": view["current_site_id"],
        "native_recruit_population_guard": view["native_recruit_population_guard"],
        "native_recruit_raid_site_available": view["native_recruit_raid_site_available"],
        "eligible_uids": sorted(row["npc_uid"] for row in view["eligible_recruits"]),
    }


def new_session(actor_uid: int, *, hire_quota: int = 2,
                director_enabled: bool = False) -> dict[str, Any]:
    if type(actor_uid) is not int or actor_uid < 0:
        raise ContractError("actor_uid must be a non-negative integer")
    if type(hire_quota) is not int or hire_quota < 1:
        raise ContractError("hire_quota must be a positive configurable role goal")
    if type(director_enabled) is not bool:
        raise ContractError("director_enabled must be a boolean")
    return {
        "schema": "character_dynamics_online_session_v0", "actor_uid": actor_uid,
        "director_enabled": director_enabled,
        "actor_goal": {"kind": "party_quota", "required_hires": hire_quota,
                       "source": "ACTOR", "goal_id": "actor:party_quota"},
        "actor_history": {"observed_hired_uids": [], "goal_satisfied_at": None},
        "author_obligations": {}, "inflight_request": None,
        "decision_sequence": 0, "history": [], "last_observation_id": None,
    }


def _evaluate_version(version: dict[str, Any], game_time: float,
                      events: list[dict[str, Any]], coverage: float | None) -> dict[str, Any]:
    witnesses = sorted((event for event in events
                        if event["target_uid"] == version["target_uid"]
                        and event["hired_by_uid"] == version["hired_by_uid"]
                        and version["effective_at"] <= event["game_time"] <= game_time),
                       key=lambda event: event["game_time"])
    witness = witnesses[0] if witnesses else None
    timely_witnesses = [event for event in witnesses if event["game_time"] <= version["deadline"]]
    late_witnesses = [event for event in witnesses if event["game_time"] > version["deadline"]]
    if timely_witnesses:
        witness = timely_witnesses[0]
        status, reason = "SATISFIED", "nativefuture settlement event"
    elif late_witnesses and (coverage is None or coverage < version["deadline"]):
        witness = late_witnesses[0]
        status, reason = "UNKNOWN", "late native settlement observed; complete evidence through the deadline is unavailable"
    elif late_witnesses:
        witness = late_witnesses[0]
        status, reason = "VIOLATED", "complete native job-event coverage through the deadline found no timely witness; a later settlement was observed"
    elif coverage is not None and coverage >= version["deadline"]:
        witness = None
        status, reason = "VIOLATED", "complete native job-event coverage reached the absolute deadline without a witness"
    elif coverage is None:
        witness = None
        status, reason = "UNKNOWN", "global native event coverage is unavailable"
    elif game_time > version["deadline"]:
        witness = None
        status, reason = "UNKNOWN", "deadline passed but authoritative coverage does not reach the deadline"
    else:
        witness = None
        status, reason = "PENDING", "absolute deadline has not passed and no native settlement witness is recorded"
    return {"status": status, "reason": reason, "witness": witness}


def _obligation_status(obligation: dict[str, Any], game_time: float,
                       events: list[dict[str, Any]], coverage: float | None) -> dict[str, Any]:
    current = obligation["versions"][-1]
    version_results: list[dict[str, Any]] = []
    for version in obligation["versions"]:
        if "closed_verdict" in version:
            verdict = version["closed_verdict"]
            lifecycle = "SUPERSEDED"
        else:
            verdict = _evaluate_version(version, game_time, events, coverage)
            lifecycle = "ACTIVE"
        version_results.append({"version": version["version"], **verdict,
                                "lifecycle": lifecycle,
                                "closed_at": version.get("closed_at")})
    active = version_results[-1]
    return {"goal_id": obligation["goal_id"], "kind": "eventual_job_hired",
            "source": "AUTHOR", "active_version": current["version"],
            "status": active["status"], "reason": active["reason"],
            "target_uid": current["target_uid"], "hired_by_uid": current["hired_by_uid"],
            "deadline": current["deadline"], "versions": version_results}


def _apply_feedback(session: dict[str, Any], feedback: Sequence[object],
                    native_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inflight = session.get("inflight_request")
    applied: list[dict[str, Any]] = []
    # A native Job observation is an author witness and a request progress
    # fact, but native cleanup is complete only after the terminal arrives.
    if inflight and any(event["target_uid"] == inflight["target_uid"]
                        and event["hired_by_uid"] == session["actor_uid"]
                        and event.get("request_id") == inflight["request_id"]
                        for event in native_events):
        inflight["native_job_seen"] = True
    for row in feedback:
        if not isinstance(row, Mapping):
            raise ContractError("feedback rows must be objects")
        event_name = row.get("event")
        request_id = row.get("request_id")
        if event_name in ("native_recruit_terminal", "native_recruit_request_rejected"):
            if not isinstance(request_id, str) or not request_id:
                raise ContractError("native terminal needs request_id")
            matched = bool(inflight and request_id == inflight["request_id"]
                           and row.get("leader_uid") == session["actor_uid"]
                           and row.get("target_uid") == inflight["target_uid"])
            if matched and event_name == "native_recruit_request_rejected":
                inflight["terminal_outcome"] = "request_rejected"
            elif matched:
                outcome = row.get("outcome")
                if outcome not in {
                    "hired_observed", "expired_before_native_action",
                    "expired_after_native_action_before_message", "expired_after_message",
                    "leader_invalidated", "target_invalidated",
                }:
                    raise ContractError("unsupported native recruitment terminal outcome")
                inflight["terminal_outcome"] = outcome
            applied.append({"request_id": request_id, "event": event_name,
                            "matched": matched, "outcome": row.get("outcome")})
            continue
        status = row.get("status")
        if status not in ("SENT", "REJECTED", "SETTLED", "UNKNOWN"):
            raise ContractError("feedback status must be SENT, REJECTED, SETTLED, or UNKNOWN")
        if not isinstance(request_id, str) or not request_id:
            raise ContractError("feedback needs request_id")
        applied.append({"request_id": request_id, "status": status})
        if not inflight or request_id != inflight["request_id"]:
            continue
        inflight.setdefault("feedback_history", []).append({"status": status, "source": row.get("source", "runner")})
    if inflight and (inflight.get("terminal_outcome") in {
            "request_rejected", "expired_before_native_action",
            "expired_after_native_action_before_message", "expired_after_message",
            "leader_invalidated", "target_invalidated",
        } or (inflight.get("terminal_outcome") == "hired_observed"
              and inflight.get("native_job_seen") is True)):
        if inflight.get("terminal_outcome") != "hired_observed":
            session["last_native_terminal"] = {
                "request_id": inflight["request_id"], "target_uid": inflight["target_uid"],
                "outcome": inflight.get("terminal_outcome"),
                "actor_condition_signature": inflight.get("actor_condition_signature"),
            }
        session["inflight_request"] = None
    return applied


def step(session: Mapping[str, Any], actor_view: Mapping[str, Any], *, game_time: float,
         native_evidence: object = None, author_commands: Sequence[object] = (),
         director_hint: Mapping[str, Any] | None = None,
         feedback: Sequence[object] = ()) -> dict[str, Any]:
    """Consume one fresh ActorView plus separated monitor/runner inputs.

    Returns a new JSON-safe session and a proposal. It never writes a request
    file, changes native game state, or treats a prediction as a settlement.
    """
    state = json_safe(session)
    if state.get("schema") != "character_dynamics_online_session_v0":
        raise ContractError("unsupported session schema")
    actor_uid = state.get("actor_uid")
    if type(actor_uid) is not int:
        raise ContractError("session actor_uid is invalid")
    view = validate_actor_view(actor_view)
    if view["npc_uid"] != actor_uid:
        raise ContractError("ActorView npc_uid does not match session actor_uid")
    if not finite_number(game_time) or game_time < 0:
        raise ContractError("game_time must be an absolute non-negative number")
    now = float(game_time)
    if now < float(view["time"]):
        raise ContractError("game_time may not precede the ActorView time")
    observation_id = hashlib.sha256(json.dumps(view, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if observation_id == state.get("last_observation_id"):
        raise ContractError("each decision must consume a new ActorView observation")

    events, coverage, evidence_source = evidence_parts(native_evidence)
    # Evidence rows are global author-monitor input; never copy into ActorView.
    state.setdefault("native_job_evidence", []).extend(events)
    all_events = state["native_job_evidence"]
    prior_coverage = state.get("global_native_coverage_through")
    if coverage is not None:
        state["global_native_coverage_through"] = max(float(prior_coverage or 0), coverage)
    coverage = state.get("global_native_coverage_through")
    if coverage is not None and coverage > now:
        raise ContractError("global native coverage may not extend beyond current game_time")
    if evidence_source:
        state.setdefault("monitor_sources", []).append(evidence_source)

    obligations = state.setdefault("author_obligations", {})
    applied_commands: list[dict[str, Any]] = []
    for raw in author_commands:
        command = validate_command(raw, actor_uid, obligations)
        if command["op"] == "append":
            obligations[command["goal_id"]] = {
                "goal_id": command["goal_id"],
                "versions": [{**{key: command[key] for key in
                                 ("version", "kind", "target_uid", "hired_by_uid", "deadline", "source")},
                              "effective_at": now}],
            }
        else:
            record = obligations[command["goal_id"]]
            prior_version = record["versions"][-1]
            if "closed_verdict" not in prior_version:
                prior_version["closed_at"] = now
                prior_version["closed_verdict"] = _evaluate_version(prior_version, now, all_events, coverage)
            record["versions"].append(
                {**{key: command[key] for key in ("version", "kind", "target_uid", "hired_by_uid", "deadline", "source")},
                 "effective_at": now})
        applied_commands.append(command)

    # Actor history is built only from its own 24m ActorView. The ongoing
    # roster goal uses this observation, not cumulative historical witnesses.
    prior_local = set(state["actor_history"].get("last_local_hired_uids", []))
    local_now = {row["npc_uid"] for row in view["hired_members"]}
    observed = set(state["actor_history"].get("observed_hired_uids", [])) | local_now
    state["actor_history"]["observed_hired_uids"] = sorted(observed)
    state["actor_history"]["last_local_hired_uids"] = sorted(local_now)
    quota = state["actor_goal"]["required_hires"]
    actor_satisfied = len(local_now) >= quota
    if actor_satisfied and state["actor_history"].get("goal_satisfied_at") is None:
        state["actor_history"]["goal_satisfied_at"] = now

    applied_feedback = _apply_feedback(state, feedback, events)
    obligation_statuses = [_obligation_status(item, now, all_events, coverage)
                           for item in obligations.values()]

    hint = director_hint or {}
    if not isinstance(hint, Mapping):
        raise ContractError("director_hint must be an object")
    goal_order = hint.get("goal_order", []) if state["director_enabled"] else []
    candidate_order = hint.get("candidate_order", []) if state["director_enabled"] else []
    if not isinstance(goal_order, Sequence) or isinstance(goal_order, (str, bytes)):
        raise ContractError("director_hint.goal_order must be an array")
    if not isinstance(candidate_order, Sequence) or isinstance(candidate_order, (str, bytes)):
        raise ContractError("director_hint.candidate_order must be an array")
    goal_rank = {goal_id: index for index, goal_id in enumerate(goal_order) if isinstance(goal_id, str)}

    request: dict[str, Any] | None = None
    blocked: dict[str, Any] | None = None
    planning: dict[str, Any] | None = None
    inflight = state.get("inflight_request")
    active_obligations = sorted(
        (status for status in obligation_statuses if status["status"] in ("PENDING", "UNKNOWN")),
        key=lambda item: (goal_rank.get(item["goal_id"], len(goal_rank)), item["deadline"], item["goal_id"]))
    if inflight is not None:
        blocked = {"code": "NATIVE_REQUEST_IN_FLIGHT", "reason": "request has no verified native terminal; no cancellation or duplicate submission capability",
                   "request_id": inflight["request_id"], "target_uid": inflight["target_uid"],
                   "goal_id": inflight.get("goal_id"),
                   "native_job_seen": inflight.get("native_job_seen", False),
                   "terminal_outcome": inflight.get("terminal_outcome")}
    else:
        goal = active_obligations[0] if active_obligations and state["director_enabled"] else None
        source = "DIRECTOR" if goal else "ACTOR"
        if goal is None and actor_satisfied:
            plan = {"status": "GOAL_SATISFIED", "reason": "ACTOR party quota has been met by actor-visible native Job observations", "target_uid": None}
        else:
            target = goal["target_uid"] if goal else None
            plan = choose_recruit_target(dict(view), target_uid=target,
                                         candidate_order=list(candidate_order))
        planning = json_safe(plan)
        if plan["status"] == "PROPOSED":
            last_terminal = state.get("last_native_terminal")
            same_failed_choice = bool(
                last_terminal
                and last_terminal["target_uid"] == plan["target_uid"]
                and last_terminal.get("actor_condition_signature") == _actor_condition_signature(view)
            )
            if same_failed_choice:
                blocked = {"code": "NATIVE_TERMINAL_REQUIRES_CHANGED_ACTOR_VIEW",
                           "reason": "the same candidate remains eligible under unchanged native guards after its native terminal",
                           "request_id": last_terminal["request_id"],
                           "target_uid": last_terminal["target_uid"],
                           "terminal_outcome": last_terminal["outcome"]}
                planning["proposal_suppressed"] = True
            else:
                seq = int(state["decision_sequence"]) + 1
                goal_id = goal["goal_id"] if goal else state["actor_goal"]["goal_id"]
                source_name = source
                raw_id = f"{actor_uid}:{seq}:{plan['target_uid']}:{now:.6f}:{source_name}"
                request_id = hashlib.sha256(raw_id.encode()).hexdigest()[:20]
                request = {"request_id": request_id, "task": "RecruitMember",
                           "leader_uid": actor_uid, "target_uid": plan["target_uid"],
                           "goal_id": goal_id, "source": source_name,
                           "author_version": goal["active_version"] if goal else None,
                           "observed_time": float(view["time"]), "deadline": goal["deadline"] if goal else None,
                           "native_settlement": "awaiting Veloren"}
                state["inflight_request"] = {"request_id": request_id, "target_uid": plan["target_uid"],
                                              "goal_id": goal_id, "source": source_name,
                                              "author_version": goal["active_version"] if goal else None,
                                              "created_at": now, "feedback_history": [],
                                              "native_job_seen": False, "terminal_outcome": None,
                                              "actor_condition_signature": _actor_condition_signature(view)}
        elif goal is not None:
            blocked = {"code": plan["status"], "reason": plan["reason"],
                       "goal_id": goal["goal_id"], "source": "DIRECTOR"}
        elif not actor_satisfied:
            blocked = {"code": plan["status"], "reason": plan["reason"],
                       "goal_id": state["actor_goal"]["goal_id"], "source": "ACTOR"}

    state["decision_sequence"] = int(state["decision_sequence"]) + 1
    state["last_observation_id"] = observation_id
    decision = {
        "sequence": state["decision_sequence"], "game_time": now,
        "actor_view_time": float(view["time"]),
        "sources": {"native": "NATIVE", "actor_goal": "ACTOR",
                    "author_goals": "AUTHOR", "coordination": "DIRECTOR"},
        "director_enabled": state["director_enabled"],
        "actor_goal": {**state["actor_goal"], "status": "SATISFIED" if actor_satisfied else "PENDING",
                       "observed_hired_uids": sorted(local_now),
                       "historical_actor_observed_hired_uids": sorted(observed),
                       "previously_visible_now_unknown_uids": sorted(prior_local - local_now)},
        "author_obligations": obligation_statuses,
        "author_commands_applied": applied_commands,
        "feedback_applied": applied_feedback,
        "global_native_coverage_through": coverage,
        "global_evidence_source": evidence_source,
        "planning": planning, "request": request, "blocked": blocked,
        "continuation": "ACTOR_GOAL_MET_NATIVE_MAY_CONTINUE" if actor_satisfied and request is None and blocked is None else None,
        "prediction_is_not_settlement": True,
    }
    state.setdefault("history", []).append(json_safe(decision))
    return {"session": json_safe(state), "decision": json_safe(decision)}
