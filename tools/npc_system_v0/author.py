"""Author requirements are TypedIR constraints, never character task lists.

Reuses the existing constraint compiler/monitor. Unsupported evidence remains
INDETERMINATE; forecasts are kept separate from committed traces.
"""
from fractions import Fraction

from trajectory_constraints_v0.ast import (Anchor, AnchorKind, Compare, CompareValue,
    EventCount, EventOrder, NumericBand, StrictOrder, TemporalConstraint, TemporalOp, Window,
    ast_to_json, ast_from_json, NumericLiteral)
from trajectory_constraints_v0.monitor import evaluate
from trajectory_constraints_v0.compiler import compile_constraint
from trajectory_constraints_v0.trace import Event, Point, Trace
from trajectory_constraints_v0.types import (Owner, Registry, RegistryEntry, TimeMode, TypeSpec,
    ValueKind, ValueRef, StableEntity)
from tools.e0_keyledger_v0.fixtures import PRODUCER_VERSION as E0
from .executor import validate_evidence


def registry(model_version):
    return Registry((
        RegistryEntry("ledger_acquired", E0, Owner.LEDGER, "Acquisition", {"actor": "Actor", "item": "Item"},
                      TypeSpec(ValueKind.EVENT), "ledger_event_v1", ("settlement_ledger",), TimeMode.EVENT),
        RegistryEntry("loan_reply_accepted", E0, Owner.LEDGER, "Consent", {"actor": "Actor", "item": "Item", "offer_id": "str"},
                      TypeSpec(ValueKind.EVENT), "ledger_event_v1", ("settlement_ledger",), TimeMode.EVENT),
        RegistryEntry("resources", "npc-world-v0", Owner.WORLD, "World", {},
                      TypeSpec(ValueKind.REAL, unit="credits", lower=0, upper=100),
                      "registered_field_v1", ("W.director_resources",), TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("holding", "npc-world-v0", Owner.WORLD, "Holding", {},
                      TypeSpec(ValueKind.BOOL), "registered_field_v1", ("W.holders.ledger",), TimeMode.POINT_ONLY),
        RegistryEntry("stress", model_version, Owner.ACTOR_S, "Actor", {"actor": "Actor"},
                      TypeSpec(ValueKind.REAL, unit="synthetic-score", lower=0, upper=1),
                      "registered_field_v1", ("S.stress",), TimeMode.PIECEWISE_CONSTANT, model_pin=model_version),
    ))


def requirements(deadline=10):
    if type(deadline) is not int or not 2 <= deadline <= 10:
        raise ValueError("bounded application author deadline must be in [2,10]")
    # Fixed-absolute anchors keep replanning from sliding the deadline.
    absolute = Anchor(AnchorKind.FIXED_ABSOLUTE, absolute_time=0)
    return (
        EventCount("ledger-event", "ledger_acquired", E0, Window(2, deadline),
                   event_filter={"actor": StableEntity("Actor", "A"), "item": StableEntity("Item", "ledger")}, anchor=absolute),
        EventOrder("consent-before-acquisition", "loan_reply_accepted", E0, "ledger_acquired", E0,
                   StrictOrder.PHYSICAL_TIME, Window(2, deadline), anchor=absolute),
        TemporalConstraint("world-resource-line", TemporalOp.ALWAYS,
                           CompareValue(ValueRef("resources", "npc-world-v0", {}), Compare.GE,
                                        NumericLiteral(Fraction(0), "credits")), Window(2, 10), anchor=absolute),
        TemporalConstraint("final-holding-point", TemporalOp.AT,
                           CompareValue(ValueRef("holding", "npc-world-v0", {}), Compare.EQ, True),
                           Window(deadline, deadline), anchor=absolute),
    )


def monitor(snapshots, constraints, model_version):
    cp = snapshots[-1]
    validate_evidence(cp)
    trace = Trace(scenario_start=2, now=cp["clock"]["now"])
    for snap in snapshots:
        now = snap["clock"]["now"]
        trace.add_point(Point(ValueRef("resources", "npc-world-v0", {}), now,
                              Fraction(snap["W"]["director_resources"]), "world_snapshot_projector"))
        trace.add_point(Point(ValueRef("holding", "npc-world-v0", {}), now,
                              snap["W"]["holders"]["ledger"] == "A", "world_snapshot_projector"))
        for who in ("A", "B"):
            trace.add_point(Point(ValueRef("stress", model_version, {"actor": StableEntity("Actor", who)}), now,
                                  Fraction(str(snap["characters"][who]["S"]["stress"])), "committed_model_state"))
    for row in cp["events"]:
        if row["time"] >= 2:
            args = {k: v for k, v in row["typed_args"].items() if k != "event"}
            for name, kind in (("actor", "Actor"), ("item", "Item")):
                if name in args:
                    args[name] = StableEntity(kind, args[name])
            trace.add_event(Event(row["event_id"], row["event_type"], row["time"], row["sequence"],
                                  args, row["producer_version"]))
    contiguous = 2
    seal_times = {s["sealed_through"] for s in cp["seals"]}
    while contiguous in seal_times:
        contiguous += 1
    if contiguous > 2:
        trace.seal_events_through(contiguous - 1)
    # Sparse snapshots do not certify intervening value coverage.
    if [s["clock"]["now"] for s in snapshots] == list(range(2, cp["clock"]["now"] + 1)):
        trace.seal_values_through(ValueRef("resources", "npc-world-v0", {}), cp["clock"]["now"])
        for who in ("A", "B"):
            trace.seal_values_through(ValueRef("stress", model_version, {"actor": StableEntity("Actor", who)}), cp["clock"]["now"])
    results = []
    pinned_registry = registry(model_version)
    for constraint in constraints:
        # expected_owner is a type assertion, not a distinct physical sample.
        # Check it first, then resolve to the canonical projector reference;
        # don't change the frozen reference library or discard wrong-owner errors.
        compile_constraint(constraint, pinned_registry)
        def resolve_refs(value):
            if isinstance(value, dict):
                result = {k: resolve_refs(v) for k, v in value.items()}
                if result.get("$type") == "ValueRef":
                    result["expected_owner"] = None
                return result
            if isinstance(value, list):
                return [resolve_refs(v) for v in value]
            return value
        resolved = ast_from_json(resolve_refs(ast_to_json(constraint)))
        for r in evaluate(resolved, trace, pinned_registry):
            results.append({"id": r.constraint_id, "hard": constraint.hard, "status": r.verdict.value,
                            "reason": r.reason, "witness": ast_to_json(r.witness)})
    return results
