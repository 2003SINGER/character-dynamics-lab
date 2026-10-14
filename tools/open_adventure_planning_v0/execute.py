"""Thin, bounded B0 controller over the existing Open Adventure P1 Session."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
import uuid
from typing import Any

from tools.open_adventure_v0 import runner as p1_runner
from tools.open_adventure_v0.session import OpenAdventureSession, StepResult

from .domain import OPERATORS, State, initial_state
from .observe import Reconciliation, reconcile
from .search import Goal, SearchLimits, uniform_cost_search
from .verify import verify_ledger

PROJECT_ROOT = p1_runner.PROJECT_ROOT
RUNS_ROOT = PROJECT_ROOT / "02_实验/OpenAdventure_Planning_B0_v0/runs"
SEED = 20261014
INPUT_BUDGET = 80
SEARCH_EXPANSIONS = 10_000
SEARCH_SECONDS = 10.0
TOTAL_SEARCH_SECONDS = 120.0
P1_TIMEOUT_SECONDS = 20.0

GOALS = {
    "D": Goal(frozenset({("at", "player", "BELOWGRATE"),
                         ("carrying", "keys"), ("carrying", "lamp"), ("lamp_on",)})),
    "E": Goal(frozenset({("at", "player", "WESTBANK"), ("bridge",),
                         ("carrying", "keys"), ("carrying", "lamp"), ("lamp_on",)})),
}
GOAL_TEXT = {
    "D": "Reach BELOWGRATE while holding keys and lamp, lamp on, with no native death.",
    "E": "Create the crystal bridge and reach WESTBANK while holding keys and lamp, lamp on, with no native death.",
}


def _jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _goal_hash(goal: Goal) -> str:
    payload = json.dumps({"required": sorted(goal.required), "forbidden": sorted(goal.forbidden)},
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _native_question(text: str) -> str | None:
    folded = " ".join(text.casefold().split())
    if "welcome to adventure!! would you like instructions?" in folded:
        return "startup_instructions"
    if "do you really want to quit now?" in folded:
        return "quit_confirmation"
    if "are you trying to get into the cave?" in folded:
        return "cave_hint_confirmation"
    if "would you like a hint" in folded or "would you like help" in folded:
        return "hint_confirmation"
    return None


def _decline_cave_hint(session: OpenAdventureSession) -> StepResult:
    """Answer the one frozen, known, non-blocking cave hint question."""
    return session.step("n", controller="b0-native-question",
                        decision_source="decline known visible cave hint question")


def _expected_action(action: Any, observed: Reconciliation) -> bool:
    if action.name == "move":
        return observed.observed_room == action.args[2]
    if action.name == "take":
        return f"native_take_ok:{action.args[1]}" in observed.evidence
    if action.name == "drop":
        return f"native_drop_ok:{action.args[1]}" in observed.evidence
    if action.name == "lamp_on":
        return "native_lamp_on" in observed.evidence
    if action.name == "lamp_off":
        return "native_lamp_off" in observed.evidence
    if action.name == "unlock":
        return "native_grate_open" in observed.evidence
    if action.name == "lock":
        return "native_grate_closed" in observed.evidence
    if action.name == "wave_rod":
        return ("native_bridge_present" in observed.evidence
                or "native_bridge_absent" in observed.evidence)
    return False


def _goal_complete(goal: Goal, state: State) -> bool:
    return goal.satisfied(state)


def _run_unsupported(goal_id: str) -> dict[str, Any]:
    return {"goal_id": goal_id, "status": "UNSUPPORTED_SEMANTICS",
            "evidence": "Open Adventure has no registered pirate trust state, help attribution, or later trust-consumption mechanism.",
            "native_inputs": 0, "search_calls": 0, "model_calls": "NOT_RUN"}


def run_episode(goal_id: str, *, scenario: str, execute_native: bool) -> dict[str, Any]:
    if goal_id == "G":
        return _run_unsupported(goal_id)
    if goal_id not in GOALS:
        raise ValueError("goal_id must be D, E, or G")
    if not execute_native:
        raise RuntimeError("native execution requires the explicit --execute-native switch")
    if scenario not in ("clean", "feedback_negative_control"):
        raise ValueError("unknown frozen scenario")
    if scenario == "feedback_negative_control" and goal_id != "D":
        raise ValueError("negative control is defined only for D")

    episode_id = f"oa-b0-{goal_id}-{scenario}-{uuid.uuid4().hex[:10]}"
    session = OpenAdventureSession(runs_root=RUNS_ROOT, timeout=P1_TIMEOUT_SECONDS)
    task_inputs = 0
    search_calls = 0
    total_search_seconds = 0.0
    decision_path: Path | None = None
    frozen_goal = GOALS[goal_id]
    state = initial_state()
    status = "RUNNING"
    buffered_injection: list[StepResult] = []
    intervention_done = False
    current_plan: tuple[Any, ...] = ()
    plan_index = 0

    try:
        first = session.reset({
            "experiment_config_version": "open-adventure-planning-b0-v0",
            "episode_id": episode_id, "goal_id": goal_id,
            "goal_text": GOAL_TEXT[goal_id], "goal_predicate_sha256": _goal_hash(frozen_goal),
            "controller": "B0 forward uniform-cost search, h=0",
            "domain_label": "finite source-derived model; STATIC_MODEL_ASSUMPTION initial map/object positions",
            "model_calls": "NOT_RUN", "rng_seed": SEED,
            "seed_timing": "after native startup answer n; pre-initialization randomness uncontrolled",
            "native_input_budget": INPUT_BUDGET,
            "search_limits": {"expansions_per_call": SEARCH_EXPANSIONS,
                              "seconds_per_call": SEARCH_SECONDS,
                              "total_seconds": TOTAL_SEARCH_SECONDS},
            "scenario": scenario,
        })
        assert session.run_dir is not None and session.log_path is not None
        decision_path = session.run_dir / "b0_trace.jsonl"
        package_root = Path(__file__).parent
        package_hashes = {}
        for filename in ("PROTOCOL.md", "domain.py", "search.py", "observe.py", "verify.py", "execute.py"):
            source = (PROJECT_ROOT / "02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md"
                      if filename == "PROTOCOL.md" else package_root / filename)
            package_hashes[filename] = hashlib.sha256(source.read_bytes()).hexdigest()
        _jsonl(decision_path, {
            "event": "b0_start", "episode_id": episode_id, "goal_id": goal_id,
            "goal_predicate_sha256": _goal_hash(frozen_goal),
            "model_calls": "NOT_RUN", "controller": "unit-cost UCS h=0",
            "static_model_assumptions": {
                "player_room": "START", "keys_room": "BUILDING",
                "lamp_room": "BUILDING", "rod_room": "DEBRIS",
                "lamp_on": False, "grate_closed": True, "fissure_unbridged": True,
            },
            "exogenous_risks": ["native dwarf startup/random attack", "lamp energy/blackness",
                                "unmodeled object/NPC behavior; no seed screening"],
            "code_operator_count": len(OPERATORS),
            "b0_source_sha256": package_hashes,
        })
        if not session._initial_input_boundary or session._initial_timed_out:
            status = "INCOMPLETE_INITIAL_OBSERVATION"
            return _summary(goal_id, status, session, task_inputs, search_calls,
                            total_search_seconds, decision_path)

        # The first native response is the fixed startup question. Its answer
        # and the seed command are setup inputs outside the 80 task-input cap.
        startup = session.step("n", controller="b0-bootstrap",
                               decision_source="fixed native startup answer")
        if not startup.input_boundary_reached:
            status = "INCOMPLETE_STARTUP"
            return _summary(goal_id, status, session, task_inputs, search_calls,
                            total_search_seconds, decision_path)
        seed_step = session.step(f"seed {SEED}", controller="b0-bootstrap",
                                 decision_source="fixed protocol seed after startup answer")
        if not seed_step.input_boundary_reached:
            status = "INCOMPLETE_SEED"
            return _summary(goal_id, status, session, task_inputs, search_calls,
                            total_search_seconds, decision_path)
        boot = reconcile(state, startup.observation, command="n")
        if boot.observed_room:
            state = boot.state
        _jsonl(decision_path, {"event": "bootstrap", "startup_complete": True,
                               "seed": SEED, "startup_room": boot.observed_room,
                               "initial_raw_ledger": str(session.log_path)})

        while task_inputs < INPUT_BUDGET:
            if total_search_seconds >= TOTAL_SEARCH_SECONDS:
                status = "BUDGET"
                break
            limits = SearchLimits(SEARCH_EXPANSIONS,
                                  min(SEARCH_SECONDS, TOTAL_SEARCH_SECONDS - total_search_seconds))
            result = uniform_cost_search(state, frozen_goal, limits=limits)
            search_calls += 1
            total_search_seconds += result.elapsed_seconds
            _jsonl(decision_path, {
                "event": "search", "call": search_calls, "status": result.status,
                "expansions": result.expansions, "generated": result.generated,
                "duplicate_states": result.duplicate_states,
                "frontier_peak": result.frontier_peak,
                "elapsed_seconds": result.elapsed_seconds, "reason": result.reason,
                "state_sha256": hashlib.sha256(repr(sorted(state)).encode()).hexdigest(),
                "goal_predicate_sha256": _goal_hash(frozen_goal),
                "remaining_task_inputs": INPUT_BUDGET - task_inputs,
            })
            if result.status != "FOUND":
                status = result.status
                break
            current_plan = result.plan
            plan_index = 0
            if not current_plan:
                status = "MODEL_GOAL_REACHED"
                break
            action = current_plan[0]

            if scenario == "feedback_negative_control" and not intervention_done and action.name == "unlock":
                intervention_done = True
                for command in ("build", "in", "drop keys", "out", "depre"):
                    if task_inputs >= INPUT_BUDGET:
                        status = "BUDGET_INPUTS"
                        break
                    row = session.step(command, controller="b0-harness-injection",
                                      decision_source="frozen visible-input delay fault; not delivered to strategy yet")
                    task_inputs += 1
                    buffered_injection.append(row)
                    _jsonl(decision_path, {
                        "event": "fault_injection_input", "command": command,
                        "step_sequence": row.sequence, "input_count": task_inputs,
                        "raw_output_deferred": True, "stale_plan_sha256": hashlib.sha256(
                            repr(tuple(a.command for a in current_plan)).encode()).hexdigest(),
                        "complete": row.input_boundary_reached,
                    })
                    if not row.input_boundary_reached:
                        status = "INCOMPLETE_INJECTION"
                        break
                if status != "RUNNING":
                    break
                continue

            if task_inputs >= INPUT_BUDGET:
                status = "BUDGET_INPUTS"
                break
            planned_hash = hashlib.sha256(
                repr(tuple(a.command for a in current_plan)).encode()).hexdigest()
            step = session.step(action.command, controller="b0-ucs",
                                decision_source=f"first primitive of UCS plan {planned_hash}")
            task_inputs += 1
            _jsonl(decision_path, {
                "event": "decision", "step_sequence": step.sequence,
                "input_count": task_inputs, "plan_hash": planned_hash,
                "predicted_plan": [{"operator": a.name, "args": list(a.args),
                                    "command": a.command} for a in current_plan],
                "plan_is_prediction_only": True,
                "plan_index": plan_index, "operator": action.name,
                "operator_args": action.args, "command": action.command,
                "before_state_sha256": hashlib.sha256(repr(sorted(state)).encode()).hexdigest(),
                "native_complete": step.input_boundary_reached,
                "native_terminated": step.terminated, "native_error": step.error,
            })
            if not step.input_boundary_reached:
                status = "INCOMPLETE_NATIVE_FEEDBACK"
                break

            question = _native_question(step.observation)
            if question is not None:
                if question == "cave_hint_confirmation" and task_inputs < INPUT_BUDGET:
                    answer = _decline_cave_hint(session)
                    task_inputs += 1
                    _jsonl(decision_path, {"event": "native_question", "kind": question,
                                           "answer": "n", "input_count": task_inputs,
                                           "trigger_step_sequence": step.sequence,
                                           "step_sequence": answer.sequence,
                                           "complete": answer.input_boundary_reached,
                                           "raw_output": answer.observation,
                                           "raw_output_is_not_planned_action": True})
                    if not answer.input_boundary_reached:
                        status = "INCOMPLETE_NATIVE_QUESTION_ANSWER"
                        break
                else:
                    status = ("BUDGET_INPUTS" if question == "cave_hint_confirmation"
                              else "NATIVE_QUESTION_UNSUPPORTED")
                    break

            # Frozen fault: keep the old planned unlock through the intervention.
            # Only after the native rejection do we deliver the buffered public
            # responses, in their original order, followed by fresh look/inventory.
            observed = reconcile(state, step.observation, command=action.command)
            expected = _expected_action(action, observed)
            if not expected:
                _jsonl(decision_path, {"event": "model_mismatch",
                                       "step_sequence": step.sequence,
                                       "operator": action.name, "command": action.command,
                                       "native_output": step.observation,
                                       "feedback_delay_injection_active": bool(buffered_injection)})
                refresh_rows = list(buffered_injection)
                buffered_injection.clear()
                for delayed in refresh_rows:
                    reconciled = reconcile(state, delayed.observation, command=delayed.command,
                                           complete=delayed.input_boundary_reached)
                    if reconciled.status in ("INCOMPLETE", "UNMODELED_EVENT"):
                        status = reconciled.status
                        break
                    state = reconciled.state
                    _jsonl(decision_path, {"event": "delayed_visible_feedback_delivered",
                                           "step_sequence": delayed.sequence,
                                           "command": delayed.command,
                                           "reconcile_status": reconciled.status,
                                           "evidence": reconciled.evidence,
                                           "state_sha256": hashlib.sha256(repr(sorted(state)).encode()).hexdigest()})
                if status == "RUNNING":
                    failure = reconcile(state, step.observation, command=action.command)
                    _jsonl(decision_path, {"event": "native_failure_feedback",
                                           "step_sequence": step.sequence,
                                           "evidence": failure.evidence,
                                           "state_changed_from_failure": failure.state != state})
                    if failure.status == "UNMODELED_EVENT":
                        status = failure.status
                        break
                    if failure.state != state:
                        state = failure.state
                    refreshed_with_evidence = False
                    for command in ("look", "inventory"):
                        if task_inputs >= INPUT_BUDGET:
                            status = "BUDGET_INPUTS"
                            break
                        refresh = session.step(command, controller="b0-refresh",
                                               decision_source="generic visible-state refresh after native rejection")
                        task_inputs += 1
                        reconciled = reconcile(state, refresh.observation, command=command,
                                               complete=refresh.input_boundary_reached)
                        _jsonl(decision_path, {"event": "refresh_observation",
                                               "step_sequence": refresh.sequence,
                                               "command": command, "input_count": task_inputs,
                                               "reconcile_status": reconciled.status,
                                               "evidence": reconciled.evidence})
                        if not refresh.input_boundary_reached or reconciled.status in ("INCOMPLETE", "UNMODELED_EVENT"):
                            status = reconciled.status if refresh.input_boundary_reached else "INCOMPLETE_NATIVE_FEEDBACK"
                            break
                        state = reconciled.state
                        refreshed_with_evidence = refreshed_with_evidence or bool(reconciled.evidence)
                    if status == "RUNNING" and not refreshed_with_evidence:
                        status = "MODEL_MISMATCH"
                    if status == "RUNNING":
                        continue
                    break
                if status != "RUNNING":
                    break
            _jsonl(decision_path, {"event": "reconciliation",
                                   "step_sequence": step.sequence,
                                   "status": observed.status, "evidence": observed.evidence,
                                   "observed_room": observed.observed_room,
                                   "state_sha256": hashlib.sha256(repr(sorted(observed.state)).encode()).hexdigest()})
            if observed.status in ("INCOMPLETE", "UNMODELED_EVENT"):
                status = observed.status
                break
            if not expected:
                status = "MODEL_MISMATCH"
                break
            state = observed.state
            if _goal_complete(frozen_goal, state):
                # These final observations are native inputs and consume budget.
                for command in ("look", "inventory"):
                    if task_inputs >= INPUT_BUDGET:
                        status = "BUDGET_INPUTS"
                        break
                    audit = session.step(command, controller="b0-final-observation",
                                         decision_source="frozen independent-goal evidence collection")
                    task_inputs += 1
                    reconciled = reconcile(state, audit.observation, command=command,
                                           complete=audit.input_boundary_reached)
                    _jsonl(decision_path, {"event": "final_observation",
                                           "command": command, "step_sequence": audit.sequence,
                                           "input_count": task_inputs,
                                           "reconcile_status": reconciled.status,
                                           "evidence": reconciled.evidence})
                    if not audit.input_boundary_reached:
                        status = "INCOMPLETE_NATIVE_FEEDBACK"
                        break
                    state = reconciled.state
                else:
                    status = verify_ledger(session.log_path, goal_id)["status"]
                break
        else:
            status = "BUDGET_INPUTS"

        result = verify_ledger(session.log_path, goal_id)
        _jsonl(decision_path, {"event": "episode_result", "status": status,
                               "independent_verifier": result,
                               "native_task_inputs": task_inputs,
                               "search_calls": search_calls,
                               "search_seconds": total_search_seconds,
                               "model_calls": "NOT_RUN"})
        return _summary(goal_id, status, session, task_inputs, search_calls,
                        total_search_seconds, decision_path, verifier=result)
    finally:
        session.close()


def _summary(goal_id: str, status: str, session: OpenAdventureSession,
             task_inputs: int, search_calls: int, search_seconds: float,
             trace_path: Path | None, *, verifier: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "goal_id": goal_id, "status": status,
        "run_dir": str(session.run_dir) if session.run_dir else None,
        "native_ledger": str(session.log_path) if session.log_path else None,
        "decision_trace": str(trace_path) if trace_path else None,
        "native_task_inputs_including_refreshes": task_inputs,
        "bootstrap_and_cleanup_inputs_recorded_separately": {"bootstrap": 2, "cleanup": "session.close process cleanup; not a game success"},
        "search_calls": search_calls, "search_seconds": search_seconds,
        "model_calls": "NOT_RUN", "verifier": verifier,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True, choices=("D", "E", "G"))
    parser.add_argument("--scenario", default="clean",
                        choices=("clean", "feedback_negative_control"))
    parser.add_argument("--execute-native", action="store_true",
                        help="required explicit switch to launch the original game")
    args = parser.parse_args()
    print(json.dumps(run_episode(args.goal, scenario=args.scenario,
                                 execute_native=args.execute_native),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
