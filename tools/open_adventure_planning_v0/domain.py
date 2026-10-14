"""Frozen finite STRIPS model for the Open Adventure B0 baseline.

This model predicts candidate actions only. The pinned native game is the
authority; callers may update a state only from completed visible feedback.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TypeAlias

Atom: TypeAlias = tuple[str, ...]
State: TypeAlias = frozenset[Atom]

ROOMS = (
    "START", "BUILDING", "VALLEY", "SLIT", "GRATE", "BELOWGRATE",
    "COBBLE", "DEBRIS", "AWKWARD", "BIRDCHAMBER", "PITTOP",
    "MISTHALL", "EASTBANK", "WESTBANK",
)
OBJECTS = ("keys", "lamp", "rod")
CARRIED = "CARRIED"
STATIC_MODEL_ASSUMPTION = "STATIC_MODEL_ASSUMPTION"
# The selected source locations without an unconditional LIT condition. This
# conservative policy makes the no-dark-travel subdomain explicit; it is not
# reported as a native game prohibition or a complete-map optimality claim.
DARK_ROOMS = frozenset({"DEBRIS", "AWKWARD", "BIRDCHAMBER", "PITTOP",
                        "MISTHALL", "EASTBANK", "WESTBANK"})
POLICY_SAFETY = "enter/remain in non-LIT rooms only while carrying the lit lamp"

# (source room, every vocabulary spelling for the source travel row, target)
# Destinations outside ROOMS and non-goto travel responses are deliberately
# omitted. This is a finite-domain model, not a complete map or shortest-path
# claim for the whole game.
MOVE_ROWS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("START", ("enter", "build", "house", "inwar", "insid", "in", "east", "e"), "BUILDING"),
    ("START", ("downs", "gully", "strea", "south", "s", "d", "downw", "down", "desce"), "VALLEY"),
    ("START", ("depre",), "GRATE"),
    ("BUILDING", ("out", "outsi", "exit", "leave", "outdo", "west", "w"), "START"),
    ("VALLEY", ("upstr", "build", "house", "north", "n"), "START"),
    ("VALLEY", ("downs", "south", "s", "d", "downw", "down", "desce"), "SLIT"),
    ("VALLEY", ("depre",), "GRATE"),
    ("SLIT", ("build", "house"), "START"),
    ("SLIT", ("upstr", "north", "n"), "VALLEY"),
    ("SLIT", ("downs", "bed", "south", "s", "depre"), "GRATE"),
    ("GRATE", ("build", "house"), "START"),
    ("GRATE", ("upstr", "gully", "north", "n"), "SLIT"),
    ("GRATE", ("enter", "inwar", "insid", "in", "d", "downw", "down", "desce"), "BELOWGRATE"),
    ("BELOWGRATE", ("out", "outsi", "exit", "leave", "upwar", "up", "u", "above", "ascen"), "GRATE"),
    ("BELOWGRATE", ("crawl", "cobbl", "inwar", "insid", "in", "west", "w"), "COBBLE"),
    ("BELOWGRATE", ("pit",), "PITTOP"),
    ("BELOWGRATE", ("debri",), "DEBRIS"),
    ("COBBLE", ("out", "outsi", "exit", "leave", "surfa", "east", "e"), "BELOWGRATE"),
    ("COBBLE", ("inwar", "insid", "in", "dark", "west", "w", "debri"), "DEBRIS"),
    ("COBBLE", ("pit",), "PITTOP"),
    ("DEBRIS", ("depre",), "GRATE"),
    ("DEBRIS", ("entra",), "BELOWGRATE"),
    ("DEBRIS", ("crawl", "cobbl", "passa", "tunne", "low", "east", "e"), "COBBLE"),
    ("DEBRIS", ("canyo", "inwar", "insid", "in", "upwar", "up", "u", "above", "ascen", "west", "w"), "AWKWARD"),
    ("DEBRIS", ("pit",), "PITTOP"),
    ("AWKWARD", ("depre",), "GRATE"),
    ("AWKWARD", ("entra",), "BELOWGRATE"),
    ("AWKWARD", ("d", "downw", "down", "desce", "east", "e", "debri"), "DEBRIS"),
    ("AWKWARD", ("inwar", "insid", "in", "upwar", "up", "u", "above", "ascen", "west", "w"), "BIRDCHAMBER"),
    ("AWKWARD", ("pit",), "PITTOP"),
    ("BIRDCHAMBER", ("depre",), "GRATE"),
    ("BIRDCHAMBER", ("entra",), "BELOWGRATE"),
    ("BIRDCHAMBER", ("debri",), "DEBRIS"),
    ("BIRDCHAMBER", ("canyo", "east", "e"), "AWKWARD"),
    ("BIRDCHAMBER", ("passa", "tunne", "pit", "west", "w"), "PITTOP"),
    ("PITTOP", ("depre",), "GRATE"),
    ("PITTOP", ("entra",), "BELOWGRATE"),
    ("PITTOP", ("debri",), "DEBRIS"),
    ("PITTOP", ("passa", "tunne", "east", "e"), "BIRDCHAMBER"),
    ("PITTOP", ("d", "downw", "down", "desce"), "MISTHALL"),
    ("MISTHALL", ("forwa", "conti", "onwar", "hall", "west", "w"), "EASTBANK"),
    ("MISTHALL", ("upwar", "up", "u", "above", "ascen"), "PITTOP"),
    ("EASTBANK", ("hall", "east", "e"), "MISTHALL"),
    ("EASTBANK", ("over",), "WESTBANK"),
    ("WESTBANK", ("over",), "EASTBANK"),
)

MOVE_SOURCE = "upstream/adventure.yaml:382-398,414-425,461-659,768-784"
ITEM_SOURCE = "upstream/actions.c:303-425,483,623-715; upstream/adventure.yaml:3277-3320"
LAMP_SOURCE = "upstream/actions.c:655-695,919-956; upstream/adventure.yaml:3285-3296"
GRATE_SOURCE = "upstream/actions.c:998-1049; upstream/adventure.yaml:488-524,3297-3309"
WAVE_SOURCE = "upstream/actions.c:1360-1400; upstream/adventure.yaml:641-659,768-784,3389-3402"


@dataclass(frozen=True)
class Operator:
    name: str
    args: tuple[str, ...]
    preconditions: tuple[Atom, ...]
    negative_preconditions: tuple[Atom, ...]
    add_effects: tuple[Atom, ...]
    delete_effects: tuple[Atom, ...]
    command: str
    source: str

    def applicable(self, state: State) -> bool:
        return all(p in state for p in self.preconditions) and not any(
            p in state for p in self.negative_preconditions
        )

    def apply(self, state: State) -> State:
        if not self.applicable(state):
            raise ValueError(f"operator {self.name}{self.args} is not applicable")
        return frozenset((set(state) - set(self.delete_effects)) | set(self.add_effects))


def ground_operators() -> tuple[Operator, ...]:
    """Ground all domain primitives once; no goal-specific operator filtering."""
    ops: list[Operator] = []
    for room, aliases, dest in MOVE_ROWS:
        for command in aliases:
            pre = [("at", "player", room)]
            add = [("at", "player", dest)]
            delete = [("at", "player", room)]
            if room == "GRATE" and dest == "BELOWGRATE":
                pre.append(("grate_open",))
            if room == "BELOWGRATE" and dest == "GRATE":
                pre.append(("grate_open",))
            if room in ("DEBRIS", "AWKWARD", "BIRDCHAMBER", "PITTOP") and dest == "GRATE":
                pre.append(("grate_open",))
            if room in DARK_ROOMS or dest in DARK_ROOMS:
                pre.extend((("lamp_on",), ("carrying", "lamp")))
            if (room, command, dest) in (("EASTBANK", "over", "WESTBANK"), ("WESTBANK", "over", "EASTBANK")):
                pre.append(("bridge",))
            ops.append(Operator("move", (room, command, dest), tuple(pre), (), tuple(add), tuple(delete), command, MOVE_SOURCE))

    for room, obj in product(ROOMS, OBJECTS):
        ops.append(Operator("take", (room, obj),
            (("at", "player", room), ("at", obj, room)), (("carrying", obj),),
            (("carrying", obj), ("at", obj, CARRIED)), (("at", obj, room),),
            f"take {obj}", ITEM_SOURCE))
        ops.append(Operator("drop", (room, obj),
            (("at", "player", room), ("carrying", obj)), (),
            (("at", obj, room),), (("carrying", obj), ("at", obj, CARRIED)),
            f"drop {obj}", ITEM_SOURCE))

    for room in ROOMS:
        for lamp_at in ((("carrying", "lamp"),), (("at", "lamp", room),)):
            ops.append(Operator("lamp_on", (room, *lamp_at[0]),
                (("at", "player", room), *lamp_at), (("lamp_on",),),
                (("lamp_on",),), (("lamp_off",),), "on lamp", LAMP_SOURCE))
            ops.append(Operator("lamp_off", (room, *lamp_at[0]),
                (("at", "player", room), *lamp_at, ("lamp_on",)), (),
                (("lamp_off",),), (("lamp_on",),), "off lamp", LAMP_SOURCE))

    for room in ("GRATE", "BELOWGRATE"):
        for key_here in ((("carrying", "keys"),), (("at", "keys", room),)):
            for action, present, absent in (("unlock", "grate_closed", "grate_open"),
                                            ("lock", "grate_open", "grate_closed")):
                ops.append(Operator(action, (room, *key_here[0]),
                    (("at", "player", room), *key_here, (present,)), (),
                    ((absent,),), ((present,),), f"{action} grate", GRATE_SOURCE))

    # The fissure can be toggled from either bank. Each direction is explicit,
    # so the planner cannot apply both contradictory effects to one state.
    for room in ("EASTBANK", "WESTBANK"):
        ops.append(Operator("wave_rod", (room, "unbridged"),
            (("at", "player", room), ("carrying", "rod"), ("unbridged",)), (),
            (("bridge",),), (("unbridged",),), "wave rod", WAVE_SOURCE))
        ops.append(Operator("wave_rod", (room, "bridge"),
            (("at", "player", room), ("carrying", "rod"), ("bridge",)), (),
            (("unbridged",),), (("bridge",),), "wave rod", WAVE_SOURCE))
    return tuple(ops)


OPERATORS = ground_operators()


def initial_state(*, player: str = "START", keys: str = "BUILDING",
                  lamp: str = "BUILDING", rod: str = "DEBRIS",
                  lamp_lit: bool = False, grate_open: bool = False,
                  bridge: bool = False) -> State:
    """Apply explicit shared static priors; never inspect live hidden state."""
    if player not in ROOMS or any(room not in ROOMS for room in (keys, lamp, rod)):
        raise ValueError("initial room outside frozen domain")
    facts: set[Atom] = {
        ("at", "player", player), ("at", "keys", keys),
        ("at", "lamp", lamp), ("at", "rod", rod),
        ("lamp_on",) if lamp_lit else ("lamp_off",),
        ("grate_open",) if grate_open else ("grate_closed",),
        ("bridge",) if bridge else ("unbridged",),
    }
    return frozenset(facts)


def has(state: State, predicate: str, *args: str) -> bool:
    return (predicate, *args) in state
