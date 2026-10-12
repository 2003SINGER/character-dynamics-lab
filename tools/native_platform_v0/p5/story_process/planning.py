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
               "active_task", "task_status"}


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
        if (not isinstance(row, Mapping) or set(row) != {"id", "reachable_by", "estimated_minutes"}
                or type(row["id"]) is not int or row["id"] <= 0
                or not isinstance(row["reachable_by"], list)
                or any(a not in {"A", "B"} for a in row["reachable_by"])
                or type(row["estimated_minutes"]) is not int or row["estimated_minutes"] < 0):
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
                  rendezvous_destination_id: int | None = None) -> dict[str, Any]:
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
    if rendezvous_destination_id is not None:
        row["rendezvous_destination_id"] = rendezvous_destination_id
    return row


def _method_preconditions(method: str, request: StoryProcessRequest, s: Mapping[str, Any]) -> tuple[bool, list[str], list[dict[str, Any]]]:
    reasons: list[str] = []
    tasks: list[dict[str, Any]] = []
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
        if _task_rejected(s["actors"]["B"], "archive_note"):
            reasons.append("B_previously_rejected_this_local_task")
        if request.objective["note_id"] not in s["actors"]["B"]["locally_observed_item_ids"]:
            reasons.append("B_has_not_locally_observed_exact_note")
        tasks = [_task_request(request, s, "B", "archive_note", method)]
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
        if (_task_rejected(s["actors"]["B"], "handover_note")
                or _task_rejected(s["actors"]["A"], "archive_note")):
            reasons.append("an_actor_previously_rejected_a_required_local_task")
        if request.objective["note_id"] not in b["locally_observed_item_ids"]:
            reasons.append("B_has_not_locally_observed_exact_note_for_handover")
        tasks = [_task_request(request, s, "B", "handover_note", method),
                 _task_request(request, s, "A", "archive_note", method,
                               prerequisites=["committed_native_handover_receipt_for_exact_note_at_rendezvous",
                                              "A_locally_observes_exact_note", "native_actor_accepts_task"],
                               rendezvous_destination_id=s["destinations"]["handover"]["id"])]
    else:
        reasons.append("unknown_method")
    cost = sum(s["destinations"]["handover" if row["task_kind"] == "handover_note" else "archive"]["estimated_minutes"]
               for row in tasks)
    if s["sealed_minute"] + cost > request.objective["by_minute"]:
        reasons.append("absolute_deadline_time_infeasible")
    return not reasons, reasons, tasks


def _actor_busy(actor: Mapping[str, Any]) -> bool:
    active = actor.get("active_task")
    return bool(active and active.get("status") in {"ACCEPTED", "IN_PROGRESS"}) or actor.get("task_status") in {"ACCEPTED", "IN_PROGRESS"}


def _task_rejected(actor: Mapping[str, Any], task_kind: str) -> bool:
    active = actor.get("active_task")
    return bool(active and active.get("task_kind") == task_kind and active.get("status") == "REJECTED")


def _timing_budget(request: StoryProcessRequest, s: Mapping[str, Any], tasks: list[dict[str, Any]]) -> dict[str, int | bool]:
    cost = sum(s["destinations"]["handover" if row["task_kind"] == "handover_note" else "archive"]["estimated_minutes"]
               for row in tasks)
    finish = s["sealed_minute"] + cost
    return {"estimated_task_minutes": cost, "sealed_minute": s["sealed_minute"],
            "projected_finish_minute": finish,
            "absolute_deadline_minute": request.objective["by_minute"],
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


def _typedir_monitor(request: StoryProcessRequest, s: Mapping[str, Any]) -> list[dict[str, Any]]:
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
                   Window(0, request.objective["by_minute"]),
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


def _event_baseline(request: StoryProcessRequest, s: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic strong event dispatcher over exactly the same legal method set."""
    if s["response"] is None or request.control["mode"] == "zero":
        return [], [], [{"kind": "WAITING_FOR_NATIVE_RESPONSE" if s["response"] is None else "NO_TASK_AUTHORIZED"}]
    feasible = []
    rejected = []
    candidates = []
    for method in ("file_by_B", "return_then_file_by_A"):
        ok, guards, tasks = _method_preconditions(method, request, s)
        row = {"method_id": method, "feasible": ok, "preconditions": guards, "task_requests": tasks}
        row["resource_time"] = _timing_budget(request, s, tasks)
        candidates.append(row)
        (feasible if ok else rejected).append(row)
    # Same content, affordances, permissions, and cost; fixed event policy prefers B's filing.
    chosen = next((row for row in feasible if row["method_id"] == "file_by_B"), None)
    if chosen is None and feasible:
        chosen = feasible[0]
    return (list(chosen["task_requests"]) if chosen else []), candidates, rejected


def plan_story_process(request: StoryProcessRequest, sealed_state: Mapping[str, Any], *, strategy: str = "gtpyhop") -> dict[str, Any]:
    """Plan task requests from a sealed state; never applies world effects."""
    s = _validate_state(request, sealed_state)
    if strategy not in {"gtpyhop", "event_driven"}:
        raise ValueError("strategy must be gtpyhop or event_driven")
    # Report the same-state alternative guards independently of search.  This is
    # diagnostic evidence only: it must not preselect, order, or feed the planner.
    alternative_guard_diagnostics = []
    for method in ("file_by_B", "return_then_file_by_A"):
        feasible, guards, tasks = _method_preconditions(method, request, s)
        alternative_guard_diagnostics.append({
            "method_id": method,
            "feasible": feasible,
            "preconditions": guards,
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
        reqs, candidates, rejected = _event_baseline(request, s)
        attempts, decomposition = deepcopy(candidates), deepcopy(reqs)
        outstanding = _preserved_obligations(s)
        if not reqs:
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
            ok, guards, tasks = _method_preconditions("file_by_B", world.request, world.sealed)
            method_attempts.append({"method_id": "file_by_B", "feasible": ok,
                                    "preconditions": guards, "decomposition": deepcopy(tasks),
                                    "resource_time": _timing_budget(world.request, world.sealed, tasks)})
            return [("emit_task", tasks[0])] if ok else None

        def return_then_file_by_A(world):
            ok, guards, tasks = _method_preconditions("return_then_file_by_A", world.request, world.sealed)
            method_attempts.append({"method_id": "return_then_file_by_A", "feasible": ok,
                                    "preconditions": guards, "decomposition": deepcopy(tasks),
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
            active = [row for row in outstanding if row.get("kind") == "actor_story_task"
                      and row.get("status") in {"ACCEPTED", "IN_PROGRESS"}]
            if active:
                outstanding.append({"kind": "WAITING_FOR_ACTIVE_NATIVE_TASK",
                                    "request_ids": [row["request_id"] for row in active],
                                    "reason": "existing actor task retains priority; planner emitted no replacement"})
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
                       "decomposition": row.get("decomposition", [])} for row in attempts]
        rejected = [row for row in candidates if not row["feasible"]]
        status = "TASKS_PROPOSED" if reqs else ("WAITING_OR_BLOCKED" if s["response"] is not None else "WAITING_FOR_RESPONSE")
        extra_trace = planner_trace

    # Guard all proposed work with the fixed immutable scenario grant.
    for task in reqs:
        if (task["actor_alias"] not in request.task_control_grant["actor_aliases"]
                or task["task_kind"] not in request.task_control_grant["task_kinds"]
                or task["grant_id"] != request.task_control_grant["grant_id"]):
            raise ValueError("planner proposed a task outside the fixed scenario grant")
    typedir = _typedir_monitor(request, s)
    fb = {"new_committed_event_ids": sorted(e["event_id"] for e in s["typed_trace"]["events"]
                                               if isinstance(e, Mapping) and e.get("provenance") == "committed_ledger"),
          "sealed_minute": s["sealed_minute"], "request_version": request.version}
    return {"schema": SCHEMA, "status": status, "strategy": strategy,
            "controller_mode": mode, "sealed_minute": s["sealed_minute"],
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
