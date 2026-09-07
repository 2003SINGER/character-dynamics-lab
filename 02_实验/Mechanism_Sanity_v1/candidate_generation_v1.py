"""Dataset-neutral SceneSnapshot -> affordance -> generated A^O.

The generator deliberately accepts only a canonical snapshot projection.  In
particular, ``source_candidates`` and the recorded action are not read here;
they are labels/diagnostics for a later support check.  Missing object facts
never get promoted to portability, ownership, or success preconditions.
"""
from __future__ import annotations

import re
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
ARTICLES = {"a", "an", "the"}
GENERATOR_VERSION = "scene-affordance-action-v1"


def _bare_label(value: Any) -> str:
    tokens = TOKEN_RE.findall(str(value or "").casefold())
    while tokens and tokens[0] in ARTICLES:
        tokens.pop(0)
    return " ".join(tokens)


def _display_label(value: Any) -> str:
    # Preserve the source label's words but drop a leading article so the
    # generated action remains readable and deterministic.
    raw = str(value or "").strip()
    parts = raw.split()
    if parts and parts[0].casefold() in ARTICLES:
        parts = parts[1:]
    return " ".join(parts) or "object"


def _unique_entities(snapshot: dict, kind: str) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for entity in snapshot.get("entities") or []:
        if entity.get("kind") != kind:
            continue
        label = _bare_label(entity.get("label"))
        if not label or label in seen:
            continue
        seen.add(label)
        result.append(entity)
    return result


def generate_affordances(snapshot: dict) -> list[dict]:
    """Derive transparent affordance records from entity *types* only.

    ``inspect`` is the only object affordance because no source fact licenses
    a portability/ownership inference.  For another visible agent we expose
    generic contact affordances; these are candidates, not claims that the
    action succeeds or is socially appropriate.
    """
    actor = _bare_label(snapshot.get("actor"))
    affordances: list[dict] = []
    for entity in _unique_entities(snapshot, "object"):
        label = _display_label(entity.get("label"))
        affordances.append({
            "action_id": f"inspect:{entity['id']}",
            "action": f"inspect {label}",
            "target_entity_id": entity.get("id"),
            "kind": "object_inspection",
            "semantic_family": "inspect",
            "source": "entity_type_only",
            "required_facts": [],
        })
    for entity in _unique_entities(snapshot, "agent"):
        if _bare_label(entity.get("label")) == actor:
            continue
        label = _display_label(entity.get("label"))
        for verb, kind in (("hug", "social_contact"), ("hit", "physical_conflict")):
            affordances.append({
                "action_id": f"{verb}:{entity['id']}",
                "action": f"{verb} {label}",
                "target_entity_id": entity.get("id"),
                "kind": kind,
                "semantic_family": kind,
                "source": "agent_presence_only",
                "required_facts": [],
            })
    return affordances


def generate_action_candidates(snapshot: dict) -> list[dict]:
    """Return generated A^O; no current A* support or source action is read."""
    return generate_affordances(snapshot)


def support_diagnostic(generated: list[dict], source_candidates: list[str] | None) -> dict:
    """Compare after generation, for diagnosis only."""
    generated_actions = [item["action"] for item in generated]
    source = list(source_candidates or [])
    return {
        "generated_count": len(generated_actions),
        "source_count": len(source),
        "source_action_support_hit": {action: action in generated_actions for action in source},
        "source_candidates_used_for_generation": False,
    }
