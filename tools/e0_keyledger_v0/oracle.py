"""Independent exhaustive oracle for the frozen E0-KeyLedger-v0 domain.

This module intentionally has no imports from the executor, planner, prediction
checker, or fixture builder.  It consumes a complete JSON checkpoint and owns
its own precondition and effect transcription from the frozen protocol.
"""

from __future__ import annotations

from copy import deepcopy
import heapq
import json
import time
from typing import Any


_MAX_MINUTE = 10
_GOAL_EVENT = "ledger_acquired"


def _state_key(checkpoint: dict[str, Any]) -> str:
    """Keep the entire raw checkpoint in the key; no history is folded away."""
    return json.dumps(checkpoint, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _now(checkpoint: dict[str, Any]) -> int:
    return int(checkpoint["clock"]["now"])


def _sync_time(checkpoint: dict[str, Any], now: int) -> None:
    checkpoint["clock"]["now"] = now
    checkpoint["W"]["t"] = now


def _target_event(checkpoint: dict[str, Any], deadline: int) -> dict[str, Any] | None:
    contiguous_through, sequence_frontier = _contiguous_seal(checkpoint)
    for event in checkpoint["events"]:
        args = event.get("typed_args", {})
        event_type = event.get("event_type")
        event_time = event.get("time")
        event_sequence = event.get("sequence")
        if not (event_type == _GOAL_EVENT
                and args == {"event": _GOAL_EVENT, "actor": "A", "item": "ledger"}
                and isinstance(event_time, int) and isinstance(event_sequence, int)
                and 2 <= event_time <= deadline
                and event.get("producer_version") == checkpoint["domain"]["producer_version"]
                and contiguous_through >= event_time
                and event_sequence <= sequence_frontier):
            continue
        for receipt in checkpoint["receipts"]:
            intent = receipt.get("intent", {})
            intent_args = intent.get("args", {})
            payloads = receipt.get("event_payloads", [])
            history_match = any(
                row.get("action_id") == receipt.get("action_id")
                and row.get("receipt_id") == receipt.get("receipt_id")
                and row.get("status") == "SUCCESS"
                and row.get("intent") == intent
                for row in checkpoint["action_history"]
            )
            if (receipt.get("producer_version") == event.get("producer_version")
                    and receipt.get("accepted") is True
                    and receipt.get("status") in ("SUCCESS", "SETTLED")
                    and receipt.get("end_time") == event_time
                    and receipt.get("event_ids") == [event.get("event_id")]
                    and payloads == [event]
                    and intent.get("operator") == "take_ledger"
                    and intent.get("actor") == "A"
                    and intent_args == {"item": "ledger"}
                    and history_match):
                return event
    return None


def _contiguous_seal(checkpoint: dict[str, Any]) -> tuple[int, int]:
    """Return the largest contiguous seal prefix and its sequence frontier."""
    producer = checkpoint["domain"]["producer_version"]
    through = 0
    sequence_frontier = -1
    for seal in checkpoint["seals"]:
        seal_time = seal.get("sealed_through")
        seal_sequence = seal.get("sequence_frontier")
        if (seal.get("producer_version") != producer
                or seal_time != through + 1
                or not isinstance(seal_sequence, int)
                or seal_sequence < sequence_frontier):
            break
        through = seal_time
        sequence_frontier = seal_sequence
    return through, sequence_frontier


def _append_fact(observation: dict[str, Any], fact: str) -> None:
    facts = observation.setdefault("known_facts", [])
    if fact not in facts:
        facts.append(fact)


def _know_entity(observation: dict[str, Any], entity_id: str) -> None:
    entities = observation.setdefault("known_entities", [])
    if entity_id not in entities:
        entities.append(entity_id)


def _remove_fact(observation: dict[str, Any], fact: str) -> None:
    facts = observation.setdefault("known_facts", [])
    observation["known_facts"] = [existing for existing in facts if existing != fact]


def _allocate(checkpoint: dict[str, Any], kind: str, prefix: str) -> str:
    ids = checkpoint["next_ids"]
    number = int(ids[kind])
    ids[kind] = number + 1
    return f"{prefix}-{number:06d}"


def _append_event(checkpoint: dict[str, Any], event_type: str, typed_args: dict[str, Any], at: int) -> str:
    event_id = _allocate(checkpoint, "event", "event")
    sequence = int(checkpoint["next_ids"]["sequence"])
    checkpoint["next_ids"]["sequence"] = sequence + 1
    checkpoint["events"].append({
        "event_id": event_id,
        "event_type": event_type,
        "time": at,
        "sequence": sequence,
        "producer_version": checkpoint["domain"]["producer_version"],
        "typed_args": {"event": event_type, **typed_args},
    })
    return event_id


def _refresh_monitor(checkpoint: dict[str, Any], through: int, deadline: int) -> None:
    seals = checkpoint["seals"]
    sequence_frontier = int(checkpoint["next_ids"]["sequence"]) - 1
    contiguous_through, _ = _contiguous_seal(checkpoint)
    if through == contiguous_through + 1:
        seals.append({
            "sealed_through": through,
            "producer_version": checkpoint["domain"]["producer_version"],
            "sequence_frontier": sequence_frontier,
        })
        contiguous_through = through
    monitor = checkpoint["monitor"]
    monitor["coverage_complete_through"] = contiguous_through
    witness = _target_event(checkpoint, deadline)
    if witness is not None:
        monitor.update({
            "status": "SATISFIED",
            "witness_event_id": witness["event_id"],
            "reason": "TARGET_SETTLEMENT_EVENT",
        })
    elif contiguous_through >= deadline:
        monitor.update({
            "status": "VIOLATED",
            "witness_event_id": None,
            "reason": "SEALED_DEADLINE_WITHOUT_WITNESS",
        })
    elif contiguous_through < through:
        monitor.update({"status": "INDETERMINATE", "witness_event_id": None,
                        "reason": "MISSING_PAST_COVERAGE"})
    else:
        monitor.update({
            "status": "PENDING",
            "witness_event_id": None,
            "reason": "NO_WITNESS",
        })


def _intent(operator: str, controller: str, **args: Any) -> dict[str, Any]:
    return {"operator": operator, "actor": controller, "args": args}


def _eligible(checkpoint: dict[str, Any], intent: dict[str, Any]) -> bool:
    w = checkpoint["W"]
    obs = checkpoint["O"]
    op = intent["operator"]
    session = w["offer_session"]
    used = w["action_used_bits"]
    if w["running_action"] is not None:
        return False
    if op == "idle":
        return True
    if op == "offer_loan":
        return (not used["offer_loan"] and session["status"] == "NONE"
                and intent["args"].get("target") == "B"
                and intent["args"].get("payment") == "payment"
                and "payment" in obs["A"]["known_entities"]
                and w["locations"]["A"] == "ENTRANCE"
                and w["locations"]["B"] == "ENTRANCE"
                and w["holders"]["payment"] == "A")
    if op in ("choose_accept", "choose_decline"):
        if (session["status"] != "OFFERED" or used["reply"]
                or session["offer_id"] not in obs["B"]["known_entities"]
                or intent["args"].get("offer_id") != session["offer_id"]):
            return False
        pin = checkpoint["config_pins"]["reply"]
        if pin != "JOINT" and pin != ("ACCEPT" if op == "choose_accept" else "DECLINE"):
            return False
        if op == "choose_accept":
            return (w["holders"]["key1"] == "B" and w["intact"]["key1"]
                    and not w["destroyed"]["key1"]
                    and "key1" in obs["B"]["known_entities"]
                    and "payment" in obs["B"]["known_entities"]
                    and w["beneficial_owners"]["key1"] == "B"
                    and w["beneficial_owners"]["payment"] == "A")
        return True
    if op == "accept_loan":
        return (not used["accept_loan"] and session["status"] == "ACCEPTED"
                and intent["args"].get("offer_id") == session["offer_id"]
                and intent["args"].get("actor") == "A"
                and intent["args"].get("item") == "key1"
                and intent["args"].get("payment") == "payment"
                and session["offer_id"] in obs["B"]["known_entities"]
                and session["offer_id"] in obs["A"]["known_entities"]
                and "key1" in obs["A"]["known_entities"]
                and "key1" in obs["B"]["known_entities"]
                and "payment" in obs["A"]["known_entities"]
                and "payment" in obs["B"]["known_entities"]
                and w["holders"]["key1"] == "B" and w["intact"]["key1"]
                and not w["destroyed"]["key1"] and w["holders"]["payment"] == "A"
                and w["beneficial_owners"]["key1"] == "B"
                and w["beneficial_owners"]["payment"] == "A"
                and w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE")
    if op == "return_tool":
        return (not used["return_tool"] and intent["args"].get("target") == "B"
                and intent["args"].get("item") == "toolB" and w["holders"]["toolB"] == "A"
                and "toolB" in obs["A"]["known_entities"]
                and "toolB" in obs["B"]["known_entities"]
                and w["beneficial_owners"]["toolB"] == "B"
                and w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE")
    if op == "unlock":
        duration = int(checkpoint["config_pins"]["unlock_duration"])
        return (not used["unlock"] and intent["args"].get("item") == "key1"
                and _now(checkpoint) + duration <= min(_MAX_MINUTE, int(checkpoint["config_pins"]["deadline"]))
                and "key1" in obs["A"]["known_entities"]
                and w["holders"]["key1"] == "A" and w["intact"]["key1"]
                and not w["destroyed"]["key1"] and w["locations"]["A"] == "ENTRANCE"
                and w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE"
                and w["beneficial_owners"]["key1"] == "B"
                and not w["archive_open"])
    if op == "take_ledger":
        return (not used["take_ledger"] and intent["args"].get("item") == "ledger"
                and "ledger" in obs["A"]["known_entities"]
                and w["locations"]["A"] == "ENTRANCE"
                and w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE"
                and w["archive_open"] and w["holders"]["ledger"] == "ARCHIVE"
                and w["beneficial_owners"]["ledger"] == "ARCHIVE"
                and not w["destroyed"]["ledger"])
    return False


def _candidate_intents(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    w = checkpoint["W"]
    session = w["offer_session"]
    candidates: list[dict[str, Any]] = []
    if w["running_action"] is not None:
        candidates.append(_intent("idle", "WorldStep"))
        return candidates
    candidates.append(_intent("idle", "WorldStep"))
    candidates.extend([
        _intent("offer_loan", "A", target="B", payment="payment"),
    ])
    if session["status"] == "OFFERED":
        candidates.extend([
            _intent("choose_accept", "B", offer_id=session["offer_id"]),
            _intent("choose_decline", "B", offer_id=session["offer_id"]),
        ])
    if session["status"] == "ACCEPTED":
        candidates.append(_intent("accept_loan", "B", actor="A", offer_id=session["offer_id"], item="key1", payment="payment"))
    candidates.extend([
        _intent("return_tool", "A", target="B", item="toolB"),
        _intent("unlock", "A", item="key1"),
        _intent("take_ledger", "A", item="ledger"),
    ])
    return [candidate for candidate in candidates if _eligible(checkpoint, candidate)]


def _record_completion(checkpoint: dict[str, Any], record: dict[str, Any], at: int,
                       outcome: str, event_ids: list[str]) -> None:
    record["status"] = "SUCCESS"
    action_id = record["action_id"]
    checkpoint["outcome_history"].append({
        "receipt_id": record["receipt_id"],
        "outcome": outcome,
        "event_ids": list(event_ids),
        "time": at,
    })
    event_by_id = {event["event_id"]: event for event in checkpoint["events"]}
    receipt = next((existing for existing in checkpoint["receipts"]
                    if existing.get("receipt_id") == record["receipt_id"]), None)
    if receipt is None:
        receipt = {
            "receipt_id": record["receipt_id"],
            "action_id": action_id,
            "producer_version": checkpoint["domain"]["producer_version"],
            "intent": deepcopy(record["intent"]),
            "accepted": True,
            "start_time": record["time"],
        }
        checkpoint["receipts"].append(receipt)
    receipt.update({
        "action_id": action_id,
        "producer_version": checkpoint["domain"]["producer_version"],
        "intent": deepcopy(record["intent"]),
        "accepted": True,
        "end_time": at,
        "status": "SUCCESS",
        "outcome": outcome,
        "event_ids": list(event_ids),
        "event_payloads": [deepcopy(event_by_id[event_id]) for event_id in event_ids],
        "delta_w": {"settled_operator": record["intent"]["operator"]},
        "delta_o": {},
    })


def _settle(checkpoint: dict[str, Any], record: dict[str, Any], at: int) -> None:
    w = checkpoint["W"]
    obs = checkpoint["O"]
    intent = record["intent"]
    op = intent["operator"]
    args = intent["args"]
    event_ids: list[str] = []
    outcome = op.upper() + "_SETTLED"
    if op == "offer_loan":
        offer_id = "offer-" + record["action_id"].split("-")[-1]
        w["offer_session"].update({"status": "OFFERED", "offer_id": offer_id,
                                    "terms": {"payment": "payment", "amount": 1, "key": None},
                                    "reply_time": None})
        for actor in ("A", "B"):
            _append_fact(obs[actor], "offer_terms_visible")
            _know_entity(obs[actor], offer_id)
            _know_entity(obs[actor], "payment")
        w["action_used_bits"]["offer_loan"] = True
        outcome = "OFFERED"
    elif op in ("choose_accept", "choose_decline"):
        accept = op == "choose_accept"
        w["offer_session"].update({"status": "ACCEPTED" if accept else "DECLINED", "reply_time": at})
        w["action_used_bits"]["reply"] = True
        for actor in ("A", "B"):
            _append_fact(obs[actor], "offer_reply_accepted" if accept else "offer_reply_declined")
        if accept and "key1" not in obs["A"]["known_entities"]:
            obs["A"]["known_entities"].append("key1")
            _append_fact(obs["A"], "key1_disclosed_by_B")
        event_ids.append(_append_event(checkpoint, "loan_reply_accepted" if accept else "loan_reply_declined", {
            "actor": "B", "offer_id": args["offer_id"],
            **({"item": "key1"} if accept else {}),
        }, at))
        outcome = "ACCEPTED" if accept else "DECLINED"
    elif op == "accept_loan":
        w["holders"]["key1"] = "A"
        w["holders"]["payment"] = "B"
        w["beneficial_owners"]["payment"] = "B"
        w["offer_session"]["status"] = "SETTLED"
        w["action_used_bits"]["accept_loan"] = True
        for actor in ("A", "B"):
            _remove_fact(obs[actor], "key1_held_by_B")
            _remove_fact(obs[actor], "payment_held_by_A")
            _append_fact(obs[actor], "key1_held_by_A")
            _append_fact(obs[actor], "payment_held_by_B")
        event_ids.append(_append_event(checkpoint, "loan_exchanged", {
            "actor": "B", "item": "key1", "payment": "payment", "offer_id": args["offer_id"]
        }, at))
        outcome = "EXCHANGED"
    elif op == "return_tool":
        w["holders"]["toolB"] = "B"
        w["action_used_bits"]["return_tool"] = True
        for actor in ("A", "B"):
            _remove_fact(obs[actor], "toolB_held_by_A")
            _append_fact(obs[actor], "toolB_held_by_B")
        event_ids.append(_append_event(checkpoint, "tool_returned", {"actor": "A", "item": "toolB"}, at))
        outcome = "RETURNED"
    elif op == "unlock":
        w["archive_open"] = True
        w["action_used_bits"]["unlock"] = True
        for actor in ("A", "B"):
            _remove_fact(obs[actor], "archive_closed")
            _append_fact(obs[actor], "archive_open")
        event_ids.append(_append_event(checkpoint, "archive_unlocked", {
            "actor": "A", "key": "key1", "item": "ARCHIVE"
        }, at))
        outcome = "UNLOCKED"
    elif op == "take_ledger":
        w["holders"]["ledger"] = "A"
        w["action_used_bits"]["take_ledger"] = True
        for actor in ("A", "B"):
            _remove_fact(obs[actor], "ledger_in_archive")
            _append_fact(obs[actor], "ledger_held_by_A")
        event_ids.append(_append_event(checkpoint, _GOAL_EVENT, {"actor": "A", "item": "ledger"}, at))
        outcome = "ACQUIRED"
    _record_completion(checkpoint, record, at, outcome, event_ids)
    checkpoint["W"]["running_action"] = None
    checkpoint["W"]["reservations"] = []


def _tick(checkpoint: dict[str, Any], deadline: int, *, control: str,
          boundary_action_id: str | None) -> None:
    """Advance one boundary, completing a running action only at its duration."""
    old_time = _now(checkpoint)
    new_time = old_time + 1
    running_before = checkpoint["W"]["running_action"]
    running_id_before = None if running_before is None else running_before.get("id", running_before.get("action_id"))
    checkpoint.setdefault("minute_history", []).append({
        "from_time": old_time,
        "to_time": new_time,
        "control": control,
        "action_id": boundary_action_id,
        "running_action_id": running_id_before,
        **({"intent": deepcopy(running_before["intent"])} if control == "ACTION_START" and running_before else {}),
    })
    _sync_time(checkpoint, new_time)
    running = checkpoint["W"]["running_action"]
    if running is not None:
        running["elapsed"] = int(running["elapsed"]) + 1
        running["progress"] = running["elapsed"]
        if running["elapsed"] >= int(running["duration"]):
            running_id = running.get("id", running.get("action_id"))
            record = next((item for item in reversed(checkpoint["action_history"])
                           if item.get("action_id", item.get("id")) == running_id), None)
            if record is None:
                record = {
                    "action_id": running_id,
                    "receipt_id": running["receipt_id"],
                    "intent": deepcopy(running["intent"]),
                    "time": running["start"],
                    "status": "RUNNING",
                }
                checkpoint["action_history"].append(record)
            else:
                record.setdefault("receipt_id", running["receipt_id"])
                record.setdefault("intent", deepcopy(running["intent"]))
                record.setdefault("time", running.get("start", new_time - int(running["elapsed"])))
            _settle(checkpoint, record, new_time)
    _refresh_monitor(checkpoint, new_time, deadline)


def _apply(checkpoint: dict[str, Any], intent: dict[str, Any], deadline: int) -> dict[str, Any]:
    result = deepcopy(checkpoint)
    op = intent["operator"]
    if op == "idle":
        running = result["W"]["running_action"]
        if running is not None:
            _tick(result, deadline, control="NO_CONTROL", boundary_action_id=None)
            return result
        action_id = _allocate(result, "action", "action")
        receipt_id = _allocate(result, "receipt", "receipt")
        record = {"action_id": action_id, "receipt_id": receipt_id,
                  "time": _now(result), "intent": deepcopy(intent), "status": "SUCCESS"}
        result["action_history"].append(record)
        _tick(result, deadline, control="NO_CONTROL", boundary_action_id=action_id)
        record["status"] = "SUCCESS"
        result["outcome_history"].append({"receipt_id": receipt_id, "outcome": "NO_CONTROL",
                                           "event_ids": [], "time": _now(result)})
        result["receipts"].append({
            "receipt_id": receipt_id,
            "action_id": action_id,
            "producer_version": result["domain"]["producer_version"],
            "intent": deepcopy(intent),
            "accepted": True,
            "start_time": record["time"],
            "end_time": _now(result),
            "status": "SUCCESS",
            "outcome": "NO_CONTROL",
            "event_ids": [],
            "event_payloads": [],
            "delta_w": {},
            "delta_o": {},
        })
        return result

    action_id = _allocate(result, "action", "action")
    start = _now(result)
    duration = int(result["config_pins"]["unlock_duration"]) if op == "unlock" else 1
    record = {
        "action_id": action_id,
        "receipt_id": _allocate(result, "receipt", "receipt"),
        "intent": deepcopy(intent),
        "time": start,
        "status": "RUNNING",
    }
    result["action_history"].append(record)
    result["receipts"].append({
        "receipt_id": record["receipt_id"],
        "action_id": action_id,
        "producer_version": result["domain"]["producer_version"],
        "intent": deepcopy(intent),
        "accepted": True,
        "start_time": start,
        "end_time": None,
        "status": "RUNNING",
        "outcome": None,
        "event_ids": [],
        "event_payloads": [],
        "delta_w": {},
        "delta_o": {},
    })
    if duration > 1:
        result["W"]["running_action"] = {
            "id": action_id,
            "action_id": action_id,
            "operator": op,
            "intent": deepcopy(intent),
            "start": start,
            "duration": duration,
            "elapsed": 0,
            "authority": intent["actor"],
            "progress": 0,
            "receipt_id": record["receipt_id"],
        }
        result["W"]["reservations"] = [{"action_id": action_id, "resources": ["key1", "ARCHIVE"]}]
        # A multi-minute action starts now and receives its first minute.
        _tick(result, deadline, control="ACTION_START", boundary_action_id=action_id)
    else:
        # The atomic action occupies the single world token for this minute.
        result["W"]["running_action"] = {
            "id": action_id,
            "action_id": action_id,
            "operator": op,
            "intent": deepcopy(intent),
            "start": start,
            "duration": 1,
            "elapsed": 0,
            "authority": intent["actor"],
            "progress": 0,
            "receipt_id": record["receipt_id"],
        }
        _tick(result, deadline, control="ACTION_START", boundary_action_id=action_id)
    return result


def solve(
    checkpoint: dict[str, Any],
    *,
    max_expansions: int = 10_000,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    """Exhaustively enumerate reachable checkpoints under the frozen budget.

    The queue is ordered by absolute simulated time.  Goal evidence is retained
    when first encountered, but enumeration continues until the frontier is
    empty or a frozen budget is reached.
    """
    started = time.monotonic()
    if not isinstance(checkpoint, dict):
        raise TypeError("checkpoint must be a JSON object")
    if not isinstance(max_expansions, int) or max_expansions < 1:
        raise ValueError("max_expansions must be a positive integer")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    initial = deepcopy(checkpoint)
    pins = initial["config_pins"]
    deadline = int(pins["deadline"])
    horizon = min(_MAX_MINUTE, deadline)
    start_time = _now(initial)

    serial = 0
    first_key = _state_key(initial)
    # Heap time is accumulated simulation time; no actor action has a negative cost.
    frontier: list[tuple[int, int, str, dict[str, Any], list[dict[str, Any]]]] = [
        (start_time, serial, first_key, initial, [])
    ]
    queued = {first_key}
    expanded_keys: set[str] = set()
    expansions = 0
    earliest: dict[str, Any] | None = None
    termination_reason = "FRONTIER_EMPTY"

    while frontier:
        if time.monotonic() - started >= timeout_seconds:
            termination_reason = "WALL_TIMEOUT"
            break
        now, _, key, state, path = heapq.heappop(frontier)
        if key in expanded_keys:
            continue
        expanded_keys.add(key)
        expansions += 1

        witness = _target_event(state, deadline)
        if witness is not None and (earliest is None or int(witness["time"]) < earliest["time"]):
            earliest = {
                "time": int(witness["time"]),
                "duration_minutes": int(witness["time"]) - start_time,
                "path": deepcopy(path),
                "event_id": witness["event_id"],
                "sequence": witness.get("sequence"),
            }

        if now < horizon:
            for candidate in _candidate_intents(state):
                next_state = _apply(state, candidate, deadline)
                next_time = _now(next_state)
                if next_time > horizon:
                    continue
                next_key = _state_key(next_state)
                if next_key in queued or next_key in expanded_keys:
                    continue
                queued.add(next_key)
                serial += 1
                # Keep every one-minute control, including forced no_control
                # boundaries while a long running action owns the token. This
                # makes the oracle path directly replayable from the checkpoint.
                next_path = path + [{
                    "operator": candidate["operator"],
                    "actor": candidate["actor"],
                    "args": deepcopy(candidate["args"]),
                    "start_time": now,
                    "end_time": next_time,
                }]
                heapq.heappush(frontier, (next_time, serial, next_key, next_state, next_path))

        if expansions >= max_expansions and frontier:
            termination_reason = "STATE_CAP"
            break

    exhausted = not frontier and termination_reason == "FRONTIER_EMPTY"
    complete = exhausted
    if not exhausted:
        solve_status = "BUDGET"
    elif earliest is not None:
        solve_status = "POSSIBLE_IN_WORLD"
    else:
        solve_status = "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN"
    elapsed = time.monotonic() - started
    return {
        "solve_status": solve_status,
        "termination_reason": termination_reason,
        "complete": complete,
        "exhausted": exhausted,
        "goal_found": earliest is not None,
        "expansions": expansions,
        "budget": {"max_expansions": max_expansions, "timeout_seconds": timeout_seconds},
        "wall_seconds": elapsed,
        "frontier": len(frontier),
        "visited": len(expanded_keys),
        "earliest_completion_time": None if earliest is None else earliest["time"],
        "shortest_duration_minutes": None if earliest is None else earliest["duration_minutes"],
        "goal_path": [] if earliest is None else earliest["path"],
        "goal_event_witness": None if earliest is None else {
            "source": "oracle-synthetic-state",
            "event_id": earliest["event_id"],
            "time": earliest["time"],
            "sequence": earliest["sequence"],
        },
    }
