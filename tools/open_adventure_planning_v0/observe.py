"""Visible-text-only reconciliation for completed native responses."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .domain import Atom, CARRIED, State

ROOM_MARKERS = {
    "START": ("you're in front of building", "standing at the end of a road before a small brick building"),
    "BUILDING": ("you're inside building", "inside a building, a well house"),
    "VALLEY": ("you're in valley", "you are in a valley in the forest beside a stream"),
    "SLIT": ("you're at slit in streambed", "2-inch slit in the rock"),
    "GRATE": ("you're outside grate", "you are in a 20-foot depression floored with bare dirt"),
    "BELOWGRATE": ("you're below the grate", "small chamber beneath a 3x3 steel grate"),
    "COBBLE": ("you're in cobble crawl", "crawling over cobbles in a low passage"),
    "DEBRIS": ("you're in debris room", "debris room filled with stuff washed in from the surface"),
    "AWKWARD": ("awkward sloping east/west canyon",),
    "BIRDCHAMBER": ("you're in bird chamber", "splendid chamber thirty feet high"),
    "PITTOP": ("you're at top of small pit", "small pit breathing traces of white mist"),
    "MISTHALL": ("you're in hall of mists", "one end of a vast hall stretching forward"),
    "EASTBANK": ("you're on east bank of fissure", "east bank of a fissure slicing clear across the hall"),
    "WESTBANK": ("you're on west bank of fissure", "west side of the fissure in the hall of mists"),
}
INVENTORY_NAMES = {"keys": "set of keys", "lamp": "brass lantern", "rod": "black rod"}
UNMODELED_MARKERS = (
    "little dwarf", "dwarves", "knife", "you are dead", "you seem to have gotten yourself killed",
    "reincarnat", "death", "blinding flash", "cave is now closed",
)


@dataclass(frozen=True)
class Reconciliation:
    status: str
    state: State
    observed_room: str | None
    observed_inventory: frozenset[str] | None
    evidence: tuple[str, ...]
    reason: str | None = None


def parse_room(text: str) -> str | None:
    folded = text.casefold()
    matches = [room for room, markers in ROOM_MARKERS.items()
               if any(marker in folded for marker in markers)]
    return matches[0] if len(matches) == 1 else None


def parse_inventory(text: str) -> frozenset[str] | None:
    """Only parse item names after the native inventory heading."""
    match = re.search(r"you are currently holding the following:\s*(.*?)(?:\n\s*\n|\Z)",
                      text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        if "you're not carrying anything" in text.casefold():
            return frozenset()
        return None
    body = match.group(1).casefold()
    return frozenset(obj for obj, label in INVENTORY_NAMES.items() if label in body)


def _put_room(state: set[Atom], room: str) -> None:
    state.difference_update({atom for atom in state if atom[:2] == ("at", "player")})
    state.add(("at", "player", room))


def _set_inventory(state: set[Atom], carried: frozenset[str]) -> None:
    for obj in INVENTORY_NAMES:
        state.discard(("carrying", obj))
        state.discard(("at", obj, CARRIED))
        if obj in carried:
            state.add(("carrying", obj))
            state.add(("at", obj, CARRIED))
            state.difference_update({atom for atom in state
                                     if atom[:2] == ("at", obj) and atom[2] != CARRIED})


def reconcile(state: State, text: str, *, command: str | None = None,
              complete: bool = True) -> Reconciliation:
    """Update only facts with explicit evidence in a complete player-visible reply.

    Predicted operator effects are never an input to reconciliation.
    """
    if not complete:
        return Reconciliation("INCOMPLETE", state, None, None, (), "native_boundary_missing")
    folded = text.casefold()
    if any(marker in folded for marker in UNMODELED_MARKERS):
        return Reconciliation("UNMODELED_EVENT", state, None, None,
                              tuple(marker for marker in UNMODELED_MARKERS if marker in folded),
                              "death_or_unmodeled_npc_event")

    facts = set(state)
    evidence: list[str] = []
    room = parse_room(text)
    if room is not None:
        _put_room(facts, room)
        evidence.append(f"visible_room:{room}")

    inventory = parse_inventory(text)
    if inventory is not None:
        _set_inventory(facts, inventory)
        evidence.append("native_inventory_heading")

    if "your lamp is now on" in folded:
        facts.discard(("lamp_off",)); facts.add(("lamp_on",)); evidence.append("native_lamp_on")
    elif "your lamp is now off" in folded or "your lamp has run out of power" in folded:
        facts.discard(("lamp_on",)); facts.add(("lamp_off",)); evidence.append("native_lamp_off")
    if "the grate is now unlocked" in folded or "the grate is open" in folded:
        facts.discard(("grate_closed",)); facts.add(("grate_open",)); evidence.append("native_grate_open")
    elif "the grate is now locked" in folded or "the grate is locked" in folded:
        facts.discard(("grate_open",)); facts.add(("grate_closed",)); evidence.append("native_grate_closed")
    if "a crystal bridge now spans the fissure" in folded or "a crystal bridge spans the fissure" in folded:
        facts.discard(("unbridged",)); facts.add(("bridge",)); evidence.append("native_bridge_present")
    elif "the crystal bridge has vanished" in folded:
        facts.discard(("bridge",)); facts.add(("unbridged",)); evidence.append("native_bridge_absent")

    if command:
        command = command.casefold().strip()
        native_ok = bool(re.search(r"(?:^|\n)\s*ok\s*(?:\n|$)", text, re.IGNORECASE))
        if native_ok and command.startswith("take "):
            obj = command[5:].strip()
            if obj in INVENTORY_NAMES:
                _set_inventory(facts, frozenset({obj}) | frozenset(
                    o for o in INVENTORY_NAMES if ("carrying", o) in facts
                ))
                room_now = next((a[2] for a in facts if a[:2] == ("at", "player")), None)
                if room_now:
                    facts.discard(("at", obj, room_now))
                evidence.append(f"native_take_ok:{obj}")
        elif native_ok and command.startswith("drop "):
            obj = command[5:].strip()
            if obj in INVENTORY_NAMES:
                facts.discard(("carrying", obj)); facts.discard(("at", obj, CARRIED))
                room_now = next((a[2] for a in facts if a[:2] == ("at", "player")), None)
                if room_now:
                    facts.add(("at", obj, room_now))
                evidence.append(f"native_drop_ok:{obj}")

    return Reconciliation("RECONCILED" if evidence else "NO_NEW_EVIDENCE",
                          frozenset(facts), room, inventory, tuple(evidence))
