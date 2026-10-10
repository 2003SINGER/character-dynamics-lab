"""Small fixed-rule P4 director selector and TypedIR ledger monitor.

This is a bounded opportunity rule, not a reproduction of DODM/SAS/RL and not
an NPC planner. World state, ledger seals, and event authenticity must be
validated by the server adapter before any monitor result is treated as evidence.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from tools.trajectory_constraints_v0.ast import Anchor, AnchorKind, EventCount, Window
from tools.trajectory_constraints_v0.monitor import evaluate
from tools.trajectory_constraints_v0.trace import Event, Trace
from tools.trajectory_constraints_v0.types import (
    Owner, Registry, RegistryEntry, StableEntity, TimeMode, TypeSpec, ValueKind,
)


PROFILE = "p4_story_v0"
LEDGER_PRODUCER = "native-p4-ledger-v1"
AUTHOR_DEADLINE = 24
SHORT_DEADLINE = 6
DIRECTOR_ACTIONS = frozenset({"OPEN_PASSAGE", "NO_OP"})
AUTHORIZED_VIEW_KEYS = frozenset({
    "now", "deadline", "door_closed", "opportunity_used", "goal_witness_present",
})


def choose_director(authorized_view: Mapping[str, Any], enabled: bool) -> dict[str, Any]:
    """Choose only from the fixed author action set using an exact public view."""
    if not isinstance(authorized_view, Mapping) or set(authorized_view) != AUTHORIZED_VIEW_KEYS:
        raise ValueError("authorized view must contain exactly the five public P4 fields")
    if type(enabled) is not bool:
        raise TypeError("director enabled flag must be boolean")
    now = authorized_view["now"]
    deadline = authorized_view["deadline"]
    if type(now) is not int or type(deadline) is not int or not 0 <= now <= deadline:
        raise ValueError("P4 view clock must be bounded integer simulated minutes")
    for key in ("door_closed", "opportunity_used", "goal_witness_present"):
        if type(authorized_view[key]) is not bool:
            raise TypeError(f"{key} must be boolean")

    open_now = (enabled and now >= 4 and authorized_view["door_closed"]
                and not authorized_view["opportunity_used"]
                and not authorized_view["goal_witness_present"])
    opportunity = (now >= 4 and authorized_view["door_closed"]
                   and not authorized_view["opportunity_used"]
                   and not authorized_view["goal_witness_present"])
    action = "OPEN_PASSAGE" if open_now else "NO_OP"
    return {
        "action": action,
        "candidates": ["OPEN_PASSAGE", "NO_OP"] if opportunity else ["NO_OP"],
        "reason": "fixed_opportunity_rule" if open_now else "no_authorized_opportunity",
    }


def author_constraint(deadline: int = AUTHOR_DEADLINE) -> EventCount:
    """TypedIR target: one settled A-courier to B-resident note response by deadline."""
    if type(deadline) is not int or deadline not in (SHORT_DEADLINE, AUTHOR_DEADLINE):
        raise ValueError("P4 deadline is frozen to 6 or 24 simulated minutes")
    return EventCount(
        "single-note-response",
        "p4_note_response",
        "1",
        Window(Fraction(0), Fraction(deadline), True, True),
        minimum=1,
        maximum=1,
        event_filter={
            "actor": StableEntity("Actor", "A"),
            "recipient": StableEntity("Actor", "B"),
            "item": StableEntity("Item", "note"),
        },
        anchor=Anchor(AnchorKind.FIXED_ABSOLUTE, absolute_time=Fraction(0)),
    )


def ledger_registry() -> Registry:
    return Registry((RegistryEntry(
        "p4_note_response", "1", Owner.LEDGER, "NoteResponse",
        {"actor": "Actor", "recipient": "Actor", "item": "Item", "response": "str"},
        TypeSpec(ValueKind.EVENT), "ledger_event_v1",
        ("server_owned_scene_ledger",), TimeMode.EVENT,
    ),))


def _project_sealed_ledger(ledger: list[dict[str, Any]], *, scene_roles: Mapping[str, Any]) -> list[Event]:
    if not isinstance(ledger, list) or not isinstance(scene_roles, Mapping):
        raise TypeError("P4 ledger and scene role map must be explicit collections")
    if set(scene_roles) != {"courier", "resident"} or not all(
            type(value) is int and value > 0 for value in scene_roles.values()):
        raise ValueError("scene role map must resolve courier and resident stable IDs")
    courier_id, resident_id = scene_roles["courier"], scene_roles["resident"]
    result: list[Event] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[int, int]] = set()
    last_key = (-1, -1)
    for row in ledger:
        if not isinstance(row, dict) or row.get("sealed") is not True:
            raise ValueError("unsealed/non-object ledger row cannot be monitor evidence")
        if row.get("producer_version") != LEDGER_PRODUCER or row.get("event_version") != 1:
            raise ValueError("ledger row does not match the pinned P4 producer/version")
        event_id, minute, sequence = row.get("event_id"), row.get("minute"), row.get("sequence")
        if not isinstance(event_id, str) or not event_id or type(minute) is not int or type(sequence) is not int:
            raise ValueError("ledger row has invalid event identity/time/order")
        key = (minute, sequence)
        if event_id in seen_ids or key in seen_keys or key < last_key:
            raise ValueError("duplicate or reordered P4 ledger event")
        seen_ids.add(event_id); seen_keys.add(key); last_key = key

    rows_by_id = {row["event_id"]: row for row in ledger}
    for row in ledger:
        event_id = row["event_id"]
        minute, sequence = row["minute"], row["sequence"]
        if row.get("event_type") != "SOCIAL_RESPONSE":
            continue
        args = row.get("typed_args")
        if not isinstance(args, dict):
            raise ValueError("social response has no typed ledger args")
        decision = args.get("decision")
        physical = args.get("physical_receipt")
        if decision not in {"accepted", "rejected"} or not isinstance(physical, dict) \
                or physical.get("status") != "settled" \
                or args.get("native_commit_status") != "settled" \
                or not args.get("native_commit_receipt_id"):
            continue
        if (args.get("initiator_actor_id") != courier_id
                or args.get("responder_actor_id") != resident_id
                or args.get("responder_role") != "love"):
            continue
        if not isinstance(args.get("note_id"), int) or args.get("note_id") <= 0:
            raise ValueError("social response is not bound to a physical note item")
        request_id = args.get("request_id")
        source_id = args.get("source_event_id")
        request = rows_by_id.get(source_id)
        if (not isinstance(request_id, str) or request is None
                or request.get("event_type") != "SOCIAL_REQUEST"
                or request.get("minute", 0) > minute
                or request.get("minute") == minute and request.get("sequence", 0) >= sequence):
            continue
        request_args = request.get("typed_args", {})
        request_receipt = request_args.get("physical_receipt", {})
        action_name = args.get("selected_action")
        expected_action = "writeLoveNoteAccept" if decision == "accepted" else "writeLoveNoteReject"
        commit_id = args.get("native_commit_receipt_id")
        commit = rows_by_id.get(commit_id)
        commit_args = commit.get("typed_args", {}) if isinstance(commit, dict) else {}
        if (request_args.get("request_id") != request_id
                or request_args.get("initiator_actor_id") != courier_id
                or request_args.get("recipient_actor_id") != resident_id
                or request_args.get("note_id") != args.get("note_id")
                or not isinstance(request_receipt, dict)
                or request_receipt.get("status") != "settled"
                or request_receipt.get("recipient_inventory_actor_id") != resident_id
                or request_receipt.get("after_location_id") != resident_id
                or physical.get("actor_id") != resident_id
                or physical.get("before_location_id") != resident_id
                or physical.get("after_location_id") != resident_id
                or physical.get("same_note_id") != args.get("note_id")
                or action_name != expected_action
                or not isinstance(commit, dict)
                or commit.get("event_type") != "SOCIAL_COMMIT"
                or commit.get("minute", 0) < minute
                or commit.get("minute") == minute and commit.get("sequence", 0) <= sequence
                or commit_args.get("request_id") != request_id
                or commit_args.get("note_id") != args.get("note_id")
                or commit_args.get("action_name") != expected_action
                or commit_args.get("settlement_receipt_id") != physical.get("receipt_id")):
            continue
        result.append(Event(
            event_id=event_id,
            event_type="p4_note_response",
            time=minute,
            sequence=sequence,
            args={"actor": StableEntity("Actor", "A"),
                  "recipient": StableEntity("Actor", "B"),
                  "item": StableEntity("Item", "note"),
                  "response": "ACCEPTED" if decision == "accepted" else "REFUSED"},
            version="1", provenance="committed_ledger",
        ))
    return result


def evaluate_author_constraint(ledger: list[dict[str, Any]], *, now: int, deadline: int,
                               ledger_sealed_through: Mapping[str, Any] | None,
                               scene_roles: Mapping[str, str]) -> dict[str, Any]:
    """Evaluate only sealed server ledger receipts; proposals are never witnesses.

    An unsealed, malformed, or incomplete ledger is INDETERMINATE/PENDING; a
    planner proposal or text payload cannot be converted into monitor evidence.
    """
    from tools.trajectory_constraints_v0.monitor import Verdict

    if type(now) is not int or type(deadline) is not int or not 0 <= now <= deadline:
        raise ValueError("invalid P4 monitor clock")
    if not isinstance(ledger_sealed_through, Mapping):
        return {"constraint_id": "single-note-response", "verdict": "INDETERMINATE",
                "reason": "P4 ledger has no authoritative completeness seal"}
    seal_minute = ledger_sealed_through.get("minute")
    if (ledger_sealed_through.get("closed") is not True or type(seal_minute) is not int
            or seal_minute != deadline or now != deadline
            or type(ledger_sealed_through.get("sequence")) is not int):
        return {"constraint_id": "single-note-response", "verdict": "INDETERMINATE",
                "reason": "authoritative ledger is not sealed through the fixed deadline"}
    trace = Trace(scenario_start=0, now=now)
    try:
        for event in _project_sealed_ledger(ledger, scene_roles=scene_roles):
            trace.add_event(event)
    except (TypeError, ValueError) as exc:
        return {"constraint_id": "single-note-response", "verdict": "INDETERMINATE",
                "reason": f"sealed ledger validation failed: {type(exc).__name__}"}
    trace.finalize_events(deadline)
    result = evaluate(author_constraint(deadline), trace, ledger_registry())[0]
    return {"constraint_id": result.constraint_id, "verdict": result.verdict.value,
            "reason": result.reason, "witness": result.witness}
