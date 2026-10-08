"""Deterministic editor-to-AST compilation; prose is annotation only."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Any

from .ast import (Anchor, AnchorKind, Compare, CompareValue, EnumTransitionSequence,
                  EventCount, EventOrder, NumericBand, NumericLiteral, TemporalConstraint, TemporalOp,
                  Window, StrictOrder, SequenceMode)
from .types import ValueRef


class EnvelopeInterpretation(str, Enum):
    LINEAR = "LINEAR"
    HOLD = "HOLD"
    POINT_ONLY = "POINT_ONLY"


@dataclass(frozen=True)
class EventNode:
    event_type: str
    instance_id: str
    event_version: str = "1"


def compile_state_point(constraint_id: str, ref: ValueRef, value: Any, time: Fraction,
                        *, unit: str | None = None, annotation: str = "") -> TemporalConstraint:
    expected = NumericLiteral(Fraction(str(value)), unit) if unit is not None else value
    return TemporalConstraint(constraint_id, TemporalOp.AT, CompareValue(ref, Compare.EQ, expected),
                              Window(0, 0), Anchor(AnchorKind.FIXED_ABSOLUTE, absolute_time=time), annotation=annotation)


def compile_milestone(constraint_id: str, ref: ValueRef, value: Any, deadline: Fraction,
                      *, start: Fraction = Fraction(0), unit: str | None = None,
                      annotation: str = "") -> TemporalConstraint:
    expected = NumericLiteral(Fraction(str(value)), unit) if unit is not None else value
    return TemporalConstraint(constraint_id, TemporalOp.EVENTUALLY, CompareValue(ref, Compare.EQ, expected),
                              Window(start, deadline, True, True), Anchor(AnchorKind.SCENARIO_START), annotation=annotation)


def compile_event_point(constraint_id: str, event_type: str, time: Fraction, *, event_version: str="1") -> EventCount:
    return EventCount(constraint_id,event_type,event_version,Window(time,time),minimum=1,maximum=1)


def compile_event_milestone(constraint_id: str, event_type: str, deadline: Fraction,
                            *, start: Fraction=Fraction(0), event_version: str="1", annotation: str="") -> EventCount:
    """At least one occurrence by an inclusive deadline; annotation is non-semantic."""
    return EventCount(constraint_id,event_type,event_version,Window(start,deadline,True,True),minimum=1)


def compile_enum_sequence(constraint_id: str, ref: ValueRef, states: tuple[str, ...],
                          window: Window, *, subsequence: bool = False) -> EnumTransitionSequence:
    return EnumTransitionSequence(constraint_id, ref, states,
        SequenceMode.ORDERED_SUBSEQUENCE if subsequence else SequenceMode.EXACT, window)


def compile_event_dag(edges: tuple[tuple[EventNode, EventNode], ...], window: Window, *, strict: StrictOrder = StrictOrder.EVENT_KEY) -> tuple[EventOrder, ...]:
    """A DAG is represented as explicit order constraints; cyclic input is rejected."""
    nodes={n for edge in edges for n in edge}
    graph={n:set() for n in nodes}
    for a,b in edges: graph[a].add(b)
    visiting=set(); visited=set()
    def visit(n):
        if n in visiting: raise ValueError("event ordering graph contains a cycle")
        if n in visited: return
        visiting.add(n)
        for child in graph[n]: visit(child)
        visiting.remove(n); visited.add(n)
    for n in nodes: visit(n)
    return tuple(EventOrder(f"order:{a.instance_id}:{b.instance_id}", a.event_type, a.event_version, b.event_type, b.event_version, strict,window,
        before_filter={"event_id":a.instance_id},after_filter={"event_id":b.instance_id}) for a,b in edges)


def compile_envelope(constraint_id: str, ref: ValueRef, points: tuple[tuple[Fraction, Fraction, Fraction], ...],
                     *, unit: str, interpretation: EnvelopeInterpretation | None,
                     annotation: str = "") -> tuple[NumericBand, ...]:
    """Each row is (time, lower, upper); unspecified gaps add no constraint.

    LINEAR emits an explicit affine envelope between adjacent author points.
    HOLD emits [t_i,t_(i+1)) segments; its final control point is an end marker,
    not an additional constrained point. POINT_ONLY emits zero-width bands.
    """
    if interpretation is None:
        raise ValueError("envelope requires explicit linear/hold/point-only interpretation")
    if not points: return ()
    if len(points)==1 and interpretation is not EnvelopeInterpretation.POINT_ONLY:
        raise ValueError("a one-point envelope requires POINT_ONLY; LINEAR/HOLD need an explicit end marker")
    if any(points[i][0] >= points[i+1][0] for i in range(len(points)-1)):
        raise ValueError("envelope control times must strictly increase")
    out=[]
    if interpretation is EnvelopeInterpretation.POINT_ONLY:
        for i,(t,lo,hi) in enumerate(points):
            out.append(NumericBand(f"{constraint_id}:{i}",ref,Window(t,t),Fraction(str(lo)),Fraction(str(hi)),unit=unit))
    elif interpretation is EnvelopeInterpretation.HOLD:
        for i in range(len(points)-1):
            t,lo,hi=points[i]; end=points[i+1][0]
            out.append(NumericBand(f"{constraint_id}:{i}",ref,Window(t,end,True,False),Fraction(str(lo)),Fraction(str(hi)),unit=unit))
    else:
        for i in range(len(points)-1):
            t,lo,hi=points[i]; end,lo2,hi2=points[i+1]
            out.append(NumericBand(f"{constraint_id}:{i}",ref,Window(t,end,True,True),Fraction(str(lo)),Fraction(str(hi)),Fraction(str(lo2)),Fraction(str(hi2)),unit))
    return tuple(out)
