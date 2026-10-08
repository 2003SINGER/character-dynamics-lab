"""Exact time, typed registry contracts, and value references for V0."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Mapping


def exact_time(value: int | str | Fraction) -> Fraction:
    """Parse simulation minutes exactly. Floats and bools are deliberately rejected."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("time must be an int, decimal string, or Fraction")
    result = value if isinstance(value, Fraction) else Fraction(value)
    return result


class Owner(str, Enum):
    WORLD = "WORLD"
    ACTOR_O = "ACTOR_O"
    ACTOR_S = "ACTOR_S"
    LEDGER = "LEDGER"


class ValueKind(str, Enum):
    BOOL = "BOOL"
    ENUM = "ENUM"
    REAL = "REAL"
    SET = "SET"
    EVENT = "EVENT"


class TimeMode(str, Enum):
    POINT_ONLY = "POINT_ONLY"
    PIECEWISE_CONSTANT = "PIECEWISE_CONSTANT"
    CERTIFIED_POLYNOMIAL = "CERTIFIED_POLYNOMIAL"
    INTERVAL_BOUNDS = "INTERVAL_BOUNDS"
    EVENT = "EVENT"


class MissingPolicy(str, Enum):
    INDETERMINATE = "INDETERMINATE"
    EXISTS_FALSE = "EXISTS_FALSE"


@dataclass(frozen=True, order=True)
class StableEntity:
    entity_type: str
    stable_id: str
    display_name: str = field(default="", compare=False)
    deleted: bool = field(default=False, compare=False)


@dataclass(frozen=True)
class TypeSpec:
    kind: ValueKind
    unit: str | None = None
    enum_values: tuple[str, ...] = ()
    element_type: str | None = None
    lower: Fraction | None = None
    upper: Fraction | None = None

    def __post_init__(self):
        object.__setattr__(self,"enum_values",tuple(self.enum_values))
        if self.kind is ValueKind.REAL:
            if self.unit is None or self.lower is None or self.upper is None:
                raise ValueError("REAL requires explicit unit and bounded domain")
            object.__setattr__(self, "lower", Fraction(str(self.lower)))
            object.__setattr__(self, "upper", Fraction(str(self.upper)))
            if self.lower > self.upper: raise ValueError("REAL domain lower exceeds upper")


@dataclass(frozen=True)
class RegistryEntry:
    observable_id: str
    version: str
    owner: Owner
    subject_type: str
    args: Mapping[str, str]
    value: TypeSpec
    evaluator_id: str
    reads: tuple[str, ...]
    time_mode: TimeMode
    missing_policy: MissingPolicy = MissingPolicy.INDETERMINATE
    model_pin: str | None = None

    def __post_init__(self):
        object.__setattr__(self,"args",MappingProxyType(dict(self.args)))
        object.__setattr__(self,"reads",tuple(self.reads))


@dataclass(frozen=True)
class ValueRef:
    observable_id: str
    version: str
    args: Mapping[str, Any]
    expected_owner: Owner | None = None

    def __post_init__(self):
        object.__setattr__(self,"args",MappingProxyType(dict(self.args)))

    @property
    def dependency_key(self) -> tuple[str, str, tuple[tuple[str, str], ...]]:
        args = tuple(sorted((k, stable_key(v)) for k, v in self.args.items()))
        return (self.observable_id, self.version, args)


def stable_key(value: Any) -> str:
    if isinstance(value, StableEntity):
        return f"{value.entity_type}:{value.stable_id}"
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    return str(value)


class Registry:
    """Immutable-version registry. Re-registering a pinned key is forbidden."""
    def __init__(self, entries: tuple[RegistryEntry, ...] = ()) -> None:
        self._entries: dict[tuple[str, str], RegistryEntry] = {}
        for entry in entries:
            self.add(entry)

    def add(self, entry: RegistryEntry) -> None:
        key = (entry.observable_id, entry.version)
        if key in self._entries:
            raise ValueError(f"registry version already pinned: {key}")
        if not entry.observable_id or not entry.version or not entry.evaluator_id:
            raise ValueError("observable id, version, and evaluator id are required")
        from .evaluation import EVALUATOR_DISPATCH
        if entry.evaluator_id not in EVALUATOR_DISPATCH:
            raise ValueError(f"evaluator is not allowlisted: {entry.evaluator_id}")
        if entry.value.kind is ValueKind.ENUM and not entry.value.enum_values:
            raise ValueError("enum registry entries require a nonempty domain")
        if entry.missing_policy is MissingPolicy.EXISTS_FALSE and entry.value.kind is not ValueKind.BOOL:
            raise ValueError("EXISTS_FALSE is only defined for boolean existence observables")
        self._entries[key] = entry

    def resolve(self, observable_id: str, version: str) -> RegistryEntry:
        try:
            return self._entries[(observable_id, version)]
        except KeyError as exc:
            raise KeyError(f"unknown observable or missing model/version pin: {observable_id}@{version}") from exc

    def entries(self) -> tuple[RegistryEntry, ...]:
        return tuple(self._entries[k] for k in sorted(self._entries))

    def to_json(self) -> dict[str, Any]:
        return {"entries": [
            {"observable_id": e.observable_id, "version": e.version, "owner": e.owner.value,
             "subject_type": e.subject_type, "args": dict(sorted(e.args.items())),
             "value": {"kind": e.value.kind.value, "unit": e.value.unit,
                       "enum_values": list(e.value.enum_values), "element_type": e.value.element_type,
                       "lower": str(e.value.lower) if e.value.lower is not None else None,
                       "upper": str(e.value.upper) if e.value.upper is not None else None},
             "evaluator_id": e.evaluator_id, "reads": list(e.reads), "time_mode": e.time_mode.value,
             "missing_policy": e.missing_policy.value, "model_pin": e.model_pin}
            for e in self.entries()]}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "Registry":
        entries = []
        for raw in data["entries"]:
            val = raw["value"]
            entries.append(RegistryEntry(raw["observable_id"], raw["version"], Owner(raw["owner"]),
                raw["subject_type"], dict(raw["args"]),
                TypeSpec(ValueKind(val["kind"]), val.get("unit"), tuple(val.get("enum_values", ())), val.get("element_type"), val.get("lower"), val.get("upper")),
                raw["evaluator_id"], tuple(raw["reads"]), TimeMode(raw["time_mode"]),
                MissingPolicy(raw.get("missing_policy", "INDETERMINATE")), raw.get("model_pin")))
        return cls(tuple(entries))


# Stable evaluator names map only to pure reference projectors implemented here.
ALLOWED_EVALUATORS = frozenset({
    "task_progress_fraction_v1", "world_holding_v1", "actor_belief_v1",
    "factive_observer_knows_v1", "registered_field_v1", "ledger_event_v1",
})
