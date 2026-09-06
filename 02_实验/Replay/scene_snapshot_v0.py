"""Canonical, source-preserving scene snapshot for external ReplayRecords.

This is a projection layer only: it does not promote LIGHT fields to W or A^O.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    yield from (data if isinstance(data, list) else [data])


def object_id(label: str) -> str:
    slug = "-".join(TOKEN_RE.findall(label.casefold())) or "object"
    return "light.object." + slug


def compile_light_step(rec: dict, step: dict) -> dict:
    ctx = step.get("source_step_context") or {}
    episode = rec.get("source_episode_context") or {}
    setting = episode.get("setting") or {}
    descriptions = episode.get("all_descriptions") or {}
    objects = []
    for label in ctx.get("room_objects") or []:
        objects.append({
            "id": object_id(str(label)),
            "label": label,
            "description": descriptions.get(label),
            "state": {},
            "affordances": [],
            "affordance_status": "not_projected",
        })
    agents = [{"id": "light.agent." + str(a).casefold().replace(" ", "-"),
               "label": a} for a in (ctx.get("room_agents") or [])]
    return {
        "schema_version": "canonical_scene_snapshot_v0",
        "dataset": "LIGHT",
        "trajectory_id": rec.get("trajectory_id"),
        "t": step.get("t"),
        "place": setting.get("name"),
        "setting": setting,
        "objects": objects,
        "agents": agents,
        "actor": ctx.get("actor"),
        "actor_inventory": {
            "carrying": ctx.get("carrying") or [],
            "wearing": ctx.get("wearing") or [],
            "wielding": ctx.get("wielding") or [],
        },
        "actor_observation": step.get("source_O"),
        "source_candidates": step.get("candidate_set_factual"),
        "provenance": {
            "source_record_id": rec.get("source_record_id"),
            "source_step": f"{rec.get('source_record_id')}:{step.get('t')}",
            "source_replay_sha256": None,
            "world_projection_status": "deferred",
            "observation_projection_status": "actor_context_preserved",
            "candidate_status": "observed_source_only_not_A_O",
        },
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    digest = sha256(args.replay)
    rows = []
    for rec in iter_records(args.replay):
        if rec.get("source_dataset") != "LIGHT":
            continue
        for step in rec.get("steps", []):
            row = compile_light_step(rec, step)
            row["provenance"]["source_replay_sha256"] = digest
            rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in rows), encoding="utf-8")
    print(json.dumps({"snapshot_count": len(rows), "output": str(args.output), "source_replay_sha256": digest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
