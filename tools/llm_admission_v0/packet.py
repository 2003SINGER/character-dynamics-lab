"""Lossless B0 rules export; never imports goals, search paths or old results."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from tools.open_adventure_planning_v0 import domain as d
from tools.open_adventure_v0.session import OpenAdventureSession

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "02_实验/LLM_Admission_v0"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def shared_rules() -> dict:
    # Merge only input aliases with identical predicates/effects/source. This
    # preserves every grounded action, without giving a solved goal or plan.
    grouped: dict[tuple, dict] = {}
    for op in d.OPERATORS:
        key = (op.name, op.preconditions, op.negative_preconditions,
               op.add_effects, op.delete_effects, op.source)
        row = grouped.setdefault(key, {
            "name": op.name, "pre": op.preconditions,
            "not_pre": op.negative_preconditions, "add": op.add_effects,
            "delete": op.delete_effects, "source": op.source, "variants": []})
        row["variants"].append({"command": op.command, "args": op.args})
    return {
        "schema": "oa-shared-rules-v0", "game_version": "Open Adventure 1.22",
        "game_source_commit": "e6160529e70a8c7a06b9a5f190d69aa35c4c62f5",
        "model_source_sha256": hashlib.sha256(Path(d.__file__).read_bytes()).hexdigest(),
        "rooms": d.ROOMS, "objects": d.OBJECTS, "dark_rooms": sorted(d.DARK_ROOMS),
        "initial_prior_facts": sorted(d.initial_state()),
        "initial_prior_label": "STATIC_MODEL_ASSUMPTION, not a live hidden-state query",
        "operator_groups": list(grouped.values()), "ground_operator_count": len(d.OPERATORS),
        "predicate_vocabulary": {
            "at": ["player or one of objects", "one room or CARRIED for objects"],
            "carrying": ["one of objects"],
            "lamp_on": [], "lamp_off": [], "grate_open": [], "grate_closed": [],
            "bridge": [], "unbridged": [],
        },
        "safety": "MODEL_POLICY_SAFETY: modeled dark-room travel requires carried lit lamp; conservative search restriction, not native action illegality.",
        "coverage": "14 rooms and 3 objects only; outside-region routes, other items, lamp energy, closing and random NPC evolution are not fully modeled.",
        "hidden_and_unknown": ["current NPC positions/flags", "PRNG cursor", "exact energy/closing state", "unaudited mechanisms"],
        "obligation_vocabulary": {
            "no_death_ever": "Hard trajectory obligation; checked from committed complete native output by independent verifier, not a State atom or proof from the planner.",
        },
        "native_process_audit": {
            "scope": "audited producer/consumer paths, not proof about every possible unaudited game mechanism",
            "dwarf": "Native seen/loc/oldloc and global dflag affect pursuit, blocking and attacks; randomized evolution; hidden running values not supplied.",
            "pirate": "Audited encounter reads current treasure/lamp/world progress, transfers treasure, resets pirate location/seen. These paths expose current game progress/latches, not a certified general autobiographical event-to-social-behavior model.",
            "sources": ["upstream/main.c:231-474", "upstream/advent.h:179-245", "upstream/main.c:1199-1247"],
        },
    }


def expand_packet(packet: dict) -> list[dict]:
    return [dict(name=g["name"], args=v["args"], command=v["command"],
                 preconditions=g["pre"], negative_preconditions=g["not_pre"],
                 add_effects=g["add"], delete_effects=g["delete"], source=g["source"])
            for g in packet["operator_groups"] for v in g["variants"]]


def assert_lossless(packet: dict) -> None:
    actual = sorted(canonical(x) for x in expand_packet(packet))
    expected = sorted(canonical(asdict(op)) for op in d.OPERATORS)
    if actual != expected or canonical(packet["initial_prior_facts"]) != canonical(sorted(d.initial_state())):
        raise ValueError("information packet does not round-trip frozen B0 rules")


def prepare() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "shared_rules.json"
    if target.exists():
        raise FileExistsError("do not overwrite a published information packet")
    packet = shared_rules()
    assert_lossless(packet)
    target.write_bytes(canonical(packet) + b"\n")
    session = OpenAdventureSession(runs_root=OUT / "runs")
    history = []
    try:
        opening = session.reset({"experiment_config_version": "luna-admission-visible-bootstrap-v0"})
        for command in ("n", "seed 20261014"):
            result = session.step(command, controller="admission-bootstrap",
                                  decision_source="fixed observation preparation, not model decision")
            if not result.input_boundary_reached or result.error or result.timed_out:
                raise RuntimeError("incomplete native bootstrap")
            history.append({"command": command, "visible_response": result.observation})
        visible = {"schema": "oa-visible-start-v0", "opening": opening,
                   "history": history, "current_observation": session.observe(),
                   "native_ledger": str(session.log_path),
                   "observed": ["player at START", "seed request acknowledged"],
                   "unconfirmed": ["all object/map priors not yet inspected in this episode"],
                   "input_budget": 80, "search_budget": {"expansions_per_call": 10000, "seconds_per_call": 10, "total_seconds": 120},
                   "created_at_utc": datetime.now(timezone.utc).isoformat()}
        (OUT / "visible_start.json").write_bytes(canonical(visible) + b"\n")
    finally:
        session.close()
    manifest = {"shared_rules_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "visible_start_sha256": hashlib.sha256((OUT / "visible_start.json").read_bytes()).hexdigest(),
                "lossless_operator_instances": len(expand_packet(packet)),
                "rule_groups": len(packet["operator_groups"]),
                "sources": sorted(set(op.source for op in d.OPERATORS)),
                "excluded_inputs": ["GOALS mapping", "walkthrough", "B0 plans/results", "live hidden game state"],
                "game_model_permission": "same static source-derived priors as B0; no full-world current truth"}
    (OUT / "packet_manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    prepare()
