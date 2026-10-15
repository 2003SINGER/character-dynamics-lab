"""Strict task and native-evidence contracts for obligation-aware planning.

This module deliberately accepts a small registered vocabulary. It preserves
the author's original task text but does not interpret natural language.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .search import Goal


EVENTS = frozenset({
    "create_bridge",
    "destroy_bridge",
    "arrive_west",
    "return_east",
    "player_death",
})

Atom: TypeAlias = tuple[str, ...]


class TaskSpecError(ValueError):
    """Raised when a task or evidence record exceeds the registered contract."""


@dataclass(frozen=True)
class Eventually:
    event: str


@dataclass(frozen=True)
class InOrder:
    events: tuple[str, ...]


@dataclass(frozen=True)
class Never:
    event: str


@dataclass(frozen=True)
class MaxCount:
    event: str
    maximum: int


Obligation: TypeAlias = Eventually | InOrder | Never | MaxCount


@dataclass(frozen=True)
class TaskSpec:
    id: str
    version: str
    text: str
    goal: "Goal"
    obligations: tuple[Obligation, ...] = ()
    always_no_death: bool = False

    @property
    def task_id(self) -> str:
        """Compatibility spelling for callers that name the stable ID explicitly."""
        return self.id

    def __post_init__(self) -> None:
        _nonempty(self.id, "task id")
        _nonempty(self.version, "task version")
        if not isinstance(self.text, str) or not self.text.strip():
            raise TaskSpecError("text must preserve a non-empty original task")
        if type(self.always_no_death) is not bool:
            raise TaskSpecError("always_no_death must be a boolean")
        if not isinstance(self.obligations, tuple):
            raise TaskSpecError("obligations must be a tuple")
        _validate_goal(self.goal)
        for obligation in self.obligations:
            _validate_obligation(obligation)
        if (not self.goal.required and not self.goal.forbidden
                and not self.obligations and not self.always_no_death):
            raise TaskSpecError("task must contain at least one goal or author constraint")


@dataclass(frozen=True)
class EvidenceEvent:
    """One event backed by a native observation/step record.

    Multiple distinct events may share a source ID and sequence when they came
    from the same native step. The pair plus event name must be unique.
    """

    name: str
    source_id: str
    sequence: int

    def __post_init__(self) -> None:
        _validate_event(self.name)
        _nonempty(self.source_id, "evidence source_id")
        if type(self.sequence) is not int or self.sequence < 0:
            raise TaskSpecError("evidence sequence must be a nonnegative integer")


def task_spec_from_dict(payload: object) -> TaskSpec:
    """Decode the versioned JSON-compatible schema; reject unknown fields."""
    from .search import Goal

    data = _mapping(payload, "task")
    _keys(data, {"id", "version", "text", "goal", "obligations", "always_no_death"}, "task",
          required={"id", "version", "text", "goal", "obligations"})
    goal_data = _mapping(data["goal"], "goal")
    _keys(goal_data, {"required", "forbidden"}, "goal", required={"required", "forbidden"})
    goal = Goal(
        required=frozenset(_parse_atom(atom, "goal.required") for atom in _list(goal_data["required"], "goal.required")),
        forbidden=frozenset(_parse_atom(atom, "goal.forbidden") for atom in _list(goal_data["forbidden"], "goal.forbidden")),
    )
    obligations: list[Obligation] = []
    for index, raw in enumerate(_list(data["obligations"], "obligations")):
        label = f"obligations[{index}]"
        item = _mapping(raw, label)
        kind = item.get("type")
        if kind == "eventually":
            _keys(item, {"type", "event"}, label, required={"type", "event"})
            obligations.append(Eventually(_event_value(item["event"], label)))
        elif kind == "in_order":
            _keys(item, {"type", "events"}, label, required={"type", "events"})
            events = tuple(_event_value(event, label) for event in _list(item["events"], f"{label}.events"))
            if not events:
                raise TaskSpecError(f"{label}.events must not be empty")
            obligations.append(InOrder(events))
        elif kind == "never":
            _keys(item, {"type", "event"}, label, required={"type", "event"})
            obligations.append(Never(_event_value(item["event"], label)))
        elif kind == "max_count":
            _keys(item, {"type", "event", "maximum"}, label,
                  required={"type", "event", "maximum"})
            maximum = item["maximum"]
            if type(maximum) is not int or maximum < 1:
                raise TaskSpecError(f"{label}.maximum must be a positive integer")
            obligations.append(MaxCount(_event_value(item["event"], label), maximum))
        else:
            raise TaskSpecError(f"{label}.type is not a registered obligation")
    no_death = data.get("always_no_death", False)
    if type(no_death) is not bool:
        raise TaskSpecError("always_no_death must be a boolean")
    return TaskSpec(data["id"], data["version"], data["text"], goal,
                    tuple(obligations), no_death)


def task_spec_to_dict(task: TaskSpec) -> dict[str, object]:
    """Serialize a task without changing its original natural-language text."""
    from .search import Goal

    _validate_goal(task.goal)
    goal: Goal = task.goal
    serialized: list[dict[str, object]] = []
    for obligation in task.obligations:
        _validate_obligation(obligation)
        if isinstance(obligation, Eventually):
            serialized.append({"type": "eventually", "event": obligation.event})
        elif isinstance(obligation, InOrder):
            serialized.append({"type": "in_order", "events": list(obligation.events)})
        elif isinstance(obligation, Never):
            serialized.append({"type": "never", "event": obligation.event})
        else:
            serialized.append({"type": "max_count", "event": obligation.event,
                               "maximum": obligation.maximum})
    return {
        "id": task.id,
        "version": task.version,
        "text": task.text,
        "goal": {
            "required": [list(atom) for atom in sorted(goal.required)],
            "forbidden": [list(atom) for atom in sorted(goal.forbidden)],
        },
        "obligations": serialized,
        "always_no_death": task.always_no_death,
    }


def _validate_goal(goal: object) -> None:
    from .search import Goal

    if not isinstance(goal, Goal):
        raise TaskSpecError("goal must be a Goal instance")
    if not hasattr(goal, "required") or not hasattr(goal, "forbidden"):
        raise TaskSpecError("goal must use the registered Goal contract")
    for field in ("required", "forbidden"):
        atoms = getattr(goal, field)
        if not isinstance(atoms, (set, frozenset)):
            raise TaskSpecError(f"goal.{field} must be a set of atoms")
        for atom in atoms:
            _validate_atom(atom, f"goal.{field}")
    if goal.required & goal.forbidden:
        raise TaskSpecError("goal cannot both require and forbid the same atom")


def _validate_atom(atom: object, label: str) -> None:
    from ..open_adventure_planning_v0.domain import CARRIED, OBJECTS, ROOMS

    if not isinstance(atom, tuple) or not atom or any(not isinstance(part, str) for part in atom):
        raise TaskSpecError(f"{label} atom must be a tuple of strings")
    predicate, *args = atom
    if predicate == "at":
        if len(args) != 2:
            raise TaskSpecError(f"{label} at atom must have two arguments")
        subject, location = args
        valid_subject = subject == "player" or subject in OBJECTS
        valid_location = location in ROOMS or (subject in OBJECTS and location == CARRIED)
        if not valid_subject or not valid_location:
            raise TaskSpecError(f"{label} at atom is outside the finite domain")
    elif predicate == "carrying":
        if len(args) != 1 or args[0] not in OBJECTS:
            raise TaskSpecError(f"{label} carrying atom is outside the finite domain")
    elif predicate in {"lamp_on", "lamp_off", "grate_open", "grate_closed", "bridge", "unbridged"}:
        if args:
            raise TaskSpecError(f"{label} {predicate} atom takes no arguments")
    else:
        raise TaskSpecError(f"{label} predicate {predicate!r} is not registered")


def _parse_atom(value: object, label: str) -> Atom:
    raw = _list(value, label)
    atom = tuple(raw)
    _validate_atom(atom, label)
    return atom


def _validate_obligation(obligation: object) -> None:
    if isinstance(obligation, (Eventually, Never)):
        _validate_event(obligation.event)
    elif isinstance(obligation, InOrder):
        if not isinstance(obligation.events, tuple) or not obligation.events:
            raise TaskSpecError("InOrder.events must be a non-empty tuple")
        for event in obligation.events:
            _validate_event(event)
    elif isinstance(obligation, MaxCount):
        _validate_event(obligation.event)
        if type(obligation.maximum) is not int or obligation.maximum < 1:
            raise TaskSpecError("MaxCount.maximum must be a positive integer")
    else:
        raise TaskSpecError("obligation is not a registered type")


def _validate_event(event: object) -> None:
    if not isinstance(event, str) or event not in EVENTS:
        raise TaskSpecError(f"event {event!r} is not registered")


def _event_value(value: object, label: str) -> str:
    _validate_event(value)
    return value  # type: ignore[return-value]


def _nonempty(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TaskSpecError(f"{label} must be a non-empty string")


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TaskSpecError(f"{label} must be an object with string keys")
    return value


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise TaskSpecError(f"{label} must be an array")
    return value


def _keys(data: dict[str, object], allowed: set[str], label: str,
          *, required: set[str]) -> None:
    unknown = set(data) - allowed
    missing = required - set(data)
    if unknown:
        raise TaskSpecError(f"{label} has unknown fields: {sorted(unknown)}")
    if missing:
        raise TaskSpecError(f"{label} is missing fields: {sorted(missing)}")
