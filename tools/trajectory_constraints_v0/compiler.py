"""Strict V0 typechecker and deliberately narrow hard-conflict detector."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Any

from .ast import (And, Compare, CompareValue, Constraint, EnumTransitionSequence, EventCount,
                  EventOrder, Formula, Not, NumericBand, NumericLiteral, Or, Trigger,
                  TemporalConstraint, TimeWeightedMeanDifference)
from .types import Registry, StableEntity, ValueKind, ValueRef, stable_key


class Compatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    HARD_CONFLICT_PROVEN = "HARD_CONFLICT_PROVEN"
    COMPATIBILITY_UNKNOWN = "COMPATIBILITY_UNKNOWN"


@dataclass(frozen=True)
class CompileResult:
    constraint: Constraint
    dependencies: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...]


def _validate_ref(ref: ValueRef, registry: Registry) -> None:
    entry = registry.resolve(ref.observable_id, ref.version)
    if ref.expected_owner is not None and ref.expected_owner is not entry.owner:
        raise TypeError(f"reference owner mismatch: requested {ref.expected_owner.value}, registry owns {entry.owner.value}")
    if entry.model_pin is None and entry.owner.value == "ACTOR_S":
        raise ValueError(f"model-scoped observable lacks immutable model pin: {ref.observable_id}")
    if set(ref.args) != set(entry.args):
        raise ValueError(f"wrong argument names for {ref.observable_id}; expected {sorted(entry.args)}")
    for name, expected in entry.args.items():
        value = ref.args[name]
        actual = value.entity_type if isinstance(value, StableEntity) else type(value).__name__
        if actual != expected:
            raise TypeError(f"argument {name} expects {expected}, got {actual}")


def _validate_event(event_type:str,version:str,filters:Any,registry:Registry):
    entry=registry.resolve(event_type,version)
    if entry.owner.value!="LEDGER" or entry.value.kind is not ValueKind.EVENT or entry.time_mode.value!="EVENT":
        raise TypeError(f"event selector must pin a LEDGER EVENT: {event_type}@{version}")
    filters=filters or {}
    for name,value in filters.items():
        if name=="event_id":
            if not isinstance(value,str): raise TypeError("event_id selector must be a string")
            continue
        if name not in entry.args: raise ValueError(f"unknown event selector argument {name!r}")
        expected=entry.args[name]
        actual=value.entity_type if isinstance(value,StableEntity) else type(value).__name__
        if expected!=actual: raise TypeError(f"event argument {name} expects {expected}, got {actual}")
    return entry


def _formula_refs(formula: Formula) -> list[ValueRef]:
    if isinstance(formula, CompareValue):
        return [formula.ref]
    if isinstance(formula, Not):
        return _formula_refs(formula.child)
    if isinstance(formula, (And, Or)):
        return [r for c in formula.children for r in _formula_refs(c)]
    raise TypeError(f"unsupported formula node: {type(formula).__name__}")


def _check_formula(formula: Formula, registry: Registry) -> None:
    if isinstance(formula, CompareValue):
        _validate_ref(formula.ref, registry)
        entry = registry.resolve(formula.ref.observable_id, formula.ref.version)
        kind = entry.value.kind
        if formula.op is Compare.IN:
            if kind is not ValueKind.ENUM or not isinstance(formula.value, tuple):
                raise TypeError("in comparison requires an enum and a tuple domain")
            invalid = set(formula.value) - set(entry.value.enum_values)
            if invalid:
                raise ValueError(f"unknown enum value(s): {sorted(invalid)}")
        elif kind is ValueKind.REAL:
            if formula.op not in (Compare.EQ, Compare.LE, Compare.GE):
                raise TypeError("real supports eq/le/ge")
            if not isinstance(formula.value, NumericLiteral) or formula.value.unit != entry.value.unit:
                raise TypeError(f"numeric literal must explicitly use unit {entry.value.unit!r}")
        elif kind is ValueKind.BOOL:
            if formula.op is not Compare.EQ or not isinstance(formula.value, bool):
                raise TypeError("boolean comparisons require eq with bool")
        elif kind is ValueKind.ENUM:
            if formula.op is not Compare.EQ or formula.value not in entry.value.enum_values:
                raise TypeError("enum comparison requires eq with a registered enum value")
        else:
            raise TypeError(f"{kind.value} does not support scalar comparisons")
        return
    if isinstance(formula, Not):
        _check_formula(formula.child, registry); return
    if isinstance(formula, (And, Or)):
        if not formula.children:
            raise ValueError("and/or must have at least one child")
        for child in formula.children:
            _check_formula(child, registry)
        return
    raise TypeError(f"unsupported formula node: {type(formula).__name__}")


def compile_constraint(constraint: Constraint, registry: Registry) -> CompileResult:
    event_deps=set()
    anchor=getattr(constraint,"anchor",None)
    if anchor is not None and anchor.kind.value=="EVENT_INSTANCE":
        ent=_validate_event(anchor.event_type,anchor.event_version,anchor.event_filter,registry)
        event_deps.add((f"event:{anchor.event_type}",anchor.event_version,tuple(sorted((k,stable_key(v)) for k,v in (anchor.event_filter or {}).items()))))
        event_deps.add(("clock","simulation-minute",()))
        event_deps.update((f"raw:{r}",anchor.event_version,()) for r in ent.reads)
    trigger=getattr(constraint,"trigger",None)
    if trigger is not None:
        ent=_validate_event(trigger.event_type,trigger.event_version,trigger.event_filter,registry)
        event_deps.add((f"event:{trigger.event_type}",trigger.event_version,tuple(sorted((k,stable_key(v)) for k,v in (trigger.event_filter or {}).items()))))
        event_deps.add(("clock","simulation-minute",()))
        event_deps.update((f"raw:{r}",trigger.event_version,()) for r in ent.reads)
    if isinstance(constraint, TemporalConstraint):
        _check_formula(constraint.formula, registry)
        refs = _formula_refs(constraint.formula)
        if isinstance(constraint.formula, (And, Or, Not)):
            if any(registry.resolve(r.observable_id, r.version).time_mode.value in ("CERTIFIED_POLYNOMIAL", "INTERVAL_BOUNDS") for r in refs):
                raise ValueError("continuous boolean composition is unsupported; split into certified numeric constraints")
        if isinstance(constraint.formula, CompareValue):
            ent=registry.resolve(constraint.formula.ref.observable_id,constraint.formula.ref.version)
            if constraint.op.value!="AT" and ent.value.kind is ValueKind.REAL and ent.time_mode.value in ("CERTIFIED_POLYNOMIAL","INTERVAL_BOUNDS") and constraint.formula.op not in (Compare.LE,Compare.GE):
                raise ValueError("continuous temporal predicates support only certified <= or >= comparisons")
        if constraint.op.value != "AT" and any(registry.resolve(r.observable_id,r.version).time_mode.value == "POINT_ONLY" for r in refs):
            raise ValueError("POINT_ONLY observables support AT constraints only")
    elif isinstance(constraint, (NumericBand, TimeWeightedMeanDifference)):
        _validate_ref(constraint.ref, registry)
        entry = registry.resolve(constraint.ref.observable_id, constraint.ref.version)
        if entry.value.kind is not ValueKind.REAL:
            raise TypeError("numeric constraints require REAL observable")
        if isinstance(constraint, TimeWeightedMeanDifference) and constraint.unit != entry.value.unit:
            raise TypeError("mean difference unit mismatch")
        if isinstance(constraint, TimeWeightedMeanDifference):
            if entry.time_mode.value != "CERTIFIED_POLYNOMIAL":
                raise ValueError("time-weighted means require certified polynomial segments")
            if constraint.earlier.end <= constraint.earlier.start or constraint.later.end <= constraint.later.start:
                raise ValueError("weighted-mean windows require positive duration")
            if max(constraint.earlier.start,constraint.later.start) < min(constraint.earlier.end,constraint.later.end):
                raise ValueError("weighted-mean windows must not overlap")
        if isinstance(constraint, NumericBand):
            if constraint.unit != entry.value.unit:
                raise TypeError(f"numeric band must explicitly use unit {entry.value.unit!r}")
            lows=[v for v in (constraint.lower,constraint.lower_at_end) if v is not None]
            highs=[v for v in (constraint.upper,constraint.upper_at_end) if v is not None]
            if any(v<entry.value.lower for v in lows) or any(v>entry.value.upper for v in highs):
                raise ValueError("band exceeds registered observable domain")
            if entry.time_mode.value == "POINT_ONLY" and constraint.window.start != constraint.window.end:
                raise ValueError("POINT_ONLY numeric observables support only zero-width bands")
            if entry.time_mode.value == "PIECEWISE_CONSTANT" and constraint.window.start != constraint.window.end:
                raise ValueError("non-point NumericBand requires continuous certificates; step REAL band monitoring is not implemented")
            if entry.time_mode.value not in ("CERTIFIED_POLYNOMIAL", "INTERVAL_BOUNDS", "POINT_ONLY", "PIECEWISE_CONSTANT"):
                raise ValueError("unsupported numeric band time mode")
        refs = [constraint.ref]
    elif isinstance(constraint, EnumTransitionSequence):
        _validate_ref(constraint.ref, registry)
        entry = registry.resolve(constraint.ref.observable_id, constraint.ref.version)
        if entry.value.kind is not ValueKind.ENUM:
            raise TypeError("enum sequence requires ENUM observable")
        if entry.time_mode.value!="PIECEWISE_CONSTANT": raise ValueError("enum transition sequences require piecewise-constant semantics")
        invalid = set(constraint.states) - set(entry.value.enum_values)
        if invalid:
            raise ValueError(f"unknown enum states: {sorted(invalid)}")
        refs = [constraint.ref]
    elif isinstance(constraint, EventCount):
        ent=_validate_event(constraint.event_type,constraint.event_version,constraint.event_filter,registry)
        event_deps.add((f"event:{constraint.event_type}",constraint.event_version,tuple(sorted((k,stable_key(v)) for k,v in (constraint.event_filter or {}).items()))))
        event_deps.add(("clock","simulation-minute",()))
        event_deps.update((f"raw:{r}",constraint.event_version,()) for r in ent.reads)
        refs = []
    elif isinstance(constraint, EventOrder):
        before=_validate_event(constraint.before_type,constraint.before_version,constraint.before_filter,registry)
        after=_validate_event(constraint.after_type,constraint.after_version,constraint.after_filter,registry)
        for name,version,filters,ent in ((constraint.before_type,constraint.before_version,constraint.before_filter,before),(constraint.after_type,constraint.after_version,constraint.after_filter,after)):
            event_deps.add((f"event:{name}",version,tuple(sorted((k,stable_key(v)) for k,v in (filters or {}).items()))))
            event_deps.update((f"raw:{r}",version,()) for r in ent.reads)
        event_deps.add(("clock","simulation-minute",()))
        refs = []
    else:
        raise TypeError(f"unsupported constraint node: {type(constraint).__name__}")
    deps = set(event_deps)
    for ref in refs:
        entry = registry.resolve(ref.observable_id, ref.version)
        deps.add(ref.dependency_key)
        # Declared raw reads are conservatively included; their identities are strings here.
        deps.update((f"raw:{name}", entry.version, ()) for name in entry.reads)
    return CompileResult(constraint, tuple(sorted(deps)))


@dataclass(frozen=True)
class ConflictProof:
    left_id: str
    right_id: str
    reason: str
    overlap: tuple[Fraction, Fraction]


def _bounds_for(formula: Formula) -> dict[tuple, tuple[Fraction | None, Fraction | None]] | None:
    if isinstance(formula, CompareValue):
        if formula.op is Compare.EQ and isinstance(formula.value, bool):
            v = Fraction(int(formula.value)); return {formula.ref.dependency_key: (v, v)}
        if isinstance(formula.value, NumericLiteral):
            v = formula.value.value
            return {formula.ref.dependency_key: ((None, v) if formula.op is Compare.LE else (v, None) if formula.op is Compare.GE else (v, v))}
    return None


def detect_hard_conflict(items: list[Constraint]) -> tuple[Compatibility, ConflictProof | None]:
    """Proves only same-anchor universal/AT bound contradictions on identical refs."""
    uncertain = False
    for i, a in enumerate(items):
        if not getattr(a, "hard", False): continue
        for b in items[i + 1:]:
            if not getattr(b, "hard", False): continue
            wa, wb = getattr(a, "window", None), getattr(b, "window", None)
            if wa is None or wb is None or getattr(a,"trigger",None) is not None or getattr(b,"trigger",None) is not None:
                uncertain = True; continue
            aa,ab=getattr(a,"anchor",None),getattr(b,"anchor",None)
            if isinstance(a,TemporalConstraint) and a.op.value not in ("ALWAYS","AT"): uncertain=True; continue
            if isinstance(b,TemporalConstraint) and b.op.value not in ("ALWAYS","AT"): uncertain=True; continue
            # Relative event windows and unequal anchors need temporal normalization, so never guess.
            def absolute(c):
                an=getattr(c,"anchor",None)
                if an is None or an.kind.value=="SCENARIO_START": return Fraction(0)
                if an.kind.value=="FIXED_ABSOLUTE": return an.absolute_time
                return None
            kind_a=getattr(aa,"kind",None); kind_b=getattr(ab,"kind",None)
            if kind_a is not None and kind_b is not None and kind_a is not kind_b and {kind_a.value,kind_b.value}=={"SCENARIO_START","FIXED_ABSOLUTE"}:
                uncertain=True; continue
            base_a,base_b=absolute(a),absolute(b)
            if base_a is None or base_b is None:
                uncertain=True; continue
            la,ra=base_a+wa.start,base_a+wa.end; lb,rb=base_b+wb.start,base_b+wb.end
            lo,hi=max(la,lb),min(ra,rb)
            def is_closed_at(window,base,t):
                rel=t-base
                if rel==window.start and not window.left_closed: return False
                if rel==window.end and not window.right_closed: return False
                return window.start<=rel<=window.end
            if hi < lo or (hi==lo and not (is_closed_at(wa,base_a,lo) and is_closed_at(wb,base_b,lo))): continue
            ba = _bounds_for(a.formula) if isinstance(a, TemporalConstraint) else ({a.ref.dependency_key: (a.lower, a.upper)} if isinstance(a, NumericBand) and a.lower_at_end is None and a.upper_at_end is None else None)
            bb = _bounds_for(b.formula) if isinstance(b, TemporalConstraint) else ({b.ref.dependency_key: (b.lower, b.upper)} if isinstance(b, NumericBand) and b.lower_at_end is None and b.upper_at_end is None else None)
            if ba is None or bb is None:
                uncertain = True; continue
            common = set(ba) & set(bb)
            for refkey in common:
                al, au = ba[refkey]; bl, bu = bb[refkey]
                lower = max(x for x in (al, bl) if x is not None) if al is not None or bl is not None else None
                upper = min(x for x in (au, bu) if x is not None) if au is not None or bu is not None else None
                if lower is not None and upper is not None and lower > upper:
                    return Compatibility.HARD_CONFLICT_PROVEN, ConflictProof(a.constraint_id, b.constraint_id,
                        f"incompatible bounds for {refkey[0]}@{refkey[1]}", (lo, hi))
            uncertain = True
    return (Compatibility.COMPATIBILITY_UNKNOWN if items else Compatibility.COMPATIBLE), None


def verify_migration(old_version: str, new_version: str, old_constraints: list[Constraint],
                     migrated: list[Constraint], registry: Registry, replay: Any) -> None:
    """Explicit migration gate: require distinct pins and caller-supplied replay acceptance."""
    if not old_version or not new_version or old_version == new_version:
        raise ValueError("migration requires distinct explicit old/new versions")
    def refs_of(item):
        if isinstance(item,TemporalConstraint): return _formula_refs(item.formula)
        if isinstance(item,(NumericBand,TimeWeightedMeanDifference,EnumTransitionSequence)): return [item.ref]
        return []
    for item in old_constraints:
        if any(r.version!=old_version for r in refs_of(item)):
            raise ValueError("old constraint set does not match declared old version")
    for item in migrated:
        compile_constraint(item, registry)
        if any(r.version!=new_version for r in refs_of(item)):
            raise ValueError("migrated constraints do not pin declared new version")
    if len(old_constraints) != len(migrated) or not replay(old_constraints, migrated):
        raise ValueError("migration replay verification failed")
