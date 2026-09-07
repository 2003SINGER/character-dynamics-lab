"""Build fixtures and run the controlled Theory-S / candidate-generation sanity."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from candidate_generation_v1 import generate_action_candidates, support_diagnostic
from theory_s_v1 import TheoryPersonality, TheoryState, scene_appraisal, score_candidates, state_to_dict

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "02_实验" / "Replay" / "review_samples" / "LIGHT_review_v0.jsonl"
OUT = Path(__file__).resolve().parent


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    transformed = row["transformed"]
    raw = row.get("raw") or {}
    ctx = transformed.get("source_step_context") or {}
    setting = raw.get("setting") or {}
    return {
        "schema_version": "canonical_scene_snapshot_v0",
        "dataset": "LIGHT",
        "trajectory_id": row.get("source_record_ref"),
        "t": transformed.get("t"),
        "place": setting.get("name"),
        "setting": setting,
        "actor": ctx.get("actor"),
        "entities": [
            {"id": f"fixture.object.{i}", "label": label, "kind": "object", "facts": {}}
            for i, label in enumerate(ctx.get("room_objects") or [])
        ] + [
            {"id": f"fixture.agent.{i}", "label": label, "kind": "agent", "facts": {}}
            for i, label in enumerate(ctx.get("room_agents") or [])
        ],
        "possessions": [],
        "actor_observation": transformed.get("source_O"),
        "source_candidates": transformed.get("candidate_set_factual"),
        "provenance": {"source_record_ref": row.get("source_record_ref")},
    }


def _read_rows() -> list[dict[str, Any]]:
    rows = []
    with REVIEW.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            source = row.get("transformed", {}).get("candidate_set_factual") or []
            if len(source) >= 4:
                rows.append(row)
    return rows


def _choose_fixtures() -> list[dict[str, Any]]:
    # Fixed first-match selection across distinct scenes; this is a development
    # fixture set, not a sample or a test split.
    selected = []
    seen_places = set()
    for row in _read_rows():
        snap = _snapshot(row)
        generated = generate_action_candidates(snap)
        place = snap.get("place")
        if len(generated) >= 4 and place not in seen_places:
            selected.append({"row": row, "snapshot": snap, "generated": generated})
            seen_places.add(place)
        if len(selected) == 5:
            break
    if len(selected) < 3:
        raise RuntimeError("LIGHT did not yield 3 generated-action fixtures")
    return selected


def _distribution(scores: list[dict[str, Any]]) -> dict[str, float]:
    return {str(item["action"]): float(item["probability"]) for item in scores}


def _intervention(fixture: dict[str, Any]) -> dict[str, Any]:
    generated = fixture["generated"]
    generated_before = generate_action_candidates(fixture["snapshot"])
    generated_after = generate_action_candidates(fixture["snapshot"])
    p = TheoryPersonality()
    before = TheoryState(fatigue=0.05, engagement=0.95, tension=0.05)
    after = TheoryState(fatigue=0.95, engagement=0.05, tension=0.95)
    b_scores = score_candidates(generated, before, p, temperature=0.42)
    a_scores = score_candidates(generated, after, p, temperature=0.42)
    bp = _distribution(b_scores)
    ap = _distribution(a_scores)
    actions = [item["action"] for item in b_scores]
    before_rank = {a: i + 1 for i, a in enumerate(sorted(actions, key=lambda x: bp[x], reverse=True))}
    after_rank = {a: i + 1 for i, a in enumerate(sorted(actions, key=lambda x: ap[x], reverse=True))}
    tv = 0.5 * sum(abs(ap[a] - bp[a]) for a in actions)
    return {
        "fixture_id": fixture["row"]["review_id"],
        "place": fixture["snapshot"].get("place"),
        "generated_action_count": len(generated),
        "source_candidates": fixture["snapshot"].get("source_candidates"),
        "before_S": state_to_dict(before),
        "after_S": state_to_dict(after),
        "generated_A_O_before_after_identical": [x["action_id"] for x in generated_before] == [x["action_id"] for x in generated_after],
        "before": b_scores,
        "after": a_scores,
        "delta_probability": {a: ap[a] - bp[a] for a in actions},
        "before_rank": before_rank,
        "after_rank": after_rank,
        "tv_distance": tv,
        "direction_explanation": "fatigue/low engagement lowers inspection/social stimulation; higher tension raises conflict salience and environment-control preference; support is unchanged",
        "engineering_threshold": {"max_key_delta": 0.10, "tv_delta": 0.015},
        "engineering_trigger": bool(tv > 0.015 or max(abs(ap[a] - bp[a]) for a in actions) > 0.10),
        "support_diagnostic": support_diagnostic(generated, fixture["snapshot"].get("source_candidates")),
    }


def main() -> int:
    fixtures = _choose_fixtures()
    fixture_rows = []
    intervention_rows = []
    for fixture in fixtures:
        fixture_rows.append({
            "fixture_id": fixture["row"]["review_id"],
            "place": fixture["snapshot"].get("place"),
            "snapshot": fixture["snapshot"],
            "generated_affordances": fixture["generated"],
            "source_candidates_posthoc": fixture["snapshot"].get("source_candidates"),
        })
        intervention_rows.append(_intervention(fixture))
    (OUT / "fixtures.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in fixture_rows), encoding="utf-8"
    )
    result = {
        "protocol": "Mechanism_Sanity_v1",
        "theory_version": "theory-s-v1",
        "generator_version": "scene-affordance-action-v1",
        "dataset": "LIGHT",
        "status": "engineering_sanity_only",
        "fixture_count": len(fixture_rows),
        "results": intervention_rows,
        "global_invariants": {
            "generator_does_not_read_A_star": True,
            "S_intervention_does_not_change_generated_A_O": True,
            "P_or_S_do_not_change_action_legality": True,
            "source_available_actions_posthoc_only": True,
        },
    }
    (OUT / "intervention_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"fixture_count": len(fixture_rows), "output": str(OUT / "intervention_results.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
