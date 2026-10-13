"""GTPyhop decomposition and event-driven baseline for one bounded story process.

Planning emits actor task requests only. The native executor owns task acceptance,
actions, receipts, event projection, and settlement.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from typing import Any, Mapping

from .model import METHODS, StoryProcessRequest

SCHEMA = "story-process-decision-v1"
_DOMAIN = "native-p5-story-process-v1"
_SEALED_KEYS = {"scenario_id", "sealed_minute", "horizon", "request_id", "request_version",
                "response", "note", "actors", "destinations", "task_grant",
                "current_obligations", "typed_trace", "event_registry"}
_ACTOR_KEYS = {"present", "can_receive_note", "willing_to_archive", "locally_observed_item_ids",
               "active_task", "task_status", "remaining_work_minutes"}


def _validate_state(request: StoryProcessRequest, state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, StoryProcessRequest):
        raise TypeError("request must be a validated StoryProcessRequest")
    if not isinstance(state, Mapping) or set(state) != _SEALED_KEYS:
        raise ValueError(f"sealed_state requires exact keys {sorted(_SEALED_KEYS)}")
    # Registry is immutable but contains MappingProxyType entries; preserve its
    # reference while copying all mutable evidence projections.
    s = {key: value if key == "event_registry" else deepcopy(value)
         for key, value in state.items()}
    if (s["scenario_id"] != request.scenario_id or s["request_id"] != request.request_id
            or s["request_version"] != request.version or s["task_grant"] != request.task_control_grant):
        raise ValueError("sealed state is not bound to this request version, scenario, and immutable grant")
    now, horizon = s["sealed_minute"], s["horizon"]
    if (type(now) is not int or type(horizon) is not int or not 0 <= now <= horizon <= 24):
        raise ValueError("sealed minute/horizon must fit the fixed absolute 24-minute scenario")
    response, note = s["response"], s["note"]
    if not isinstance(note, Mapping) or set(note) != {"item_id", "location_id", "holder_alias"}:
        raise ValueError("exact note identity/location/holder projection is required")
    note_id = request.objective["note_id"]
    if (type(note["item_id"]) is not int or note["item_id"] != note_id
            or type(note["location_id"]) is not int or note["location_id"] <= 0
            or note["holder_alias"] not in {None, "A", "B", "PLAYER", "ROOM"}):
        raise ValueError("note projection must identify the exact authored entity")
    if response is not None:
        if (not isinstance(response, Mapping) or set(response) != {"outcome", "event_id", "minute", "note_id"}
                or response["outcome"] not in {"accepted", "rejected"}
                or not isinstance(response["event_id"], str) or not response["event_id"]
                or type(response["minute"]) is not int or not 0 <= response["minute"] <= now
                or response["note_id"] != note_id):
            raise ValueError("response must be an already sealed native event for this exact note")
        real_response = [e for e in s["typed_trace"].get("events", ()) if isinstance(e, Mapping)
                         and e.get("event_id") == response["event_id"]
                         and e.get("event_type") == "p5_note_response"
                         and e.get("provenance") == "committed_ledger"]
        if len(real_response) != 1:
            raise ValueError("response event id is not present exactly once in committed TypedIR evidence")
    actors = s["actors"]
    if not isinstance(actors, Mapping) or set(actors) != {"A", "B"}:
        raise ValueError("sealed actor-local projections for A and B are required")
    for alias, actor in actors.items():
        if not isinstance(actor, Mapping) or set(actor) != _ACTOR_KEYS:
            raise ValueError(f"actor {alias} projection requires exact keys {sorted(_ACTOR_KEYS)}")
        if any(type(actor[k]) is not bool for k in ("present", "can_receive_note", "willing_to_archive")):
            raise ValueError(f"actor {alias} eligibility flags must be booleans")
        if (actor["remaining_work_minutes"] is not None
                and (type(actor["remaining_work_minutes"]) is not int
                     or actor["remaining_work_minutes"] < 0)):
            raise ValueError(f"actor {alias} remaining_work_minutes must be a nonnegative local estimate or null")
        if (not isinstance(actor["locally_observed_item_ids"], list)
                or any(type(i) is not int or i <= 0 for i in actor["locally_observed_item_ids"])):
            raise ValueError(f"actor {alias} observation must contain exact positive IDs")
        if actor["task_status"] not in {"IDLE", "ACCEPTED", "REJECTED", "IN_PROGRESS", "SETTLED", "BLOCKED"}:
            raise ValueError(f"actor {alias} task status is unsupported")
        active = actor["active_task"]
        if active is not None:
            if not isinstance(active, Mapping) or set(active) != {
                    "request_id", "task_kind", "item_id", "destination_id", "status"}:
                raise ValueError("active_task must be null or the exact actor-local story-task projection")
            if (not isinstance(active["request_id"], str) or active["task_kind"] not in {"handover_note", "archive_note"}
                    or active["item_id"] != note_id or type(active["destination_id"]) is not int
                    or active["status"] not in {"ACCEPTED", "IN_PROGRESS", "REJECTED", "SETTLED", "BLOCKED"}):
                raise ValueError("active story-task projection is malformed or bound to another entity")
    destinations = s["destinations"]
    if not isinstance(destinations, Mapping) or set(destinations) != {"archive", "handover"}:
        raise ValueError("registered archive and handover destinations are required")
    for key in ("archive", "handover"):
        row = destinations[key]
        if (not isinstance(row, Mapping) or set(row) != {"id", "reachable_by", "estimated_minutes",
                                                         "estimated_minutes_by_actor"}
                or type(row["id"]) is not int or row["id"] <= 0
                or not isinstance(row["reachable_by"], list)
                or any(a not in {"A", "B"} for a in row["reachable_by"])
                or type(row["estimated_minutes"]) is not int or row["estimated_minutes"] < 0
                or not isinstance(row["estimated_minutes_by_actor"], Mapping)
                or set(row["estimated_minutes_by_actor"]) != {"A", "B"}
                or any(value is not None and (type(value) is not int or value < 0)
                       for value in row["estimated_minutes_by_actor"].values())):
            raise ValueError(f"{key} destination needs a registered ID, reachability, and sealed time estimate")
    if not isinstance(s["current_obligations"], list) or not isinstance(s["typed_trace"], Mapping):
        raise ValueError("current obligations and TypedIR trace are required")
    if not isinstance(s["typed_trace"].get("events"), list):
        raise ValueError("TypedIR trace must expose committed event rows")
    if s["event_registry"] is None:
        raise ValueError("the existing TypedIR event registry must be supplied")
    return s


def _task_request(request: StoryProcessRequest, state: Mapping[str, Any], actor: str,
                  kind: str, method: str, prerequisites: list[str] | None = None,
                  rendezvous_destination_id: int | None = None,
                  required_story_events: Mapping[str, Any] | None = None) -> dict[str, Any]:
    destination_key = "handover" if kind == "handover_note" else "archive"
    dest = state["destinations"][destination_key]
    row = {"request_id": f"{request.request_id}:v{request.version}:{method}:{actor}:{kind}",
            "actor_alias": actor, "task_kind": kind, "item_id": request.objective["note_id"],
            "destination_id": dest["id"],
            "prerequisites": list(prerequisites or ["sealed_native_note_response",
                              "actor_locally_observes_exact_note", "native_actor_accepts_task"]),
            "source_method_id": method,
            "control_source": ("AUTHORED" if request.control["mode"] == "direct" else
                               "LOCKED_FRAGMENT" if request.control["mode"] == "locked_fragment" else "PLANNER"),
            "grant_id": request.task_control_grant["grant_id"]}
    if required_story_events is not None:
        required = required_story_events.get("required_handover")
        row["required_constraint_ids"] = [required_story_events["archive_constraint_id"]]
        row["required_story_event_types"] = ["p5_note_archived"]
        row["earliest_terminal_minute"] = (
            required["start_minute"] if kind == "handover_note" and required
            else 0 if kind == "handover_note"
            else required_story_events["archive_start_minute"])
        row["required_story_deadline_minute"] = (
            required["deadline_minute"] if kind == "handover_note" and required
            else request.objective["by_minute"] if kind == "handover_note"
            else required_story_events["archive_deadline_minute"])
        if required:
            row["required_constraint_ids"].extend([
                required["event_count_constraint_id"], required["order_constraint_id"]])
            row["required_story_event_types"] = ["p5_note_handed_over", "p5_note_archived"]
            row["required_story_deadline_minute"] = required["deadline_minute"]
    if rendezvous_destination_id is not None:
        row["rendezvous_destination_id"] = rendezvous_destination_id
    return row


def _validate_story_requirements(request: StoryProcessRequest,
                                 requirements: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if requirements is None:
        return None
    if (not isinstance(requirements, Mapping)
            or set(requirements) != {"source_bundle_id", "source_version", "source_sha256",
                                     "archive_constraint_id", "archive_start_minute",
                                     "archive_deadline_minute", "note_id",
                                     "required_handover", "residual_constraints"}
            or not isinstance(requirements["source_bundle_id"], str)
            or not requirements["source_bundle_id"]
            or type(requirements["source_version"]) is not int or requirements["source_version"] < 1
            or not isinstance(requirements["source_sha256"], str)
            or len(requirements["source_sha256"]) != 64
            or not isinstance(requirements["archive_constraint_id"], str)
            or not requirements["archive_constraint_id"]
            or type(requirements["archive_start_minute"]) is not int
            or not 0 <= requirements["archive_start_minute"] <= request.objective["by_minute"]
            or type(requirements["archive_deadline_minute"]) is not int
            or requirements["archive_deadline_minute"] != request.objective["by_minute"]
            or requirements["archive_start_minute"] > requirements["archive_deadline_minute"]
            or requirements["note_id"] != request.objective["note_id"]
            or not isinstance(requirements["residual_constraints"], list)):
        raise ValueError("required_story_events must be bound to the current AuthorBundle, archive goal, deadline, and exact note")
    for row in requirements["residual_constraints"]:
        if (not isinstance(row, Mapping)
                or set(row) != {"constraint_id", "kind", "source_constraint_sha256"}
                or not all(isinstance(row[key], str) and row[key]
                           for key in ("constraint_id", "kind", "source_constraint_sha256"))):
            raise ValueError("residual authored constraints must remain explicitly identified")
    handover = requirements["required_handover"]
    if handover is not None:
        keys = {"event_count_constraint_id", "order_constraint_id", "event_type", "actor_alias",
                "recipient_alias", "before_event_type", "start_minute", "deadline_minute"}
        if (not isinstance(handover, Mapping) or set(handover) != keys
                or not all(isinstance(handover[key], str) and handover[key]
                           for key in ("event_count_constraint_id", "order_constraint_id"))
                or handover["event_count_constraint_id"] == handover["order_constraint_id"]
                or handover["event_type"] != "p5_note_handed_over"
                or handover["actor_alias"] != "B" or handover["recipient_alias"] != "A"
                or handover["before_event_type"] != "p5_note_archived"
                or type(handover["deadline_minute"]) is not int
                or type(handover["start_minute"]) is not int
                or not 0 <= handover["start_minute"] <= handover["deadline_minute"]
                or not requirements["archive_start_minute"] <= handover["start_minute"]
                or not 1 <= handover["deadline_minute"] <= requirements["archive_deadline_minute"]):
            raise ValueError("required handover must be the registered same-note B→A event strictly before archive")
    return deepcopy(dict(requirements))


def _causal_support(method: str, requirements: Mapping[str, Any] | None) -> dict[str, Any]:
    required = ["p5_note_archived"]
    if requirements and requirements.get("required_handover"):
        required = ["p5_note_handed_over", "p5_note_archived"]
    supported = ({"p5_note_archived"} if method == "file_by_B" else
                 {"p5_note_handed_over", "p5_note_archived"})
    missing = [event for event in required if event not in supported]
    if requirements and requirements.get("residual_constraints"):
        missing.extend(f"unmapped_constraint:{row['constraint_id']}"
                       for row in requirements["residual_constraints"])
    return {"supported_event_types": sorted(supported),
            "required_event_types": required,
            "missing_required_event_types": missing}


def _method_preconditions(method: str, request: StoryProcessRequest, s: Mapping[str, Any],
                          required_story_events: Mapping[str, Any] | None = None) -> tuple[bool, list[str], list[dict[str, Any]]]:
    reasons: list[str] = []
    tasks: list[dict[str, Any]] = []
    support = _causal_support(method, required_story_events)
    if support["missing_required_event_types"]:
        reasons.append("method_lacks_causal_support_for_required_story_event:" +
                       ",".join(support["missing_required_event_types"]))
    handover_requirement = (required_story_events or {}).get("required_handover")
    if (method == "return_then_file_by_A" and handover_requirement
            and s["sealed_minute"] < handover_requirement["start_minute"]):
        reasons.append("waiting_for_authored_handover_window_start")
    mode, control = request.control["mode"], request.control
    allowed = set(control["allowed_methods"])
    if method not in allowed:
        reasons.append("method_not_allowed_by_current_authored_request")
    if mode == "zero":
        reasons.append("zero_control_mode_does_not_authorize_task_requests")
    if control["file_actor"] and method == "file_by_B" and control["file_actor"] != "B":
        reasons.append("file_actor_edit_excludes_B")
    if control["file_actor"] and method == "return_then_file_by_A" and control["file_actor"] != "A":
        reasons.append("file_actor_edit_excludes_A")
    response, note = s["response"], s["note"]
    if response is None:
        reasons.append("waiting_for_actual_native_note_response")
        return False, reasons, tasks
    if not s["actors"]["B"]["present"] or note["holder_alias"] != "B":
        reasons.append("B_does_not_hold_exact_note")
    if method == "file_by_B":
        disposition = request.actor_postresponse[response["outcome"]]["B_archive"]
        if disposition == "UNWILLING":
            reasons.append("authored_character_task_disposition_B_archive_unwilling")
        if "B" not in s["destinations"]["archive"]["reachable_by"]:
            reasons.append("archive_location_not_reachable_by_B")
        if _actor_busy(s["actors"]["B"]):
            reasons.append("B_has_an_unsettled_native_task_that_retains_priority")
        if s["actors"]["B"]["remaining_work_minutes"] is None:
            reasons.append("B_remaining_commitment_work_is_unknown")
        if _task_rejected(s["actors"]["B"], "archive_note"):
            reasons.append("B_previously_rejected_this_local_task")
        if request.objective["note_id"] not in s["actors"]["B"]["locally_observed_item_ids"]:
            reasons.append("B_has_not_locally_observed_exact_note")
        tasks = [_task_request(request, s, "B", "archive_note", method,
                               required_story_events=required_story_events)]
    elif method == "return_then_file_by_A":
        a, b = s["actors"]["A"], s["actors"]["B"]
        if not a["present"] or not a["can_receive_note"]:
            reasons.append("A_cannot_legally_receive_note_now")
        if not b["present"]:
            reasons.append("B_is_not_present_for_handover")
        if "B" not in s["destinations"]["handover"]["reachable_by"] or "A" not in s["destinations"]["handover"]["reachable_by"]:
            reasons.append("registered_handover_location_not_reachable_by_both_actors")
        dispositions = request.actor_postresponse[response["outcome"]]
        if dispositions["B_return"] == "UNWILLING":
            reasons.append("authored_character_task_disposition_B_return_unwilling")
        if dispositions["A_archive"] == "UNWILLING":
            reasons.append("authored_character_task_disposition_A_archive_unwilling")
        if "A" not in s["destinations"]["archive"]["reachable_by"]:
            reasons.append("archive_location_not_reachable_by_A")
        if any(_actor_busy(s["actors"][actor]) for actor in ("A", "B")):
            reasons.append("required_actor_has_an_unsettled_native_task_that_retains_priority")
        if any(s["actors"][actor]["remaining_work_minutes"] is None for actor in ("A", "B")):
            reasons.append("required_actor_remaining_commitment_work_is_unknown")
        if (_task_rejected(s["actors"]["B"], "handover_note")
                or _task_rejected(s["actors"]["A"], "archive_note")):
            reasons.append("an_actor_previously_rejected_a_required_local_task")
        if request.objective["note_id"] not in b["locally_observed_item_ids"]:
            reasons.append("B_has_not_locally_observed_exact_note_for_handover")
        tasks = [_task_request(request, s, "B", "handover_note", method,
                               required_story_events=required_story_events),
                 _task_request(request, s, "A", "archive_note", method,
                               prerequisites=["committed_native_handover_receipt_for_exact_note_at_rendezvous",
                                              "A_locally_observes_exact_note", "native_actor_accepts_task"],
                               rendezvous_destination_id=s["destinations"]["handover"]["id"],
                               required_story_events=required_story_events)]
    else:
        reasons.append("unknown_method")
    timing = _timing_budget(request, s, tasks)
    effective_deadline = min(request.objective["by_minute"],
                             handover_requirement["deadline_minute"]
                             if handover_requirement else request.objective["by_minute"])
    if timing["projected_finish_minute"] > effective_deadline:
        reasons.append("absolute_deadline_time_infeasible")
    if required_story_events and required_story_events.get("required_handover"):
        handover_deadline = required_story_events["required_handover"]["deadline_minute"]
        handover_finish = s["sealed_minute"] + timing["handover_completion_offset_minutes"]
        if handover_finish > handover_deadline:
            reasons.append("absolute_handover_deadline_time_infeasible")
    return not reasons, reasons, tasks


def _actor_busy(actor: Mapping[str, Any]) -> bool:
    active = actor.get("active_task")
    return bool(active and active.get("status") in {"ACCEPTED", "IN_PROGRESS"}) or actor.get("task_status") in {"ACCEPTED", "IN_PROGRESS"}


def _task_rejected(actor: Mapping[str, Any], task_kind: str) -> bool:
    active = actor.get("active_task")
    return bool(active and active.get("task_kind") == task_kind and active.get("status") == "REJECTED")


def _timing_budget(request: StoryProcessRequest, s: Mapping[str, Any], tasks: list[dict[str, Any]]) -> dict[str, int | bool]:
    route = 0
    handover_offset = 0
    for row in tasks:
        key = "handover" if row["task_kind"] == "handover_note" else "archive"
        destination = s["destinations"][key]
        actor = row["actor_alias"]
        per_actor = destination.get("estimated_minutes_by_actor", {})
        minutes = per_actor.get(actor, destination["estimated_minutes"])
        if row["task_kind"] == "handover_note":
            # Both participants must reach the registered rendezvous before the
            # give can occur; this remains a route lower-bound, not a guarantee.
            minutes = max(per_actor.get("A", minutes), per_actor.get("B", minutes))
        route += minutes
        if row["task_kind"] == "handover_note":
            handover_offset = route
    if tasks and tasks[0]["source_method_id"] == "file_by_B":
        workload = s["actors"]["B"]["remaining_work_minutes"] or 0
    elif tasks:
        workload = max(s["actors"][alias]["remaining_work_minutes"] or 0 for alias in ("A", "B"))
    else:
        workload = 0
    cost = route + workload
    if handover_offset:
        handover_offset += workload
    finish = s["sealed_minute"] + cost
    return {"estimated_task_minutes": cost, "sealed_minute": s["sealed_minute"],
            "route_task_minutes": route, "remaining_work_lower_bound_minutes": workload,
            "remaining_work_basis": "receipt-verified actor-local primitive lower bound; null means unknown; not a route-feasibility proof",
            "handover_completion_offset_minutes": handover_offset,
            "projected_finish_minute": finish,
            "absolute_deadline_minute": request.objective["by_minute"],
            "effective_story_deadline_minute": min(
                request.objective["by_minute"],
                tasks[0].get("required_story_deadline_minute", request.objective["by_minute"])) if tasks else request.objective["by_minute"],
            "remaining_minutes": max(0, request.objective["by_minute"] - s["sealed_minute"]),
            "deadline_fit": finish <= request.objective["by_minute"]}


def _preserved_obligations(s: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = deepcopy(list(s["current_obligations"]))
    for alias, actor in s["actors"].items():
        task = actor["active_task"]
        if task is not None:
            rows.append({"kind": "actor_story_task", "actor_alias": alias,
                         "request_id": task["request_id"], "task_kind": task["task_kind"],
                         "item_id": task["item_id"], "status": task["status"],
                         "preserved": True})
    return rows


def _temporary_method_wait(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transient = {"B_has_an_unsettled_native_task_that_retains_priority",
                 "required_actor_has_an_unsettled_native_task_that_retains_priority",
                 "B_remaining_commitment_work_is_unknown",
                 "required_actor_remaining_commitment_work_is_unknown",
                 "waiting_for_authored_handover_window_start"}
    waits = []
    for row in candidates:
        blockers = [reason for reason in row.get("preconditions", ()) if reason in transient]
        if blockers:
            waits.append({"kind": "WAITING_FOR_ACTOR_COMMITMENT_FRONTIER",
                          "method_id": row.get("method_id"),
                          "temporary_blockers": blockers})
    return waits


def _locked_tasks(request: StoryProcessRequest, s: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    fragment = request.locked_fragment
    assert fragment is not None
    reasons = []
    guard = fragment["entry_guard"]
    if guard["response_required"] and s["response"] is None:
        reasons.append("locked_fragment_entry_guard_requires_actual_response")
    if s["note"]["holder_alias"] != guard["note_holder_alias"]:
        reasons.append("locked_fragment_entry_guard_note_holder_mismatch")
    if reasons:
        return [], reasons
    rows = []
    for index, task in enumerate(fragment["sequence"]):
        destination = s["destinations"][task["destination_ref"]]
        rows.append({"request_id": f"{request.request_id}:v{request.version}:locked:{index}",
                     "actor_alias": task["actor_alias"], "task_kind": task["task_kind"],
                     "item_id": request.objective["note_id"], "destination_id": destination["id"],
                     "item_ref": task["item_ref"], "destination_ref": task["destination_ref"],
                     "prerequisites": ["exact_locked_sequence", "native_actor_accepts_task"],
                     "source_method_id": "locked_fragment",
                     "control_source": "LOCKED_FRAGMENT",
                     "grant_id": request.task_control_grant["grant_id"]})
    return rows, []


def _typedir_monitor(request: StoryProcessRequest, s: Mapping[str, Any],
                     required_story_events: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Evaluate the existing typed event registry over the sealed ledger trace."""
    from tools.trajectory_constraints_v0.ast import EventCount, EventOrder, StrictOrder, Window
    from tools.trajectory_constraints_v0.trace import Event, Trace
    from tools.trajectory_constraints_v0.monitor import evaluate
    from tools.trajectory_constraints_v0.types import StableEntity

    aliases = {"A": StableEntity("Actor", "A", "A"), "B": StableEntity("Actor", "B", "B"),
               "note": StableEntity("Item", str(request.objective["note_id"]), "note")}
    trace = Trace(now=s["sealed_minute"])
    for row in s["typed_trace"]["events"]:
        if not isinstance(row, Mapping) or row.get("provenance") != "committed_ledger":
            continue
        args = dict(row.get("args", {}))
        for key, value in list(args.items()):
            if isinstance(value, Mapping) and value.get("stable_id") is not None:
                typ = value.get("entity_type")
                args[key] = StableEntity(str(typ), str(value["stable_id"]), str(value.get("label", value["stable_id"])))
            elif isinstance(value, str) and value in aliases and key in {"actor", "recipient", "item"}:
                args[key] = aliases[value]
        trace.add_event(Event(str(row["event_id"]), str(row["event_type"]), row["time"], row["sequence"],
                              args, str(row.get("version", "1")), "committed_ledger"))
    trace.seal_events_through(s["sealed_minute"])
    note = aliases["note"]
    permitted_actors = {request.control["file_actor"]} if request.control["file_actor"] else set()
    if not permitted_actors and len(request.control["allowed_methods"]) == 1:
        only_method = request.control["allowed_methods"][0]
        permitted_actors = {"B" if only_method == "file_by_B" else "A"}
    actor_filter = {"actor": aliases[next(iter(permitted_actors))]} if len(permitted_actors) == 1 else {}
    constraints = [
        EventCount("story-note-archive-by-deadline", "p5_note_archived", "1",
                   Window(required_story_events["archive_start_minute"] if required_story_events else 0,
                          request.objective["by_minute"]),
                   minimum=1, maximum=1, event_filter={"item": note, **actor_filter}),
        EventOrder("story-response-before-archive", "p5_note_response", "1",
                   "p5_note_archived", "1", StrictOrder.EVENT_KEY,
                   Window(0, request.objective["by_minute"]),
                   before_filter={"actor": aliases["A"], "recipient": aliases["B"], "item": note},
                   after_filter={"item": note, **actor_filter}),
        EventCount("story-note-handover-at-most-once", "p5_note_handed_over", "1",
                   Window(0, request.objective["by_minute"]), minimum=0, maximum=1,
                   event_filter={"item": note}),
    ]
    if required_story_events and required_story_events.get("required_handover"):
        required = required_story_events["required_handover"]
        handover_window = Window(required["start_minute"], required["deadline_minute"])
        constraints.extend([
            EventCount(required["event_count_constraint_id"], "p5_note_handed_over", "1",
                       handover_window, minimum=1, maximum=1,
                       event_filter={"actor": aliases["B"], "recipient": aliases["A"], "item": note}),
            EventOrder(required["order_constraint_id"], "p5_note_handed_over", "1",
                       "p5_note_archived", "1", StrictOrder.EVENT_KEY,
                       handover_window,
                       before_filter={"actor": aliases["B"], "recipient": aliases["A"], "item": note},
                       after_filter={"item": note}),
        ])
    result = []
    for constraint in constraints:
        try:
            verdicts = evaluate(constraint, trace, s["event_registry"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"TypedIR event registry/evidence rejected the story-process trace: {exc}") from exc
        result.append({"constraint_id": constraint.constraint_id,
                       "verdicts": [{"verdict": v.verdict.value, "reason": v.reason,
                                     "witness": v.witness,
                                     "activation_id": v.activation_id} for v in verdicts]})
    if len(permitted_actors) != 1:
        permitted = permitted_actors or ({"A", "B"} if len(request.control["allowed_methods"]) == 2 else set())
        archive_rows = [e for e in s["typed_trace"]["events"]
                        if isinstance(e, Mapping) and e.get("event_type") == "p5_note_archived"
                        and e.get("provenance") == "committed_ledger"
                        and str(_event_arg_id(e, "item")) == str(request.objective["note_id"])]
        if archive_rows:
            legal = [e for e in archive_rows if _event_actor_alias(e) in permitted]
            result.append({"constraint_id": "story-authorized-filer",
                           "verdicts": [{"verdict": "SATISFIED" if legal else "VIOLATED",
                                         "reason": "archive filer is within authored future method scope" if legal else
                                                   "archive filer violates authored future method scope",
                                         "event_ids": [e["event_id"] for e in (legal or archive_rows)]}]})
    return result


def _event_arg_id(event: Mapping[str, Any], key: str) -> Any:
    value = event.get("args", {}).get(key)
    return value.get("stable_id") if isinstance(value, Mapping) else value


def _event_actor_alias(event: Mapping[str, Any]) -> str | None:
    value = _event_arg_id(event, "actor")
    if value in {"A", "B"}:
        return value
    return None


def _event_baseline(request: StoryProcessRequest, s: Mapping[str, Any],
                    required_story_events: Mapping[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic strong event dispatcher over exactly the same legal method set."""
    if s["response"] is None or request.control["mode"] == "zero":
        return [], [], [{"kind": "WAITING_FOR_NATIVE_RESPONSE" if s["response"] is None else "NO_TASK_AUTHORIZED"}]
    feasible = []
    rejected = []
    candidates = []
    for method in ("file_by_B", "return_then_file_by_A"):
        ok, guards, tasks = _method_preconditions(method, request, s, required_story_events)
        row = {"method_id": method, "feasible": ok, "preconditions": guards,
               "causal_support": _causal_support(method, required_story_events),
               "task_requests": tasks}
        row["resource_time"] = _timing_budget(request, s, tasks)
        candidates.append(row)
        (feasible if ok else rejected).append(row)
    # Same content, affordances, permissions, and cost; fixed event policy prefers B's filing.
    chosen = next((row for row in feasible if row["method_id"] == "file_by_B"), None)
    if chosen is None and feasible:
        chosen = feasible[0]
    return (list(chosen["task_requests"]) if chosen else []), candidates, rejected


def plan_story_process(request: StoryProcessRequest, sealed_state: Mapping[str, Any], *, strategy: str = "gtpyhop",
                       required_story_events: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Plan task requests from a sealed state; never applies world effects."""
    s = _validate_state(request, sealed_state)
    required_story_events = _validate_story_requirements(request, required_story_events)
    if strategy not in {"gtpyhop", "event_driven"}:
        raise ValueError("strategy must be gtpyhop or event_driven")
    # Report the same-state alternative guards independently of search.  This is
    # diagnostic evidence only: it must not preselect, order, or feed the planner.
    alternative_guard_diagnostics = []
    for method in ("file_by_B", "return_then_file_by_A"):
        feasible, guards, tasks = _method_preconditions(method, request, s, required_story_events)
        alternative_guard_diagnostics.append({
            "method_id": method,
            "feasible": feasible,
            "preconditions": guards,
            "causal_support": _causal_support(method, required_story_events),
            "resource_time": _timing_budget(request, s, tasks),
            "diagnostic_only": True,
            "used_to_select_method": False,
        })
    mode = request.control["mode"]
    # Non-search control modes do not invoke GTPyhop; keep their trace empty and
    # avoid leaking an uninitialized local in the serialized decision.
    extra_trace = []
    if mode == "zero":
        reqs, candidates, rejected, attempts, decomposition = [], [], [], [], []
        outstanding = _preserved_obligations(s)
        status = "NO_CONTROL"
    elif mode == "locked_fragment":
        reqs, reasons = _locked_tasks(request, s)
        candidates = [{"method_id": "locked_fragment", "feasible": not reasons,
                       "preconditions": reasons, "decomposition": deepcopy(reqs)}]
        rejected, attempts, decomposition = [], [], deepcopy(reqs)
        outstanding = _preserved_obligations(s)
        outstanding.append({"kind": "LOCKED_FRAGMENT_ENTRY_GUARD", "reasons": reasons} if reasons else
                           {"kind": "LOCKED_TASKS_AWAIT_NATIVE_ACCEPTANCE",
                            "request_ids": [r["request_id"] for r in reqs]})
        status = "LOCKED_ABORTED" if reasons else "TASKS_PROPOSED"
    elif strategy == "event_driven":
        reqs, candidates, rejected = _event_baseline(request, s, required_story_events)
        attempts, decomposition = deepcopy(candidates), deepcopy(reqs)
        outstanding = _preserved_obligations(s)
        if not reqs:
            waits = _temporary_method_wait(candidates)
            outstanding.extend(waits)
            if not waits:
                outstanding.append({"kind": "WAITING_FOR_NATIVE_RESPONSE" if s["response"] is None else "NO_FEASIBLE_METHOD"})
        status = "TASKS_PROPOSED" if reqs else "WAITING_OR_BLOCKED"
    else:
        try:
            import gtpyhop as g
            import gtpyhop.main as main
        except ImportError as exc:
            raise RuntimeError("story-process GTN requires the already pinned GTPyhop installation") from exc
        from tools.native_platform_v0.p3.planning import _LOCK
        state = g.State("native-story-process")
        state.proposals = []
        state.request = request
        state.sealed = {key: value for key, value in s.items() if key != "event_registry"}
        state.outstanding = _preserved_obligations(s)

        def emit_task(world, task):
            world.proposals.append(deepcopy(task))
            return world

        def wait_response(world):
            world.outstanding.append({"kind": "WAITING_FOR_NATIVE_RESPONSE",
                                      "deadline": world.request.objective["by_minute"]})
            return world

        method_attempts = []

        def file_by_B(world):
            ok, guards, tasks = _method_preconditions("file_by_B", world.request, world.sealed, required_story_events)
            method_attempts.append({"method_id": "file_by_B", "feasible": ok,
                                    "preconditions": guards, "decomposition": deepcopy(tasks),
                                    "causal_support": _causal_support("file_by_B", required_story_events),
                                    "resource_time": _timing_budget(world.request, world.sealed, tasks)})
            return [("emit_task", tasks[0])] if ok else None

        def return_then_file_by_A(world):
            ok, guards, tasks = _method_preconditions("return_then_file_by_A", world.request, world.sealed, required_story_events)
            method_attempts.append({"method_id": "return_then_file_by_A", "feasible": ok,
                                    "preconditions": guards, "decomposition": deepcopy(tasks),
                                    "causal_support": _causal_support("return_then_file_by_A", required_story_events),
                                    "resource_time": _timing_budget(world.request, world.sealed, tasks)})
            return [("emit_task", tasks[0]), ("emit_task", tasks[1])] if ok else None

        def wait_for_response(world):
            ok = world.sealed["response"] is None
            method_attempts.append({"method_id": "wait_for_response", "feasible": ok,
                                    "preconditions": [] if ok else ["a sealed response already exists"],
                                    "decomposition": []})
            return [("wait_response",)] if ok else None

        previous = None
        with _LOCK, redirect_stdout(StringIO()):
            previous = main.current_domain
            try:
                domain = g.Domain(_DOMAIN)
                g.declare_actions(emit_task, wait_response)
                g.declare_task_methods("archive_note", file_by_B, return_then_file_by_A,
                                       wait_for_response)
                with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking",
                                      verbose=0, structured_logging=False) as planner:
                    search = planner.find_plan(state, [("archive_note",)], timeout_ms=1000, trace=True)
            finally:
                main.current_domain = previous
        planner_trace = ([{"depth": e.depth, "task": repr(e.item), "status": e.status,
                           "detail": e.detail} for e in search.trace.events]
                         if search.trace is not None else [])
        if not search.success:
            reqs = []
            outstanding = _preserved_obligations(s)
            outstanding.extend(_temporary_method_wait(method_attempts))
            active = [row for row in outstanding if row.get("kind") == "actor_story_task"
                      and row.get("status") in {"ACCEPTED", "IN_PROGRESS"}]
            if active:
                outstanding.append({"kind": "WAITING_FOR_ACTIVE_NATIVE_TASK",
                                    "request_ids": [row["request_id"] for row in active],
                                    "reason": "existing actor task retains priority; planner emitted no replacement"})
            elif _temporary_method_wait(method_attempts):
                pass
            else:
                outstanding.append({"kind": "GTPYHOP_SEARCH_NO_PLAN",
                                    "reason": "no legal method decomposition found in sealed state"})
        else:
            simulated = deepcopy(state)
            for step in search.plan:
                if step and step[0] == "emit_task":
                    emit_task(simulated, *step[1:])
                elif step and step[0] == "wait_response":
                    wait_response(simulated, *step[1:])
            reqs = deepcopy(simulated.proposals)
            outstanding = deepcopy(simulated.outstanding)
        attempts = deepcopy(method_attempts)
        decomposition = deepcopy(reqs)
        candidates = [{"method_id": row["method_id"], "feasible": row["feasible"],
                       "preconditions": row["preconditions"],
                       "causal_support": row.get("causal_support"),
                       "decomposition": row.get("decomposition", [])} for row in attempts]
        rejected = [row for row in candidates if not row["feasible"]]
        status = "TASKS_PROPOSED" if reqs else (
            "WAITING_OR_BLOCKED" if s["response"] is not None else "WAITING_FOR_RESPONSE")
        extra_trace = planner_trace

    # Guard all proposed work with the fixed immutable scenario grant.
    for task in reqs:
        if (task["actor_alias"] not in request.task_control_grant["actor_aliases"]
                or task["task_kind"] not in request.task_control_grant["task_kinds"]
                or task["grant_id"] != request.task_control_grant["grant_id"]):
            raise ValueError("planner proposed a task outside the fixed scenario grant")
    typedir = _typedir_monitor(request, s, required_story_events)
    fb = {"new_committed_event_ids": sorted(e["event_id"] for e in s["typed_trace"]["events"]
                                               if isinstance(e, Mapping) and e.get("provenance") == "committed_ledger"),
          "sealed_minute": s["sealed_minute"], "request_version": request.version}
    return {"schema": SCHEMA, "status": status, "strategy": strategy,
            "controller_mode": mode, "sealed_minute": s["sealed_minute"],
            "required_story_events": deepcopy(required_story_events),
            "target_version": request.version, "selected_method":
                (reqs[0]["source_method_id"] if reqs else None),
            "method_plans": candidates, "rejected_methods": rejected,
            "attempted_methods": attempts,
            "alternative_guard_diagnostics": alternative_guard_diagnostics,
            "decomposition": decomposition, "task_requests": reqs,
            "outstanding_obligations": outstanding,
            "guards": {"grant_id": request.task_control_grant["grant_id"],
                       "absolute_deadline_minute": request.objective["by_minute"], "response_event_id":
                           s["response"]["event_id"] if s["response"] else None},
            "feedback_changes": fb, "typedir_verdicts": typedir,
            "gtpyhop_search_trace": extra_trace if strategy == "gtpyhop" else [],
            "task_requests_are_proposals": mode in {"result_only", "process"},
            "task_request_semantics": {"zero": "NO_CONTROL",
                                       "result_only": "PLANNER_PROPOSAL_REQUIRES_ACTOR_ACCEPTANCE",
                                       "process": "PLANNER_PROPOSAL_WITH_AUTHORED_METHOD_SCOPE",
                                       "direct": "AUTHORED_TASK_ASSIGNMENT_SUBJECT_TO_NATIVE_LEGALITY",
                                       "locked_fragment": "EXACT_AUTHORED_CORE_ABORT_ON_GUARD_MISS"}[mode],
            "accepted_task_request_ids": [],
            "native_execution_occurred": False,
            "world_effects_applied": False}


__all__ = ["plan_story_process", "SCHEMA"]


_STATION_METHODS = ("inspect_then_repair", "repair_then_inspect")
_STATION_EVENT_FILTERS = {
    "station_supply_inspected": {"actor": "A", "item": "courier_supply",
                                  "tool": "station_tool"},
    "station_passage_repaired": {"actor": "B", "tool": "station_tool",
                                  "exit": "pickup_to_side_south"},
    "station_supply_stored": {"actor": "A", "item": "courier_supply",
                               "storage": "station_storage"},
}


def _station_constraint_compatibility(constraints):
    """Fail closed when a hard authored event cannot be witnessed by this plan."""
    reasons = []
    for row in constraints:
        source = row.get("source_constraint", {})
        if source.get("kind") == "event_by_deadline":
            clauses = [(source.get("event"), source.get("filters", {}))]
        elif source.get("kind") == "event_order":
            clauses = [(side.get("event"), side.get("filters", {}))
                       for side in (source.get("before", {}), source.get("after", {}))]
        else:
            reasons.append(f"{row.get('constraint_id')}:unsupported_constraint_kind")
            continue
        for event, filters in clauses:
            expected = _STATION_EVENT_FILTERS.get(event)
            if expected is None:
                reasons.append(f"{row.get('constraint_id')}:no_station_method_witness_for_{event}")
                continue
            if not isinstance(filters, Mapping):
                reasons.append(f"{row.get('constraint_id')}:invalid_event_filters")
                continue
            if any(key not in expected or expected[key] != value
                   for key, value in filters.items()):
                reasons.append(f"{row.get('constraint_id')}:filters_not_supported_by_registered_task")
    return reasons


def _station_order_constraints(constraints):
    orders = []
    windows = {}
    allowed = set(_STATION_METHODS)
    for row in constraints:
        if not isinstance(row, Mapping):
            raise ValueError("station constraints must be compiled AuthorProjection rows")
        source = row.get("source_constraint", {})
        control = row.get("control", {})
        methods = control.get("allowed_methods", list(_STATION_METHODS))
        if not isinstance(methods, list) or not methods:
            raise ValueError("station work constraints must expose registered allowed_methods")
        allowed.intersection_update(methods)
        if source.get("kind") == "event_order":
            before = source.get("before", {}).get("event")
            after = source.get("after", {}).get("event")
            if (before, after) == ("station_supply_inspected", "station_passage_repaired"):
                orders.append("inspect_then_repair")
            elif (before, after) == ("station_passage_repaired", "station_supply_inspected"):
                orders.append("repair_then_inspect")
            for event in (before, after):
                old = windows.get(event, {"start": 0, "deadline": int(source["deadline"])})
                windows[event] = {"start": max(old["start"], int(source["start"])),
                                  "deadline": min(old["deadline"], int(source["deadline"]))}
        elif source.get("kind") == "event_by_deadline":
            event = source.get("event")
            old = windows.get(event, {"start": 0, "deadline": int(source["deadline"])})
            windows[event] = {"start": max(old["start"], int(source["start"])),
                              "deadline": min(old["deadline"], int(source["deadline"]))}
    if orders and any(order != orders[0] for order in orders):
        allowed.clear()
    if orders:
        allowed.intersection_update({orders[0]})
    return allowed, windows, orders


def _station_task_request(sealed, alias, kind, method_id, *, duration, deadline,
                          planned_start_minute, earliest_terminal_minute=0,
                          item_id=None, target_id=None):
    content = sealed["station_content"]
    projection_id = sealed.get("projection_id")
    offer_id = f"{sealed.get('station_id', 'station')}:{sealed['sealed_minute']}:{method_id}:{alias}:{kind}"
    mode = next((row.get("control", {}).get("mode") for row in sealed["constraints"]
                 if row.get("control", {}).get("mode")), "process")
    # A locked binding restricts only its literal sequence rows. Ordinary
    # method prerequisites remain planner proposals even when they cite that
    # binding as a required source constraint; the locked-core loop below marks
    # exact sequence matches explicitly.
    control_source = "AUTHORED" if mode == "direct" else "PLANNER"
    task = {"offer_id": offer_id, "request_id": offer_id, "source": "AUTHOR",
            "control_source": control_source,
            "source_method_id": method_id, "actor_alias": alias, "task_kind": kind,
            "goal_id": f"{method_id}:{kind}", "item_id": item_id,
            "tool_id": content["tool_id"], "target_id": target_id,
            "target_room_id": content["workbench_room_id"],
            "storage_destination_id": content["storage_id"],
            "storage_room_id": content["storage_room_id"],
            "duration_minutes": duration, "deadline_minute": deadline,
            "earliest_terminal_minute": earliest_terminal_minute,
            "planned_start_minute": planned_start_minute,
            "estimated_finish_minute": planned_start_minute + duration,
            "item_alias": "courier_supply" if item_id is not None else None,
            "tool_alias": "station_tool",
            "target_alias": ("pickup_to_side_south" if kind == "repair_passage"
                             else "courier_supply" if kind == "inspect_supply" else None),
            "destination_alias": "station_storage" if kind in {"inspect_supply", "store_item"} else None,
            "commitment_id": f"{offer_id}:commitment",
            "grant_id": sealed.get("grant_id"), "projection_id": projection_id,
            "constraint_id": sealed.get("constraint_id"),
            "required_constraint_ids": []}
    # Remove fields which are not meaningful to this task; actor/native contracts
    # remain exact and method provenance stays attached to every proposal.
    if kind == "repair_passage":
        task.pop("item_id")
        task.pop("item_alias")
        task.pop("storage_destination_id")
        task.pop("storage_room_id")
    elif kind == "store_item":
        task.pop("target_id")
        task.pop("target_alias")
        task.pop("target_room_id")
        task.pop("tool_id")
        task.pop("tool_alias")
        task.pop("duration_minutes")
    return task


def _station_task_minutes(sealed, alias, task, *, predicted_inspection=False,
                          conditional_tool_release=False):
    """Estimate primitive travel/setup from the same actor-local P3 HTN."""
    local_view = sealed["actors"][alias].get("local_view")
    if not isinstance(local_view, Mapping):
        return None, "actor_local_view_unavailable"
    from tools.native_platform_v0.p3.planning import thaw
    local_view = thaw(local_view)
    if conditional_tool_release and task["task_kind"] in {"inspect_supply", "repair_passage"}:
        # Pure forecast only: a separately verified lease due time permits
        # route-length estimation after release; it does not mutate the sealed
        # observation or assert that the tool is already free.
        for tool in local_view.get("observation", {}).get("station_tools", ()):
            if str(tool.get("id")) == str(task.get("tool_id")):
                tool["lease_status"] = "FREE"
    if task["task_kind"] == "store_item" and predicted_inspection:
        observation = local_view.setdefault("observation", {})
        workbench_room_id = sealed["station_content"]["workbench_room_id"]
        supplies = list(observation.get("station_supplies", ()))
        found = False
        for row in supplies:
            if str(row.get("id")) == str(task["item_id"]):
                row["inspection_status"] = "APPROVED"
                row["visible"] = True
                row["room_id"] = workbench_room_id
                found = True
        if not found:
            supplies.append({"id": task["item_id"], "visible": True,
                             "room_id": workbench_room_id,
                             "inspection_status": "APPROVED"})
        observation["station_supplies"] = supplies
        visible = [row for row in observation.get("visible_items", ())
                   if str(row.get("id")) != str(task["item_id"])]
        visible.append({"id": task["item_id"], "room_id": workbench_room_id})
        observation["visible_items"] = visible
        # The successful prior inspection is a conditional effect of this
        # decomposition, not a claim about the current sealed observation.
        observation["room_id"] = workbench_room_id
    from tools.native_platform_v0.p3.planning import plan_actor_task
    result = plan_actor_task(local_view, task)
    if result.get("status") != "SOLVED":
        return None, result.get("reason", result.get("status", "actor_task_plan_unavailable"))
    return len(result.get("plan", ())), (
        "shared_p3_actor_htn_after_verified_lease_due" if conditional_tool_release
        else "shared_p3_actor_htn")


def _native_self_binding(sealed, alias, kind, *, tool_id, target_id):
    """Find the exact actor-local native binding; never invent a SELF task."""
    actor = sealed["actors"].get(alias, {})
    view = actor.get("local_view", {})
    observation = view.get("observation", {}) if isinstance(view, Mapping) else {}
    binding = next((row for row in observation.get("station_task_bindings", ())
                    if isinstance(row, Mapping) and row.get("task_kind") == kind
                    and str(row.get("tool_id")) == str(tool_id)
                    and str(row.get("target_id")) == str(target_id)), None)
    active = next((row for row in actor.get("commitments", ())
                   if isinstance(row, Mapping) and row.get("source") == "SELF"
                   and row.get("task_kind") == kind
                   and str(row.get("tool_id")) == str(tool_id)
                   and str(row.get("target_id")) == str(target_id)
                   and row.get("status") in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}), None)
    if active:
        return {"status": "EXISTING_NATIVE_SELF_COMMITMENT",
                "offer_id": active.get("source_offer_id", active.get("commitment_id")),
                "commitment_id": active.get("commitment_id"),
                "receipt_ids": list(active.get("receipt_ids", []))}
    if binding:
        actor_id = actor.get("actor_id", view.get("actor_id"))
        if type(actor_id) is int:
            return {"status": "NATIVE_SELF_OFFER_CANDIDATE_NOT_ACCEPTED",
                    "offer_id": f"self:{actor_id}:{kind}:{target_id}",
                    "binding": deepcopy(dict(binding))}
    return None


def _preserved_station_obligations(sealed):
    obligations = []
    for alias, actor in sealed["actors"].items():
        pending = actor.get("pending_action")
        if isinstance(pending, Mapping) and pending.get("status") in {"planned", "executing"}:
            obligations.append({"kind": "native_actor_pending", "actor_alias": alias,
                                "status": pending.get("status"),
                                "task_kind": pending.get("task_kind"),
                                "commitment_id": pending.get("commitment_id"),
                                "due_minute": pending.get("due_minute")})
        for row in actor.get("commitments", ()):
            if isinstance(row, Mapping) and row.get("status") in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}:
                obligations.append({"kind": "native_actor_commitment", "actor_alias": alias,
                                    "status": row.get("status"),
                                    "task_kind": row.get("task_kind"),
                                    "commitment_id": row.get("commitment_id"),
                                    "due_minute": row.get("due_minute"),
                                    "receipt_ids": list(row.get("receipt_ids", []))})
    lease = sealed.get("active_tool_lease")
    if isinstance(lease, Mapping):
        obligations.append({"kind": "shared_tool_lease", "status": lease.get("status"),
                            "commitment_id": lease.get("commitment_id"),
                            "due_minute": lease.get("due_minute")})
    return obligations


def _station_candidate(sealed, method_id, allowed, windows):
    from tools.native_platform_v0.p5.ongoing_station.work import TASK_DURATIONS

    now, horizon = sealed["sealed_minute"], sealed["horizon"]
    content = sealed["station_content"]
    reasons = []
    reasons.extend(_station_constraint_compatibility(sealed["constraints"]))
    if method_id not in allowed:
        reasons.append("method_not_in_current_authorized_candidate_set")
    actors = sealed["actors"]
    actor_available = {"A": now, "B": now}
    inspection_window = windows.get("station_supply_inspected", {"start": 0, "deadline": horizon})
    repair_window = windows.get("station_passage_repaired", {"start": 0, "deadline": horizon})
    storage_window = windows.get("station_supply_stored", {"start": 0, "deadline": horizon})
    first, second = (("inspect_supply", "repair_passage") if method_id == "inspect_then_repair"
                     else ("repair_passage", "inspect_supply"))
    duration_by_kind = TASK_DURATIONS
    settled_at = {}
    settled_commitments = {}
    event_match = {
        "inspect_supply": ("p5_station_supply_inspected", {"actor": "A",
            "item": content["supply_id"], "tool": content["tool_id"]}),
        "repair_passage": ("p5_station_passage_repaired", {"actor": "B",
            "tool": content["tool_id"], "exit": content["repair_exit_id"]}),
        "store_item": ("p5_station_supply_stored", {"actor": "A",
            "item": content["supply_id"], "storage": content["storage_id"]}),
    }
    for event in sealed["typed_trace"]["events"]:
        if not isinstance(event, Mapping) or event.get("provenance") != "committed_ledger":
            continue
        args = event.get("args", {})
        for kind, (event_type, expected) in event_match.items():
            if (event.get("event_type") == event_type and isinstance(args, Mapping)
                    and event.get("native_receipt_id") and event.get("native_commitment_id")
                    and all(str(_event_arg_id(event, name)) == str(value)
                            for name, value in expected.items())):
                if event.get("native_task_kind") != kind:
                    continue
                minute = event.get("time")
                if type(minute) is int:
                    settled_at[kind] = min(minute, settled_at.get(kind, minute))
                    settled_commitments.setdefault(kind, set()).add(
                        str(event.get("native_commitment_id")))
    completed = set(settled_at)
    actor_for_kind = {"inspect_supply": "A", "repair_passage": "B", "store_item": "A"}
    remaining_kinds = {"inspect_supply", "repair_passage", "store_item"} - completed
    relevant_aliases = {actor_for_kind[kind] for kind in remaining_kinds}
    active_kinds = set()
    active_finish_by_kind = {}
    conditional_release_forecasts = []
    lease = sealed.get("active_tool_lease")
    for alias in sorted(relevant_aliases):
        row = actors[alias]
        pending = row.get("pending_action")
        if isinstance(pending, Mapping) and pending.get("status") in {"planned", "executing"}:
            due = pending.get("due_minute")
            if type(due) is int:
                actor_available[alias] = max(actor_available[alias], due)
            else:
                reasons.append(f"{alias}_native_pending_release_time_unknown")
        active = [item for item in row.get("commitments", ())
                  if isinstance(item, Mapping) and item.get("status") in {"ACCEPTED", "IN_PROGRESS"}]
        for commitment in active:
            kind = commitment.get("task_kind")
            lease_matches = (
                isinstance(lease, Mapping)
                and commitment.get("commitment_id") is not None
                and str(commitment.get("commitment_id")) == str(lease.get("commitment_id"))
                and lease.get("status") in {"BUSY", "IN_PROGRESS"}
                and kind in {"inspect_supply", "repair_passage"}
                and lease.get("task_kind") == kind
                and lease.get("actor_alias") == alias
                and str(lease.get("tool_id")) == str(content["tool_id"])
                and str(lease.get("target_id")) == str(
                    content["supply_id"] if kind == "inspect_supply" else content["repair_exit_id"])
            )
            if lease_matches:
                due = lease.get("due_minute")
                if type(due) is int and due >= now:
                    actor_available[alias] = max(actor_available[alias], due)
                    active_kinds.add(kind)
                    active_finish_by_kind[kind] = due
                    continue
                reasons.append("matching_native_work_lease_release_time_invalid")
                continue
            due = commitment.get("due_minute", commitment.get("expected_finish_minute"))
            if type(due) is int:
                actor_available[alias] = max(actor_available[alias], due)
            elif (commitment.get("remaining_work_minutes") is not None
                  and commitment.get("release_time_basis") == "conditional_no_future_failure_estimate"):
                remaining = commitment["remaining_work_minutes"]
                if type(remaining) is not int or remaining < 0:
                    reasons.append(f"{alias}_active_commitment_release_estimate_invalid")
                    continue
                actor_available[alias] = max(actor_available[alias], now + remaining)
                conditional_release_forecasts.append({
                    "actor_alias": alias,
                    "commitment_id": commitment.get("commitment_id"),
                    "remaining_work_minutes": remaining,
                    "basis": "source_attached_local_prefix_estimate",
                    "assumption": "no further primitive failure; conditional forecast, not a release upper bound"})
            else:
                reasons.append(f"{alias}_active_commitment_release_time_unknown")
    tool = sealed.get("station_tool")
    unfinished_tool_work = not {"inspect_supply", "repair_passage"} <= completed
    if unfinished_tool_work:
        if (not isinstance(tool, Mapping) or tool.get("id") != content["tool_id"]
                or tool.get("room_id") != content["workbench_room_id"]):
            reasons.append("registered_tool_location_or_identity_mismatch")
        elif tool.get("holder_alias") is not None:
            reasons.append("registered_tool_is_not_at_workbench_for_native_work")
        elif tool.get("lease_status") not in {"FREE", "BUSY"}:
            reasons.append("registered_tool_has_unknown_native_lease_status")
    lease = sealed.get("active_tool_lease")
    temporary_wait_until = None
    if unfinished_tool_work and lease is not None:
        due = lease.get("due_minute") if isinstance(lease, Mapping) else None
        if type(due) is not int:
            reasons.append("shared_tool_lease_release_time_unknown")
        elif due > now:
            temporary_wait_until = due
    elif unfinished_tool_work and isinstance(tool, Mapping) and tool.get("lease_status") == "BUSY":
        reasons.append("busy_tool_has_no_matching_native_lease_receipt")
    if ("inspect_supply" in completed and "repair_passage" in completed
            and ((settled_at["inspect_supply"] < settled_at["repair_passage"])
                 != (method_id == "inspect_then_repair"))):
        reasons.append("settled_work_order_conflicts_with_candidate_order")
    if (("inspect_supply" in active_kinds and method_id != "inspect_then_repair")
            or ("repair_passage" in active_kinds and method_id != "repair_then_inspect")):
        reasons.append("active_native_work_conflicts_with_candidate_order")
    if "store_item" in completed and "inspect_supply" not in completed:
        reasons.append("stored_supply_lacks_matching_inspection_receipt")
    first_actor = "A" if first == "inspect_supply" else "B"
    second_actor = "A" if second == "inspect_supply" else "B"
    first_start = max(now, actor_available[first_actor])
    if unfinished_tool_work and lease is not None and type(lease.get("due_minute")) is int:
        first_start = max(first_start, lease["due_minute"])
    if temporary_wait_until is not None:
        first_start = max(first_start, temporary_wait_until)
    first_event = "station_supply_inspected" if first == "inspect_supply" else "station_passage_repaired"
    first_window = inspection_window if first == "inspect_supply" else repair_window
    first_start = max(first_start, first_window["start"])
    first_finish = (settled_at[first] if first in completed else
                    active_finish_by_kind.get(first, first_start + duration_by_kind[first]))
    second_event = "station_supply_inspected" if second == "inspect_supply" else "station_passage_repaired"
    second_window = inspection_window if second == "inspect_supply" else repair_window
    second_start = max(first_finish, second_window["start"], actor_available[second_actor])
    second_finish = (settled_at[second] if second in completed else
                     active_finish_by_kind.get(second, second_start + duration_by_kind[second]))
    finish_by_kind = {first: first_finish, second: second_finish}
    if finish_by_kind["inspect_supply"] > inspection_window["deadline"]:
        reasons.append("inspection_deadline_not_feasible_under_serial_tool_capacity")
    if finish_by_kind["repair_passage"] > repair_window["deadline"]:
        reasons.append("repair_deadline_not_feasible_under_serial_tool_capacity")
    # Storage follows successful inspection and does not consume the shared tool.
    storage_start = max(second_finish, storage_window["start"])
    storage_finish = storage_start + (0 if "store_item" in completed else 1)
    if storage_finish > storage_window["deadline"]:
        reasons.append("storage_deadline_not_feasible_after_inspection_and_tool_schedule")
    if storage_finish > horizon:
        reasons.append("profile_horizon_exceeded")

    item_id, exit_id = content["supply_id"], content["repair_exit_id"]
    inspection = _station_task_request(
        sealed, "A", "inspect_supply", method_id, duration=duration_by_kind["inspect_supply"],
        deadline=inspection_window["deadline"],
        earliest_terminal_minute=inspection_window["start"],
        planned_start_minute=first_start if first == "inspect_supply" else second_start,
        item_id=item_id, target_id=item_id)
    repair = _station_task_request(
        sealed, "B", "repair_passage", method_id, duration=duration_by_kind["repair_passage"],
        deadline=repair_window["deadline"],
        earliest_terminal_minute=repair_window["start"],
        planned_start_minute=first_start if first == "repair_passage" else second_start,
        target_id=exit_id)
    store = _station_task_request(
        sealed, "A", "store_item", method_id, duration=1,
        deadline=storage_window["deadline"], earliest_terminal_minute=storage_window["start"],
        planned_start_minute=storage_start, item_id=item_id)
    tasks_by_kind = {"inspect_supply": inspection, "repair_passage": repair, "store_item": store}
    route_estimates = {}
    for kind, task in tasks_by_kind.items():
        if kind in completed:
            route_estimates[kind] = {"minutes": 0, "source": "settled_native_receipt"}
            continue
        if kind in active_kinds:
            route_estimates[kind] = {"minutes": 0, "source": "exact_active_native_lease"}
            continue
        minutes, source = _station_task_minutes(sealed, task["actor_alias"], task,
                                                predicted_inspection=(kind == "store_item"
                                                                      and "inspect_supply" not in completed),
                                                conditional_tool_release=(temporary_wait_until is not None))
        route_estimates[kind] = {"minutes": minutes, "source": source}
        if minutes is None:
            reasons.append(f"{kind}_route_cost_unknown_from_actor_local_htn")
    start_by_kind = {}
    dispatch_by_kind = {}
    if all(row["minutes"] is not None for row in route_estimates.values()):
        # A sealed planner decision is consumed by actor callbacks on the next
        # minute. Each P3 primitive then occupies one callback; the final
        # primitive's effect therefore occurs at dispatch + plan_length - 1.
        first_dispatch = max(now + 1, actor_available[first_actor])
        first_start = (settled_at[first] if first in completed else
                       max(first_dispatch + max(0, route_estimates[first]["minutes"] - 1),
                           lease.get("due_minute", now) if isinstance(lease, Mapping) else now,
                           first_window["start"]))
        first_finish = (settled_at[first] if first in completed else
                        active_finish_by_kind.get(first, first_start + duration_by_kind[first]))
        # The bounded adapter publishes one proposal at a time. Preserve this
        # conservative sequence in the forecast; it is not a shared-tool rule
        # for storage and does not claim parallel scheduling.
        second_dispatch = max(first_finish + 1, actor_available[second_actor], now + 1)
        second_start = (settled_at[second] if second in completed else
                        max(second_dispatch + max(0, route_estimates[second]["minutes"] - 1),
                            second_window["start"], first_finish))
        second_finish = (settled_at[second] if second in completed else
                         active_finish_by_kind.get(second, second_start + duration_by_kind[second]))
        start_by_kind = {first: first_start, second: second_start}
        dispatch_by_kind = {first: first_dispatch, second: second_dispatch}
        finish_by_kind = {first: first_finish, second: second_finish}
        storage_dispatch = max(second_finish + 1, actor_available["A"], now + 1)
        storage_start = (settled_at["store_item"] if "store_item" in completed else
                         max(storage_dispatch + max(0, route_estimates["store_item"]["minutes"] - 1),
                             storage_window["start"]))
        storage_finish = (settled_at["store_item"] if "store_item" in completed
                          else storage_start)
        dispatch_by_kind["store_item"] = storage_dispatch
        if finish_by_kind["inspect_supply"] > inspection_window["deadline"]:
            reasons.append("inspection_deadline_exceeded_after_actor_local_route")
        if finish_by_kind["repair_passage"] > repair_window["deadline"]:
            reasons.append("repair_deadline_exceeded_after_actor_local_route")
        if storage_finish > storage_window["deadline"]:
            reasons.append("storage_deadline_exceeded_after_actor_local_route")
    else:
        storage_start = None
        storage_finish = None
    requests = ([inspection, repair, store] if method_id == "inspect_then_repair"
                else [repair, inspection, store])
    ordered_kinds = (["inspect_supply", "repair_passage"] if method_id == "inspect_then_repair"
                     else ["repair_passage", "inspect_supply"])
    tasks_by_kind = {"inspect_supply": inspection, "repair_passage": repair,
                     "store_item": store}
    requests = [tasks_by_kind[kind] for kind in ordered_kinds + ["store_item"]
                if kind not in completed and kind not in active_kinds]
    event_for_kind = {"inspect_supply": "station_supply_inspected",
                      "repair_passage": "station_passage_repaired",
                      "store_item": "station_supply_stored"}
    for task in requests:
        task_event = event_for_kind[task["task_kind"]]
        for constraint in sealed["constraints"]:
            source = constraint.get("source_constraint", {})
            relevant = (source.get("kind") == "event_by_deadline"
                        and source.get("event") == task_event)
            if source.get("kind") == "event_order":
                relevant = any(
                    side.get("event") == task_event
                    for side in (source.get("before", {}), source.get("after", {})))
            if relevant:
                task["required_constraint_ids"].append(constraint["constraint_id"])
        task["required_constraint_ids"] = sorted(set(task["required_constraint_ids"]))
        # A hard storage goal causally requires inspection, so that exact
        # author constraint may authorize inspection as a prerequisite. Repair
        # remains a native SELF goal unless a hard bundle event/order actually
        # requires the repair occurrence.
        if task["task_kind"] == "inspect_supply" and not task["required_constraint_ids"]:
            for constraint in sealed["constraints"]:
                source = constraint.get("source_constraint", {})
                if ((source.get("kind") == "event_by_deadline"
                     and source.get("event") == "station_supply_stored")
                        or (source.get("kind") == "event_order"
                            and any(side.get("event") == "station_supply_stored"
                                    for side in (source.get("before", {}), source.get("after", {}))))):
                    task["required_constraint_ids"].append(constraint["constraint_id"])
        task["required_constraint_ids"] = sorted(set(task["required_constraint_ids"]))
        primary_id = task["required_constraint_ids"]
        if primary_id:
            task["constraint_id"] = primary_id[0]
            task["grant_id"] = sealed.get("grant_ids", {}).get(primary_id[0])
            if task["grant_id"] is None:
                task["grant_id"] = (f"{sealed.get('station_id')}:{primary_id[0]}:fixed-native-grant"
                                    if sealed.get("station_id") else None)
        if task["task_kind"] in start_by_kind:
            # `planned_start_minute` is when the actor may begin the task's
            # first native intent (usually a route step), not when it reaches
            # the workbench or completes the task. Keep those forecast points
            # separate so the controller never waits until the terminal action
            # before dispatching the route.
            task_alias = task["actor_alias"]
            task["planned_start_minute"] = dispatch_by_kind.get(
                task["task_kind"], max(now + 1, actor_available[task_alias]))
            task["estimated_work_start_minute"] = start_by_kind[task["task_kind"]]
            if "duration_minutes" in task:
                task["estimated_finish_minute"] = (task["estimated_work_start_minute"]
                                                   + task["duration_minutes"])
        elif task["task_kind"] == "store_item" and storage_start is not None:
            task["planned_start_minute"] = dispatch_by_kind.get(
                "store_item", max(now + 1, actor_available[task["actor_alias"]]))
            task["estimated_work_start_minute"] = storage_start
            task["estimated_finish_minute"] = storage_finish

    # Repair is an independent native SELF objective unless the bundle has a
    # direct event/dependency requirement for it. A candidate method may use
    # that registered SELF binding as conditional support, but never relabel
    # it as an AUTHOR grant or infer actor acceptance.
    derived_support = []
    for task in requests:
        if task["task_kind"] != "repair_passage" or task["required_constraint_ids"]:
            task["source"] = "AUTHOR"
            continue
        support = _native_self_binding(sealed, "B", "repair_passage",
                                       tool_id=content["tool_id"],
                                       target_id=content["repair_exit_id"])
        if support is None:
            reasons.append("independent_repair_self_goal_not_locally_bound")
            continue
        task.update({"source": "NATIVE_SELF_GOAL", "control_source": "SELF_SUPPORT",
                     "goal_id": f"native-self:B:repair_passage:{content['repair_exit_id']}",
                     "grant_id": None, "constraint_id": None, "required_constraint_ids": [],
                     "support_role": "DERIVED_METHOD_SUPPORT",
                     "self_support_status": support["status"],
                     "self_offer_id": support.get("offer_id"),
                     "existing_commitment_id": support.get("commitment_id"),
                     "support_receipt_ids": support.get("receipt_ids", [])})
        derived_support.append(task)
    author_requests = [row for row in requests if row.get("source") == "AUTHOR"]
    locked_constraints = [row for row in sealed["constraints"]
                          if row.get("control", {}).get("mode") == "locked_fragment"]
    for constraint in locked_constraints:
        fragment = constraint.get("locked_fragment") or {}
        guard = fragment.get("entry_guard", {})
        requires_workbench_tool = guard.get("tool_at_room") == "pickup"
        if requires_workbench_tool and (
                sealed["station_tool"].get("room_id") != content["workbench_room_id"]
                or sealed["station_tool"].get("holder_alias") is not None
                or sealed["station_tool"].get("lease_status") != "FREE"):
                reasons.append("locked_fragment_entry_guard_failed")
        if (guard.get("supply_alias") == "courier_supply"
                and guard.get("storage_alias") == "station_storage"
                and (str(content["supply_id"]) == "None"
                     or str(content["storage_id"]) == "None")):
            reasons.append("locked_fragment_exact_storage_binding_unavailable")
        if (guard.get("inspection_receipt_required") is True
                and "inspect_supply" not in completed):
            reasons.append("locked_fragment_inspection_receipt_guard_failed")
        sequence = fragment.get("sequence", [])
        lock_rows = []
        for index, lock in enumerate(sequence):
            match = next((task for task in requests
                          if task["actor_alias"] == lock.get("actor_alias")
                          and task["task_kind"] == lock.get("task_kind")), None)
            if match is None:
                kind = lock.get("task_kind")
                actor_alias = lock.get("actor_alias")
                if kind in completed and actor_alias == actor_for_kind.get(kind):
                    native_ids = settled_commitments.get(kind, set())
                    witnessed = any(
                        str(row.get("commitment_id")) in native_ids
                        and row.get("control_source") == "LOCKED_FRAGMENT"
                        and row.get("locked_fragment_hash") == fragment.get("sequence_sha256")
                        and row.get("locked_sequence_index") == index
                        for row in actors[actor_alias].get("commitments", ())
                        if isinstance(row, Mapping))
                    if not witnessed:
                        reasons.append("LOCKED_CORE_EXECUTION_UNWITNESSED")
                    lock_rows.append({"actor_alias": actor_alias, "task_kind": kind,
                                      "already_settled": witnessed})
                    continue
                if kind in active_kinds and actor_alias == actor_for_kind.get(kind):
                    lock_rows.append({"actor_alias": actor_alias, "task_kind": kind,
                                      "in_progress": True})
                    continue
                reasons.append("locked_fragment_task_not_in_candidate_decomposition")
                continue
            aliases = {"tool_ref": ("tool_alias", "station_tool"),
                       "target_ref": ("target_alias", "pickup_to_side_south"),
                       "item_ref": ("item_alias", "courier_supply"),
                       "destination_ref": ("destination_alias", "station_storage")}
            if any(match.get(column) != value for field, (column, value) in aliases.items()
                   if field in lock):
                reasons.append("locked_fragment_reference_mismatch")
                continue
            match["locked_fragment_sha256"] = fragment["sequence_sha256"]
            match["locked_sequence_index"] = index
            match["control_source"] = "LOCKED_FRAGMENT"
            match["required_constraint_ids"] = sorted(set(
                match["required_constraint_ids"] + [constraint["constraint_id"]]))
            match["constraint_id"] = constraint["constraint_id"]
            match["grant_id"] = sealed.get("grant_ids", {}).get(constraint["constraint_id"])
            if match["grant_id"] is None and sealed.get("station_id"):
                match["grant_id"] = (f"{sealed['station_id']}:{constraint['constraint_id']}:fixed-native-grant")
            lock_rows.append(match)
        if len(lock_rows) != len(sequence):
            reasons.append("locked_fragment_core_incomplete")
        else:
            locked_task_keys = {(row["actor_alias"], row["task_kind"]) for row in lock_rows}
            # A lock covers only its literal core. Keep independently authorized
            # prerequisite/order tasks outside that core (e.g. repair→store).
            requests = ([row for row in requests
                         if (row["actor_alias"], row["task_kind"]) not in locked_task_keys]
                        + lock_rows)
    author_requests = [row for row in requests
                       if row.get("source") == "AUTHOR"
                       or row.get("control_source") == "LOCKED_FRAGMENT"]
    schedule = []
    for kind, start, finish in ((first, first_start, first_finish),
                                (second, second_start, second_finish),
                                ("store_item", storage_start, storage_finish)):
        task = tasks_by_kind[kind]
        dispatch_minute = dispatch_by_kind.get(
            kind, task.get("planned_start_minute", max(now + 1, actor_available[actor_for_kind[kind]])))
        work_start_minute = start_by_kind.get(kind, task.get("estimated_work_start_minute", start))
        finish_minute = (active_finish_by_kind[kind] if kind in active_finish_by_kind else
                         settled_at[kind] if kind in settled_at else
                         task.get("estimated_finish_minute", finish))
        schedule.append({"task_kind": kind,
                         "dispatch_minute": dispatch_minute,
                         "work_start_minute": work_start_minute,
                         "finish_minute": finish_minute})
    return {"method_id": method_id, "feasible": not reasons, "preconditions": reasons,
            "task_requests": author_requests, "derived_support_tasks": derived_support,
            "decomposition": requests, "schedule": schedule,
            "resource_capacity": {"tool_id": content["tool_id"], "capacity": 1,
                                  "serialized_task_kinds": ["inspect_supply", "repair_passage"],
                                  "storage_uses_tool": False},
    "proposal_sequence_policy": (
                "CONSERVATIVE_SERIAL_METHOD_PROPOSALS; storage follows the tool-work order "
                "in this bounded controller, not because storage consumes tool capacity"),
            "settled_work_receipt_minutes": deepcopy(settled_at),
            "route_estimates": route_estimates,
            "conditional_release_forecasts": conditional_release_forecasts,
            "temporary_wait_until_minute": temporary_wait_until,
            "satisfied": {"inspect_supply": "inspect_supply" in completed,
                          "repair_passage": "repair_passage" in completed,
                          "store_item": "store_item" in completed},
            "acceptance": "CONDITIONAL_UNTIL_ACTOR_ACCEPTS"}


def plan_station_work_order(sealed_state: Mapping[str, Any], *, strategy="gtpyhop"):
    """Compare the two registered station-work decompositions from one sealed snapshot.

    Both strategies share the exact methods, task costs, constraints, and world
    projection. GTPyhop invokes the two decomposition callbacks; event_driven is
    a deterministic strong rule baseline over their same feasibility records.
    Returned tasks are conditional proposals only; no actor acceptance or effect
    is inferred here.
    """
    if strategy not in {"gtpyhop", "event_driven"}:
        raise ValueError("strategy must be gtpyhop or event_driven")
    required = {"sealed_minute", "horizon", "station_content", "station_tool", "actors",
                "active_tool_lease", "constraints", "typed_trace"}
    if not isinstance(sealed_state, Mapping) or not required <= set(sealed_state):
        raise ValueError("station planner requires sealed minute, content, actors, lease, and constraints")
    s = deepcopy(dict(sealed_state))
    if (type(s["sealed_minute"]) is not int or type(s["horizon"]) is not int
            or not 0 <= s["sealed_minute"] <= s["horizon"]):
        raise ValueError("station planner clock must be a valid absolute sealed minute")
    content = s["station_content"]
    content_keys = {"tool_id", "storage_id", "supply_id", "repair_exit_id",
                    "workbench_room_id", "storage_room_id"}
    if (not isinstance(content, Mapping) or not content_keys <= set(content)
            or any(type(content[key]) is not int or content[key] <= 0 for key in content_keys)):
        raise ValueError("station_content must bind exact positive native object IDs")
    if not isinstance(s["actors"], Mapping) or set(s["actors"]) != {"A", "B"}:
        raise ValueError("actor-local snapshots for A and B are required")
    if (not isinstance(s["station_tool"], Mapping)
            or set(s["station_tool"]) - {"id", "room_id", "holder_alias", "lease_status", "due_minute"}
            or not {"id", "room_id", "holder_alias", "lease_status"} <= set(s["station_tool"])
            or not isinstance(s["typed_trace"], Mapping)
            or not isinstance(s["typed_trace"].get("events"), list)):
        raise ValueError("exact registered tool projection and committed TypedIR event rows are required")
    if not isinstance(s["constraints"], (list, tuple)):
        raise ValueError("constraints must be a compiled AuthorProjection sequence")
    allowed, windows, authored_orders = _station_order_constraints(s["constraints"])
    prefix_candidates = [_station_candidate(s, method, allowed, windows)
                         for method in _STATION_METHODS]
    if (any(row["feasible"] and all(row["satisfied"].values())
            for row in prefix_candidates)):
        return {"schema": "ongoing-station-work-decision-v1",
                "strategy": strategy,
                "sealed_minute": s["sealed_minute"],
                "selected_method": None,
                "status": "SATISFIED_PREFIX",
                "method_plans": prefix_candidates,
                "rejected_methods": [row for row in prefix_candidates if not row["feasible"]],
                "attempted_methods": [],
                "gtpyhop_search_succeeded": None,
                "gtpyhop_search_trace": [],
                "task_requests": [],
                "derived_support_tasks": [],
                "outstanding_obligations": _preserved_station_obligations(s),
                "authored_order_constraints": authored_orders,
                "native_execution_occurred": False,
                "world_effects_applied": False}
    attempted = []
    trace = []
    search_success = None
    if strategy == "gtpyhop":
        import gtpyhop as g
        import gtpyhop.main as main
        from tools.native_platform_v0.p3.planning import _LOCK
        state = g.State("ongoing-station-joint-work")
        state.sealed = s
        state.allowed, state.windows = allowed, windows
        state.proposals = []
        state.candidates = []
        state.selected_method = None

        def propose_station_task(world, task):
            # Each decomposition step is a registered task proposal primitive;
            # native actor acceptance and execution remain outside this search.
            if (task.get("actor_alias") not in {"A", "B"}
                    or task.get("task_kind") not in {"inspect_supply", "repair_passage", "store_item"}
                    or type(task.get("duration_minutes", 1)) is not int):
                return False
            world.proposals.append(deepcopy(task))
            world.selected_method = task["source_method_id"]
            return world

        def inspect_then_repair(world):
            candidate = _station_candidate(world.sealed, "inspect_then_repair",
                                           world.allowed, world.windows)
            world.candidates.append(candidate)
            attempted.append({"method_id": "inspect_then_repair", "feasible": candidate["feasible"],
                              "preconditions": candidate["preconditions"]})
            return ([*(('propose_station_task', task) for task in candidate["decomposition"]) ]
                    if candidate["feasible"] else None)

        def repair_then_inspect(world):
            candidate = _station_candidate(world.sealed, "repair_then_inspect",
                                           world.allowed, world.windows)
            world.candidates.append(candidate)
            attempted.append({"method_id": "repair_then_inspect", "feasible": candidate["feasible"],
                              "preconditions": candidate["preconditions"]})
            return ([*(('propose_station_task', task) for task in candidate["decomposition"]) ]
                    if candidate["feasible"] else None)

        with _LOCK, redirect_stdout(StringIO()):
            previous = main.current_domain
            try:
                domain = g.Domain("ongoing-station-joint-work-v1")
                g.declare_actions(propose_station_task)
                g.declare_task_methods("coordinate_station_work", inspect_then_repair,
                                       repair_then_inspect)
                with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking",
                                      verbose=0, structured_logging=False) as planner:
                    search = planner.find_plan(state, [("coordinate_station_work",)],
                                               timeout_ms=1000, trace=True)
            finally:
                main.current_domain = previous
        trace = ([{"depth": event.depth, "task": repr(event.item), "status": event.status,
                   "detail": event.detail} for event in search.trace.events]
                 if search.trace is not None else [])
        search_success = bool(search.success)
        selected_method = getattr(search, "state", None)
        # Planner result state is not relied on for evidence; replay the actual
        # primitive task sequence from its plan exactly as the existing story lane does.
        proposals = []
        selected_method_id = None
        if search.success:
            for step in search.plan:
                if step and step[0] == "propose_station_task":
                    task = deepcopy(step[1])
                    proposals.append(task)
                    selected_method_id = task["source_method_id"]
        selected = {"method_id": selected_method_id, "task_requests": proposals} if proposals else None
        candidates = prefix_candidates
    else:
        candidates = prefix_candidates
        attempted = [{"method_id": row["method_id"], "feasible": row["feasible"],
                      "preconditions": deepcopy(row["preconditions"])} for row in candidates]
        selected = next((row for row in candidates if row["feasible"]), None)
    by_id = {row["method_id"]: row for row in candidates}
    selected = by_id.get(selected["method_id"]) if selected else None
    outstanding = _preserved_station_obligations(s)
    outstanding.append({"kind": "ACTOR_ACCEPTANCE_PENDING", "method_id": selected["method_id"]}
                       if selected else {"kind": "NO_CURRENTLY_FEASIBLE_ORDER"})
    return {"schema": "ongoing-station-work-decision-v1",
            "strategy": strategy,
            "sealed_minute": s["sealed_minute"],
            "selected_method": selected["method_id"] if selected else None,
            "status": "CONDITIONAL_PLAN" if selected else "WAIT_OR_UNSATISFIED",
            "method_plans": candidates,
            "rejected_methods": [row for row in candidates if not row["feasible"]],
            "attempted_methods": attempted,
            "gtpyhop_search_succeeded": search_success,
            "gtpyhop_search_trace": trace if strategy == "gtpyhop" else [],
            "task_requests": deepcopy(selected["task_requests"]) if selected else [],
            "derived_support_tasks": deepcopy(selected["derived_support_tasks"]) if selected else [],
            "outstanding_obligations": outstanding,
            "authored_order_constraints": authored_orders,
            "native_execution_occurred": False,
            "world_effects_applied": False}


__all__ = ["plan_story_process", "plan_station_work_order", "SCHEMA"]
