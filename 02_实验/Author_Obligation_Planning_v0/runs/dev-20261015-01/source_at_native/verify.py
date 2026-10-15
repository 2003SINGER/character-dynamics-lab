"""Independent post-execution audit: raw game bytes, not predicted state.

The small event interpreter is deliberately separate from the search product.
It supports only the published finite diagnostic vocabulary.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.open_adventure_planning_v0.verify import (
    _complete, _raw_text, DEATH_MARKERS, DIRECTION_WORDS,
)
from tools.open_adventure_planning_v0.observe import ROOM_MARKERS


def _room(text):
    # Share only the frozen native vocabulary, not reconciliation/state logic.
    found = [room for room, markers in ROOM_MARKERS.items()
             if any(marker in text.casefold() for marker in markers)]
    return found[0] if len(found) == 1 else None


def verify_native(path: Path, task: dict) -> dict:
    try:
        rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    except (OSError, ValueError) as exc:
        return {"status": "UNKNOWN", "reason": f"unreadable:{type(exc).__name__}"}
    return inspect_rows(rows, task)


def inspect_rows(rows: list[dict], task: dict) -> dict:
    native = [r for r in rows if r.get("event") in {"initial_observation", "step"}]
    steps = [r for r in native if r.get("event") == "step"]
    closes = [r for r in rows if r.get("event") == "close"]
    sequence = [r.get("sequence") for r in steps]
    complete = (bool(native) and native[0].get("event") == "initial_observation"
                and sum(r.get("event") == "initial_observation" for r in native) == 1
                and sequence == list(range(1, len(steps) + 1))
                and all(_complete(r) and _raw_text(r) is not None for r in native))
    sealed = (len(closes) == 1 and closes[0].get("terminated") is True
              and closes[0].get("error") is None and bool(steps)
              and rows.index(closes[0]) > rows.index(steps[-1]))
    events: list[dict] = []
    current_room = None
    lamp = None
    bridge = None
    inventory = None
    room_sequence = None
    final_look = None
    final_inventory = None
    uncertain: list[dict] = []
    awaiting_hint = False

    for row in native:
        text = _raw_text(row)
        if text is None:
            continue
        folded = text.casefold()
        seq = row.get("sequence", 0)
        command = str(row.get("command", "")).casefold().strip()
        question_answer = awaiting_hint and command in {"n", "no", "y", "yes"}
        awaiting_hint = ("are you trying to get into the cave?" in folded
                         or "would you like a hint" in folded or "would you like help" in folded)
        for marker in DEATH_MARKERS:
            if marker in folded:
                events.append({"name": "player_death", "sequence": seq, "evidence": marker})
                break
        if not _complete(row):
            continue
        room = _room(text)
        previous = current_room
        if room:
            if room == "WESTBANK" and previous != "WESTBANK":
                events.append({"name": "arrive_west", "sequence": seq, "evidence": "native room"})
            if room == "EASTBANK" and previous == "WESTBANK":
                events.append({"name": "return_east", "sequence": seq, "evidence": "native room"})
            current_room, room_sequence = room, seq
        elif not question_answer and command.split(" ", 1)[0] in DIRECTION_WORDS:
            # A clear rejection keeps position. Other unrecognized movement
            # feedback cannot silently inherit a predicted destination.
            if not any(s in folded for s in ("can't go", "cannot go", "no way", "grate is locked")):
                current_room = None
                uncertain.append({"sequence": seq, "kind": "movement"})
        if command == "wave rod":
            if "a crystal bridge now spans the fissure" in folded:
                bridge = True
                events.append({"name": "create_bridge", "sequence": seq, "evidence": "native creation"})
            elif "the crystal bridge has vanished" in folded:
                bridge = False
                events.append({"name": "destroy_bridge", "sequence": seq, "evidence": "native destruction"})
            elif not any(s in folded for s in ("nothing happens", "aren't carrying", "are not carrying")):
                uncertain.append({"sequence": seq, "kind": "bridge"})
        if "your lamp is now on" in folded:
            lamp = True
        if "your lamp is now off" in folded or "your lamp has run out of power" in folded:
            lamp = False
        if command in {"look", "l"}:
            final_look = seq
            # Source-registered FISSURE descriptions (adventure.yaml): it is
            # listed in a lit bank look iff BRIDGED. Darkness is not absence.
            if room in {"EASTBANK", "WESTBANK"} and lamp is True:
                bridge = "a crystal bridge spans the fissure" in folded
            final_inventory = None
        elif command in {"inventory", "inven", "i"}:
            marker = "you are currently holding the following:"
            if marker in folded:
                body = folded.split(marker, 1)[1].split("\n\n", 1)[0]
                inventory = {name for name, label in (("keys", "set of keys"),
                             ("lamp", "brass lantern"), ("rod", "black rod")) if label in body}
                final_inventory = seq
            elif "you're not carrying anything" in folded:
                inventory, final_inventory = set(), seq
        elif row.get("event") == "step" and final_look is not None:
            final_look, final_inventory = None, None

    fresh = (complete and sealed and bool(steps) and final_look is not None
             and final_inventory == steps[-1].get("sequence") and final_look < final_inventory)
    facts = {}
    if current_room:
        facts[("at", "player", current_room)] = True
    if inventory is not None:
        for obj in ("keys", "lamp", "rod"):
            facts[("carrying", obj)] = obj in inventory
    if lamp is not None:
        facts[("lamp_on",)], facts[("lamp_off",)] = lamp, not lamp
    if bridge is not None:
        facts[("bridge",)], facts[("unbridged",)] = bridge, not bridge
    verdicts = {}
    for polarity, atoms in task["goal"].items():
        for atom_list in atoms:
            atom = tuple(atom_list)
            value = facts.get(atom)
            if atom[:2] == ("at", "player") and current_room is not None:
                value = atom[2] == current_room
            want = polarity == "required"
            verdicts[f"final:{polarity}:{'/'.join(atom)}"] = (
                "UNKNOWN" if not fresh or value is None else "PASS" if value == want else "FAIL")
    names = [event["name"] for event in events]
    for index, obligation in enumerate(task.get("obligations", [])):
        kind = obligation["type"]
        if kind == "eventually":
            ok = obligation["event"] in names
        elif kind == "never":
            ok = obligation["event"] not in names
        elif kind == "max_count":
            ok = names.count(obligation["event"]) <= obligation["maximum"]
        elif kind == "in_order":
            last = -1
            ok = True
            for wanted in obligation["events"]:
                match = next((e["sequence"] for e in events if e["name"] == wanted and e["sequence"] > last), None)
                if match is None:
                    ok = False
                    break
                last = match
        else:
            verdicts[f"history:{index}"] = "UNKNOWN"
            continue
        verdicts[f"history:{index}"] = "UNKNOWN" if not complete or not sealed or uncertain else "PASS" if ok else "FAIL"
    if task.get("always_no_death"):
        verdicts["always:no_death"] = ("FAIL" if "player_death" in names else
                                       "PASS" if complete and sealed else "UNKNOWN")
    values = set(verdicts.values())
    status = "FAIL" if "FAIL" in values else "UNKNOWN" if "UNKNOWN" in values else "PASS"
    return {"status": status, "obligations": verdicts, "events": events,
            "ledger_complete": complete, "sealed": sealed, "fresh_final_audit": fresh,
            "unknown_feedback": uncertain, "last_room": current_room,
            "room_witness_sequence": room_sequence, "inventory": sorted(inventory) if inventory is not None else None,
            "lamp_on": lamp, "bridge": bridge,
            "evidence_owner": "raw native receipts only; no planner/progress import"}
