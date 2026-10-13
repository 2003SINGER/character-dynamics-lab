"""Render a readable, evidence-linked replay without inventing a global order."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import argparse
import json
from pathlib import Path
from typing import Any


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def build_replay(trace: Mapping[str, Any]) -> str:
    station = trace.get("ongoing_station", {})
    station = station if isinstance(station, Mapping) else {}
    ledger = _rows(trace.get("ledger", []))
    actors = _rows(trace.get("actor_evidence", []))
    decisions = _rows(station.get("actor_goal_decisions", []))
    if not decisions:
        decisions = [entry for actor in actors for entry in _rows(actor.get("log", []))
                     if entry.get("kind") == "ongoing_station_decision"]

    # The sealed ledger has its own sequence. Preserve actor-log and receipt order
    # within each actor, but do not synthesize a total order across those streams.
    by_minute: dict[int, dict[str, list[tuple[int, Mapping[str, Any]]]]] = defaultdict(
        lambda: {"ledger": [], "decisions": [], "receipts": []})
    callback_event_ids: dict[tuple[int, str], str] = {}
    for index, event in enumerate(ledger):
        minute = event.get("minute")
        if type(minute) is not int:
            continue
        by_minute[minute]["ledger"].append((index, event))
        args = event.get("typed_args", {})
        if (event.get("event_type") == "P5_NPC_CALLBACK" and isinstance(args, Mapping)):
            alias = args.get("actor_alias") or args.get("role")
            if isinstance(alias, str):
                callback_event_ids[(minute, alias)] = str(event.get("event_id", "missing-event-id"))

    alias_by_id = {actor.get("actor_id"): actor.get("actor_alias") for actor in actors
                   if actor.get("actor_id") is not None}
    for actor_index, actor in enumerate(actors):
        alias = actor.get("actor_alias", actor.get("actor_id", f"actor-{actor_index}"))
        actor_id = actor.get("actor_id", "unknown")
        for log_index, entry in enumerate(_rows(actor.get("log", []))):
            if entry.get("kind") != "ongoing_station_decision":
                continue
            minute = entry.get("minute")
            if type(minute) is int:
                by_minute[minute]["decisions"].append(
                    (actor_index * 1_000_000 + log_index,
                     {**entry, "_source_path": f"actor_evidence[{actor_index}].log[{log_index}]"}))
        for receipt_index, receipt in enumerate(_rows(actor.get("native_receipts", []))):
            if receipt.get("settled") is not True:
                continue
            minute = receipt.get("sim_minute", receipt.get("minute"))
            if type(minute) is int:
                by_minute[minute]["receipts"].append(
                    (actor_index * 1_000_000 + receipt_index,
                     {**receipt, "_actor_alias": alias, "_actor_id": actor_id}))

    # Some exporters expose central decision rows without copying the actor logs.
    if decisions and not any(group["decisions"] for group in by_minute.values()):
        for index, decision in enumerate(decisions):
            minute = decision.get("minute")
            if type(minute) is int:
                by_minute[minute]["decisions"].append((index, decision))

    lines = ["# Ongoing Station — Native Run Replay", "",
             f"Scene: `{trace.get('scene_id', 'unknown')}` · "
             f"status: `{trace.get('run_status', 'unknown')}` · "
             f"sealed through: `{trace.get('complete_through', {})}`", "",
             "This is a derived replay. Sealed ledger rows are ordered by their recorded "
             "minute and sequence (with source-array order as a tie-breaker). Decisions "
             "and receipts retain their order within each actor-local source stream. "
             "The evidence does not provide a precise cross-stream sequence, so the "
             "sections below are not a claim of total ordering.", ""]
    if not by_minute:
        lines.append("No renderable sealed events, actor decisions, or settled receipts were present.")

    for minute in sorted(by_minute):
        group = by_minute[minute]
        lines.extend([f"## Minute {minute}", ""])
        # Keep time ticks, snapshots, and generic callback bookkeeping out of
        # the story body. They remain complete in the source ledger appendix.
        ledger_items = [(index, event) for index, event in group["ledger"]
                        if event.get("event_type") not in {
                            "TIME_ADVANCED", "P5_WORLD_SNAPSHOT", "P5_NPC_CALLBACK",
                            "P5_DIRECTOR_DECISION"}]
        if ledger_items:
            lines.extend(["### Sealed ledger (recorded sequence)", ""])
            ledger_items.sort(key=lambda pair: (
                pair[1].get("sequence") if type(pair[1].get("sequence")) is int else 2**63,
                pair[0]))
            for source_index, event in ledger_items:
                args = event.get("typed_args", {})
                args = args if isinstance(args, Mapping) else {}
                details = []
                for label, value in (("actor", args.get("actor_alias") or args.get("role")),
                                     ("operation", args.get("operation") or args.get("kind")),
                                     ("receipt", args.get("receipt_id"))):
                    if value is not None:
                        details.append(f"{label}=`{value}`")
                sequence = event.get("sequence", f"source-index-{source_index}")
                lines.append(f"- `{event.get('event_type', 'native_event')}` "
                             f"— event `{event.get('event_id', 'missing-event-id')}`, "
                             f"sequence `{sequence}`"
                             + (f"; {', '.join(details)}" if details else ""))
            lines.append("")

        if group["decisions"]:
            lines.extend(["### Actor-local decisions (source-log order)", ""])
            for source_index, decision in group["decisions"]:
                actor_id = decision.get("actor_id", "unknown")
                alias = decision.get("actor_alias", alias_by_id.get(actor_id, actor_id))
                commitment = decision.get("commitment")
                commitment = commitment if isinstance(commitment, Mapping) else {}
                goal = commitment.get("goal_id", decision.get("selected_goal", "unknown"))
                source = commitment.get("source", decision.get("source", "unknown source"))
                disposition = decision.get("disposition", "undocumented disposition")
                rationale = decision.get("rationale", "no rationale recorded")
                decision_id = decision.get("decision_id")
                ref = (f"decision_id=`{decision_id}`" if decision_id is not None else
                       f"source=`{decision.get('_source_path', f'ongoing_station.actor_goal_decisions[{source_index}]')}`")
                details = [f"{source} goal `{goal}` / `{disposition}`", ref, rationale]
                for key in ("commitment_id", "task_kind", "route_waypoints", "waypoint_receipts"):
                    if commitment.get(key) is not None:
                        details.append(f"{key}=`{commitment[key]}`")
                intent = decision.get("intent")
                if isinstance(intent, Mapping):
                    details.append(f"intent=`{intent.get('operator', intent.get('primitive', 'native'))}`")
                callback = callback_event_ids.get((minute, str(alias)))
                if callback:
                    details.append(f"callback_event=`{callback}`")
                lines.append(f"- NPC `{alias}`: " + "; ".join(details))
            lines.append("")

        if group["receipts"]:
            lines.extend(["### Settled native receipts (actor receipt-array order)", ""])
            for _, receipt in group["receipts"]:
                lines.append(f"- NPC `{receipt['_actor_alias']}`: "
                             f"`{receipt.get('kind', 'native action')}` receipt "
                             f"`{receipt.get('receipt_id', 'missing-receipt-id')}`; "
                             f"commitment `{receipt.get('ongoing_commitment_id', 'unlinked')}`")
            lines.append("")

    lines.extend(["## Complete sealed-ledger index", "",
                  "The following appendix preserves every ledger source ID in its recorded "
                  "sequence; routine ticks/callbacks are omitted from the story body only.", ""])
    all_ledger = []
    for index, event in enumerate(ledger):
        minute, sequence = event.get("minute"), event.get("sequence")
        if type(minute) is int:
            all_ledger.append((minute,
                               sequence if type(sequence) is int else 2**63 + index,
                               index, event))
    for minute, sequence, index, event in sorted(all_ledger, key=lambda row: row[:3]):
        lines.append(f"- minute `{minute}`, sequence `{event.get('sequence', f'source-index-{index}')}`: "
                     f"`{event.get('event_type', 'native_event')}` — "
                     f"`{event.get('event_id', 'missing-event-id')}`")
    if not all_ledger:
        lines.append("No sealed ledger rows were present.")

    lines.extend(["", "## Outcome boundary", "",
                  "A proposal is not an accepted commitment; an accepted commitment is not a settled action. "
                  "Only the native ledger, receipt, and independent database readback establish physical effects."])
    return "\n".join(lines) + "\n"


def write_replay_once(path: Path, trace: Mapping[str, Any], *, correction_note: str | None = None) -> None:
    """Persist readable Markdown with exclusive creation; preserve evidence artifacts."""
    text = build_replay(trace)
    if correction_note:
        text = (f"> {correction_note}\n> This is a derived rendering; the original trace and replay are unchanged.\n\n"
                + text)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an existing native trace as readable Markdown.")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--correction-note")
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    if not isinstance(trace, Mapping):
        raise ValueError("trace root must be a JSON object")
    write_replay_once(args.output, trace, correction_note=args.correction_note)
    print(f"wrote derived replay: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
