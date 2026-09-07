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


def _series(rows: list[dict], field: str) -> list[float]:
    return [float(row["S_t_plus_1"][field]) for row in rows]


def _relaxation_check(rows: list[dict], field: str) -> dict:
    values = _series(rows, field)
    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    nonzero = [abs(delta) for delta in deltas if abs(delta) > 1e-10]
    direction = 1 if sum(deltas) >= 0 else -1
    same_direction = all(direction * delta >= -1e-10 for delta in deltas)
    shrinking = all(b <= a + 1e-10 for a, b in zip(nonzero, nonzero[1:])) if len(nonzero) > 1 else True
    return {"values": values, "step_deltas": deltas, "same_direction": same_direction,
            "step_magnitude_nonincreasing": shrinking, "pass": same_direction and shrinking}


def _phase_rows(state: TheoryState, xs: list[dict[str, float]], candidates: list[dict]) -> tuple[list[dict], TheoryState]:
    rows = []
    for x in xs:
        row = _step(state, x, candidates)
        rows.append(row)
        state = TheoryState(**row["S_t_plus_1"])
    return rows, state


def _trajectory(name: str, phases: list[tuple[str, list[dict[str, float]]]], candidates: list[dict]) -> dict:
    state = BASELINE_S
    all_rows: list[dict] = []
    phase_rows = []
    for phase_name, xs in phases:
        rows, state = _phase_rows(state, xs, candidates)
        phase_rows.append({"phase": phase_name, "steps": rows})
        all_rows.extend(rows)

    checks: dict[str, object] = {"support_fixed": True}
    if name == "effort_build_up_recovery":
        build = phase_rows[0]["steps"]
        recover = phase_rows[1]["steps"]
        checks["fatigue_builds"] = _series(build, "fatigue")[-1] > _series(build, "fatigue")[0]
        checks["fatigue_recovers"] = _series(recover, "fatigue")[-1] < _series(recover, "fatigue")[0]
        checks["fatigue_relaxation_build"] = _relaxation_check(build, "fatigue")
        checks["fatigue_relaxation_recovery"] = _relaxation_check(recover, "fatigue")
        checks["stimulation_mass_declines_on_build"] = _mass(build[-1]["pi_t"]).get("inspect", 0) <= _mass(build[0]["pi_t"]).get("inspect", 0)
        checks["posture_mass_tracks_recovery"] = _mass(recover[-1]["pi_t"]).get("posture", 0) <= _mass(recover[0]["pi_t"]).get("posture", 0)
    elif name == "positive_progress":
        checks["engagement_builds"] = _series(all_rows, "engagement")[-1] > _series(all_rows, "engagement")[0]
        checks["engagement_relaxation"] = _relaxation_check(all_rows, "engagement")
        checks["social_mass_rises"] = _mass(all_rows[-1]["pi_t"]).get("social_communication", 0) >= _mass(all_rows[0]["pi_t"]).get("social_communication", 0)
        checks["cross_effect_tension_declines"] = _series(all_rows, "tension")[-1] <= _series(all_rows, "tension")[0]
    elif name == "obstruction_build_up_decay":
        build = phase_rows[0]["steps"]
        decay = phase_rows[1]["steps"]
        checks["tension_builds"] = _series(build, "tension")[-1] > _series(build, "tension")[0]
        checks["tension_decays"] = _series(decay, "tension")[-1] < _series(decay, "tension")[0]
        checks["tension_relaxation_build"] = _relaxation_check(build, "tension")
        checks["tension_relaxation_decay"] = _relaxation_check(decay, "tension")
        checks["conflict_mass_rises_on_build"] = _mass(build[-1]["pi_t"]).get("physical_conflict", 0) >= _mass(build[0]["pi_t"]).get("physical_conflict", 0)
        checks["conflict_mass_returns_on_decay"] = _mass(decay[-1]["pi_t"]).get("physical_conflict", 0) <= _mass(decay[0]["pi_t"]).get("physical_conflict", 0)
        checks["cross_effect_fatigue_reported"] = _series(build, "fatigue")[-1] >= _series(build, "fatigue")[0]
    else:
        checks["fatigue_recovers"] = _series(all_rows, "fatigue")[-1] < _series(all_rows, "fatigue")[0]
        checks["tension_recovers"] = _series(all_rows, "tension")[-1] < _series(all_rows, "tension")[0]
        checks["fatigue_relaxation"] = _relaxation_check(all_rows, "fatigue")
        checks["tension_relaxation"] = _relaxation_check(all_rows, "tension")
    checks["all_pass"] = all(value if isinstance(value, bool) else value["pass"] for value in checks.values())
    return {"trajectory": name, "phases": phase_rows, "checks": checks,
            "cross_effects": {field: {"values": _series(all_rows, field),
                                        "net_change": _series(all_rows, field)[-1] - _series(all_rows, field)[0]}
                               for field in ("fatigue", "engagement", "tension")}}


def main() -> int:
    candidates = generate_action_candidates(_scene())
    trajectories = {
        "effort_build_up_recovery": [("build_up", [{"effort_load": 0.9} for _ in range(6)]),
                                     ("recovery", [{"recovery_cue": 0.9} for _ in range(8)])],
        "positive_progress": [("progress", [{"positive_conduciveness": 0.9, "social_opportunity": 0.9} for _ in range(6)])],
        "obstruction_build_up_decay": [("obstruction", [{"negative_conduciveness": 0.9} for _ in range(6)]),
                                        ("neutral_decay", [{} for _ in range(8)])],
        "rest_recovery": [("recovery", [{"recovery_cue": 0.9} for _ in range(8)])],
    }
    results = [_trajectory(name, phases, candidates) for name, phases in trajectories.items()]
    payload = {"protocol": "Mechanism_Sanity_v1.2", "status": "controlled_trajectory_sanity_only",
               "candidate_action_ids": [c["action_id"] for c in candidates],
               "results": results, "invariants": {"A_O_fixed": True, "A_star_read": False,
               "P_fixed": True, "new_state_fields": False, "formal_prediction": False,
               "cross_effects_reported": True}}
    (OUT / "trajectory_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"trajectory_count": len(results), "all_pass": all(r["checks"]["all_pass"] for r in results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
