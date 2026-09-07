from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "02_实验" / "Mechanism_Sanity_v1"
sys.path.insert(0, str(V1))

from candidate_generation_v1 import generate_action_candidates
from theory_s_v1 import TheoryPersonality, TheoryState, score_candidates, state_to_dict, update_state

OUT = Path(__file__).resolve().parent
BASELINE_P = TheoryPersonality()
BASELINE_S = TheoryState(fatigue=0.25, engagement=0.45, tension=0.20)


def _scene() -> dict:
    return {"actor": "student", "entities": [
        {"id": "desk", "label": "desk", "kind": "object", "type": "desk", "facts": {}},
        {"id": "stool", "label": "stool", "kind": "object", "type": "stool", "facts": {}},
        {"id": "book", "label": "book", "kind": "object", "type": "book", "facts": {"portable": True}},
        {"id": "friend", "label": "friend", "kind": "agent", "facts": {}},
    ], "possessions": [], "source_O": "controlled fixture"}


def _mass(scores: list[dict]) -> dict[str, float]:
    result: defaultdict[str, float] = defaultdict(float)
    for row in scores:
        result[str(row["semantic_family"])] += float(row["probability"])
    return dict(sorted(result.items()))


def _step(state: TheoryState, x: dict[str, float], candidates: list[dict]) -> dict:
    after = update_state(state, x, BASELINE_P)
    pi = score_candidates(candidates, after, BASELINE_P, temperature=0.42)
    return {"X_t": dict(x), "S_t": state_to_dict(state), "S_t_plus_1": state_to_dict(after),
            "pi_t": pi, "family_mass": _mass(pi),
            "top_action": max(pi, key=lambda row: float(row["probability"]))["action_id"]}


def _trajectory(name: str, xs: list[dict[str, float]], candidates: list[dict]) -> dict:
    state = BASELINE_S
    steps = []
    for x in xs:
        row = _step(state, x, candidates)
        steps.append(row)
        state = TheoryState(**row["S_t_plus_1"])
    fatigue = [row["S_t_plus_1"]["fatigue"] for row in steps]
    engagement = [row["S_t_plus_1"]["engagement"] for row in steps]
    tension = [row["S_t_plus_1"]["tension"] for row in steps]
    checks = {"support_fixed": True}
    if name == "continuous_effort":
        checks["fatigue_accumulates"] = all(b >= a for a, b in zip(fatigue, fatigue[1:]))
        checks["stimulation_mass_nonincreasing"] = all(
            b <= a + 1e-12 for a, b in zip([r["family_mass"].get("inspect", 0.0) for r in steps],
                                             [r["family_mass"].get("inspect", 0.0) for r in steps][1:]))
    elif name == "positive_progress":
        checks["engagement_accumulates"] = all(b >= a for a, b in zip(engagement, engagement[1:]))
        checks["social_mass_non_decreasing"] = all(
            b >= a - 1e-12 for a, b in zip([r["family_mass"].get("social_communication", 0.0) for r in steps],
                                             [r["family_mass"].get("social_communication", 0.0) for r in steps][1:]))
    elif name == "repeated_obstruction":
        checks["tension_accumulates"] = all(b >= a for a, b in zip(tension, tension[1:]))
        checks["conflict_mass_non_decreasing"] = all(
            b >= a - 1e-12 for a, b in zip([r["family_mass"].get("physical_conflict", 0.0) for r in steps],
                                             [r["family_mass"].get("physical_conflict", 0.0) for r in steps][1:]))
    else:
        checks["fatigue_recovers"] = all(b <= a for a, b in zip(fatigue, fatigue[1:]))
        checks["tension_recovers"] = all(b <= a for a, b in zip(tension, tension[1:]))
    checks["all_pass"] = all(checks.values())
    return {"trajectory": name, "steps": steps, "checks": checks}


def main() -> int:
    scene = _scene()
    candidates = generate_action_candidates(scene)
    xs = {
        "continuous_effort": [{"effort_load": 0.9, "goal_relevance": 0.2} for _ in range(6)],
        "positive_progress": [{"goal_relevance": 0.9, "positive_conduciveness": 0.9, "social_opportunity": 0.2} for _ in range(6)],
        "repeated_obstruction": [{"goal_relevance": 0.9, "negative_conduciveness": 0.9} for _ in range(6)],
        "rest_recovery": [{"recovery_cue": 0.9} for _ in range(6)],
    }
    results = [_trajectory(name, values, candidates) for name, values in xs.items()]
    payload = {"protocol": "Mechanism_Sanity_v1.2", "status": "controlled_trajectory_sanity_only",
               "candidate_action_ids": [c["action_id"] for c in candidates],
               "results": results, "invariants": {"A_O_fixed": True, "A_star_read": False,
               "P_fixed": True, "new_state_fields": False, "formal_prediction": False}}
    (OUT / "trajectory_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"trajectory_count": len(results), "all_pass": all(r["checks"]["all_pass"] for r in results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
