#!/usr/bin/env python3
"""Run one gated cancel control and, only if clean, one native TalkToNpc probe.

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
PAIR_MAX_WALL_AGE = 2.0
PAIR_MAX_GAME_AGE = 2.0
PAIR_MAX_DISTANCE = 8.0
STABLE_SECONDS = 5.0
PAIR_WINDOW_SECONDS = 60.0
NEGATIVE_WAIT_SECONDS = 80.0
POSITIVE_WAIT_SECONDS = 80.0
POST_WINDOW_SECONDS = 20.0
MAX_REQUEST_BYTES = 1_000_000


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
    for uid in (npc_uid, target_uid):
        sample = samples.get(uid)
        if not sample or now - sample["wall"] > PAIR_MAX_WALL_AGE:
            return False
        row = sample["row"]
        if row.get("event") != "native_npc_baseline" or row.get("mode") != "loaded":
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
        behavior = world.get("agent_behavior")
        if (not isinstance(pos, list) or len(pos) != 3
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pos)
                or not isinstance(behavior, str) or "SPEAK" not in behavior.upper()):
            return False
        pair.append((game_time, pos))
    if abs(pair[0][0] - pair[1][0]) > PAIR_MAX_GAME_AGE:
        return False
    delta = [pair[0][1][i] - pair[1][1][i] for i in range(3)]
    return math.sqrt(sum(value * value for value in delta)) <= PAIR_MAX_DISTANCE


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


def wait_for_pair(args, request_path: Path, samples: dict, event_state: dict,
                  latest: dict, deadline: float, require_empty: bool,
                  expected_request_bytes: bytes | None) -> bool:
    stable_since = None
    while time.monotonic() < deadline:
        if require_empty:
            if request_path.stat().st_size != 0:
                emit("abort_request_prefix_not_empty")
                return False
        elif expected_request_bytes is not None:
            if request_path.read_bytes() != expected_request_bytes:
                emit("abort_request_log_changed_after_cancel_control")
                return False

        for row in tail_events(Path(args.events), event_state):
            if isinstance(row.get("time"), (int, float)):
                latest["game_time"] = max(latest["game_time"], float(row["time"]))
            if row.get("event") == "native_npc_baseline" and row.get("npc_uid") in (
                args.npc_uid, args.target_uid
            ):
                samples[row["npc_uid"]] = {"row": row, "wall": time.monotonic()}

        now = time.monotonic()
        fresh = baseline_is_fresh_pair(samples, now, latest["game_time"],
                                       args.npc_uid, args.target_uid)
        if fresh:
            if stable_since is None:
                stable_since = now
                emit("pair_window_started", npc_uid=args.npc_uid,
                     target_uid=args.target_uid, game_time=latest["game_time"])
            if now - stable_since >= STABLE_SECONDS:
                emit("pair_window_passed", seconds=STABLE_SECONDS,
                     npc_uid=args.npc_uid, target_uid=args.target_uid,
                     game_time=latest["game_time"])
                return True
        else:
            stable_since = None
        time.sleep(POLL_SECONDS)
    emit("pair_window_expired", seconds=PAIR_WINDOW_SECONDS)
    return False


def run(args) -> int:
    request_path = Path(args.requests)
    check_empty_request_file(request_path)
    if args.npc_uid == args.target_uid or args.npc_uid < 0 or args.target_uid < 0:
        raise ValueError("NPC UIDs must be distinct non-negative integers")
    if args.cancel_id == args.request_id or not args.cancel_id or not args.request_id:
        raise ValueError("cancel ID and positive request ID must be distinct and non-empty")
    for value, label in ((args.source, "source"), (args.cancel_id, "cancel ID"),
                         (args.request_id, "request ID")):
        if len(value.encode("utf-8")) > 128 or (label == "source" and not value):
            raise ValueError(f"{label} must be non-empty when required and at most 128 UTF-8 bytes")

    events_path = Path(args.events)
    event_state = {"offset": events_path.stat().st_size if events_path.exists() else 0,
                   "pending": b""}
    samples = {}
    latest = {"game_time": float("-inf")}
    emit("probe_started", events=args.events, requests=args.requests,
         npc_uid=args.npc_uid, target_uid=args.target_uid,
         cancel_id=args.cancel_id, request_id=args.request_id,
         input_file_initially_empty=True, server_control="none")

    if not wait_for_pair(args, request_path, samples, event_state, latest,
                         time.monotonic() + PAIR_WINDOW_SECONDS, True, None):
        return 2

    negative_request = {
        "request_id": args.cancel_id, "npc_uid": args.npc_uid,
        "target_uid": args.target_uid, "source": args.source,
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

    negative_events = []
    negative_deadline = time.monotonic() + NEGATIVE_WAIT_SECONDS
    while time.monotonic() < negative_deadline:
        rows = tail_events(events_path, event_state)
        negative_events.extend(row for row in rows if row.get("request_id") == args.cancel_id)
        clean, reason = cancel_is_clean(negative_events, args.cancel_id)
        if any(row.get("event") == "native_brain_action_terminal"
               for row in negative_events):
            emit("cancel_control_terminal", clean=clean, reason=reason)
            if not clean:
                return 4
            break
        time.sleep(POLL_SECONDS)
    else:
        clean, reason = cancel_is_clean(negative_events, args.cancel_id)
        emit("abort_cancel_control_unproven", clean=clean, reason=reason)
        return 5

    if request_path.read_bytes() != negative_bytes:
        emit("abort_request_log_changed_after_cancel_control")
        return 6
    if not wait_for_pair(args, request_path, samples, event_state, latest,
                         time.monotonic() + PAIR_WINDOW_SECONDS, False, negative_bytes):
        return 7

    positive_request = {
        "request_id": args.request_id, "npc_uid": args.npc_uid,
        "target_uid": args.target_uid, "source": args.source,
        "ttl": 60.0, "kind": "TalkToNpc",
    }
    try:
        positive_bytes, written = append_records_once(
            request_path, [positive_request], len(negative_bytes)
        )
    except (OSError, RuntimeError, ValueError) as exc:
        emit("abort_positive_request_write", error=str(exc))
        return 8
    emit("input_transcript_positive_append", record=positive_request,
         os_write_calls=1, bytes=written, server_events_not_modified=True)

    positive_events = []
    positive_deadline = time.monotonic() + POSITIVE_WAIT_SECONDS
    agent_effect = brain_terminal = False
    while time.monotonic() < positive_deadline:
        rows = tail_events(events_path, event_state)
        positive_events.extend(row for row in rows if row.get("request_id") == args.request_id)
        agent_effect, brain_terminal = positive_complete(positive_events, args.request_id)
        if agent_effect and brain_terminal:
            emit("positive_observed_sender_agent_and_brain_terminal",
                 agent_effect=agent_effect, brain_terminal=brain_terminal)
            break
        time.sleep(POLL_SECONDS)
    else:
        emit("positive_wait_ttl_plus_20_timeout", agent_effect=agent_effect,
             brain_terminal=brain_terminal)

    emit("post_request_observation_started", seconds=POST_WINDOW_SECONDS)
    post_deadline = time.monotonic() + POST_WINDOW_SECONDS
    while time.monotonic() < post_deadline:
        for row in tail_events(events_path, event_state):
            if isinstance(row.get("time"), (int, float)):
                latest["game_time"] = max(latest["game_time"], float(row["time"]))
            if row.get("event") == "native_npc_baseline" and row.get("npc_uid") in (
                args.npc_uid, args.target_uid
            ):
                samples[row["npc_uid"]] = {"row": row, "wall": time.monotonic()}
        time.sleep(POLL_SECONDS)
    emit("probe_finished_not_game_verdict", positive_agent_effect=agent_effect,
         brain_terminal=brain_terminal, no_recipient_acceptance_claim=True)
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
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        emit("probe_aborted", error=str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
