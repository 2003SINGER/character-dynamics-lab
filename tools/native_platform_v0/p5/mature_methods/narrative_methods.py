"""A small P5 high-level GTPyhop task domain.

This domain proposes control steps and native-event obligations. It never
simulates a delivery or a social response. P5's existing planning.plan is the
only route/opportunity selector.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from typing import Any, Mapping

from .method_adapters import MatureSnapshot


_MATURE_METHODS_DOMAIN = "p5-mature-methods-v1"


def _goal_descriptors(bundle) -> list[dict[str, Any]]:
    aliases = {entity: alias for alias, entity in bundle.entities.items()}
    rows = []
    for goal in bundle.goals:
        constraint = goal.constraint
        event_type = None
        filters = {}
        before_filters = None
        if hasattr(constraint, "event_type"):
            event_type = constraint.event_type
            filters = dict(constraint.event_filter or {})
        elif hasattr(constraint, "before_type"):
            event_type = constraint.after_type
            filters = dict(constraint.after_filter or {})
            before_filters = dict(constraint.before_filter or {})
        else:
            before_filters = None
        filters = {key: aliases.get(value, value) for key, value in filters.items()}
        if hasattr(constraint, "before_type"):
            before_filters = {key: aliases.get(value, value)
                              for key, value in before_filters.items()}
        kind = ("delivery" if event_type == "p5_delivery_settled" else
                "social_response" if event_type == "p5_note_response" else "unbound")
        rows.append({"constraint_id": goal.constraint_id, "hard": goal.hard,
                     "start": goal.start, "deadline": goal.deadline,
                     "event_type": event_type, "kind": kind, "filters": filters,
                     "before_event_type": (getattr(constraint, "before_type", None)),
                     "before_filters": before_filters})
    return rows


def _p5_candidate(snapshot: MatureSnapshot, route_id: str) -> Mapping[str, Any] | None:
    for candidate in snapshot.director_plan.get("candidates", ()):
        if candidate.get("route_id") == route_id:
            return candidate
    return None


def _support_method(snapshot: MatureSnapshot) -> tuple[str, Mapping[str, Any] | None]:
    """Resolve the P5 Director's selected candidate to an explicit GTN method."""
    plan = snapshot.director_plan
    selected = plan.get("selected_action")
    if selected == "open_main_passage":
        candidate = _p5_candidate(snapshot, "main_passage")
        if candidate and candidate.get("feasible") and candidate.get("opportunity_id") == selected:
            return "open_main", candidate
    if selected == "open_side_passage":
        candidate = _p5_candidate(snapshot, "side_passage")
        if candidate and candidate.get("feasible") and candidate.get("opportunity_id") == selected:
            return "open_side", candidate
    if selected == "NO_OP":
        for route_id in ("main_passage", "side_passage"):
            candidate = _p5_candidate(snapshot, route_id)
            if (candidate and candidate.get("feasible") and candidate.get("action") == "NO_OP"
                    and candidate.get("supported_hard_constraints")):
                return "existing_path", candidate
        hard_statuses = [row.get("status") for row in snapshot.verdicts if row.get("hard")]
        if hard_statuses and all(status == "SATISFIED" for status in hard_statuses):
            return "existing_path", None
    return "blocked", None


def _build_obligations(bundle, snapshot: MatureSnapshot) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    descriptors = _goal_descriptors(bundle)
    status = {row["constraint_id"]: row["status"] for row in snapshot.verdicts}
    deliveries: dict[str, list[dict[str, Any]]] = {"A": [], "B": []}
    social = []
    residuals = []
    task_bindings = snapshot.scene_binding.get("task_bindings", {})
    for descriptor in descriptors:
        filters = descriptor["filters"]
        if descriptor["kind"] == "delivery":
            actor = filters.get("actor")
            binding = task_bindings.get(actor, {})
            valid_binding = (actor in deliveries and filters.get("item") == binding.get("item_alias"))
            if not valid_binding:
                if descriptor["hard"] and status[descriptor["constraint_id"]] not in {"SATISFIED", "VIOLATED"}:
                    residuals.append({"constraint_id": descriptor["constraint_id"],
                                      "status": "UNBOUND_RESIDUAL",
                                      "reason": "hard delivery filter does not match the existing actor-owned P5 task binding"})
                continue
            evidence_ids = _matching_native_events(snapshot, descriptor.get("event_type"), filters, bundle)
            if status[descriptor["constraint_id"]] == "SATISFIED" and not evidence_ids:
                raise ValueError("SATISFIED delivery monitor has no matching sealed native receipt event")
            deliveries[actor].append({**descriptor, "status": status[descriptor["constraint_id"]],
                                      "item": filters.get("item"),
                                      "native_task_binding": deepcopy(binding),
                                      "evidence_event_ids": evidence_ids})
        elif descriptor["kind"] == "social_response":
            response = filters.get("response")
            response_supported = response in {None, "accepted", "rejected"}
            if (filters.get("actor"), filters.get("recipient"), filters.get("item")) != ("A", "B", "note") or \
                    not response_supported:
                if descriptor["hard"] and status[descriptor["constraint_id"]] not in {"SATISFIED", "VIOLATED"}:
                    residuals.append({"constraint_id": descriptor["constraint_id"],
                                      "status": "UNBOUND_RESIDUAL",
                                      "reason": "hard social filter is outside the registered native A-to-B Note response"})
                continue
            if descriptor.get("before_event_type") and not (
                    descriptor.get("before_event_type") == "p5_delivery_settled"
                    and descriptor.get("before_filters") == {"actor": "A", "item": "courier_supply"}):
                if descriptor["hard"] and status[descriptor["constraint_id"]] not in {"SATISFIED", "VIOLATED"}:
                    residuals.append({"constraint_id": descriptor["constraint_id"],
                                      "status": "UNBOUND_RESIDUAL",
                                      "reason": "hard social event order is not the registered A-delivery-before-note relation"})
                continue
            evidence_ids = _matching_native_events(snapshot, descriptor.get("event_type"), filters, bundle)
            if status[descriptor["constraint_id"]] == "SATISFIED" and not evidence_ids:
                raise ValueError("SATISFIED social monitor has no matching sealed native response event")
            before_events = _matching_native_events(snapshot, descriptor.get("before_event_type"),
                                                    descriptor.get("before_filters"), bundle)
            social.append({**descriptor, "status": status[descriptor["constraint_id"]],
                           "actor": filters.get("actor"), "recipient": filters.get("recipient"),
                           "item": filters.get("item"), "response": filters.get("response"),
                           "evidence_event_ids": evidence_ids})
            if descriptor.get("before_event_type"):
                social[-1]["required_before_event"] = {
                    "event_type": descriptor["before_event_type"],
                    "filters": descriptor.get("before_filters") or {},
                    "observed_event_ids": before_events}
        elif descriptor["hard"] and status[descriptor["constraint_id"]] not in {"SATISFIED", "VIOLATED"}:
            residuals.append({"constraint_id": descriptor["constraint_id"], "status": "UNBOUND_RESIDUAL",
                              "reason": "no registered P5 high-level wait method for this hard constraint"})
    return deliveries["A"] + deliveries["B"], social + residuals


def _matching_native_events(snapshot: MatureSnapshot, event_type, filters, bundle) -> list[str]:
    if not event_type or not isinstance(filters, Mapping):
        return []
    matched = []
    for event in snapshot.typed_trace.get("events", ()):
        if (not isinstance(event, Mapping) or event.get("event_type") != event_type
                or event.get("provenance") != "committed_ledger"
                or not isinstance(event.get("event_id"), str) or not event.get("event_id")):
            continue
        args = event.get("args", {})
        ok = True
        for key, expected in filters.items():
            actual = args.get(key)
            actual = actual.get("stable_id") if isinstance(actual, Mapping) else actual
            if hasattr(expected, "stable_id"):
                expected = expected.stable_id
            elif isinstance(expected, str) and expected in bundle.entities:
                expected = bundle.entities[expected].stable_id
            if actual != expected:
                ok = False
                break
        if ok:
            matched.append(str(event.get("event_id")))
    return matched


def _delivery_availability(snapshot: MatureSnapshot) -> dict[tuple[str, str], dict[str, Any]]:
    if not snapshot.world_snapshots:
        return {}
    latest = max(snapshot.world_snapshots, key=lambda row: row.get("minute", -1))
    holders = latest.get("holders", {})
    item_locations = latest.get("item_locations", {})
    actor_ids = {row.get("actor_alias"): row.get("actor_id") for row in snapshot.actor_evidence}
    room_roles = snapshot.scene_binding.get("room_roles", {})
    room_ids = {value for value in room_roles.values() if type(value) is int}
    result = {}
    for actor_alias, binding in snapshot.scene_binding.get("task_bindings", {}).items():
        item_alias = binding.get("item_alias")
        location = item_locations.get(item_alias)
        held_by_bound_actor = bool(holders.get(item_alias, {}).get(actor_alias))
        if held_by_bound_actor or (type(location) is int and location in room_ids):
            classification = "AVAILABLE_IN_REGISTERED_ROOM_OR_BOUND_INVENTORY"
            status = "AVAILABLE"
        elif type(location) is int and location in set(actor_ids.values()):
            classification = "HELD_BY_OTHER_NATIVE_ACTOR"
            status = "UNAVAILABLE"
        elif type(location) is int:
            classification = "OUTSIDE_REGISTERED_ROOMS_AND_NPC_INVENTORIES"
            status = "UNAVAILABLE"
        else:
            classification = "LOCATION_UNKNOWN_IN_SEALED_W"
            status = "UNKNOWN"
        result[(actor_alias, item_alias)] = {
            "status": status, "classification": classification,
            "native_location_id": location, "bound_item_id": binding.get("item_id"),
            "held_by_bound_actor": held_by_bound_actor,
            "observation_source": "sealed_p5_world_snapshot"}
    return result


def plan_high_level(bundle, snapshot: MatureSnapshot) -> dict[str, Any]:
    """Run the isolated mature-method domain against a validated P5 snapshot.

    GTPyhop plans only the high-level decomposition. Primitive rows named
    propose_* or wait_* are application control records, not native actions or
    achievement effects.
    """
    if not isinstance(snapshot, MatureSnapshot):
        raise TypeError("plan_high_level requires a validated MatureSnapshot")
    if bundle.bundle_id != snapshot.bundle_id or bundle.version != snapshot.bundle_version:
        raise ValueError("active bundle no longer matches the snapshot")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("mature P5 methods require the existing pinned GTPyhop installation") from exc
    from tools.native_platform_v0.p3.planning import _LOCK

    deliveries, social_and_residual = _build_obligations(bundle, snapshot)
    delivery_rows = {alias: [row for row in deliveries if row["filters"].get("actor") == alias]
                     for alias in ("A", "B")}
    social_rows = [row for row in social_and_residual if row.get("kind") == "social_response"]
    residual_rows = [row for row in social_and_residual if row.get("status") == "UNBOUND_RESIDUAL"]
    settled_delivery_ids = {row["constraint_id"] for row in deliveries if row["status"] == "SATISFIED"}
    a_delivery_ids = {row["constraint_id"] for row in delivery_rows["A"]}
    a_delivery_settled = bool(a_delivery_ids) and a_delivery_ids.issubset(settled_delivery_ids)
    method_name, selected_candidate = _support_method(snapshot)
    plan_data = snapshot.director_plan

    state = g.State("p5-mature-method-state")
    state.method_records = []
    state.obligations = []
    state.support_method = method_name
    state.support_candidate = deepcopy(selected_candidate)
    state.director_plan = deepcopy(plan_data)
    state.delivery_rows = deepcopy(deliveries)
    state.delivery_availability = _delivery_availability(snapshot)
    state.social_rows = deepcopy(social_rows)
    state.residual_rows = deepcopy(residual_rows)
    state.a_delivery_settled = a_delivery_settled
    state.a_delivery_ids = sorted(a_delivery_ids)
    state.snapshot_identity = {"scene_id": snapshot.scene_id, "now": snapshot.now,
                               "bundle_id": snapshot.bundle_id,
                               "bundle_version": snapshot.bundle_version,
                               "bundle_sha256": snapshot.bundle_sha256,
                               "trace_identity": dict(snapshot.trace_identity)}

    def record_support(world, method, candidate):
        world.method_records.append({"task": "support_deliveries", "method_id": method,
                                     "candidate": deepcopy(candidate),
                                     "director_plan_schema": plan_data.get("schema"),
                                     "prediction_only": True})
        return world

    def record_delivery_wait(world, actor, rows):
        for row in rows:
            status = row["status"]
            if status == "SATISFIED":
                world.obligations.append({"constraint_id": row["constraint_id"], "kind": "delivery",
                                          "actor": actor, "item": row.get("item"),
                                          "event_type": row["event_type"],
                                          "native_task_binding": deepcopy(row.get("native_task_binding")),
                                          "status": "SETTLED_BY_NATIVE_MONITOR",
                                          "native_evidence_event_ids": list(row.get("evidence_event_ids", []))})
            elif status == "VIOLATED":
                world.obligations.append({"constraint_id": row["constraint_id"], "kind": "delivery",
                                          "actor": actor, "item": row.get("item"),
                                          "event_type": row["event_type"],
                                          "native_task_binding": deepcopy(row.get("native_task_binding")),
                                          "status": "NATIVE_MONITOR_VIOLATED"})
            else:
                availability = world.delivery_availability.get(
                    (actor, row.get("item")), {"status": "UNKNOWN"})
                world.obligations.append({"constraint_id": row["constraint_id"], "kind": "delivery",
                                          "actor": actor, "item": row.get("item"),
                                          "event_type": row["event_type"],
                                          "native_task_binding": deepcopy(row.get("native_task_binding")),
                                          "status": ("WAITING_FOR_ITEM_AVAILABILITY"
                                                     if availability["status"] == "UNAVAILABLE"
                                                     else "WAITING_FOR_NATIVE_RECEIPT"),
                                          "deadline": row["deadline"],
                                          "native_task_binding_required": True,
                                          "item_availability": deepcopy(availability)})
        return world

    def record_social_wait(world, rows):
        for row in rows:
            if row["status"] == "SATISFIED":
                status = "SETTLED_BY_NATIVE_MONITOR"
            elif row["status"] == "VIOLATED":
                status = "NATIVE_MONITOR_VIOLATED"
            elif (row.get("required_before_event") and
                  not row["required_before_event"].get("observed_event_ids")):
                status = "DEFERRED_UNTIL_REQUIRED_NATIVE_EVENT"
            else:
                status = "WAITING_FOR_NATIVE_SOCIAL_EVENT"
            world.obligations.append({"constraint_id": row["constraint_id"], "kind": "social_response",
                                      "status": status,
                                      "actor": row.get("actor"),
                                      "recipient": row.get("recipient"),
                                      "item": row.get("item"),
                                      "event_type": row.get("event_type"),
                                      "native_evidence_event_ids": list(row.get("evidence_event_ids", [])),
                                      "depends_on_native_event_ids": (row.get("required_before_event", {})
                                                                       .get("observed_event_ids", [])),
                                      "required_before_event": deepcopy(row.get("required_before_event")),
                                      "deadline": row["deadline"],
                                      "response_is_native_and_may_be_accept_or_reject": True})
        return world

    def record_residual(world, rows):
        for row in rows:
            world.obligations.append(deepcopy(row))
        return world

    def outcome(world):
        return [("support_deliveries",), ("wait_delivery", "A"),
                ("wait_delivery", "B"), ("wait_social",), ("record_residuals",)]

    method_attempts = []

    def _attempt(world, method_id):
        method_attempts.append({"method_id": method_id,
                                "selected_by_p5_director": world.support_method == method_id,
                                "candidate": deepcopy(world.support_candidate)
                                if world.support_method == method_id else None})

    def support_existing_path(world):
        _attempt(world, "existing_path")
        return ([ ("record_support", "existing_path", world.support_candidate) ]
                if world.support_method == "existing_path" else None)

    def support_open_main(world):
        _attempt(world, "open_main")
        candidate = world.support_candidate
        if world.support_method == "open_main" and candidate:
            return [("record_support", "open_main", candidate)]
        return None

    def support_open_side(world):
        _attempt(world, "open_side")
        candidate = world.support_candidate
        if world.support_method == "open_side" and candidate:
            return [("record_support", "open_side", candidate)]
        return None

    def support_blocked(world):
        _attempt(world, "blocked")
        if world.support_method != "blocked":
            return None
        details = [row for row in world.director_plan.get("diagnostics", [])]
        return [("record_support", "blocked", {"diagnostics": details,
                "unmet_hard_constraints": _unmet_hard(world.director_plan),
                "prediction_only": True})]

    def wait_delivery(world, actor):
        return [("record_delivery_wait", actor,
                 [row for row in world.delivery_rows if row["filters"].get("actor") == actor])]

    def wait_social(world):
        return [("record_social_wait", world.social_rows)]

    def record_residuals(world):
        return [("record_residual", world.residual_rows)]

    actions = (record_support, record_delivery_wait, record_social_wait, record_residual)
    # GTPyhop's registration API uses a legacy current-domain global. The same
    # lock as P3 planning prevents NPC and narrative registration from racing.
    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain(_MATURE_METHODS_DOMAIN)
            g.declare_actions(*actions)
            g.declare_task_methods("author_outcome", outcome)
            g.declare_task_methods("support_deliveries", support_existing_path,
                                   support_open_main, support_open_side, support_blocked)
            g.declare_task_methods("wait_delivery", wait_delivery)
            g.declare_task_methods("wait_social", wait_social)
            g.declare_task_methods("record_residuals", record_residuals)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking",
                                  verbose=0, structured_logging=False) as session:
                result = session.find_plan(state, [("author_outcome",)], timeout_ms=1000,
                                           trace=True)
        finally:
            main.current_domain = previous

    if not result.success:
        raise RuntimeError("GTPyhop mature-method decomposition did not resolve its bounded task network")
    raw_steps = [list(row) for row in result.plan]
    planner_trace = ([{"depth": event.depth, "task": repr(event.item),
                       "status": event.status, "detail": event.detail}
                      for event in result.trace.events]
                     if result.trace is not None else [])
    # PlannerSession returns the simulated action sequence, not the terminal
    # simulated state. Rebuild the report from those exact returned control
    # primitives; do not assume the original input State was mutated.
    report_state = deepcopy(state)
    for row in raw_steps:
        if not row:
            continue
        name, *args = row
        if name == "record_support":
            record_support(report_state, *args)
        elif name == "record_delivery_wait":
            record_delivery_wait(report_state, *args)
        elif name == "record_social_wait":
            record_social_wait(report_state, *args)
        elif name == "record_residual":
            record_residual(report_state, *args)
    records = deepcopy(report_state.method_records)
    obligations = deepcopy(report_state.obligations)
    if len(records) != 1:
        raise RuntimeError("high-level method domain must emit exactly one support decision")
    support = records[0]
    if support["method_id"] == "blocked":
        status = "BLOCKED"
    elif any(row["status"].startswith("WAITING") or row["status"].startswith("DEFERRED")
             for row in obligations):
        status = "WAITING"
    else:
        status = "PROPOSED"
    proposal_available = support["method_id"] != "blocked"
    selected_action = plan_data.get("selected_action")
    candidate_guard = None
    if selected_action in {"open_main_passage", "open_side_passage"}:
        candidate_guard = {"scene_id": snapshot.scene_id,
                           "bundle_version": snapshot.bundle_version,
                           "based_on_minute": snapshot.now,
                           "events_through": snapshot.trace_identity["events_through"],
                           "values_through": snapshot.trace_identity["values_through"],
                           "selected_action": selected_action,
                           "opportunity_id": selected_action}
    hard_statuses = [row.get("status") for row in snapshot.verdicts if row.get("hard")]
    goal_monitor_status = ("SATISFIED" if hard_statuses and all(s == "SATISFIED" for s in hard_statuses)
                           else "VIOLATED" if any(s == "VIOLATED" for s in hard_statuses)
                           else "PENDING_OR_INDETERMINATE")
    return {"schema": "p5-mature-method-plan-v1", "status": status,
            "control_proposal_status": ("PROPOSAL_AVAILABLE" if proposal_available else "BLOCKED"),
            "control_proposal": {"selected_action": selected_action,
                                 "candidate": deepcopy(support.get("candidate")),
                                 "candidate_guard": candidate_guard,
                                 "selection_source": "unchanged_p5_planning_plan",
                                 "time_forecast_status": "TIME_UNCERTAIN_NATIVE_ACTOR_CALLBACKS",
                                 "timing_boundary": "P5 route min_minutes is a lower bound, not an actor arrival or delivery prediction"},
            "goal_monitor_status": goal_monitor_status,
            "scene_id": snapshot.scene_id, "based_on_minute": snapshot.now,
            "bundle_id": snapshot.bundle_id, "bundle_version": snapshot.bundle_version,
            "bundle_sha256": snapshot.bundle_sha256, "trace_identity": dict(snapshot.trace_identity),
            "method_trace": records, "obligations": obligations,
            "method_attempts": deepcopy(method_attempts),
            "gtpyhop_search_trace": planner_trace,
            "gtpyhop_plan": raw_steps, "gtpyhop_domain": _MATURE_METHODS_DOMAIN,
            "planner": "GTPyhop-PlannerSession-iterative_dfs_backtracking",
            "director_plan": deepcopy(plan_data),
            "author_goals_satisfied_by_meta_plan": False,
            "native_execution_occurred": False}


def _unmet_hard(plan: Mapping[str, Any]) -> list[str]:
    return sorted({constraint for candidate in plan.get("candidates", ())
                   for constraint in candidate.get("unmet_hard_constraints", ())})


__all__ = ["plan_high_level"]
