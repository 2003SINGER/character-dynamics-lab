"""Closed, serializable V0 temporal constraint syntax."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Mapping

from .types import ValueRef, exact_time


class Compare(str, Enum):
    EQ = "eq"
    LE = "le"
    GE = "ge"
    IN = "in"


class TemporalOp(str, Enum):
    AT = "AT"
    EVENTUALLY = "EVENTUALLY"
    ALWAYS = "ALWAYS"


class AnchorKind(str, Enum):
    SCENARIO_START = "SCENARIO_START"
    FIXED_ABSOLUTE = "FIXED_ABSOLUTE"
    EVENT_INSTANCE = "EVENT_INSTANCE"


class Occurrence(str, Enum):
    FIRST = "FIRST"
    EACH = "EACH"


class StrictOrder(str, Enum):
    EVENT_KEY = "EVENT_KEY"       # lexicographic (time, sequence)
    PHYSICAL_TIME = "PHYSICAL_TIME"  # strict t1 < t2


class SequenceMode(str, Enum):
    EXACT = "EXACT"
    ORDERED_SUBSEQUENCE = "ORDERED_SUBSEQUENCE"


@dataclass(frozen=True)
class Window:
    start: Fraction
    end: Fraction
    left_closed: bool = True
    right_closed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", exact_time(self.start))
        object.__setattr__(self, "end", exact_time(self.end))
        if self.end < self.start:
            raise ValueError("window end precedes start")
        if self.end==self.start and not (self.left_closed and self.right_closed):
            raise ValueError("zero-width empty window is not admitted")

    def contains(self, value: Fraction) -> bool:
        return (value > self.start or (self.left_closed and value == self.start)) and (
            value < self.end or (self.right_closed and value == self.end))


@dataclass(frozen=True)
class Anchor:
    kind: AnchorKind
    absolute_time: Fraction | None = None
    event_type: str | None = None
    event_version: str = "1"
    event_filter: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.event_filter is not None: object.__setattr__(self,"event_filter",MappingProxyType(dict(self.event_filter)))
        if self.absolute_time is not None:
            object.__setattr__(self, "absolute_time", exact_time(self.absolute_time))
        if self.kind is AnchorKind.FIXED_ABSOLUTE and self.absolute_time is None:
            raise ValueError("fixed absolute anchor requires explicit time")
        if self.kind is AnchorKind.EVENT_INSTANCE and not self.event_type:
            raise ValueError("event-instance anchor requires event_type")


class Formula:
    """Marker for closed pointwise formula nodes."""


@dataclass(frozen=True)
class NumericLiteral:
    value: Fraction
    unit: str
    def __post_init__(self):
        object.__setattr__(self, "value", Fraction(str(self.value)))


@dataclass(frozen=True)
class CompareValue(Formula):
    ref: ValueRef
    op: Compare
    value: Any


@dataclass(frozen=True)
class Not(Formula):
    child: Formula


@dataclass(frozen=True)
class And(Formula):
    children: tuple[Formula, ...]


@dataclass(frozen=True)
class Or(Formula):
    children: tuple[Formula, ...]


@dataclass(frozen=True)
class Trigger:
    event_type: str
    event_version: str
    event_filter: Mapping[str, Any] | None = None
    occurrence: Occurrence = Occurrence.FIRST

    def __post_init__(self):
        if self.event_filter is not None: object.__setattr__(self,"event_filter",MappingProxyType(dict(self.event_filter)))


@dataclass(frozen=True)
class TemporalConstraint:
    constraint_id: str
    op: TemporalOp
    formula: Formula
    window: Window
    anchor: Anchor = Anchor(AnchorKind.SCENARIO_START)
    trigger: Trigger | None = None
    hard: bool = True
    annotation: str = ""

    def __post_init__(self):
        if self.op is TemporalOp.AT and self.window.start!=self.window.end:
            raise ValueError("AT requires a zero-width explicit time window")


@dataclass(frozen=True)
class EventCount:
    constraint_id: str
    event_type: str
    event_version: str
    window: Window
    minimum: int = 1
    maximum: int | None = None
    event_filter: Mapping[str, Any] | None = None
    anchor: Anchor = Anchor(AnchorKind.SCENARIO_START)
    trigger: Trigger | None = None
    hard: bool = True
    def __post_init__(self) -> None:
        if self.event_filter is not None: object.__setattr__(self,"event_filter",MappingProxyType(dict(self.event_filter)))
        if self.minimum < 0 or (self.maximum is not None and self.maximum < self.minimum):
            raise ValueError("invalid event count bounds")


@dataclass(frozen=True)
class EventOrder:
    constraint_id: str
    before_type: str
    before_version: str
    after_type: str
    after_version: str
    order: StrictOrder
    window: Window
    anchor: Anchor = Anchor(AnchorKind.SCENARIO_START)
    before_filter: Mapping[str, Any] | None = None
    after_filter: Mapping[str, Any] | None = None
    hard: bool = True
    def __post_init__(self):
        if self.before_filter is not None: object.__setattr__(self,"before_filter",MappingProxyType(dict(self.before_filter)))
        if self.after_filter is not None: object.__setattr__(self,"after_filter",MappingProxyType(dict(self.after_filter)))


@dataclass(frozen=True)
class NumericBand:
    constraint_id: str
    ref: ValueRef
    window: Window
    lower: Fraction | None = None
    upper: Fraction | None = None
    lower_at_end: Fraction | None = None
    upper_at_end: Fraction | None = None
    unit: str | None = None
    anchor: Anchor = Anchor(AnchorKind.SCENARIO_START)
    trigger: Trigger | None = None
    hard: bool = True
    def __post_init__(self) -> None:
        if self.lower is None and self.upper is None:
            raise ValueError("band needs at least one bound")
        if self.lower is not None:
            object.__setattr__(self, "lower", Fraction(str(self.lower)))
        if self.upper is not None:
            object.__setattr__(self, "upper", Fraction(str(self.upper)))
        if self.lower_at_end is not None: object.__setattr__(self,"lower_at_end",Fraction(str(self.lower_at_end)))
        if self.upper_at_end is not None: object.__setattr__(self,"upper_at_end",Fraction(str(self.upper_at_end)))
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("band lower exceeds upper")
        if self.lower_at_end is not None and self.upper_at_end is not None and self.lower_at_end > self.upper_at_end:
            raise ValueError("band end lower exceeds upper")


@dataclass(frozen=True)
class TimeWeightedMeanDifference:
    constraint_id: str
    ref: ValueRef
    earlier: Window
    later: Window
    minimum_difference: Fraction
    unit: str
    anchor: Anchor = Anchor(AnchorKind.SCENARIO_START)
    trigger: Trigger | None = None
    hard: bool = True
    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum_difference", Fraction(str(self.minimum_difference)))
        if self.earlier.end<=self.earlier.start or self.later.end<=self.later.start:
            raise ValueError("weighted-mean windows require positive duration")
        if max(self.earlier.start,self.later.start)<min(self.earlier.end,self.later.end):
            raise ValueError("weighted-mean windows must not overlap")


@dataclass(frozen=True)
class EnumTransitionSequence:
    constraint_id: str
    ref: ValueRef
    states: tuple[str, ...]
    mode: SequenceMode
    window: Window
    hard: bool = True
    def __post_init__(self) -> None:
        if len(self.states) < 2:
            raise ValueError("transition sequence requires at least two states")


Constraint = TemporalConstraint | EventCount | EventOrder | NumericBand | TimeWeightedMeanDifference | EnumTransitionSequence


def ast_to_json(value: Any) -> Any:
    """Tagged JSON-compatible encoding for AST, Fraction, enums and stable refs."""
    from .types import StableEntity
    if isinstance(value, Fraction):
        return {"$fraction": [value.numerator, value.denominator]}
    if isinstance(value, Enum):
        return {"$enum": [type(value).__name__, value.value]}
    if isinstance(value, StableEntity):
        return {"$entity": [value.entity_type, value.stable_id, value.display_name, value.deleted]}
    if isinstance(value, ValueRef):
        return {"$type": "ValueRef", "observable_id": value.observable_id, "version": value.version,
                "args": ast_to_json(dict(value.args)), "expected_owner": value.expected_owner.value if value.expected_owner else None}
    if isinstance(value, tuple):
        return [ast_to_json(v) for v in value]
    if isinstance(value, list):
        return [ast_to_json(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): ast_to_json(v) for k, v in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {"$type": type(value).__name__, **{k: ast_to_json(getattr(value, k)) for k in value.__dataclass_fields__}}
    return value


def ast_from_json(data: Any) -> Any:
    from .types import StableEntity
    if isinstance(data, list):
        return tuple(ast_from_json(v) for v in data)
    if not isinstance(data, dict):
        return data
    if "$fraction" in data:
        return Fraction(*data["$fraction"])
    if "$entity" in data:
        return StableEntity(*data["$entity"])
    if "$enum" in data:
        enums = {c.__name__: c for c in (Compare, TemporalOp, AnchorKind, Occurrence, StrictOrder, SequenceMode)}
        typ, val = data["$enum"]
        return enums[typ](val)
    typ = data.get("$type")
    values = {k: ast_from_json(v) for k, v in data.items() if k != "$type"}
    if typ is None:
        return values
    classes = {c.__name__: c for c in (Window, Anchor, NumericLiteral, CompareValue, Not, And, Or, Trigger, TemporalConstraint,
        EventCount, EventOrder, NumericBand, TimeWeightedMeanDifference, EnumTransitionSequence)}
    if typ == "ValueRef":
        from .types import Owner
        owner=Owner(values["expected_owner"]) if values.get("expected_owner") else None
        return ValueRef(values["observable_id"], values["version"], values["args"], owner)
    return classes[typ](**values)
