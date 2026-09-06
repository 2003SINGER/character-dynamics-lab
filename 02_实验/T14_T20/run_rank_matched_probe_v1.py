#!/usr/bin/env python3
"""One-command dev runner for the rank-matched raw-feature probe v1.

This is an orchestration/dev-smoke tool, not a formal LIGHT evaluation.  All
world/scene/transition/appraisal definitions remain frozen in Replay modules.
"""
from __future__ import annotations
import argparse, hashlib, json, random, sys, csv
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
        cur=snaps[i]; prior=snaps[i-1] if i else cur; prev_action=rec.get("steps",[])[i-1].get("source_action_A_star") if i else None
        x=ta.appraise_transition(prior,cur,prev_action) if i else {"positive_conduciveness":0.0}
        events=ta.diff_scene_snapshots(prior,cur) if i else []
        support=1.0 if ta.expected_effect(prev_action,prior) else 0.0
        signals={"theory":float(x.get("positive_conduciveness",0.0)),"activity":float(bool(events)),"support":support}
        # Decision boundary: evolve S_t from X_t before admitting A*_t.
        for kind in previous: previous[kind]=previous[kind]+ETA*(signals[kind]-previous[kind])
        action=step.get("source_action_A_star"); candidates=step.get("candidate_set_factual")
        if not isinstance(candidates,list) or not candidates or action is None: continue
        gold=base.gold_index(candidates,action)
        if gold is None: continue
        states={k:previous[k] for k in previous}
        compiled=[rf.vectorize(rf.compile_candidate_v1(c,cur,rules)[0]) for c in candidates]
        for kind in previous:
            rows.append({"trajectory_id":str(rec["trajectory_id"]),"horizon_index":i,"t":int(step["t"]),"features":compiled,"gold_index":gold,"state":states[kind],"kind":kind})
    return rows

def split(records):
    ids=[str(r["trajectory_id"]) for r in records]; rng=random.Random(SEED); rng.shuffle(ids)
    n=len(ids); ntr=max(1,int(round(n*.70))); nv=max(1,int(round(n*.15))) if n>=3 else 0
    return {"train":ids[:ntr],"validation":ids[ntr:ntr+nv],"test":ids[ntr+nv:]}, ids

def pick_lambda(train, valid, stateful, means, scales, condition):
    best=None; trials=[]
    for lam in probe.LAMBDA_GRID:
        model=(probe.fit_stateful(train,lam,means,scales) if stateful else probe.fit_no_state(train,lam,means,scales))
        score=probe.evaluate(model,valid)
        trials.append({"condition":condition,"lambda":lam,"train_rows":len(train),"validation_rows":len(valid),"train_data_nll":model["optimizer"]["final_data_nll"],"train_regularized_objective":model["optimizer"]["final_objective"],"validation_nll":score,"weights_theta":model["weights_theta"],"weights_w":model["weights_w"],"optimizer":model["optimizer"],"optimization_history":model["optimization_history"]})
        key=(score,-lam)
        if best is None or key<best[0]: best=(key,lam,model,score)
    for t in trials: t["selected"]=bool(t["lambda"]==best[1])
    return best[1],best[2],best[3],trials

def metrics(model, rows, state_override=None):
    if not rows: return {"nll":None}
    nll=0.; ranks=[]; top=0
    for r in rows:
        p=probe.predict(model,r["features"],r.get("state",0.) if state_override is None else state_override(r)); order=sorted(range(len(p)),key=lambda i:p[i],reverse=True); rank=order.index(int(r["gold_index"]))+1; nll-=np.log(max(p[int(r["gold_index"])],1e-300)); ranks.append(rank); top+=rank==1
    return {"nll":float(nll/len(rows)),"bits_per_action":float(nll/len(rows)/np.log(2)),"top1":top/len(rows),"mrr":float(np.mean([1/r for r in ranks])),"mean_rank":float(np.mean(ranks)),"rows":len(rows)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("output",type=Path); ap.add_argument("--max-trajectories",type=int,default=50); ap.add_argument("--dev-smoke",action="store_true"); ap.add_argument("--overwrite-dev-run",action="store_true"); args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite_dev_run:
        raise RuntimeError(f"output directory is non-empty; choose a new path or pass --overwrite-dev-run: {args.output}")
    rules=json.loads((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8")); records=load_records(args.replay,args.max_trajectories)
    split_map, shuffled=split(records); by_id={str(r["trajectory_id"]):r for r in records}; all_rows={k:[] for k in ("activity","support","theory")}
    for rec in records:
        for row in state_rows(rec,rules): all_rows[row["kind"]].append(row)
    keys=lambda kind: [(r["trajectory_id"],r["horizon_index"],r["t"],r["gold_index"],r["features"]) for r in all_rows[kind]]
    assert keys("activity")==keys("support")==keys("theory"), "condition rows/features diverged"
    assert all(np.isfinite(np.asarray(r["features"],float)).all() for r in all_rows["theory"]), "non-finite feature"
    def rows_for(kind, part): return [r for r in all_rows[kind] if r["trajectory_id"] in split_map[part]]
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"split.json").write_text(json.dumps({"seed":SEED,"trajectory_order":shuffled,"partitions":split_map,"dev_smoke":args.dev_smoke},indent=2)+"\n",encoding="utf8")
    models={}; summary={}; all_trials=[]
    common_train=[r for r in all_rows["theory"] if r["trajectory_id"] in split_map["train"]]
    _, _, means, scales = probe._design(common_train)
    raw_all=np.asarray([x for r in common_train for x in r["features"]],float); raw_stds=raw_all.std(0); zero=[n for n,s in zip(rf.FEATURE_NAMES,raw_stds) if s==0.0]
    (args.output/"feature_stats.json").write_text(json.dumps({"feature_version":rf.FEATURE_VERSION,"feature_names":list(rf.FEATURE_NAMES),"dimension":len(rf.FEATURE_NAMES),"means":means.tolist(),"raw_stds":raw_stds.tolist(),"applied_scales":scales.tolist(),"zero_variance_features":zero,"train_candidate_count":sum(len(r["features"]) for r in common_train),"train_decision_count":len(common_train),"missing_value_count":0,"nonfinite_value_count":0,"replacement_policy":"fail-fast; no replacements"},indent=2)+"\n",encoding="utf8")
    # Fit a common base feature normalization and lambda selection per condition.
    for kind in ("activity","support","theory"):
        tr,va,te=rows_for(kind,"train"),rows_for(kind,"validation"),rows_for(kind,"test")
        lam,model,val_nll,trials=pick_lambda(tr,va,True,means,scales,kind); all_trials.extend(trials)
        models[f"{kind}_s"] = model; summary[f"{kind}-S"]={"train_rows":len(tr),"validation_rows":len(va),"dev_holdout_rows":len(te),"lambda":lam,"validation_nll":val_nll,"dev_holdout_nll":probe.evaluate(model,te)}
    tr,va,te=rows_for("theory","train"),rows_for("theory","validation"),rows_for("theory","test")
    lam,model,val_nll,trials=pick_lambda(tr,va,False,means,scales,"retrained-no-S"); all_trials.extend(trials); models["retrained_no_s"]=model; summary["retrained-no-S"]={"lambda":lam,"validation_nll":val_nll,"dev_holdout_nll":probe.evaluate(model,te)}
    theory=models["theory_s"]
    summary["Theory zeroed-S"]={"dev_holdout_nll":probe.evaluate(theory,te,lambda r:0.0)}
    by_h={}
    for r in te: by_h.setdefault(r["horizon_index"],{}).setdefault(r["trajectory_id"],r["state"])
    rng=random.Random(SEED); donor_map={}; perm_rows=[]
    for h, states in by_h.items():
        tids=list(states); rng.shuffle(tids)
        if len(tids)>1:
            rotated=tids[1:]+tids[:1]
            for recipient, donor in zip(tids,rotated):
                donor_map[(recipient,h)]=states[donor]
                perm_rows.append({"trajectory_id":recipient,"horizon_index":h,"donor_trajectory_id":donor,"donor_state":states[donor],"seed":SEED})
    (args.output/"permutation_map.jsonl").write_text("".join(json.dumps(x)+"\n" for x in perm_rows),encoding="utf8")
    paired=[r for r in te if (r["trajectory_id"],r["horizon_index"]) in donor_map]
    summary["Theory permuted-S"]={"dev_holdout_nll":probe.evaluate(theory,paired,lambda r:donor_map[(r["trajectory_id"],r["horizon_index"])]),"permutation_seed":SEED,"eligible_paired_rows":len(paired)}
    summary["uniform"]={"dev_holdout_nll":float(np.mean([np.log(len(r["features"])) for r in te]))}
    summary["diagnostics"]={"Activity-S":metrics(models["activity_s"],rows_for("activity","test")),"ActionSupport-S":metrics(models["support_s"],rows_for("support","test")),"Theory-S":metrics(theory,te),"Theory zeroed-S":metrics(theory,te,lambda r:0.0),"Theory permuted-S":metrics(theory,paired,lambda r:donor_map[(r["trajectory_id"],r["horizon_index"])]),"paired_intervention_rows":len(paired)}
    (args.output/"lambda_sweep.json").write_text(json.dumps(all_trials,indent=2)+"\n",encoding="utf8")
    hist_dir=args.output/"optimization_history"; hist_dir.mkdir(exist_ok=True)
    trial_dir=args.output/"optimization_trials"; trial_dir.mkdir(exist_ok=True)
    for trial in all_trials:
        safe=str(trial["lambda"]).replace(".","p"); (trial_dir/f"{trial['condition']}.lambda_{safe}.json").write_text(json.dumps(trial,indent=2)+"\n",encoding="utf8"); (hist_dir/f"{trial['condition']}.lambda_{safe}.jsonl").write_text("\n".join(json.dumps(x) for x in trial["optimization_history"])+"\n",encoding="utf8")
    for name,model in models.items(): (args.output/f"{name}.model.json").write_text(json.dumps(model,indent=2)+"\n",encoding="utf8")
    with (args.output/"learned_weights.csv").open("w",newline="",encoding="utf8") as fh:
        w=csv.writer(fh); w.writerow(["condition","feature","theta","w"])
        for name,model in models.items():
            for feature,theta,wgt in zip(rf.FEATURE_NAMES,model["weights_theta"],model["weights_w"]): w.writerow([name,feature,theta,wgt])
    md=["# Learned weights (development diagnostic)",""]
    for name,model in models.items():
        md += [f"## {name}","","| feature | theta | state interaction w |","|---|---:|---:|"]
        md += [f"| {f} | {t:.8g} | {w:.8g} |" for f,t,w in zip(rf.FEATURE_NAMES,model["weights_theta"],model["weights_w"])] + [""]
    (args.output/"learned_weights.md").write_text("\n".join(md),encoding="utf8")
    manifest={"schema_version":"character_dynamics_rank_matched_probe_manifest_v1","probe_version":probe.PROBE_VERSION,"feature_version":rf.FEATURE_VERSION,"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"semantic_rules_sha256":hashlib.sha256((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_bytes()).hexdigest(),"eta":ETA,"seed":SEED,"dev_smoke":args.dev_smoke,"frozen_boundaries":["ReplayRecord","SceneSnapshot","transition compiler","expected-effect","appraisal X","candidate support","gold boundary"],"learnable_parameters":["theta","w"],"temperature":1.0}
    manifest.update({"evaluation_status":"development_only","formal_test":False,"split_seed":SEED,"permutation_seed":SEED,"optimizer_seed":None,"optimizer_deterministic":True,"lambda_grid":list(probe.LAMBDA_GRID),"selection_rule":"minimum validation NLL; ties choose larger lambda","initialization":"zeros","trajectory_counts":{"total":len(records),"train":len(split_map["train"]),"validation":len(split_map["validation"]),"dev_holdout":len(split_map["test"])},"row_counts":{k:len(v) for k,v in all_rows.items()}})
    (args.output/"training_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8"); (args.output/"dev_comparison.summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
