#!/usr/bin/env python3
"""Export one paired-harness JSONL trace to a player-safe static timeline.

Only explicit player-facing fields are copied into the output. The raw trace
is never embedded, transformed wholesale, or served to the browser.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


PROTOCOL = "npc-continuity-paired-trace-v1"
POLICIES = {"utility", "history-llm"}
CASES = {"alarm_active", "quiet_active", "near_completion_alarm"}
ACTION_NAMES = {
    "use_phone", "shop_on_phone", "use_computer", "study_at_computer",
    "study_focused", "study_halfhearted", "rest_at_bed", "sleep_at_bed",
    "go_to_bathroom", "get_meal", "turn_light_on", "turn_light_off",
    "turn_off_alarm", "open_curtain", "close_curtain", "idle",
}
ACTION_STATUSES = {"running", "completed", "interrupted", "rejected"}
FACT_KEYS = {
    "room.alarm",
    "message.unread_count",
    "task.coursework.status",
    "task.coursework.effort",
    "task.coursework.effort_target",
}
DISPLAY_TARGETS = {"desk", "computer", "bed", "phone", "door", "light", "alarm", "window", ""}
MAX_RECORDS = 100_005


class TraceError(ValueError):
    pass


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TraceError(f"{label} must be an object")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise TraceError(f"{label} must be an integer >= {minimum}")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TraceError(f"{label} must be a finite number")
    return float(value)


def _clock(total_minutes: int) -> str:
    day, minute = divmod(total_minutes, 24 * 60)
    clock = f"{minute // 60:02d}:{minute % 60:02d}"
    return clock if day == 0 else f"Day {day + 1} · {clock}"


def _fact_map(raw_facts: Any, label: str) -> dict[str, dict[str, str]]:
    if not isinstance(raw_facts, list):
        raise TraceError(f"{label} must be an array")
    facts: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(raw_facts):
        item = _object(raw, f"{label}[{index}]")
        key, value, status = item.get("key"), item.get("value"), item.get("status")
        if not all(isinstance(part, str) for part in (key, value, status)):
            raise TraceError(f"{label}[{index}] needs string key/value/status")
        if status not in {"known", "stale", "unknown"}:
            raise TraceError(f"{label}[{index}] has unsupported knowledge status")
        if key in FACT_KEYS:
            facts[key] = {"value": value, "status": status}
    return facts


def _known_value(facts: dict[str, dict[str, str]], key: str) -> str | None:
    fact = facts.get(key)
    if fact and fact["status"] == "known":
        return fact["value"]
    return None


def _safe_target(raw_target: Any) -> str:
    if not isinstance(raw_target, str) or raw_target not in DISPLAY_TARGETS:
        raise TraceError("running action target is not a display-safe room object")
    return raw_target


def _running_action(raw: Any, label: str, *, progress_at: int | None = None) -> dict[str, Any] | None:
    if raw is None:
        return None
    item = _object(raw, label)
    action = item.get("action")
    if action not in ACTION_NAMES:
        raise TraceError(f"{label}.action is not a known action")
    target = _safe_target(item.get("target"))
    start = _integer(item.get("started_at_total_minutes"), f"{label}.started_at_total_minutes")
    elapsed = _integer(item.get("elapsed_minutes"), f"{label}.elapsed_minutes")
    planned = _integer(item.get("planned_minutes"), f"{label}.planned_minutes", minimum=1)
    status = item.get("status")
    if status not in ACTION_STATUSES:
        raise TraceError(f"{label}.status is not a known running-action status")
    shown_elapsed = elapsed if progress_at is None else max(0, min(planned, progress_at - start))
    return {
        "action": action,
        "target": target,
        "status": status,
        "started_at_minute": start,
        "planned_minutes": planned,
        "elapsed_minutes": shown_elapsed,
        "progress": round(min(1.0, shown_elapsed / planned), 6),
    }


def _known_public_state(facts: dict[str, dict[str, str]]) -> dict[str, Any]:
    state: dict[str, Any] = {}
    alarm = _known_value(facts, "room.alarm")
    if alarm in {"ringing", "silent"}:
        state["alarm"] = alarm
    unread = _known_value(facts, "message.unread_count")
    if unread is not None:
        try:
            count = int(unread)
        except ValueError as exc:
            raise TraceError("known message.unread_count is not an integer") from exc
        if count < 0:
            raise TraceError("known message.unread_count cannot be negative")
        state["unread_messages"] = count
    task_status = _known_value(facts, "task.coursework.status")
    if task_status in {"active", "completed"}:
        state["coursework_status"] = task_status
    effort, target = (_known_value(facts, key) for key in (
        "task.coursework.effort", "task.coursework.effort_target"))
    if effort is not None and target is not None:
        try:
            effort_value, target_value = float(effort), float(target)
        except ValueError as exc:
            raise TraceError("known coursework progress facts must be numeric") from exc
        if not math.isfinite(effort_value) or not math.isfinite(target_value) or target_value <= 0:
            raise TraceError("known coursework progress facts are invalid")
        state["coursework_progress"] = round(max(0.0, min(1.0, effort_value / target_value)), 6)
    return state


def coursework_percentage(state: dict[str, Any]) -> float | None:
    progress = state.get("coursework_progress")
    if progress is None:
        return None
    if state.get("coursework_status") == "completed":
        return 100.0
    # A ratio at/near one does not establish task completion. Completion is
    # shown as 100% only when the actor has an explicit known O status.
    return min(99.9, math.floor(float(progress) * 1000) / 10)


def _cues(raw_deltas: Any, facts: dict[str, dict[str, str]],
          previous_state: dict[str, Any], current_state: dict[str, Any], minute: int) -> list[dict[str, Any]]:
    if not isinstance(raw_deltas, list):
        raise TraceError("boundary.observation_deltas must be an array")
    cues: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_deltas):
        delta = _object(raw, f"boundary.observation_deltas[{index}]")
        key, value, status = delta.get("key"), delta.get("value"), delta.get("status")
        if not all(isinstance(part, str) for part in (key, value, status)):
            raise TraceError(f"observation_deltas[{index}] needs string key/value/status")
        if status != "known" or key not in FACT_KEYS:
            continue
        if _known_value(facts, key) != value:
            continue
        if key == "room.alarm" and value in {"ringing", "silent"}:
            previous_alarm = previous_state.get("alarm")
            if (value == "ringing" and previous_alarm != "ringing") or (value == "silent" and previous_alarm == "ringing"):
                cues.append({"minute": minute, "text": "闹钟响了。" if value == "ringing" else "闹钟静音了。"})
        elif key == "message.unread_count":
            try:
                count = int(value)
            except ValueError as exc:
                raise TraceError("known unread-count delta is not an integer") from exc
            prior_count = previous_state.get("unread_messages")
            if count >= 0 and prior_count != count and (prior_count is not None or count > 0):
                cues.append({"minute": minute, "text": f"未读消息：{count} 条。"})
        elif key == "task.coursework.status" and value in {"active", "completed"}:
            prior_status = previous_state.get("coursework_status")
            if prior_status != value:
                cues.append({"minute": minute, "text": "课程任务已完成。" if value == "completed" else "课程任务状态：进行中。"})
        elif key == "task.coursework.effort":
            progress = current_state.get("coursework_progress")
            prior_progress = previous_state.get("coursework_progress")
            if progress is not None and progress != prior_progress:
                percentage = coursework_percentage(current_state)
                if percentage is not None:
                    cues.append({"minute": minute, "text": f"课程任务进度：{percentage:.1f}%。"})
    return cues


def export_trace(lines: list[str], clip_id: str = "clip-01") -> dict[str, Any]:
    if not re.fullmatch(r"clip-[A-Za-z0-9]{1,16}", clip_id):
        raise TraceError("clip id must match clip-<1 to 16 alphanumeric characters>")
    if not lines or len(lines) > MAX_RECORDS:
        raise TraceError("trace is empty or exceeds the boundary limit")
    try:
        records = [json.loads(line) for line in lines if line.strip()]
    except json.JSONDecodeError as exc:
        raise TraceError(f"invalid JSONL at line {exc.lineno}: {exc.msg}") from exc
    if len(records) < 3:
        raise TraceError("trace requires header, initial_state, and termination records")
    header = _object(records[0], "header")
    if header.get("kind") != "header" or header.get("protocol") != PROTOCOL:
        raise TraceError(f"expected {PROTOCOL} header")
    if header.get("policy") not in POLICIES or header.get("case") not in CASES:
        raise TraceError("unsupported paired-run policy or case")
    initial = _object(records[1], "initial_state")
    if initial.get("kind") != "initial_state":
        raise TraceError("second JSONL record must be initial_state")
    initial_minute = _integer(initial.get("minute"), "initial_state.minute")
    observation = _object(initial.get("observation"), "initial_state.observation")
    if _integer(observation.get("clock_total_minutes"), "initial_state.observation.clock_total_minutes") != initial_minute:
        raise TraceError("initial state minute and observation clock disagree")
    facts = _fact_map(observation.get("facts"), "initial_state.observation.facts")
    frames: list[dict[str, Any]] = [{
        "minute": initial_minute,
        "clock": _clock(initial_minute),
        "interval": None,
        "running_action": _running_action(initial.get("running_action"), "initial_state.running_action"),
        "visible_state": _known_public_state(facts),
        "cues": [],
    }]

    expected_index = 0
    last_minute = initial_minute
    terminated = False
    for record_number, raw_record in enumerate(records[2:], start=3):
        record = _object(raw_record, f"line {record_number}")
        kind = record.get("kind")
        if kind == "boundary":
            if terminated:
                raise TraceError("boundary found after termination")
            if _integer(record.get("index"), "boundary.index") != expected_index:
                raise TraceError("boundary indices must be contiguous and start at zero")
            interval = _object(record.get("interval"), "boundary.interval")
            start = _integer(interval.get("from_total_minutes"), "interval.from_total_minutes")
            end = _integer(interval.get("at_total_minutes"), "interval.at_total_minutes")
            elapsed = _integer(interval.get("elapsed_minutes"), "interval.elapsed_minutes")
            if interval.get("ownership") != "interval_before_boundary_then_events_at_at_total_minutes":
                raise TraceError("unsupported interval ownership contract")
            if start != last_minute or end < start or elapsed != end - start:
                raise TraceError("boundary interval is discontinuous or has inconsistent elapsed time")
            before_raw = record.get("running_before")
            before = _running_action(before_raw, "boundary.running_before")
            if before is not None and before["started_at_minute"] + before["elapsed_minutes"] != start:
                raise TraceError("running_before does not own the interval start")
            previous_state = _known_public_state(facts)
            after_facts = _fact_map(record.get("observation_facts"), "boundary.observation_facts")
            # Persistent facts that are absent from a delta remain part of O.
            facts.update(after_facts)
            current_state = _known_public_state(facts)
            cues = _cues(record.get("observation_deltas"), facts, previous_state, current_state, end)
            interval_action = None
            if before is not None:
                interval_action = dict(before)
                interval_action["elapsed_end_minutes"] = max(
                    interval_action["elapsed_minutes"],
                    min(interval_action["planned_minutes"], interval_action["elapsed_minutes"] + elapsed))
                interval_action["progress_end"] = round(
                    interval_action["elapsed_end_minutes"] / interval_action["planned_minutes"], 6)
            frames.append({
                "minute": end,
                "clock": _clock(end),
                "interval": {"from_minute": start, "to_minute": end, "running_action": interval_action},
                "running_action": _running_action(record.get("running_after"), "boundary.running_after"),
                "visible_state": current_state,
                "cues": cues,
            })
            expected_index += 1
            last_minute = end
        elif kind == "termination":
            if record_number != len(records) or terminated:
                raise TraceError("termination must be the final record")
            minute = _integer(record.get("minute"), "termination.minute")
            if minute != last_minute:
                raise TraceError("termination minute does not match the final boundary")
            terminated = True
        elif kind == "error":
            raise TraceError("cannot export a trace containing an error record")
        else:
            raise TraceError(f"unexpected record kind on line {record_number}")
    if not terminated:
        raise TraceError("trace has no final termination record")
    return {"clip_id": clip_id, "frames": frames}


def export_bundle(inputs: list[tuple[str, list[str]]]) -> dict[str, Any]:
    if not inputs:
        raise TraceError("at least one trace is required")
    clip_ids = [clip_id for clip_id, _ in inputs]
    if len(set(clip_ids)) != len(clip_ids):
        raise TraceError("clip ids must be unique")
    return {"clips": [export_trace(lines, clip_id) for clip_id, lines in inputs]}


def standalone_html(payload: dict[str, Any], template: str) -> str:
    if template.count("__PLAYER_SAFE_JSON__") != 1:
        raise TraceError("viewer template must contain exactly one player-data placeholder")
    safe_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    safe_json = safe_json.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    safe_json = safe_json.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return template.replace("__PLAYER_SAFE_JSON__", safe_json)


def write_outputs(payload: dict[str, Any], json_path: Path, html_path: Path | None = None) -> None:
    paths = [json_path] + ([html_path] if html_path else [])
    resolved_paths = [path.resolve() for path in paths]
    if len(set(resolved_paths)) != len(resolved_paths):
        raise TraceError("JSON and HTML output paths must be different")
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise TraceError("refusing to overwrite existing output: " + ", ".join(existing))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    html_text = None
    if html_path:
        template = Path(__file__).with_name("viewer.html").read_text(encoding="utf-8")
        html_text = standalone_html(payload, template)
        html_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("x", encoding="utf-8") as output_file:
        output_file.write(json_text)
    if html_path:
        with html_path.open("x", encoding="utf-8") as html_file:
            html_file.write(html_text or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, nargs="?", help="one paired harness JSONL trace")
    parser.add_argument("--clip", action="append", default=[], metavar="ID=TRACE",
                        help="add an anonymous clip (repeat for a multi-clip bundle)")
    parser.add_argument("--output", type=Path, required=True, help="player-safe JSON output")
    parser.add_argument("--html-output", type=Path, help="optional self-contained HTML viewer output")
    args = parser.parse_args()
    try:
        if args.trace and args.clip:
            raise TraceError("use either the positional trace or repeated --clip arguments")
        pairs: list[tuple[str, Path]] = []
        if args.trace:
            pairs = [("clip-01", args.trace)]
        else:
            for item in args.clip:
                clip_id, separator, trace_path = item.partition("=")
                if not separator or not trace_path:
                    raise TraceError("--clip must use ID=TRACE form")
                pairs.append((clip_id, Path(trace_path)))
        payload = export_bundle([
            (clip_id, trace_path.read_text(encoding="utf-8").splitlines())
            for clip_id, trace_path in pairs
        ])
        write_outputs(payload, args.output, args.html_output)
    except (OSError, TraceError) as exc:
        parser.error(str(exc))
    frame_count = sum(len(clip["frames"]) for clip in payload["clips"])
    print(f"Exported {len(payload['clips'])} anonymous clips / {frame_count} player-safe frames to {args.output}")
    if args.html_output:
        print(f"Wrote standalone viewer to {args.html_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
