"""Small goal-aware symbolic opportunity search; all outcomes remain conditional."""
from __future__ import annotations

from typing import Any, Mapping

from tools.trajectory_constraints_v0.ast import EventCount, EventOrder, TemporalConstraint
from tools.trajectory_constraints_v0.ast import CompareValue

from .bundle import AuthorBundle, P5_INITIAL_PHYSICAL_BUDGET, ROUTE_IDS

SCHEMA = "p5-plan-v1"
NO_OP = "NO_OP"
ROUTE_ACTION = {"main_passage": "open_main_passage", "side_passage": "open_side_passage"}
ROUTE_ROW_KEYS = {"id", "opportunity_id", "open", "available", "cost", "min_minutes", "resource"}


def _invalid(message: str) -> ValueError:
    return ValueError(f"invalid P5 symbolic state: {message}")


def _validate_state(state: Mapping[str, Any]) -> dict[str, Any]:
    required = {"now", "horizon", "routes", "spent_cost", "opportunities_used", "verdicts", "physical_budget"}
    if not isinstance(state, Mapping) or set(state) != required:
        raise _invalid(f"expected exact keys {sorted(required)}")
    for key in ("now", "horizon", "spent_cost", "opportunities_used", "physical_budget"):
        if type(state[key]) is not int or state[key] < 0:
            raise _invalid(f"{key} must be a nonnegative integer")
    if state["now"] > state["horizon"] or state["spent_cost"] > state["physical_budget"]:
        raise _invalid("now/horizon or spent/physical budget is inconsistent")
    if state["physical_budget"] > P5_INITIAL_PHYSICAL_BUDGET or state["opportunities_used"] > 1:
        raise _invalid("P5 physical budget/opportunity limit exceeded")
    if not isinstance(state["routes"], list):
        raise _invalid("routes must be a list")
    seen, routes = set(), []
    for index, route in enumerate(state["routes"]):
        if not isinstance(route, Mapping) or set(route) != ROUTE_ROW_KEYS:
            raise _invalid(f"route[{index}] requires exact keys {sorted(ROUTE_ROW_KEYS)}")
        route_id = route["id"]
        if not isinstance(route_id, str) or route_id not in ROUTE_IDS or route_id in seen:
            raise _invalid(f"unknown or duplicate route id {route_id!r}")
        seen.add(route_id)
        if route["opportunity_id"] != ROUTE_ACTION[route_id]:
            raise _invalid(f"route {route_id!r} has a mismatched opportunity_id")
        if type(route["open"]) is not bool or type(route["available"]) is not bool:
            raise _invalid(f"route {route_id!r} open/available must be booleans")
        for key in ("cost", "min_minutes"):
            if type(route[key]) is not int or route[key] < 0:
                raise _invalid(f"route {route_id!r} {key} must be a nonnegative integer")
        if route["resource"] is not None and (not isinstance(route["resource"], str) or not route["resource"]):
            raise _invalid(f"route {route_id!r} resource must be null or a stable string")
        routes.append(dict(route))
    verdicts = state["verdicts"]
    if not isinstance(verdicts, list):
        raise _invalid("verdicts must be a list")
    seen_verdicts = set()
    allowed_status = {"NOT_ACTIVATED", "PENDING", "SATISFIED", "VIOLATED", "INDETERMINATE"}
    for row in verdicts:
        if (not isinstance(row, Mapping) or set(row) != {"constraint_id", "status"}
                or not isinstance(row["constraint_id"], str) or not row["constraint_id"]
                or not isinstance(row["status"], str) or row["status"] not in allowed_status):
            raise _invalid("each verdict needs a known constraint_id/status")
        if row["constraint_id"] in seen_verdicts:
            raise _invalid("duplicate constraint verdict")
        seen_verdicts.add(row["constraint_id"])
    return {**dict(state), "routes": routes, "verdicts": [dict(v) for v in verdicts]}


def _goal_status(bundle: AuthorBundle, verdicts: list[dict[str, Any]]) -> dict[str, str]:
    statuses = {row["constraint_id"]: row["status"] for row in verdicts}
    return {goal.constraint_id: statuses.get(goal.constraint_id, "PENDING") for goal in bundle.goals}


def _event_name(event_type: str) -> str | None:
    return {"p5_note_response": "note_response", "p5_delivery_settled": "delivery_settled"}.get(event_type)


def _support(goal: Any, route_id: str, bundle: AuthorBundle) -> tuple[str, list[str], str | None]:
    """Return support level, explicit dependencies and relevant route, if known."""
    aliases = {entity: alias for alias, entity in bundle.entities.items()}
    alias = lambda entity: aliases.get(entity)
    if isinstance(goal.constraint, EventCount):
        kind = _event_name(goal.constraint.event_type)
        filt = goal.constraint.event_filter or {}
        if kind == "delivery_settled":
            actor, item = filt.get("actor"), filt.get("item")
            if alias(actor) == "A" and alias(item) == "courier_supply":
                return "CONDITIONAL_PREREQUISITE", ["courier_supply_available", "route_open", "native_delivery_receipt"], route_id
            if alias(actor) == "B" and alias(item) in {"resident_parcel", "courier_supply"}:
                return "PARALLEL_NPC_OBLIGATION", ["B_own_bound_task_item_and_native_delivery_receipt"], None
            return "UNSUPPORTED_BY_ROUTE_ACTION", [], None
        if kind == "note_response":
            f = goal.constraint.event_filter or {}
            is_ab = (alias(f.get("actor")) == "A" and alias(f.get("recipient")) == "B"
                     and alias(f.get("item")) == "note")
            if is_ab:
                return "CONDITIONAL_PREREQUISITE", ["A_own_delivery", "local_contact", "positive_native_intent",
                                                     "B_native_response", "same_note_settlement"], route_id
            return "UNSUPPORTED_BY_ROUTE_ACTION", [], None
        return "UNKNOWN", [], None
    if isinstance(goal.constraint, EventOrder):
        before = _event_name(goal.constraint.before_type)
        after = _event_name(goal.constraint.after_type)
        before_filter = goal.constraint.before_filter or {}
        after_filter = goal.constraint.after_filter or {}
        a_delivery_then_note = (
            before == "delivery_settled" and after == "note_response"
            and alias(before_filter.get("actor")) == "A"
            and alias(before_filter.get("item")) == "courier_supply"
            and alias(after_filter.get("actor")) == "A"
            and alias(after_filter.get("recipient")) == "B"
            and alias(after_filter.get("item")) == "note")
        if a_delivery_then_note:
            return "CONDITIONAL_DEPENDENCY", [f"{before}_before_{after}"], route_id
        return "UNSUPPORTED_DEPENDENCY", [f"{before}_before_{after}"], None
    if isinstance(goal.constraint, TemporalConstraint) and isinstance(goal.constraint.formula, CompareValue):
        ref = goal.constraint.formula.ref
        if ref.observable_id == "p5_route_open":
            target = ref.args.get("route")
            expected = goal.constraint.formula.value is True
            if target != route_id:
                return "UNSUPPORTED_BY_ROUTE_ACTION", [], None
            return (("DIRECT_CONDITION", [f"route_open:{target}"], target) if expected
                    else ("DIRECT_CONFLICT", [f"route_must_remain_closed:{target}"], target))
        if ref.observable_id == "p5_holding":
            args = ref.args
            if alias(args.get("actor")) == "B" and alias(args.get("item")) == "resident_parcel":
                return "PARALLEL_NPC_OBLIGATION", ["resident_local_inventory_snapshot"], None
            return "RESOURCE_CONDITION_ONLY", ["world_holder_snapshot_required"], None
    return "UNKNOWN", [], None


def _finish_absolute_deadline(bundle: AuthorBundle, route: Mapping[str, Any], now: int) -> int:
    # This is a lower bound for changing route state, not a forecast of NPC arrival.
    return now + (0 if route["open"] else route["min_minutes"])


def plan(bundle: AuthorBundle, symbolic_state: Mapping[str, Any], *, max_expansions: int = 100) -> dict[str, Any]:
    """Enumerate a bounded AND/OR opportunity graph with goal-specific diagnostics.

    A passage can only provide a prerequisite or satisfy its own registered
    route-open state. It never guarantees a delivery, meeting, or social reply.
    """
    if not isinstance(bundle, AuthorBundle):
        raise TypeError("plan requires an AuthorBundle")
    state = _validate_state(symbolic_state)
    if type(max_expansions) is not int or max_expansions < 1:
        raise ValueError("max_expansions must be a positive integer")
    now, horizon = state["now"], state["horizon"]
    statuses = _goal_status(bundle, state["verdicts"])
    hard_unmet = [g for g in bundle.goals if g.hard and statuses[g.constraint_id] != "SATISFIED"]
    hard_targets = [g for g in hard_unmet if statuses[g.constraint_id] in {"PENDING", "NOT_ACTIVATED"}]
    unrecoverable = [g.constraint_id for g in hard_unmet if statuses[g.constraint_id] == "VIOLATED"]
    uncertain = [g.constraint_id for g in hard_unmet if statuses[g.constraint_id] == "INDETERMINATE"]
    soft_unmet = [g for g in bundle.goals if not g.hard and statuses[g.constraint_id] != "SATISFIED"]
    allowed = set(bundle.permissions["world_opportunities"])
    cost_cap = min(bundle.permissions["cost_budget"], state["physical_budget"])
    remaining_cost = max(0, cost_cap - state["spent_cost"])
    candidates = [{"candidate_id": "path:no-op", "action": NO_OP, "opportunity_id": None,
                   "route_id": None,
                   "feasible": True, "incremental_cost": 0, "projected_cost": state["spent_cost"],
                   "goal_support": [], "unmet_hard_constraints": [g.constraint_id for g in hard_unmet],
                   "unmet_soft_constraints": [g.constraint_id for g in soft_unmet],
                   "reason": "retain current world; no author action is executed",
                   "assumptions": ["NPC response and physical outcomes remain world-authoritative"]}]
    diagnostics: list[dict[str, Any]] = []
    expansions, exhausted = 1, False
    for route in sorted(state["routes"], key=lambda r: r["id"]):
        if expansions >= max_expansions:
            exhausted = True
            diagnostics.append({"code": "SEARCH_BUDGET_EXHAUSTED"})
            break
        expansions += 1
        action = NO_OP if route["open"] else route["opportunity_id"]
        cost = 0 if route["open"] else route["cost"]
        finish_lb = _finish_absolute_deadline(bundle, route, now)
        support_rows = []
        hard_blocks = []
        soft_penalties = []
        for goal in bundle.goals:
            if statuses[goal.constraint_id] == "SATISFIED":
                continue
            support, dependencies, target_route = _support(goal, route["id"], bundle)
            relevant = support in {"CONDITIONAL_PREREQUISITE", "DIRECT_CONDITION", "CONDITIONAL_DEPENDENCY"}
            parallel = support == "PARALLEL_NPC_OBLIGATION"
            direct_conflict = support == "DIRECT_CONFLICT"
            effective_cutoff = min(goal.deadline, horizon)
            goal_bound = now if support == "DIRECT_CONDITION" else finish_lb
            deadline_fit = goal_bound <= effective_cutoff
            row = {"constraint_id": goal.constraint_id, "hard": goal.hard,
                   "support": support if relevant or parallel or direct_conflict else "UNSUPPORTED_BY_THIS_ACTION",
                   "dependencies": dependencies, "window_start": goal.start, "deadline": goal.deadline,
                   "parallel_unaffected": parallel,
                   "opportunity_settlement_lower_bound": now,
                   "dependent_task_lower_bound": finish_lb if support != "DIRECT_CONDITION" else None,
                   "goal_relevant_lower_bound": goal_bound, "effective_cutoff": effective_cutoff,
                   "deadline_lower_bound_fits": deadline_fit,
                   "outcome_guaranteed": False}
            support_rows.append(row)
            if goal.hard and not parallel and (
                    direct_conflict or not relevant or not deadline_fit):
                hard_blocks.append(goal.constraint_id)
            if not goal.hard and (not relevant or not deadline_fit):
                soft_penalties.append(goal.constraint_id)
        reasons = []
        if not route["open"] and route["opportunity_id"] not in allowed:
            reasons.append("opportunity is not authorized by the active bundle")
        if not route["open"] and not route["available"]:
            reasons.append("world preconditions currently make this opportunity unavailable")
        if not route["open"] and state["opportunities_used"] >= bundle.permissions["max_opportunities"]:
            reasons.append("bundle opportunity limit is already spent")
        if cost > remaining_cost:
            reasons.append("incremental opportunity cost exceeds remaining author/physical budget")
        if hard_blocks:
            reasons.append("hard goal support/deadline conflict: " + ", ".join(hard_blocks))
        feasible = not reasons
        relevant_hard = [r for r in support_rows if r["hard"] and r["support"] in
                         {"CONDITIONAL_PREREQUISITE", "DIRECT_CONDITION", "CONDITIONAL_DEPENDENCY"}
                         and r["deadline_lower_bound_fits"]]
        relevant_soft = [r for r in support_rows if not r["hard"] and r["support"] in
                         {"CONDITIONAL_PREREQUISITE", "DIRECT_CONDITION", "CONDITIONAL_DEPENDENCY"}
                         and r["deadline_lower_bound_fits"]]
        soft_penalties = [r["constraint_id"] for r in support_rows if not r["hard"]
                          and r["constraint_id"] in [g.constraint_id for g in soft_unmet]
                          and r not in relevant_soft]
        candidates.append({"candidate_id": f"path:{route['id']}", "action": action,
                           "opportunity_id": None if action == NO_OP else route["opportunity_id"],
                           "route_id": route["id"], "feasible": feasible, "incremental_cost": cost,
                           "projected_cost": state["spent_cost"] + cost,
                           "opportunity_settlement_lower_bound": now,
                           "dependent_task_lower_bound": finish_lb,
                           "goal_support": support_rows,
                           "supported_hard_constraints": [r["constraint_id"] for r in relevant_hard],
                           "supported_soft_constraints": [r["constraint_id"] for r in relevant_soft],
                           "soft_unmet_penalties": soft_penalties,
                           "soft_support_count": len(relevant_soft),
                           "unmet_hard_constraints": [g.constraint_id for g in hard_unmet],
                           "unmet_soft_constraints": [g.constraint_id for g in soft_unmet],
                           "reason": "; ".join(reasons) if reasons else "conditional prerequisite only; no NPC/world result is guaranteed",
                           "assumptions": ["route min_minutes is an absolute lower bound from now, not an NPC arrival prediction",
                                           "delivery requires an actual native settled receipt",
                                           "note response requires the actual native response and same-note settlement"]})
        if reasons:
            diagnostics.append({"code": "CANDIDATE_CONFLICT", "candidate_id": f"path:{route['id']}",
                                "detail": "; ".join(reasons)})

    actionable = [c for c in candidates[1:] if c["feasible"] and c["route_id"] is not None
                  and c["supported_hard_constraints"]]
    if unrecoverable or uncertain:
        actionable = []
        diagnostics.append({"code": "HARD_EVIDENCE_NOT_ACTIONABLE",
                            "unrecoverable_violations": unrecoverable,
                            "indeterminate_constraints": uncertain,
                            "detail": "a failed historical goal is not repaired by an author opportunity; unknown evidence keeps NO_OP"})
    selected = min(actionable, key=lambda c: (-c["soft_support_count"], c["incremental_cost"],
                                               c["dependent_task_lower_bound"], c["opportunity_id"]))["action"] if actionable else NO_OP
    dependency_edges = []
    for goal in bundle.goals:
        if isinstance(goal.constraint, EventOrder):
            dependency_edges.append({"constraint_id": goal.constraint_id,
                                     "before": goal.constraint.before_type,
                                     "after": goal.constraint.after_type,
                                     "order": goal.constraint.order.value,
                                     "guaranteed": False})
    branches = [{"branch_id": b.branch_id, "guard": {"event": "note_response", "response": b.response},
                 "storylet": {"id": b.storylet_id, "text": b.text},
                 "conditional_on_actual_event": True, "selectable_world_action": False}
                for b in bundle.branches]
    and_or = {"root": {"node_id": "hard-goals", "operator": "AND",
                        "children": [g.constraint_id for g in hard_unmet]},
              "opportunity_choice": {"node_id": "route-choice", "operator": "OR",
                                     "children": [c["candidate_id"] for c in candidates]},
              "dependencies": dependency_edges, "branches": branches}
    if hard_unmet and not actionable:
        diagnostics.append({"code": "NO_SUPPORTED_HARD_PATH",
                            "detail": "no candidate has supported hard-goal prerequisites; result is not an impossibility proof"})
    return {"schema": SCHEMA, "bundle_id": bundle.bundle_id, "bundle_version": bundle.version,
            "status": "SEARCH_INCOMPLETE" if exhausted else "SEARCH_COMPLETE",
            "selected_action": selected, "candidates": candidates,
            "conditional_branches": branches, "and_or_graph": and_or,
            "diagnostics": diagnostics, "expansions": expansions,
            "max_expansions": max_expansions,
            "candidate_set_complete": not exhausted, "optimality_claim": False,
            "search_scope": "finite symbolic passage opportunities with goal-specific lower-bound checks",
            "prediction_guarantee": False}


__all__ = ["plan", "NO_OP", "SCHEMA"]
