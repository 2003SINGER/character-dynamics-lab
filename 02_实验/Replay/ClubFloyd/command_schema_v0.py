"""Deterministic open-text command canonicalization for ClubFloyd Stage A.

This is a representation/evaluation schema, not a semantic admission oracle.
The raw command is always retained; normalization is versioned and reversible.
"""

from __future__ import annotations

import re
from typing import Any

VERBS = {
    "ask", "break", "close", "climb", "cross", "cut", "dig", "drink", "drop",
    "eat", "enter", "examine", "get", "give", "go", "help", "hit", "jump",
    "kill", "knock", "look", "open", "pick", "put", "pull", "push", "read",
    "remove", "save", "say", "search", "show", "sit", "stand", "take", "tell",
    "throw", "tie", "turn", "unlock", "use", "wait", "wear", "begin", "inventory",
}

# Stage-0b diagnostic family mapping.  This is deliberately separate from the
# reversible raw parse above: v0 remains immutable, while the family target
# collapses aliases and direction shorthands using the frozen command schema.
VERB_FAMILY_ALIASES = {
    "get": "take", "x": "examine", "i": "inventory", "inv": "inventory",
    "n": "navigation", "s": "navigation", "e": "navigation", "w": "navigation",
    "north": "navigation", "south": "navigation", "east": "navigation", "west": "navigation",
    "ne": "navigation", "nw": "navigation", "se": "navigation", "sw": "navigation",
    "up": "navigation", "down": "navigation",
}

def canonical_verb_family(raw: str) -> str:
    tokens = normalize_raw(raw).split()
    if not tokens:
        return "<EMPTY>"
    token = tokens[0]
    return VERB_FAMILY_ALIASES.get(token, token if token in VERBS else "<UNPARSED>")


def normalize_raw(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().casefold())


def canonicalize(raw: str, quality: str | None = None) -> dict[str, Any]:
    normalized = normalize_raw(raw)
    tokens = normalized.split()
    verb = tokens[0] if tokens and tokens[0] in VERBS else None
    rest = tokens[1:]
    modifier = None
    target = None
    if verb in {"ask", "tell", "give", "show"} and rest:
        for prep in ("about", "to", "with"):
            if prep in rest:
                idx = rest.index(prep)
                target = " ".join(rest[:idx]) or None
                modifier = " ".join(rest[idx + 1 :]) or None
                break
    if target is None and rest:
        target = " ".join(rest) or None
    status = "parsed" if verb else "unparsed"
    if quality in {"chat/commentary-like", "meta-command"}:
        status = "excluded_quality_class"
    return {
        "raw_command": raw,
        "normalized_command": normalized,
        "parse_confidence": 1.0 if status == "parsed" else 0.0,
        "verb": verb,
        "target": target,
        "modifier": modifier,
        "parse_status": status,
        "quality_class": quality,
    }
