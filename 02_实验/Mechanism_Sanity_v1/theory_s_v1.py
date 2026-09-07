"""Candidate mechanism / engineering operator for the v1.1 sanity slice.

The three fields are candidate mechanisms, not an engineered or fitted Theory-S
model.  The operator is intentionally explicit so each coupling can be audited
and removed without changing the generated support set.
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
PERSONALITY_FIELDS = ("recovery_preference", "stimulation_seeking", "threat_sensitivity")
THEORY_VERSION = "theory-s-candidate-v1.1"


def update_state(state: TheoryState, x: dict[str, float], personality: TheoryPersonality,
                 dt: float = 1.0) -> TheoryState:
    """Bounded first-order candidate transition; missing appraisal stays unknown/neutral."""
    dt = max(0.0, float(dt))
    effort = clamp(x.get("effort_load", 0.0))
    goal = clamp(x.get("goal_relevance", 0.0))
    positive = clamp(x.get("positive_conduciveness", 0.0))
    negative = clamp(x.get("negative_conduciveness", 0.0))
    social = clamp(x.get("social_opportunity", 0.0))
    recovery = clamp(x.get("recovery_cue", 0.0))
    fatigue_target = clamp(0.20 + 0.55 * effort + 0.20 * negative - 0.35 * recovery)
    engagement_target = clamp(0.15 + 0.45 * goal + 0.25 * positive + 0.20 * social)
    tension_target = clamp(0.10 + 0.55 * negative + 0.25 * goal - 0.30 * recovery)
    fatigue_eta = 0.28 * (0.75 + 0.50 * (1.0 - clamp(personality.recovery_preference)))
    engagement_eta = 0.22 * (0.75 + 0.50 * clamp(personality.stimulation_seeking))
    tension_eta = 0.18 * (0.75 + 0.50 * clamp(personality.threat_sensitivity))
    return TheoryState(clamp(state.fatigue + dt * fatigue_eta * (fatigue_target - state.fatigue)),
                       clamp(state.engagement + dt * engagement_eta * (engagement_target - state.engagement)),
                       clamp(state.tension + dt * tension_eta * (tension_target - state.tension)))


def scene_appraisal(snapshot: dict[str, Any]) -> dict[str, float]:
    """Expose only auditable scene signals; most LIGHT appraisal inputs are unknown."""
    entities = snapshot.get("entities") or []
    agent_count = sum(1 for e in entities if e.get("kind") == "agent")
    object_count = sum(1 for e in entities if e.get("kind") == "object")
    return {"effort_load": 0.0, "goal_relevance": 0.0, "positive_conduciveness": 0.0,
            "negative_conduciveness": 0.0, "social_opportunity": clamp((agent_count - 1) / 2.0),
            "recovery_cue": 0.0, "observed_agent_count": float(agent_count),
            "observed_object_count": float(object_count)}


def _semantics(candidate: dict[str, Any]) -> dict[str, float]:
    family = candidate.get("semantic_family")
    social = family in {"social_communication", "social_contact", "transfer"}
    stimulation = family in {"inspect", "social_communication", "social_contact", "physical_conflict", "object_use"}
    recovery = family in {"posture"}
    return {"stimulation": float(stimulation), "social": float(social), "recovery": float(recovery),
            "conflict": float(family == "physical_conflict"), "release": float(family == "release"),
            "object_use": float(family == "object_use"), "transfer": float(family == "transfer")}


def score_candidates(candidates: list[dict[str, Any]], state: TheoryState,
                     personality: TheoryPersonality | None = None,
                     temperature: float = 0.65) -> list[dict[str, float | str]]:
    """Score generated candidates; S/P can change preference, never legality."""
    if not candidates:
        raise ValueError("cannot score an empty generated A^O")
    p = personality or TheoryPersonality()
    s = state.clamped()
    # P changes score/transition parameters only; it does not affect support.
    temp = max(0.05, float(temperature) + 0.06 * clamp(p.threat_sensitivity))
    logits: list[float] = []
    for candidate in candidates:
        f = _semantics(candidate)
        # Deliberately removed: inspect -> environment_control and tension ->
        # inspect.  No avoidance/control family is asserted in this slice.
        score = (
            0.28 * f["stimulation"] * (0.70 + 0.80 * s.engagement - 0.42 * s.fatigue)
            + 0.16 * f["social"] * (0.60 + 0.75 * s.engagement + 0.20 * p.stimulation_seeking)
            + 0.36 * f["conflict"] * (0.30 + 0.90 * s.tension - 0.25 * s.fatigue)
            * (0.65 + 0.70 * clamp(p.threat_sensitivity))
            + 0.12 * f["recovery"] * (0.65 + 0.55 * s.fatigue + 0.25 * p.recovery_preference)
            + 0.04 * f["object_use"] * (0.50 + 0.35 * s.engagement)
            + 0.02 * f["transfer"]
            - 0.01 * f["release"]
        )
        logits.append(score)
    m = max(logits)
    weights = [math.exp((v - m) / temp) for v in logits]
    z = sum(weights)
    return [{"action_id": c["action_id"], "action": c["action"], "semantic_family": c.get("semantic_family"),
             "score": float(v), "probability": float(w / z)} for c, v, w in zip(candidates, logits, weights)]


def state_to_dict(state: TheoryState) -> dict[str, float]:
    return {key: float(value) for key, value in asdict(state).items()}


def personality_to_dict(personality: TheoryPersonality) -> dict[str, float]:
    return {key: float(value) for key, value in asdict(personality).items()}
