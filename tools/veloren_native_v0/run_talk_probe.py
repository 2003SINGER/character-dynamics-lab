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
PAIR_MAX_WALL_AGE = 2.0
PAIR_MAX_GAME_AGE = 2.0
PAIR_MAX_DISTANCE = 8.0
STABLE_SECONDS = 5.0
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


def baseline_is_fresh_pair(samples: dict, now: float, latest_game_time: float,
                           npc_uid: int, target_uid: int) -> bool:
    pair = []
    for index, uid in enumerate((npc_uid, target_uid)):
        sample = samples.get(uid)
        if not sample or now - sample["wall"] > PAIR_MAX_WALL_AGE:
            return False
        row = sample["row"]
        if row.get("event") != "native_npc_baseline" or row.get("mode") != "loaded":
            return False
        if row.get("alive") is not True:
            return False
        if index == 0 and row.get("external_lease_active") is not False:
            return False
        game_time = row.get("time")
        if not isinstance(game_time, (int, float)) or not math.isfinite(game_time):
            return False
        if latest_game_time - game_time > PAIR_MAX_GAME_AGE:
            return False
        world = row.get("actual_world_state")
        if not isinstance(world, dict):
            return False
        pos = world.get("ecs_position")
        if (not isinstance(pos, list) or len(pos) != 3
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pos)
                or world.get("agent_allowed_to_speak") is not True):
            return False
        pair.append((game_time, pos))
    if abs(pair[0][0] - pair[1][0]) > PAIR_MAX_GAME_AGE:
        return False
    delta = [pair[0][1][i] - pair[1][1][i] for i in range(3)]
    return math.sqrt(sum(value * value for value in delta)) <= PAIR_MAX_DISTANCE


def normalize_pair(first_uid: int, second_uid: int) -> tuple[int, int]:
    return (first_uid, second_uid) if first_uid < second_uid else (second_uid, first_uid)


def positive_request_id(base: str, attempt: int, maximum: int) -> str:
    if not 1 <= maximum <= MAX_POSITIVE_REQUESTS or not 1 <= attempt <= maximum:
        raise ValueError("positive request attempt is outside the fixed submission budget")
    return base if maximum == 1 else f"{base}-{attempt:03d}"


def pair_distance(samples: dict, first_uid: int, second_uid: int) -> float:
    first = samples[first_uid]["row"]["actual_world_state"]["ecs_position"]
    second = samples[second_uid]["row"]["actual_world_state"]["ecs_position"]
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


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
                           latest_game_time: float, stable_since: dict,
                           stable_seconds: float = STABLE_SECONDS) -> list[tuple[int, int]]:
    for pair in list(stable_since):
        if pair not in candidate_pairs:
            stable_since.pop(pair, None)
    eligible = []
    for sender_uid, target_uid in candidate_pairs:
        if baseline_is_fresh_pair(samples, now, latest_game_time, sender_uid, target_uid):
            stable_since.setdefault((sender_uid, target_uid), now)
            if now - stable_since[(sender_uid, target_uid)] >= stable_seconds:
                eligible.append((sender_uid, target_uid))
        else:
            stable_since.pop((sender_uid, target_uid), None)
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
        return False, "cancel_control_had_intent_or_agent_effect"
    terminal = next((row for row in relevant
                     if row.get("event") == "native_brain_action_terminal"), None)
    if terminal is None:
        return False, "cancel_control_terminal_not_observed"
    if terminal.get("outcome") != "cancelled_before_native_action":
        return False, f"cancel_control_wrong_terminal:{terminal.get('outcome')}"
    return True, str(terminal.get("outcome"))


def positive_complete(events: list[dict], request_id: str) -> tuple[bool, bool]:
    relevant = [row for row in events if row.get("request_id") == request_id]
    agent = any(row.get("event") in ("native_speech_emitted", "speech_blocked")
                for row in relevant)
    brain_terminal = any(row.get("event") == "native_brain_action_terminal"
                         for row in relevant)
    return agent, brain_terminal


def check_empty_request_file(path: Path) -> None:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != 0:
        raise ValueError("request file must already exist as an empty regular file")


def read_observation_rows(args, event_state: dict, samples: dict, candidate_state: dict,
                          latest: dict) -> list[dict]:
    rows = tail_events(Path(args.events), event_state)
    now = time.monotonic()
    for row in rows:
        if isinstance(row.get("time"), (int, float)):
            latest["game_time"] = max(latest["game_time"], float(row["time"]))
        if row.get("event") == "native_npc_catalog":
            candidate_state["pairs"] = catalog_pairs_from_event(row)
        if row.get("event") == "native_npc_baseline":
            try:
                uid = int(row["npc_uid"])
            except (KeyError, TypeError, ValueError):
                continue
            samples[uid] = {"row": row, "wall": now}
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
    stable_since = {}
    emitted_started = set()
    candidate_state["pairs"].add(preferred_pair)
    emit("candidate_window_started", seconds=PAIR_WINDOW_SECONDS,
         preferred_pair=list(preferred_pair))
    while time.monotonic() < deadline:
        if not request_prefix_is_valid(request_path, require_empty, expected_request_bytes):
            return None
        read_observation_rows(args, event_state, samples, candidate_state, latest)
        candidate_state["pairs"].add(preferred_pair)
        now = time.monotonic()
        eligible = ordered_eligible_pairs(
            samples, candidate_state["pairs"], preferred_pair, now,
            latest["game_time"], stable_since)
        for pair in eligible:
            emit("candidate_pair_passed", stable_seconds=STABLE_SECONDS,
                 npc_uid=pair[0], target_uid=pair[1],
                 distance_3d=pair_distance(samples, *pair),
                 game_time=latest["game_time"],
                 selection="preferred" if pair == preferred_pair else "catalog_distance_uid_order")
            return pair
        for pair in candidate_state["pairs"]:
            if (pair[0] in samples and pair[1] in samples
                    and pair not in emitted_started
                    and baseline_is_fresh_pair(samples, now, latest["game_time"], *pair)):
                emitted_started.add(pair)
                emit("candidate_pair_stability_started", npc_uid=pair[0], target_uid=pair[1],
                     distance_3d=pair_distance(samples, *pair), game_time=latest["game_time"])
        time.sleep(POLL_SECONDS)
    emit("candidate_window_expired", seconds=PAIR_WINDOW_SECONDS,
         available_catalog_pairs=len(candidate_state["pairs"]))
    return None


def wait_for_first_baseline(args, event_state: dict, samples: dict,
                            candidate_state: dict, latest: dict,
                            deadline: float) -> bool:
    emit("server_ready_window_started", seconds=SERVER_READY_SECONDS)
    while time.monotonic() < deadline:
        rows = read_observation_rows(args, event_state, samples, candidate_state, latest)
        first = next((row for row in rows
                      if row.get("event") == "native_npc_baseline"
                      and isinstance(row.get("npc_uid"), int)
                      and isinstance(row.get("time"), (int, float))), None)
        if first:
            emit("server_ready_first_baseline", npc_uid=first["npc_uid"],
                 game_time=first["time"], catalog_pairs=len(candidate_state["pairs"]))
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
    event_state = {"offset": 0, "pending": b""}
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

    negative_events = collect_request_events(
        args, args.cancel_id, event_state, samples, candidate_state, latest,
        time.monotonic() + NEGATIVE_WAIT_SECONDS, require_handoff=True)
    clean, reason = cancel_is_clean(negative_events, args.cancel_id)
    if not any(row.get("event") == "native_brain_action_terminal" for row in negative_events):
        emit("abort_cancel_control_unproven", clean=clean, reason=reason)
        return 5
    emit("cancel_control_terminal", clean=clean, reason=reason,
         request_id=args.cancel_id, npc_uid=negative_pair[0], target_uid=negative_pair[1])
    if not clean:
        return 4

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
        rejected = next((row for row in positive_events
                         if row.get("event") == "request_rejected"), None)
        trial["request_rejected"] = rejected
        trial["terminal_seen"] = terminal is not None
        summary.append(trial)
        emit("positive_trial_result", **trial)

        continuation = post_request_continuation(
            args, pair[0], event_state, samples, candidate_state, latest)
        trial["native_continuation_proven"] = continuation
        emit("positive_trial_post_window", request_id=request_id,
             seconds=POST_WINDOW_SECONDS, native_continuation_proven=continuation)

        if agent_effect:
            emit("probe_stopped_after_agent_effect", request_id=request_id,
                 native_continuation_proven=continuation)
            break
        if filtered or (handoff and not agent_effect):
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
         complete_chain_proven=bool(summary and summary[-1]["agent_effect"]
                                    and summary[-1]["brain_terminal"]
                                    and summary[-1]["terminal"]
                                    and summary[-1]["terminal"].get("outcome") == "native_intent_queued"
                                    and summary[-1]["branch"]
                                    and summary[-1]["handoff"]
                                    and summary[-1].get("native_continuation_proven")),
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
