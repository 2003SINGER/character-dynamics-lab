#!/usr/bin/env python3
"""One-command dev runner for the rank-matched raw-feature probe v1.

This is an orchestration/dev-smoke tool, not a formal LIGHT evaluation.  All
world/scene/transition/appraisal definitions remain frozen in Replay modules.
"""
from __future__ import annotations
import argparse, hashlib, json, random, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent.parent / "Replay"))
sys.path.insert(0, str(HERE.parent.parent / "T0c_LIGHT"))
import replay_features_v1 as rf
import replay_probe_v1 as probe
import scene_snapshot_v0 as scene
import transition_appraisal_v0 as ta
import run_compiled_semantics_v0 as base

ETA = 0.35
SEED = 20260907

def load_records(path, limit):
    out=[]
    for rec in base.iter_records(path):
        if rec.get("source_dataset") != "LIGHT" or rec.get("source_episode_context",{}).get("quarantine"):
            continue
        if any(s.get("source_action_A_star") and isinstance(s.get("candidate_set_factual"),list) and base.gold_index(s["candidate_set_factual"],s["source_action_A_star"]) is not None for s in rec.get("steps",[])):
            out.append(rec)
        if len(out)>=limit: break
    return out

def state_rows(rec, rules):
    snaps=[scene.compile_light_step(rec,s) for s in rec.get("steps",[])]
    previous={"theory":0.0,"activity":0.0,"support":0.0}; rows=[]
    for i, step in enumerate(rec.get("steps",[])):
        action=step.get("source_action_A_star"); candidates=step.get("candidate_set_factual")
        if not isinstance(candidates,list) or not candidates or action is None: continue
        gold=base.gold_index(candidates,action)
        if gold is None: continue
        cur=snaps[i]; prior=snaps[i-1] if i else cur; prev_action=rec.get("steps",[])[i-1].get("source_action_A_star") if i else None
        x=ta.appraise_transition(prior,cur,prev_action) if i else {"positive_conduciveness":0.0}
        events=ta.diff_scene_snapshots(prior,cur) if i else []
        support=1.0 if ta.expected_effect(prev_action,prior) else 0.0
        signals={"theory":float(x.get("positive_conduciveness",0.0)),"activity":float(bool(events)),"support":support}
        states={k:previous[k] for k in previous}
        compiled=[rf.vectorize(rf.compile_candidate_v1(c,cur,rules)[0]) for c in candidates]
        for kind in previous:
            rows.append({"trajectory_id":str(rec["trajectory_id"]),"horizon_index":i,"t":int(step["t"]),"features":compiled,"gold_index":gold,"state":states[kind],"kind":kind})
        for kind in previous: previous[kind]=previous[kind]+ETA*(signals[kind]-previous[kind])
    return rows

def split(records):
    ids=[str(r["trajectory_id"]) for r in records]; rng=random.Random(SEED); rng.shuffle(ids)
    n=len(ids); ntr=max(1,int(round(n*.70))); nv=max(1,int(round(n*.15))) if n>=3 else 0
    return {"train":ids[:ntr],"validation":ids[ntr:ntr+nv],"test":ids[ntr+nv:]}, ids

def pick_lambda(train, valid, stateful):
    best=None
    for lam in probe.LAMBDA_GRID:
        model=(probe.fit_stateful(train,lam) if stateful else probe.fit_no_state(train,lam))
        score=probe.evaluate(model,valid)
        key=(score,-lam)
        if best is None or key<best[0]: best=(key,lam,model,score)
    return best[1],best[2],best[3]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("output",type=Path); ap.add_argument("--max-trajectories",type=int,default=50); ap.add_argument("--dev-smoke",action="store_true"); args=ap.parse_args()
    rules=json.loads((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8")); records=load_records(args.replay,args.max_trajectories)
    split_map, shuffled=split(records); by_id={str(r["trajectory_id"]):r for r in records}; all_rows={k:[] for k in ("activity","support","theory")}
    for rec in records:
        for row in state_rows(rec,rules): all_rows[row["kind"]].append(row)
    def rows_for(kind, part): return [r for r in all_rows[kind] if r["trajectory_id"] in split_map[part]]
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"split.json").write_text(json.dumps({"seed":SEED,"trajectory_order":shuffled,"partitions":split_map,"dev_smoke":args.dev_smoke},indent=2)+"\n",encoding="utf8")
    models={}; summary={}
    # Fit a common base feature normalization and lambda selection per condition.
    for kind in ("activity","support","theory"):
        tr,va,te=rows_for(kind,"train"),rows_for(kind,"validation"),rows_for(kind,"test")
        lam,model,val_nll=pick_lambda(tr,va,True)
        models[f"{kind}_s"] = model; summary[f"{kind}-S"]={"train_rows":len(tr),"validation_rows":len(va),"test_rows":len(te),"lambda":lam,"validation_nll":val_nll,"test_nll":probe.evaluate(model,te)}
    tr,va,te=rows_for("theory","train"),rows_for("theory","validation"),rows_for("theory","test")
    lam,model,val_nll=pick_lambda(tr,va,False); models["retrained_no_s"]=model; summary["retrained-no-S"]={"lambda":lam,"validation_nll":val_nll,"test_nll":probe.evaluate(model,te)}
    theory=models["theory_s"]
    summary["Theory zeroed-S"]={"test_nll":probe.evaluate(theory,te,lambda r:0.0)}
    pools={}
    for r in te: pools.setdefault(r["horizon_index"],[]).append(r["state"])
    rng=random.Random(SEED); perm={k:list(v) for k,v in pools.items()}
    for vals in perm.values(): rng.shuffle(vals)
    counters={k:0 for k in perm}
    def perm_state(r):
        k=r["horizon_index"]; i=counters[k]; counters[k]+=1; return perm[k][i%len(perm[k])] if perm.get(k) else 0.0
    summary["Theory permuted-S"]={"test_nll":probe.evaluate(theory,te,perm_state),"permutation_seed":SEED}
    summary["uniform"]={"test_nll":float(np.mean([np.log(len(r["features"])) for r in te]))}
    (args.output/"feature_stats.json").write_text(json.dumps({"feature_version":rf.FEATURE_VERSION,"feature_names":list(rf.FEATURE_NAMES),"normalization":"train-only means/std; zero std=1"},indent=2)+"\n",encoding="utf8")
    for name,model in models.items(): (args.output/f"{name}.model.json").write_text(json.dumps(model,indent=2)+"\n",encoding="utf8")
    manifest={"schema_version":"character_dynamics_rank_matched_probe_manifest_v1","probe_version":probe.PROBE_VERSION,"feature_version":rf.FEATURE_VERSION,"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"semantic_rules_sha256":hashlib.sha256((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_bytes()).hexdigest(),"eta":ETA,"seed":SEED,"dev_smoke":args.dev_smoke,"frozen_boundaries":["ReplayRecord","SceneSnapshot","transition compiler","expected-effect","appraisal X","candidate support","gold boundary"],"learnable_parameters":["theta","w"],"temperature":1.0}
    (args.output/"training_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8"); (args.output/"dev_comparison.summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
