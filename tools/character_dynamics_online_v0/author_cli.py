"""Small append-only operator CLI for live author goals in a process run.

This is an agent-operated interface, not a human-participant instrument. It
reads the latest controller decision plus the newest available native actor
views, validates against the current checkpoint, and only appends to an
already-created author-input JSONL stream.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from .contracts import ContractError, finite_number, json_safe, nonempty, uid
from .process_controller import _validate_command


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        line_number = 0
        while True:
            line = stream.readline()
            if line == "":
                break
            line_number += 1
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # The runner may be appending this exact last line now. Ignore
                # only an unterminated final record; malformed newline-ended
                # records remain an error rather than being silently hidden.
                if not line.endswith("\n"):
                    break
                raise ContractError(f"invalid JSONL at {path.name}:{line_number}")
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _latest_session(checkpoints: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(checkpoints):
        session = row.get("session")
        if isinstance(session, dict) and session.get("schema") == "character_dynamics_online_process_v0":
            return session
    return None


def _actor_views(run_dir: Path, status_rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    views: dict[int, dict[str, Any]] = {}
    # Current G1 ActorViews are written to g1-events.jsonl. Also inspect the
    # native event stream for runners that mirror them there, then retain only
    # the freshest row per actor across both sources and the startup baseline.
    for event_file in ("native-events.jsonl", "g1-events.jsonl"):
        for row in _read_jsonl(run_dir / event_file):
            if row.get("event") == "g1_actor_view" and type(row.get("actor_uid")) is int:
                previous = views.get(row["actor_uid"])
                if previous is None or float(row.get("time", -1)) >= float(previous.get("time", -1)):
                    views[row["actor_uid"]] = row
    # The native view is also pinned in the runner's startup observation.
    for status in status_rows:
        actor_views = status.get("actor_views")
        if status.get("event") != "pre_request_loaded_native_baseline" or not isinstance(actor_views, Mapping):
            continue
        for key, view in actor_views.items():
            if isinstance(view, Mapping) and type(view.get("actor_uid")) is int:
                actor_uid = view["actor_uid"]
                previous = views.get(actor_uid)
                if previous is None or float(view.get("time", -1)) >= float(previous.get("time", -1)):
                    views[actor_uid] = dict(view)
    return views


def read_run_snapshot(run_dir: Path, author_input_path: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        raise ContractError(f"run directory does not exist: {run_dir}")
    checkpoints = _read_jsonl(run_dir / "session-checkpoints.jsonl")
    decisions = [row for row in _read_jsonl(run_dir / "decisions.jsonl")
                 if row.get("event") == "controller_decision" and isinstance(row.get("decision"), dict)]
    status_rows = _read_jsonl(run_dir / "status.jsonl")
    session = _latest_session(checkpoints)
    views = _actor_views(run_dir, status_rows)
    latest_decision = None
    latest_observations = {}
    if decisions:
        last_row = decisions[-1]
        latest_decision = dict(last_row["decision"])
        if finite_number(last_row.get("game_time")):
            latest_decision["game_time"] = float(last_row["game_time"])
        actor_times = last_row.get("actor_view_times", latest_decision.get("actor_view_times", {}))
        if isinstance(actor_times, Mapping):
            latest_observations = {str(key): value for key, value in actor_times.items()
                                   if finite_number(value)}
    if not latest_observations:
        latest_observations = {str(actor_uid): view.get("time") for actor_uid, view in views.items()
                               if finite_number(view.get("time"))}
    known_markers: dict[str, dict[str, Any]] = {}
    for view in views.values():
        markers = view.get("markers", [])
        if isinstance(markers, list):
            for marker in markers:
                if isinstance(marker, dict) and isinstance(marker.get("marker_id"), str):
                    known_markers[marker["marker_id"]] = {
                        "label": marker.get("label"), "kind": marker.get("kind")}
    follower_uids: set[int] = set()
    for view in views.values():
        nearby = view.get("nearby", [])
        if isinstance(nearby, list):
            for peer in nearby:
                if isinstance(peer, Mapping) and type(peer.get("uid")) is int:
                    follower_uids.add(peer["uid"])
    for row in status_rows:
        follower = row.get("native_follower_uid")
        if type(follower) is int and follower >= 0:
            follower_uids.add(follower)
    started = any(row.get("event") == "process_started" for row in status_rows)
    ended = any(row.get("event") == "process_end" for row in status_rows)
    latest_game_time = None
    if latest_decision is not None and finite_number(latest_decision.get("game_time")):
        latest_game_time = float(latest_decision["game_time"])
    elif latest_observations:
        # Before the first controller decision, present the native observation
        # time as observation-only, not as evidence of a running decision loop.
        values = [float(value) for value in latest_observations.values() if finite_number(value)]
        latest_game_time = max(values) if values else None
    author_rows = _read_jsonl(run_dir / "author-versions.jsonl")
    recent_history = []
    if session is not None:
        recent_history = json_safe(session.get("native_history", [])[-20:])
    if decisions:
        # Session snapshots are intentionally sparse (terminal/version
        # checkpoints). For live display, use the latest controller decision
        # as authority for current plans and obligation verdicts rather than
        # presenting checkpoint plan state as if it were current.
        for row in decisions[-10:]:
            feedback_rows = row["decision"].get("feedback_applied", [])
            if isinstance(feedback_rows, list):
                recent_history.extend(json_safe(feedback_rows))
        recent_history = recent_history[-30:]
    display_obligations = (
        latest_decision.get("author_obligations")
        if isinstance(latest_decision, Mapping) and isinstance(latest_decision.get("author_obligations"), list)
        else (session.get("author_obligations", {}) if session else {}))
    display_plans = (
        latest_decision.get("plans")
        if isinstance(latest_decision, Mapping) and isinstance(latest_decision.get("plans"), list)
        else (session.get("plans", {}) if session else {}))
    return {
        "run_dir": str(run_dir),
        "run_state": "NOT_STARTED" if not started else ("ENDED" if ended else "RUNNING"),
        "has_controller_decision": latest_decision is not None,
        "latest_game_time": latest_game_time,
        "latest_observation_times": latest_observations,
        "session": session,
        "display_author_obligations": display_obligations,
        "display_plans": display_plans,
        "actor_views": views,
        "known_markers": known_markers,
        "known_follower_uids": sorted(follower_uids),
        "author_input_path": str(author_input_path.expanduser().resolve()
                                   if author_input_path is not None
                                   else run_dir / "author-input.jsonl"),
        "author_input_exists": ((author_input_path.expanduser().resolve()
                                  if author_input_path is not None
                                  else run_dir / "author-input.jsonl").is_file()),
        "author_versions": author_rows[-30:],
        "recent_native_history": recent_history,
        "latest_decision": latest_decision,
        "latest_decisions": [
            {**row["decision"], **({"game_time": float(row["game_time"])}
                                   if finite_number(row.get("game_time")) else {})}
            for row in decisions[-10:]],
    }


def _goal_version(session: Mapping[str, Any], goal_id: str, op: str) -> int:
    existing = session.get("author_obligations", {}).get(goal_id)
    if op == "append":
        if existing is not None:
            raise ContractError("append cannot replace an existing goal_id; use edit")
        return 1
    if existing is None:
        raise ContractError("edit requires an existing goal_id in the live checkpoint")
    return int(existing["versions"][-1]["version"]) + 1


def _resolve_marker(token: str, known: Mapping[str, Any]) -> str:
    folded = token.casefold()
    if token in known:
        return token
    shorthand = {"a": "a", "markera": "a", "marker-a": "a",
                 "b": "b", "markerb": "b", "marker-b": "b"}.get(folded)
    if shorthand is not None:
        matches = [marker_id for marker_id, metadata in known.items()
                   if str(metadata.get("label", "")).casefold() == shorthand.upper().casefold()
                   or marker_id.casefold().endswith("_" + shorthand)
                   or marker_id.casefold().endswith("-" + shorthand)]
        if len(matches) == 1:
            return matches[0]
    raise ContractError(f"marker {token!r} is not uniquely present in current native observations")


def build_rally_command(snapshot: Mapping[str, Any], *, op: str, goal_id: str,
                        actor_uid: int, marker: str, follower_uid: int,
                        deadline: float) -> dict[str, Any]:
    session = snapshot.get("session")
    if not isinstance(session, Mapping):
        raise ContractError("no session checkpoint is available; wait for the live runner")
    if snapshot.get("run_state") != "RUNNING":
        raise ContractError("rally command requires a currently running process")
    if not snapshot.get("has_controller_decision"):
        raise ContractError("no live controller decision/observation has been recorded yet")
    if not snapshot.get("author_input_exists"):
        raise ContractError("author-input.jsonl was not created by the runner; refusing to create a new stream")
    actor_uid = uid(actor_uid, "actor_uid")
    if actor_uid not in session.get("actor_uids", []):
        raise ContractError("actor_uid must belong to the live process configuration")
    follower_uid = uid(follower_uid, "follower_uid")
    if follower_uid not in snapshot.get("known_follower_uids", []):
        raise ContractError("follower_uid is not present in current native observations/configuration")
    marker_id = _resolve_marker(marker, snapshot.get("known_markers", {}))
    if not finite_number(deadline) or deadline < 0:
        raise ContractError("deadline must be an absolute non-negative game time")
    command = {
        "op": op, "goal_id": nonempty(goal_id, "goal_id"),
        "version": _goal_version(session, goal_id, op), "actor_uid": actor_uid,
        "ast": {"op": "deadline", "event": {"event": "g1_rally_completed",
                "args": [actor_uid, marker_id, follower_uid]}, "at": float(deadline)},
    }
    return _validate_command(command, session)


def validate_raw_command(snapshot: Mapping[str, Any], command: object) -> dict[str, Any]:
    session = snapshot.get("session")
    if not isinstance(session, Mapping):
        raise ContractError("no session checkpoint is available; wait for the live runner")
    if snapshot.get("run_state") != "RUNNING" or not snapshot.get("has_controller_decision"):
        raise ContractError("raw author command requires a running process with a live decision")
    if not snapshot.get("author_input_exists"):
        raise ContractError("author-input.jsonl was not created by the runner; refusing to create a new stream")
    clean = _validate_command(command, session)
    if clean["actor_uid"] not in session.get("actor_uids", []):
        raise ContractError("actor_uid must belong to the live process configuration")
    # Event/state references must only use live-known markers and identities.
    ast = clean["ast"]
    def check(node: Mapping[str, Any]) -> None:
        if node["op"] in ("and", "or"):
            for child in node["children"]:
                check(child)
        elif node["op"] == "deadline":
            event = node["event"]
            if event["event"] == "g1_rally_completed":
                args = event.get("args", [])
                if len(args) != 3 or args[0] != clean["actor_uid"]:
                    raise ContractError("rally event must identify this command's actor and [actor, marker, follower]")
                _resolve_marker(str(args[1]), snapshot.get("known_markers", {}))
                if type(args[2]) is not int or args[2] not in snapshot.get("known_follower_uids", []):
                    raise ContractError("rally event follower is not currently observed/configured")
        elif node["op"] == "event_before":
            for event in (node["first"], node["second"]):
                if event["event"] == "g1_rally_completed":
                    args = event.get("args", [])
                    if len(args) != 3 or args[0] != clean["actor_uid"]:
                        raise ContractError("rally order selector must bind to the command actor")
                    _resolve_marker(str(args[1]), snapshot.get("known_markers", {}))
                    if type(args[2]) is not int or args[2] not in snapshot.get("known_follower_uids", []):
                        raise ContractError("rally order follower is not currently observed/configured")
    check(ast)
    return clean


def append_author_command(run_dir: Path, command: Mapping[str, Any], *,
                          input_path: Path | None = None,
                          local_time: str | None = None) -> dict[str, Any]:
    run_dir = run_dir.expanduser().resolve()
    path = (input_path.expanduser().resolve() if input_path is not None
            else run_dir / "author-input.jsonl")
    if not path.is_file() or path.is_symlink():
        raise ContractError("author-input.jsonl must already exist as a regular runner-created file")
    issued_at = command.get("_issued_at_game_time")
    if not finite_number(issued_at) or issued_at < 0:
        raise ContractError("operator command needs the latest observed absolute game time")
    # `_validate_command` returns an internal normalized form that includes
    # source=AUTHOR. The runner's external JSONL contract deliberately accepts
    # only the five author-command fields; provenance belongs to the envelope.
    command_fields = ("op", "goal_id", "version", "actor_uid", "ast")
    if any(key not in command for key in command_fields):
        raise ContractError("operator command is missing required author-command fields")
    wire_command = {key: command[key] for key in command_fields}
    row = {"source": "AGENT_OPERATOR", "operator_kind": "agent",
           "command": json_safe(wire_command),
           "issued_at_game_time": float(issued_at),
           "issued_local_time": local_time or datetime.now().astimezone().isoformat(timespec="milliseconds")}
    encoded = (json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        with os.fdopen(descriptor, "ab", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    return row


def _display_snapshot(snapshot: Mapping[str, Any], section: str = "summary") -> dict[str, Any]:
    session = snapshot.get("session")
    decision = snapshot.get("latest_decision") or {}
    summary = {
        "run_dir": snapshot["run_dir"], "run_state": snapshot["run_state"],
        "has_controller_decision": snapshot["has_controller_decision"],
        "latest_game_time": snapshot["latest_game_time"],
        "latest_observation_times": snapshot["latest_observation_times"],
        "known_markers": snapshot["known_markers"],
        "known_follower_uids": snapshot["known_follower_uids"],
        "inflight_by_actor": session.get("inflight_by_actor", {}) if session else {},
        "current_requests": [{key: row.get(key) for key in
                              ("request_id", "actor_uid", "primitive", "args", "source", "goal_id", "author_version")}
                             for row in decision.get("requests", []) if isinstance(row, Mapping)],
        "blocked": decision.get("blocked", []),
    }
    goals = {
        "actor_goals": session.get("actor_goal_specs", []) if session else [],
        "author_goals": snapshot["display_author_obligations"],
    }
    plans = {"plans": snapshot["display_plans"]}
    history = {
        "recent_native_history": snapshot["recent_native_history"],
        "author_versions": snapshot["author_versions"],
        "recent_decisions": [{
            "sequence": row.get("sequence"), "game_time": row.get("game_time"),
            "author_commands_applied": row.get("author_commands_applied", []),
            "feedback_applied": row.get("feedback_applied", []),
            "requests": [{key: request.get(key) for key in
                          ("request_id", "actor_uid", "primitive", "args", "source", "goal_id", "author_version")}
                         for request in row.get("requests", []) if isinstance(request, Mapping)],
            "blocked": row.get("blocked", []),
        } for row in snapshot["latest_decisions"]],
    }
    sections = {"summary": summary, "goals": goals, "plans": plans, "history": history}
    if section == "all":
        return {key: value for part in sections.values() for key, value in part.items()}
    return sections[section]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--author-input", type=Path,
                        help="optional existing external JSONL stream also passed to process_runner")
    sub = parser.add_subparsers(dest="operation", required=True)
    show = sub.add_parser("show", help="show latest run state, goals, plans, and history")
    show.add_argument("--section", choices=("summary", "goals", "plans", "history", "all"),
                      default="summary")
    show.add_argument("--compact", action="store_true")
    raw = sub.add_parser("raw", help="append a complete validated author command as JSON")
    raw.add_argument("--command", required=True,
                     help="complete JSON object with op, goal_id, version, actor_uid, ast")
    for op, alias in (("append-rally", "append-meet"), ("edit-rally", "edit-meet")):
        rally = sub.add_parser(op, aliases=[alias],
                               help="append/edit one deadline-bound rally marker goal")
        rally.add_argument("--goal-id", required=True)
        rally.add_argument("--actor-uid", required=True, type=int)
        rally.add_argument("--marker", required=True, help="current observed marker ID or A/B shorthand")
        rally.add_argument("--follower-uid", required=True, type=int)
        rally.add_argument("--deadline", required=True, type=float,
                           help="absolute game-time deadline; never reset relative to now")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        snapshot = read_run_snapshot(args.run_dir, args.author_input)
        if args.operation == "show":
            output = _display_snapshot(snapshot, args.section)
            print(json.dumps(output, indent=None if args.compact else 2, ensure_ascii=False, sort_keys=True))
            return 0
        if args.operation == "raw":
            try:
                raw = json.loads(args.command)
            except json.JSONDecodeError as exc:
                raise ContractError(f"--command is not valid JSON: {exc.msg}") from exc
            command = validate_raw_command(snapshot, raw)
        else:
            command = build_rally_command(
                snapshot, op="append" if args.operation in ("append-rally", "append-meet") else "edit",
                goal_id=args.goal_id, actor_uid=args.actor_uid, marker=args.marker,
                follower_uid=args.follower_uid, deadline=args.deadline)
        decision = snapshot.get("latest_decision")
        if not isinstance(decision, Mapping) or not finite_number(decision.get("game_time")):
            raise ContractError("latest controller decision has no absolute game_time")
        command = {**command, "_issued_at_game_time": float(decision["game_time"])}
        row = append_author_command(args.run_dir, command, input_path=args.author_input)
        print(json.dumps({"appended": True, "source": row["source"],
                          "operator_kind": row["operator_kind"],
                          "issued_at_game_time": row["issued_at_game_time"],
                          "issued_local_time": row["issued_local_time"],
                          "command": row["command"]}, ensure_ascii=False, indent=2))
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(f"author-cli: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
