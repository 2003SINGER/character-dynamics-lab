#!/usr/bin/env python3
"""Run one gated cancel control and up to six native TalkToNpc probes.

This helper never starts/stops Veloren and never writes to the server event log.
It appends request JSONL once per planned input and reports observations, not
game success.
"""

import argparse
import json
import math
import os
import stat
import sys
import time
from pathlib import Path


POLL_SECONDS = 0.1
SERVER_READY_SECONDS = 120.0
PAIR_MAX_WALL_AGE = 1.0
PAIR_MAX_TIME_SKEW = 0.1
PAIR_MAX_DISTANCE = 5.0
PAIR_PREVIOUS_MAX_DISTANCE = 6.0
PAIR_MAX_SEPARATION_SPEED = 0.5
PAIR_WINDOW_SECONDS = 60.0
NEGATIVE_WAIT_SECONDS = 80.0
POSITIVE_WAIT_SECONDS = 80.0
POST_WINDOW_SECONDS = 20.0
MAX_REQUEST_BYTES = 1_000_000
MAX_POSITIVE_REQUESTS = 6


def emit(event: str, **fields) -> None:
    print(json.dumps({"harness": event, **fields}, ensure_ascii=False,
                     separators=(",", ":")), flush=True)


def tail_events(path: Path, state: dict) -> list[dict]:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return []
    if size < state["offset"]:
        state["offset"] = 0
        state["pending"] = b""
        emit("events_truncated_restart_read", path=str(path))
    with path.open("rb") as stream:
        stream.seek(state["offset"])
        chunk = stream.read()
        state["offset"] += len(chunk)
    state["pending"] += chunk
    rows = []
    while b"\n" in state["pending"]:
        line, state["pending"] = state["pending"].split(b"\n", 1)
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            emit("ignored_unparsed_server_event_line", bytes=len(line))
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _valid_baseline_sample(sample: dict, now: float, sender: bool,
                           require_recent: bool = True) -> bool:
    if not sample or (require_recent and now - sample["wall"] > PAIR_MAX_WALL_AGE):
        return False
    row = sample["row"]
    world = row.get("actual_world_state")
    pos = world.get("ecs_position") if isinstance(world, dict) else None
    return (row.get("event") == "native_npc_baseline"
            and row.get("mode") == "loaded" and row.get("alive") is True
            and (not sender or row.get("external_lease_active") is False)
            and isinstance(row.get("time"), (int, float))
            and math.isfinite(row["time"])
            and isinstance(pos, list) and len(pos) == 3
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in pos)
            and world.get("agent_allowed_to_speak") is True)


def _paired_history(samples: dict, sender_uid: int, target_uid: int) -> list[tuple[dict, dict]]:
    left = samples.get(sender_uid, {}).get("history", [])
    right = samples.get(target_uid, {}).get("history", [])
    if len(left) < 2 or len(right) < 2:
        return []
    left, right = left[-2:], right[-2:]
    if any(float(a["row"]["time"]) >= float(b["row"]["time"])
           for a, b in zip(left, left[1:])):
        return []
    if any(float(a["row"]["time"]) >= float(b["row"]["time"])
           for a, b in zip(right, right[1:])):
        return []
    if any(abs(float(a["row"]["time"]) - float(b["row"]["time"]))
           > PAIR_MAX_TIME_SKEW for a, b in zip(left, right)):
        return []
    return list(zip(left, right))


def _distance_between_samples(first: dict, second: dict) -> float:
    a = first["row"]["actual_world_state"]["ecs_position"]
    b = second["row"]["actual_world_state"]["ecs_position"]
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def baseline_is_fresh_pair(samples: dict, now: float, latest_game_time: float,
                           npc_uid: int, target_uid: int) -> bool:
    history = _paired_history(samples, npc_uid, target_uid)
    if len(history) < 2:
        return False
    (sender_prev, target_prev), (sender_now, target_now) = history
    if not all((_valid_baseline_sample(sender_prev, now, True, False),
                _valid_baseline_sample(target_prev, now, False, False),
                _valid_baseline_sample(sender_now, now, True),
                _valid_baseline_sample(target_now, now, False))):
        return False
    if max(now - sender_now["wall"], now - target_now["wall"]) > PAIR_MAX_WALL_AGE:
        return False
    previous_time = (sender_prev["row"]["time"] + target_prev["row"]["time"]) / 2.0
    current_time = (sender_now["row"]["time"] + target_now["row"]["time"]) / 2.0
    delta_time = current_time - previous_time
    if delta_time <= 0:
        return False
    previous_distance = _distance_between_samples(sender_prev, target_prev)
    current_distance = _distance_between_samples(sender_now, target_now)
    separation_speed = (current_distance - previous_distance) / delta_time
    return (previous_distance <= PAIR_PREVIOUS_MAX_DISTANCE
            and current_distance <= PAIR_MAX_DISTANCE
            and separation_speed <= PAIR_MAX_SEPARATION_SPEED)


def normalize_pair(first_uid: int, second_uid: int) -> tuple[int, int]:
    return (first_uid, second_uid) if first_uid < second_uid else (second_uid, first_uid)


def positive_request_id(base: str, attempt: int, maximum: int) -> str:
    if not 1 <= maximum <= MAX_POSITIVE_REQUESTS or not 1 <= attempt <= maximum:
        raise ValueError("positive request attempt is outside the fixed submission budget")
    return base if maximum == 1 else f"{base}-{attempt:03d}"


def pair_distance(samples: dict, first_uid: int, second_uid: int) -> float:
    return _distance_between_samples(samples[first_uid], samples[second_uid])


def catalog_pairs_from_event(row: dict) -> set[tuple[int, int]]:
    if row.get("event") != "native_npc_catalog":
        return set()
    pairs = set()
    for pair in row.get("loaded_talkable_pairs_sample", []):
        try:
            first_uid = int(pair["from"]["npc_uid"])
            second_uid = int(pair["to"]["npc_uid"])
        except (KeyError, TypeError, ValueError):
            continue
        if first_uid >= 0 and second_uid >= 0 and first_uid != second_uid:
            pairs.add(normalize_pair(first_uid, second_uid))
    return pairs


def ordered_eligible_pairs(samples: dict, candidate_pairs: set[tuple[int, int]],
                           preferred_pair: tuple[int, int], now: float,
                           latest_game_time: float) -> list[tuple[int, int]]:
    eligible = []
    for sender_uid, target_uid in candidate_pairs:
        if baseline_is_fresh_pair(samples, now, latest_game_time, sender_uid, target_uid):
            eligible.append((sender_uid, target_uid))
    if preferred_pair in eligible:
        return [preferred_pair] + sorted(
            (pair for pair in eligible if pair != preferred_pair),
            key=lambda pair: (pair_distance(samples, *pair), pair[0], pair[1]))
    return sorted(eligible, key=lambda pair: (pair_distance(samples, *pair), pair[0], pair[1]))


def append_records_once(path: Path, records: list[dict], expected_size: int) -> tuple[bytes, int]:
    payload = b"".join(
        (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for record in records
    )
    if len(payload) >= MAX_REQUEST_BYTES:
        raise ValueError("planned JSONL append exceeds the server's 1 MiB batch limit")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        current_size = os.fstat(fd).st_size
        if current_size != expected_size:
            raise RuntimeError(f"request file changed unexpectedly: {current_size} != {expected_size}")
        written = os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    if written != len(payload):
        raise OSError(f"single append was partial: {written}/{len(payload)} bytes; not retried")
    return payload, written


def cancel_is_clean(events: list[dict], request_id: str) -> tuple[bool, str]:
    relevant = [row for row in events if row.get("request_id") == request_id]
    if any(row.get("event") in ("native_speech_emitted", "speech_blocked")
           or row.get("event") in ("native_action_handoff", "native_action_filtered")
           or (row.get("event") == "native_brain_action_terminal"
               and row.get("outcome") == "native_intent_queued") for row in relevant):
        return False, "CANCEL_INCORRECT_RESULT"
    if any(row.get("event") == "request_rejected" for row in relevant):
        return False, "CANCEL_REJECTED_AT_ADMISSION"
    terminal = next((row for row in relevant
                     if row.get("event") == "native_brain_action_terminal"), None)
    if terminal is None:
        return False, "CANCEL_NOT_OBSERVED"
    if terminal.get("outcome") != "cancelled_before_native_action":
        return False, "CANCEL_INCORRECT_RESULT"
    return True, "CANCEL_PASS"


def positive_complete(events: list[dict], request_id: str) -> tuple[bool, bool]:
    relevant = [row for row in events if row.get("request_id") == request_id]
    agent = any(row.get("event") in ("native_speech_emitted", "speech_blocked")
                for row in relevant)
    brain_terminal = any(row.get("event") == "native_brain_action_terminal"
                         for row in relevant)
    return agent, brain_terminal


def positive_chain_complete(events: list[dict], request_id: str,
                            native_continuation: bool) -> bool:
    relevant = [row for row in events if row.get("request_id") == request_id]
    accepted = any(row.get("event") == "request_accepted" for row in relevant)
    branch = any(row.get("event") == "native_talk_branch" for row in relevant)
    terminal = any(row.get("event") == "native_brain_action_terminal"
                   and row.get("outcome") == "native_intent_queued" for row in relevant)
    handoff = any(row.get("event") == "native_action_handoff"
                  and row.get("action") == "Say"
                  and row.get("destination") == "agent_queue" for row in relevant)
    agent = any(row.get("event") in ("native_speech_emitted", "speech_blocked")
                for row in relevant)
    return bool(accepted and branch and terminal and handoff and agent and native_continuation)


def _readable_native_snapshot(row: dict) -> bool:
    world = row.get("actual_world_state")
    pos = world.get("ecs_position") if isinstance(world, dict) else None
    return (row.get("event") == "native_npc_baseline"
            and row.get("mode") == "loaded" and row.get("alive") is True
            and isinstance(row.get("brain_backtrace"), list)
            and isinstance(row.get("controller_activity"), str)
            and isinstance(pos, list) and len(pos) == 3
            and all(isinstance(value, (int, float)) and math.isfinite(value) for value in pos))


def baseline_prefix_ready(prefix_snapshots: dict) -> bool:
    times = sorted(prefix_snapshots)
    return (len(times) >= 3
            and prefix_snapshots[times[-1]] - prefix_snapshots[times[0]] >= 2.0)


def check_empty_request_file(path: Path) -> None:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != 0:
        raise ValueError("request file must already exist as an empty regular file")


def read_observation_rows(args, event_state: dict, samples: dict, candidate_state: dict,
                          latest: dict) -> list[dict]:
    rows = tail_events(Path(args.events), event_state)
    now = time.monotonic()
    for row in rows:
        if row.get("request_id") in event_state.get("monitored_request_ids", set()):
            event_state.setdefault("monitored_events", []).append(row)
        if isinstance(row.get("time"), (int, float)):
            latest["game_time"] = max(latest["game_time"], float(row["time"]))
        if row.get("event") == "native_npc_catalog":
            candidate_state["pairs"] = catalog_pairs_from_event(row)
        if row.get("event") == "native_npc_baseline":
            if _readable_native_snapshot(row):
                event_state.setdefault("prefix_snapshots", {}).setdefault(
                    float(row["time"]), now)
            try:
                uid = int(row["npc_uid"])
            except (KeyError, TypeError, ValueError):
                continue
            history = samples.setdefault(uid, {"history": []})["history"]
            game_time = row.get("time")
            if not history or game_time > history[-1]["row"].get("time", float("-inf")):
                history.append({"row": row, "wall": now})
                del history[:-4]
                samples[uid]["row"] = row
                samples[uid]["wall"] = now
    cancel_id = event_state.get("cancel_id")
    if cancel_id:
        monitored = [row for row in event_state.get("monitored_events", [])
                     if row.get("request_id") == cancel_id]
        rejected = any(row.get("event") == "request_rejected" for row in monitored)
        effects = [row for row in monitored if row.get("event") in (
            "native_action_handoff", "native_action_filtered", "native_speech_emitted",
            "speech_blocked") or (row.get("event") == "native_brain_action_terminal"
                                   and row.get("outcome") == "native_intent_queued")]
        if effects and not event_state.get("control_violation"):
            event_state["control_violation"] = {
                "request_id": cancel_id, "admission_rejected": rejected, "events": effects,
            }
    return rows


def request_prefix_is_valid(request_path: Path, require_empty: bool,
                            expected_request_bytes: bytes | None) -> bool:
    if require_empty:
        valid = request_path.stat().st_size == 0
    else:
        valid = (expected_request_bytes is not None
                 and request_path.read_bytes() == expected_request_bytes)
    if not valid:
        emit("abort_request_prefix_changed")
    return valid


def wait_for_candidate(args, request_path: Path, samples: dict, event_state: dict,
                       candidate_state: dict, latest: dict, deadline: float,
                       require_empty: bool, expected_request_bytes: bytes | None,
                       preferred_pair: tuple[int, int]) -> tuple[int, int] | None:
    candidate_state["pairs"].add(preferred_pair)
    emit("candidate_window_started", seconds=PAIR_WINDOW_SECONDS,
         preferred_pair=list(preferred_pair))
    while time.monotonic() < deadline:
        if event_state.get("control_violation"):
            emit("probe_stopped_cancel_attribution_violation",
                 violation=event_state["control_violation"])
            return None
        if not request_prefix_is_valid(request_path, require_empty, expected_request_bytes):
            return None
        read_observation_rows(args, event_state, samples, candidate_state, latest)
        if event_state.get("cancel_id"):
            monitored = [row for row in event_state.get("monitored_events", [])
                         if row.get("request_id") == event_state["cancel_id"]]
            rejected = any(row.get("event") == "request_rejected" for row in monitored)
            action_events = [row for row in monitored if row.get("event") in (
                "native_action_handoff", "native_action_filtered", "native_speech_emitted",
                "speech_blocked") or (row.get("event") == "native_brain_action_terminal"
                                       and row.get("outcome") == "native_intent_queued")]
            if action_events:
                event_state["control_violation"] = {
                    "request_id": event_state["cancel_id"],
                    "admission_rejected": rejected,
                    "events": action_events,
                }
                emit("cancel_request_later_effect_violation",
                     violation=event_state["control_violation"])
                return None
        candidate_state["pairs"].add(preferred_pair)
        now = time.monotonic()
        eligible = ordered_eligible_pairs(
            samples, candidate_state["pairs"], preferred_pair, now,
            latest["game_time"])
        for pair in eligible:
            emit("candidate_pair_passed", samples_required=2,
                 npc_uid=pair[0], target_uid=pair[1],
                 distance_3d=pair_distance(samples, *pair),
                 game_time=latest["game_time"],
                 selection="preferred" if pair == preferred_pair else "catalog_distance_uid_order")
            return pair
        time.sleep(POLL_SECONDS)
    emit("candidate_window_expired", seconds=PAIR_WINDOW_SECONDS,
         available_catalog_pairs=len(candidate_state["pairs"]))
    return None


def wait_for_first_baseline(args, event_state: dict, samples: dict,
                            candidate_state: dict, latest: dict,
                            deadline: float) -> bool:
    emit("server_ready_window_started", seconds=SERVER_READY_SECONDS,
         required_distinct_game_times=3, required_wall_span_seconds=2.0,
         request_file_must_remain_empty=True)
    while time.monotonic() < deadline:
        if Path(args.requests).stat().st_size != 0:
            emit("abort_request_prefix_changed_before_baseline")
            return False
        read_observation_rows(args, event_state, samples, candidate_state, latest)
        snapshots = event_state.get("prefix_snapshots", {})
        times = sorted(snapshots)
        if baseline_prefix_ready(snapshots):
            emit("server_ready_baseline_prefix", distinct_game_times=len(times),
                 first_game_time=times[0], last_game_time=times[-1],
                 first_wall_monotonic=snapshots[times[0]],
                 last_wall_monotonic=snapshots[times[-1]],
                 catalog_pairs=len(candidate_state["pairs"]))
            return True
        time.sleep(POLL_SECONDS)
    emit("server_ready_timeout", seconds=SERVER_READY_SECONDS)
    return False


def collect_request_events(args, request_id: str, event_state: dict, samples: dict,
                           candidate_state: dict, latest: dict, deadline: float,
                           require_handoff: bool = False) -> list[dict]:
    relevant = []
    while time.monotonic() < deadline:
        for row in read_observation_rows(args, event_state, samples, candidate_state, latest):
            if row.get("request_id") == request_id:
                relevant.append(row)
                if row.get("event") == "request_rejected":
                    emit("request_rejected_terminal", request_id=request_id,
                         reason=row.get("reason"), server_event=row)
                    return relevant
        if event_state.get("control_violation"):
            emit("probe_stopped_cancel_attribution_violation",
                 violation=event_state["control_violation"])
            return relevant
        has_agent_effect = any(row.get("event") in ("native_speech_emitted", "speech_blocked")
                               for row in relevant)
        has_handoff = any(row.get("event") == "native_action_handoff" for row in relevant)
        has_terminal = any(row.get("event") == "native_brain_action_terminal" for row in relevant)
        has_filtered = any(row.get("event") == "native_action_filtered" for row in relevant)
        if has_agent_effect and has_terminal and (has_handoff or has_filtered or not require_handoff):
            break
        if has_terminal and not has_agent_effect and not has_handoff and not has_filtered:
            terminal = next(row for row in reversed(relevant)
                            if row.get("event") == "native_brain_action_terminal")
            if terminal.get("outcome") not in ("native_intent_queued",):
                break
        if has_filtered:
            break
        time.sleep(POLL_SECONDS)
    return relevant


def post_request_continuation(args, sender_uid: int, event_state: dict, samples: dict,
                              candidate_state: dict, latest: dict) -> bool:
    observed = []
    last_game_time = float("-inf")
    deadline = time.monotonic() + POST_WINDOW_SECONDS
    while time.monotonic() < deadline:
        read_observation_rows(args, event_state, samples, candidate_state, latest)
        if event_state.get("control_violation"):
            emit("probe_stopped_cancel_attribution_violation",
                 violation=event_state["control_violation"])
            return False
        sample = samples.get(sender_uid)
        if sample and sample["row"].get("time", float("-inf")) > last_game_time:
            row = sample["row"]
            if (row.get("event") == "native_npc_baseline"
                    and row.get("alive") is True
                    and row.get("external_lease_active") is False
                    and isinstance(row.get("brain_backtrace"), list)
                    and row.get("brain_backtrace")):
                observed.append(sample)
                last_game_time = float(row["time"])
        time.sleep(POLL_SECONDS)
    if len(observed) < 2:
        return False
    first = observed[0]["row"]
    last = observed[-1]["row"]
    first_world = first.get("actual_world_state") or {}
    last_world = last.get("actual_world_state") or {}
    continued = any((first.get("brain_backtrace") != last.get("brain_backtrace"),
                     first_world.get("ecs_position") != last_world.get("ecs_position"),
                     first.get("controller_activity") != last.get("controller_activity")))
    emit("native_continuation_observed", sender_uid=sender_uid,
         samples=len(observed), continued=continued,
         first_game_time=first.get("time"), last_game_time=last.get("time"))
    return continued


def run(args) -> int:
    request_path = Path(args.requests)
    check_empty_request_file(request_path)
    if args.npc_uid == args.target_uid or args.npc_uid < 0 or args.target_uid < 0:
        raise ValueError("NPC UIDs must be distinct non-negative integers")
    if args.cancel_id == args.request_id or not args.cancel_id or not args.request_id:
        raise ValueError("cancel ID and positive request ID prefix must be distinct and non-empty")
    if not 1 <= args.max_positive <= MAX_POSITIVE_REQUESTS:
        raise ValueError(f"max-positive must be between 1 and {MAX_POSITIVE_REQUESTS}")
    for value, label in ((args.source, "source"), (args.cancel_id, "cancel ID"),
                         (args.request_id, "request ID prefix")):
        if len(value.encode("utf-8")) > 128 or (label == "source" and not value):
            raise ValueError(f"{label} must be non-empty when required and at most 128 UTF-8 bytes")

    events_path = Path(args.events)
    if events_path.exists() and events_path.stat().st_size:
        raise ValueError("events file must be new or empty for this run")
    event_state = {"offset": 0, "pending": b"", "monitored_request_ids": set(),
                   "monitored_events": []}
    samples = {}
    latest = {"game_time": float("-inf")}
    candidate_state = {"pairs": set()}
    preferred_pair = normalize_pair(args.npc_uid, args.target_uid)
    emit("probe_started", events=args.events, requests=args.requests,
         npc_uid=args.npc_uid, target_uid=args.target_uid,
         cancel_id=args.cancel_id, request_id=args.request_id,
         max_positive=args.max_positive, input_file_initially_empty=True,
         server_control="none")

    if not wait_for_first_baseline(
            args, event_state, samples, candidate_state, latest,
            time.monotonic() + SERVER_READY_SECONDS):
        return 9

    negative_pair = wait_for_candidate(
        args, request_path, samples, event_state, candidate_state, latest,
        time.monotonic() + PAIR_WINDOW_SECONDS, True, None, preferred_pair)
    if negative_pair is None:
        return 2

    negative_request = {
        "request_id": args.cancel_id, "npc_uid": negative_pair[0],
        "target_uid": negative_pair[1], "source": args.source,
        "ttl": 60.0, "kind": "TalkToNpc",
    }
    negative_cancel = {"cancel_request_id": args.cancel_id}
    try:
        negative_bytes, written = append_records_once(
            request_path, [negative_request, negative_cancel], 0
        )
    except (OSError, RuntimeError, ValueError) as exc:
        emit("abort_negative_control_write", error=str(exc))
        return 3
    emit("input_transcript_negative_atomic_append", records=[negative_request, negative_cancel],
         os_write_calls=1, bytes=written, server_events_not_modified=True)
    event_state["monitored_request_ids"].add(args.cancel_id)
    event_state["cancel_id"] = args.cancel_id

    negative_events = collect_request_events(
        args, args.cancel_id, event_state, samples, candidate_state, latest,
        time.monotonic() + NEGATIVE_WAIT_SECONDS, require_handoff=True)
    clean, reason = cancel_is_clean(negative_events, args.cancel_id)
    emit("cancel_control_terminal", clean=clean, reason=reason,
         request_id=args.cancel_id, npc_uid=negative_pair[0], target_uid=negative_pair[1])
    if reason == "CANCEL_INCORRECT_RESULT":
        emit("probe_stopped_invalid_cancel_result", request_id=args.cancel_id)
        return 4
    if reason == "CANCEL_NOT_OBSERVED":
        emit("cancel_control_status", status=reason, request_id=args.cancel_id)
    elif reason == "CANCEL_REJECTED_AT_ADMISSION":
        emit("cancel_control_status", status=reason, request_id=args.cancel_id)

    prefix = negative_bytes
    summary = []
    for attempt in range(1, args.max_positive + 1):
        if not request_prefix_is_valid(request_path, False, prefix):
            return 6
        pair = wait_for_candidate(
            args, request_path, samples, event_state, candidate_state, latest,
            time.monotonic() + PAIR_WINDOW_SECONDS, False, prefix, preferred_pair)
        if pair is None:
            emit("positive_budget_stopped_no_eligible_pair", submitted=len(summary),
                 maximum=args.max_positive)
            break
        request_id = positive_request_id(args.request_id, attempt, args.max_positive)
        if request_id == args.cancel_id:
            raise ValueError("generated positive request ID collides with cancel ID")
        if len(request_id.encode("utf-8")) > 128:
            raise ValueError("generated request ID exceeds 128 UTF-8 bytes")
        positive_request = {
            "request_id": request_id, "npc_uid": pair[0],
            "target_uid": pair[1], "source": args.source,
            "ttl": 60.0, "kind": "TalkToNpc",
        }
        try:
            positive_bytes, written = append_records_once(
                request_path, [positive_request], len(prefix)
            )
        except (OSError, RuntimeError, ValueError) as exc:
            emit("abort_positive_request_write", attempt=attempt, error=str(exc))
            return 8
        prefix += positive_bytes
        emit("input_transcript_positive_append", attempt=attempt, record=positive_request,
             os_write_calls=1, bytes=written, server_events_not_modified=True)

        positive_events = collect_request_events(
            args, request_id, event_state, samples, candidate_state, latest,
            time.monotonic() + POSITIVE_WAIT_SECONDS, require_handoff=True)
        agent_effect, brain_terminal = positive_complete(positive_events, request_id)
        branch = next((row for row in positive_events
                       if row.get("event") == "native_talk_branch"), None)
        handoff = next((row for row in positive_events
                        if row.get("event") == "native_action_handoff"
                        and row.get("action") == "Say"
                        and row.get("destination") == "agent_queue"), None)
        filtered = next((row for row in positive_events
                         if row.get("event") == "native_action_filtered"), None)
        terminal = next((row for row in reversed(positive_events)
                         if row.get("event") == "native_brain_action_terminal"), None)
        trial = {"attempt": attempt, "request_id": request_id,
                 "npc_uid": pair[0], "target_uid": pair[1],
                 "branch": branch, "handoff": handoff, "filtered": filtered,
                 "terminal": terminal, "agent_effect": agent_effect,
                 "brain_terminal": brain_terminal}
        trial["request_accepted"] = next((row for row in positive_events
                                          if row.get("event") == "request_accepted"), None)
        rejected = next((row for row in positive_events
                         if row.get("event") == "request_rejected"), None)
        trial["request_rejected"] = rejected
        trial["terminal_seen"] = terminal is not None
        summary.append(trial)
        emit("positive_trial_result", **trial)

        continuation = post_request_continuation(
            args, pair[0], event_state, samples, candidate_state, latest)
        trial["native_continuation_proven"] = continuation
        trial["complete_chain"] = positive_chain_complete(
            positive_events, request_id, continuation)
        emit("positive_trial_post_window", request_id=request_id,
             seconds=POST_WINDOW_SECONDS, native_continuation_proven=continuation)

        if trial["complete_chain"]:
            emit("probe_stopped_after_agent_effect", request_id=request_id,
                 native_continuation_proven=continuation)
            break
        if agent_effect or filtered or handoff:
            emit("probe_stopped_at_agent_handoff_boundary", request_id=request_id)
            break
        if terminal is None and rejected is None:
            emit("probe_stopped_feedback_unclosed", request_id=request_id,
                 submitted=len(summary))
            break
        if attempt < args.max_positive:
            emit("positive_trial_no_agent_effect_continue_within_fixed_budget",
                 attempt=attempt, request_id=request_id,
                 terminal=terminal, request_rejected=rejected)

    emit("probe_finished_not_game_verdict", positive_submissions=len(summary),
         maximum_positive_submissions=args.max_positive,
         agent_effect_seen=any(trial["agent_effect"] for trial in summary),
         complete_chain_proven=bool(summary and summary[-1].get("complete_chain")),
         no_recipient_acceptance_claim=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--npc-uid", type=int, required=True)
    parser.add_argument("--target-uid", type=int, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--cancel-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--max-positive", type=int, default=1,
                        help=f"positive request cap (1..{MAX_POSITIVE_REQUESTS}); each write counts")
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        emit("probe_aborted", error=str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
