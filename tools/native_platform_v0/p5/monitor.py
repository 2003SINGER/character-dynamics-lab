"""P5 package monitoring and event-guarded storylet eligibility over TypedIR Trace."""
from __future__ import annotations

from enum import Enum
from fractions import Fraction
from typing import Any, Mapping

from tools.trajectory_constraints_v0.monitor import Verdict, evaluate
from tools.trajectory_constraints_v0.trace import Trace
from tools.trajectory_constraints_v0.types import Registry

from .bundle import AuthorBundle, p5_registry


def _goal_status(results: list[dict[str, Any]]) -> str:
    statuses = {row["status"] for row in results}
    if "VIOLATED" in statuses:
        return "VIOLATED"
    if "INDETERMINATE" in statuses:
        return "INDETERMINATE"
    if "PENDING" in statuses or "NOT_ACTIVATED" in statuses:
        return "PENDING"
    return "SATISFIED"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "stable_id") and hasattr(value, "entity_type"):
        return {"entity_type": value.entity_type, "stable_id": value.stable_id}
    return value


def evaluate_bundle(bundle: AuthorBundle, trace: Trace,
                    registry: Registry | None = None) -> dict[str, Any]:
    """Evaluate goals and real-event storylet guards, never proposals or authored text.

    The caller must construct `trace` from the authoritative server ledger and
    committed world snapshots. This adapter does not authenticate a producer.
    """
    if not isinstance(bundle, AuthorBundle) or not isinstance(trace, Trace):
        raise TypeError("evaluate_bundle requires an AuthorBundle and typed Trace")
    registry = registry or p5_registry()
    constraints = []
    hard_statuses = []
    for goal in bundle.goals:
        rows = []
        for result in evaluate(goal.constraint, trace, registry):
            row = {"constraint_id": goal.constraint_id, "hard": goal.hard,
                   "status": result.verdict.value, "reason": result.reason,
                   "witness": _json_safe(result.witness), "dependencies": _json_safe(result.dependencies),
                   "activation_id": result.activation_id}
            rows.append(row)
            constraints.append(row)
        if goal.hard:
            hard_statuses.extend(row["status"] for row in rows)

    if not hard_statuses:
        hard_status = "NO_HARD_GOALS"
    elif "VIOLATED" in hard_statuses:
        hard_status = "VIOLATED"
    elif "INDETERMINATE" in hard_statuses:
        hard_status = "INDETERMINATE"
    elif "PENDING" in hard_statuses or "NOT_ACTIVATED" in hard_statuses:
        hard_status = "PENDING"
    else:
        hard_status = "SATISFIED"

    branches = []
    note_responses = trace.matching_events("p5_note_response", version="1")
    for branch in bundle.branches:
        matches = [event for event in note_responses
                   if event.args.get("response") == branch.response]
        if matches:
            for event in matches:
                sealed = (event.provenance == "committed_ledger"
                          and trace.events_sealed_through is not None
                          and trace.events_sealed_through >= event.time)
                branches.append({"branch_id": branch.branch_id,
                                 "status": "ELIGIBLE" if sealed else "WAITING",
                                 "event_id": event.event_id if sealed else None,
                                 "response": branch.response,
                                 "storylet": {"id": branch.storylet_id, "text": branch.text},
                                 "effect": "content_only_no_world_effect"})
        else:
            complete = (trace.events_sealed_through is not None
                        and trace.events_sealed_through >= trace.now)
            branches.append({"branch_id": branch.branch_id,
                             "status": "NOT_APPLICABLE" if complete else "WAITING",
                             "event_id": None, "response": branch.response,
                             "storylet": {"id": branch.storylet_id, "text": branch.text},
                             "effect": "content_only_no_world_effect"})
    return {"bundle_id": bundle.bundle_id, "bundle_version": bundle.version,
            "now": _json_safe(trace.now), "constraints": constraints,
            "hard_status": hard_status, "branches": branches,
            "storylets_execute_world_effects": False}


__all__ = ["evaluate_bundle", "Verdict"]
