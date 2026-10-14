"""Strict, non-repairing admission of a tested model's semantic candidate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.open_adventure_planning_v0.domain import ROOMS, OBJECTS, CARRIED
from tools.open_adventure_planning_v0.search import Goal
from tools.open_adventure_planning_v0 import domain as d

SOURCE_IDS = {"movement": d.MOVE_SOURCE, "items": d.ITEM_SOURCE,
              "lamp": d.LAMP_SOURCE, "grate": d.GRATE_SOURCE,
              "rod": d.WAVE_SOURCE,
              "native_output_verifier": "committed complete native output; trajectory no-death verifier"}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def parse_candidate(raw: str) -> dict:
    # No extracting favorable JSON fragments from prose, repair or retry.
    candidate = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(candidate, dict) or candidate.get("schema") != "oa-author-binding-v0":
        raise ValueError("expected one oa-author-binding-v0 JSON object")
    return candidate


def _atom(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(x, str) for x in value):
        raise ValueError("atom must be an array of strings")
    atom = tuple(value)
    if atom[0] == "at" and len(atom) == 3:
        if atom[1] == "player" and atom[2] in ROOMS:
            return atom
        if atom[1] in OBJECTS and atom[2] in (*ROOMS, CARRIED):
            return atom
    elif atom[0] == "carrying" and len(atom) == 2 and atom[1] in OBJECTS:
        return atom
    elif len(atom) == 1 and atom[0] in (
        "lamp_on", "lamp_off", "grate_open", "grate_closed", "bridge", "unbridged"):
        return atom
    raise ValueError(f"unregistered atom: {atom}")


def compile_candidate(candidate: dict) -> Goal:
    """Compile actual returned atoms; never fill or select a Goal ID."""
    payload = candidate.get("goal")
    if not isinstance(payload, dict):
        raise ValueError("missing goal object")
    required, forbidden = payload.get("required"), payload.get("forbidden")
    if not isinstance(required, list) or not isinstance(forbidden, list):
        raise ValueError("required/forbidden must both be arrays")
    req = frozenset(_atom(x) for x in required)
    neg = frozenset(_atom(x) for x in forbidden)
    if not req or req & neg:
        raise ValueError("empty or contradictory goal")
    return Goal(req, neg)


def validate_e(candidate: dict) -> dict:
    # Independent acceptance, never included in the model input.
    goal = compile_candidate(candidate)
    expected = frozenset({("at", "player", "WESTBANK"), ("bridge",),
                          ("carrying", "keys"), ("carrying", "lamp"), ("lamp_on",)})
    missing = sorted(expected - goal.required)
    extra = sorted(goal.required - expected)
    obligations = candidate.get("trajectory_obligations", [])
    no_death = (isinstance(obligations, list) and any(
        isinstance(row, dict) and row.get("kind") == "no_death_ever"
        and row.get("hard") is True for row in obligations))
    residuals = candidate.get("residual_obligations")
    bindings = candidate.get("bindings")
    errors = []
    if missing: errors.append("missing original author goal atoms")
    if extra or goal.forbidden: errors.append("unsupported additional hard constraints")
    if not no_death: errors.append("missing hard no-death trajectory obligation")
    if not isinstance(bindings, list) or not bindings or any(
        not isinstance(row, dict) or not row.get("capability_sources")
        for row in bindings): errors.append("missing binding source provenance")
    elif any(not isinstance(row["capability_sources"], list) or any(
        source not in SOURCE_IDS for source in row["capability_sources"])
             for row in bindings): errors.append("unregistered capability source")
    if not isinstance(residuals, list): errors.append("residuals must be explicit")
    elif any(not isinstance(row, dict) or row.get("hard") is not False
             for row in residuals): errors.append("unresolved hard requirement")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "missing_atoms": missing, "additional_atoms": extra,
            "no_death_ever": no_death,
            "compiled_actual_goal": {"required": sorted(goal.required), "forbidden": sorted(goal.forbidden)},
            "controller_added_atoms": [], "gold_not_sent_to_model": True}


def execute_validated(raw_path: Path) -> dict:
    raw = raw_path.read_text(encoding="utf-8")
    candidate = parse_candidate(raw)
    report = validate_e(candidate)
    if report["status"] != "PASS":
        raise ValueError("model binding rejected; no native execution")
    audit = json.loads((raw_path.parent / "audit.json").read_text(encoding="utf-8"))
    if (audit.get("classification") != "AGENT_CONFOUNDED" or audit.get("tool_calls_observed")
        or {row.get("model") for row in audit.get("actual_turn_context", [])} != {"gpt-6-luna"}
        or audit.get("assistant_final_outputs") != [raw]):
        raise ValueError("runtime model/output provenance rejected; no native execution")
    # Imports after validation. No GOALS lookup or substitute goal.
    from tools.open_adventure_planning_v0.execute import run_episode
    return run_episode("E", scenario="clean", execute_native=True,
                       external_goal=compile_candidate(candidate),
                       external_goal_text=candidate.get("author_text", "model-generated author binding"),
                       runs_root=Path(__file__).resolve().parents[2] / "02_实验/LLM_Admission_v0/runs")
