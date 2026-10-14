"""Read native byte receipts, never planner state predictions.

Fixed E temporal semantics: bridge-created before first west arrival, final
west/keys/lamp/on and no death over the sealed interval. Marker extraction
reuses frozen independent-verifier helpers, not its final-bridge requirement.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.open_adventure_planning_v0.verify import (
    _raw_text, _complete, _room, _inventory, DEATH_MARKERS,
)


def inspect_rows(rows: list[dict], *, ended: bool) -> dict:
    allowed = {"reset_requested", "reset", "initial_observation", "step", "close", "close_source_check"}
    native = [r for r in rows if r.get("event") in {"initial_observation", "step"}]
    initials = [r for r in native if r.get("event") == "initial_observation"]
    steps = [r for r in native if r.get("event") == "step"]
    sequence_ok = ([r.get("sequence") for r in steps] == list(range(1, len(steps) + 1)))
    complete = (len(initials) == 1 and bool(native) and native[0] == initials[0]
                and all(r.get("event") in allowed for r in rows)
                and sequence_ok and all(_complete(r) and _raw_text(r) is not None for r in native))
    # A missing middle receipt, corrupt byte row or unclosed interval cannot
    # establish ALWAYS from absence of counter-evidence.
    close_rows = [r for r in rows if r.get("event") == "close"]
    sealed = (ended and len(close_rows) == 1 and close_rows[0].get("terminated") is True
              and close_rows[0].get("error") is None and bool(steps)
              and rows.index(close_rows[0]) > rows.index(steps[-1]))
    created, arrived, deaths = [], [], []
    lamp, lamp_sequence, last_look, last_inventory = None, None, None, None
    after_look_action = False
    for row in native:
        text = _raw_text(row)
        if text is None:
            continue
        folded = text.casefold()
        command = str(row.get("command", "")).strip().casefold()
        seq = row.get("sequence", 0)
        # A definite native death is a counterexample even if other rows are
        # missing; zero detected death with missing rows is only UNKNOWN.
        if row.get("event") == "step" and row.get("sent_bytes_b64") == row.get("intended_bytes_b64"):
            deaths.extend({"sequence": seq, "marker": marker} for marker in DEATH_MARKERS if marker in folded)
        if not _complete(row):
            continue
        if command == "wave rod" and "a crystal bridge now spans the fissure" in folded:
            created.append(seq)
        seen_room = _room(text)
        if seen_room == "WESTBANK":
            arrived.append(seq)
        if "your lamp is now on" in folded:
            lamp, lamp_sequence = True, seq
        elif "your lamp is now off" in folded or "your lamp has run out of power" in folded:
            lamp, lamp_sequence = False, seq
        if row.get("event") == "step":
            if command in {"look", "l"}:
                last_look = {"sequence": seq, "room": seen_room}
                last_inventory = None
                after_look_action = False
            elif command in {"inventory", "inven", "i"}:
                items = _inventory(text)
                last_inventory = {"sequence": seq, "items": sorted(items)} if items is not None else None
            elif last_look is not None:
                # Conservative: any non-audit input after look can stale its
                # location/object witness, not only our known action names.
                after_look_action = True
    fresh = (complete and sealed and last_look is not None and last_inventory is not None
             and last_look["sequence"] < last_inventory["sequence"]
             and last_inventory["sequence"] == steps[-1].get("sequence") and not after_look_action)
    event_status = "PASS" if complete and created else ("FAIL" if complete and sealed else "UNKNOWN" if not complete else "PENDING")
    if complete and created and arrived:
        order_status = "PASS" if created[0] < arrived[0] else "FAIL"
    elif complete and sealed:
        order_status = "FAIL"
    else:
        order_status = "UNKNOWN" if not complete else "PENDING"
    survival = ("FAIL" if deaths else "UNKNOWN" if not complete or (ended and not sealed)
                else "PASS" if sealed else "PENDING")
    final = {}
    for name, value in {
        "author-arrive-west": last_look is not None and last_look["room"] == "WESTBANK",
        "author-keys": last_inventory is not None and "keys" in last_inventory["items"],
        "author-lamp": last_inventory is not None and "lamp" in last_inventory["items"],
        "author-lamp-on": lamp,
    }.items():
        final[name] = ("PENDING" if not ended and complete else "UNKNOWN" if not fresh or value is None
                       else "PASS" if value else "FAIL")
    verdicts = {**final, "author-build-bridge": event_status,
                "author-build-before-arrival": order_status, "author-no-death": survival}
    values = set(verdicts.values())
    overall = ("FAIL" if "FAIL" in values else "UNKNOWN" if "UNKNOWN" in values
               else "PENDING" if "PENDING" in values else "PASS")
    return {"status": overall, "obligations": verdicts, "ledger_complete": complete,
            "sealed_interval": sealed, "sequence_contiguous": sequence_ok,
            "bridge_created_sequences": created, "west_arrival_sequences": arrived,
            "death_witnesses": deaths, "last_look": last_look, "last_inventory": last_inventory,
            "fresh_final_audit": fresh, "lamp_on_feedback": lamp,
            "lamp_feedback_sequence": lamp_sequence,
            "complete_native_sequences": [r.get("sequence", 0) for r in native] if complete else [],
            "source": "native committed output only; no predictions/hidden state",
            "event_source": "upstream/actions.c:1360-1400; adventure.yaml:3399-3402",
            "survival_scope": "observed sealed execution interval and registered native death markers, not future immunity"}


def inspect_ledger(path: Path, *, ended: bool) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        if any(not isinstance(r, dict) for r in rows):
            raise ValueError("non-object receipt")
        return inspect_rows(rows, ended=ended)
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "UNKNOWN", "reason": f"unreadable_native_ledger:{type(exc).__name__}"}
