#!/usr/bin/env python3
"""Export eligible physical LIGHT turns as ReplayRecord v0 records."""
from __future__ import annotations
import argparse, hashlib, json, pickle
from pathlib import Path

def record(e: dict, idx: int, split_id: str) -> dict:
    actions = e["action"]
    steps = []
    for t, action in enumerate(actions):
        if action is None or not str(action).strip():
            continue
        actor = e.get("character", (None,) * len(actions))[t]
        context = e.get("context", (None,) * len(actions))[t]
        candidates = e.get("available_actions", (None,) * len(actions))[t]
        steps.append({
            "t": t,
            "source_O": context,
            "source_event": None,
            "source_action_A_star": action,
            "source_step_context": {
                "actor": actor,
                "speech": e.get("speech", (None,) * len(actions))[t],
                "emote": e.get("emote", (None,) * len(actions))[t],
                "room_objects": e.get("room_objects", (None,) * len(actions))[t],
                "room_agents": e.get("room_agents", (None,) * len(actions))[t],
                "carrying": e.get("carrying", (None,) * len(actions))[t],
                "wearing": e.get("wearing", (None,) * len(actions))[t],
                "wielding": e.get("wielding", (None,) * len(actions))[t],
            },
            "W": None,
            "state_label": None,
            "candidate_set_factual": list(candidates) if candidates else None,
            "candidate_set_expanded": None,
            "timestamp": None,
            "provenance": "observed",
            "provenance_detail": "Processed LIGHT record; actor-specific context and recorded action copied without semantic inference.",
            "field_provenance": {
                "source_O": {"kind": "observed", "source_ref": f"episode:{idx}:turn:{t}"},
                "source_action_A_star": {"kind": "observed", "source_ref": f"episode:{idx}:turn:{t}"},
                "candidate_set_factual": {"kind": "observed", "source_ref": f"episode:{idx}:turn:{t}:available_actions"},
            },
        })
    agents = e.get("agents", [])
    return {
        "trajectory_id": f"light::episode-{idx:05d}",
        "subject_id": None,
        "group_id": None,
        "split_id": split_id,
        "source_dataset": "LIGHT",
        "source_revision": "light-dialog-processed-small7.pkl",
        "source_record_id": f"episode:{idx}",
        "source_license": "LIGHT repository is MIT; processed data terms require separate review.",
        "persona_P": None,
        "source_episode_context": {
            "source_agents": agents,
            "source_persona": agents,
            "setting": e.get("setting"),
            "all_descriptions": e.get("all_descriptions"),
            "character_sequence": list(e.get("character", ())),
            "source_environment_fields": ["setting", "room_objects", "room_agents", "all_descriptions"],
            "observation_boundary": "Only context is used as actor-available O; environment fields remain source context.",
            "candidate_semantics": "Source-provided available-action list; relation to A^W/A^O unresolved.",
        },
        "steps": steps,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pickle_path", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--split-id", default="light_dev_2026-09-06")
    args = ap.parse_args()
    data = pickle.loads(args.pickle_path.read_bytes())
    selected = [(i, e) for i, e in enumerate(data[: args.limit]) if any(a is not None and str(a).strip() for a in e.get("action", ()))]
    records = [record(e, i, args.split_id) for i, e in selected]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "steps": sum(len(r["steps"]) for r in records), "source_sha256": hashlib.sha256(args.pickle_path.read_bytes()).hexdigest()}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
