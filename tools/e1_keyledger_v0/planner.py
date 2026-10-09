"""A-local h=0 uniform-cost search over disclosed schemas and assumptions."""
from __future__ import annotations

from copy import deepcopy
import heapq
import json
import time


def restore_budget(saved, *, max_expansions=None, wall_seconds=None):
    """Rebuild a monotonic watchdog from serialized elapsed time, never its old clock."""
    max_expansions = saved.get("max_expansions", 10000) if max_expansions is None else max_expansions
    wall_seconds = saved.get("wall_seconds", 2.0) if wall_seconds is None else wall_seconds
    elapsed = float(saved.get("elapsed_seconds", 0.0))
    return {"expansions": int(saved.get("expansions", 0)),
            "generated": int(saved.get("generated", 0)),
            "started": time.monotonic() - elapsed,
            "max_expansions": max_expansions, "wall_seconds": wall_seconds}


def snapshot_budget(budget):
    return {"expansions": int(budget["expansions"]), "generated": int(budget["generated"]),
            "elapsed_seconds": max(0.0, time.monotonic() - budget["started"]),
            "max_expansions": int(budget["max_expansions"]),
            "wall_seconds": float(budget["wall_seconds"])}


ORDER = ("return_tool", "offer_loan", "unlock", "take_ledger", "idle")


def _key(state):
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


def uniform_cost_search(view, *, max_expansions=10000, wall_seconds=2.0, budget=None):
    """Search symbolic A-local states; the actual B observation is never supplied."""
    start_time = time.monotonic()
    ledger = budget if budget is not None else {"expansions": 0, "generated": 0,
                                                "started": start_time, "max_expansions": max_expansions,
                                                "wall_seconds": wall_seconds}
    now = view["clock"]["now"]
    deadline = view["deadline"]
    facts = set(view["observation"]["known_facts"])
    entities = set(view["observation"]["known_entities"])
    contract = view["contract"]
    # belief state contains only A observations and explicit hypothetical effects.
    initial = {"t": now, "facts": sorted(facts), "entities": sorted(entities),
               "offered": "offer_visible" in facts, "declined": "reply_decline_visible" in facts,
               "accepted": "reply_accept_visible" in facts, "exchanged": "exchange_visible" in facts,
               "open": "archive_open" in facts,
               "acquired": any(e.get("event_type") == "ledger_acquired"
                               and e.get("typed_args", {}).get("actor") == "A"
                               and e.get("typed_args", {}).get("item") == "ledger"
                               for e in view["observation"].get("known_events", [])),
               "offer_id": next((x for x in entities if x.startswith("offer-")), None),
               "loan_key": "key1" if "key1" in entities else None,
               "assumptions": []}
    queue = [(0, (), 0, initial, [])]
    serial = 1
    visited = set()
    while queue:
        if ledger["expansions"] >= max_expansions:
            return _result("BUDGET", False, False, "EXPANSION_CAP", ledger, [], None)
        if time.monotonic() - ledger["started"] >= wall_seconds:
            return _result("BUDGET", False, False, "WALL_TIMEOUT", ledger, [], None)
        cost, tie_key, _, state, path = heapq.heappop(queue)
        key = _key(state)
        if key in visited:
            continue
        visited.add(key)
        ledger["expansions"] += 1
        if state["acquired"]:
            return _result("SOLVED", True, False, "SHORTEST_SYMBOLIC_PLAN", ledger, path, state["t"])
        if state["t"] >= deadline:
            continue
        successors = []
        sf = set(state["facts"]); se = set(state["entities"])
        offer_id = state["offer_id"] or "offer-LoanKey"
        # Candidate enumeration depends only on A's typed catalogue and observation.
        if "toolB_held_by_A" in sf and "return_tool_visible" not in sf:
            nxt = deepcopy(state); nxt["t"] += 1
            nxt["facts"] = sorted((sf - {"toolB_held_by_A"}) | {"toolB_held_by_B", "tool_return_visible"})
            successors.append((1, {"operator": "return_tool", "actor": "A",
                "args": {"target": "B", "item": "toolB"}}, nxt))
        if not state["offered"] and "payment" in se and "offer_visible" not in sf:
            reply = "ACCEPT" if (2 - contract["c"] - (contract["p"] if "toolB_held_by_A" in sf else 0)) > 0 else "DECLINE"
            # Offer consumes one minute. B's real chooser is forecast from A's
            # public contract; reply/exchange costs are included in the search edge.
            nxt = deepcopy(state); nxt["offer_id"] = offer_id; nxt["offered"] = True
            nxt["t"] += 1
            nxt["facts"] = sorted(sf | {"offer_visible"} | ({"reply_accept_visible", "key1_disclosed_by_B"} if reply == "ACCEPT" else {"reply_decline_visible"}))
            nxt["entities"] = sorted(se | {offer_id})
            if reply == "ACCEPT":
                nxt["accepted"] = True
                nxt["loan_key"] = "key1" if "key1" in se else "LoanKey(" + offer_id + ")"
                nxt["assumptions"] = ["hypothetical: B has an intact lendable key; actual key ID requires B disclosure"]
                need_tool = "toolB_held_by_A" in sf
                if (2 - contract["c"] - (contract["p"] if need_tool else 0)) > 0:
                    nxt["t"] += 2
                    nxt["exchanged"] = True
                    nxt["facts"] = sorted(set(nxt["facts"]) | {"exchange_visible", "key1_held_by_A", "payment_held_by_B"})
                else:
                    # B accepts only under its own chooser utility, so this is defensive.
                    nxt["t"] += 1
            else:
                nxt["t"] += 1
            successors.append((nxt["t"] - state["t"], {"operator": "offer_loan", "actor": "A",
                "args": {"target": "B", "payment": "payment"}}, nxt))
        if state["exchanged"] and state["loan_key"] and not state["open"]:
            # Before disclosure the binding is a symbolic variable, never an
            # entity ID or dispatchable ActionIntent.
            if state["loan_key"] == "key1" and "key1" in se:
                nxt = deepcopy(state); nxt["t"] += 1; nxt["open"] = True
                nxt["facts"] = sorted(sf | {"archive_open", "unlock_visible"})
                successors.append((1, {"operator": "unlock", "actor": "A",
                    "args": {"item": "key1"}}, nxt))
            elif state["loan_key"].startswith("LoanKey("):
                nxt = deepcopy(state); nxt["t"] += 1; nxt["open"] = True
                nxt["facts"] = sorted(sf | {"archive_open", "unlock_visible"})
                successors.append((1, {"operator": "unlock", "actor": "A",
                    "args": {"item": {"symbol": "LoanKey", "offer_id": offer_id}}}, nxt))
        if state["open"] and not state["acquired"] and "ledger" in se:
            nxt = deepcopy(state); nxt["t"] += 1; nxt["acquired"] = True
            nxt["facts"] = sorted(sf | {"ledger_held_by_A"})
            successors.append((1, {"operator": "take_ledger", "actor": "A",
                "args": {"item": "ledger"}}, nxt))
        # A-slot idle is a legal no-control edge; include it in the finite UCS.
        nxt = deepcopy(state); nxt["t"] += 1
        successors.append((1, {"operator": "idle", "actor": "WorldStep", "args": {}}, nxt))
        successors.sort(key=lambda row: ORDER.index(row[1]["operator"]))
        for delta, action, nxt in successors:
            if nxt["t"] <= deadline:
                ledger["generated"] += 1
                ranks = tie_key + (ORDER.index(action["operator"]),)
                heapq.heappush(queue, (cost + delta, ranks, serial, nxt, path + [action]))
                serial += 1
    return _result("PROVEN_UNREACHABLE_IN_FINITE_DOMAIN", True, True,
                   "FRONTIER_EXHAUSTED", ledger, [], None)


def _result(status, complete, exhausted, reason, ledger, path, earliest):
    selected = deepcopy(path[0]) if path else None
    return {"solve_status": status, "complete": complete, "exhausted": exhausted,
            "termination_reason": reason, "expansions": ledger["expansions"],
            "generated": ledger["generated"], "elapsed_seconds": time.monotonic()-ledger["started"],
            "earliest_completion_time": earliest, "path": deepcopy(path),
            "selected_action": selected, "forecast_plan": deepcopy(path),
            "forecast_plan_prediction_only": True, "unresolved_bindings_dispatchable": False,
            "budget": {"max_expansions": ledger["max_expansions"],
                       "wall_seconds": ledger["wall_seconds"]}}
