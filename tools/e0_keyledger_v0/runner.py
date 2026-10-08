"""Per-fixture E0 contract runner and non-overwriting result writer.

This is a development/acceptance harness, not a claim that any run passed.
Each fixture result keeps search state separate from its assertion result.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import sys
import subprocess
import time
import traceback
import traceback

from .executor import Executor, intent
from .fixtures import CASE_IDS, PRODUCER_VERSION, initial_checkpoint
from .monitor_bridge import MonitorContractError, evaluate_goal, evaluate_holding_at
from .oracle import solve as solve_oracle
from .planner import uniform_cost_search
from .prediction import (
    EFFECT_COVERAGE, EVENT_COVERAGE, OBSERVATION_COVERAGE, PRECONDITIONS,
    WORLD_COVERAGE, audit_prediction, prediction_record, validate_binding,
)

EXPANSION_CAP = 10_000
WALL_SECONDS = 2.0


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _trace_payload(checkpoint: dict) -> dict:
    return deepcopy(checkpoint)


def _code_revision() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
                                  capture_output=True, text=True).stdout.strip()
        scope = ["tools/e0_keyledger_v0", "00_研究设计/E0_KeyLedger_Protocol_v0.md",
                 "00_研究设计/README.md", "02_实验/README.md", "02_实验/E0_KeyLedger_v0",
                 ".github/workflows/runtime-regression.yml"]
        dirty_rows = subprocess.run(["git", "status", "--porcelain", "--", *scope], cwd=repo_root,
                                    check=True, capture_output=True, text=True).stdout.splitlines()
        return {"commit": revision, "repo_root": str(repo_root), "e0_scoped_dirty": bool(dirty_rows),
                "e0_scoped_status": dirty_rows}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_dirty": None, "error": "GIT_REVISION_UNAVAILABLE"}


def _path_value(checkpoint: dict, path: str):
    root = {"W": checkpoint["W"], "O": checkpoint["O"],
            "config_pins": checkpoint["config_pins"], "clock": checkpoint["clock"]}
    value = root
    for key in path.split("."):
        value = value[key]
    return deepcopy(value)


def _event_signatures(events: list[dict]) -> list[dict]:
    return [{key: deepcopy(event[key]) for key in
             ("event_type", "time", "sequence", "producer_version", "typed_args")} for event in events]


def _coverage(operator: str) -> dict:
    effects = EFFECT_COVERAGE[operator]
    return {
        "preconditions": list(PRECONDITIONS[operator]),
        "post_world": list(WORLD_COVERAGE),
        "post_observation": list(OBSERVATION_COVERAGE),
        "effects": list(effects),
        "events": list(EVENT_COVERAGE),
        "invariants": [path for path in WORLD_COVERAGE if path not in effects],
    }


def _boundary_snapshot(executor: Executor, *, label: str, phase: str) -> dict:
    checkpoint = executor.checkpoint()
    return {"label": label, "phase": phase, "time": checkpoint["clock"]["now"],
            "W": deepcopy(checkpoint["W"]), "O": deepcopy(checkpoint["O"]),
            "running_action": deepcopy(checkpoint["W"]["running_action"]),
            "reservations": deepcopy(checkpoint["W"]["reservations"]),
            "events": deepcopy(checkpoint["events"]), "receipts": deepcopy(checkpoint["receipts"]),
            "seals": deepcopy(checkpoint["seals"]), "monitor": deepcopy(checkpoint["monitor"]),
            "minute_history": deepcopy(checkpoint["minute_history"])}


def _execute_recorded(executor: Executor, action: dict, *, label: str,
                      recordings: dict[str, list[dict]]) -> dict:
    before = executor.checkpoint()
    if action.get("operator") in PRECONDITIONS:
        forecast_receipt, forecast_after, predicted = _forecast_transition(before, action)
    else:
        forecast_receipt, forecast_after, predicted = None, None, None
    if action.get("operator") == "idle":
        receipt = executor.execute(action)
        recordings.setdefault(label, []).append(_boundary_snapshot(executor, label=label, phase="NO_CONTROL_BOUNDARY"))
        if receipt.get("accepted") and receipt.get("status") == "SUCCESS":
            actual = executor.checkpoint()
            audit = _audit_transition(before, actual, receipt, predicted)
            recordings[label].append({"label": label, "phase": "PREDICTION_CHECK",
                                      "prediction": predicted, "forecast_receipt": forecast_receipt,
                                      "actual_receipt": receipt, "audit": audit})
            if audit["status"] != "MATCH":
                raise AssertionError("forecast no_control prediction mismatch: " + str(audit))
        return receipt
    receipt = executor.start(action)
    recordings.setdefault(label, []).append(_boundary_snapshot(executor, label=label, phase="ACTION_START"))
    if not receipt.get("accepted"):
        return receipt
    first = True
    while executor.checkpoint()["W"]["running_action"] is not None:
        executor.advance_minute(started_action_id=receipt["action_id"] if first else None)
        recordings[label].append(_boundary_snapshot(executor, label=label, phase="MINUTE_BOUNDARY"))
        first = False
    actual = next(row for row in executor.checkpoint()["receipts"] if row["receipt_id"] == receipt["receipt_id"])
    audit = _audit_transition(before, executor.checkpoint(), actual, predicted)
    recordings[label].append({"label": label, "phase": "PREDICTION_CHECK",
                              "prediction": predicted, "forecast_receipt": forecast_receipt,
                              "actual_receipt": actual, "audit": audit})
    if audit["status"] != "MATCH":
        raise AssertionError("forecast action prediction mismatch: " + str(audit))
    return actual


def _forecast_transition(before: dict, action: dict) -> tuple[dict, dict, dict]:
    """Use an isolated forward-model fork before dispatch to create the proposal."""
    forecast = Executor(before)
    receipt = forecast.execute(action)
    after = forecast.checkpoint()
    prediction = _prediction_for_transition(before, after, receipt) if receipt.get("accepted") else None
    return receipt, after, prediction


def _prediction_for_transition(before: dict, after: dict, receipt: dict) -> dict:
    operator = receipt["intent"]["operator"]
    preconditions = {path: _path_value(before, path) for path in PRECONDITIONS[operator]}
    pins = before["config_pins"]
    return prediction_record(
        receipt["intent"], preconditions=preconditions,
        post_world=after["W"], post_observation=after["O"],
        effects=receipt["delta_w"], events=_event_signatures(receipt["event_payloads"]),
        checkpoint_id=_hash(before), frontier_id=str(before["clock"]["now"]),
        duration_pin=pins["unlock_duration"], deadline_pin=pins["deadline"],
        reply_pin=pins["reply"], coverage=_coverage(operator),
    )


def _audit_transition(before: dict, after: dict, receipt: dict, prediction: dict | None = None) -> dict:
    return audit_prediction(
        prediction or _prediction_for_transition(before, after, receipt), receipt,
        receipt["delta_w"], receipt["delta_o"], actual_world=after["W"],
        actual_observation=after["O"], before_world=before["W"],
        before_observation=before["O"], actual_events=receipt["event_payloads"],
        checkpoint_id=_hash(before), frontier_id=str(before["clock"]["now"]),
        config_pins=before["config_pins"],
    )


def _perform_goal_path(checkpoint: dict, *, label: str = "goal_path",
                       recordings: dict[str, list[dict]] | None = None) -> tuple[dict, list[dict]]:
    executor = Executor(checkpoint)
    recordings = recordings if recordings is not None else {}
    start = executor.checkpoint()["clock"]["now"]
    receipts = []
    receipts.append(_execute_recorded(executor, intent("offer_loan", target="B", payment="payment"), label=label, recordings=recordings))
    offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
    receipts.append(_execute_recorded(executor, intent("choose_accept", offer_id=offer_id), label=label, recordings=recordings))
    receipts.append(_execute_recorded(executor, intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id), label=label, recordings=recordings))
    receipts.append(_execute_recorded(executor, intent("unlock", item="key1"), label=label, recordings=recordings))
    receipts.append(_execute_recorded(executor, intent("take_ledger", item="ledger"), label=label, recordings=recordings))
    for receipt in receipts:
        if receipt["status"] != "SUCCESS" or not receipt["accepted"]:
            raise AssertionError("goal path action did not settle: " + str(receipt))
    result = executor.checkpoint()
    if result["clock"]["now"] - start != 5:
        raise AssertionError("baseline path must consume exactly five simulated minutes")
    return result, receipts


def _replay_minute_path(checkpoint: dict, path: list[dict], *, planner_path: bool,
                        recordings: dict[str, list[dict]] | None = None, label: str = "replay") -> dict:
    """Replay an actual search path through Executor, one boundary at a time."""
    executor = Executor(checkpoint)
    recordings = recordings if recordings is not None else {}
    recordings.setdefault(label, [])
    start_time = executor.checkpoint()["clock"]["now"]
    active_prediction = None

    def begin_forecast(action: dict) -> None:
        nonlocal active_prediction
        before = executor.checkpoint()
        forecast_receipt, forecast_after, prediction = _forecast_transition(before, action)
        active_prediction = {"before": before, "forecast_receipt": forecast_receipt,
                             "prediction": prediction}
        recordings[label].append({"label": label, "phase": "PREDICTION_INPUT",
                                  "prediction": prediction, "forecast_receipt": forecast_receipt,
                                  "forecast_checkpoint": forecast_after})

    def check_settlement() -> None:
        nonlocal active_prediction
        if active_prediction is None or executor.checkpoint()["W"]["running_action"] is not None:
            return
        actual_cp = executor.checkpoint()
        action_id = active_prediction["forecast_receipt"]["action_id"]
        actual_receipt = next((row for row in actual_cp["receipts"] if row.get("action_id") == action_id), None)
        if actual_receipt is None or actual_receipt.get("status") != "SUCCESS":
            raise AssertionError("search path did not produce its forecasted settlement receipt")
        audit = _audit_transition(active_prediction["before"], actual_cp, actual_receipt,
                                  active_prediction["prediction"])
        recordings[label].append({"label": label, "phase": "PREDICTION_CHECK",
                                  "prediction": active_prediction["prediction"],
                                  "actual_receipt": actual_receipt, "audit": audit})
        if audit["status"] != "MATCH":
            raise AssertionError("search-path prediction mismatch: " + str(audit))
        active_prediction = None

    for index, step in enumerate(path):
        if planner_path:
            control = step.get("control")
            if control == "ACTION_START":
                action = step.get("intent")
                begin_forecast(action)
                receipt = executor.start(action)
                if not receipt.get("accepted"):
                    raise AssertionError(f"planner replay rejected action at edge {index}: {receipt}")
                recordings[label].append(_boundary_snapshot(executor, label=label, phase="ACTION_START"))
                executor.advance_minute(started_action_id=receipt["action_id"])
            elif step.get("running_action_id") is not None:
                executor.advance_minute()
            else:
                begin_forecast(intent("idle"))
                receipt = executor.execute(intent("idle"))
                if receipt.get("status") != "SUCCESS":
                    raise AssertionError(f"planner replay no_control failed at edge {index}")
        else:
            op = step.get("operator")
            if op == "idle":
                running = executor.checkpoint()["W"]["running_action"]
                if running is not None:
                    executor.advance_minute()
                else:
                    begin_forecast(intent("idle"))
                    receipt = executor.execute(intent("idle"))
                    if receipt.get("status") != "SUCCESS":
                        raise AssertionError(f"oracle replay no_control failed at edge {index}")
            else:
                action = {"operator": op, "actor": step["actor"], "args": deepcopy(step["args"])}
                begin_forecast(action)
                receipt = executor.start(action)
                if not receipt.get("accepted"):
                    raise AssertionError(f"oracle replay rejected action at edge {index}: {receipt}")
                recordings[label].append(_boundary_snapshot(executor, label=label, phase="ACTION_START"))
                executor.advance_minute(started_action_id=receipt["action_id"])
        state = executor.checkpoint()
        if state["clock"]["now"] != step.get("to_time", step.get("end_time")):
            raise AssertionError(f"replay boundary mismatch at edge {index}")
        recordings[label].append(_boundary_snapshot(executor, label=label, phase="MINUTE_BOUNDARY"))
        check_settlement()
    final = executor.checkpoint()
    goal = evaluate_goal(final)
    if goal["status"] != "SATISFIED":
        raise AssertionError("search witness replay did not satisfy the shared event Monitor")
    return {"start_time": start_time, "end_time": final["clock"]["now"],
            "witness_event_ids": goal["witness_event_ids"], "trace": _trace_payload(final),
            "boundary_snapshots": recordings[label]}


def _seal_to_deadline(checkpoint: dict, *, label: str = "no_control_to_deadline",
                      recordings: dict[str, list[dict]] | None = None) -> dict:
    executor = Executor(checkpoint)
    recordings = recordings if recordings is not None else {}
    while executor.checkpoint()["clock"]["now"] < executor.checkpoint()["config_pins"]["deadline"]:
        receipt = _execute_recorded(executor, intent("idle"), label=label, recordings=recordings)
        if receipt["status"] != "SUCCESS":
            raise AssertionError("no_control failed before deadline")
    return executor.checkpoint()


def _search_result(case_id: str, checkpoint: dict) -> tuple[dict, dict, str | None]:
    if case_id == "E0-C01":
        return (uniform_cost_search(checkpoint, max_expansions=1, wall_seconds=WALL_SECONDS),
                solve_oracle(checkpoint, max_expansions=1, timeout_seconds=WALL_SECONDS), "BUDGET")
    if case_id in ("E0-X01", "E0-X02", "E0-U01", "E0-F01"):
        return {}, {}, None
    planner = uniform_cost_search(checkpoint, max_expansions=EXPANSION_CAP, wall_seconds=WALL_SECONDS)
    oracle = solve_oracle(checkpoint, max_expansions=EXPANSION_CAP, timeout_seconds=WALL_SECONDS)
    expected = "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN" if case_id in ("E0-N01", "E0-N02", "E0-B02", "E0-H02") else "POSSIBLE_IN_WORLD"
    return planner, oracle, expected


def _check_search(case_id: str, planner: dict, oracle: dict, expected: str | None) -> None:
    if expected is None:
        return
    if expected == "BUDGET":
        if not (planner.get("solve_status") == "BUDGET" and oracle.get("solve_status") == "BUDGET"
                and planner.get("complete") is False and oracle.get("complete") is False
                and planner.get("exhausted") is False and oracle.get("exhausted") is False):
            raise AssertionError("budget fixture must report incomplete BUDGET, not a solved verdict")
        return
    if not oracle.get("complete") or not oracle.get("exhausted"):
        raise AssertionError("oracle did not exhaust the finite state space")
    if oracle["solve_status"] != expected:
        raise AssertionError(f"oracle status {oracle['solve_status']} != {expected}")
    expected_planner = "UNREACHABLE" if expected == "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN" else "WITNESS_FOUND"
    if planner.get("solve_status") != expected_planner:
        raise AssertionError(f"planner status {planner.get('solve_status')} != {expected_planner}")
    if expected == "POSSIBLE_IN_WORLD":
        if planner.get("earliest_completion_time") != oracle.get("earliest_completion_time"):
            raise AssertionError("planner/oracle earliest completion time differs")
        if planner.get("shortest_simulated_duration") != oracle.get("shortest_duration_minutes"):
            raise AssertionError("planner/oracle shortest simulated duration differs")


def _case_checks(case_id: str, checkpoint: dict, recordings: dict[str, list[dict]],
                 evidence: dict | None = None) -> dict:
    evidence = evidence if evidence is not None else {}
    evidence["initial_checkpoint_sha256"] = _hash(checkpoint)
    if case_id in ("E0-P01", "E0-B01"):
        final, _ = _perform_goal_path(checkpoint, label="goal_path", recordings=recordings)
        evidence["goal_monitor"] = evaluate_goal(final)
        if evidence["goal_monitor"]["status"] != "SATISFIED":
            raise AssertionError("successful path lacks Monitor SATISFIED witness")
        evidence["raw_trace"] = _trace_payload(final)
        expected_time = 7
        if evidence["goal_monitor"]["witness_event_ids"] != ["event-000004"] or final["clock"]["now"] != expected_time:
            raise AssertionError("deadline-boundary witness or path endpoint differs")
    elif case_id == "E0-B02":
        final = _seal_to_deadline(checkpoint, recordings=recordings)
        evidence["goal_monitor"] = evaluate_goal(final)
        if evidence["goal_monitor"]["status"] != "VIOLATED":
            raise AssertionError("deadline 6 must seal without target event")
        evidence["raw_trace"] = _trace_payload(final)
    elif case_id in ("E0-N01", "E0-N02"):
        declining = Executor(checkpoint)
        offer = _execute_recorded(declining, intent("offer_loan", target="B", payment="payment"), label="decline_path", recordings=recordings)
        offer_id = declining.checkpoint()["W"]["offer_session"]["offer_id"]
        reply = _execute_recorded(declining, intent("choose_decline", offer_id=offer_id), label="decline_path", recordings=recordings)
        after_reply = declining.checkpoint()
        if (offer["status"] != "SUCCESS" or reply["status"] != "SUCCESS"
                or after_reply["clock"]["now"] != 4
                or after_reply["W"]["holders"]["key1"] != (None if case_id == "E0-N02" else "B")
                or after_reply["W"]["holders"]["payment"] != "A"):
            raise AssertionError("decline must not transfer key/payment")
        evidence["after_decline"] = _trace_payload(after_reply)
        evidence["pending_after_decline"] = evaluate_goal(after_reply)
        if evidence["pending_after_decline"]["status"] != "PENDING":
            raise AssertionError("decline at t4 must leave event objective pending")
        final = _seal_to_deadline(after_reply, label="decline_no_control_to_deadline", recordings=recordings)
        evidence["goal_monitor"] = evaluate_goal(final)
        if evidence["goal_monitor"]["status"] != "VIOLATED":
            raise AssertionError("decline/tombstone fixture must seal without target event")
        if case_id == "E0-N02" and not final["W"]["destroyed"]["key1"]:
            raise AssertionError("key1 tombstone was lost")
        evidence["raw_trace"] = _trace_payload(final)
        joint = deepcopy(checkpoint)
        joint["config_pins"]["reply"] = "JOINT"
        joint_planner, joint_oracle = (
            uniform_cost_search(joint, max_expansions=EXPANSION_CAP, wall_seconds=WALL_SECONDS),
            solve_oracle(joint, max_expansions=EXPANSION_CAP, timeout_seconds=WALL_SECONDS),
        )
        evidence["joint_pin_search"] = {"search_result": joint_planner, "oracle_result": joint_oracle}
        joint_expected = "POSSIBLE_IN_WORLD" if case_id == "E0-N01" else "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN"
        _check_search(case_id, joint_planner, joint_oracle, joint_expected)
        if joint_expected == "POSSIBLE_IN_WORLD":
            evidence["joint_pin_replay"] = _replay_minute_path(
                joint, joint_planner["path"], planner_path=True,
                recordings=recordings, label="joint_pin_planner_replay")
    elif case_id == "E0-H01":
        before = deepcopy(checkpoint)
        executor = Executor(checkpoint)
        receipt = _execute_recorded(executor, intent("unlock", item="key0"), label="illegal_key0_unlock", recordings=recordings)
        final = executor.checkpoint()
        evidence["rejected_key0_unlock"] = receipt
        evidence["rejected_key0_trace"] = _trace_payload(final)
        if receipt["accepted"] or final["W"]["intact"]["key0"] or not final["W"]["destroyed"]["key0"]:
            raise AssertionError("destroyed key0 was revived or unlock accepted")
        if final["W"] != before["W"]:
            raise AssertionError("rejected key0 unlock changed world state")
        clear_executor = Executor(final)
        first_no_control = _execute_recorded(clear_executor, intent("idle"), label="key0_rejection_no_control",
                                             recordings=recordings)
        if first_no_control["status"] != "SUCCESS" or clear_executor.checkpoint()["clock"]["now"] != 3:
            raise AssertionError("key0 unlock rejection must be followed by one no_control minute")
        clear_before = clear_executor.checkpoint()
        clear_receipt = _execute_recorded(clear_executor, intent("clear_tombstone", item="key0"),
                                           label="unknown_clear_request", recordings=recordings)
        if clear_receipt.get("accepted") or clear_executor.checkpoint()["W"] != clear_before["W"]:
            raise AssertionError("unknown tombstone-clear action was not rejected without W effect")
        no_control = _execute_recorded(clear_executor, intent("idle"), label="clear_rejection_no_control",
                                       recordings=recordings)
        if no_control["status"] != "SUCCESS" or clear_executor.checkpoint()["clock"]["now"] != 4:
            raise AssertionError("clear rejection was not followed by one normal no_control minute")
        evidence["rejected_clear"] = clear_receipt
        evidence["clear_request_trace"] = _trace_payload(clear_executor.checkpoint())
        goal, _ = _perform_goal_path(checkpoint, label="goal_path_after_key0_rejection", recordings=recordings)
        evidence["goal_monitor"] = evaluate_goal(goal)
        evidence["valid_goal_trace"] = _trace_payload(goal)
        evidence["raw_trace"] = _trace_payload(goal)
    elif case_id == "E0-B03":
        positive, _ = _perform_goal_path(checkpoint, label="positive_suffix", recordings=recordings)
        negative = _seal_to_deadline(checkpoint, label="negative_no_control_suffix", recordings=recordings)
        evidence["positive_monitor"] = evaluate_goal(positive)
        evidence["negative_monitor"] = evaluate_goal(negative)
        evidence["positive_raw_trace"] = _trace_payload(positive)
        evidence["negative_raw_trace"] = _trace_payload(negative)
        evidence["raw_trace"] = _trace_payload(positive)
        if positive["clock"]["now"] != 10 or evidence["positive_monitor"]["status"] != "SATISFIED":
            raise AssertionError("B03 positive suffix failed at t10")
        if evidence["negative_monitor"]["status"] != "VIOLATED":
            raise AssertionError("B03 no-control suffix did not seal negative at t10")
    elif case_id == "E0-H02":
        final = _seal_to_deadline(checkpoint, recordings=recordings)
        evidence["holding_at_10"] = evaluate_holding_at(final, at_time=10)
        evidence["goal_monitor"] = evaluate_goal(final)
        evidence["raw_trace"] = _trace_payload(final)
        if evidence["holding_at_10"]["status"] != "SATISFIED" or evidence["goal_monitor"]["status"] != "VIOLATED":
            raise AssertionError("H02 must separate state-at-T from event obligation")
    elif case_id == "E0-X01":
        invalid = intent("offer_loan", target="B", payment="payment", key="key1")
        evidence["illegal_binding"] = validate_binding(invalid, checkpoint["O"]["A"], checkpoint["domain"]["entities"])
        if evidence["illegal_binding"].get("status") != "INVALID_BINDING" or evidence["illegal_binding"].get("dispatch"):
            raise AssertionError("illegal key-bound offer was not blocked before dispatch")

        before = deepcopy(checkpoint)
        offer_action = intent("offer_loan", target="B", payment="payment")
        forecast_offer_receipt, forecast_offer_after, offer_prediction = _forecast_transition(before, offer_action)
        executor = Executor(checkpoint)
        receipt = _execute_recorded(executor, offer_action, label="x01_offer_actual_settlement", recordings=recordings)
        after = executor.checkpoint()
        matching = offer_prediction
        evidence["valid_prediction_input"] = matching
        evidence["valid_prediction_forecast_receipt"] = forecast_offer_receipt
        evidence["valid_prediction"] = _audit_transition(before, after, receipt, matching)
        if evidence["valid_prediction"]["status"] != "MATCH":
            raise AssertionError("valid offer prediction did not match")

        leaked = deepcopy(matching)
        leaked["post_observation"]["A"]["known_entities"].append("key1")
        evidence["offer_disclosure_mutation"] = _audit_transition(before, after, receipt, leaked)
        if evidence["offer_disclosure_mutation"]["status"] != "PREDICTION_MISMATCH":
            raise AssertionError("legal offer with false key1 disclosure escaped prediction audit")
        if after["W"]["offer_session"]["status"] != "OFFERED":
            raise AssertionError("prediction mismatch rolled back a legally settled offer")

        # The unlock prediction is audited independently from an actual unlock
        # settlement; a predicted ledger transfer must mismatch the real ΔW.
        staged = Executor(checkpoint)
        _execute_recorded(staged, intent("offer_loan", target="B", payment="payment"), label="x01_unlock_setup", recordings=recordings)
        offer_id = staged.checkpoint()["W"]["offer_session"]["offer_id"]
        _execute_recorded(staged, intent("choose_accept", offer_id=offer_id), label="x01_unlock_setup", recordings=recordings)
        _execute_recorded(staged, intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id), label="x01_unlock_setup", recordings=recordings)
        unlock_before = staged.checkpoint()
        unlock_action = intent("unlock", item="key1")
        forecast_unlock_receipt, forecast_unlock_after, unlock_prediction = _forecast_transition(unlock_before, unlock_action)
        unlock_receipt = _execute_recorded(staged, unlock_action, label="x01_unlock_actual_settlement", recordings=recordings)
        unlock_after = staged.checkpoint()
        unlock_prediction["post_world"]["holders"]["ledger"] = "A"
        unlock_prediction["effects"]["holders"] = ["ARCHIVE", "A"]
        unlock_prediction["events"].append({
            "event_type": "ledger_acquired", "time": unlock_after["clock"]["now"],
            "sequence": unlock_after["next_ids"]["sequence"], "producer_version": PRODUCER_VERSION,
            "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"},
        })
        evidence["unlock_prediction_input"] = unlock_prediction
        evidence["unlock_prediction_forecast_receipt"] = forecast_unlock_receipt
        evidence["unlock_ledger_mutation"] = _audit_transition(
            unlock_before, unlock_after, unlock_receipt, unlock_prediction)
        if evidence["unlock_ledger_mutation"]["status"] != "PREDICTION_MISMATCH":
            raise AssertionError("unlock prediction's direct ledger effect escaped audit")
        if unlock_after["W"]["holders"]["ledger"] != "ARCHIVE":
            raise AssertionError("unlock prediction mismatch changed the actual ledger holder")
        evidence["offer_actual_settlement_trace"] = _trace_payload(after)
        evidence["unlock_actual_settlement_trace"] = _trace_payload(unlock_after)
        evidence["unlock_monitor_without_ledger_event"] = evaluate_goal(unlock_after)
        if evidence["unlock_monitor_without_ledger_event"]["status"] != "PENDING":
            raise AssertionError("unlock-only mutation created a ledger-acquired witness")
        evidence["raw_trace"] = _trace_payload(after)
    elif case_id == "E0-X02":
        executor = Executor(checkpoint)
        _execute_recorded(executor, intent("offer_loan", target="B", payment="payment"), label="x02_real_prefix", recordings=recordings)
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        _execute_recorded(executor, intent("choose_accept", offer_id=offer_id), label="x02_real_prefix", recordings=recordings)
        real_t4 = executor.checkpoint()
        initial_hash = _hash(checkpoint)
        real_t4_hash = _hash(real_t4)
        fork = deepcopy(real_t4)
        fork["W"]["holders"]["payment"] = None
        before = deepcopy(fork)
        failed = Executor(fork)
        receipt = _execute_recorded(failed, intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id),
                                    label="x02_rejected_exchange", recordings=recordings)
        after = failed.checkpoint()
        evidence["atomic_exchange_rejection"] = receipt
        if receipt["accepted"] or after["W"]["holders"]["key1"] != "B" or after["W"]["holders"]["payment"] is not None:
            raise AssertionError("failed exchange partially transferred key or payment")
        if any(event["event_type"] == "loan_exchanged" for event in after["events"]):
            raise AssertionError("failed exchange emitted loan_exchanged")
        if after["W"] != before["W"] or after["events"] != before["events"]:
            raise AssertionError("rejected atomic exchange changed fork world or event ledger")
        if _hash(checkpoint) != initial_hash or _hash(real_t4) != real_t4_hash:
            raise AssertionError("X02 fork mutation contaminated initial or real accepted checkpoint")
        evidence["input_checkpoint_sha256"] = initial_hash
        evidence["real_t4_checkpoint_sha256"] = real_t4_hash
        evidence["mutated_fork_before_rejection"] = _trace_payload(before)
        evidence["rejected_fork_after"] = _trace_payload(after)
        evidence["raw_trace"] = _trace_payload(after)
    elif case_id == "E0-P02":
        executor = Executor(checkpoint)
        _execute_recorded(executor, intent("offer_loan", target="B", payment="payment"), label="p02_setup", recordings=recordings)
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        _execute_recorded(executor, intent("choose_accept", offer_id=offer_id), label="p02_setup", recordings=recordings)
        _execute_recorded(executor, intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id), label="p02_setup", recordings=recordings)
        before_start = executor.checkpoint()
        unlock_action = intent("unlock", item="key1")
        forecast_unlock_receipt, forecast_unlock_after, unlock_prediction = _forecast_transition(before_start, unlock_action)
        started = executor.start(intent("unlock", item="key1"))
        action_id = started["action_id"]
        recordings.setdefault("p02_running_unlock", []).append(_boundary_snapshot(executor, label="p02_running_unlock", phase="ACTION_START"))
        boundaries = []
        for expected_elapsed in (1, 2, 3):
            executor.advance_minute(started_action_id=action_id if expected_elapsed == 1 else None)
            state = executor.checkpoint()
            recordings["p02_running_unlock"].append(_boundary_snapshot(executor, label="p02_running_unlock", phase="MINUTE_BOUNDARY"))
            running = state["W"]["running_action"]
            if expected_elapsed < 3:
                if not running or running["id"] != action_id or running["elapsed"] != expected_elapsed:
                    raise AssertionError("P02 running action ID/elapsed drifted at minute boundary")
                if state["W"]["reservations"] != [{"action_id": action_id, "resources": ["key1", "ARCHIVE"]}]:
                    raise AssertionError("P02 reservation was not preserved")
            boundaries.append({"time": state["clock"]["now"], "running_action": running,
                               "reservations": state["W"]["reservations"]})
        if executor.checkpoint()["clock"]["now"] != 8 or executor.checkpoint()["W"]["archive_open"] is not True:
            raise AssertionError("P02 unlock did not settle at t8")
        settled = executor.checkpoint()
        unlock_receipts = [r for r in settled["receipts"] if r.get("intent", {}).get("operator") == "unlock"]
        if (settled["W"]["running_action"] is not None or settled["W"]["reservations"]
                or len(unlock_receipts) != 1 or unlock_receipts[0]["status"] != "SUCCESS"
                or unlock_receipts[0]["end_time"] != 8):
            raise AssertionError("P02 must release R/reservation and settle exactly once at t8")
        actual_unlock = unlock_receipts[0]
        unlock_audit = _audit_transition(before_start, settled, actual_unlock, unlock_prediction)
        evidence["unlock_prediction"] = unlock_prediction
        evidence["unlock_forecast_receipt"] = forecast_unlock_receipt
        evidence["unlock_prediction_audit"] = unlock_audit
        if unlock_audit["status"] != "MATCH":
            raise AssertionError("P02 unlock forecast did not match eventual settlement")
        _execute_recorded(executor, intent("take_ledger", item="ledger"), label="p02_take", recordings=recordings)
        final = executor.checkpoint()
        evidence["minute_boundaries"] = boundaries
        evidence["event_goal"] = evaluate_goal(final)
        evidence["raw_trace"] = _trace_payload(final)
        evidence["prior_clock"] = before_start["clock"]["now"]
        if final["clock"]["now"] != 9 or evidence["event_goal"]["status"] != "SATISFIED":
            raise AssertionError("P02 take event must settle at t9")
    elif case_id == "E0-U01":
        real_checkpoint = deepcopy(checkpoint)
        real_hash = _hash(real_checkpoint)
        evidence_copy = deepcopy(real_checkpoint)
        evidence_copy["seals"] = [seal for seal in evidence_copy["seals"] if seal["sealed_through"] < 2]
        evidence["untampered_input_hash"] = real_hash
        evidence["evidence_copy_hash"] = _hash(evidence_copy)
        evidence["missing_coverage"] = evaluate_goal(evidence_copy)
        evidence["raw_trace"] = _trace_payload(evidence_copy)
        if evidence["missing_coverage"]["status"] != "INDETERMINATE":
            raise AssertionError("U01 missing historical seal was not preserved as unknown")
        if _hash(real_checkpoint) != real_hash or real_checkpoint["seals"] != checkpoint["seals"]:
            raise AssertionError("U01 evidence mutation modified the real input checkpoint")
        later = Executor(evidence_copy)
        _execute_recorded(later, intent("idle"), label="u01_future_boundary", recordings=recordings)
        evidence["after_future_seal"] = evaluate_goal(later.checkpoint())
        if evidence["after_future_seal"]["status"] != "INDETERMINATE":
            raise AssertionError("future seal repaired U01's earlier gap")
        errors = []
        fake_event = deepcopy(evidence_copy)
        fake_event["events"].append({"event_id": "fake-ledger-event", "event_type": "ledger_acquired",
                                     "time": 2, "sequence": 99, "producer_version": PRODUCER_VERSION,
                                     "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"}})
        try:
            evaluate_goal(fake_event)
        except MonitorContractError as exc:
            errors.append({"mutation": "unsigned_target_event", "error": str(exc)})
        bad_version = deepcopy(evidence_copy)
        bad_version["events"][0]["producer_version"] = "forged-producer"
        event_id = bad_version["events"][0]["event_id"]
        for receipt in bad_version["receipts"]:
            if event_id in receipt.get("event_ids", []):
                receipt["event_payloads"][0]["producer_version"] = "forged-producer"
        try:
            evaluate_goal(bad_version)
        except MonitorContractError as exc:
            errors.append({"mutation": "forged_event_version", "error": str(exc)})
        evidence["contract_error_mutations"] = errors
        if len(errors) != 2:
            raise AssertionError("U01 did not retain both counterfeit-event and forged-version contract errors")
    elif case_id == "E0-C01":
        planner, oracle, _ = _search_result(case_id, checkpoint)
        evidence["budget_diagnostic"] = {"search_result": planner, "oracle_result": oracle}
        evidence["raw_trace"] = _trace_payload(checkpoint)
        if not (planner.get("solve_status") == "BUDGET" and oracle.get("solve_status") == "BUDGET"
                and planner.get("complete") is False and oracle.get("complete") is False
                and planner.get("exhausted") is False and oracle.get("exhausted") is False):
            raise AssertionError("C01 must correctly report capped, incomplete BUDGET")
    elif case_id == "E0-F01":
        base = initial_checkpoint("E0-P02")
        staged = Executor(base)
        _execute_recorded(staged, intent("offer_loan", target="B", payment="payment"), label="f01_running_prefix", recordings=recordings)
        offer_id = staged.checkpoint()["W"]["offer_session"]["offer_id"]
        _execute_recorded(staged, intent("choose_accept", offer_id=offer_id), label="f01_running_prefix", recordings=recordings)
        _execute_recorded(staged, intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id), label="f01_running_prefix", recordings=recordings)
        start = staged.start(intent("unlock", item="key1"))
        recordings.setdefault("f01_running_prefix", []).append(_boundary_snapshot(staged, label="f01_running_prefix", phase="ACTION_START"))
        staged.advance_minute(started_action_id=start["action_id"])
        recordings["f01_running_prefix"].append(_boundary_snapshot(staged, label="f01_running_prefix", phase="MINUTE_BOUNDARY"))
        running_cp = staged.checkpoint()
        if running_cp["W"]["running_action"] is None or running_cp["W"]["running_action"]["elapsed"] != 1:
            raise AssertionError("F01 fork checkpoint must include an active running action")
        input_hash = _hash(running_cp)

        def finish_same_suffix(source: dict, label: str) -> dict:
            branch = Executor(source)
            branch.advance_minute()
            recordings.setdefault(label, []).append(_boundary_snapshot(branch, label=label, phase="MINUTE_BOUNDARY"))
            branch.advance_minute()
            recordings[label].append(_boundary_snapshot(branch, label=label, phase="MINUTE_BOUNDARY"))
            _execute_recorded(branch, intent("take_ledger", item="ledger"), label=label, recordings=recordings)
            return branch.checkpoint()

        fork_one = finish_same_suffix(running_cp, "f01_fork_one")
        fork_two = finish_same_suffix(running_cp, "f01_fork_two")
        full_hash_one, full_hash_two = _hash(fork_one), _hash(fork_two)
        if full_hash_one != full_hash_two:
            raise AssertionError("restored running-action forks did not reproduce identical full checkpoints")
        mutated = deepcopy(running_cp)
        mutated["W"]["holders"]["ledger"] = "A"
        mutated["O"]["A"]["known_facts"].append("injected_fork_fact")
        mutated["W"]["running_action"]["progress"] = 99
        mutated["events"].append({"event_id": "fork-only-event", "event_type": "ledger_acquired",
                                  "time": 6, "sequence": 99, "producer_version": "fork-mutation",
                                  "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"}})
        if _hash(running_cp) != input_hash or _hash(finish_same_suffix(running_cp, "f01_fork_two_recheck")) != full_hash_two:
            raise AssertionError("fork mutation contaminated sibling or original running checkpoint")
        evidence.update({"running_checkpoint_sha256": input_hash,
                         "fork_full_checkpoint_hash_1": full_hash_one,
                         "fork_full_checkpoint_hash_2": full_hash_two,
                         "mutated_fork": _trace_payload(mutated),
                         "fork_one_trace": _trace_payload(fork_one),
                         "fork_two_trace": _trace_payload(fork_two),
                         "input_ledger_holder": running_cp["W"]["holders"]["ledger"]})
        evidence["raw_trace"] = _trace_payload(running_cp)
    return evidence


def run_case(case_id: str) -> dict:
    started = time.monotonic()
    checkpoint = initial_checkpoint(case_id)
    recordings: dict[str, list[dict]] = {}
    replay_recordings: dict[str, list[dict]] = {}
    evidence: dict = {}
    result = {"fixture_id": case_id, "input_hash": _hash(checkpoint),
              "config_pins": deepcopy(checkpoint["config_pins"]),
              "search_result": {}, "oracle_result": {},
              "fixture_test_result": "FAIL", "expected_label": None,
              "evidence": evidence, "boundary_snapshots": recordings,
              "search_replay_snapshots": replay_recordings, "errors": []}
    try:
        planner, oracle, expected = _search_result(case_id, checkpoint)
        result["search_result"], result["oracle_result"] = planner, oracle
        result["expected_label"] = expected
        _check_search(case_id, planner, oracle, expected)
        if expected == "POSSIBLE_IN_WORLD" and oracle.get("complete") and oracle.get("goal_found"):
            planner_replay = _replay_minute_path(checkpoint, planner.get("path", []), planner_path=True,
                                                 recordings=replay_recordings, label="planner_replay")
            oracle_replay = _replay_minute_path(checkpoint, oracle.get("goal_path", []), planner_path=False,
                                                recordings=replay_recordings, label="oracle_replay")
            expected_time = oracle["earliest_completion_time"]
            if planner_replay["end_time"] != expected_time or oracle_replay["end_time"] != expected_time:
                raise AssertionError("actual executor replays disagree with oracle earliest goal time")
            result["replay_evidence"] = {"planner": planner_replay, "oracle": oracle_replay}
        _case_checks(case_id, checkpoint, recordings, evidence)
        result["fixture_test_result"] = "PASS"
    except Exception as exc:  # Keep failure data in the result for diagnostics.
        result["errors"].append({"type": type(exc).__name__, "message": str(exc),
                                 "traceback": traceback.format_exc()})
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def run_all(case_ids: tuple[str, ...] = CASE_IDS) -> dict:
    runs = [run_case(case_id) for case_id in case_ids]
    code_revision = _code_revision()
    repo_root = Path(__file__).resolve().parents[2]
    protocol_path = repo_root / "00_研究设计/E0_KeyLedger_Protocol_v0.md"
    source_paths = [repo_root / "tools/e0_keyledger_v0" / name for name in
                    ("executor.py", "planner.py", "oracle.py", "prediction.py", "monitor_bridge.py", "runner.py", "fixtures.py")]
    source_paths.extend((repo_root / "tools/e0_keyledger_v0/tests" / name for name in
                         ("test_executor.py", "test_oracle.py", "test_monitor_bridge.py", "test_runner.py")))
    return {
        "schema_version": "e0-run-result-v0",
        "protocol_version": "E0-KeyLedger-v0",
        "run_kind": "ci" if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else "development",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "code_revision": code_revision,
        "provenance": {
            "protocol_freeze_commit": "e411ff45f67855e58d047fd37332b6896db5b8fe",
            "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest() if protocol_path.exists() else None,
            "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in source_paths if path.exists()},
            "python": sys.version,
            "platform": platform.platform(),
            "hardware": {"processor": platform.processor(), "machine": platform.machine(),
                         "cpu_count": os.cpu_count(),
                         "physical_memory_bytes": (os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                                                   if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names else None)},
            "execution_config": {"process_count": 1, "thread_count": 1,
                                  "expansion_cap": EXPANSION_CAP, "wall_seconds": WALL_SECONDS},
        },
        "budget": {"max_expansions": EXPANSION_CAP, "wall_seconds": WALL_SECONDS},
        "fixture_test_result": "PASS" if all(row["fixture_test_result"] == "PASS" for row in runs) else "FAIL",
        "fixtures": runs,
    }


def write_run(result: dict, output_root: Path, *, run_id: str | None = None) -> Path:
    """Write a unique, recoverable run folder; refuse to overwrite any path."""
    output_root.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case = result["fixtures"][0]["fixture_id"] if len(result["fixtures"]) == 1 else "all"
    run_id = run_id or secrets.token_hex(4)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", run_id):
        raise ValueError("run_id must contain only letters, digits, underscore, or hyphen")
    if any(output_root.glob(f"*_{case}_{run_id}")):
        raise FileExistsError(f"run_id already exists for {case}: {run_id}")
    run_dir = output_root / f"{created}_{case}_{run_id}"
    run_dir.mkdir(parents=False, exist_ok=False)
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in result["fixtures"]:
        raw = initial_checkpoint(row["fixture_id"])
        fixture_dir = run_dir / row["fixture_id"]
        fixture_dir.mkdir()
        (fixture_dir / "input_checkpoint.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (fixture_dir / "fixture_result.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("runs/e0_keyledger_v0/development"))
    parser.add_argument("--case", choices=("all", *CASE_IDS), default="all")
    parser.add_argument("--run-id", help="Optional stable identifier; an existing run folder is never overwritten.")
    parser.add_argument("--formal", action="store_true", help="Mark as formal; requires parent authorization outside this CLI.")
    args = parser.parse_args(argv)
    selected = CASE_IDS if args.case == "all" else (args.case,)
    selected_case = selected[0] if len(selected) == 1 else "all"
    check_id = args.run_id or "preflight"
    if args.run_id and any(args.output_root.glob(f"*_{selected_case}_{check_id}")):
        parser.error(f"run-id already exists for {selected_case}; refusing before running: {check_id}")
    result = run_all(selected)
    result["run_kind"] = "formal" if args.formal else ("ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "development")
    path = write_run(result, args.output_root, run_id=args.run_id)
    print(json.dumps({"run_dir": str(path), "fixture_test_result": result["fixture_test_result"],
                      "fixture_results": {row["fixture_id"]: row["fixture_test_result"] for row in result["fixtures"]}},
                     ensure_ascii=False, indent=2))
    return 0 if result["fixture_test_result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
