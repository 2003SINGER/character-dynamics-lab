"""Small executable reference monitor with explicit uncertainty and witnesses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any

from .ast import (And, AnchorKind, Compare, CompareValue, Constraint, EnumTransitionSequence,
                  EventCount, EventOrder, Formula, Not, NumericBand, NumericLiteral, Or,
                  SequenceMode, TemporalConstraint, TemporalOp, TimeWeightedMeanDifference)
from .compiler import compile_constraint
from .trace import Event, Point, Segment, Trace
from .types import MissingPolicy, Registry, StableEntity, TimeMode, ValueKind, ValueRef


class Verdict(str, Enum):
    NOT_ACTIVATED = "NOT_ACTIVATED"
    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class MonitorResult:
    constraint_id: str
    verdict: Verdict
    reason: str
    witness: Any = None
    dependencies: tuple[Any, ...] = ()
    activation_id: str | None = None
    margin: tuple[Fraction, str] | None = None


def _tri(formula: Formula, at: Fraction, trace: Trace, registry: Registry) -> bool | None:
    if isinstance(formula, CompareValue):
        entry=registry.resolve(formula.ref.observable_id,formula.ref.version)
        deleted=any(isinstance(v,StableEntity) and (v.deleted or trace.is_tombstoned(v.stable_id,at)) for v in formula.ref.args.values())
        if deleted:
            return _cmp(False,formula.op,formula.value) if entry.missing_policy is MissingPolicy.EXISTS_FALSE and entry.value.kind is ValueKind.BOOL else None
        hits = [p for p in trace.values(formula.ref) if p.time == at]
        if not hits and registry.resolve(formula.ref.observable_id,formula.ref.version).time_mode.value == "PIECEWISE_CONSTANT":
            prior=[p for p in trace.values(formula.ref) if p.time < at]
            seal=trace.values_sealed_through(formula.ref)
            if prior and seal is not None and seal>=at: hits=[prior[-1]]
        if not hits:
            for s in trace.segments:
                if s.ref == formula.ref and s.start <= at <= s.end and s.kind == "POLYNOMIAL":
                    value = s.value(at); return _cmp(value, formula.op, formula.value)
            return None
        return _cmp(hits[-1].value, formula.op, formula.value)
    if isinstance(formula, Not):
        v = _tri(formula.child, at, trace, registry); return None if v is None else not v
    if isinstance(formula, And):
        vals = [_tri(c, at, trace, registry) for c in formula.children]
        if False in vals: return False
        return None if None in vals else True
    if isinstance(formula, Or):
        vals = [_tri(c, at, trace, registry) for c in formula.children]
        if True in vals: return True
        return None if None in vals else False
    raise TypeError(f"unsupported formula node {type(formula).__name__}")


def _cmp(actual: Any, op: Compare, expected: Any) -> bool:
    if isinstance(expected, NumericLiteral): expected = expected.value
    if op is Compare.EQ: return actual == expected
    if op is Compare.LE: return Fraction(str(actual)) <= expected
    if op is Compare.GE: return Fraction(str(actual)) >= expected
    if op is Compare.IN: return actual in expected
    raise ValueError(op)


def _anchor_time(c: Constraint, trace: Trace) -> tuple[Fraction | None, Event | None]:
    anchor = getattr(c, "anchor", None)
    if anchor is None or anchor.kind is AnchorKind.SCENARIO_START:
        return trace.scenario_start, None
    if anchor.kind is AnchorKind.FIXED_ABSOLUTE:
        return anchor.absolute_time, None
    matches = trace.matching_events(anchor.event_type or "", anchor.event_filter,anchor.event_version)
    return (matches[0].time, matches[0]) if matches else (None, None)


def _instances(c: Constraint, trace: Trace) -> list[tuple[Fraction, str | None, Event | None]]:
    trigger = getattr(c, "trigger", None)
    if trigger is not None:
        events = trace.matching_events(trigger.event_type, trigger.event_filter,trigger.event_version)
        if not events: return []
        events = events[:1] if trigger.occurrence.value == "FIRST" else events
        return [(e.time, e.event_id, e) for e in events]
    base, event = _anchor_time(c, trace)
    if base is None: return []
    return [(base, event.event_id if event else None, event)]


def _window_abs(window, base):
    return (base + window.start, base + window.end)


def _earlier_witness(current: Fraction | None, candidate: Fraction | None) -> Fraction | None:
    if candidate is None:
        return current
    return candidate if current is None else min(current, candidate)


def _temporal_one(c: TemporalConstraint, trace: Trace, registry: Registry, base: Fraction,
                  activation: str | None) -> MonitorResult:
    left, right = _window_abs(c.window, base)
    if left>trace.now and c.op is not TemporalOp.AT:
        return MonitorResult(c.constraint_id,Verdict.PENDING,"entire temporal window is in the future",None,tuple(compile_constraint(c,registry).dependencies),activation)
    open_times = {p.time for p in trace.points if left <= p.time <= min(right, trace.now)}
    if left <= trace.now: open_times.add(left)
    if right <= trace.now: open_times.add(right)
    for seg in trace.segments:
        if seg.start <= trace.now and seg.end >= left:
            open_times.update((max(left, seg.start), min(right, seg.end)))
    times = sorted(t for t in open_times if t <= trace.now and c.window.contains(t-base))
    vals = [(t, _tri(c.formula, t, trace, registry)) for t in times]
    deps = tuple(compile_constraint(c, registry).dependencies)
    refs = {n.ref.dependency_key:n.ref for n in _walk(c.formula) if isinstance(n,CompareValue)}
    continuous = any(registry.resolve(r.observable_id, r.version).time_mode.value in ("CERTIFIED_POLYNOMIAL", "INTERVAL_BOUNDS") for r in refs.values())
    step_refs=[r for r in refs.values() if registry.resolve(r.observable_id,r.version).time_mode is TimeMode.PIECEWISE_CONSTANT]
    continuous_witness = None
    continuous_counterexample = None
    continuous_unknown = False
    atom = c.formula if isinstance(c.formula, CompareValue) else None
    if atom is not None and atom.op in (Compare.LE, Compare.GE) and isinstance(atom.value, NumericLiteral):
        threshold = atom.value.value
        for seg in trace.segments:
            if seg.ref != atom.ref: continue
            a, b = max(left, seg.start), min(right, seg.end, trace.now)
            if a > b: continue
            if seg.kind == "POLYNOMIAL": lo, hi = seg.extrema(a, b)
            else: lo, hi = seg.lower, seg.upper
            vertex = None
            if seg.kind == "POLYNOMIAL" and len(seg.coefficients) == 3 and seg.coefficients[2] != 0:
                candidate = seg.start - seg.coefficients[1] / (2 * seg.coefficients[2])
                if a < candidate < b: vertex = candidate
            if atom.op is Compare.LE:
                if seg.kind == "BOUNDS":
                    if hi <= threshold: continuous_witness = _earlier_witness(continuous_witness, a)
                    if lo > threshold: continuous_counterexample = _earlier_witness(continuous_counterexample, a)
                    if lo <= threshold < hi: continuous_unknown = True
                else:
                    candidates=[a,b,(a+b)/2]+([vertex] if vertex is not None else [])
                    witness=next((t for t in candidates if c.window.contains(t-base) and seg.value(t)<=threshold),None)
                    counterexample=next((t for t in candidates if c.window.contains(t-base) and seg.value(t)>threshold),None)
                    continuous_witness = _earlier_witness(continuous_witness, witness)
                    continuous_counterexample = _earlier_witness(continuous_counterexample, counterexample)
            else:
                if seg.kind == "BOUNDS":
                    if lo >= threshold: continuous_witness = _earlier_witness(continuous_witness, a)
                    if hi < threshold: continuous_counterexample = _earlier_witness(continuous_counterexample, a)
                    if lo < threshold <= hi: continuous_unknown = True
                else:
                    candidates=[a,b,(a+b)/2]+([vertex] if vertex is not None else [])
                    witness=next((t for t in candidates if c.window.contains(t-base) and seg.value(t)>=threshold),None)
                    counterexample=next((t for t in candidates if c.window.contains(t-base) and seg.value(t)<threshold),None)
                    continuous_witness = _earlier_witness(continuous_witness, witness)
                    continuous_counterexample = _earlier_witness(continuous_counterexample, counterexample)
    if c.op is TemporalOp.AT:
        at = left
        val = _tri(c.formula, at, trace, registry) if at <= trace.now else None
        if val is True: verdict, reason, witness = Verdict.SATISFIED, "predicate true at anchored time", at
        elif val is False: verdict, reason, witness = Verdict.VIOLATED, "predicate false at anchored time", at
        else: verdict, reason, witness = (Verdict.PENDING, "anchored time is in the future", at) if at > trace.now else (Verdict.INDETERMINATE, "anchored value missing", at)
        return MonitorResult(c.constraint_id, verdict, reason, witness, deps, activation)
    if c.op is TemporalOp.EVENTUALLY:
        hit = next(((t, v) for t, v in vals if v is True), None)
        if hit is None and continuous_witness is not None:
            hit = (continuous_witness, True)
        if hit:
            return MonitorResult(c.constraint_id, Verdict.SATISFIED, "pointwise witness", hit[0], deps, activation)
        observed_end=min(right,trace.now)
        if any(trace.values_sealed_through(ref) is None or trace.values_sealed_through(ref)<observed_end for ref in step_refs):
            return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"piecewise-constant signal prefix is not sealed complete",None,deps,activation)
        if continuous:
            for ref in refs.values():
                cursor=left
                for a,b in sorted((max(left,s.start),min(observed_end,s.end)) for s in trace.segments if s.ref==ref and s.end>left and s.start<observed_end):
                    if a>cursor: return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"continuous prefix has an uncertified gap",None,deps,activation)
                    cursor=max(cursor,b)
                if cursor<observed_end and observed_end>left:
                    return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"continuous prefix lacks a certificate",None,deps,activation)
        complete = trace.now >= right
        if not vals or any(v is None for _, v in vals) or (continuous and not continuous_witness and not continuous_counterexample and continuous_unknown):
            return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "completed window contains missing relevant value", deps, deps, activation)
        if complete:
            return MonitorResult(c.constraint_id, Verdict.VIOLATED, "no witness in completed window", (left, right), deps, activation)
        return MonitorResult(c.constraint_id, Verdict.PENDING, "eventuality window has future remaining", None, deps, activation)
    # ALWAYS: false point is a counterexample; unknown can be masked by it.
    bad = next(((t, v) for t, v in vals if v is False), None)
    if bad is None and continuous_counterexample is not None:
        bad = (continuous_counterexample, False)
    if bad:
        return MonitorResult(c.constraint_id, Verdict.VIOLATED, "pointwise counterexample", bad[0], deps, activation)
    observed_end=min(right,trace.now)
    if any(trace.values_sealed_through(ref) is None or trace.values_sealed_through(ref)<observed_end for ref in step_refs):
        return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"piecewise-constant signal prefix is not sealed complete",None,deps,activation)
    if any(v is None for _,v in vals) or continuous_unknown:
        return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"relevant past value or interval is unknown",None,deps,activation)
    if continuous:
        observed_end=min(right,trace.now)
        for ref in refs.values():
            cursor=left
            for a,b in sorted((max(left,s.start),min(observed_end,s.end)) for s in trace.segments if s.ref==ref and s.end>left and s.start<observed_end):
                if a>cursor: return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"continuous prefix has an uncertified gap",None,deps,activation)
                cursor=max(cursor,b)
            if cursor<observed_end and observed_end>left:
                return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"continuous prefix lacks a certificate",None,deps,activation)
    if trace.now < right:
        return MonitorResult(c.constraint_id, Verdict.PENDING, "always window has future remaining", None, deps, activation)
    # Endpoint samples alone cannot certify the open intervals between them.
    if continuous_unknown:
        return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "interval bounds do not determine truth throughout the window", None, deps, activation)
    if continuous:
        refset=set(refs)
        intervals = sorted((max(left,s.start), min(right,s.end)) for s in trace.segments if s.ref.dependency_key in refset and s.end >= left and s.start <= right)
        cursor=left
        for a,b in intervals:
            if a > cursor: return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "continuous certificate has a coverage gap", None, deps, activation)
            cursor=max(cursor,b)
        if cursor < right:
            return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "no complete continuous certificate for entire interval", None, deps, activation)
        if not vals or any(v is None for _,v in vals):
            return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "continuous endpoint value missing", None, deps, activation)
        return MonitorResult(c.constraint_id, Verdict.SATISFIED, "full continuous certificate proves predicate", (left,right), deps, activation)
    if any(v is None for _, v in vals):
        return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "relevant past value missing", None, deps, activation)
    if not times or times[0] > left or times[-1] < right:
        return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "discrete trace does not cover both window endpoints", None, deps, activation)
    return MonitorResult(c.constraint_id, Verdict.SATISFIED, "complete discrete window certified", (left, right), deps, activation)


def _walk(f: Formula):
    yield f
    if isinstance(f, Not): yield from _walk(f.child)
    if isinstance(f, (And, Or)):
        for c in f.children: yield from _walk(c)


def _monitor_band(c: NumericBand, trace: Trace, registry: Registry, base: Fraction, aid: str | None) -> MonitorResult:
    left, right = _window_abs(c.window, base)
    deps = tuple(compile_constraint(c, registry).dependencies)
    entry=registry.resolve(c.ref.observable_id,c.ref.version)
    stable_args=[v for v in c.ref.args.values() if isinstance(v,StableEntity)]
    if any(v.deleted for v in stable_args): return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"reference is tombstoned",None,deps,aid)
    tombstones=[trace.tombstone_times[v.stable_id] for v in stable_args if v.stable_id in trace.tombstone_times]
    deleted_at=min(tombstones) if tombstones else None
    intersects_deletion=deleted_at is not None and (left<=deleted_at<right or (deleted_at==right and c.window.right_closed))
    effective_right=min(right,deleted_at) if deleted_at is not None else right
    if deleted_at is not None and deleted_at<=left and right>=left:
        return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"stable entity is deleted at or before the constrained point",None,deps,aid)
    if left==right and entry.time_mode.value=="POINT_ONLY":
        hits=[p for p in trace.values(c.ref) if p.time==left]
        if not hits: return MonitorResult(c.constraint_id,Verdict.PENDING if left>trace.now else Verdict.INDETERMINATE,"point-only sample missing",None,deps,aid)
        value=Fraction(str(hits[-1].value))
        ok=(c.lower is None or value>=c.lower) and (c.upper is None or value<=c.upper)
        return MonitorResult(c.constraint_id,Verdict.SATISFIED if ok else Verdict.VIOLATED,"point-only band check",(left,value),deps,aid)
    if left==right:
        vals=[p.value for p in trace.values(c.ref) if p.time==left]
        if not vals:
            for s in trace.segments:
                if s.ref==c.ref and s.start<=left<=s.end:
                    if s.kind=="POLYNOMIAL": vals=[s.value(left)]
                    elif c.lower is not None and s.upper<c.lower or c.upper is not None and s.lower>c.upper:
                        return MonitorResult(c.constraint_id,Verdict.VIOLATED,"point enclosure lies outside band",(left,s.lower,s.upper),deps,aid)
        if not vals: return MonitorResult(c.constraint_id,Verdict.PENDING if left>trace.now else Verdict.INDETERMINATE,"band point missing",None,deps,aid)
        value=Fraction(str(vals[-1])); ok=(c.lower is None or value>=c.lower) and (c.upper is None or value<=c.upper)
        return MonitorResult(c.constraint_id,Verdict.SATISFIED if ok else Verdict.VIOLATED,"zero-width band point check",(left,value),deps,aid)
    covered = []
    for seg in trace.segments:
        if seg.ref != c.ref: continue
        if deleted_at is not None and seg.start>=deleted_at: continue
        a, b = max(left, seg.start), min(effective_right, seg.end, trace.now)
        if a >= b: continue
        covered.append((a, b, seg))
        if seg.kind == "POLYNOMIAL":
            lo, hi = seg.extrema(a, b)
        else:
            lo, hi = seg.lower, seg.upper
        frac_a=(a-left)/(right-left) if right>left else Fraction(0)
        frac_b=(b-left)/(right-left) if right>left else Fraction(0)
        lower_a=c.lower+(c.lower_at_end-c.lower)*frac_a if c.lower is not None and c.lower_at_end is not None else c.lower
        lower_b=c.lower+(c.lower_at_end-c.lower)*frac_b if c.lower is not None and c.lower_at_end is not None else c.lower
        upper_a=c.upper+(c.upper_at_end-c.upper)*frac_a if c.upper is not None and c.upper_at_end is not None else c.upper
        upper_b=c.upper+(c.upper_at_end-c.upper)*frac_b if c.upper is not None and c.upper_at_end is not None else c.upper
        violation_time=None; violation_value=None
        if seg.kind=="POLYNOMIAL":
            def difference_extreme(bound_a,bound_b, state_minus_bound=True):
                if bound_a is None: return None,None
                slope=(bound_b-bound_a)/(b-a) if b>a else Fraction(0)
                intercept=bound_a+slope*(seg.start-a)
                if state_minus_bound: coeff=tuple([seg.coefficients[0]-intercept, seg.coefficients[1]-slope]+list(seg.coefficients[2:]))
                else: coeff=tuple([intercept-seg.coefficients[0], slope-seg.coefficients[1]]+[-x for x in seg.coefficients[2:]])
                vals=[(a,sum(v*(a-seg.start)**i for i,v in enumerate(coeff))),(b,sum(v*(b-seg.start)**i for i,v in enumerate(coeff)))]
                vertex=None
                if len(coeff)==3 and coeff[2]!=0:
                    q=seg.start-coeff[1]/(2*coeff[2])
                    if a<q<b: vals.append((q,sum(v*(q-seg.start)**i for i,v in enumerate(coeff)))); vertex=q
                return max(vals,key=lambda x:x[1])
            if c.upper is not None:
                ex=difference_extreme(upper_a,upper_b,True)
                if ex and ex[1]>0: violation_time,violation_value=ex[0],seg.value(ex[0])
            if violation_time is None and c.lower is not None:
                ex=difference_extreme(lower_a,lower_b,False)
                if ex and ex[1]>0: violation_time,violation_value=ex[0],seg.value(ex[0])
        else:
            max_upper=max(v for v in (upper_a,upper_b) if v is not None) if upper_a is not None else None
            min_lower=min(v for v in (lower_a,lower_b) if v is not None) if lower_a is not None else None
            if max_upper is not None and lo>max_upper: violation_time,violation_value=a,(lo,hi)
            elif min_lower is not None and hi<min_lower: violation_time,violation_value=a,(lo,hi)
        if violation_time is not None:
            return MonitorResult(c.constraint_id,Verdict.VIOLATED,"certified segment lies outside band",(violation_time,violation_value),deps,aid)
    cursor = left
    unresolved = False
    for a,b,seg in sorted(covered):
        if a > cursor: unresolved = True
        cursor = max(cursor,b)
        if seg.kind == "BOUNDS" or c.lower_at_end is not None or c.upper_at_end is not None:
            frac_a=(a-left)/(right-left) if right>left else Fraction(0); frac_b=(b-left)/(right-left) if right>left else Fraction(0)
            lower_a=c.lower+(c.lower_at_end-c.lower)*frac_a if c.lower is not None and c.lower_at_end is not None else c.lower
            lower_b=c.lower+(c.lower_at_end-c.lower)*frac_b if c.lower is not None and c.lower_at_end is not None else c.lower
            upper_a=c.upper+(c.upper_at_end-c.upper)*frac_a if c.upper is not None and c.upper_at_end is not None else c.upper
            upper_b=c.upper+(c.upper_at_end-c.upper)*frac_b if c.upper is not None and c.upper_at_end is not None else c.upper
            if (c.lower is not None and (lower_a is None or seg.kind=="BOUNDS" and seg.lower<max(lower_a,lower_b))) or (c.upper is not None and (upper_a is None or seg.kind=="BOUNDS" and seg.upper>min(upper_a,upper_b))): unresolved=True
    if cursor < min(right,trace.now): unresolved = True
    if trace.now < right:
        return MonitorResult(c.constraint_id, Verdict.PENDING, "band window has future remaining", None, deps, aid)
    if intersects_deletion:
        return MonitorResult(c.constraint_id,Verdict.INDETERMINATE,"stable entity was deleted during the constrained window",None,deps,aid)
    if unresolved:
        return MonitorResult(c.constraint_id, Verdict.INDETERMINATE, "coverage or interval bound cannot certify band", None, deps, aid)
    return MonitorResult(c.constraint_id, Verdict.SATISFIED, "certified full-window band", (left,right), deps, aid)


def _mean(c: TimeWeightedMeanDifference, trace: Trace) -> tuple[Fraction | None, str, Verdict | None]:
    duration = c.end - c.start
    if duration <= 0: return None, "zero-duration window",Verdict.INDETERMINATE
    if trace.now<=c.start: return None,"window is entirely in future",Verdict.PENDING
    covered_end=min(c.end,trace.now)
    parts = [s for s in trace.segments if s.ref == c.ref and s.kind == "POLYNOMIAL" and s.start < covered_end and s.end > c.start]
    cursor, integral = c.start, Fraction(0)
    for seg in sorted(parts, key=lambda s:s.start):
        a,b=max(c.start,seg.start),min(covered_end,seg.end)
        if a > cursor: return None, "uncovered historical integration interval",Verdict.INDETERMINATE
        if b > cursor:
            integral += seg.integral(max(cursor,a),b); cursor=b
    if cursor<covered_end: return None,"uncovered historical integration interval",Verdict.INDETERMINATE
    if trace.now<c.end: return None,"window has future integration duration",Verdict.PENDING
    return integral/duration,"ok",None


def evaluate(constraint: Constraint, trace: Trace, registry: Registry) -> list[MonitorResult]:
    """Evaluate a compiled constraint; EACH triggers return distinct instances."""
    compile_constraint(constraint, registry)
    selectors=[]
    trigger=getattr(constraint,"trigger",None)
    if trigger is not None: selectors.append((trigger.event_type,trigger.event_version,trigger.event_filter))
    anchor=getattr(constraint,"anchor",None)
    if anchor is not None and anchor.kind is AnchorKind.EVENT_INSTANCE: selectors.append((anchor.event_type,anchor.event_version,anchor.event_filter))
    if isinstance(constraint,EventCount): selectors.append((constraint.event_type,constraint.event_version,constraint.event_filter))
    if isinstance(constraint,EventOrder): selectors.extend(((constraint.before_type,constraint.before_version,constraint.before_filter),(constraint.after_type,constraint.after_version,constraint.after_filter)))
    for event_type,version,_filters in selectors:
        entry=registry.resolve(event_type,version)
        for event in trace.events:
            if event.event_type!=event_type: continue
            if event.version!=version: raise ValueError(f"event version mismatch for pinned selector {event_type}@{version}")
            if set(event.args)!=set(entry.args): raise ValueError(f"event payload schema mismatch for {event_type}@{version}")
            for name,expected in entry.args.items():
                value=event.args[name]
                actual=value.entity_type if isinstance(value,StableEntity) else type(value).__name__
                if actual!=expected: raise TypeError(f"event payload {name} expects {expected}, got {actual}")
            if event.provenance!="committed_ledger":
                raise ValueError(f"event selector {event_type}@{version} requires committed-ledger provenance")
    refs=[]
    if isinstance(constraint,TemporalConstraint): refs=[n.ref for n in _walk(constraint.formula) if isinstance(n,CompareValue)]
    elif isinstance(constraint,(NumericBand,TimeWeightedMeanDifference,EnumTransitionSequence)): refs=[constraint.ref]
    for ref in refs:
        ent=registry.resolve(ref.observable_id,ref.version)
        matching_segments=[seg for seg in trace.segments if seg.ref==ref]
        if ent.value.kind is not ValueKind.REAL and matching_segments:
            raise TypeError(f"{ent.value.kind.value} observables cannot carry numeric segments")
        if ent.time_mode is TimeMode.EVENT and trace.values(ref):
            raise TypeError("EVENT observables cannot carry state points")
        if ent.time_mode is TimeMode.POINT_ONLY and matching_segments:
            raise TypeError("POINT_ONLY observables cannot carry interval segments")
        if ent.time_mode is TimeMode.INTERVAL_BOUNDS and any(seg.kind!="BOUNDS" for seg in matching_segments):
            raise TypeError("INTERVAL_BOUNDS observables accept only interval-bound certificates")
        if ent.time_mode is TimeMode.PIECEWISE_CONSTANT:
            for seg in matching_segments:
                if seg.kind=="POLYNOMIAL" and any(v!=0 for v in seg.coefficients[1:]):
                    raise ValueError("piecewise-constant REAL certificates must have degree zero")
                if seg.kind=="BOUNDS" and seg.lower!=seg.upper:
                    raise ValueError("piecewise-constant REAL bounds must be singleton values")
        for point in trace.values(ref):
            value=point.value
            if ent.value.kind is ValueKind.REAL:
                if isinstance(value,bool): raise TypeError("REAL point cannot be bool")
                numeric=Fraction(str(value))
                if numeric<ent.value.lower or numeric>ent.value.upper: raise ValueError("trace value outside registered REAL domain")
            elif ent.value.kind is ValueKind.BOOL and type(value) is not bool: raise TypeError("BOOL point requires bool")
            elif ent.value.kind is ValueKind.ENUM and value not in ent.value.enum_values: raise ValueError("trace enum value outside registered domain")
        if ent.value.kind is ValueKind.REAL:
            for seg in trace.segments:
                if seg.ref!=ref: continue
                lo,hi=seg.extrema(seg.start,seg.end) if seg.kind=="POLYNOMIAL" else (seg.lower,seg.upper)
                if lo<ent.value.lower or hi>ent.value.upper: raise ValueError("segment certificate outside registered REAL domain")
    instances = _instances(constraint, trace)
    if not instances:
        if getattr(constraint, "trigger", None) is not None or (getattr(getattr(constraint,"anchor",None),"kind",None) is AnchorKind.EVENT_INSTANCE):
            if trace.events_sealed_through is not None and trace.events_sealed_through>=trace.now:
                return [MonitorResult(constraint.constraint_id, Verdict.NOT_ACTIVATED, "no matching event in complete ledger prefix")]
            return [MonitorResult(constraint.constraint_id,Verdict.INDETERMINATE,"event prefix is incomplete; activation is unknown")]
        return [MonitorResult(constraint.constraint_id, Verdict.INDETERMINATE, "anchor unavailable")]
    out = []
    for base, aid, event in instances:
        if event is not None and (trace.events_sealed_through is None or trace.events_sealed_through<event.time):
            result=MonitorResult(constraint.constraint_id,Verdict.INDETERMINATE,"ledger prefix is not complete through selected activation",None,(),aid)
        elif isinstance(constraint, TemporalConstraint):
            result = _temporal_one(constraint, trace, registry, base, aid)
        elif isinstance(constraint, NumericBand):
            result = _monitor_band(constraint, trace, registry, base, aid)
        elif isinstance(constraint, EventCount):
            lo,hi=_window_abs(constraint.window,base)
            ev=[e for e in trace.matching_events(constraint.event_type,constraint.event_filter,constraint.event_version) if constraint.window.contains(e.time-base)]
            if constraint.maximum is not None and len(ev)>constraint.maximum:
                result=MonitorResult(constraint.constraint_id,Verdict.VIOLATED,"event count exceeded maximum",tuple(e.event_id for e in ev),(),aid)
            elif len(ev)>=constraint.minimum and constraint.maximum is None:
                result=MonitorResult(constraint.constraint_id,Verdict.SATISFIED,"event count within bounds",tuple(e.event_id for e in ev),(),aid)
            elif len(ev)>=constraint.minimum and constraint.maximum is not None and trace.now>=hi and trace.events_sealed_through is not None and trace.events_sealed_through>=hi:
                result=MonitorResult(constraint.constraint_id,Verdict.SATISFIED,"completed event count within bounds",tuple(e.event_id for e in ev),(),aid)
            elif trace.now>=hi and trace.events_sealed_through is not None and trace.events_sealed_through>=hi:
                v=Verdict.VIOLATED if len(ev)<constraint.minimum or (constraint.maximum is not None and len(ev)>constraint.maximum) else Verdict.SATISFIED
                result=MonitorResult(constraint.constraint_id,v,"completed event-count window",tuple(e.event_id for e in ev),(),aid)
            elif trace.events_sealed_through is None or trace.events_sealed_through<min(trace.now,hi):
                result=MonitorResult(constraint.constraint_id,Verdict.INDETERMINATE,"event ledger prefix is incomplete",None,(),aid)
            else: result=MonitorResult(constraint.constraint_id,Verdict.PENDING,"event-count window has future remaining",None,(),aid)
        elif isinstance(constraint, EventOrder):
            before=trace.matching_events(constraint.before_type,constraint.before_filter,constraint.before_version); after=trace.matching_events(constraint.after_type,constraint.after_filter,constraint.after_version)
            base=_anchor_time(constraint,trace)[0]
            lo,hi=_window_abs(constraint.window,base) if base is not None else (None,None)
            before=[e for e in before if lo is not None and constraint.window.contains(e.time-base)]
            after=[e for e in after if lo is not None and constraint.window.contains(e.time-base)]
            pairs=[(a,b) for a in before for b in after if a.event_id!=b.event_id and ((a.time,a.sequence)<(b.time,b.sequence) if constraint.order.value=="EVENT_KEY" else a.time<b.time)]
            if pairs: result=MonitorResult(constraint.constraint_id,Verdict.SATISFIED,"ordered event witness",(pairs[0][0].event_id,pairs[0][1].event_id))
            elif trace.events_sealed_through is None or (lo is not None and trace.events_sealed_through<min(trace.now,hi)):
                result=MonitorResult(constraint.constraint_id,Verdict.INDETERMINATE,"event ledger prefix is incomplete")
            elif trace.now<hi: result=MonitorResult(constraint.constraint_id,Verdict.PENDING,"ordered events may still occur")
            elif trace.events_sealed_through>=hi: result=MonitorResult(constraint.constraint_id,Verdict.VIOLATED,"complete window contains no ordered distinct pair")
            else: result=MonitorResult(constraint.constraint_id,Verdict.INDETERMINATE,"no order witness in available event history")
        elif isinstance(constraint, TimeWeightedMeanDifference):
            # Store windows on the AST object rather than assuming equal sample weighting.
            class W: pass
            w1=W(); w1.ref=constraint.ref; w1.start=base+constraint.earlier.start; w1.end=base+constraint.earlier.end
            w2=W(); w2.ref=constraint.ref; w2.start=base+constraint.later.start; w2.end=base+constraint.later.end
            m1,reason1,state1=_mean(w1,trace); m2,reason2,state2=_mean(w2,trace)
            deps=tuple(compile_constraint(constraint,registry).dependencies)
            if m1 is None or m2 is None:
                state=Verdict.INDETERMINATE if Verdict.INDETERMINATE in (state1,state2) else Verdict.PENDING
                result=MonitorResult(constraint.constraint_id,state,reason1 if m1 is None else reason2,None,deps,aid)
            else:
                d=m1-m2
                v=Verdict.SATISFIED if d>=constraint.minimum_difference else Verdict.VIOLATED
                result=MonitorResult(constraint.constraint_id,v,"exact duration-weighted mean difference",(m1,m2),deps,aid,(d-constraint.minimum_difference,constraint.unit))
        elif isinstance(constraint, EnumTransitionSequence):
            left=base+constraint.window.start
            pts=[p for p in trace.values(constraint.ref) if constraint.window.contains(p.time-base)]
            entry=registry.resolve(constraint.ref.observable_id,constraint.ref.version)
            if entry.time_mode.value=="PIECEWISE_CONSTANT":
                prior=[p for p in trace.values(constraint.ref) if p.time<=left]
                if prior and (not pts or pts[0].time>left): pts.insert(0,prior[-1])
                elif prior and pts and pts[0].time==left and prior[-1] not in pts: pts.insert(0,prior[-1])
            states=[]
            for p in pts:
                if not states or states[-1]!=p.value: states.append(p.value)
            if constraint.mode is SequenceMode.EXACT: ok=tuple(states)==constraint.states
            else:
                it=iter(states); ok=all(any(x==target for x in it) for target in constraint.states)
            if ok and constraint.mode is SequenceMode.ORDERED_SUBSEQUENCE: v=Verdict.SATISFIED
            elif trace.now<left: v=Verdict.PENDING
            elif constraint.mode is SequenceMode.EXACT or not ok:
                seal=trace.values_sealed_through(constraint.ref)
                if seal is None or seal<min(trace.now,base+constraint.window.end): v=Verdict.INDETERMINATE
                elif ok and trace.now>=base+constraint.window.end: v=Verdict.SATISFIED
                elif trace.now<base+constraint.window.end: v=Verdict.PENDING
                else: v=Verdict.VIOLATED if pts else Verdict.INDETERMINATE
            elif ok and trace.now>=base+constraint.window.end: v=Verdict.SATISFIED
            elif trace.now < base+constraint.window.end: v=Verdict.PENDING
            else: v=Verdict.VIOLATED if pts else Verdict.INDETERMINATE
            result=MonitorResult(constraint.constraint_id,v,"enum transition sequence evaluation",tuple(states),tuple(compile_constraint(constraint,registry).dependencies),aid)
        else:
            raise TypeError(type(constraint))
        out.append(result)
    return out


class MonitorSession:
    """Isolated bookkeeping wrapper; checkpoint covers monitor IDs only, never world state."""
    def __init__(self, registry: Registry, seen: frozenset[tuple[str,str]] = frozenset()):
        self.registry=registry
        self._seen=set(seen)

    def evaluate(self, constraint: Constraint, trace: Trace) -> list[MonitorResult]:
        results=evaluate(constraint,trace,self.registry)
        for result in results:
            self._seen.add((result.constraint_id,result.activation_id or "@unanchored"))
        return results

    def checkpoint(self) -> frozenset[tuple[str,str]]:
        return frozenset(self._seen)

    def fork(self) -> "MonitorSession":
        return MonitorSession(self.registry,self.checkpoint())
