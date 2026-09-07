#!/usr/bin/env python3
"""Run 3b: robustness of same-horizon permutation effects across assignments."""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve()
sys.path.insert(0,str(HERE.parent))
import run_frozen_base_incremental_v1 as run2
import run_rank_matched_probe_v1 as runner

KINDS=("activity","support","theory")
BASE_SEED=20260909

def donors_for(rows, seed):
    by_h={}
    for r in rows: by_h.setdefault(r["horizon_index"],{})[r["trajectory_id"]]=r
    donor={}
    for h,states in by_h.items():
        ids=list(states); rng=random.Random(seed + int(h)); rng.shuffle(ids)
        if len(ids)<2: continue
        for recipient, donor_id in zip(ids, ids[1:]+ids[:1]):
            if recipient==donor_id: raise RuntimeError("self donor generated")
            donor[(recipient,h)]=states[donor_id]["state"]
    return donor

def nll(model, row, state):
    p=run2.predict_frozen(model["theta"],model["w"],model["means"],model["scales"],row["features"],state)
    return -math.log(max(float(p[int(row["gold_index"])]),1e-300))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("run1",type=Path); ap.add_argument("run2_output",type=Path); ap.add_argument("output",type=Path); ap.add_argument("--assignments",type=int,default=512); args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()): raise RuntimeError(f"output directory is non-empty: {args.output}")
    run1_manifest=json.loads((args.run1/"training_manifest.json").read_text(encoding="utf8")); run2_summary=json.loads((args.run2_output/"run2_summary.json").read_text(encoding="utf8"));
    if hashlib.sha256(args.replay.read_bytes()).hexdigest()!=run1_manifest["source_replay_sha256"]: raise RuntimeError("replay SHA does not match Run 1")
    split=run2_summary["manifest"]["split"]; rules=json.loads((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8")); records=runner.load_records(args.replay,100000)
    all_rows={k:[] for k in KINDS}
    for rec in records:
        for row in runner.state_rows(rec,rules): all_rows[row["kind"]].append(row)
    test_ids=set(split["test"]); rows={k:[r for r in all_rows[k] if r["trajectory_id"] in test_ids] for k in KINDS}
    models={}
    for k in KINDS:
        raw=json.loads((args.run2_output/f"{k}_s_frozen.model.json").read_text(encoding="utf8")); models[k]={"theta":np.asarray(raw["weights_theta"],float),"w":np.asarray(raw["weights_w"],float),"means":np.asarray(raw["means"],float),"scales":np.asarray(raw["scales"],float)}
    summary={}; raw_deltas={k:[] for k in KINDS}
    for i in range(args.assignments):
        seed=BASE_SEED+i
        for kind in KINDS:
            te=rows[kind]; model=models[kind]; donor=donors_for(te,seed)
            paired=[r for r in te if (r["trajectory_id"],r["horizon_index"]) in donor]
            correct=sum(nll(model,r,r["state"]) for r in paired)
            perm=sum(nll(model,r,donor[(r["trajectory_id"],r["horizon_index"])]) for r in paired)
            raw_deltas[kind].append((perm-correct)/len(paired))
    for kind in KINDS:
        a=np.asarray(raw_deltas[kind],float)
        summary[kind]={"assignments":args.assignments,"paired_rows":len([r for r in rows[kind] if (r["trajectory_id"],r["horizon_index"]) in donors_for(rows[kind],BASE_SEED)]),"seed_first":BASE_SEED,"seed_last":BASE_SEED+args.assignments-1,"mean":float(a.mean()),"median":float(np.median(a)),"ci95_percentile":[float(np.percentile(a,2.5)),float(np.percentile(a,97.5))],"fraction_positive":float(np.mean(a>0)),"min":float(a.min()),"max":float(a.max()),"values":a.tolist()}
    args.output.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":"character_dynamics_permutation_assignment_robustness_manifest_v1","run":"Run 3b","fitted":False,"source_run2":str(args.run2_output),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"split":split,"assignment_unit":"same-horizon cyclic no-self donor mapping","assignment_count":args.assignments,"base_seed":BASE_SEED,"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"runner_sha256":hashlib.sha256(HERE.read_bytes()).hexdigest(),"numpy_version":np.__version__}
    (args.output/"permutation_robustness_summary.json").write_text(json.dumps({"manifest":manifest,"summary":summary},indent=2)+"\n",encoding="utf8")
    print(json.dumps({"manifest":manifest,"summary":{k:{x:v for x,v in val.items() if x!="values"} for k,val in summary.items()}},indent=2))

if __name__=="__main__": main()
