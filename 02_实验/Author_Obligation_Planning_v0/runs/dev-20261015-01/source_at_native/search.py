"""UCS over the finite Open Adventure world × author-obligation monitor."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import time
from typing import Iterable

from ..open_adventure_planning_v0.domain import Atom, OPERATORS, Operator, State
from ..open_adventure_planning_v0.search import Goal, SearchLimits
from .contracts import (
    EVENTS,
    EvidenceEvent,
    Eventually,
    InOrder,
    MaxCount,
    Never,
    Obligation,
    TaskSpec,
    TaskSpecError,
)


@dataclass(frozen=True)
class ProgressSnapshot:
    """Finite, task-specific summary of append-only event history."""

    eventually_satisfied: tuple[bool, ...]
    ordered_cursors: tuple[int, ...]
    event_counts: tuple[tuple[str, int, int], ...]
    violations: tuple[str, ...]
    death_seen: bool
    complete: bool
    history_events_used: int
    history_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlanningResult:
    status: str
    plan: tuple[Operator, ...]
    expansions: int
    generated: int
    duplicate_states: int
    frontier_peak: int
    elapsed_seconds: float
    reason: str | None
    task_id: str
    task_version: str
    history_events_used: int
    history_source_ids: tuple[str, ...]
    final_progress: ProgressSnapshot


@dataclass(frozen=True)
class _ProgressKey:
    eventual: tuple[bool, ...]
    cursors: tuple[int, ...]
    counts: tuple[int, ...]
    violated: tuple[bool, ...]
    death_seen: bool


@dataclass(frozen=True)
class _ProductState:
    world: State
    progress: _ProgressKey


def compile_history_progress(task: TaskSpec,
                             history: Iterable[EvidenceEvent]) -> ProgressSnapshot:
    """Compile the full evidence history anew for this exact task version."""
    events = _validated_history(history)
    progress = _initial_progress(task)
    for sequence, batch in _by_sequence(events):
        progress = _advance(task, progress, tuple(event.name for event in batch))
    return _snapshot(task, progress, events)


def plan_task(initial: State, task: TaskSpec, *,
              history: Iterable[EvidenceEvent] = (),
              operators: Iterable[Operator] = OPERATORS,
              limits: SearchLimits = SearchLimits()) -> PlanningResult:
    """Run unit-cost forward UCS on (world state, bounded author progress).

    Existing native history is recompiled for every call; no progress from a
    replaced task version is accepted. The supplied operators remain in their
    original order and are filtered only by the actor's current source room.
    """
    if limits.max_expansions < 0 or limits.max_seconds <= 0:
        raise ValueError("search limits must be nonnegative expansions and positive seconds")
    evidence = _validated_history(history)
    start_progress = _initial_progress(task)
    for _, batch in _by_sequence(evidence):
        start_progress = _advance(task, start_progress, tuple(event.name for event in batch))

    started = time.monotonic()
    ops = tuple(operators)
    room_ops = _operators_by_source_room(ops)
    start = _ProductState(initial, start_progress)
    queue: list[tuple[int, int, _ProductState]] = [(0, 0, start)]
    serial = 1
    parent: dict[_ProductState, tuple[_ProductState, Operator] | None] = {start: None}
    costs: dict[_ProductState, int] = {start: 0}
    expansions = generated = duplicates = 0
    peak = 1

    def result(status: str, node: _ProductState | None = None,
               reason: str | None = None) -> PlanningResult:
        plan: list[Operator] = []
        if node is not None:
            cursor = node
            while parent[cursor] is not None:
                previous, action = parent[cursor]  # type: ignore[misc]
                plan.append(action)
                cursor = previous
            plan.reverse()
            final_progress = node.progress
        else:
            final_progress = start_progress
        snapshot = _snapshot(task, final_progress, evidence)
        return PlanningResult(
            status=status,
            plan=tuple(plan),
            expansions=expansions,
            generated=generated,
            duplicate_states=duplicates,
            frontier_peak=peak,
            elapsed_seconds=time.monotonic() - started,
            reason=reason,
            task_id=task.id,
            task_version=task.version,
            history_events_used=len(evidence),
            history_source_ids=tuple(event.source_id for event in evidence),
            final_progress=snapshot,
        )

    while queue:
        if time.monotonic() - started >= limits.max_seconds:
            return result("BUDGET", reason="time_limit")
        _, _, node = heapq.heappop(queue)
        if _goal_and_obligations_satisfied(task, node.world, node.progress):
            return result("FOUND", node)
        if _has_violation(task, node.progress):
            continue
        if expansions >= limits.max_expansions:
            return result("BUDGET", reason="expansion_limit")
        expansions += 1

        next_cost = costs[node] + 1
        for action in _applicable_room_ops(node.world, room_ops, ops):
            if not action.applicable(node.world):
                continue
            successor_world = action.apply(node.world)
            generated += 1
            emitted = _transition_events(node.world, successor_world)
            successor_progress = _advance(task, node.progress, emitted)
            successor = _ProductState(successor_world, successor_progress)
            if next_cost >= costs.get(successor, 1 << 60):
                duplicates += 1
                continue
            costs[successor] = next_cost
            parent[successor] = (node, action)
            heapq.heappush(queue, (next_cost, serial, successor))
            serial += 1
        peak = max(peak, len(queue))

    return result("EXHAUSTED_FINITE_MODEL", reason="frontier_empty")


def _initial_progress(task: TaskSpec) -> _ProgressKey:
    _validate_task(task)
    eventual = tuple(False for obligation in task.obligations
                     if isinstance(obligation, Eventually))
    cursors = tuple(0 for obligation in task.obligations
                    if isinstance(obligation, InOrder))
    counts = tuple(0 for obligation in task.obligations
                   if isinstance(obligation, MaxCount))
    violated = tuple(False for _ in task.obligations)
    return _ProgressKey(eventual, cursors, counts, violated, False)


def _advance(task: TaskSpec, progress: _ProgressKey,
             emitted: tuple[str, ...]) -> _ProgressKey:
    eventual_values = list(progress.eventual)
    cursor_values = list(progress.cursors)
    count_values = list(progress.counts)
    violated_values = list(progress.violated)
    event_index = 0
    cursor_index = 0
    count_index = 0
    death_seen = progress.death_seen

    # One transition/receipt may advance each strict sequence at most once,
    # even if its evidence contains several records with the same sequence.
    for obligation_index, obligation in enumerate(task.obligations):
        if isinstance(obligation, Eventually):
            if any(name == obligation.event for name in emitted):
                eventual_values[event_index] = True
            event_index += 1
        elif isinstance(obligation, InOrder):
            cursor = cursor_values[cursor_index]
            if cursor < len(obligation.events) and any(
                    name == obligation.events[cursor] for name in emitted):
                cursor_values[cursor_index] = cursor + 1
            cursor_index += 1
        elif isinstance(obligation, Never):
            if any(name == obligation.event for name in emitted):
                violated_values[obligation_index] = True
        elif isinstance(obligation, MaxCount):
            current = count_values[count_index]
            increment = sum(name == obligation.event for name in emitted)
            updated = min(obligation.maximum + 1, current + increment)
            count_values[count_index] = updated
            if updated > obligation.maximum:
                violated_values[obligation_index] = True
            count_index += 1

    if "player_death" in emitted:
        death_seen = True
    return _ProgressKey(tuple(eventual_values), tuple(cursor_values),
                        tuple(count_values), tuple(violated_values), death_seen)


def _snapshot(task: TaskSpec, progress: _ProgressKey,
              evidence: tuple[EvidenceEvent, ...]) -> ProgressSnapshot:
    event_counts: list[tuple[str, int, int]] = []
    count_index = 0
    eventual_index = 0
    cursor_index = 0
    violations: list[str] = []
    all_done = True
    for index, obligation in enumerate(task.obligations):
        if isinstance(obligation, Eventually):
            done = progress.eventual[eventual_index]
            eventual_index += 1
            all_done = all_done and done
            if not done:
                pass
        elif isinstance(obligation, InOrder):
            done = progress.cursors[cursor_index] >= len(obligation.events)
            cursor_index += 1
            all_done = all_done and done
        elif isinstance(obligation, MaxCount):
            count = progress.counts[count_index]
            count_index += 1
            event_counts.append((obligation.event, obligation.maximum, count))
        if progress.violated[index]:
            if isinstance(obligation, Never):
                violations.append(f"never:{obligation.event}")
            elif isinstance(obligation, MaxCount):
                violations.append(f"max_count:{obligation.event}>{obligation.maximum}")
    if task.always_no_death and progress.death_seen:
        violations.append("always_no_death:player_death")
    obligations_complete = all_done and not violations
    return ProgressSnapshot(
        eventually_satisfied=progress.eventual,
        ordered_cursors=progress.cursors,
        event_counts=tuple(event_counts),
        violations=tuple(violations),
        death_seen=progress.death_seen,
        complete=obligations_complete,
        history_events_used=len(evidence),
        history_source_ids=tuple(event.source_id for event in evidence),
    )


def _goal_and_obligations_satisfied(task: TaskSpec, state: State,
                                   progress: _ProgressKey) -> bool:
    if not task.goal.satisfied(state) or _has_violation(task, progress):
        return False
    snapshot = _snapshot(task, progress, ())
    return snapshot.complete


def _has_violation(task: TaskSpec, progress: _ProgressKey) -> bool:
    return any(progress.violated) or (task.always_no_death and progress.death_seen)


def _transition_events(before: State, after: State) -> tuple[str, ...]:
    """Infer registered events from changed predicates, never operator labels."""
    events: list[str] = []
    before_bridge = ("bridge",) in before
    after_bridge = ("bridge",) in after
    if not before_bridge and after_bridge:
        events.append("create_bridge")
    elif before_bridge and not after_bridge:
        events.append("destroy_bridge")
    before_room = _player_room(before)
    after_room = _player_room(after)
    if before_room != "WESTBANK" and after_room == "WESTBANK":
        events.append("arrive_west")
    if before_room == "WESTBANK" and after_room == "EASTBANK":
        events.append("return_east")
    if ("dead",) not in before and ("dead",) in after:
        events.append("player_death")
    return tuple(events)


def _player_room(state: State) -> str | None:
    rooms = [atom[2] for atom in state
             if len(atom) == 3 and atom[:2] == ("at", "player")]
    return rooms[0] if len(rooms) == 1 else None


def _operators_by_source_room(operators: tuple[Operator, ...]) -> dict[str, tuple[Operator, ...]]:
    mutable: dict[str, list[Operator]] = {}
    for action in operators:
        room = next((pre[2] for pre in action.preconditions
                     if len(pre) == 3 and pre[:2] == ("at", "player")), None)
        if room is not None:
            mutable.setdefault(room, []).append(action)
    return {room: tuple(actions) for room, actions in mutable.items()}


def _applicable_room_ops(state: State,
                         by_room: dict[str, tuple[Operator, ...]],
                         all_ops: tuple[Operator, ...]) -> tuple[Operator, ...]:
    room = _player_room(state)
    if room is None:
        return all_ops
    return by_room.get(room, ())


def _validated_history(history: Iterable[EvidenceEvent]) -> tuple[EvidenceEvent, ...]:
    events = tuple(history)
    previous_sequence = -1
    seen: set[tuple[int, str]] = set()
    for event in events:
        if not isinstance(event, EvidenceEvent):
            raise TaskSpecError("history entries must be EvidenceEvent instances")
        if event.sequence < previous_sequence:
            raise TaskSpecError("history must be supplied in nondecreasing sequence order")
        previous_sequence = event.sequence
        identity = (event.sequence, event.name)
        if identity in seen:
            raise TaskSpecError("a receipt sequence cannot contain the same event twice")
        seen.add(identity)
    return events


def _by_sequence(events: tuple[EvidenceEvent, ...]):
    batch: list[EvidenceEvent] = []
    current: int | None = None
    for event in events:
        if current is not None and event.sequence != current:
            yield current, tuple(batch)
            batch = []
        current = event.sequence
        batch.append(event)
    if current is not None:
        yield current, tuple(batch)


def _validate_task(task: TaskSpec) -> None:
    if not isinstance(task, TaskSpec):
        raise TaskSpecError("task must be a TaskSpec")

