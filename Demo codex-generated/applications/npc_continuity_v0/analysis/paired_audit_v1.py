#!/usr/bin/env python3
"""Evidence-only consistency audit for npc-continuity-paired-trace-v1.

This audits paired input/protocol integrity and recorded Runtime outcomes. It is
not a player evaluation, behavior-quality score, or preference judgement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROTOCOL = "npc-continuity-paired-trace-v1"
CASES = ("alarm_active", "quiet_active", "near_completion_alarm")
POLICIES = ("utility", "history-llm")
PLAYER_CUE_KEYS = {
    "room.alarm", "message.unread_count", "task.coursework.status",
    "task.coursework.effort", "task.coursework.completed",
}


class AuditError(ValueError):
    pass


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"{path}:{number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise AuditError(f"{path}:{number}: JSONL record must be an object")
            rows.append(value)
    return rows


def _single(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("kind") == kind]
    if len(matches) != 1:
        raise AuditError(f"expected exactly one {kind} record; got {len(matches)}")
    return matches[0]


def _outcomes(step: dict[str, Any]):
    for field in ("pre_policy_outcome", "post_policy_outcome"):
        outcome = step.get(field)
        if outcome is not None:
            if not isinstance(outcome, dict):
                raise AuditError(f"{field} must be an object or null")
            yield field, outcome


def _known_fact_projection(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: fact.get(k) for k in ("key", "value", "status")}
            for fact in facts if fact.get("status") in ("known", "stale")]


def _check_request_snapshot(selection: dict[str, Any]) -> dict[str, Any]:
    raw = selection.get("request_json")
    if not isinstance(raw, str):
        raise AuditError("selection_input.request_json missing")
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AuditError(f"selection_input.request_json invalid: {exc}") from exc
    if selection.get("clock_total_minutes") != request.get("clock_total_minutes"):
        raise AuditError("selection clock differs from serialized shared request")
    if selection.get("clock_time") != request.get("clock_time"):
        raise AuditError("selection clock.time differs from serialized shared request")
    if _known_fact_projection(selection.get("observation_known_facts", [])) != request.get("observation_known_facts"):
        raise AuditError("selection O-known facts differ from serialized shared request")
    if selection.get("actor_history") != request.get("actor_history"):
        raise AuditError("selection actor history differs from serialized shared request")
    if selection.get("running_action") != request.get("running_action"):
        raise AuditError("selection running action differs from serialized shared request")
    if selection.get("candidates") != request.get("candidates"):
        raise AuditError("selection hard candidates differ from serialized shared request")
    return request


def _run_summary(trace_path: Path, journal_path: Path | None) -> dict[str, Any]:
    rows = read_jsonl(trace_path)
    allowed_kinds = {"header", "initial_state", "boundary", "error", "termination"}
    unknown = [row.get("kind") for row in rows if row.get("kind") not in allowed_kinds]
    if unknown:
        raise AuditError(f"{trace_path}: unknown record kinds: {unknown}")
    if len(rows) < 3 or rows[0].get("kind") != "header" or rows[1].get("kind") != "initial_state" or rows[-1].get("kind") != "termination":
        raise AuditError(f"{trace_path}: expected header, initial_state, ... , termination ordering")
    header = _single(rows, "header")
    initial = _single(rows, "initial_state")
    termination = _single(rows, "termination")
    if header.get("protocol") != PROTOCOL:
        raise AuditError(f"{trace_path}: wrong trace protocol")
    if header.get("case") not in CASES or header.get("policy") not in POLICIES:
        raise AuditError(f"{trace_path}: unknown case/policy")
    boundaries = [row for row in rows if row.get("kind") == "boundary"]
    error_rows = [row for row in rows if row.get("kind") == "error"]
    start = header.get("scenario_setup", {}).get("start_total_minutes")
    horizon = header.get("horizon_minutes")
    if not isinstance(start, int) or not isinstance(horizon, int) or horizon <= 0:
        raise AuditError(f"{trace_path}: invalid start/horizon metadata")
    if initial.get("minute") != start:
        raise AuditError(f"{trace_path}: initial minute differs from scenario setup")

    previous = start
    action_minutes: Counter[str] = Counter()
    starts: Counter[str] = Counter()
    continuations: Counter[str] = Counter()
    world_event_ids: Counter[str] = Counter()
    cue_deltas: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    validations = {"performed": 0, "accepted": 0, "rejected": 0, "not_performed": 0}
    selections: list[dict[str, Any]] = []
    decision_intents: list[dict[str, Any]] = []
    task_progress_timeline: list[dict[str, Any]] = []
    previous_running = initial.get("running_action")

    for index, step in enumerate(boundaries):
        interval = step.get("interval", {})
        at = interval.get("at_total_minutes")
        from_minute = interval.get("from_total_minutes")
        elapsed = interval.get("elapsed_minutes")
        if from_minute != previous or not isinstance(at, int) or not isinstance(elapsed, int):
            raise AuditError(f"{trace_path}: boundary {index} has discontinuous interval")
        if at - from_minute != elapsed or elapsed < 0 or at > start + horizon:
            raise AuditError(f"{trace_path}: boundary {index} duration/horizon mismatch")
        if interval.get("ownership") != "interval_before_boundary_then_events_at_at_total_minutes":
            raise AuditError(f"{trace_path}: boundary {index} has unknown interval ownership")
        if step.get("index") != index:
            raise AuditError(f"{trace_path}: boundary index must be zero-based and contiguous")
        previous = at

        before = step.get("running_before")
        after = step.get("running_after")
        if before != previous_running:
            raise AuditError(f"{trace_path}: running_before differs from preceding initial/running_after state")
        if before and before.get("status") == "running" and before.get("started_at_total_minutes", -1) + before.get("elapsed_minutes", -1) != from_minute:
            raise AuditError(f"{trace_path}: running_before start/elapsed does not reach interval start")
        if after and after.get("status") == "running" and after.get("started_at_total_minutes", -1) + after.get("elapsed_minutes", -1) != at:
            raise AuditError(f"{trace_path}: running_after start/elapsed does not reach boundary time")
        if before and before.get("status") == "running" and elapsed:
            action_minutes[before["action"]] += elapsed
        if after and (not before or any(after.get(key) != before.get(key)
                                        for key in ("action", "target", "started_at_total_minutes"))):
            starts[after["action"]] += 1
        if before and after and all(before.get(key) == after.get(key)
                                    for key in ("action", "target", "started_at_total_minutes")):
            continuations[before["action"]] += 1
        validation = step.get("replacement_validation", {})
        if validation.get("performed") is True:
            validations["performed"] += 1
            if validation.get("accepted") is True:
                validations["accepted"] += 1
            elif validation.get("accepted") is False:
                validations["rejected"] += 1
            else:
                raise AuditError(f"{trace_path}: performed replacement validation lacks accepted result")
        else:
            validations["not_performed"] += 1
            if validation.get("accepted") is not None:
                raise AuditError(f"{trace_path}: nonperformed validation must have accepted=null")
        for event in step.get("world_events", []):
            world_event_ids[event.get("id", "<missing>")] += 1
        for delta in step.get("observation_deltas", []):
            if delta.get("key") in PLAYER_CUE_KEYS:
                cue_deltas.append({"minute": at, "key": delta.get("key"), "value": delta.get("value"),
                                   "status": delta.get("status")})
        for _, outcome in _outcomes(step):
            outcomes.append(outcome)
        if step.get("policy_evaluated"):
            selection = step.get("selection_input")
            if not isinstance(selection, dict):
                raise AuditError(f"{trace_path}: evaluated policy lacks selection_input")
            _check_request_snapshot(selection)
            if selection.get("clock_total_minutes") != at:
                raise AuditError(f"{trace_path}: selection clock is not the boundary clock")
            selections.append(selection)
            task_facts = {f.get("key"): f for f in selection.get("observation_known_facts", [])}
            request = json.loads(selection["request_json"])
            decision_intents.append({"minute": at, "selected_action_intent": step.get("selected_action"),
                "selected_target_intent": step.get("selected_target"),
                "running_before": before, "running_after": after,
                "visible_task_status": task_facts.get("task.coursework.status", {}).get("value"),
                "visible_task_effort": task_facts.get("task.coursework.effort", {}).get("value"),
                "visible_task_effort_target": task_facts.get("task.coursework.effort_target", {}).get("value"),
                "hard_candidate_actions": [c.get("action") for c in request.get("candidates", [])]})
        elif step.get("selection_input") is not None:
            raise AuditError(f"{trace_path}: non-policy boundary has a selection_input")
        if (step.get("policy_evaluated") and before and before.get("status") == "running"
                and step.get("selected_action") == before.get("action")
                and step.get("selected_target") == before.get("target")
                and step.get("pre_policy_outcome") is None
                and before.get("elapsed_minutes", 0) + elapsed < before.get("planned_minutes", 0)
                and step.get("replacement_validation", {}).get("performed") is not True):
            expected_elapsed = before["elapsed_minutes"] + elapsed
            if not after or after.get("started_at_total_minutes") != before.get("started_at_total_minutes") or after.get("elapsed_minutes") != expected_elapsed:
                raise AuditError(f"{trace_path}: same-intent continuation reset start/progress before planned completion")
        task_after = step.get("task_world_after")
        if isinstance(task_after, dict):
            effort = task_after.get("effort_done")
            target = task_after.get("effort_target")
            task_progress_timeline.append({"minute": at, "status": task_after.get("status"),
                "effort_done": effort, "effort_target": target,
                "effort_remaining": max(0.0, target-effort) if isinstance(target, (int, float)) and isinstance(effort, (int, float)) else None,
                "task_completed_outcome_this_boundary": any(o.get("task_completed") is True for _, o in _outcomes(step))})
        previous_running = after

    completed_outcomes = [outcome for outcome in outcomes if outcome.get("task_completed") is True]
    completion_outcomes = [outcome for outcome in outcomes if outcome.get("accepted") is True
        and outcome.get("interrupted") is not True and outcome.get("plan_invalidated") is not True]
    for outcome in completed_outcomes:
        if outcome.get("accepted") is not True or outcome.get("interrupted") is True or outcome.get("plan_invalidated") is True:
            raise AuditError(f"{trace_path}: task_completed outcome is not an accepted completion")
    final_task = boundaries[-1].get("task_world_after") if boundaries else initial.get("task_world")
    world_completed = isinstance(final_task, dict) and final_task.get("status") == "completed"
    if world_completed != bool(completed_outcomes):
        raise AuditError(f"{trace_path}: task completion state lacks matching true Runtime outcome")
    if termination.get("boundaries") != len(boundaries):
        raise AuditError(f"{trace_path}: termination boundary count mismatch")
    if termination.get("minute") != previous or termination.get("simulated_minutes") != previous-start:
        raise AuditError(f"{trace_path}: termination time does not match boundary sequence")
    full_horizon = (termination.get("reason") == "horizon" and previous-start == horizon
                    and previous == start+horizon)
    if termination.get("reason") == "horizon" and not full_horizon:
        raise AuditError(f"{trace_path}: horizon termination is short or overshot")
    if termination.get("reason") == "horizon" and error_rows:
        raise AuditError(f"{trace_path}: horizon termination cannot contain an error record")
    evaluated_count = sum(step.get("policy_evaluated") is True for step in boundaries)
    policy_calls = termination.get("policy_calls")
    if not isinstance(policy_calls, int):
        raise AuditError(f"{trace_path}: termination.policy_calls is missing or invalid")
    if policy_calls == evaluated_count:
        pass
    elif termination.get("reason") == "errors" and policy_calls == evaluated_count + 1 and error_rows:
        attempt = error_rows[-1].get("selection_input")
        if not isinstance(attempt, dict):
            raise AuditError(f"{trace_path}: failed policy attempt has no captured selection input")
        _check_request_snapshot(attempt)
    else:
        raise AuditError(f"{trace_path}: policy_calls does not match evaluated boundaries/one recorded failed attempt")
    if termination.get("reason") == "errors" and not error_rows:
        raise AuditError(f"{trace_path}: errors termination lacks error record")

    journal_rows: list[dict[str, Any]] = []
    if journal_path is not None and journal_path.exists():
        journal_rows = read_jsonl(journal_path)
    elif header.get("policy") == "history-llm":
        journal_rows = []
    if header.get("policy") == "history-llm":
        evaluated = [step for step in boundaries if step.get("policy_evaluated") is True]
        if termination.get("reason") == "horizon" and len(journal_rows) != evaluated_count:
            raise AuditError(f"{trace_path}: full-horizon history-llm journal must have one row per evaluation")
        if termination.get("reason") == "errors" and policy_calls == evaluated_count + 1 and len(journal_rows) != policy_calls:
            raise AuditError(f"{trace_path}: failed policy attempt lacks a matching HTTP journal row")
        if termination.get("reason") != "errors" and len(journal_rows) != policy_calls:
            raise AuditError(f"{trace_path}: history-llm journal count differs from policy_calls")
        for index, row in enumerate(journal_rows):
            request = row.get("request")
            if not isinstance(request, dict):
                continue
            if row.get("model") != header.get("requested_model_id"):
                raise AuditError(f"{trace_path}: HTTP journal model differs from requested model id")
            messages = request.get("messages", [])
            if len(messages) < 2 or not isinstance(messages[1].get("content"), str):
                raise AuditError(f"{trace_path}: HTTP journal lacks user policy request")
            try:
                journal_policy_request = json.loads(messages[1]["content"])
            except json.JSONDecodeError as exc:
                raise AuditError(f"{trace_path}: HTTP user request is invalid JSON") from exc
            expected_selection = (evaluated[index]["selection_input"] if index < len(evaluated)
                                  else error_rows[-1].get("selection_input"))
            if not isinstance(expected_selection, dict):
                raise AuditError(f"{trace_path}: journal row has no matching selection/error input")
            expected_request = json.loads(expected_selection["request_json"])
            if journal_policy_request != expected_request:
                raise AuditError(f"{trace_path}: API body policy request differs from captured selection input")
            if row.get("status") == "ok":
                candidate_map = {item["candidate_id"]: item["action"] for item in journal_policy_request.get("candidates", [])}
                selected_id = row.get("candidate_id")
                if index < len(evaluated):
                    selected_action = evaluated[index].get("selected_action")
                    if selected_id not in candidate_map or candidate_map[selected_id] != selected_action:
                        raise AuditError(f"{trace_path}: journal candidate choice differs from Runtime selected action")
        if termination.get("reason") == "horizon" and any(r.get("status") != "ok" for r in journal_rows):
            raise AuditError(f"{trace_path}: full-horizon history-llm journal contains failed calls")
    usage = [row.get("usage") if isinstance(row.get("usage"), dict) else {} for row in journal_rows]
    prompt_tokens = [u.get("prompt_tokens") for u in usage if isinstance(u.get("prompt_tokens"), int) and u["prompt_tokens"] >= 0]
    completion_tokens = [u.get("completion_tokens") for u in usage if isinstance(u.get("completion_tokens"), int) and u["completion_tokens"] >= 0]
    api_elapsed = [row.get("elapsed_ms") for row in journal_rows if isinstance(row.get("elapsed_ms"), int) and row["elapsed_ms"] >= 0]
    api_statuses = Counter(str(row.get("status", "unknown")) for row in journal_rows)
    for row in journal_rows:
        request = row.get("request")
        sha = row.get("request_sha256")
        if isinstance(request, dict) and isinstance(sha, str):
            canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(canonical).hexdigest() != sha:
                raise AuditError(f"{trace_path}: journal request_sha256 mismatch")
    return {
        "trace_path": str(trace_path), "journal_path": str(journal_path) if journal_path and journal_path.exists() else None,
        "case": header["case"], "policy": header["policy"], "policy_identity": header.get("policy_identity"),
        "application_model": header.get("application_model"), "endpoint": header.get("endpoint"),
        "requested_model_id": header.get("requested_model_id"), "start_total_minutes": start,
        "fixture_seed": header.get("fixture_seed"), "policy_seed": header.get("policy_seed"),
        "max_boundaries": header.get("max_boundaries"), "max_policy_calls": header.get("max_policy_calls"),
        "compiled_git_revision": header.get("compiled_git_revision"),
        "horizon_minutes": horizon, "termination_reason": termination.get("reason"),
        "simulated_minutes": previous-start, "full_horizon": full_horizon,
        "policy_calls": termination.get("policy_calls"), "boundary_count": len(boundaries),
        "first_selection_input": selections[0] if selections else None,
        "initial_observation": initial.get("observation"), "initial_running_action": initial.get("running_action"),
        "scenario_setup": header.get("scenario_setup"), "action_minutes_by_running_before": dict(action_minutes),
        "policy_action_starts_excluding_initial_scenario_action": dict(starts),
        "same_running_action_intervals_including_closed_gates": dict(continuations),
        "world_event_counts": dict(world_event_ids), "player_visible_fact_deltas": cue_deltas,
        "replacement_validation": validations,
        "runtime_outcomes": {"count": len(outcomes), "completion_count": len(completion_outcomes),
            "task_completion_count": len(completed_outcomes),
            "typed_rejection_count": sum(o.get("accepted") is False and o.get("rejection_reason") not in (None, "none") for o in outcomes),
            "interruption_count": sum(o.get("interrupted") is True for o in outcomes),
            "plan_invalidation_count": sum(o.get("plan_invalidated") is True for o in outcomes)},
        "world_task_final_status": final_task.get("status") if isinstance(final_task, dict) else None,
        "decision_intents": decision_intents, "task_progress_timeline": task_progress_timeline,
        "http_journal": {"call_count": len(journal_rows), "statuses": dict(api_statuses),
            "prompt_tokens": sum(prompt_tokens) if prompt_tokens and len(prompt_tokens)==len(journal_rows) else None,
            "completion_tokens": sum(completion_tokens) if completion_tokens and len(completion_tokens)==len(journal_rows) else None,
            "api_elapsed_ms_total": sum(api_elapsed) if api_elapsed and len(api_elapsed)==len(journal_rows) else None,
            "elapsed_status": "measured_per_call" if len(api_elapsed)==len(journal_rows) and journal_rows else
                              "no_calls" if not journal_rows and header.get("policy")=="utility" else "unavailable",
            "calls": [{"status": row.get("status"), "stage": row.get("stage"), "error_type": row.get("error_type"),
                "request_sha256": row.get("request_sha256"), "elapsed_ms": row.get("elapsed_ms"),
                "prompt_tokens": (row.get("usage") or {}).get("prompt_tokens") if isinstance(row.get("usage"), dict) else None,
                "completion_tokens": (row.get("usage") or {}).get("completion_tokens") if isinstance(row.get("usage"), dict) else None,
                "candidate_id": row.get("candidate_id")} for row in journal_rows]},
        "actor_history_window": header.get("history_window"),
    }


def audit_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    if left["case"] != right["case"] or left["policy"] == right["policy"]:
        raise AuditError("pair must contain the same case and different policies")
    common_fields = ("start_total_minutes", "horizon_minutes", "fixture_seed", "policy_seed", "max_boundaries",
                     "max_policy_calls", "compiled_git_revision", "application_model",
                     "requested_model_id", "scenario_setup",
                     "initial_observation", "initial_running_action")
    mismatches = [field for field in common_fields if left[field] != right[field]]
    if mismatches:
        raise AuditError("paired initial configuration mismatch: " + ", ".join(mismatches))
    if left["first_selection_input"] is None or right["first_selection_input"] is None:
        raise AuditError("pair missing an actual policy selection input")
    if left["first_selection_input"] != right["first_selection_input"]:
        raise AuditError("first actual O/clock/history/running/candidates differ across policies")
    return {"case": left["case"], "initial_config_equal": True,
            "initial_observation_running_equal": True, "first_selection_input_equal": True,
            "both_full_horizon": left["full_horizon"] and right["full_horizon"],
            "policies": [left["policy"], right["policy"]]}


def _markdown(report: dict[str, Any]) -> str:
    lines = ["# Paired NPC continuity trace audit", "",
        "Scope: protocol/input consistency and recorded Runtime outcomes only. This is not a player evaluation, behavior-quality score, or policy-preference judgement.", "",
        "| Case | Policy | End | Min | Horizon | Policy calls | Starts | Action completions | Interruptions | Continuation intervals | Replacement validation (performed/rejected) | Typed rejections | Task completed | HTTP calls | API ms | Tokens P/C |",
        "|---|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for run in report["runs"]:
        http = run["http_journal"]
        tokens = (f"{http['prompt_tokens']}/{http['completion_tokens']}" if http["prompt_tokens"] is not None and http["completion_tokens"] is not None else "unknown")
        elapsed = str(http["api_elapsed_ms_total"]) if http["api_elapsed_ms_total"] is not None else "unknown (no HTTP timing)"
        validation = run["replacement_validation"]
        lines.append(f"| {run['case']} | {run['policy']} | {run['termination_reason']} | {run['simulated_minutes']} | {run['full_horizon']} | {run['policy_calls']} | {sum(run['policy_action_starts_excluding_initial_scenario_action'].values())} | {run['runtime_outcomes']['completion_count']} | {run['runtime_outcomes']['interruption_count']} | {sum(run['same_running_action_intervals_including_closed_gates'].values())} | {validation['performed']}/{validation['rejected']} | {run['runtime_outcomes']['typed_rejection_count']} | {run['runtime_outcomes']['task_completion_count']} | {http['call_count']} | {elapsed} | {tokens} |")
    lines += ["", "## Pair integrity", "", "| Case | Same setup/O/running | Same first O/clock/history/candidates | Both full horizon |", "|---|:---:|:---:|:---:|"]
    for pair in report["pairs"]:
        lines.append(f"| {pair['case']} | {pair['initial_config_equal']} | {pair['first_selection_input_equal']} | {pair['both_full_horizon']} |")
    lines += ["", "Action duration is attributed to a running `running_before` over each `[from, at)` interval. Starts counted here are Runtime transitions after the initial scenario action (which is excluded); same-running-action intervals also include boundaries with a closed policy gate. Action completion, interruption, task completion, and typed rejection are separate counts. Replacement validation counts include only `performed=true`; unperformed replacements are not rejections. `selected_action` is not treated as execution. Task completion is counted only from accepted typed Runtime outcomes and cross-checked with final World task status.", "",
        "Utility has no HTTP request; its model-call latency/tokens are not applicable, and CPU execution latency is unavailable rather than zero. HTTP elapsed time is transport/API timing from the journal, not inference-only timing. A call-limit/error stop is not reported as a full-horizon run.", ""]
    near = [run for run in report["runs"] if run["case"] == "near_completion_alarm"]
    if near:
        lines += ["## Near-completion case: recorded task state and decision inputs", "",
            "The table reports raw debug task progress and policy-selected intent at policy boundaries; selection is not execution, and no reason is inferred from the policy choice.", "",
            "| Policy | Minute | Task status | Effort / target | Remaining | Selected intent | StudyFocused candidate present |",
            "|---|---:|---|---:|---:|---|:---:|"]
        for run in near:
            intents = {item["minute"]: item for item in run["decision_intents"]}
            for point in run["task_progress_timeline"]:
                intent = intents.get(point["minute"])
                if not intent:
                    continue
                effort = point["effort_done"]
                target = point["effort_target"]
                remaining = point["effort_remaining"]
                lines.append(f"| {run['policy']} | {point['minute']} | {point['status']} | {effort} / {target} | {remaining} | {intent['selected_action_intent']} | {'study_focused' in intent['hard_candidate_actions']} |")
        lines += ["", "An active task near its target is not a completed task. Completion counts above require `task_completed=true` in a typed Runtime outcome and agreement with the final World task status.", ""]
    return "\n".join(lines)


def build_report(run_root: Path) -> dict[str, Any]:
    runs = []
    for case in CASES:
        for policy in POLICIES:
            trace = run_root / f"{case}.{policy}.jsonl"
            if not trace.is_file():
                raise AuditError(f"missing expected trace: {trace}")
            journal = run_root / f"{case}_{policy}" / "history_llm_calls.jsonl" if policy == "history-llm" else None
            runs.append(_run_summary(trace, journal))
    by_key = {(r["case"], r["policy"]): r for r in runs}
    pairs = [audit_pair(by_key[(case, "utility")], by_key[(case, "history-llm")]) for case in CASES]
    return {"protocol": "npc-continuity-paired-audit-v1", "scope": "trace_integrity_and_runtime_outcomes_not_player_evaluation",
            "run_root": str(run_root), "runs": runs, "pairs": pairs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.run_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"audited {len(report['runs'])} traces; pair checks: {sum(p['first_selection_input_equal'] for p in report['pairs'])}/{len(report['pairs'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(f"paired audit failed: {exc}")
