"""Adapter from committed E0 checkpoints to the shared typed trajectory monitor."""

from __future__ import annotations

from fractions import Fraction

from trajectory_constraints_v0.ast import (
    Compare,
    CompareValue,
    EventCount,
    TemporalConstraint,
    TemporalOp,
    Window,
)
from trajectory_constraints_v0.monitor import evaluate
from trajectory_constraints_v0.trace import Event, Point, Trace
from trajectory_constraints_v0.types import (
    Owner,
    Registry,
    RegistryEntry,
    StableEntity,
    TimeMode,
    TypeSpec,
    ValueKind,
    ValueRef,
)

from .fixtures import PRODUCER_VERSION

SCENARIO_START = 2
TARGET_EVENT = "ledger_acquired"
TARGET_EVENT_VERSION = PRODUCER_VERSION

_EVENT_OPERATOR = {
    "key_destroyed": "destroy_key",
    "loan_reply_accepted": "choose_accept",
    "loan_reply_declined": "choose_decline",
    "loan_exchanged": "accept_loan",
    "tool_returned": "return_tool",
    "archive_unlocked": "unlock",
    "ledger_acquired": "take_ledger",
}


def _expected_event_args(event_type: str, receipt: dict) -> dict:
    intent = receipt.get("intent", {})
    args = intent.get("args", {})
    signatures = {
        "key_destroyed": {"event": "key_destroyed", "actor": intent.get("actor"),
                          "item": args.get("item") if args.get("item") in ("key0", "key1") else None},
        "loan_reply_accepted": {"event": "loan_reply_accepted", "actor": "B",
                                 "offer_id": args.get("offer_id"), "item": "key1"},
        "loan_reply_declined": {"event": "loan_reply_declined", "actor": "B",
                                 "offer_id": args.get("offer_id")},
        "loan_exchanged": {"event": "loan_exchanged", "actor": "B", "item": "key1",
                            "payment": "payment", "offer_id": args.get("offer_id")},
        "tool_returned": {"event": "tool_returned", "actor": "A", "item": "toolB"},
        "archive_unlocked": {"event": "archive_unlocked", "actor": "A",
                              "item": "ARCHIVE", "key": "key1"},
        "ledger_acquired": {"event": "ledger_acquired", "actor": "A", "item": "ledger"},
    }
    return signatures[event_type]


class MonitorContractError(ValueError):
    """The checkpoint's claimed committed event evidence is inconsistent."""


def _registry() -> Registry:
    return Registry((
        RegistryEntry(
            TARGET_EVENT,
            TARGET_EVENT_VERSION,
            Owner.LEDGER,
            "LedgerAcquired",
            {"actor": "Actor", "item": "Item"},
            TypeSpec(ValueKind.EVENT),
            "ledger_event_v1",
            ("settlement_ledger",),
            TimeMode.EVENT,
        ),
        RegistryEntry(
            "world.holding",
            "e0-world-v0",
            Owner.WORLD,
            "Holding",
            {"actor": "Actor", "item": "Item"},
            TypeSpec(ValueKind.BOOL),
            "registered_field_v1",
            ("W.holders",),
            TimeMode.POINT_ONLY,
        ),
    ))


def _entity(value: str, entity_type: str) -> StableEntity:
    return StableEntity(entity_type, value, value)


def _validate_committed_events(checkpoint: dict) -> tuple[list[dict], list[dict]]:
    events = checkpoint.get("events")
    receipts = checkpoint.get("receipts")
    if not isinstance(events, list) or not isinstance(receipts, list):
        raise MonitorContractError("checkpoint events and receipts must be lists")

    by_receipt: dict[str, dict] = {}
    claimed_event_ids: dict[str, dict] = {}
    receipt_event_payloads: dict[str, dict] = {}
    for receipt in receipts:
        rid = receipt.get("receipt_id")
        if not isinstance(rid, str) or not rid or rid in by_receipt:
            raise MonitorContractError("receipt IDs must be unique nonempty strings")
        by_receipt[rid] = receipt
        ids = receipt.get("event_ids", [])
        payloads = receipt.get("event_payloads")
        if (not isinstance(ids, list) or len(ids) != len(set(ids))
                or not isinstance(payloads, list)
                or [row.get("event_id") for row in payloads if isinstance(row, dict)] != ids
                or len(payloads) != len(ids)):
            raise MonitorContractError(f"receipt {rid} has invalid event_ids/event_payloads")
        for event_id, payload in zip(ids, payloads):
            if event_id in claimed_event_ids:
                raise MonitorContractError(f"event {event_id} is claimed by multiple receipts")
            claimed_event_ids[event_id] = receipt
            receipt_event_payloads[event_id] = payload

    seen_ids: set[str] = set()
    seen_order_keys: set[tuple[int, int]] = set()
    previous_order_key = None
    for row in events:
        event_id = row.get("event_id")
        event_type = row.get("event_type")
        time = row.get("time")
        sequence = row.get("sequence")
        producer = row.get("producer_version")
        args = row.get("typed_args")
        if (not isinstance(event_id, str) or not event_id or event_id in seen_ids
                or not isinstance(event_type, str) or not isinstance(time, int)
                or isinstance(time, bool) or not isinstance(sequence, int)
                or isinstance(sequence, bool) or sequence < 0 or producer != PRODUCER_VERSION
                or not isinstance(args, dict)):
            raise MonitorContractError("event identity, timestamp, sequence, producer, or payload is invalid")
        seen_ids.add(event_id)
        order_key = (time, sequence)
        if order_key in seen_order_keys:
            raise MonitorContractError("event (time, sequence) keys must be unique")
        if previous_order_key is not None and order_key <= previous_order_key:
            raise MonitorContractError("append-only event ledger is reordered")
        previous_order_key = order_key
        seen_order_keys.add(order_key)
        if args.get("event") != event_type:
            raise MonitorContractError(f"event {event_id} type disagrees with typed_args")
        operator = _EVENT_OPERATOR.get(event_type)
        receipt = claimed_event_ids.get(event_id)
        if operator is None or receipt is None:
            raise MonitorContractError(f"event {event_id} has no admitted producer receipt")
        if receipt_event_payloads[event_id] != row:
            raise MonitorContractError(f"event {event_id} payload differs from its committed receipt")
        intent = receipt.get("intent")
        if (receipt.get("producer_version") != PRODUCER_VERSION
                or receipt.get("accepted") is not True
                or receipt.get("status") != "SUCCESS"
                or receipt.get("end_time") != time
                or not isinstance(intent, dict)
                or intent.get("operator") != operator):
            raise MonitorContractError(f"event {event_id} does not match a successful executor receipt")
        if event_type == "key_destroyed" and (intent.get("actor") != "PLAYER"
                                                or intent.get("args", {}).get("item") not in ("key0", "key1")):
            raise MonitorContractError(f"event {event_id} has invalid destroy-key actor or item binding")
        if args != _expected_event_args(event_type, receipt):
            raise MonitorContractError(f"event {event_id} payload does not match its operator signature")

    if set(claimed_event_ids) != seen_ids:
        raise MonitorContractError("receipt event_ids and committed event ledger disagree")

    seals = checkpoint.get("seals")
    if not isinstance(seals, list):
        raise MonitorContractError("checkpoint seals must be a list")
    return events, seals


def checkpoint_trace(checkpoint: dict) -> Trace:
    """Build an E0 horizon trace, validating every event against its receipt.

    E0 time ``t=2`` is the scenario start. Earlier committed context remains in
    the checkpoint but is outside this bounded monitor window and is not copied
    into the horizon trace.
    """
    clock = checkpoint.get("clock", {}).get("now")
    if not isinstance(clock, int) or isinstance(clock, bool) or clock < SCENARIO_START:
        raise MonitorContractError("checkpoint clock is outside the E0 horizon")
    if checkpoint.get("W", {}).get("t") != clock:
        raise MonitorContractError("W.t and clock.now disagree")

    events, seals = _validate_committed_events(checkpoint)
    trace = Trace(scenario_start=SCENARIO_START, now=clock)
    # Preserve ledger order: sorting here would silently repair an append-only
    # history violation before Trace sees it.
    for row in events:
        if row["time"] < SCENARIO_START:
            continue
        typed = row["typed_args"]
        args = {key: value for key, value in typed.items() if key != "event"}
        if "actor" in args:
            args["actor"] = _entity(args["actor"], "Actor")
        if "item" in args:
            args["item"] = _entity(args["item"], "Item")
        trace.add_event(Event(
            event_id=row["event_id"],
            event_type=row["event_type"],
            time=row["time"],
            sequence=row["sequence"],
            args=args,
            version=row["producer_version"],
            provenance="committed_ledger",
        ))

    previous_time = None
    frontier_by_time: dict[int, int] = {}
    for seal in seals:
        through = seal.get("sealed_through")
        frontier = seal.get("sequence_frontier")
        if (not isinstance(through, int) or isinstance(through, bool)
                or not isinstance(frontier, int) or isinstance(frontier, bool)
                or frontier < 0 or seal.get("producer_version") != PRODUCER_VERSION):
            raise MonitorContractError("seal identity, producer, or frontier is invalid")
        if previous_time is not None and through <= previous_time:
            raise MonitorContractError("append-only seal ledger is reordered or duplicated")
        previous_time = through
        if through < SCENARIO_START:
            continue
        if through > clock:
            raise MonitorContractError("seal frontier is outside the committed trace")
        if through in frontier_by_time:
            raise MonitorContractError("checkpoint contains duplicate seals for one boundary")
        covered = [event for event in events if event["time"] <= through]
        if any(event["sequence"] > frontier for event in covered):
            raise MonitorContractError("seal sequence frontier omits an event in its time prefix")
        frontier_by_time[through] = frontier
    # A later local boundary seal cannot fill a missing earlier coverage seal.
    # Preserve only the contiguous sealed prefix beginning at E0 scenario time.
    contiguous = SCENARIO_START
    while contiguous in frontier_by_time:
        contiguous += 1
    last_contiguous = contiguous - 1
    if last_contiguous >= SCENARIO_START:
        trace.seal_events_through(last_contiguous)
    return trace


def goal_constraint(deadline: int) -> EventCount:
    if not isinstance(deadline, int) or isinstance(deadline, bool) or not SCENARIO_START <= deadline <= 10:
        raise ValueError("deadline must be an integer in [2,10]")
    return EventCount(
        constraint_id="E0-ledger-acquired-A",
        event_type=TARGET_EVENT,
        event_version=TARGET_EVENT_VERSION,
        # EventCount windows are relative to scenario_start, while E0 fixtures
        # use the absolute interval [2, deadline].
        window=Window(Fraction(0), Fraction(deadline - SCENARIO_START), True, True),
        minimum=1,
        maximum=None,
        event_filter={"actor": _entity("A", "Actor"), "item": _entity("ledger", "Item")},
    )


def evaluate_goal(checkpoint: dict, deadline: int | None = None) -> dict:
    pins = checkpoint.get("config_pins", {})
    deadline = pins.get("deadline", 10) if deadline is None else deadline
    trace = checkpoint_trace(checkpoint)
    result = evaluate(goal_constraint(deadline), trace, _registry())[0]
    return {
        "status": result.verdict.value,
        "reason": result.reason,
        "witness_event_ids": list(result.witness or ()),
        "now": int(trace.now),
        "coverage_complete_through": (int(trace.events_sealed_through)
                                       if trace.events_sealed_through is not None else None),
    }


def evaluate_holding_at(checkpoint: dict, *, at_time: int, actor: str = "A", item: str = "ledger") -> dict:
    """Evaluate the H02 state snapshot separately from the event obligation."""
    if not isinstance(at_time, int) or isinstance(at_time, bool) or at_time != checkpoint.get("clock", {}).get("now"):
        raise ValueError("holding snapshot time must equal the checkpoint's committed clock")
    trace = checkpoint_trace(checkpoint)
    ref = ValueRef(
        observable_id="world.holding",
        version="e0-world-v0",
        args={"actor": _entity(actor, "Actor"), "item": _entity(item, "Item")},
        expected_owner=Owner.WORLD,
    )
    trace.add_point(Point(
        ref=ref,
        time=at_time,
        value=checkpoint["W"]["holders"].get(item) == actor,
        source="world_snapshot_projector",
    ))
    relative_time = at_time - SCENARIO_START
    constraint = TemporalConstraint(
        constraint_id="E0-holding-at-deadline",
        op=TemporalOp.AT,
        formula=CompareValue(ref, Compare.EQ, True),
        window=Window(relative_time, relative_time, True, True),
    )
    result = evaluate(constraint, trace, _registry())[0]
    return {"status": result.verdict.value, "reason": result.reason}
