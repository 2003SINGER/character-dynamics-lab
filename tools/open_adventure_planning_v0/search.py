"""Goal-independent, unit-cost forward search for the frozen B0 operators."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import time
from typing import Iterable

from .domain import Atom, OPERATORS, Operator, State


@dataclass(frozen=True)
class Goal:
    required: frozenset[Atom]
    forbidden: frozenset[Atom] = frozenset()

    def satisfied(self, state: State) -> bool:
        return self.required <= state and not (self.forbidden & state)


@dataclass(frozen=True)
class SearchLimits:
    max_expansions: int = 10_000
    max_seconds: float = 10.0


@dataclass(frozen=True)
class SearchResult:
    status: str
    plan: tuple[Operator, ...]
    expansions: int
    generated: int
    duplicate_states: int
    frontier_peak: int
    elapsed_seconds: float
    reason: str | None = None


def uniform_cost_search(initial: State, goal: Goal, *,
                        operators: Iterable[Operator] = OPERATORS,
                        limits: SearchLimits = SearchLimits()) -> SearchResult:
    """Classic forward UCS (h=0), with distinct finite exhaustion and budgets."""
    if limits.max_expansions < 0 or limits.max_seconds <= 0:
        raise ValueError("search limits must be nonnegative expansions and positive seconds")
    started = time.monotonic()
    ops = tuple(operators)
    queue: list[tuple[int, int, State]] = [(0, 0, initial)]
    serial = 1
    parent: dict[State, tuple[State, Operator] | None] = {initial: None}
    cost: dict[State, int] = {initial: 0}
    expansions = generated = duplicates = 0
    peak = 1

    def result(status: str, state: State | None = None, reason: str | None = None) -> SearchResult:
        plan: list[Operator] = []
        if state is not None:
            cursor = state
            while parent[cursor] is not None:
                previous, action = parent[cursor]  # type: ignore[misc]
                plan.append(action)
                cursor = previous
            plan.reverse()
        return SearchResult(status, tuple(plan), expansions, generated, duplicates,
                            peak, time.monotonic() - started, reason)

    while queue:
        if time.monotonic() - started >= limits.max_seconds:
            return result("BUDGET", reason="time_limit")
        _, _, state = heapq.heappop(queue)
        if goal.satisfied(state):
            return result("FOUND", state)
        if expansions >= limits.max_expansions:
            return result("BUDGET", reason="expansion_limit")
        expansions += 1
        next_cost = cost[state] + 1
        for action in ops:
            if not action.applicable(state):
                continue
            successor = action.apply(state)
            generated += 1
            if next_cost >= cost.get(successor, 1 << 60):
                duplicates += 1
                continue
            cost[successor] = next_cost
            parent[successor] = (state, action)
            heapq.heappush(queue, (next_cost, serial, successor))
            serial += 1
        peak = max(peak, len(queue))
    return result("EXHAUSTED_FINITE_MODEL", reason="frontier_empty")
