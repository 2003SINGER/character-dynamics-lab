"""Small, source-preserving SceneSnapshot transition and appraisal layer."""
from __future__ import annotations
import re

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

def words(value):
    return TOKEN_RE.findall(str(value or "").casefold())

def _entities(snapshot):
    return {e.get("id"): e for e in snapshot.get("entities", [])}

def _visible(snapshot, entity):
    return bool(entity and set(words(entity.get("label"))) <= set(words(snapshot.get("actor_observation"))))

def diff_scene_snapshots(previous, current):
    events = []
    if previous.get("place") != current.get("place"):
        events.append({"kind": "place_changed", "before": previous.get("place"), "after": current.get("place"), "source": "canonical_scene_snapshot"})
    pe, ce = _entities(previous), _entities(current)
    for entity_id in sorted(ce.keys() - pe.keys()):
        events.append({"kind": "entity_entered_scene", "entity_id": entity_id, "after": ce[entity_id].get("label"), "source": "canonical_scene_snapshot"})
    for entity_id in sorted(pe.keys() - ce.keys()):
        events.append({"kind": "entity_left_scene", "entity_id": entity_id, "before": pe[entity_id].get("label"), "source": "canonical_scene_snapshot"})
    pp = {(p.get("entity"), p.get("relation")) for p in previous.get("possessions", [])}
    cp = {(p.get("entity"), p.get("relation")) for p in current.get("possessions", [])}
    for entity_id, relation in sorted(cp - pp):
        events.append({"kind": "possession_added", "entity_id": entity_id, "relation": relation, "source": "canonical_scene_snapshot"})
    for entity_id, relation in sorted(pp - cp):
        events.append({"kind": "possession_removed", "entity_id": entity_id, "relation": relation, "source": "canonical_scene_snapshot"})
    for entity_id in sorted(set(pe) & set(ce)):
        if pe[entity_id].get("facts", {}) != ce[entity_id].get("facts", {}):
            events.append({"kind": "fact_changed", "entity_id": entity_id, "before": pe[entity_id].get("facts", {}), "after": ce[entity_id].get("facts", {}), "source": "canonical_scene_snapshot"})
        before, after = _visible(previous, pe[entity_id]), _visible(current, ce[entity_id])
        if before != after:
            events.append({"kind": "observed_entity_gained" if after else "observed_entity_lost", "entity_id": entity_id, "source": "derived_from_actor_observation"})
    return events

def expected_effect(action, previous):
    toks = words(action)
    if not toks:
        return None
    verb = toks[0]
    target_words = set(toks[1:])
    entities = previous.get("entities", [])
    target = next((e for e in entities if target_words & set(words(e.get("label")))), None)
    if not target:
        return None
    relation = {"wear": "wearing", "wield": "wielding"}.get(verb)
    if verb in {"get", "take", "steal"}:
        kind = "possession_added"
    elif verb in {"drop", "give"}:
        kind = "possession_removed"
    elif relation:
        kind = "possession_added"
    else:
        return None
    return {"behavior": verb, "target_entity": target["id"], "effect_kind": kind, "relation": relation or "carrying", "source": "expected_effect_v0"}

def appraise_transition(previous, current, action):
    events = diff_scene_snapshots(previous, current)
    effect = expected_effect(action, previous)
    x = {"goal_relevance": 0.0, "positive_conduciveness": 0.0, "negative_conduciveness": 0.0, "evidence": [], "transition_events": events, "matched_effect_events": [], "expected_effect": effect}
    if not effect:
        return x
    matches = [e for e in events if e.get("kind") == effect["effect_kind"] and e.get("entity_id") == effect["target_entity"] and (not effect.get("relation") or e.get("relation") == effect["relation"])]
    if matches:
        x["goal_relevance"] = 1.0
        x["positive_conduciveness"] = 1.0
        x["matched_effect_events"] = matches
        x["evidence"].append("expected_effect_observed")
    else:
        x["evidence"].append("expected_effect_unconfirmed_not_obstruction")
    return x

def zero_state():
    return {"relevance_trace": 0.0, "positive_conduciveness_trace": 0.0, "negative_conduciveness_trace": 0.0}

def update_state(state, x, eta=0.35):
    for src, dst in (("goal_relevance", "relevance_trace"), ("positive_conduciveness", "positive_conduciveness_trace"), ("negative_conduciveness", "negative_conduciveness_trace")):
        state[dst] = max(0.0, min(1.0, state[dst] + eta * (x[src] - state[dst])))
    return dict(state)

def apply_state_to_candidate(feat, state):
    # Fixed, deliberately small interaction head; scorer itself is unchanged.
    signal = state["relevance_trace"] + state["positive_conduciveness_trace"] - state["negative_conduciveness_trace"]
    feat = dict(feat)
    feat["goal_progress"] = max(0.0, min(1.0, feat["goal_progress"] * (1.0 + 0.20 * signal)))
    return feat
