"""Finite, explicit author task candidates for Author Obligation Planning v0.

These records specify desired facts and event obligations only. They do not
contain action paths or claim that any candidate has been executed natively.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from tools.open_adventure_planning_v0.domain import Atom, State, initial_state
from .contracts import (
    Eventually, InOrder, MaxCount, Never, task_spec_to_dict,
)
from .search import Goal, TaskSpec


@dataclass(frozen=True)
class TaskCase:
    """A task plus its initial state and (for H cases) a gated edit."""

    task: TaskSpec
    initial: State
    edit_trigger: str | None = None
    requires_native_feedback: bool = False


def _task(task_id: str, description: str, *, required: Iterable[Atom],
          forbidden: Iterable[Atom] = (), obligations=()) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        version="1",
        text=description.rstrip(" .") + "; do not die at any point.",
        goal=Goal(frozenset(required), frozenset(forbidden)),
        obligations=tuple(obligations),
        always_no_death=True,
    )


def _east_goal(*, bridge: str | None) -> tuple[set[Atom], set[Atom]]:
    required: set[Atom] = {
        ("at", "player", "EASTBANK"),
        ("carrying", "keys"),
        ("carrying", "lamp"),
        ("lamp_on",),
    }
    forbidden: set[Atom] = set()
    if bridge == "bridge":
        required.add(("bridge",))
    elif bridge == "unbridged":
        required.add(("unbridged",))
    return required, forbidden


def _west_goal(*, bridge: str | None = None,
               forbidden_items: Iterable[str] = ()) -> tuple[set[Atom], set[Atom]]:
    required: set[Atom] = {
        ("at", "player", "WESTBANK"),
        ("carrying", "keys"),
        ("carrying", "lamp"),
        ("lamp_on",),
    }
    forbidden: set[Atom] = {("carrying", item) for item in forbidden_items}
    if bridge == "bridge":
        required.add(("bridge",))
    elif bridge == "unbridged":
        required.add(("unbridged",))
    return required, forbidden


def _a_to_f() -> list[TaskSpec]:
    tasks: list[TaskSpec] = []
    bridge_states = ("unbridged", "bridge", None)
    for prefix, extra in (
        ("A", ()),
        ("B", (Eventually("create_bridge"),)),
        ("C", (InOrder(("arrive_west", "return_east")),)),
        ("D", (Never("arrive_west"),)),
        ("E", (InOrder(("create_bridge", "destroy_bridge")),)),
        ("F", (Never("create_bridge"),)),
    ):
        for index, bridge in enumerate(bridge_states, 1):
            required, forbidden = _east_goal(bridge=bridge)
            history_text = {
                "A": "with no bridge history requirement",
                "B": "and actually create the bridge at least once",
                "C": "after visiting WESTBANK and then returning to EASTBANK",
                "D": "without ever visiting WESTBANK",
                "E": "after creating and then destroying the bridge in that order",
                "F": "without ever creating the bridge",
            }[prefix]
            tasks.append(_task(
                f"{prefix}{index}",
                f"Finish at EASTBANK carrying keys and lamp with the lamp on"
                + (f" and {bridge}" if bridge else "")
                + f" {history_text}",
                required=required, forbidden=forbidden, obligations=extra,
            ))
    return tasks


def _g_tasks() -> list[TaskSpec]:
    east = ("at", "player", "EASTBANK")
    west = ("at", "player", "WESTBANK")
    keys, lamp, rod = (("carrying", item) for item in ("keys", "lamp", "rod"))
    lit, dark = ("lamp_on",), ("lamp_off",)
    bridge, unbridged = ("bridge",), ("unbridged",)
    return [
        _task("G1", "Finish east with a bridge, carrying the lamp, lamp on; keys unrestricted",
              required={east, bridge, lamp, lit}),
        _task("G2", "Finish east unbridged carrying keys; lamp unrestricted",
              required={east, unbridged, keys}),
        _task("G3", "Finish east with a bridge, not carrying keys, carrying the lit lamp",
              required={east, bridge, lamp, lit}, forbidden={keys}),
        _task("G4", "Finish west carrying keys and the lit lamp; bridge unrestricted",
              required={west, keys, lamp, lit}),
        _task("G5", "Finish west unbridged carrying keys and the lit lamp",
              required={west, unbridged, keys, lamp, lit}),
        _task("G6", "Finish east carrying keys and lamp with the lamp off; bridge unrestricted",
              required={east, keys, lamp, dark}),
        _task("G7", "Finish east unbridged carrying keys, rod, and the lit lamp",
              required={east, unbridged, keys, rod, lamp, lit}),
        _task("G8", "Finish west not carrying the rod, carrying the lit lamp; keys and bridge unrestricted",
              required={west, lamp, lit}, forbidden={rod}),
        _task("G9", "Finish east carrying the lit lamp after arriving west and returning east; keys and bridge unrestricted",
              required={east, lamp, lit},
              obligations=(InOrder(("arrive_west", "return_east")),)),
        _task("G10", "Finish east with a bridge and the lit lamp, keys unrestricted, creating at most one bridge",
              required={east, bridge, lamp, lit},
              obligations=(MaxCount("create_bridge", 1),)),
    ]


def _h_cases() -> list[TaskCase]:
    a2 = next(task for task in _a_to_f() if task.id == "A2")
    a3 = next(task for task in _a_to_f() if task.id == "A3")
    # The proposed take/drop sequence is intentionally not encoded as a plan.
    # A real player intervention and native receipt are prerequisites.
    h4_task = _task(
        "H4", "Finish EASTBANK carrying keys and the lit lamp with the bridge present; actually create the bridge at least once; preserve this requirement through the true-execution rejection and feedback negative control",
        required=a2.goal.required,
        forbidden=a2.goal.forbidden,
        obligations=(Eventually("create_bridge"),),
    )
    h4 = TaskCase(h4_task, initial_state(), edit_trigger="after_native_player_intervention",
                  requires_native_feedback=True)
    return [
        TaskCase(_task("H1", "Begin with A2; after a successful rod pickup, author revises the goal to A1",
                       required=a2.goal.required, forbidden=a2.goal.forbidden), initial_state(),
                 edit_trigger="after_successful_take_rod"),
        TaskCase(_task("H2", "Begin with A3; after first arriving east, author adds west then return-east history",
                       required=a3.goal.required, forbidden=a3.goal.forbidden), initial_state(),
                 edit_trigger="after_first_arrive_east"),
        TaskCase(_task("H3", "Begin with A2; immediately before building, author adds whole-interval never-create",
                       required=a2.goal.required, forbidden=a2.goal.forbidden), initial_state(),
                 edit_trigger="immediately_before_build"),
        h4,
    ]


STATIC_TASKS: tuple[TaskSpec, ...] = tuple(_a_to_f() + _g_tasks())
DYNAMIC_CASES: tuple[TaskCase, ...] = tuple(_h_cases())
ALL_TASK_IDS = tuple(task.id for task in STATIC_TASKS) + tuple(case.task.id for case in DYNAMIC_CASES)

if len(ALL_TASK_IDS) != 32 or len(set(ALL_TASK_IDS)) != 32:
    raise RuntimeError("author obligation task catalog must contain 32 unique candidates")


def task_by_id(task_id: str) -> TaskSpec | TaskCase:
    for task in STATIC_TASKS:
        if task.id == task_id:
            return task
    for case in DYNAMIC_CASES:
        if case.task.id == task_id:
            return case
    raise KeyError(task_id)


def revise_after(task: TaskSpec, trigger: str) -> TaskSpec:
    """Apply the author edit associated with H1-H3 after its named gate.

    This returns a new version and leaves the prior TaskSpec object intact.
    Callers keep native history separately and pass it unchanged to plan_task.
    """
    if task.id == "H1" and trigger == "after_successful_take_rod":
        a1 = next(row for row in _a_to_f() if row.id == "A1")
        bridge_atoms = {("bridge",), ("unbridged",)}
        required = (set(task.goal.required) - bridge_atoms) | (set(a1.goal.required) & bridge_atoms)
        forbidden = (set(task.goal.forbidden) - bridge_atoms) | (set(a1.goal.forbidden) & bridge_atoms)
        return replace(task, version="2",
                       text="H1 author revision adopts A1's final bridge state after successful take rod; do not die at any point.",
                       goal=Goal(frozenset(required), frozenset(forbidden)))
    if task.id == "H2" and trigger == "after_first_arrive_east":
        return replace(task, version="2",
                       text="H2 revised after first east arrival: visit WESTBANK then return to EASTBANK; do not die at any point.",
                       obligations=task.obligations + (InOrder(("arrive_west", "return_east")),))
    if task.id == "H3" and trigger == "immediately_before_build":
        return replace(task, version="2",
                       text="H3 revised before build: never create a bridge over the whole interval; do not die at any point.",
                       obligations=task.obligations + (Never("create_bridge"),))
    raise ValueError("trigger does not match a registered author revision")


def serialize_task(task: TaskSpec) -> dict:
    """Return the strict public JSON shape consumed by task_spec_from_dict."""
    return task_spec_to_dict(task)
