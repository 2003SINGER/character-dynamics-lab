"""Two real actor-planner implementations behind a narrow view -> proposal seam.

GOAP reuses frozen E1 UCS; HTN uses installed GTPyhop's backtracking search.
Neither executes B's forecast actions or consumes W.
"""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import os
import threading
import time

from tools.e1_keyledger_v0.planner import uniform_cost_search

_LOCK = threading.RLock()


def failure(status, reason):
    return {"solve_status": status, "termination_reason": reason, "selected_action": None,
            "forecast_plan": [], "forecast_plan_prediction_only": True}


def propose(view, implementation="goap", max_expansions=1000, wall_seconds=.5):
    if implementation not in ("goap", "htn"):
        raise ValueError("planner must be goap or htn")
    if "key1_destroyed" in view["observation"]["known_facts"] and "archive_open" not in view["observation"]["known_facts"]:
        return failure("UNREACHABLE_UNDER_LOCAL_MODEL", "observed required resource destruction")
    if max_expansions <= 0 or wall_seconds <= 0:
        return failure("BUDGET", "configured planning budget exhausted")
    if implementation == "goap":
        result = uniform_cost_search(deepcopy(view), max_expansions=max_expansions, wall_seconds=wall_seconds)
        # E1's finite proof is conditional on a public response model, not a world guarantee.
        result["proof_scope"] = "finite symbolic domain under disclosed contract"
        return result
    return _htn(view, max_expansions, wall_seconds)


def _htn(view, cap, wall_seconds):
    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("HTN requires pip install -r tools/npc_system_v0/requirements.txt; no silent fallback") from exc
    start = time.monotonic()
    visits = 0
    exhausted = False

    def budget():
        nonlocal visits, exhausted
        visits += 1
        if visits > cap or time.monotonic() - start >= wall_seconds:
            exhausted = True
            return False
        return True

    def advance(state, amount):
        state.t += amount
        return state if state.t <= state.deadline else False

    def return_tool(state):
        if not budget() or not state.tool_out:
            return False
        state.tool_out = False
        return advance(state, 1)

    def offer_loan(state):
        # Reply/exchange are explicitly hypothetical public-contract effects.
        if not budget() or state.offered or 2 - state.c - (state.p if state.tool_out else 0) <= 0:
            return False
        state.offered, state.exchanged = True, True
        return advance(state, 3)

    def unlock(state):
        if not budget() or not state.exchanged or state.open:
            return False
        state.open = True
        return advance(state, 1)

    def take_ledger(state):
        if not budget() or not state.open:
            return False
        state.acquired = True
        return advance(state, 1)

    def already_done(state):
        return [] if budget() and state.acquired else None

    def take_if_open(state):
        return [("take_ledger",)] if budget() and state.open and not state.acquired else None

    def open_if_borrowed(state):
        return [("unlock",), ("acquire_ledger",)] if budget() and state.exchanged and not state.open else None

    def borrow_direct(state):
        if budget() and not state.offered and 2 - state.c - (state.p if state.tool_out else 0) > 0:
            return [("offer_loan",), ("acquire_ledger",)]
        return None

    def borrow_after_return(state):
        if budget() and not state.offered and state.tool_out and 2 - state.c > 0:
            return [("return_tool",), ("offer_loan",), ("acquire_ledger",)]
        return None

    facts = set(view["observation"]["known_facts"])
    state = g.State("actor-local-belief")
    state.t, state.deadline = view["clock"]["now"], view["deadline"]
    state.c, state.p = view["contract"]["c"], view["contract"]["p"]
    state.tool_out, state.offered = "toolB_held_by_A" in facts, "offer_visible" in facts
    state.exchanged, state.open = "exchange_visible" in facts, "archive_open" in facts
    state.acquired = any(e["event_type"] == "ledger_acquired" for e in view["observation"].get("known_events", []))
    # Domain construction uses GTPyhop's legacy current-domain API; isolate it.
    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("npc-system-local-htn")
            g.declare_actions(return_tool, offer_loan, unlock, take_ledger)
            g.declare_task_methods("acquire_ledger", already_done, take_if_open,
                                   open_if_borrowed, borrow_direct, borrow_after_return)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking", verbose=0,
                                  structured_logging=False) as session:
                result = session.find_plan(state, [("acquire_ledger",)], timeout_ms=int(wall_seconds * 1000))
        finally:
            main.current_domain = previous
    if exhausted or time.monotonic() - start >= wall_seconds:
        return failure("BUDGET", "cooperative method/action cap or wall watchdog")
    if not result.success:
        return failure("NO_PLAN_UNDER_HTN_METHODS", "method frontier exhausted; not general impossibility")
    path = []
    for step in result.plan:
        op = step[0]
        args = {"return_tool": {"target": "B", "item": "toolB"},
                "offer_loan": {"target": "B", "payment": "payment"},
                "unlock": {"item": "key1"}, "take_ledger": {"item": "ledger"}}[op]
        if op == "unlock" and "key1" not in view["observation"]["known_entities"]:
            args = {"item": {"symbol": "LoanKey", "binding": "requires B disclosure"}}
        path.append({"operator": op, "actor": "A", "args": args})
    return {"solve_status": "SOLVED", "selected_action": path[0] if path else None,
            "forecast_plan": path, "forecast_plan_prediction_only": True,
            "unresolved_bindings_dispatchable": False, "implementation": "GTPyhop-" + g.__version__,
            "method_action_visits": visits, "elapsed_seconds": time.monotonic() - start}
