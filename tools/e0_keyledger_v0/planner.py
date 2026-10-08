"""h=0 uniform-cost planner using Executor forks as its forward model.

The independent oracle must not import this module or its transition model.
"""

import heapq
import json
import time
from copy import deepcopy

from .executor import Executor, legal_intents


def _key(checkpoint):
    return json.dumps(checkpoint, sort_keys=True, separators=(",", ":"))


def _goal_event(checkpoint):
    """Read only receipt-backed sealed settlement events, never the Monitor summary."""
    producer = checkpoint["domain"]["producer_version"]
    deadline = checkpoint["config_pins"]["deadline"]
    for event in checkpoint["events"]:
        args = event["typed_args"]
        if (event.get("event_type") != "ledger_acquired" or args.get("event") != "ledger_acquired"
                or args.get("actor") != "A" or args.get("item") != "ledger"
                or event.get("producer_version") != producer or not 2 <= event.get("time", -1) <= deadline):
            continue
        receipt = next((item for item in checkpoint["receipts"]
                        if event["event_id"] in item.get("event_ids", [])), None)
        if (receipt is None or not receipt.get("accepted") or receipt.get("status") != "SUCCESS"
                or receipt.get("producer_version") != producer):
            continue
        if event not in receipt.get("event_payloads", []):
            continue
        if not any(seal.get("sealed_through", -1) >= event["time"]
                   and seal.get("sequence_frontier", -1) >= event.get("sequence", 10**18)
                   and seal.get("producer_version") == producer for seal in checkpoint["seals"]):
            continue
        return event
    return None


def uniform_cost_search(checkpoint, max_expansions=10000, wall_seconds=2.0):
    started = time.monotonic()
    initial = deepcopy(checkpoint)
    queue = [(0, 0, initial)]
    serial = 1
    visited = set()
    best_goal = None
    expansions = 0
    termination = "FRONTIER_EXHAUSTED"
    solve_status = "UNREACHABLE"
    complete, exhausted = True, True
    while queue:
        elapsed = time.monotonic() - started
        if expansions >= max_expansions:
            termination, solve_status, complete, exhausted = "STATE_CAP", "BUDGET", False, False
            break
        if elapsed >= wall_seconds:
            termination, solve_status, complete, exhausted = "WALL_TIMEOUT", "BUDGET", False, False
            break
        cost, _, state = heapq.heappop(queue)
        key = _key(state)
        if key in visited:
            continue
        visited.add(key)
        expansions += 1  # includes the initial state
        if _goal_event(state) is not None:
            best_goal = (cost, state)
            termination, solve_status, complete, exhausted = "SHORTEST_WITNESS_PROVEN", "WITNESS_FOUND", True, False
            break
        if state["clock"]["now"] >= state["config_pins"]["deadline"]:
            continue
        for action in legal_intents(state):
            branch = Executor(state)
            running = state["W"]["running_action"]
            if running is not None:
                branch.advance_minute()
            elif action["operator"] == "idle":
                branch.advance_minute()
            else:
                duration = state["config_pins"]["unlock_duration"] if action["operator"] == "unlock" else 1
                if state["clock"]["now"] + duration > state["config_pins"]["deadline"]:
                    continue
                receipt = branch.start(action)
                if not receipt["accepted"]:
                    continue
                branch.advance_minute(started_action_id=receipt["action_id"])
            next_state = branch.checkpoint()
            delta = next_state["clock"]["now"] - state["clock"]["now"]
            if delta <= 0 or next_state["clock"]["now"] > state["config_pins"]["deadline"]:
                continue
            heapq.heappush(queue, (cost + delta, serial, next_state))
            serial += 1
        if time.monotonic() - started >= wall_seconds:
            termination, solve_status, complete, exhausted = "WALL_TIMEOUT", "BUDGET", False, False
            break
    if best_goal is not None:
        cost, state = best_goal
        path = _path_from_history(state, initial)
        earliest = state["clock"]["now"]
        shortest = cost
    else:
        path, earliest, shortest = [], None, None
        if queue and not complete:
            solve_status = "BUDGET"
    return {"solve_status": solve_status, "termination_reason": termination,
            "complete": complete, "exhausted": exhausted, "expansions": expansions,
            "elapsed_seconds": time.monotonic() - started, "earliest_completion_time": earliest,
            "shortest_simulated_duration": shortest, "path": path,
            "frontier_count": len(queue), "visited_count": len(visited),
            "budget": {"max_expansions": max_expansions, "wall_seconds": wall_seconds}}


def _path_from_history(state, initial):
    before = len(initial["minute_history"])
    return deepcopy(state["minute_history"][before:])
