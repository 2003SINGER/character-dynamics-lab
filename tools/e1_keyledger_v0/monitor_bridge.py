"""E1 event/receipt adapter with explicit E0 and E1 producer validation."""
from copy import deepcopy

from tools.e0_keyledger_v0.monitor_bridge import evaluate_goal as e0_evaluate_goal
from tools.e0_keyledger_v0.monitor_bridge import checkpoint_trace as e0_checkpoint_trace
from .fixtures import E1_PRODUCER_VERSION


class MonitorContractError(ValueError):
    pass


def _e0_view(cp):
    view = deepcopy(cp)
    view["events"] = [e for e in cp["events"] if e.get("producer_version") != E1_PRODUCER_VERSION]
    view["receipts"] = [r for r in cp["receipts"] if r.get("producer_version") != E1_PRODUCER_VERSION]
    return view


def validate_e1_evidence(cp):
    events, receipts = cp.get("events"), cp.get("receipts")
    if not isinstance(events, list) or not isinstance(receipts, list):
        raise MonitorContractError("events and receipts must be lists")
    ids, seqs, receipt_claims, receipt_ids = set(), set(), {}, set()
    by_id = {r.get("receipt_id"): r for r in receipts}
    for r in receipts:
        if not isinstance(r.get("receipt_id"), str) or not r["receipt_id"] or r["receipt_id"] in receipt_ids:
            raise MonitorContractError("receipt IDs must be globally unique nonempty strings")
        receipt_ids.add(r["receipt_id"])
        if r.get("producer_version") == E1_PRODUCER_VERSION:
            payloads, claimed = r.get("event_payloads"), r.get("event_ids")
            if not isinstance(payloads, list) or not isinstance(claimed, list):
                raise MonitorContractError("malformed E1 receipt")
            if [e.get("event_id") for e in payloads] != claimed:
                raise MonitorContractError("E1 receipt IDs and payloads disagree")
            for e in payloads:
                if e.get("event_id") in receipt_claims:
                    raise MonitorContractError("duplicate event receipt ownership")
                receipt_claims[e.get("event_id")] = r
    prior = (-1, -1)
    prior_sequence = -1
    clock_now = cp.get("clock", {}).get("now")
    for e in events:
        eid, time, seq = e.get("event_id"), e.get("time"), e.get("sequence")
        if (not isinstance(eid, str) or eid in ids or not isinstance(time, int) or isinstance(time, bool)
                or not isinstance(seq, int) or isinstance(seq, bool) or seq < 0 or not isinstance(clock_now, int)
                or time > clock_now or seq <= prior_sequence):
            raise MonitorContractError("invalid E1/E0 event identity")
        if (time, seq) <= prior:
            raise MonitorContractError("event ledger is not append ordered")
        ids.add(eid); seqs.add(seq); prior = (time, seq); prior_sequence = seq
        if e.get("producer_version") == E1_PRODUCER_VERSION:
            r = receipt_claims.get(eid)
            expected = {"event": "tool_return_requested", "actor": "B", "target": "A", "item": "toolB"}
            if (r is None or e.get("event_type") != "tool_return_requested"
                    or e.get("typed_args") != expected or r.get("intent", {}).get("operator") != "request_tool"
                    or r.get("intent", {}).get("actor") != "B" or r.get("accepted") is not True
                    or r.get("status") != "SUCCESS" or r.get("end_time") != time
                    or r.get("outcome") != "COMPLETED" or r.get("producer_version") != E1_PRODUCER_VERSION
                    or r.get("intent") != {"operator": "request_tool", "actor": "B",
                                           "args": {"target": "A", "item": "toolB"}}
                    or r.get("duration") != 1
                    or r.get("event_payloads") != [e] or len(r.get("event_ids", [])) != 1):
                raise MonitorContractError("request event lacks its exact successful E1 settlement receipt")
            if (e["time"] != r.get("end_time") or e["sequence"] >= cp["next_ids"]["sequence"]
                    or r.get("end_time") != r.get("start_time") + 1
                    or r.get("delta_w") != {"request_used": [False, True]}):
                raise MonitorContractError("request settlement timestamp or sequence is not committed")
    if ids != set(receipt_claims) | {e.get("event_id") for e in events if e.get("producer_version") != E1_PRODUCER_VERSION}:
        raise MonitorContractError("event ledger and receipt claims disagree")
    provenance = cp.get("O", {}).get("B", {}).get("request_sent_provenance")
    req_events = [e for e in events if e.get("event_type") == "tool_return_requested"]
    sent = cp["O"]["B"].get("request_sent")
    if bool(cp.get("W", {}).get("request_used")) != bool(sent):
        raise MonitorContractError("world request bit and B's receipt-backed request history disagree")
    if sent:
        if (len(req_events) != 1 or provenance != {"kind": "settlement_receipt",
                "event_id": req_events[0]["event_id"], "time": req_events[0]["time"], "actor": "B"}):
            raise MonitorContractError("B request_sent lacks exact settlement provenance")
    elif req_events or provenance.get("kind") != "initial_actor_history":
        raise MonitorContractError("false request_sent conflicts with request history")
    seals = cp.get("seals", [])
    last_minute, last_frontier = 0, -1
    seal_by_minute = {}
    for seal in seals:
        minute, frontier = seal.get("sealed_through"), seal.get("sequence_frontier")
        if (seal.get("producer_version") != cp["domain"]["producer_version"]
                or not isinstance(minute, int) or isinstance(minute, bool)
                or not isinstance(frontier, int) or isinstance(frontier, bool)
                or minute <= last_minute or minute > clock_now or frontier < last_frontier
                or minute in seal_by_minute):
            raise MonitorContractError("coverage seals are invalid or nonmonotonic")
        if any(e["time"] <= minute and e["sequence"] > frontier for e in events):
            raise MonitorContractError("coverage seal omits an event in its committed prefix")
        if any(e["time"] > minute and e["sequence"] <= frontier for e in events):
            raise MonitorContractError("coverage seal claims a future event sequence")
        seal_by_minute[minute] = frontier
        last_minute, last_frontier = minute, frontier
    if req_events:
        through = req_events[0]["time"]
        if (seal_by_minute.get(through, -1) < req_events[0]["sequence"]
                or any(minute not in seal_by_minute for minute in range(2, through + 1))):
            raise MonitorContractError("request event is not within a contiguous sealed prefix")
    # Existing E0 evidence is validated in full by the original adapter.
    e0_checkpoint_trace(_e0_view(cp))
    return True


def evaluate_goal(cp, deadline=None):
    validate_e1_evidence(cp)
    return e0_evaluate_goal(_e0_view(cp), deadline)


def evaluate_goals(cp):
    monitor = evaluate_goal(cp)
    facts = cp["O"]["B"]["known_facts"]
    return {**monitor, "B_goals": {
        "toolB_returned": "toolB_held_by_B" in facts,
        "payment_received": "payment_held_by_B" in facts,
        "key1_beneficial_owner_B": cp["W"]["beneficial_owners"]["key1"] == "B",
    }}
