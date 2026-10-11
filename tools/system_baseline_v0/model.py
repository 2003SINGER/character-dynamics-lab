"""P5 evidence projection and candidate freshness contract for System Baseline v0."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from typing import Any, Mapping

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.trajectory_constraints_v0.ast import CompareValue, TemporalConstraint


ROUTE_COSTS = {"main_passage": ("open_main_passage", 2),
               "side_passage": ("open_side_passage", 1)}
ACTION_TO_ROUTE = {value[0]: key for key, value in ROUTE_COSTS.items()}
NO_OP = "NO_OP"


@dataclass(frozen=True)
class PlanningView:
    scene_id: str
    bundle_id: str
    bundle_version: int
    now: int
    horizon: int
    events_through: int
    values_through: int
    route_open: tuple[tuple[str, bool], ...]
    spent_cost: int
    opportunities_used: int
    allowed_world_opportunities: tuple[str, ...]
    cost_budget: int
    max_opportunities: int
    hard_route_targets: tuple[tuple[str, bool], ...]
    route_contracts: tuple[tuple[str, str, bool, str, str, str, bool, bool, str], ...]
    hard_unresolved: tuple[str, ...]
    hard_route_blockers: tuple[str, ...]
    constraint_statuses: tuple[tuple[str, str], ...]
    projection_obligations: tuple[tuple[str, str], ...]
    evidence_sha256: str


@dataclass(frozen=True)
class Candidate:
    selected_action: str
    opportunity_id: str | None
    scene_id: str
    bundle_id: str
    bundle_version: int
    based_on_minute: int
    events_through: int
    values_through: int
    problem_sha256: str
    plan_sha256: str
    search_status: str
    projection_obligations: tuple[tuple[str, str], ...]

    def native_guard(self) -> dict[str, Any]:
        return {"scene_id": self.scene_id, "bundle_version": self.bundle_version,
                "based_on_minute": self.based_on_minute,
                "events_through": self.events_through, "values_through": self.values_through,
                "selected_action": self.selected_action, "opportunity_id": self.opportunity_id}


def _sha(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")).hexdigest()


def _route_goal(goal: Any) -> tuple[str, bool, str, Fraction, Fraction, bool, bool] | None:
    constraint = goal.constraint
    if not isinstance(constraint, TemporalConstraint) or not isinstance(constraint.formula, CompareValue):
        return None
    ref = constraint.formula.ref
    route = ref.args.get("route") if ref.observable_id == "p5_route_open" else None
    if route not in ROUTE_COSTS or type(constraint.formula.value) is not bool:
        return None
    return (route, constraint.formula.value, constraint.op.value,
            constraint.window.start, constraint.window.end,
            constraint.window.left_closed, constraint.window.right_closed)


def project_p5_for_sabre(trace: Mapping[str, Any], raw_bundle: Mapping[str, Any],
                         scene_id: str) -> PlanningView:
    """Project only sealed P5 trace/world fields and the active validated bundle."""
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("scene_id must be a nonempty generated P5 scene identity")
    if not isinstance(trace, Mapping) or not isinstance(raw_bundle, Mapping):
        raise TypeError("P5 trace and AuthorBundle input must be mappings")
    if (trace.get("scene_id") != scene_id
            or trace.get("evidence_schema") != "p5-live-trace-v1"
            or trace.get("source") != "native_platform_v0.p5.service._evidence"
            or trace.get("prefix_status") != "SEALED_COMPLETE"):
        raise ValueError("planner projection requires this scene's P5 live-evidence trace")
    bundle = load_bundle(raw_bundle)
    if type(bundle.version) is not int:
        raise ValueError("P5 bundle version is not a strict integer")
    now = trace.get("now")
    complete = trace.get("complete_through")
    if type(now) is not int or not isinstance(complete, Mapping):
        raise ValueError("P5 trace clock/frontiers are missing or malformed")
    events = complete.get("events")
    values = complete.get("values")
    if type(events) is not int or type(values) is not int or not (events == values == now):
        raise ValueError("P5 planning requires a complete sealed prefix through the current minute")
    identity = trace.get("bundle_identity")
    if (not isinstance(identity, Mapping) or identity.get("bundle_id") != bundle.bundle_id
            or type(identity.get("version")) is not int or identity.get("version") != bundle.version):
        raise ValueError("trace verdicts are not bound to the supplied active bundle identity/version")
    snapshots = trace.get("world_snapshots")
    if not isinstance(snapshots, list):
        raise ValueError("P5 trace lacks native world snapshots")
    snapshot = next((row for row in snapshots if isinstance(row, Mapping)
                     and row.get("minute") == values), None)
    if snapshot is None or not isinstance(snapshot.get("routes"), Mapping):
        raise ValueError("route state must come from the snapshot at the sealed values frontier")
    route_open = tuple((route, snapshot["routes"].get(route)) for route in ROUTE_COSTS)
    if any(type(value) is not bool for _, value in route_open):
        raise ValueError("P5 snapshot route facts must be booleans")
    ledger = trace.get("ledger")
    if not isinstance(ledger, list):
        raise ValueError("P5 trace lacks native ledger rows")
    opportunity_rows = [row for row in ledger if isinstance(row, Mapping)
                        and row.get("event_type") == "P5_OPPORTUNITY_SETTLED"]
    if any(type(row.get("minute")) is not int or row.get("sealed") is not True
           for row in opportunity_rows):
        raise ValueError("opportunity ledger contains an unsealed or un-timed settlement")
    settled = [row for row in opportunity_rows if row["minute"] <= events]
    spent = 0
    for row in settled:
        args = row.get("typed_args")
        if not isinstance(args, Mapping) or type(args.get("cost")) is not int:
            raise ValueError("sealed opportunity ledger row lacks typed cost")
        spent += args["cost"]
    goals = []
    route_contracts = []
    hard_unresolved = []
    hard_route_blockers = []
    obligations = []
    verdicts_obj = trace.get("verdicts")
    if not isinstance(verdicts_obj, Mapping):
        raise ValueError("P5 trace lacks native TypedIR verdicts")
    verdict_rows = verdicts_obj.get("constraints")
    if not isinstance(verdict_rows, list):
        raise ValueError("P5 trace constraints are malformed")
    status_by_id = {row.get("constraint_id"): row.get("status") for row in verdict_rows
                    if isinstance(row, Mapping)}
    if any(goal.constraint_id not in status_by_id for goal in bundle.goals):
        raise ValueError("native TypedIR verdicts omit one or more active bundle constraints")
    for goal in bundle.goals:
        if goal.hard and status_by_id[goal.constraint_id] == "SATISFIED":
            obligations.append((goal.constraint_id, "WITNESSED: native TypedIR reports SATISFIED on the sealed prefix"))
            continue
        route_goal = _route_goal(goal)
        if route_goal is not None:
            route, desired, op, start, deadline, left_closed, right_closed = route_goal
            status = status_by_id.get(goal.constraint_id)
            route_contracts.append((goal.constraint_id, route, desired, op, str(start),
                                    str(deadline), left_closed, right_closed, str(status)))
            dispatch_minute = now + 1
            dispatch_inside_window = (
                (dispatch_minute > start or left_closed and dispatch_minute == start)
                and (dispatch_minute < deadline or right_closed and dispatch_minute == deadline))
            if not goal.hard:
                obligations.append((goal.constraint_id, "UNSCORED: soft route constraint is not optimized"))
            elif (desired and op == "EVENTUALLY" and dispatch_inside_window
                  and status != "VIOLATED"):
                if status != "SATISFIED":
                    goals.append((route, True))
                obligations.append((goal.constraint_id,
                                    f"candidate-only EVENTUALLY {route}=true in [{start},{deadline}]"))
            else:
                reason = ("route-close is outside the registered action set" if not desired else
                          "only EVENTUALLY=true with a dispatch minute inside its absolute window is projected")
                hard_unresolved.append(goal.constraint_id)
                hard_route_blockers.append(goal.constraint_id)
                obligations.append((goal.constraint_id, "RESIDUAL: " + reason))
        elif goal.hard:
            hard_unresolved.append(goal.constraint_id)
            obligations.append((goal.constraint_id, "RESIDUAL: outside the finite route-opportunity Sabre abstraction"))
        else:
            obligations.append((goal.constraint_id, "UNSCORED: outside the finite route-opportunity Sabre abstraction"))
    verdicts = verdict_rows
    statuses = tuple(sorted((str(row["constraint_id"]), str(row["status"]))
                            for row in verdicts if isinstance(row, Mapping)
                            and isinstance(row.get("constraint_id"), str)
                            and isinstance(row.get("status"), str)))
    evidence_projection = {"scene_id": scene_id, "now": now, "frontier": [events, values],
                           "snapshot": snapshot, "ledger": ledger, "bundle": raw_bundle}
    horizon = trace.get("horizon", 24)
    if type(horizon) is not int or horizon < now:
        raise ValueError("P5 horizon is malformed or precedes the sealed prefix")
    return PlanningView(
        scene_id, bundle.bundle_id, bundle.version, now, horizon, events, values,
        route_open, spent, len(settled),
        tuple(bundle.permissions["world_opportunities"]), int(bundle.permissions["cost_budget"]),
        int(bundle.permissions["max_opportunities"]), tuple(sorted(set(goals))),
        tuple(route_contracts), tuple(hard_unresolved), tuple(hard_route_blockers), statuses,
        tuple(obligations), _sha(evidence_projection))


def validate_candidate_guard(candidate: Candidate | Mapping[str, Any], *, scene_id: str,
                             bundle_id: str, bundle_version: int, now: int,
                             events_through: int, values_through: int,
                             action: str, opportunity_id: str | None) -> bool:
    """Pure host-side guard; native P5 repeats scene/version/frontier/action checks."""
    if isinstance(candidate, Candidate):
        row = candidate.native_guard() | {"bundle_id": candidate.bundle_id}
    elif isinstance(candidate, Mapping):
        row = candidate
    else:
        return False
    base_minute = now - 1
    return (row.get("scene_id") == scene_id and row.get("bundle_id", bundle_id) == bundle_id
            and type(row.get("bundle_version")) is int and row.get("bundle_version") == bundle_version
            and type(row.get("based_on_minute")) is int and row.get("based_on_minute") == base_minute
            and type(row.get("events_through")) is int and row.get("events_through") == events_through == base_minute
            and type(row.get("values_through")) is int and row.get("values_through") == values_through == base_minute
            and row.get("selected_action") == action and row.get("opportunity_id") == opportunity_id)


def make_candidate(view: PlanningView, selected_action: str, problem: str,
                   plan_document: Mapping[str, Any], search_status: str) -> Candidate:
    if selected_action != NO_OP and selected_action not in ACTION_TO_ROUTE:
        raise ValueError("Sabre returned an action outside the P5 registered route-opportunity set")
    opportunity = None if selected_action == NO_OP else selected_action
    return Candidate(selected_action, opportunity, view.scene_id, view.bundle_id, view.bundle_version,
                     view.now, view.events_through, view.values_through, sha256(problem.encode()).hexdigest(),
                     _sha(plan_document), search_status, view.projection_obligations)
