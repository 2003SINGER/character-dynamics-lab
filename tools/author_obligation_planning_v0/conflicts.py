"""Conservative static conflict proofs for the finite author-task model.

``NO_CONFLICT_PROVED`` means only that these checks found no certificate. It
does not establish reachability or feasibility in the game.
"""
from __future__ import annotations

from collections import deque
from typing import Iterable

from ..open_adventure_planning_v0.domain import OPERATORS, ROOMS, Operator, State
from .contracts import EvidenceEvent, MaxCount, Never, TaskSpec, TaskSpecError
from .search import compile_history_progress


CONFLICT_PROVED = "CONFLICT_PROVED_IN_FINITE_MODEL"
NO_CONFLICT_PROVED = "NO_CONFLICT_PROVED"

_BRIDGE = ("bridge",)
_UNBRIDGED = ("unbridged",)
_LAMP_ON = ("lamp_on",)
_LAMP_OFF = ("lamp_off",)


def static_conflicts(state: State, task: TaskSpec,
                     history: Iterable[EvidenceEvent] = ()) -> dict[str, object]:
    """Return conservative, auditable conflict certificates for a task.

    Checks are limited to explicit goal contradictions, violations already
    present in the verified event prefix, and a two-state bridge projection
    over the frozen B0 operators. No result here claims whole-game
    unreachability.
    """
    proofs: list[dict[str, object]] = []
    required = set(task.goal.required)
    forbidden = set(task.goal.forbidden)

    overlap = sorted(required & forbidden)
    if overlap:
        proofs.append({
            "kind": "required_and_forbidden_literal",
            "certificate": {
                "atoms": [list(atom) for atom in overlap],
                "explanation": "The same state literal is required and forbidden at the goal.",
            },
        })

    for group_name, group in _exclusive_groups():
        required_values = sorted(required & group)
        forbidden_values = sorted(forbidden & group)
        if len(required_values) > 1:
            proofs.append({
                "kind": "mutually_exclusive_required_literals",
                "certificate": {
                    "group": group_name,
                    "required": [list(atom) for atom in required_values],
                    "explanation": "The finite model permits exactly one value in this group.",
                },
            })
        elif not required_values and group <= forbidden:
            proofs.append({
                "kind": "all_mutually_exclusive_values_forbidden",
                "certificate": {
                    "group": group_name,
                    "forbidden": [list(atom) for atom in sorted(group)],
                    "explanation": "Every value in this finite exactly-one group is forbidden.",
                },
            })

    history_records = tuple(history)
    try:
        progress = compile_history_progress(task, history_records)
    except (TaskSpecError, TypeError) as exc:
        history_check: dict[str, object] = {
            "status": "UNUSABLE_HISTORY",
            "reason": str(exc),
            "source_ids": [event.source_id for event in history_records
                           if isinstance(event, EvidenceEvent)],
        }
    else:
        history_check = {
            "status": "VERIFIED_PREFIX_CHECKED",
            "events_used": progress.history_events_used,
            "source_ids": list(progress.history_source_ids),
            "violations": list(progress.violations),
        }
        if progress.violations:
            violated_names = set(progress.violations)
            evidence = [
                {"name": event.name, "source_id": event.source_id,
                 "sequence": event.sequence}
                for event in history_records
                if ((f"never:{event.name}" in violated_names)
                    or f"max_count:{event.name}>" in " ".join(violated_names)
                    or (event.name == "player_death"
                        and "always_no_death:player_death" in violated_names))
            ]
            proofs.append({
                "kind": "already_violated_history_obligation",
                "certificate": {
                    "violations": list(progress.violations),
                    "events": evidence,
                    "source_ids": list(progress.history_source_ids),
                    "explanation": "A verified prior event cannot be undone by replanning.",
                },
            })

    bridge_never = any(isinstance(obligation, Never)
                       and obligation.event == "create_bridge"
                       for obligation in task.obligations)
    if _BRIDGE in required and bridge_never and _BRIDGE not in state:
        projection = _bridge_projection_without_creation(OPERATORS)
        if True not in projection["reachable"]:
            proofs.append({
                "kind": "bridge_goal_conflicts_with_never_create",
                "certificate": {
                    "initial_bridge_present": False,
                    "required_goal_literal": list(_BRIDGE),
                    "forbidden_event": "create_bridge",
                    "producers": projection["producers"],
                    "projection": {
                        "states": [False, True],
                        "start": False,
                        "target": True,
                        "reachable_without_forbidden_event": projection["reachable"],
                        "allowed_edges": projection["edges"],
                        "blocked_create_edges": projection["blocked_create_edges"],
                        "non_bridge_preconditions": "abstracted away (over-approximation)",
                    },
                    "explanation": (
                        "From an absent bridge, every registered transition to a present "
                        "bridge is a create_bridge state change; Never(create_bridge) "
                        "blocks every such transition in this finite operator model."
                    ),
                    "scope": "frozen finite Open Adventure operator model only",
                },
            })

    return {
        "status": CONFLICT_PROVED if proofs else NO_CONFLICT_PROVED,
        "task_id": task.id,
        "task_version": task.version,
        "scope": "finite-model static checks; no proof of whole-game infeasibility",
        "proofs": proofs,
        "history_check": history_check,
    }


def _exclusive_groups() -> tuple[tuple[str, frozenset[tuple[str, ...]]], ...]:
    return (
        ("bridge_state", frozenset({_BRIDGE, _UNBRIDGED})),
        ("lamp_state", frozenset({_LAMP_ON, _LAMP_OFF})),
        ("player_location", frozenset(("at", "player", room) for room in ROOMS)),
    )


def _bridge_projection_without_creation(
        operators: tuple[Operator, ...]) -> dict[str, object]:
    """Explore the two bridge-presence states while rejecting create edges.

    Conditions on bridge presence are respected. All other operator
    preconditions are ignored, which adds possible transitions and therefore
    makes an unreachable result conservative for the actual finite model.
    """
    producers = [
        {"name": action.name, "args": list(action.args), "source": action.source}
        for action in operators
        if _BRIDGE in action.add_effects and _BRIDGE not in action.delete_effects
        and _BRIDGE not in action.preconditions
    ]
    reachable = {False}
    pending = deque([False])
    edges: set[tuple[bool, bool]] = set()
    blocked: set[tuple[bool, bool]] = set()
    while pending:
        present = pending.popleft()
        for action in operators:
            if _BRIDGE in action.preconditions and not present:
                continue
            if _BRIDGE in action.negative_preconditions and present:
                continue
            if _BRIDGE in action.add_effects:
                successor = True
            elif _BRIDGE in action.delete_effects:
                successor = False
            else:
                successor = present

            # Event semantics follow state differences. Operator labels and
            # command strings do not participate in the classification.
            creates = not present and successor
            if creates:
                blocked.add((present, successor))
                continue
            edges.add((present, successor))
            if successor not in reachable:
                reachable.add(successor)
                pending.append(successor)
    return {
        "reachable": [value for value in (False, True) if value in reachable],
        "edges": [{"from": before, "to": after}
                  for before, after in sorted(edges)],
        "blocked_create_edges": [{"from": before, "to": after}
                                 for before, after in sorted(blocked)],
        "producers": producers,
    }
