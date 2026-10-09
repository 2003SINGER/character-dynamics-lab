"""Actor-local fixed B chooser and A planning input projection."""
from copy import deepcopy
import hashlib
import json

PUBLIC_CATALOGUE = ("request_tool", "return_tool", "offer_loan", "choose_accept",
                    "choose_decline", "accept_loan", "unlock", "take_ledger", "idle")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode()).hexdigest()


def actor_view(checkpoint, actor):
    """Build a view from one O and validate its own projected settlement history.

    Raw W and the other actor's observation are not copied into the returned
    view and never reach choose_b or the A planner.
    """
    own = deepcopy(checkpoint["O"][actor])
    committed = {event["event_id"]: event for event in checkpoint.get("events", [])}
    for projected in own.get("known_events", []):
        event = committed.get(projected.get("event_id"))
        receipt = next((r for r in checkpoint.get("receipts", [])
                        if projected.get("event_id") in r.get("event_ids", [])), None)
        covered = any(seal.get("sealed_through", -1) >= projected.get("time", 10**9)
                      and seal.get("sequence_frontier", -1) >= projected.get("sequence", 10**9)
                      for seal in checkpoint.get("seals", []))
        if (event != projected or receipt is None or receipt.get("accepted") is not True
                or receipt.get("status") != "SUCCESS" or receipt.get("producer_version") != event.get("producer_version")
                or event not in receipt.get("event_payloads", []) or not covered):
            raise ValueError("actor-visible event projection lacks matching successful sealed receipt")
    if actor == "A":
        view = {"actor": "A", "observation": own, "goals": deepcopy(checkpoint["goals_A"]),
                "catalogue": list(PUBLIC_CATALOGUE),
                "contract": deepcopy(own["public_contract"]),
                "clock": deepcopy(checkpoint["clock"]), "deadline": checkpoint["config_pins"]["deadline"]}
    else:
        view = {"actor": "B", "observation": own, "goals": deepcopy(checkpoint["goals_B"]),
                "catalogue": list(PUBLIC_CATALOGUE),
                "contract": deepcopy(own["public_contract"])}
    return view


def choose_b(view):
    """Deterministic policy consumes only B's own view and the public contract."""
    o, goals, pin = view["observation"], view["goals"], view["contract"]
    facts, entities = set(o["known_facts"]), set(o["known_entities"])
    offer_id = next((x for x in entities if x.startswith("offer-")), None)
    if "reply_accept_visible" in facts and "exchange_visible" not in facts:
        if "payment_held_by_B" in facts:
            return {"operator": "idle", "actor": "B", "args": {}}
        need_tool = "toolB_held_by_A" in facts and "toolB_held_by_B" not in facts
        value = 2 - view["contract"]["c"] - (view["contract"]["p"] if need_tool else 0)
        if value <= 0 or "key1_held_by_B" not in facts:
            return {"operator": "idle", "actor": "B", "args": {}}
        return {"operator": "accept_loan", "actor": "B", "args": {"actor": "A", "item": "key1", "payment": "payment", "offer_id": offer_id}}
    if "offer_visible" in facts and "reply_accept_visible" not in facts and "reply_decline_visible" not in facts:
        intact = "key1" in entities and "key1_destroyed" not in facts
        need_tool = "toolB_held_by_B" in goals and "toolB_held_by_A" in facts
        value = 2 - pin["c"] - (pin["p"] if need_tool else 0)
        accept = intact and value > 0 and "payment" in entities
        return {"operator": "choose_accept" if accept else "choose_decline", "actor": "B",
                "args": {"offer_id": offer_id}}
    if not o.get("request_sent") and "toolB_held_by_A" in facts and "toolB" in entities:
        return {"operator": "request_tool", "actor": "B", "args": {"target": "A", "item": "toolB"}}
    return {"operator": "idle", "actor": "B", "args": {}}


def explain_b(view, action):
    """Return public-contract decision metadata without changing ActionIntent."""
    facts = set(view["observation"]["known_facts"])
    contract = view["contract"]
    unmet_tool = "toolB_held_by_A" in facts and "toolB_held_by_B" not in facts
    utility = 2 - contract["c"] - (contract["p"] if unmet_tool else 0)
    if action["operator"] == "request_tool":
        reason = "TOOL_REQUIRED"
    elif action["operator"] == "choose_accept" or action["operator"] == "accept_loan":
        reason = "NET_GAIN"
    elif action["operator"] == "choose_decline":
        if "key1" not in view["observation"]["known_entities"] or "key1_destroyed" in facts:
            reason = "NO_LOANABLE_KEY"
        elif unmet_tool and utility <= 0:
            reason = "TOOL_REQUIRED"
        else:
            reason = "KEEP_KEY"
    else:
        reason = "NO_ACTION"
    return {"reason": reason, "utility": utility, "tool_goal_unmet": unmet_tool}


def a_input(checkpoint):
    view = actor_view(checkpoint, "A")
    return {"view": view, "input_hash": _hash(view),
            "assumptions": ["B follows the disclosed deterministic policy contract",
                            "LoanKey(offer_id) is a delayed symbolic binding until B discloses key1"]}


def forecast_b_from_a(view):
    """Forecast contract-level choices from A's view; never inspect actual O_B."""
    facts = set(view["observation"]["known_facts"])
    contract = view["contract"]
    need_tool = "toolB_held_by_A" in facts
    utility = 2 - contract["c"] - (contract["p"] if need_tool else 0)
    return {"reply": "ACCEPT" if utility > 0 else "DECLINE", "utility": utility,
            "assumption": "B has a loanable intact key if it accepts; this is hypothetical until disclosure"}
