"""Small, explicit Theory-S v1 for mechanism engineering sanity checks.

This is not a fitted psychological model.  It is a frozen, auditable
state-transition and candidate-scoring operator whose support set is supplied
by the SceneSnapshot affordance generator.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Any


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


@dataclass(frozen=True)
class TheoryState:
    fatigue: float = 0.25
    engagement: float = 0.50
    tension: float = 0.20

    def clamped(self) -> "TheoryState":
        return TheoryState(clamp(self.fatigue), clamp(self.engagement), clamp(self.tension))


@dataclass(frozen=True)
class TheoryPersonality:
    recovery_preference: float = 0.50
    stimulation_seeking: float = 0.50
    threat_sensitivity: float = 0.50


STATE_FIELDS = ("fatigue", "engagement", "tension")
THEORY_VERSION = "theory-s-v1"


def update_state(state: TheoryState, x: dict[str, float], personality: TheoryPersonality,
                 dt: float = 1.0) -> TheoryState:
    """Per-field first-order update with bounded saturation and P modulation.

    X is an appraisal record, not a direct state delta.  ``x`` can contain
    ``effort_load``, ``goal_relevance``, ``positive_conduciveness``,
    ``negative_conduciveness``, ``social_opportunity`` and ``recovery_cue``.
    Missing values mean unknown/no evidence and are kept at neutral 0.
    """
    dt = max(0.0, float(dt))
    effort = clamp(x.get("effort_load", 0.0))
    goal = clamp(x.get("goal_relevance", 0.0))
    positive = clamp(x.get("positive_conduciveness", 0.0))
    negative = clamp(x.get("negative_conduciveness", 0.0))
    social = clamp(x.get("social_opportunity", 0.0))
    recovery = clamp(x.get("recovery_cue", 0.0))

    # Each field has its own target, inertia and relaxation.  P changes only
    # the update operator; it cannot add/remove an action candidate.
    fatigue_target = clamp(0.20 + 0.55 * effort + 0.20 * negative - 0.35 * recovery)
    engagement_target = clamp(0.15 + 0.45 * goal + 0.25 * positive + 0.20 * social)
    tension_target = clamp(0.10 + 0.55 * negative + 0.25 * goal - 0.30 * recovery)

    fatigue_eta = 0.28 * (0.75 + 0.50 * (1.0 - personality.recovery_preference))
    engagement_eta = 0.22 * (0.75 + 0.50 * personality.stimulation_seeking)
    tension_eta = 0.18 * (0.75 + 0.50 * personality.threat_sensitivity)
    # Natural recovery/decay is explicit and cannot overshoot the target.
    f = state.fatigue + dt * fatigue_eta * (fatigue_target - state.fatigue)
    e = state.engagement + dt * engagement_eta * (engagement_target - state.engagement)
    t = state.tension + dt * tension_eta * (tension_target - state.tension)
    return TheoryState(clamp(f), clamp(e), clamp(t))


def scene_appraisal(snapshot: dict[str, Any]) -> dict[str, float]:
    """Only report signals supported by the snapshot; no A* or goal inference."""
    entities = snapshot.get("entities") or []
    agent_count = sum(1 for e in entities if e.get("kind") == "agent")
    object_count = sum(1 for e in entities if e.get("kind") == "object")
    return {
        "effort_load": 0.0,
        "goal_relevance": 0.0,  # LIGHT has no verified goal field.
        "positive_conduciveness": 0.0,
        "negative_conduciveness": 0.0,
        "social_opportunity": clamp((agent_count - 1) / 2.0),
        "recovery_cue": 0.0,
        "observed_agent_count": float(agent_count),
        "observed_object_count": float(object_count),
    }


def _semantics(candidate: dict[str, Any]) -> dict[str, float]:
    family = candidate.get("semantic_family")
    return {
        "goal_progress": 0.0,
        "stimulation": 1.0 if family in {"inspect", "social_contact", "physical_conflict"} else 0.0,
        "recovery": 0.0,
        "short_term_reward": 1.0 if family == "social_contact" else 0.0,
        "environment_control": 1.0 if family == "inspect" else 0.0,
        "social_contact": 1.0 if family == "social_contact" else 0.0,
        "conflict": 1.0 if family == "physical_conflict" else 0.0,
    }


def score_candidates(candidates: list[dict[str, Any]], state: TheoryState,
                     personality: TheoryPersonality | None = None,
                     temperature: float = 0.65) -> list[dict[str, float | str]]:
    """Score every generated candidate; S/P never gate action legality."""
    if not candidates:
        raise ValueError("cannot score an empty generated A^O")
    p = personality or TheoryPersonality()
    s = state.clamped()
    temp = max(0.05, float(temperature) + 0.10 * p.threat_sensitivity)
    logits: list[float] = []
    for candidate in candidates:
        f = _semantics(candidate)
        # S alters preference, not candidate membership.  Tension makes
        # conflict salient but also makes inspection/environment control safer;
        # this produces an interpretable competing-action sanity check.
        score = (
            0.20 * f["stimulation"] * (0.65 + 0.70 * s.engagement - 0.25 * s.fatigue)
            + 0.22 * f["short_term_reward"] * (0.65 + 0.45 * s.engagement)
            + 0.20 * f["environment_control"] * (0.75 + 0.30 * s.tension + 0.20 * s.fatigue)
            + 0.34 * f["conflict"] * (0.35 + 0.65 * s.tension) * (0.55 + 0.45 * p.threat_sensitivity)
            - 0.12 * f["conflict"] * s.fatigue
        )
        logits.append(score)
    m = max(logits)
    weights = [math.exp((v - m) / temp) for v in logits]
    z = sum(weights)
    return [{"action_id": c["action_id"], "action": c["action"],
             "score": float(v), "probability": float(w / z)}
            for c, v, w in zip(candidates, logits, weights)]


def state_to_dict(state: TheoryState) -> dict[str, float]:
    return {key: float(value) for key, value in asdict(state).items()}

