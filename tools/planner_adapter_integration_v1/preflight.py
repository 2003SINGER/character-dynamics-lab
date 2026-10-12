"""Reproducible parser/search preflight for the isolated integration-v1 domain.

This deliberately uses a synthetic snapshot shaped only from the closed P5
room/task/route schema. It is not a native run, a world reachability claim, or
an execution receipt. The parent runner owns live evidence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .model import PlannerSnapshot
from . import sabre


def _fixture(*, deadline: int, permissions: bool) -> PlannerSnapshot:
    data = {
        "scene_id": "synthetic-p5-schema-only", "bundle_id": "synthetic-preflight",
        "bundle_version": 1, "minute": 0, "horizon": 24,
        "source_trace_sha256": "synthetic-not-native", "source_bundle_sha256": "synthetic-not-native",
        "renderer_version": "p5-sabre-causal-domain-v1",
        "route_open": (("main_passage", False), ("side_passage", False)),
        "route_available": (("main_passage", permissions), ("side_passage", permissions)),
        "route_cost": (("main_passage", 2), ("side_passage", 1)),
        "spent_cost": 0, "opportunity_count": 0, "opportunity_limit": 1,
        "cost_budget": 2, "actor_roles": ("A", "B"),
        "actor_rooms": (("A", "pickup"), ("B", "pickup")),
        "actor_ready": (("A", True), ("B", True)),
        "observation_evidence": (("A", "synthetic-O-only", 0), ("B", "synthetic-O-only", 0)),
        "scene_room_roles": (("pickup", "pickup"), ("side", "side"), ("porch", "porch")),
        "scene_room_ids": (("pickup", 41), ("side", 42), ("porch", 43)),
        "world_route_edges": (
            ("main_passage", "pickup", "porch", True, False),
            ("main_passage", "porch", "pickup", False, True),
            ("side_passage", "pickup", "side", True, False),
            ("side_passage", "side", "pickup", False, True),
            ("side_passage", "side", "porch", True, False),
            ("side_passage", "porch", "side", False, False),
        ),
        "task_bindings": (("A", "courier_supply", "51", "porch"),
                          ("B", "resident_parcel", "52", "porch")),
        "known_exits": (),
        "known_task_item_locations": (("A", "courier_supply", "pickup", False),
                                       ("B", "resident_parcel", "pickup", False)),
        "world_item_location": (("courier_supply", "pickup"),
                                ("resident_parcel", "pickup"), ("note", None)),
        "world_holders": (("courier_supply", None), ("resident_parcel", None), ("note", None)),
        "social_target_visible": True,
        "witnessed_events": (), "known_held_items": (("A", ()), ("B", ())),
        "constraint_statuses": (("delivery_a", "UNRESOLVED"), ("delivery_b", "UNRESOLVED"),
                                ("response", "UNRESOLVED"), ("order", "UNRESOLVED")),
        "branches": (), "projection_residuals": (),
    }
    sources = (
        ("delivery_a", {"kind": "event_by_deadline", "event": "delivery_settled",
                         "filters": {"actor": "A", "item": "courier_supply"},
                         "min_count": 1, "max_count": 1, "start": 0, "deadline": deadline}),
        ("delivery_b", {"kind": "event_by_deadline", "event": "delivery_settled",
                         "filters": {"actor": "B", "item": "resident_parcel"},
                         "min_count": 1, "max_count": 1, "start": 0, "deadline": deadline}),
        ("response", {"kind": "event_by_deadline", "event": "note_response",
                       "filters": {"actor": "A", "recipient": "B", "item": "note"},
                       "min_count": 1, "max_count": 1, "start": 0, "deadline": deadline}),
        ("order", {"kind": "event_order",
                   "before": {"event": "delivery_settled", "filters": {"actor": "A", "item": "courier_supply"}},
                   "after": {"event": "note_response", "filters": {"actor": "A", "recipient": "B", "item": "note"}},
                   "order": "PHYSICAL_TIME", "start": 0, "deadline": deadline}),
    )
    data["hard_requirements"] = tuple(
        (clause_id, source["kind"], source["start"], source["deadline"],
         json.dumps(source, sort_keys=True, separators=(",", ":")))
        for clause_id, source in sources
    )
    return PlannerSnapshot(**data)


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def run(output_dir: Path, cases: tuple[str, ...] = ("positive-24", "negative-no-opportunity")) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=False)
    results = []
    case_specs = {"positive-24": (24, True), "negative-no-opportunity": (24, False),
                  "positive-tight-12": (12, True)}
    if not cases or any(case not in case_specs for case in cases):
        raise ValueError("cases must be a nonempty subset of the registered synthetic preflight cases")
    for case_id in cases:
        horizon, permissions = case_specs[case_id]
        case = output_dir / case_id
        case.mkdir()
        snapshot = _fixture(deadline=horizon, permissions=permissions)
        problem_path = case / "problem.txt"
        problem_path.write_text(sabre.render_problem(snapshot, deadline=horizon), encoding="utf-8")
        result = sabre.invoke_sabre(problem_path)
        (case / "stdout.txt").write_text(str(result.get("stdout", "")), encoding="utf-8")
        (case / "stderr.txt").write_text(str(result.get("stderr", "")), encoding="utf-8")
        decoded = sabre.decode_plan(result.get("plan_actions", []))
        (case / "result.json").write_text(json.dumps({
            "status": result.get("status"), "native_result": result.get("native_result"),
            "returncode": result.get("returncode"), "nodes_visited": result.get("nodes_visited"),
            "nodes_generated": result.get("nodes_generated"),
            "elapsed_native_ms": result.get("elapsed_native_ms"), "decoded": decoded,
            "command": result.get("command"), "synthetic_input_only": True,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results.append({"case": case_id, "status": result.get("status"),
                        "native_result": result.get("native_result"),
                        "problem_sha256": _hash(problem_path)})
    manifest = {"schema": "integration-v1-sabre-preflight-v1",
                "purpose": "synthetic parser/search preflight only; no native execution evidence",
                "source_files": {},
                "search_limits": sabre.SEARCH_LIMITS, "cases": results}
    model_path = Path(__file__).with_name("model.py")
    manifest["source_files"] = {str(Path(__file__).name): _hash(Path(__file__)),
                                str(Path(sabre.__file__).name): _hash(Path(sabre.__file__)),
                                str(model_path.name): _hash(model_path)}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                               encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cases", nargs="+", choices=("positive-24", "negative-no-opportunity",
                                                           "positive-tight-12"),
                        default=("positive-24", "negative-no-opportunity"))
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir.resolve(), tuple(args.cases)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
