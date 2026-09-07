"""Dataset-neutral raw candidate features for the replay probe v1.

This module contains feature construction only.  It never receives or uses
the held-out A* except as the caller's separate evaluation label.
"""
from __future__ import annotations
import re

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
SEMANTIC_FEATURES = (
    "goal_progress", "stimulation", "recovery", "hunger_relief",
    "bathroom_relief", "short_term_reward", "environment_control",
)
FEATURE_NAMES = SEMANTIC_FEATURES + (
    "context_relevance", "has_target", "target_in_scene",
    "target_visible_in_O", "target_in_inventory", "repeated_acquire",
)
FEATURE_VERSION = "replay-raw-features-v1"

def words(value):
    return TOKEN_RE.findall(str(value or "").casefold())

def compile_candidate_v1(action, snapshot, rules):
    """Return (raw feature dict, matched group, provenance flags).

    Semantic group membership is topology-only: every mapped dimension is 1.
    Scene facts remain separate booleans; no precomputed scene bias is emitted.
    """
    toks = words(action)
    first = toks[0] if toks else ""
    feat = {key: 0.0 for key in FEATURE_NAMES}
    matched = None
    for group in rules["groups"]:
        if first in group["verbs"]:
            matched = group["name"]
            for key in group.get("features", {}):
                if key in SEMANTIC_FEATURES:
                    feat[key] = 1.0
    context_words = set(words(snapshot.get("actor_observation")))
    content = [w for w in toks[1:] if w not in {"a","an","the","to","from","at","in","on","with","of","for","into","onto","my","your","his","her","their"}]
    feat["context_relevance"] = (len(set(content) & context_words) / len(set(content)) if content else 0.0)
    target = set(content)
    entities = snapshot.get("entities") or []
    target_entities = [e for e in entities if target & set(words(e.get("label")))]
    inventory = set(words([p.get("entity", "") for p in snapshot.get("possessions") or []]))
    feat["has_target"] = float(bool(target))
    feat["target_in_scene"] = float(bool(target_entities))
    feat["target_visible_in_O"] = float(bool(target) and target.issubset(context_words))
    feat["target_in_inventory"] = float(bool(target) and target.issubset(inventory))
    feat["repeated_acquire"] = float(first in {"get", "take", "steal"} and feat["target_in_inventory"] > 0)
    flags = {
        "feature_version": FEATURE_VERSION,
        "target_entity_id": target_entities[0].get("id") if target_entities else None,
        "semantic_source": "compiled_semantics_topology_v1",
        "scene_source": "canonical_scene_snapshot_v0",
        "contains_scene_bias": False,
    }
    return feat, matched, flags

def vectorize(features):
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
