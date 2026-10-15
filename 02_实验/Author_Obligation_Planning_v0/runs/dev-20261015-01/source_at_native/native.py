"""Bounded online controller for author-obligation planning tasks.

The planner's state is reconciled only from complete, player-visible native
receipts. Temporal author progress is rebuilt from the full receipt-derived
event history before every search; predicted operator effects never create
author events.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any

from tools.open_adventure_v0 import runner as p1_runner
from tools.open_adventure_v0.session import OpenAdventureSession, StepResult
from tools.open_adventure_planning_v0.domain import OPERATORS, State, initial_state
from tools.open_adventure_planning_v0.execute import (
    P1_TIMEOUT_SECONDS,
    _expected_action,
    _native_question,
    reconcile,
)
from tools.open_adventure_planning_v0.observe import parse_room
from tools.open_adventure_planning_v0.verify import DEATH_MARKERS
from tools.author_obligation_planning_v0.conflicts import (
    CONFLICT_PROVED,
    static_conflicts,
)
from tools.author_obligation_planning_v0.search import (
    EvidenceEvent,
    SearchLimits,
    compile_history_progress,
    plan_task,
)
from tools.author_obligation_planning_v0.tasks import (
    DYNAMIC_CASES,
    revise_after,
    serialize_task,
    task_by_id,
)


PROJECT_ROOT = p1_runner.PROJECT_ROOT
RUNS_ROOT = PROJECT_ROOT / "02_实验/OpenAdventure_Author_Obligation_Planning_v0/runs"
SEED = 20261014
INPUT_BUDGET = 80
SEARCH_EXPANSIONS = 10_000
SEARCH_SECONDS = 10.0
TOTAL_SEARCH_SECONDS = 120.0

def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=repr)
    if hasattr(value, "value"):
        return value.value
    return value


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                default=str) + "\n")


def _room_from_receipt(text: str) -> str | None:
    return parse_room(text)


def _room_in_state(state: State) -> str | None:
    return next((atom[2] for atom in state if len(atom) == 3
                 and atom[:2] == ("at", "player")), None)


class UnknownNativeEvent(ValueError):
    """A complete native receipt contains an unregistered temporal outcome."""


def _receipt_events(row: StepResult, *, before_room: str | None) -> list[EvidenceEvent]:
    """Extract registered temporal events from one complete raw native reply."""
    if not row.input_boundary_reached:
        return []
    if row.sent_bytes != row.intended_bytes:
        raise UnknownNativeEvent("complete prompt followed a partial native input write")
    text = row.raw_output.decode("utf-8", errors="replace")
    folded = text.casefold()
    command = row.command.strip().casefold()
    digest = hashlib.sha256(row.raw_output).hexdigest()
    source_id = f"native-step-{row.sequence}-sha256-{digest}"
    found: list[str] = []
    if command == "wave rod":
        if "a crystal bridge now spans the fissure" in folded:
            found.append("create_bridge")
        elif "the crystal bridge has vanished" in folded:
            found.append("destroy_bridge")
        elif not any(marker in folded for marker in (
                "nothing happens", "you aren't carrying", "you are not carrying",
                "you don't have", "you do not have", "you must be carrying")):
            raise UnknownNativeEvent("wave rod receipt has no registered bridge outcome")
    room = _room_from_receipt(text)
    if room == "WESTBANK" and before_room != "WESTBANK":
        found.append("arrive_west")
    if room == "EASTBANK" and before_room == "WESTBANK":
        found.append("return_east")
    if any(marker in folded for marker in DEATH_MARKERS):
        found.append("player_death")
    return [EvidenceEvent(name=name, source_id=source_id, sequence=row.sequence)
            for name in found]


def _progress_snapshot(task: Any, history: list[EvidenceEvent]) -> Any:
    return compile_history_progress(task, tuple(history))


def _add_receipt_events(task: Any, history: list[EvidenceEvent], row: StepResult,
                        trace_path: Path, *, delivery: str = "immediate",
                        before_room: str | None = None) -> Any:
    added = _receipt_events(row, before_room=before_room)
    before = _progress_snapshot(task, history)
    history.extend(added)
    after = _progress_snapshot(task, history)
    _append_jsonl(trace_path, {
        "event": "author_history_update", "native_sequence": row.sequence,
        "delivery": delivery, "events_added": _jsonable(added),
        "history_count": len(history),
        "pre_progress_sha256": _canonical_hash(before),
        "post_progress_sha256": _canonical_hash(after),
        "history_source_ids": [event.source_id for event in history],
        "progress": _jsonable(after),
    })
    return after


def _edit_for_trigger(task: Any, case: Any, trigger: str,
                      history: list[EvidenceEvent], trace_path: Path,
                      native_sequence: int) -> Any:
    before_progress = _progress_snapshot(task, history)
    revised = revise_after(task, trigger)
    after_progress = _progress_snapshot(revised, history)
    _append_jsonl(trace_path, {
        "event": "author_edit", "task_id": task.id,
        "trigger": trigger, "native_sequence": native_sequence,
        "before_task": serialize_task(task), "after_task": serialize_task(revised),
        "before_task_sha256": _canonical_hash(serialize_task(task)),
        "after_task_sha256": _canonical_hash(serialize_task(revised)),
        "pre_progress_sha256": _canonical_hash(before_progress),
        "post_progress_sha256": _canonical_hash(after_progress),
        "progress_recompiled_from_full_history": True,
        "history_source_ids": [event.source_id for event in history],
    })
    return revised


def _append_receipt(trace_path: Path, row: StepResult, *, input_count: int,
                    role: str, delivered: bool) -> None:
    _append_jsonl(trace_path, {
        "event": "native_receipt_reference", "sequence": row.sequence,
        "input_count": input_count, "role": role, "delivered_to_strategy": delivered,
        "command": row.command, "input_boundary_reached": row.input_boundary_reached,
        "terminated": row.terminated, "error": row.error,
        "raw_output_sha256": hashlib.sha256(row.raw_output).hexdigest(),
        "raw_output_b64": base64.b64encode(row.raw_output).decode("ascii"),
    })


def _run_summary(task: Any, status: str, session: OpenAdventureSession,
                 trace_path: Path | None, history: list[EvidenceEvent],
                 task_inputs: int, search_calls: int, search_seconds: float,
                 edit_log: list[dict[str, Any]], *, failure: str | None = None,
                 h4_intervention: dict[str, Any] | None = None,
                 search_status: str | None = None,
                 final_audit_status: str = "NOT_ATTEMPTED") -> dict[str, Any]:
    return {
        "task_id": task.id, "controller_status": status,
        "search_status": search_status,
        "author_verdict": "NOT_RUN_IN_CONTROLLER",
        "verification_status": "NOT_RUN_IN_CONTROLLER",
        "final_audit_status": final_audit_status,
        "run_dir": str(session.run_dir) if session.run_dir else None,
        "native_ledger": str(session.log_path) if session.log_path else None,
        "decision_trace": str(trace_path) if trace_path else None,
        "final_task": serialize_task(task),
        "final_author_history": _jsonable(history),
        "native_task_inputs_including_h4_and_refresh": task_inputs,
        "search_calls": search_calls, "search_seconds": search_seconds,
        "model_calls": "NOT_RUN", "failure": failure,
        "edit_log": edit_log, "h4_intervention": h4_intervention,
    }


def run_episode(task_id: str, *, execute_native: bool,
                external_task: Any | None = None,
                scenario: str = "clean", runs_root: Path | None = None,
                binary: Path | None = None, game_root: Path | None = None) -> dict[str, Any]:
    """Run one task once; this function never automatically retries an episode."""
    case = next((item for item in DYNAMIC_CASES if item.task.id == task_id), None)
    reference = case.task if case is not None else task_by_id(task_id)
    if hasattr(reference, "task"):
        reference = reference.task
    task = reference if external_task is None else external_task
    if task.id != task_id:
        raise ValueError("external_task.id must match task_id")
    if not execute_native:
        raise RuntimeError("native execution requires the explicit execute_native=True switch")
    if scenario not in {"clean", "h4_feedback_delay"}:
        raise ValueError("scenario must be clean or h4_feedback_delay")
    if scenario == "h4_feedback_delay" and task_id != "H4":
        raise ValueError("h4_feedback_delay is defined only for H4")
    if task_id == "H4" and scenario != "h4_feedback_delay":
        raise ValueError("H4 requires its frozen feedback-delay intervention")

    episode_id = f"oa-author-obligation-{task_id}-{scenario}-{uuid.uuid4().hex[:10]}"
    session_kwargs: dict[str, Any] = {
        "runs_root": RUNS_ROOT if runs_root is None else runs_root,
        "timeout": P1_TIMEOUT_SECONDS,
    }
    if binary is not None:
        session_kwargs["binary"] = binary
    if game_root is not None:
        session_kwargs["game_root"] = game_root
    session = OpenAdventureSession(**session_kwargs)
    trace_path: Path | None = None
    state: State = case.initial if case is not None else initial_state()
    history: list[EvidenceEvent] = []
    edit_log: list[dict[str, Any]] = []
    task_inputs = 0
    search_calls = 0
    search_seconds = 0.0
    status = "RUNNING"
    failure: str | None = None
    h4_intervention: dict[str, Any] | None = None
    h4_done = False
    search_status: str | None = None
    final_audit_status = "NOT_ATTEMPTED"

    def collect_final_audit() -> bool:
        """Capture fresh native state for the parent-owned independent monitor."""
        nonlocal state, task_inputs, status, failure, final_audit_status
        if task_inputs + 2 > INPUT_BUDGET:
            final_audit_status = "BUDGET"
            if status == "RUNNING":
                status = "BUDGET"
                failure = "input budget cannot cover final look and inventory"
            return False
        for command in ("look", "inventory"):
            audit = session.step(command, controller="author-obligation-final-audit",
                                 decision_source="fresh native receipt for independent verifier")
            task_inputs += 1
            _append_receipt(trace_path, audit, input_count=task_inputs,
                            role="final_audit", delivered=True)
            before_room = _room_in_state(state)
            current = reconcile(state, audit.observation, command=command,
                                complete=audit.input_boundary_reached)
            if not audit.input_boundary_reached or current.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                final_audit_status = "UNKNOWN"
                status = "UNKNOWN"
                failure = "final native audit incomplete or unmodeled"
                return False
            state = current.state
            _add_receipt_events(task, history, audit, trace_path,
                                before_room=before_room)
            _append_jsonl(trace_path, {"event": "final_audit_reconciled",
                                      "sequence": audit.sequence,
                                      "command": command, "status": current.status,
                                      "evidence": list(current.evidence),
                                      "state_sha256": _canonical_hash(sorted(state))})
        final_audit_status = "COMPLETE"
        return True

    try:
        initial_observation = session.reset({
            "experiment_config_version": "open-adventure-author-obligation-planning-v0",
            "episode_id": episode_id, "task_id": task.id,
            "task_version": task.version, "task": serialize_task(task),
            "scenario": scenario, "rng_seed": SEED,
            "seed_timing": "after native startup answer n; pre-initialization randomness uncontrolled",
            "native_task_input_budget": INPUT_BUDGET,
            "search_limits": {"expansions_per_call": SEARCH_EXPANSIONS,
                              "seconds_per_call": SEARCH_SECONDS,
                              "total_seconds": TOTAL_SEARCH_SECONDS},
            "model_calls": "NOT_RUN",
            "controller": "temporal author-obligation search over B0 finite operators",
        })
        if session.run_dir is None or session.log_path is None:
            raise RuntimeError("session reset did not allocate a native ledger")
        trace_path = session.run_dir / "author_obligation_trace.jsonl"
        _append_jsonl(trace_path, {
            "event": "episode_start", "episode_id": episode_id,
            "task": serialize_task(task), "task_sha256": _canonical_hash(serialize_task(task)),
            "scenario": scenario, "seed": SEED,
            "operator_count": len(OPERATORS),
            "initial_observation_sha256": hashlib.sha256(initial_observation.encode()).hexdigest(),
            "raw_native_ledger": str(session.log_path),
            "author_progress_source": "complete native receipt-derived event history only",
        })
        if not session._initial_input_boundary or session._initial_timed_out:
            status = "UNKNOWN"
            failure = "initial native observation did not reach a complete input boundary"
        else:
            startup = session.step("n", controller="author-obligation-bootstrap",
                                   decision_source="fixed native startup answer")
            _append_receipt(trace_path, startup, input_count=0, role="startup", delivered=True)
            if not startup.input_boundary_reached:
                status, failure = "UNKNOWN", "startup answer receipt incomplete"
            else:
                seed_step = session.step(f"seed {SEED}", controller="author-obligation-bootstrap",
                                         decision_source="fixed protocol seed after startup answer")
                _append_receipt(trace_path, seed_step, input_count=0, role="seed", delivered=True)
                if not seed_step.input_boundary_reached:
                    status, failure = "UNKNOWN", "seed receipt incomplete"
                else:
                    boot = reconcile(state, startup.observation, command="n")
                    if boot.status == "UNMODELED_EVENT":
                        status, failure = "UNKNOWN", "unmodeled event during startup"
                    else:
                        state = boot.state
                        _append_jsonl(trace_path, {"event": "bootstrap_complete",
                                                  "seed": SEED,
                                                  "startup_room": boot.observed_room,
                                                  "native_ledger": str(session.log_path)})

        while status == "RUNNING":
            if search_seconds >= TOTAL_SEARCH_SECONDS:
                status = "BUDGET"
                if task_id in {"H3", "H4"}:
                    collect_final_audit()
                break
            limits = SearchLimits(SEARCH_EXPANSIONS,
                                  min(SEARCH_SECONDS, TOTAL_SEARCH_SECONDS - search_seconds))
            progress = _progress_snapshot(task, history)
            conflict = static_conflicts(state, task, history=tuple(history))
            _append_jsonl(trace_path, {
                "event": "static_conflict_check",
                "task": serialize_task(task),
                "task_sha256": _canonical_hash(serialize_task(task)),
                "state_sha256": _canonical_hash(sorted(state)),
                "history_sha256": _canonical_hash(history),
                "certificate": conflict,
            })
            if conflict.get("status") == CONFLICT_PROVED:
                search_status = CONFLICT_PROVED
                status = CONFLICT_PROVED
                failure = "finite-model static conflict certificate; native monitor verdict remains independent"
                if task_id in {"H3", "H4"}:
                    collect_final_audit()
                break
            result = plan_task(state, task, history=tuple(history),
                               operators=OPERATORS, limits=limits)
            search_calls += 1
            search_seconds += result.elapsed_seconds
            search_status = result.status
            _append_jsonl(trace_path, {
                "event": "search", "call": search_calls,
                "status": result.status, "expansions": result.expansions,
                "generated": result.generated,
                "duplicate_states": result.duplicate_states,
                "frontier_peak": result.frontier_peak,
                "elapsed_seconds": result.elapsed_seconds,
                "reason": result.reason,
                "state_sha256": _canonical_hash(sorted(state)),
                "task": serialize_task(task),
                "task_sha256": _canonical_hash(serialize_task(task)),
                "progress_sha256": _canonical_hash(progress),
                "history_sha256": _canonical_hash(history),
                "active_task_input_sha256": _canonical_hash(serialize_task(task)),
                "history_events_used": result.history_events_used,
                "history_source_ids": list(result.history_source_ids),
                "plan_is_prediction_only": True,
                "remaining_task_inputs": INPUT_BUDGET - task_inputs,
            })
            if result.status != "FOUND":
                search_status = result.status
                status = result.status
                failure = result.reason or f"search ended with {result.status}"
                if task_id in {"H3", "H4"}:
                    prior_failure = failure
                    if collect_final_audit():
                        failure = prior_failure
                break
            plan = result.plan
            if not plan:
                status = ("PLANNER_GOAL_REACHED_UNVERIFIED"
                          if collect_final_audit() else status)
                break
            action = plan[0]

            if (task_id == "H4" and not h4_done and action.name == "unlock"
                    and ("at", "player", "GRATE") in state
                    and ("carrying", "keys") in state):
                injection_commands = ("build", "in", "drop keys", "out", "depre")
                if task_inputs + len(injection_commands) + 3 > INPUT_BUDGET:
                    status = "BUDGET"
                    failure = "input budget cannot cover H4 injection, unlock, and final refresh"
                    break
                before_progress = _progress_snapshot(task, history)
                before_progress_hash = _canonical_hash(before_progress)
                h4_done = True
                h4_intervention = {
                    "kind": "controller_visible_feedback_delay_negative_control",
                    "location_basis": "frozen B0 native command sequence from GRATE",
                    "injected_commands": list(injection_commands),
                    "pre_author_progress_sha256": before_progress_hash,
                    "history_not_delivered_before_unlock": True,
                }
                _append_jsonl(trace_path, {"event": "h4_intervention_started",
                                           **h4_intervention})
                injected_rows: list[StepResult] = []
                harness_state = state
                manipulation_check: dict[str, Any] = {"drop_keys_succeeded": False,
                                                       "returned_to_grate": False}
                injection_failed = False
                for command in injection_commands:
                    injected = session.step(command, controller="h4-native-intervention",
                                            decision_source=("frozen B0 controller-visible "
                                                             "feedback-delay input sequence"))
                    task_inputs += 1
                    injected_rows.append(injected)
                    _append_receipt(trace_path, injected, input_count=task_inputs,
                                    role="h4_injected_" + command.replace(" ", "_"),
                                    delivered=False)
                    if not injected.input_boundary_reached:
                        status, failure = "UNKNOWN", "H4 injected command receipt incomplete"
                        injection_failed = True
                        break
                    witnessed = reconcile(harness_state, injected.observation,
                                          command=command,
                                          complete=injected.input_boundary_reached)
                    if witnessed.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                        status, failure = "UNKNOWN", "H4 manipulation-check receipt was unmodeled"
                        injection_failed = True
                        break
                    harness_state = witnessed.state
                    if command == "drop keys":
                        manipulation_check["drop_keys_succeeded"] = (
                            "native_drop_ok:keys" in witnessed.evidence)
                        manipulation_check["drop_keys_sequence"] = injected.sequence
                        if not manipulation_check["drop_keys_succeeded"]:
                            status, failure = "EXECUTION_FAILURE", "H4 drop keys was not accepted by the native game"
                            injection_failed = True
                            break
                    if command == "depre":
                        manipulation_check["returned_to_grate"] = (
                            witnessed.observed_room == "GRATE")
                        manipulation_check["return_sequence"] = injected.sequence
                if injection_failed:
                    h4_intervention["manipulation_check"] = manipulation_check
                    _append_jsonl(trace_path, {"event": "h4_injection_stopped",
                                               **h4_intervention, "status": status,
                                               "retry": False})
                    break
                if not manipulation_check["drop_keys_succeeded"] or not manipulation_check["returned_to_grate"]:
                    status, failure = "EXECUTION_FAILURE", "H4 native intervention did not establish the frozen precondition"
                    h4_intervention["manipulation_check"] = manipulation_check
                    _append_jsonl(trace_path, {"event": "h4_injection_stopped",
                                               **h4_intervention, "status": status,
                                               "retry": False})
                    break
                unlock = session.step(action.command, controller="author-obligation-search",
                                      decision_source=("execute first primitive from plan; "
                                                       "planned before the five delayed native receipts"))
                task_inputs += 1
                _append_receipt(trace_path, unlock, input_count=task_inputs,
                                role="h4_stale_planned_unlock", delivered=False)
                h4_intervention["unlock_sequence"] = unlock.sequence
                h4_intervention["unlock_complete"] = unlock.input_boundary_reached
                h4_intervention["actual_rejection"] = (
                    unlock.input_boundary_reached
                    and "you have no keys!" in unlock.observation.casefold())
                _append_jsonl(trace_path, {"event": "h4_actual_unlock_feedback",
                                           "sequence": unlock.sequence,
                                           "command": unlock.command,
                                           "complete": unlock.input_boundary_reached,
                                           "rejection_text_observed": h4_intervention["actual_rejection"],
                                           "observation": unlock.observation})
                if not unlock.input_boundary_reached:
                    status, failure = "UNKNOWN", "H4 planned unlock receipt incomplete"
                    break
                if not h4_intervention["actual_rejection"]:
                    status, failure = "EXECUTION_FAILURE", "H4 stale unlock did not produce the registered native no-keys rejection"
                    h4_intervention["actual_failure_recorded"] = False
                    _append_jsonl(trace_path, {"event": "h4_intervention_stopped",
                                               **h4_intervention, "status": status,
                                               "retry": False})
                    break
                h4_intervention["actual_failure_recorded"] = True
                delayed_rows = [*injected_rows, unlock]
                for delayed in delayed_rows:
                    role = ("delayed_" + delayed.command.replace(" ", "_")
                            if delayed is not unlock else "delayed_unlock_rejection")
                    before_room = _room_in_state(state)
                    reconciled = reconcile(state, delayed.observation,
                                           command=delayed.command,
                                           complete=delayed.input_boundary_reached)
                    if reconciled.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                        status = "UNKNOWN"
                        failure = f"H4 {role} could not be safely reconciled: {reconciled.status}"
                        break
                    state = reconciled.state
                    post_progress = _add_receipt_events(task, history, delayed,
                                                        trace_path, delivery=role,
                                                        before_room=before_room)
                    _append_jsonl(trace_path, {
                        "event": "h4_delayed_feedback_delivery",
                        "sequence": delayed.sequence, "command": delayed.command,
                        "role": role, "reconcile_status": reconciled.status,
                        "evidence": list(reconciled.evidence),
                        "state_sha256": _canonical_hash(sorted(state)),
                        "post_author_progress_sha256": _canonical_hash(post_progress),
                    })
                if status != "RUNNING":
                    break
                h4_refresh_evidence = False
                for command in ("look", "inventory"):
                    if task_inputs >= INPUT_BUDGET:
                        status, failure = "BUDGET", "input budget exhausted during H4 refresh"
                        break
                    refresh = session.step(command, controller="h4-refresh",
                                           decision_source="fresh native state after delayed feedback delivery")
                    task_inputs += 1
                    _append_receipt(trace_path, refresh, input_count=task_inputs,
                                    role="h4_refresh", delivered=True)
                    refresh_before_room = _room_in_state(state)
                    reconciled = reconcile(state, refresh.observation, command=command,
                                           complete=refresh.input_boundary_reached)
                    if not refresh.input_boundary_reached or reconciled.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                        status, failure = "UNKNOWN", "H4 native refresh receipt incomplete or unmodeled"
                        break
                    state = reconciled.state
                    h4_refresh_evidence = h4_refresh_evidence or bool(reconciled.evidence)
                    _add_receipt_events(task, history, refresh, trace_path,
                                        delivery="h4_refresh",
                                        before_room=refresh_before_room)
                    _append_jsonl(trace_path, {"event": "h4_refresh_reconciled",
                                              "sequence": refresh.sequence,
                                              "command": command,
                                              "reconcile_status": reconciled.status,
                                              "evidence": list(reconciled.evidence),
                                              "state_sha256": _canonical_hash(sorted(state))})
                if status == "RUNNING" and not h4_refresh_evidence:
                    status, failure = "UNKNOWN", "H4 refresh produced no fresh native state evidence"
                if status == "RUNNING":
                    h4_intervention["post_author_progress_sha256"] = _canonical_hash(
                        _progress_snapshot(task, history))
                    h4_intervention["inputs_charged"] = 8
                    _append_jsonl(trace_path, {"event": "h4_intervention_complete",
                                               **h4_intervention})
                    continue
                break

            if task_inputs >= INPUT_BUDGET:
                status = "BUDGET"
                failure = "native task input budget exhausted"
                break
            plan_hash = _canonical_hash([{"name": item.name,
                                          "args": list(item.args),
                                          "command": item.command} for item in plan])
            step = session.step(action.command, controller="author-obligation-search",
                                decision_source=f"first primitive of temporal plan {plan_hash}")
            task_inputs += 1
            _append_receipt(trace_path, step, input_count=task_inputs,
                            role="planned_action", delivered=True)
            _append_jsonl(trace_path, {
                "event": "decision", "step_sequence": step.sequence,
                "input_count": task_inputs, "plan_sha256": plan_hash,
                "predicted_plan": [{"operator": item.name, "args": list(item.args),
                                    "command": item.command} for item in plan],
                "plan_is_prediction_only": True, "operator": action.name,
                "operator_args": list(action.args), "command": action.command,
                "native_complete": step.input_boundary_reached,
                "native_terminated": step.terminated, "native_error": step.error,
            })
            if not step.input_boundary_reached:
                status, failure = "UNKNOWN", "native action did not return a complete input boundary"
                break
            question = _native_question(step.observation)
            if question is not None:
                if question != "cave_hint_confirmation" or task_inputs >= INPUT_BUDGET:
                    status = "BUDGET" if task_inputs >= INPUT_BUDGET else "EXECUTION_FAILURE"
                    failure = f"unsupported native question: {question}"
                    break
                answer = session.step("n", controller="author-obligation-native-question",
                                     decision_source="decline known visible nonblocking cave hint")
                task_inputs += 1
                _append_receipt(trace_path, answer, input_count=task_inputs,
                                role="native_question_answer", delivered=True)
                if not answer.input_boundary_reached:
                    status, failure = "UNKNOWN", "native question answer receipt incomplete"
                    break
                before_room = _room_in_state(state)
                action_reconciliation = reconcile(state, step.observation,
                                                  command=action.command)
                if action_reconciliation.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                    status, failure = "UNKNOWN", "native action receipt was incomplete or unmodeled"
                    break
                state = action_reconciliation.state
                answer_reconciliation = reconcile(state, answer.observation, command="n")
                if answer_reconciliation.status == "UNMODELED_EVENT":
                    status, failure = "UNKNOWN", "unmodeled event after native question"
                    break
                state = answer_reconciliation.state
                _add_receipt_events(task, history, step, trace_path,
                                    before_room=before_room)
                _add_receipt_events(task, history, answer, trace_path,
                                    before_room=_room_in_state(state))
                continue

            before_room = _room_in_state(state)
            reconciled = reconcile(state, step.observation, command=action.command)
            expected = _expected_action(action, reconciled)
            if reconciled.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                status, failure = "UNKNOWN", f"native response reconciliation: {reconciled.status}"
                break
            state = reconciled.state
            _add_receipt_events(task, history, step, trace_path,
                                before_room=before_room)
            _append_jsonl(trace_path, {
                "event": "reconciliation", "sequence": step.sequence,
                "status": reconciled.status, "expected_action_witnessed": expected,
                "evidence": list(reconciled.evidence),
                "observed_room": reconciled.observed_room,
                "state_sha256": _canonical_hash(sorted(state)),
            })
            if not expected:
                refreshed_with_evidence = False
                for command in ("look", "inventory"):
                    if task_inputs >= INPUT_BUDGET:
                        status, failure = "BUDGET", "input budget exhausted during mismatch refresh"
                        break
                    refresh = session.step(command, controller="author-obligation-refresh",
                                           decision_source="fresh visible-state check after native mismatch")
                    task_inputs += 1
                    _append_receipt(trace_path, refresh, input_count=task_inputs,
                                    role="mismatch_refresh", delivered=True)
                    refresh_before_room = _room_in_state(state)
                    current = reconcile(state, refresh.observation, command=command,
                                        complete=refresh.input_boundary_reached)
                    if not refresh.input_boundary_reached or current.status in {"INCOMPLETE", "UNMODELED_EVENT"}:
                        status, failure = "UNKNOWN", "mismatch refresh was incomplete or unmodeled"
                        break
                    state = current.state
                    refreshed_with_evidence = refreshed_with_evidence or bool(current.evidence)
                    _add_receipt_events(task, history, refresh, trace_path,
                                        before_room=refresh_before_room)
                if status == "RUNNING" and not refreshed_with_evidence:
                    status, failure = "UNKNOWN", "native mismatch refresh produced no fresh state evidence"
                if status != "RUNNING":
                    break
                continue

            if case is not None and case.edit_trigger == "after_successful_take_rod" \
                    and action.name == "take" and action.args[1] == "rod" \
                    and task.version == "1" \
                    and "native_take_ok:rod" in reconciled.evidence:
                before = task
                task = _edit_for_trigger(task, case, case.edit_trigger,
                                         history, trace_path, step.sequence)
                edit_log.append({"trigger": case.edit_trigger, "sequence": step.sequence,
                                 "from_version": before.version, "to_version": task.version})
            if case is not None and case.edit_trigger == "after_first_arrive_east" \
                    and reconciled.observed_room == "EASTBANK" and task.version == "1":
                before = task
                task = _edit_for_trigger(task, case, case.edit_trigger,
                                         history, trace_path, step.sequence)
                edit_log.append({"trigger": case.edit_trigger, "sequence": step.sequence,
                                 "from_version": before.version, "to_version": task.version})
            if case is not None and case.edit_trigger == "immediately_before_build" \
                    and reconciled.observed_room == "EASTBANK" \
                    and not any(event.name == "create_bridge" for event in history) \
                    and task.version == "1":
                before = task
                task = _edit_for_trigger(task, case, case.edit_trigger,
                                         history, trace_path, step.sequence)
                edit_log.append({"trigger": case.edit_trigger, "sequence": step.sequence,
                                 "from_version": before.version, "to_version": task.version})

            if task_inputs >= INPUT_BUDGET:
                status = "BUDGET"
                failure = "native task input budget exhausted"
                break
        close_result = session.close()
        if close_result.get("error"):
            status = "EXECUTION_FAILURE"
            failure = close_result["error"]
        if trace_path is not None:
            _append_jsonl(trace_path, {
                "event": "episode_end", "controller_status": status,
                "search_status": search_status,
                "author_verdict": "NOT_RUN_IN_CONTROLLER",
                "verification_status": "NOT_RUN_IN_CONTROLLER",
                "final_audit_status": final_audit_status,
                "native_task_inputs": task_inputs,
                "search_calls": search_calls, "search_seconds": search_seconds,
                "final_task": serialize_task(task),
                "final_task_sha256": _canonical_hash(serialize_task(task)),
                "final_task_input_sha256": _canonical_hash(serialize_task(task)),
                "final_history": _jsonable(history),
                "final_history_sha256": _canonical_hash(history),
                "final_progress": _jsonable(_progress_snapshot(task, history)),
                "raw_native_ledger": str(session.log_path),
                "session_close": close_result,
                "failure": failure,
            })
        return _run_summary(task, status, session, trace_path, history,
                            task_inputs, search_calls, search_seconds,
                            edit_log, failure=failure, h4_intervention=h4_intervention,
                            search_status=search_status,
                            final_audit_status=final_audit_status)
    except Exception as exc:
        status = "UNKNOWN" if isinstance(exc, UnknownNativeEvent) else "EXECUTION_FAILURE"
        failure = f"{type(exc).__name__}: {exc}"
        try:
            close_result = session.close()
        except Exception as close_exc:
            close_result = {"error": f"{type(close_exc).__name__}: {close_exc}"}
        if trace_path is not None:
            _append_jsonl(trace_path, {"event": "episode_error",
                                       "controller_status": status,
                                       "failure": failure,
                                       "native_ledger": str(session.log_path),
                                       "session_close": close_result})
        return _run_summary(task, status, session, trace_path, history,
                            task_inputs, search_calls, search_seconds,
                            edit_log, failure=failure, h4_intervention=h4_intervention,
                            search_status=search_status,
                            final_audit_status=final_audit_status)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--scenario", choices=("clean", "h4_feedback_delay"), default="clean")
    parser.add_argument("--execute-native", action="store_true",
                        help="required explicit switch to launch the original game")
    args = parser.parse_args()
    print(json.dumps(run_episode(args.task, execute_native=args.execute_native,
                                 scenario=args.scenario), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
