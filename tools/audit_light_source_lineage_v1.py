#!/usr/bin/env python3
"""Read-only join of the pinned LIGHT pickle to its actor-local view."""
from __future__ import annotations

import hashlib
import argparse
import json
import pickle
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICKLE = ROOT / "outputs/external_assets_2026-09-06/LIGHT/light_data.pkl"
VIEW = ROOT / "02_实验/T0c_LIGHT/light_actor_local_full_v0.jsonl"
OUTPUT = ROOT / "outputs/research_reset_audit_20261006/source_join_v1.json"
EXPECTED_PICKLE = "7c83cf49818586db9999ea67a4a6ad087afbd91c26ed629a9f00e21d0b84058f"
EXPECTED_VIEW = "e6f214b91ed644b60543cf442fdae4255ff177d26a25fccd750ab5c7381ba195"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    return str(value or "").strip().casefold()


def raw_turn_for_step(episode: dict, step_index: int) -> int:
    physical = [i for i, action in enumerate(episode["action"])
                if action is not None and str(action).strip()]
    if not isinstance(step_index, int) or not 0 <= step_index < len(physical):
        raise AssertionError("physical step index out of range")
    return physical[step_index]


def check_row(row: dict, episode: dict) -> int:
    t = raw_turn_for_step(episode, row["target_step_index"])
    checks = ((row["source_O"] == episode["context"][t], "source_O/context mismatch"),
              (row["source_action_A_star"] == episode["action"][t], "gold/action mismatch"),
              (row["candidate_set_factual"] == episode["available_actions"][t], "candidates mismatch"),
              (norm(row["actor"]) == norm(episode["character"][t]), "actor mismatch"))
    for passed, message in checks:
        if not passed:
            raise ValueError(message)
    return t


def output_absent(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing existing output: {path}")


def output_does_not_cover_inputs(path: Path) -> None:
    out = path.resolve()
    for source in (PICKLE.resolve(), VIEW.resolve()):
        if out == source or out in source.parents:
            raise ValueError(f"output path equals or contains an input: {out}")


def synthetic_self_test() -> None:
    ep = {"action": [None, "look", "", "take key"],
          "context": [None, "O1", None, "O2"],
          "available_actions": [None, ["look"], None, ["take key", "leave"]],
          "character": [None, "Ada", None, "Ada"]}
    row = {"target_step_index": 1, "source_O": "O2", "source_action_A_star": "take key",
           "candidate_set_factual": ["take key", "leave"], "actor": " ada "}
    if check_row(row, ep) != 3:
        raise AssertionError("synthetic physical-to-raw mapping failed")
    wrong_index = (ep["context"][row["target_step_index"]], ep["action"][row["target_step_index"]],
                   ep["available_actions"][row["target_step_index"]])
    correct = (row["source_O"], row["source_action_A_star"], row["candidate_set_factual"])
    if wrong_index == correct:
        raise AssertionError("synthetic wrong raw-turn index was not rejected")
    bad = dict(row, source_action_A_star="wrong")
    try:
        check_row(bad, ep)
    except ValueError:
        pass
    else:
        raise AssertionError("synthetic field mismatch was not rejected")
    with tempfile.TemporaryDirectory() as d:
        occupied = Path(d) / "already.json"
        occupied.write_text("preserve", encoding="utf-8")
        try:
            output_absent(occupied)
        except FileExistsError:
            pass
        else:
            raise AssertionError("existing-output refusal was not tested")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run only the synthetic checks")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="exclusive JSON output path")
    args = parser.parse_args()
    synthetic_self_test()
    if args.self_test:
        print("synthetic_self_test: passed")
        return
    output_does_not_cover_inputs(args.output)
    output_absent(args.output)
    pickle_bytes = PICKLE.read_bytes()
    pickle_hash, view_hash = sha256_bytes(pickle_bytes), sha256(VIEW)
    if pickle_hash != EXPECTED_PICKLE:
        raise SystemExit(f"refusing to unpickle unexpected source SHA-256: {pickle_hash}")
    if view_hash != EXPECTED_VIEW:
        raise SystemExit(f"unexpected actor-local view SHA-256: {view_hash}")
    episodes = pickle.loads(pickle_bytes)
    counters = {"joined": 0, "same_turn_speech_nonempty": 0,
                "raw_turn_differs_from_physical_index": 0}
    seen: set[tuple[int, int, str]] = set()
    with VIEW.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            row = json.loads(line)
            episode_id = int(row["trajectory_id"].rsplit("-", 1)[1])
            t = check_row(row, episodes[episode_id])
            key = (episode_id, row["target_step_index"], norm(row["actor"]))
            if key in seen:
                raise ValueError(f"duplicate view key at line {line_no}")
            seen.add(key)
            counters["joined"] += 1
            counters["same_turn_speech_nonempty"] += bool(
                str(episodes[episode_id].get("speech", [None] * len(episodes[episode_id]["action"]))[t] or "").strip())
            counters["raw_turn_differs_from_physical_index"] += t != row["target_step_index"]
    code_paths = [Path(__file__), ROOT / "02_实验/T0c_LIGHT/export_replay.py",
                  ROOT / "02_实验/T0c_LIGHT/run_actor_local_history_gate_v0.py"]
    result = {"schema": "light_source_lineage_join_v1", "source_pickle": str(PICKLE.relative_to(ROOT)),
              "source_pickle_sha256": pickle_hash, "actor_local_view": str(VIEW.relative_to(ROOT)),
              "actor_local_view_sha256": view_hash, "code_sha256": {
                  str(p.relative_to(ROOT)): sha256(p) for p in code_paths},
              "episode_count": len(episodes), **counters,
              "all_rows_field_join_assertions_passed": True,
              "synthetic_self_test": "passed: correct mapping, wrong raw index rejected, field mismatch rejected, existing output rejected"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({**result, "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
