"""Independent goal verifier. Depends only on the raw native event ledger."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any


# Kept local to make the verifier independent of search and reconciliation.
ROOM_MARKERS = {
    "START": ("you're in front of building",),
    "BUILDING": ("you're inside building",),
    "VALLEY": ("you're in valley",),
    "SLIT": ("you're at slit in streambed",),
    "GRATE": ("you're outside grate",),
    "BELOWGRATE": ("you're below the grate", "small chamber beneath a 3x3 steel grate"),
    "COBBLE": ("you're in cobble crawl",),
    "DEBRIS": ("you're in debris room",),
    "AWKWARD": ("awkward sloping east/west canyon",),
    "BIRDCHAMBER": ("you're in bird chamber",),
    "PITTOP": ("you're at top of small pit",),
    "MISTHALL": ("you're in hall of mists",),
    "EASTBANK": ("you're on east bank of fissure",),
    "WESTBANK": ("you're on west bank of fissure", "west side of the fissure in the hall of mists"),
}
DEATH_MARKERS = (
    "oh dear, you seem to have gotten yourself killed",
    "you clumsy oaf, you've done it again", "you clumsy oaf, you’ve done it again",
    "now you've really done it! i'm out of orange smoke",
    "now you’ve really done it! i’m out of orange smoke",
    "fell into a pit", "broke every bone", "broken neck", "looks as though you're dead",
    "looks as though you’re dead", "reincarnat", "gotten yourself killed",
)
STATE_CHANGING_COMMANDS = (
    "take ", "get ", "drop ", "release ", "on ", "light ", "off ", "extinguish ",
    "lock ", "unlock ", "open ", "wave ", "shake ", "swing ",
)
DIRECTION_WORDS = {
    "road", "hill", "enter", "build", "house", "in", "inwar", "insid", "east", "e",
    "downs", "gully", "strea", "south", "s", "d", "downw", "down", "desce",
    "north", "n", "upstr", "west", "w", "depre", "out", "outsi", "exit", "leave",
    "outdo", "crawl", "cobbl", "surface", "surfa", "dark", "pit", "debri", "entra",
    "passa", "tunne", "low", "canyo", "upwar", "up", "u", "above", "ascen",
    "forward", "forwa", "conti", "onwar", "hall", "over",
}


def _raw_text(row: dict[str, Any]) -> str | None:
    key = "raw_b64" if row.get("event") == "initial_observation" else "raw_output_b64"
    encoded = row.get(key)
    if not isinstance(encoded, str):
        return None
    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8", errors="strict")
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def _complete(row: dict[str, Any]) -> bool:
    if row.get("event") == "initial_observation":
        return (row.get("complete") is True and row.get("input_boundary_reached") is True
                and row.get("timed_out") is False and row.get("error") is None)
    if row.get("event") != "step":
        return False
    return (row.get("input_boundary_reached") is True
            and row.get("timed_out") is False and row.get("error") is None
            and row.get("sent_bytes_b64") == row.get("intended_bytes_b64"))


def _room(text: str) -> str | None:
    folded = text.casefold()
    found = [room for room, markers in ROOM_MARKERS.items()
             if any(marker in folded for marker in markers)]
    return found[0] if len(found) == 1 else None


def _inventory(text: str) -> frozenset[str] | None:
    folded = text.casefold()
    marker = "you are currently holding the following:"
    if marker not in folded:
        if "you're not carrying anything" in folded:
            return frozenset()
        return None
    body = folded.split(marker, 1)[1].split("\n\n", 1)[0]
    return frozenset(item for item, label in (
        ("keys", "set of keys"), ("lamp", "brass lantern")) if label in body)


def verify_ledger(path: Path, goal_id: str) -> dict[str, Any]:
    """Verify D/E from complete native outputs; G is unsupported by design."""
    if goal_id == "G":
        return {"status": "UNSUPPORTED_SEMANTICS",
                "evidence": "No registered trust state, help attribution, or later trust-consumption mechanism."}
    if goal_id not in ("D", "E"):
        raise ValueError("goal_id must be D, E, or G")
    rows: list[dict[str, Any]] = []
    try:
        with Path(path).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if isinstance(row, dict) and row.get("event") in ("initial_observation", "step"):
                    rows.append(row)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "INDETERMINATE", "reason": f"ledger_unreadable:{type(exc).__name__}"}
    if not rows:
        return {"status": "INDETERMINATE", "reason": "empty_native_ledger"}

    # A latest malformed, partial, timed-out, or errored row cannot be skipped
    # to recover a success from an earlier prefix.
    incomplete = any(not _complete(row) or _raw_text(row) is None for row in rows)
    if incomplete:
        return {"status": "INDETERMINATE", "reason": "latest_or_prior_native_observation_incomplete"}
    observations = [(row, _raw_text(row)) for row in rows]
    texts = [(row, text) for row, text in observations if text is not None]
    joined = "\n".join(text for _, text in texts).casefold()
    death = next((phrase for phrase in DEATH_MARKERS if phrase in joined), None)
    if death:
        return {"status": "FAIL", "reason": "native_death_or_reincarnation", "evidence": death}

    latest_room = None
    latest_room_index = None
    latest_inventory = None
    latest_inventory_index = None
    lamp_state = None
    bridge_seen = False
    bridge_absent_after = False
    latest_look_index = None
    latest_look_room = None
    latest_look_bridge = False
    last_native_index = len(texts) - 1
    post_final_audit_change_index = None
    for index, (row, text) in enumerate(texts):
        folded = text.casefold()
        command = str(row.get("command", "")).casefold().strip() if row.get("event") == "step" else ""
        seen_room = _room(text)
        if seen_room is not None:
            latest_room = seen_room
            latest_room_index = index
        items = _inventory(text)
        if items is not None:
            latest_inventory = items
            latest_inventory_index = index
        if "your lamp is now on" in folded:
            lamp_state = "on"
        elif "your lamp is now off" in folded or "your lamp has run out of power" in folded:
            lamp_state = "off"
        if "a crystal bridge now spans the fissure" in folded or "a crystal bridge spans the fissure" in folded:
            bridge_seen, bridge_absent_after = True, False
        elif "the crystal bridge has vanished" in folded:
            bridge_absent_after = True
        if command in ("look", "l"):
            latest_look_index = index
            latest_look_room = seen_room
            latest_look_bridge = ("a crystal bridge spans the fissure" in folded
                                  or "a crystal bridge now spans the fissure" in folded)
        elif latest_look_index is not None:
            if command.startswith(STATE_CHANGING_COMMANDS) or command.split(" ", 1)[0] in DIRECTION_WORDS:
                post_final_audit_change_index = index

    target_room = "BELOWGRATE" if goal_id == "D" else "WESTBANK"
    final_evidence_fresh = (
        latest_look_index is not None and latest_inventory_index is not None
        and latest_look_index < latest_inventory_index
        and latest_room_index is not None and latest_room_index >= latest_look_index
        and latest_look_room == target_room
        and (post_final_audit_change_index is None or post_final_audit_change_index < latest_look_index)
        and last_native_index == latest_inventory_index
    )
    facts = {
        "final_look_room": latest_look_room,
        "latest_room": latest_room,
        "latest_inventory_keys": latest_inventory is not None and "keys" in latest_inventory,
        "latest_inventory_lamp": latest_inventory is not None and "lamp" in latest_inventory,
        "lamp_on": lamp_state == "on",
        "bridge_seen_in_ledger": bridge_seen and not bridge_absent_after if goal_id == "E" else None,
        "bridge_seen_in_final_look": latest_look_bridge if goal_id == "E" else None,
        "death_observed": False,
        "fresh_final_look_then_inventory": final_evidence_fresh,
    }
    passed = (final_evidence_fresh and latest_room == target_room
              and facts["latest_inventory_keys"] and facts["latest_inventory_lamp"]
              and facts["lamp_on"])
    if goal_id == "E":
        passed = (passed and facts["bridge_seen_in_ledger"]
                  and facts["bridge_seen_in_final_look"])
    if passed:
        return {"status": "PASS", "facts": facts, "source": "complete native output ledger"}
    return {"status": "FAIL" if final_evidence_fresh else "INDETERMINATE",
            "facts": facts, "source": "complete native output ledger"}
