#!/usr/bin/env python3
"""Audit a small LIGHT processed-pickle slice without semantic inference."""
from __future__ import annotations
import argparse, hashlib, json, pickle
from pathlib import Path

def inspect(e: dict, index: int) -> dict:
    actions = e.get("action", ())
    physical = [i for i, a in enumerate(actions) if a is not None and str(a).strip()]
    candidates = [i for i, c in enumerate(e.get("available_actions", ())) if c]
    contexts = e.get("context", ())
    characters = e.get("character", ())
    return {
        "episode_index": index,
        "turn_count": len(actions),
        "physical_action_turns": physical,
        "physical_action_count": len(physical),
        "candidate_turn_count": len(candidates),
        "actor_values": sorted(set(characters)),
        "context_count_matches_turns": len(contexts) == len(actions),
        "persona_count": len(e.get("agents", ())),
        "setting_fields": sorted(e.get("setting", {}).keys()),
        "has_room_objects": bool(e.get("room_objects")),
        "has_room_agents": bool(e.get("room_agents")),
        "future_leakage_static_check": "unresolved",
        "semantic_audit_required": True,
        "notes": [
            "context is actor-specific text supplied by the processed LIGHT record",
            "setting/room graph is source environment and is not copied into W or O wholesale",
            "only non-null physical action turns are eligible for ReplayRecord export",
        ],
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pickle_path", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    data = pickle.loads(args.pickle_path.read_bytes())
    reports = [inspect(e, i) for i, e in enumerate(data[: args.limit])]
    out = {
        "dataset": "LIGHT",
        "source_revision": "facebookresearch/LIGHT@main-shallow-2026-09-06",
        "source_file": args.pickle_path.name,
        "source_sha256": hashlib.sha256(args.pickle_path.read_bytes()).hexdigest(),
        "requested_episode_limit": args.limit,
        "episodes_audited": len(reports),
        "episodes_with_physical_action": sum(r["physical_action_count"] > 0 for r in reports),
        "physical_action_total": sum(r["physical_action_count"] for r in reports),
        "candidate_turn_total": sum(r["candidate_turn_count"] for r in reports),
        "reports": reports,
        "admission": "restricted_dev_only",
        "export_policy": "Eligible physical turns may be exported; dialogue-only turns are not A* action steps.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("episodes_audited", "episodes_with_physical_action", "physical_action_total", "candidate_turn_total")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
