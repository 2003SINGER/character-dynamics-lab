"""Run the renderer and real Sabre CLI on a clearly synthetic P5-shaped domain.

This checks DSL syntax/search integration only. Its output is never native-game
evidence and cannot satisfy an A1-A8 gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from tools.native_platform_v0.p5.bundle import load_bundle
from .model import PlannerSnapshot
from .runner import _allocate, _json, _source_hashes, _validate_search_revision
from .sabre import SEARCH_LIMITS, decode_plan, invoke_sabre, render_problem


ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).resolve().parent / "cases"
OUTPUT = ROOT / "02_实验/Planner_Adapter_Integration_v1/validation/runs"


def synthetic_snapshot(case_path: Path) -> PlannerSnapshot:
    raw = json.loads(case_path.read_text(encoding="utf-8"))
    bundle = load_bundle(raw)
    requirements = tuple((goal.constraint_id, goal.kind, goal.start, goal.deadline,
                          json.dumps(dict(goal.source), sort_keys=True, separators=(",", ":")))
                         for goal in bundle.goals if goal.hard)
    permissions = bundle.permissions
    cost_budget = min(2, int(permissions.get("cost_budget", 0)))
    allowed = set(permissions.get("world_opportunities", ()))
    route_available = (("main_passage", "open_main_passage", 2),
                       ("side_passage", "open_side_passage", 1))
    return PlannerSnapshot(
        scene_id="SYNTHETIC_NOT_NATIVE", bundle_id=bundle.bundle_id, bundle_version=bundle.version,
        minute=0, horizon=24, source_trace_sha256="synthetic", source_bundle_sha256="synthetic",
        renderer_version="offline-synthetic-preflight", route_open=(
            ("main_passage", False), ("side_passage", False)),
        route_available=tuple((route, action in allowed and cost <= cost_budget)
                              for route, action, cost in route_available),
        route_cost=(("main_passage", 2), ("side_passage", 1)),
        spent_cost=0, opportunity_count=0, opportunity_limit=1, cost_budget=cost_budget,
        actor_roles=("A", "B"), actor_rooms=(("A", "pickup"), ("B", "pickup")),
        actor_ready=(("A", True), ("B", True)),
        observation_evidence=(("A", "synthetic-observation", 0),
                             ("B", "synthetic-observation", 0)),
        scene_room_roles=(("pickup", "pickup"), ("side", "side"), ("porch", "porch")),
        scene_room_ids=(("pickup", 1), ("side", 2), ("porch", 3)),
        world_route_edges=(
            ("main_passage", "pickup", "porch", True, False),
            ("main_passage", "porch", "pickup", True, False),
            ("side_passage", "pickup", "side", True, False),
            ("side_passage", "side", "porch", True, False),
            ("side_passage", "porch", "side", True, False),
            ("side_passage", "side", "pickup", True, False)),
        task_bindings=(("A", "courier_supply", "1", "porch"),
                       ("B", "resident_parcel", "2", "porch")),
        known_exits=(),
        known_task_item_locations=(("A", "courier_supply", "pickup", False),
                                   ("B", "resident_parcel", "pickup", False)),
        world_item_location=(("courier_supply", "pickup"), ("resident_parcel", "pickup"),
                             ("note", None)),
        world_holders=(("courier_supply", None), ("resident_parcel", None), ("note", None)),
        social_target_visible=True,
        witnessed_events=(), known_held_items=(("A", ()), ("B", ())),
        hard_requirements=requirements,
        constraint_statuses=tuple((goal.constraint_id, "UNRESOLVED")
                                  for goal in bundle.goals if goal.hard),
        branches=tuple((branch.branch_id, branch.response, branch.storylet_id)
                       for branch in bundle.branches), projection_residuals=(
                           "synthetic preflight state; no live P5 scene or receipt"))


def run(cases: tuple[str, ...] = ("wide24.json", "tight12.json",
                                 "no-opportunity-budget.json", "no-world-permission.json")) -> dict:
    _validate_search_revision()
    results = []
    for name in cases:
        case_path = CASES / name
        run_dir = _allocate(OUTPUT, f"offline-sabre-{case_path.stem}")
        snapshot = synthetic_snapshot(case_path)
        problem = render_problem(snapshot)
        problem_path = run_dir / "synthetic.problem"
        problem_path.write_text(problem, encoding="utf-8")
        result = invoke_sabre(problem_path)
        decoded = decode_plan(result.get("plan_actions", []))
        artifact = {"schema": "planner-adapter-offline-sabre-preflight-v1",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "case": name, "evidence_class": "SYNTHETIC_DOMAIN_ONLY_NOT_NATIVE",
                    "search_config_id": "planner-adapter-sabre-r2",
                    "search_limits": dict(SEARCH_LIMITS),
                    "result": result, "decoded_plan": decoded,
                    "plan_is_not_execution_or_milestone_evidence": True}
        _json(run_dir / "result.json", artifact)
        source_hashes = _source_hashes()
        _json(run_dir / "provenance.json", {"case": str(case_path), "renderer": "integration-v1",
             "scene_id": "SYNTHETIC_NOT_NATIVE", "source_sha256": source_hashes,
             "search_config_id": "planner-adapter-sabre-r2",
             "search_limits": dict(SEARCH_LIMITS),
             "scoped_worktree_sha256": __import__("hashlib").sha256(json.dumps(
                 source_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
        results.append({**artifact, "run_dir": str(run_dir)})
    return {"schema": "planner-adapter-offline-sabre-preflight-suite-v1",
            "evidence_class": "SYNTHETIC_DOMAIN_ONLY_NOT_NATIVE", "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
