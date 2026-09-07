#!/usr/bin/env python3
"""Run 1b interventions against frozen full-refit LIGHT models.

No fitting occurs here.  Rows, split, features and state definitions are
reconstructed with the existing frozen runner; only S values are replaced at
evaluation time.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, random, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import run_rank_matched_probe_v1 as runner
import replay_probe_v1 as probe

SEED = runner.SEED
KINDS = ("activity", "support", "theory")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("model_run", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--max-trajectories", type=int, default=100000)
    args = ap.parse_args()
    started = time.time()
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError(f"output directory is non-empty: {args.output}")
    rules = json.loads((HERE.parent.parent / "T0c_LIGHT" / "compiled_semantics_v1.json").read_text(encoding="utf8"))
    records = runner.load_records(args.replay, args.max_trajectories)
    by_id = {str(r["trajectory_id"]): r for r in records}
    all_rows = {k: [] for k in KINDS}
    for rec in records:
        for row in runner.state_rows(rec, rules):
            all_rows[row["kind"]].append(row)
    split = json.loads((args.model_run / "split.json").read_text(encoding="utf8"))["partitions"]
    test_ids = set(split["test"])
    rows = {k: [r for r in all_rows[k] if r["trajectory_id"] in test_ids] for k in KINDS}
    models = {k: json.loads((args.model_run / f"{k}_s.model.json").read_text(encoding="utf8")) for k in KINDS}

    def donors_for(kind):
        by_h = {}
        for r in rows[kind]:
            by_h.setdefault(r["horizon_index"], {})[r["trajectory_id"]] = r
        donor = {}
        map_rows = []
        for h, states in by_h.items():
            mapping = runner.cyclic_donors(list(states), SEED)
            for recipient, donor_id in mapping.items():
                donor[(recipient, h)] = states[donor_id]["state"]
                map_rows.append({"kind": kind, "trajectory_id": recipient,
                                 "horizon_index": h, "t": states[recipient]["t"],
                                 "original_state": states[recipient]["state"],
                                 "donor_trajectory_id": donor_id,
                                 "donor_state": states[donor_id]["state"], "seed": SEED})
        return donor, map_rows

    summary = {}
    map_rows = []
    for kind in KINDS:
        model = models[kind]
        donor, entries = donors_for(kind)
        map_rows.extend(entries)
        paired = [r for r in rows[kind] if (r["trajectory_id"], r["horizon_index"]) in donor]
        correct = probe.evaluate(model, paired)
        zero = probe.evaluate(model, paired, lambda r: 0.0)
        perm = probe.evaluate(model, paired, lambda r, d=donor: d[(r["trajectory_id"], r["horizon_index"])])
        summary[f"{kind}-S"] = {
            "dev_holdout_rows": len(rows[kind]), "eligible_paired_rows": len(paired),
            "correct_nll": correct, "zeroed_nll": zero, "permuted_nll": perm,
            "zeroed_minus_correct_nll": zero - correct,
            "permuted_minus_correct_nll": perm - correct,
            "zeroed_minus_correct_bits": (zero - correct) / np.log(2),
            "permuted_minus_correct_bits": (perm - correct) / np.log(2),
            "correct_metrics": runner.metrics(model, paired),
            "zeroed_metrics": runner.metrics(model, paired, lambda r: 0.0),
            "permuted_metrics": runner.metrics(model, paired, lambda r, d=donor: d[(r["trajectory_id"], r["horizon_index"])]),
            "state_nonzero_fraction": float(np.mean([r["state"] != 0.0 for r in rows[kind]])),
        }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "intervention_summary.json").write_text(json.dumps({
        "schema_version": "character_dynamics_rank_matched_intervention_manifest_v1",
        "source_model_run": str(args.model_run), "source_replay_sha256": hashlib.sha256(args.replay.read_bytes()).hexdigest(),
        "split": split, "seed": SEED, "fitted": False, "summary": summary,
        "duration_seconds": time.time() - started,
    }, indent=2) + "\n", encoding="utf8")
    (args.output / "permutation_map.jsonl").write_text("".join(json.dumps(x) + "\n" for x in map_rows), encoding="utf8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
