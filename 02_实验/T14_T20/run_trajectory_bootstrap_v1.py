#!/usr/bin/env python3
"""Run 3: trajectory-level paired bootstrap for frozen-base Run 2."""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys, time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve()
sys.path.insert(0,str(HERE.parent))
import run_frozen_base_incremental_v1 as run2
import run_rank_matched_probe_v1 as runner
import replay_probe_v1 as probe

SEED=20260908
KINDS=("activity","support","theory")

def nll(model, row, state):
    p=run2.predict_frozen(model["theta"],model["w"],model["means"],model["scales"],row["features"],state)
    return -math.log(max(float(p[int(row["gold_index"])]),1e-300))

def trajectory_bootstrap(rows, values, seed=SEED, replicates=2000):
    """Bootstrap pooled row-level mean from trajectory-level resampling."""
    groups={}
    for row, value in zip(rows, values): groups.setdefault(row["trajectory_id"], []).append(float(value))
    tids=sorted(groups); sums=np.asarray([sum(groups[t]) for t in tids],float); counts=np.asarray([len(groups[t]) for t in tids],float)
    rng=np.random.default_rng(seed); picks=rng.integers(0,len(tids),size=(replicates,len(tids)))
    boot=sums[picks].sum(axis=1)/counts[picks].sum(axis=1)
    point=float(sums.sum()/counts.sum())
    return {"point_estimate":point,"bootstrap_mean":float(boot.mean()),"ci95_percentile":[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))],"fraction_positive":float(np.mean(boot>0)),"trajectories":len(tids),"rows":int(counts.sum()),"replicates":replicates,"seed":seed}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("run1",type=Path); ap.add_argument("run2_output",type=Path); ap.add_argument("output",type=Path); ap.add_argument("--replicates",type=int,default=2000); args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()): raise RuntimeError(f"output directory is non-empty: {args.output}")
    run1_manifest=json.loads((args.run1/"training_manifest.json").read_text(encoding="utf8")); run2_summary=json.loads((args.run2_output/"run2_summary.json").read_text(encoding="utf8"));
    if hashlib.sha256(args.replay.read_bytes()).hexdigest()!=run1_manifest["source_replay_sha256"]: raise RuntimeError("replay SHA does not match Run 1")
    split=run2_summary["manifest"]["split"]; rules=json.loads((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8")); records=runner.load_records(args.replay,100000)
    all_rows={k:[] for k in KINDS}
    for rec in records:
        for row in runner.state_rows(rec,rules): all_rows[row["kind"]].append(row)
    test_ids=set(split["test"]); rows={k:[r for r in all_rows[k] if r["trajectory_id"] in test_ids] for k in KINDS}
    models={k:json.loads((args.run2_output/f"{k}_s_frozen.model.json").read_text(encoding="utf8")) for k in KINDS}
    for k in KINDS:
        models[k]={"theta":np.asarray(models[k]["weights_theta"],float),"w":np.asarray(models[k]["weights_w"],float),"means":np.asarray(models[k]["means"],float),"scales":np.asarray(models[k]["scales"],float)}
    summary={}; maps={}
    for kind in KINDS:
        te=rows[kind]; by_h={}
        for r in te: by_h.setdefault(r["horizon_index"],{})[r["trajectory_id"]]=r
        donor={}
        for h,states in by_h.items():
            for recipient,donor_id in run2.cyclic_donors(states).items(): donor[(recipient,h)]=states[donor_id]["state"]
        paired=[r for r in te if (r["trajectory_id"],r["horizon_index"]) in donor]; model=models[kind]
        correct=[nll(model,r,r["state"]) for r in paired]; zero=[nll(model,r,0.0) for r in paired]; perm=[nll(model,r,donor[(r["trajectory_id"],r["horizon_index"])]) for r in paired]
        # Base no-S is represented by zeroed state in the same paired rows.
        deltas={"zero_minus_correct":trajectory_bootstrap(paired,[z-c for z,c in zip(zero,correct)],SEED,args.replicates),"perm_minus_correct":trajectory_bootstrap(paired,[p-c for p,c in zip(perm,correct)],SEED+1,args.replicates)}
        summary[kind]={"paired_rows":len(paired),"deltas":deltas}
    args.output.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":"character_dynamics_trajectory_bootstrap_manifest_v1","run":"Run 3","fitted":False,"source_run2":str(args.run2_output),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"split":split,"bootstrap_unit":"trajectory_id","replicates":args.replicates,"seed":SEED,"condition_count":len(KINDS),"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"runner_sha256":hashlib.sha256(HERE.read_bytes()).hexdigest(),"numpy_version":np.__version__}
    (args.output/"bootstrap_summary.json").write_text(json.dumps({"manifest":manifest,"summary":summary},indent=2)+"\n",encoding="utf8")
    print(json.dumps({"manifest":manifest,"summary":summary},indent=2))

if __name__=="__main__": main()
