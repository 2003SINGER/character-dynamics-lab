"""Receipt-only integration monitor using the repository's TypedIR."""
from __future__ import annotations

from fractions import Fraction

from tools.trajectory_constraints_v0.ast import EventCount, EventOrder, StrictOrder, Window
from tools.trajectory_constraints_v0.monitor import evaluate
from tools.trajectory_constraints_v0.trace import Event, Trace
from tools.trajectory_constraints_v0.types import (
    Owner, Registry, RegistryEntry, TimeMode, TypeSpec, ValueKind,
)

EVENT_VERSION = "1"


def integration_registry() -> Registry:
    return Registry(tuple(
        RegistryEntry(name, EVENT_VERSION, Owner.LEDGER, "P0NativeReceipt", fields,
                      TypeSpec(ValueKind.EVENT), "ledger_event_v1",
                      ("sealed_native_evennia_ledger",), TimeMode.EVENT)
        for name, fields in (
            ("p0_delivery", {"actor": "str", "item": "str", "room": "str"}),
            ("p0_storm_observation", {"actor": "str", "weather": "str"}),
            ("p0_meeting_witness", {"weather": "str", "B_observed_storm": "bool"}),
        )))


def _project_native_receipts(ledger: list[dict], *, frontier: int) -> list[Event]:
    """Project receipt-shaped rows from a supplied sealed prefix.

    This is a semantic allowlist, not producer authentication; trusted RPC and
    native trace construction remain the caller's boundary.
    """
    if not isinstance(ledger, list) or type(frontier) is not int or frontier < 0:
        raise TypeError("ledger/frontier must be explicit native trace fields")
    projected = []
    seen = set()
    mapping = {
        "DROP_SETTLED": ("p0_delivery", "native_evennia_readback"),
        "WEATHER_OBSERVED": ("p0_storm_observation", "native_evennia_readback"),
        "MEETING_WITNESS": ("p0_meeting_witness", "native_meet_command"),
    }
    for row in ledger:
        if not isinstance(row, dict) or row.get("sequence", frontier + 1) > frontier:
            continue
        event_type = row.get("event_type")
        if event_type not in mapping:
            continue
        typed_type, source = mapping[event_type]
        if (row.get("source") != source or row.get("accepted") is not True
                or row.get("settled") is not True or not row.get("receipt_id")
                or row.get("code") not in (None, "")):
            continue
        minute, sequence, event_id = row.get("minute"), row.get("sequence"), row.get("event_id")
        args = row.get("typed_args")
        if (type(minute) is not int or type(sequence) is not int or not isinstance(event_id, str)
                or not isinstance(args, dict) or event_id in seen):
            continue
        if event_type == "DROP_SETTLED":
            if args != {"actor": "A", "item": "shelter_kit", "room": "inn"}:
                continue
            values = {"actor": "A", "item": "shelter_kit", "room": "inn"}
        elif event_type == "WEATHER_OBSERVED":
            if args.get("actor") != "B" or args.get("weather") != "storm":
                continue
            values = {"actor": "B", "weather": "storm"}
        else:
            if args.get("weather") != "storm" or args.get("B_observed_storm") is not True:
                continue
            values = {"weather": "storm", "B_observed_storm": True}
        seen.add(event_id)
        projected.append(Event(event_id, typed_type, minute, sequence, values,
                               version=EVENT_VERSION, provenance="committed_ledger"))
    return projected


def build_typed_trace(trace_data: dict) -> Trace:
    if not isinstance(trace_data, dict):
        raise TypeError("native trace must be a mapping")
    now = trace_data.get("snapshot", {}).get("clock", {}).get("now")
    if type(now) is not int or not 0 <= now <= 24:
        raise ValueError("native trace snapshot has invalid minute")
    frontier = trace_data.get("ledger_frontier")
    sealed = trace_data.get("sealed_through")
    trace = Trace(scenario_start=0, now=now)
    if type(frontier) is not int or frontier < 0:
        frontier = -1
    if type(sealed) is not int or not 0 <= sealed <= now:
        sealed = None
    rows = trace_data.get("events", [])
    sequence = [row.get("sequence") for row in rows if isinstance(row, dict)]
    full_prefix = (len(rows) == frontier and sequence == list(range(1, frontier + 1)))
    source_rows = rows if full_prefix else []
    for event in _project_native_receipts(source_rows, frontier=frontier):
        trace.add_event(event)
    if sealed is not None and full_prefix:
        trace.seal_events_through(sealed)
    if full_prefix and sealed is not None and sealed >= now:
        trace.finalize_events(now)
    return trace


def author_constraints(deadline: int = 24):
    if type(deadline) is not int or not 0 <= deadline <= 24:
        raise ValueError("deadline must be an integration-v0 minute")
    window = Window(Fraction(0), Fraction(deadline), True, True)
    return (
        EventCount("delivery-once", "p0_delivery", EVENT_VERSION, window,
                   minimum=1, maximum=1,
                   event_filter={"actor": "A", "item": "shelter_kit", "room": "inn"}),
        EventCount("b-observed-storm-once", "p0_storm_observation", EVENT_VERSION, window,
                   minimum=1, maximum=1, event_filter={"actor": "B", "weather": "storm"}),
        EventCount("meeting-witness-once", "p0_meeting_witness", EVENT_VERSION, window,
                   minimum=1, maximum=1,
                   event_filter={"weather": "storm", "B_observed_storm": True}),
        EventOrder("delivery-before-meeting", "p0_delivery", EVENT_VERSION,
                   "p0_meeting_witness", EVENT_VERSION, StrictOrder.EVENT_KEY, window,
                   before_filter={"actor": "A", "item": "shelter_kit", "room": "inn"}),
        EventOrder("observation-before-meeting", "p0_storm_observation", EVENT_VERSION,
                   "p0_meeting_witness", EVENT_VERSION, StrictOrder.EVENT_KEY, window,
                   before_filter={"actor": "B", "weather": "storm"}),
    )


def evaluate_native_trace(trace_data: dict) -> dict:
    trace = build_typed_trace(trace_data)
    registry = integration_registry()
    rows = []
    for constraint in author_constraints():
        for result in evaluate(constraint, trace, registry):
            rows.append({"constraint_id": result.constraint_id,
                         "status": result.verdict.value, "reason": result.reason,
                         "witness": list(result.witness) if isinstance(result.witness, tuple) else result.witness})
    statuses = {row["status"] for row in rows}
    overall = ("VIOLATED" if "VIOLATED" in statuses else
               "INDETERMINATE" if "INDETERMINATE" in statuses else
               "PENDING" if "PENDING" in statuses or "NOT_ACTIVATED" in statuses else "SATISFIED")
    sealed = trace_data.get("sealed_through")
    now = trace_data.get("snapshot", {}).get("clock", {}).get("now")
    complete_prefix = (type(sealed) is int and sealed >= now
                       and trace_data.get("ledger_frontier") == len(trace_data.get("events", []))
                       and [row.get("sequence") for row in trace_data.get("events", [])]
                       == list(range(1, int(trace_data.get("ledger_frontier", 0)) + 1)))
    if not complete_prefix:
        overall = "INDETERMINATE"
    return {"monitor": "repository-TypedIR-EventCount-EventOrder", "status": overall,
            "complete_ledger_prefix": complete_prefix,
            "constraints": rows, "projected_receipts": [e.event_id for e in trace.events]}


def classify_planner_result(result: dict) -> str:
    status = result.get("status")
    if status == "SUCCESS": return "PLAN_FOUND"
    if status == "BUDGET_LIMIT": return "SEARCH_BUDGET"
    if status == "NATIVE_NO_SOLUTION": return "NO_PLAN_IN_EXPORTED_DOMAIN"
    if status == "PROCESS_TIMEOUT": return "WRAPPER_TIMEOUT"
    if status in {"NATIVE_ERROR", "NATIVE_STARTUP_ERROR", "NATIVE_UNKNOWN", "WRAPPER_ERROR"}:
        return "PLANNER_ERROR"
    return "PLANNER_STATUS_UNCLASSIFIED"


def classify_native_step(response: dict) -> str:
    code = response.get("code") or response.get("status")
    if code == "ACL_DENIED": return "ACL_DENIED"
    if code in {"ILLEGAL_ACTION", "ILLEGAL"}: return "ILLEGAL_ACTION"
    if code in {"EXECUTION_FAILURE", "EXECUTION_FAILED"}: return "EXECUTION_FAILURE"
    if response.get("accepted") and response.get("settled"): return "SETTLED_NATIVE_ACTION"
    return "NATIVE_RESULT_UNCLASSIFIED"
