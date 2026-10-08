"""Explicit, pure evaluator dispatch for synthetic reference snapshots."""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from .projectors import (Projected, actor_belief, factive_observer_knows,
                         task_progress, world_holding)
from .types import Owner, RegistryEntry, StableEntity, ValueKind, stable_key


def _id(value: Any) -> str:
    return value.stable_id if isinstance(value,StableEntity) else str(value)


def _task(entry,snapshot,args):
    tasks=snapshot.get("tasks")
    if tasks is None: return task_progress(snapshot)
    raw=tasks.get(_id(args["task"]))
    return task_progress(raw if raw is not None else {})


def _holding(entry,snapshot,args):
    return world_holding(snapshot,_id(args["actor"]),_id(args["item"]))


def _belief(entry,snapshot,args):
    return actor_belief(snapshot,_id(args["actor"]),str(args["proposition"]))


def _knows(entry,snapshot,args):
    return factive_observer_knows(snapshot,_id(args["observer"]),str(args["proposition"]))


def _field(entry,snapshot,args):
    table=snapshot.get("registered_fields")
    if table is None: return Projected(None,False,"registered field snapshot missing")
    key="|".join(f"{k}={stable_key(v)}" for k,v in sorted(args.items()))
    values=table.get(entry.observable_id)
    if values is None or key not in values: return Projected(None,False,"registered field value missing")
    return Projected(values[key],True,"synthetic registered-field lookup",tuple(entry.reads))


def _ledger(entry,snapshot,args):
    if snapshot.get("ledger_events_complete") is not True:
        return Projected(None,False,"event ledger completeness unavailable")
    matches=[]
    for event in snapshot.get("ledger_events",()):
        if event.get("event_type")==entry.observable_id and all(event.get(k)==v for k,v in args.items()):
            matches.append(event)
    if entry.value.kind is ValueKind.EVENT:
        return Projected(tuple(matches),True,"typed committed-ledger event projection",tuple(entry.reads))
    return Projected(bool(matches),True,"typed committed-ledger event existence",tuple(entry.reads))


EVALUATOR_DISPATCH={
    "task_progress_fraction_v1":_task,
    "world_holding_v1":_holding,
    "actor_belief_v1":_belief,
    "factive_observer_knows_v1":_knows,
    "registered_field_v1":_field,
    "ledger_event_v1":_ledger,
}


def project_registered(entry: RegistryEntry, snapshot: Mapping[str,Any], args: Mapping[str,Any]) -> Projected:
    """Run only a named pure projector, then enforce its registry value/domain contract."""
    try: projector=EVALUATOR_DISPATCH[entry.evaluator_id]
    except KeyError as exc: raise ValueError(f"no callable allowlisted evaluator {entry.evaluator_id!r}") from exc
    if set(args)!=set(entry.args): raise ValueError("projector argument names differ from registered signature")
    result=projector(entry,snapshot,args)
    if not isinstance(result,Projected): raise TypeError("projector must return Projected")
    if not result.known: return result
    value=result.value
    if entry.value.kind is ValueKind.BOOL and type(value) is not bool: raise TypeError("projector returned non-bool for BOOL")
    if entry.value.kind is ValueKind.ENUM and value not in entry.value.enum_values: raise ValueError("projector returned enum outside registered domain")
    if entry.value.kind is ValueKind.REAL:
        if isinstance(value,bool): raise TypeError("projector returned bool for REAL")
        number=Fraction(str(value))
        if number<entry.value.lower or number>entry.value.upper: raise ValueError("projector returned REAL outside registered domain")
    if entry.value.kind is ValueKind.EVENT and not isinstance(value,tuple): raise TypeError("EVENT projector must return an immutable tuple")
    if entry.value.kind is ValueKind.SET and not isinstance(value,(set,frozenset,tuple)): raise TypeError("SET projector must return a set-like value")
    return result
