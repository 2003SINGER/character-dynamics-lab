"""E1 development conditions copied from the frozen E0 P01 fixture."""
from copy import deepcopy

from tools.e0_keyledger_v0.fixtures import initial_checkpoint as e0_initial_checkpoint

POLICIES = {
    "PAY": {"c": 1, "p": 0},
    "TOOL": {"c": 1, "p": 4},
    "KEEP": {"c": 3, "p": 0},
}
CASE_IDS = tuple(f"E1-{k}-{p}-{t}" for k in ("known", "unknown")
                 for p in ("PAY", "TOOL", "KEEP") for t in (8, 10))
E1_PRODUCER_VERSION = "e1-keyledger-adapter-v0"


def initial_checkpoint(knowledge="known", policy="PAY", deadline=8):
    if knowledge not in ("known", "unknown") or policy not in POLICIES or deadline not in (8, 10):
        raise ValueError("invalid E1 condition")
    cp = deepcopy(e0_initial_checkpoint("E0-P01", deadline=10))
    cp["fixture_id"] = f"E1-{knowledge}-{policy}-{deadline}"
    cp["protocol_version"] = "E1-KeyLedger-LocalAgency-v0.r1"
    cp["config_pins"]["deadline"] = deadline
    cp["config_pins"]["reply"] = "JOINT"
    cp["config_pins"]["e1"] = {"knowledge": knowledge, "policy": policy, **POLICIES[policy]}
    cp["goals_A"] = ["ledger_acquired(actor=A,item=ledger)"]
    cp["goals_B"] = ["toolB_held_by_B", "payment_received", "key1_beneficial_owner_B"]
    cp["scheduler"] = {"initial_b_slot_pending": True, "slot": "B"}
    cp["actor_planning"] = {
        "budget": {"expansions": 0, "generated": 0, "elapsed_seconds": 0.0,
                   "max_expansions": 10000, "wall_seconds": 2.0},
        "assumptions": [], "late_binding_map": {}}
    cp["W"]["request_used"] = False
    cp["O"]["B"]["request_sent"] = False
    cp["O"]["B"]["request_sent_provenance"] = {
        "kind": "initial_actor_history", "event_id": None, "time": 2, "actor": "B"}
    contract = {"version": "E1-B-utility-v0", "policy": policy, **POLICIES[policy]}
    for who in ("A", "B"):
        cp["O"][who]["public_contract"] = deepcopy(contract)
        cp["O"][who]["public_contract_provenance"] = {
            "kind": "published_experiment_contract", "time": 2, "source": "E1 protocol"}
    if knowledge == "known":
        cp["O"]["A"]["known_entities"].append("key1")
        cp["O"]["A"]["known_facts"].append("key1_held_by_B")
    else:
        cp["O"]["A"]["known_entities"] = [x for x in cp["O"]["A"]["known_entities"] if x != "key1"]
        cp["O"]["A"]["known_facts"] = [x for x in cp["O"]["A"]["known_facts"] if x != "key1_held_by_B"]
    return cp


def primary_conditions():
    return [initial_checkpoint(k, p, t) for k in ("known", "unknown")
            for p in ("PAY", "TOOL", "KEEP") for t in (8, 10)]
