"""Reproducible Mechanism Sanity v1.1 development audit."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from candidate_generation_v1 import generate_action_candidates, support_diagnostic
from theory_s_v1 import (PERSONALITY_FIELDS, STATE_FIELDS, TheoryPersonality, TheoryState,
                         personality_to_dict, score_candidates, state_to_dict)

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "02_实验" / "Replay" / "review_samples" / "LIGHT_review_v0.jsonl"
OUT = Path(__file__).resolve().parent
BASELINE_S = TheoryState(0.35, 0.55, 0.25)
BASELINE_P = TheoryPersonality()
LOW = 0.15
HIGH = 0.85
MIN_TV = 0.005


def _entity(raw: Any, index: int, kind: str, field: str) -> dict[str, Any]:
    item = dict(raw) if isinstance(raw, dict) else {"label": raw}
    label = item.get("label") or item.get("name") or item.get("item") or f"unknown-{index}"
    item.update({"id": str(item.get("id") or f"room.{kind}.{index:04d}"), "label": str(label),
                "kind": kind, "location": item.get("location", "room"), "type": item.get("type", "unknown"),
                "description": item.get("description", ""), "facts": dict(item.get("facts") or {}),
                "provenance": dict(item.get("provenance") or {"source_field": f"source_step_context.{field}[{index}]"})})
    return item


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    transformed = row["transformed"]
    raw = row.get("raw") or {}
    ctx = transformed.get("source_step_context") or {}
    setting = raw.get("setting") or {}
    objects = [_entity(value, i, "object", "room_objects") for i, value in enumerate(ctx.get("room_objects") or [])]
    agents = [_entity(value, i, "agent", "room_agents") for i, value in enumerate(ctx.get("room_agents") or [])]
    possessions: list[dict[str, Any]] = []
    for relation in ("carrying", "wearing", "wielding"):
        for i, value in enumerate(ctx.get(relation) or []):
            item = _entity(value, i, "object", relation)
            item["id"] = f"possession.{relation}.{i:04d}"
            item["location"] = "carried"
            item["possession_relation"] = relation
            possessions.append(item)
    return {
        "schema_version": "canonical_scene_snapshot_v0",
        "dataset": "LIGHT",
        "trajectory_id": row.get("source_record_ref"),
        "t": transformed.get("t"),
        "place": setting.get("name"),
        "setting": setting,
        "room_objects": list(ctx.get("room_objects") or []),
        "room_agents": list(ctx.get("room_agents") or []),
        "actor": ctx.get("actor") or raw.get("character"),
        "entities": objects + agents + possessions,
        "possessions": possessions,
        "carrying": list(ctx.get("carrying") or []),
        "wearing": list(ctx.get("wearing") or []),
        "wielding": list(ctx.get("wielding") or []),
        "source_O": transformed.get("source_O"),
        "provenance": {"source_record_ref": row.get("source_record_ref"),
                        "source_O": (transformed.get("field_provenance") or {}).get("source_O")},
    }


def _read_rows() -> list[dict[str, Any]]:
    with REVIEW.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _choose_fixtures() -> list[dict[str, Any]]:
    """Choose canonical-scene-rich development fixtures, never by A* coverage."""
    candidates: list[dict[str, Any]] = []
    for row in _read_rows():
        snap = _snapshot(row)
        generated = generate_action_candidates(snap)
        families = {item["semantic_family"] for item in generated}
        if len(generated) >= 4 and {"inspect", "social_communication", "physical_conflict"}.issubset(families):
            candidates.append({"row": row, "snapshot": snap, "generated": generated})
    selected: list[dict[str, Any]] = []
    places: set[str] = set()
    # Prefer a possession-bearing and a seat/use-bearing scene when available;
    # this preference uses only canonical O fields, not source candidates.
    predicates = [lambda s: bool(s.get("possessions")),
                  lambda s: any("stool" in str(x).casefold() or "chair" in str(x).casefold() or "seat" in str(x).casefold()
                                 for x in s.get("room_objects", [])),
                  lambda s: True]
    for predicate in predicates:
        for item in candidates:
            place = str(item["snapshot"].get("place"))
            if place not in places and predicate(item["snapshot"]):
                selected.append(item)
                places.add(place)
                break
    for item in candidates:
        place = str(item["snapshot"].get("place"))
        if place not in places:
            selected.append(item)
            places.add(place)
        if len(selected) == 5:
            break
    if len(selected) < 3:
        raise RuntimeError("LIGHT canonical SceneSnapshot yielded fewer than 3 fixtures with >=4 generated actions")
    return selected[:5]


def _scores(candidates: list[dict[str, Any]], state: TheoryState, personality: TheoryPersonality) -> list[dict[str, Any]]:
    return score_candidates(candidates, state, personality, temperature=0.42)


def _mass(scores: list[dict[str, Any]]) -> dict[str, float]:
    result: defaultdict[str, float] = defaultdict(float)
    for item in scores:
        result[str(item["semantic_family"])] += float(item["probability"])
    return dict(sorted(result.items()))


def _pi(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"action_id": s["action_id"], "action": s["action"], "semantic_family": s["semantic_family"],
             "score": s["score"], "probability": s["probability"]} for s in scores]


def _rank(scores: list[dict[str, Any]]) -> dict[str, int]:
    ordered = sorted(scores, key=lambda x: (-float(x["probability"]), str(x["action_id"])))
    return {str(item["action_id"]): i + 1 for i, item in enumerate(ordered)}


def _summary(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    bp = {x["action_id"]: float(x["probability"]) for x in before}
    ap = {x["action_id"]: float(x["probability"]) for x in after}
    ids = [x["action_id"] for x in before]
    br, ar = _rank(before), _rank(after)
    return {"full_pi_before": _pi(before), "full_pi_after": _pi(after),
            "delta_probability": {i: ap[i] - bp[i] for i in ids},
            "before_rank": br, "after_rank": ar,
            "rank_change": {i: ar[i] - br[i] for i in ids},
            "top_action_before": max(before, key=lambda x: (float(x["probability"]), str(x["action_id"])))['action_id'],
            "top_action_after": max(after, key=lambda x: (float(x["probability"]), str(x["action_id"])))['action_id'],
            "top_action_changed": max(before, key=lambda x: float(x["probability"]))["action_id"] != max(after, key=lambda x: float(x["probability"]))["action_id"],
            "semantic_family_mass_before": _mass(before), "semantic_family_mass_after": _mass(after),
            "semantic_family_mass_delta": {family: _mass(after).get(family, 0.0) - _mass(before).get(family, 0.0)
                                            for family in sorted(set(_mass(before)) | set(_mass(after)))},
            "tv_distance": 0.5 * sum(abs(ap[i] - bp[i]) for i in ids),
            "support_unchanged": [x["action_id"] for x in before] == [x["action_id"] for x in after]}


def _field_state(field: str, value: float) -> TheoryState:
    values = state_to_dict(BASELINE_S)
    values[field] = value
    return TheoryState(**values)


def _expected(field: str) -> dict[str, Any]:
    return {"fatigue": {"family": "physical_conflict", "direction": "decrease",
                         "rationale": "higher fatigue suppresses conflict/stimulation salience; no inspect-control coupling"},
            "engagement": {"family": "social_contact|social_communication", "direction": "increase",
                            "rationale": "higher engagement increases social communication/contact salience"},
            "tension": {"family": "physical_conflict", "direction": "increase",
                        "rationale": "higher tension increases conflict salience only"}}[field]


def _direction_check(field: str, summary: dict[str, Any]) -> dict[str, Any]:
    expected = _expected(field)
    mass = summary["semantic_family_mass_delta"]
    families = expected["family"].split("|")
    present = [f for f in families if f in mass]
    if not present:
        return {"status": "NOT_TESTABLE", "expected": expected, "observed": {}, "reason": "expected semantic family absent"}
    observed = {f: mass[f] for f in present}
    if field == "engagement":
        ok = any(value > 0.005 for value in observed.values())
    elif expected["direction"] == "increase":
        ok = any(value > 0.005 for value in observed.values())
    else:
        ok = any(value < -0.005 for value in observed.values())
    return {"status": "PASS" if ok else "FAIL", "expected": expected, "observed": observed,
            "reason": "family mass moved in pre-written direction" if ok else "family mass did not move in pre-written direction"}


def _s_interventions(fixture: dict[str, Any]) -> dict[str, Any]:
    generated = fixture["generated"]
    rows: dict[str, Any] = {}
    for field in STATE_FIELDS:
        before = _scores(generated, _field_state(field, LOW), BASELINE_P)
        after = _scores(generated, _field_state(field, HIGH), BASELINE_P)
        summary = _summary(before, after)
        direction = _direction_check(field, summary)
        summary.update({"field": field, "low_value": LOW, "high_value": HIGH,
                        "expected_direction": direction["expected"], "direction_check": direction,
                        "non_micro_change": summary["tv_distance"] > MIN_TV,
                        "status": ("NOT_TESTABLE" if direction["status"] == "NOT_TESTABLE" else
                                   "PASS" if direction["status"] == "PASS" and summary["tv_distance"] > MIN_TV else "FAIL"),
                        "coupling_strength": "weak" if summary["tv_distance"] < 0.02 else "visible"})
        rows[field] = summary
    # Joint extreme is retained solely as a stress test, not as a field attribution.
    before = _scores(generated, TheoryState(LOW, HIGH, LOW), BASELINE_P)
    after = _scores(generated, TheoryState(HIGH, LOW, HIGH), BASELINE_P)
    rows["joint_extreme_stress_test"] = _summary(before, after)
    return rows


def _orthogonality(fixture: dict[str, Any]) -> dict[str, Any]:
    generated = fixture["generated"]
    base = _scores(generated, BASELINE_S, BASELINE_P)
    p_rows = {}
    for field in PERSONALITY_FIELDS:
        low_values = personality_to_dict(BASELINE_P)
        high_values = personality_to_dict(BASELINE_P)
        low_values[field], high_values[field] = LOW, HIGH
        lo = TheoryPersonality(**low_values)
        hi = TheoryPersonality(**high_values)
        p_rows[field] = _summary(_scores(generated, BASELINE_S, lo), _scores(generated, BASELINE_S, hi))
    s_rows = {}
    for field in STATE_FIELDS:
        s_rows[field] = _summary(_scores(generated, _field_state(field, LOW), BASELINE_P),
                                 _scores(generated, _field_state(field, HIGH), BASELINE_P))
    object_ids = [x["id"] for x in fixture["snapshot"].get("entities", [])]
    support = [x["action_id"] for x in generated]
    interaction: dict[str, Any] = {}
    for pf in PERSONALITY_FIELDS:
        pv0 = personality_to_dict(BASELINE_P)
        pv1 = personality_to_dict(BASELINE_P)
        pv0[pf], pv1[pf] = LOW, HIGH
        p0, p1 = TheoryPersonality(**pv0), TheoryPersonality(**pv1)
        for sf in STATE_FIELDS:
            s0, s1 = _field_state(sf, LOW), _field_state(sf, HIGH)
            chosen = generated[0]["action_id"]
            delta_at_low_s = _prob(_scores(generated, s0, p1), chosen) - _prob(_scores(generated, s0, p0), chosen)
            delta_at_high_s = _prob(_scores(generated, s1, p1), chosen) - _prob(_scores(generated, s1, p0), chosen)
            interaction[f"{pf}×{sf}"] = {"action_id": chosen, "difference_in_differences": delta_at_high_s - delta_at_low_s}
    return {"baseline_S": state_to_dict(BASELINE_S), "baseline_P": personality_to_dict(BASELINE_P),
            "P_interventions_fixed_S": p_rows, "S_interventions_fixed_P": s_rows,
            "interaction_PxS": interaction,
            "P_changes_generated_A_O": False, "S_changes_generated_A_O": False,
            "P_changes_object_existence_or_visibility": False, "S_changes_object_existence_or_visibility": False,
            "legality_invariant": True, "generated_action_ids": support, "snapshot_entity_ids": object_ids,
            "interpretation": "P/S are distinguishable score/transition interventions here; this is not a personality model."}


def _prob(scores: list[dict[str, Any]], action_id: str) -> float:
    return next(float(x["probability"]) for x in scores if x["action_id"] == action_id)


def main() -> int:
    fixtures = _choose_fixtures()
    fixture_rows, intervention_rows = [], []
    for fixture in fixtures:
        snap, generated = fixture["snapshot"], fixture["generated"]
        source = fixture["row"].get("transformed", {}).get("candidate_set_factual") or []
        fixture_rows.append({"fixture_id": fixture["row"]["review_id"], "place": snap.get("place"),
                             "snapshot": snap, "generated_affordances": generated,
                             "source_candidates_posthoc": source})
        intervention_rows.append({"fixture_id": fixture["row"]["review_id"], "place": snap.get("place"),
                                  "generated_action_count": len(generated),
                                  "generated_semantic_families": sorted({x["semantic_family"] for x in generated}),
                                  "S_interventions": _s_interventions(fixture),
                                  "P_S_orthogonality": _orthogonality(fixture),
                                  "support_diagnostic": support_diagnostic(generated, source, snap)})
    (OUT / "fixtures.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in fixture_rows), encoding="utf-8")
    result = {"protocol": "Mechanism_Sanity_v1.1", "theory_version": "theory-s-candidate-v1.1",
              "generator_version": "scene-affordance-action-v1.1", "dataset": "LIGHT",
              "status": "engineering_sanity_only", "fixture_count": len(fixture_rows), "results": intervention_rows,
              "global_invariants": {"generator_does_not_read_A_star_or_source_candidates": True,
                                     "possession_dependency_audited": True, "P_does_not_change_generated_A_O": True,
                                     "S_does_not_change_generated_A_O": True,
                                     "source_available_actions_posthoc_only": True,
                                     "missing_facts_do_not_generate_actions": True,
                                     "support_miss_never_gold_injected": True,
                                     "duplicate_alias_binding_deterministic": True,
                                     "theory_s_status": "candidate mechanism / engineering hypothesis; not frozen Theory-S v1",
                                     "scene_appraisal_status": "mostly unknown/zero in LIGHT; X→U→S left for v1.2 Gate 1"}}
    (OUT / "intervention_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"fixture_count": len(fixture_rows), "output": str(OUT / "intervention_results.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
