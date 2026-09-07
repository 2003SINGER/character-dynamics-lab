"""Auditable canonical SceneSnapshot -> generated A^O compiler.

The compiler consumes only a canonical scene projection. Source A* /
available_actions fields are deliberately not part of its read path; they are
accepted only by support_diagnostic after compilation. Missing facts remain
unknown and therefore do not license an action.
"""
from __future__ import annotations

import re
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")
ARTICLES = {"a", "an", "the"}
GENERATOR_VERSION = "scene-affordance-action-v1.1"

SUPPORTED_VERBS = {"inspect", "take", "get", "drop", "give", "wear", "wield", "talk", "hug", "hit", "sit", "use"}
VERB_ALIASES = {"get": "take"}


def _bare_label(value: Any) -> str:
    tokens = TOKEN_RE.findall(str(value or "").casefold())
    while tokens and tokens[0] in ARTICLES:
        tokens.pop(0)
    return " ".join(tokens)


def _display_label(value: Any) -> str:
    raw = str(value or "").strip()
    parts = raw.split()
    if parts and parts[0].casefold() in ARTICLES:
        parts = parts[1:]
    return " ".join(parts) or "object"


def _fact(entity: dict[str, Any], key: str) -> Any:
    facts = entity.get("facts")
    return facts.get(key) if isinstance(facts, dict) else None


def _truth(entity: dict[str, Any], key: str) -> bool:
    return _fact(entity, key) is True


def _entities(snapshot: dict[str, Any], kind: str, *, room_only: bool = False) -> list[dict[str, Any]]:
    """Return canonical entities in stable source order, preserving duplicates."""
    result: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}
    for index, raw in enumerate(snapshot.get("entities") or []):
        if not isinstance(raw, dict) or raw.get("kind") != kind:
            continue
        location = str(raw.get("location") or "room").casefold()
        if room_only and location not in {"room", "visible", "scene"}:
            continue
        entity = dict(raw)
        base_id = str(entity.get("id") or f"{kind}.{index:04d}")
        seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
        entity["id"] = base_id if seen_ids[base_id] == 1 else f"{base_id}#{seen_ids[base_id]}"
        entity.setdefault("facts", {})
        entity.setdefault("type", "unknown")
        entity.setdefault("description", "")
        entity.setdefault("provenance", {})
        result.append(entity)
    return result


def _possessions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Materialize carrying/wearing/wielding as explicit possession records."""
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    direct = snapshot.get("possessions") or []
    for relation, values in [("carrying", direct), ("carrying", snapshot.get("carrying") or []),
                             ("wearing", snapshot.get("wearing") or []),
                             ("wielding", snapshot.get("wielding") or [])]:
        if not isinstance(values, list):
            values = [values]
        for index, raw in enumerate(values):
            item = dict(raw) if isinstance(raw, dict) else {"label": raw}
            label = item.get("label") or item.get("name") or item.get("item")
            if not label:
                continue
            key = (relation, _bare_label(label))
            if key in seen:
                continue
            seen.add(key)
            item["id"] = str(item.get("id") or f"possession.{relation}.{index:04d}")
            item["label"] = str(label)
            item["kind"] = "object"
            item["location"] = "carried"
            item["possession_relation"] = relation
            item.setdefault("facts", {})
            item.setdefault("type", "unknown")
            item.setdefault("description", "")
            item.setdefault("provenance", {"source_field": relation})
            records.append(item)
    return records


def _aliases(entity: dict[str, Any]) -> set[str]:
    values = [entity.get("label"), entity.get("id"), entity.get("type")]
    raw_aliases = entity.get("aliases") or []
    values.extend(raw_aliases if isinstance(raw_aliases, list) else [raw_aliases])
    return {_bare_label(value) for value in values if _bare_label(value)}


def _evidence(entity: dict[str, Any], source: str, facts: list[str] | None = None) -> dict[str, Any]:
    return {"source": source, "entity_id": entity.get("id"), "label": entity.get("label"),
            "type": entity.get("type", "unknown"), "description": entity.get("description", ""),
            "facts": dict(entity.get("facts") or {}), "provenance": dict(entity.get("provenance") or {}),
            "matched_facts": list(facts or [])}


def _record(verb: str, entities: list[dict[str, Any]], family: str, rule_id: str,
            required: list[str], unknown: list[str], evidence: list[dict[str, Any]],
            target_ids: list[str]) -> dict[str, Any]:
    labels = [_display_label(next(e["label"] for e in entities if e["id"] == tid)) for tid in target_ids]
    action = f"{verb} {' to '.join(labels) if verb == 'give' else ' '.join(labels)}".strip()
    return {"action_id": f"{verb}:{'|'.join(target_ids)}", "action": action,
            "target": labels[0] if len(labels) == 1 else labels, "targets": list(target_ids),
            "target_entity_id": target_ids[0] if len(target_ids) == 1 else None,
            "semantic_family": family, "rule_id": rule_id, "required_facts": required,
            "supporting_evidence": evidence, "unknown_preconditions": unknown}


def _text(entity: dict[str, Any]) -> str:
    return " ".join(str(entity.get(key) or "") for key in ("type", "description", "label")).casefold()


def _use_supported(entity: dict[str, Any]) -> bool:
    if _truth(entity, "usable"):
        return True
    # Small, auditable ontology: no broad commonsense inference from a bare object.
    return bool(re.search(r"\b(lantern|horn|scale|key|lever|button|door|weapon|sword|book)\b", _text(entity)))


def _sit_supported(entity: dict[str, Any]) -> bool:
    return bool(re.search(r"\b(chair|stool|seat)\b", _text(entity)))


def _make_action(verb: str, entity: dict[str, Any], family: str, rule_id: str,
                 required: list[str], unknown: list[str], source: str,
                 facts: list[str] | None = None, others: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    targets = [entity] + list(others or [])
    return _record(verb, targets, family, rule_id, required, unknown,
                   [_evidence(item, source, facts if item is entity else None) for item in targets],
                   [item["id"] for item in targets])


def generate_affordances(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Compile candidates from visible entities and explicit possession facts."""
    objects = _entities(snapshot, "object", room_only=True)
    agents = _entities(snapshot, "agent", room_only=True)
    possessions = _possessions(snapshot)
    actor = _bare_label(snapshot.get("actor"))
    visible_agents = [a for a in agents if _bare_label(a.get("label")) != actor]
    actions: list[dict[str, Any]] = []
    for obj in objects:
        actions.append(_make_action("inspect", obj, "inspect", "O.inspect.visible_object", ["object.visible"],
                                    ["inspection_success"], "canonical.entities[kind=object,location=room]"))
        if _truth(obj, "portable"):
            actions.append(_make_action("take", obj, "acquisition", "O.take.explicit_portable",
                                        ["object.visible", "object.portable=true"], ["ownership", "take_success"],
                                        "entity.facts.portable", ["portable"]))
        if _sit_supported(obj):
            actions.append(_make_action("sit", obj, "posture", "O.sit.seat_lexeme",
                                        ["object.visible", "chair_or_stool_or_seat_evidence"],
                                        ["permission", "sit_success"], "entity.type_or_description"))
        if _use_supported(obj):
            actions.append(_make_action("use", obj, "object_use", "O.use.explicit_use_support",
                                        ["object.visible", "type_or_description_supports_use"],
                                        ["use_success", "permission"], "entity.type_or_description"))
    for agent in visible_agents:
        actions.append(_make_action("talk", agent, "social_communication", "O.talk.visible_agent",
                                    ["agent.visible"], ["language", "conversation_success"],
                                    "canonical.entities[kind=agent,location=room]"))
        actions.append(_make_action("hug", agent, "social_contact", "O.hug.generic_contact",
                                    ["agent.visible"], ["social_permission", "appropriateness", "contact_success"],
                                    "canonical.entities[kind=agent,location=room]"))
        actions.append(_make_action("hit", agent, "physical_conflict", "O.hit.generic_contact",
                                    ["agent.visible"], ["appropriateness", "harm", "contact_success"],
                                    "canonical.entities[kind=agent,location=room]"))
    for item in possessions:
        actions.append(_make_action("drop", item, "release", "O.drop.actor_holds", ["actor.holds(object)"],
                                    ["drop_success", "destination"], "canonical.possessions", ["possession_relation"]))
        for agent in visible_agents:
            actions.append(_record("give", [item, agent], "transfer", "O.give.holds_visible_agent",
                                   ["actor.holds(object)", "agent.visible"], ["ownership", "consent", "transfer_success"],
                                   [_evidence(item, "canonical.possessions", ["possession_relation"]),
                                    _evidence(agent, "canonical.entities[kind=agent]")], [item["id"], agent["id"]]))
        if _truth(item, "wearable"):
            actions.append(_make_action("wear", item, "equipment", "O.wear.explicit_wearable",
                                        ["actor.holds(object)", "object.wearable=true"], ["wear_success", "fit"],
                                        "possession.facts.wearable", ["wearable"]))
        if _truth(item, "wieldable"):
            actions.append(_make_action("wield", item, "equipment", "O.wield.explicit_wieldable",
                                        ["actor.holds(object)", "object.wieldable=true"], ["wield_success", "appropriateness"],
                                        "possession.facts.wieldable", ["wieldable"]))
    return actions


def generate_action_candidates(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return generate_affordances(snapshot)


def _source_parts(action: str) -> tuple[str, str]:
    tokens = str(action or "").strip().casefold().split()
    return (tokens[0] if tokens else "", " ".join(tokens[1:]))


def _miss_reason(action: str, generated: list[dict], snapshot: dict[str, Any] | None) -> str:
    verb, target = _source_parts(action)
    canonical_verb = VERB_ALIASES.get(verb, verb)
    if not verb or canonical_verb not in {VERB_ALIASES.get(v, v) for v in SUPPORTED_VERBS}:
        return "ontology"
    if snapshot is None:
        return "other"
    entities = _entities(snapshot, "object") + _entities(snapshot, "agent") + _possessions(snapshot)
    target_key = _bare_label(target)
    aliases = [e for e in entities if target_key in _aliases(e) or target_key == _bare_label(e.get("label"))]
    if not aliases:
        raw_objects = snapshot.get("room_objects") or []
        raw_agents = snapshot.get("room_agents") or []
        if any(target_key == _bare_label(x.get("label") if isinstance(x, dict) else x)
               for x in list(raw_objects) + list(raw_agents)):
            return "object extraction"
        return "entity binding"
    if canonical_verb in {"take", "wear", "wield"}:
        return "hidden/unknown fact"
    if canonical_verb in {"drop", "give"}:
        return "hidden/unknown fact"
    if canonical_verb == "sit" and not any(_sit_supported(e) for e in aliases):
        return "ontology"
    if canonical_verb == "use" and not any(_use_supported(e) for e in aliases):
        return "ontology"
    return "insufficient O"


def support_diagnostic(generated: list[dict], source_candidates: list[str] | None,
                      snapshot: dict[str, Any] | None = None) -> dict:
    """Post-hoc support hit/miss report; never feeds generation."""
    generated_actions = {str(item["action"]).casefold() for item in generated}
    source = list(source_candidates or [])
    rows = []
    for action in source:
        hit = str(action).casefold() in generated_actions
        rows.append({"source_action": action, "hit": hit,
                     "miss_reason": None if hit else _miss_reason(action, generated, snapshot)})
    counts: dict[str, int] = {}
    for row in rows:
        if row["miss_reason"]:
            counts[row["miss_reason"]] = counts.get(row["miss_reason"], 0) + 1
    return {"generated_count": len(generated), "source_count": len(source),
            "source_action_support_hit": {row["source_action"]: row["hit"] for row in rows},
            "support_rows": rows, "miss_reason_counts": counts,
            "source_candidates_used_for_generation": False}
