#!/usr/bin/env python3
"""Run 2: frozen-base incremental probe for the LIGHT development split.

The no-S theta, normalization and split are read from Run 1 artifacts.  Only
the state interaction vector w is optimized for each condition/lambda.
"""
from __future__ import annotations
import argparse, csv, datetime, hashlib, json, math, platform, random, sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent.parent / "Replay"))
sys.path.insert(0, str(HERE.parent.parent / "T0c_LIGHT"))
import replay_features_v1 as rf
import replay_probe_v1 as probe
import run_rank_matched_probe_v1 as runner

SEED = runner.SEED
KINDS = ("activity", "support", "theory")

def row_identity(r):
    return (r["trajectory_id"], r["horizon_index"], r["t"], r["gold_index"], r["features"])

def predict_frozen(theta, w, means, scales, features, state):
    x = (np.asarray(features, float) - means) / scales
    z = x @ (theta + float(state) * w); z -= z.max()
    p = np.exp(z); return p / p.sum()

def evaluate_frozen(model, rows, state_override=None):
    nll = 0.0
    for r in rows:
        s = r.get("state", 0.0) if state_override is None else state_override(r)
        p = predict_frozen(model["theta"], model["w"], model["means"], model["scales"], r["features"], s)
        nll -= math.log(max(float(p[int(r["gold_index"])]), 1e-300))
    return float(nll / len(rows))

def metrics_frozen(model, rows, state_override=None):
    ranks=[]; nll=0.; top=0
    for r in rows:
        s = r.get("state", 0.0) if state_override is None else state_override(r)
        p = predict_frozen(model["theta"], model["w"], model["means"], model["scales"], r["features"], s)
        order = sorted(range(len(p)), key=lambda i: float(p[i]), reverse=True)
        rank = order.index(int(r["gold_index"])) + 1
        nll -= math.log(max(float(p[int(r["gold_index"])]), 1e-300)); ranks.append(rank); top += rank == 1
    return {"nll": nll/len(rows), "bits_per_action": nll/len(rows)/np.log(2), "top1": top/len(rows),
            "mrr": float(np.mean([1/r for r in ranks])), "mean_rank": float(np.mean(ranks)), "rows": len(rows)}

def stratified(model, rows, state_override=None):
    groups={}
    for r in rows: groups.setdefault(str(len(r["features"]) if len(r["features"]) < 5 else "5+"), []).append(r)
    return {k: metrics_frozen(model, v, state_override) for k,v in sorted(groups.items())}

def fit_w(rows, theta, means, scales, l2):
    sets=[]; ys=[]; states=[]
    for r in rows:
        sets.append((np.asarray(r["features"], float)-means)/scales); ys.append(int(r["gold_index"])); states.append(float(r["state"]))
    d = sets[0].shape[1]
    def fg(w):
        loss=0.; g=np.zeros_like(w)
        for x,s,y in zip(sets,states,ys):
            z=x @ (theta + s*w); z -= z.max(); p=np.exp(z); p /= p.sum(); target=np.zeros(len(p)); target[y]=1
            loss -= np.log(max(p[y],1e-300)); g += s*((p-target) @ x)
        reg=.5*l2*np.dot(w,w)
        return loss/len(sets)+reg, g/len(sets)+l2*w
    history=[]
    def cb(w):
        obj,grad=fg(w); reg=.5*l2*np.dot(w,w)
        history.append({"iteration":len(history)+1,"objective":float(obj),"data_nll":float(obj-reg),"l2_penalty":float(reg),"gradient_norm":float(np.linalg.norm(grad)),"w_norm":float(np.linalg.norm(w))})
    result=minimize(lambda w: fg(w), np.zeros(d), jac=True, method="L-BFGS-B", callback=cb, options={"maxiter":1000,"gtol":1e-8})
    obj,grad=fg(result.x); reg=.5*l2*np.dot(result.x,result.x)
    return {"theta":theta.copy(),"w":result.x.copy(),"means":means.copy(),"scales":scales.copy(),"lambda":l2,
            "optimization_history":history,"optimizer":{"method":"L-BFGS-B","max_iter":1000,"gtol":1e-8,"initialization":"zeros","deterministic":True,"success":bool(result.success),"status":int(result.status),"message":str(result.message),"iterations":int(result.nit),"function_evaluations":int(result.nfev),"gradient_evaluations":int(getattr(result,"njev",-1)),"final_objective":float(obj),"final_data_nll":float(obj-reg),"final_l2_penalty":float(reg),"final_gradient_norm":float(np.linalg.norm(grad))}}

def cyclic_donors(tids):
    ids=list(tids); rng=random.Random(SEED); rng.shuffle(ids)
    return {} if len(ids)<2 else dict(zip(ids, ids[1:]+ids[:1]))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("model_run",type=Path); ap.add_argument("output",type=Path); ap.add_argument("--max-trajectories",type=int,default=100000); args=ap.parse_args()
    started=time.time()
    if args.output.exists() and any(args.output.iterdir()): raise RuntimeError(f"output directory is non-empty: {args.output}")
    model_run=args.model_run; run_manifest=json.loads((model_run/"training_manifest.json").read_text(encoding="utf8")); split=json.loads((model_run/"split.json").read_text(encoding="utf8"))["partitions"]
    if hashlib.sha256(args.replay.read_bytes()).hexdigest() != run_manifest["source_replay_sha256"]: raise RuntimeError("replay SHA does not match Run 1 manifest")
    base_json=json.loads((model_run/"retrained_no_s.model.json").read_text(encoding="utf8")); theta=np.asarray(base_json["weights_theta"],float); w0=np.asarray(base_json["weights_w"],float); means=np.asarray(base_json["means"],float); scales=np.asarray(base_json["scales"],float)
    if np.any(w0 != 0): raise RuntimeError("Run 1 no-S model has nonzero w")
    rules=json.loads((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8")); records=runner.load_records(args.replay,args.max_trajectories)
    all_rows={k:[] for k in KINDS}
    for rec in records:
        for row in runner.state_rows(rec,rules): all_rows[row["kind"]].append(row)
    identities=[row_identity(r) for r in all_rows["activity"]]
    if not (identities == [row_identity(r) for r in all_rows["support"]] == [row_identity(r) for r in all_rows["theory"]]): raise RuntimeError("condition row identities diverged")
    if len(records) != run_manifest["trajectory_counts"]["total"] or any(len(all_rows[k]) != run_manifest["row_counts"][k] for k in KINDS): raise RuntimeError("reconstructed rows do not match Run 1")
    parts={k:{p:[r for r in all_rows[k] if r["trajectory_id"] in set(split[p])] for p in ("train","validation","test")} for k in KINDS}
    base_model={"theta":theta,"w":np.zeros_like(theta),"means":means,"scales":scales}
    base_nll=evaluate_frozen(base_model,parts["theory"]["test"])
    base_ref=probe.evaluate(base_json,parts["theory"]["test"])
    max_diff=0.
    for r in parts["theory"]["test"]:
        p0=predict_frozen(theta,np.zeros_like(theta),means,scales,r["features"],r["state"]); p1=np.asarray(probe.predict(base_json,r["features"],r["state"])); max_diff=max(max_diff,float(np.max(np.abs(p0-p1))))
    if abs(base_nll-base_ref)>1e-12 or max_diff>1e-12: raise RuntimeError(f"zero-w equivalence failed: nll diff={base_nll-base_ref}, p diff={max_diff}")
    models={}; summary={}; trials=[]
    for kind in KINDS:
        tr,va,te=parts[kind]["train"],parts[kind]["validation"],parts[kind]["test"]
        best=None
        for lam in probe.LAMBDA_GRID:
            model=fit_w(tr,theta,means,scales,lam); val=evaluate_frozen(model,va)
            trial={"condition":kind,"lambda":lam,"train_rows":len(tr),"validation_rows":len(va),"train_data_nll":model["optimizer"]["final_data_nll"],"train_regularized_objective":model["optimizer"]["final_objective"],"validation_nll":val,"w_norm":float(np.linalg.norm(model["w"])),"weights_w":model["w"].tolist(),"optimizer":model["optimizer"],"optimization_history":model["optimization_history"]}
            trials.append(trial); key=(val,-lam)
            if best is None or key<best[0]: best=(key,lam,model,val)
        lam,model,val=best[1],best[2],best[3]; models[kind]=model
        donor={}; by_h={}
        for r in te: by_h.setdefault(r["horizon_index"],{})[r["trajectory_id"]]=r
        for h,states in by_h.items():
            for rec,don in cyclic_donors(states).items(): donor[(rec,h)]=states[don]["state"]
        paired=[r for r in te if (r["trajectory_id"],r["horizon_index"]) in donor]
        correct=evaluate_frozen(model,paired); zero=evaluate_frozen(model,paired,lambda r:0.0); perm=evaluate_frozen(model,paired,lambda r,d=donor:d[(r["trajectory_id"],r["horizon_index"])])
        base_paired=evaluate_frozen(base_model,paired)
        if abs(zero-base_paired)>1e-12: raise RuntimeError(f"zeroed-S does not reproduce paired base for {kind}: {zero-base_paired}")
        summary[kind]={"selected_lambda":lam,"validation_nll":val,"base_no_s_nll":base_nll,"base_no_s_paired_nll":base_paired,"correct_nll":correct,"incremental_gain":base_paired-correct,"incremental_bits":(base_paired-correct)/np.log(2),"zeroed_nll":zero,"permuted_nll":perm,"zeroed_minus_base_paired_nll":zero-base_paired,"zeroed_minus_correct_nll":zero-correct,"permuted_minus_correct_nll":perm-correct,"metrics":metrics_frozen(model,paired),"candidate_count_stratified_nll":stratified(model,paired),"state_mean":float(np.mean([r["state"] for r in te])),"state_std":float(np.std([r["state"] for r in te])),"state_nonzero_fraction":float(np.mean([r["state"]!=0 for r in te])),"w_norm":float(np.linalg.norm(model["w"])),"top_abs_w":sorted(zip(rf.FEATURE_NAMES,model["w"].tolist()),key=lambda x:abs(x[1]),reverse=True)[:5],"optimizer":model["optimizer"],"paired_rows":len(paired)}
    args.output.mkdir(parents=True,exist_ok=True); td=args.output/"optimization_trials"; hd=args.output/"optimization_history"; td.mkdir(); hd.mkdir()
    for t in trials:
        safe=str(t["lambda"]).replace(".","p"); (td/f"{t['condition']}.lambda_{safe}.json").write_text(json.dumps(t,indent=2)+"\n",encoding="utf8"); (hd/f"{t['condition']}.lambda_{safe}.jsonl").write_text("\n".join(json.dumps(x) for x in t["optimization_history"])+"\n",encoding="utf8")
    for kind,m in models.items(): (args.output/f"{kind}_s_frozen.model.json").write_text(json.dumps({"theta_source":str(model_run/"retrained_no_s.model.json"),"theta_fitted":False,"normalization_fitted":False,"learnable_parameters":["w"],"lambda":m["lambda"],"weights_theta":m["theta"].tolist(),"weights_w":m["w"].tolist(),"means":m["means"].tolist(),"scales":m["scales"].tolist(),"optimizer":m["optimizer"]},indent=2)+"\n",encoding="utf8")
    manifest={"schema_version":"character_dynamics_frozen_base_incremental_manifest_v1","run":"Run 2","fitted":True,"theta_source":str(model_run/"retrained_no_s.model.json"),"theta_fitted":False,"normalization_fitted":False,"learnable_parameters":["w"],"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"split":split,"seed":SEED,"lambda_grid":list(probe.LAMBDA_GRID),"selection_rule":"minimum validation NLL; ties choose larger lambda","zero_w_equivalence":{"base_nll":base_nll,"run1_no_s_nll":base_ref,"nll_abs_diff":abs(base_nll-base_ref),"max_probability_abs_diff":max_diff,"tolerance":1e-12},"trajectory_counts":{"total":len(records),"train":len(split["train"]),"validation":len(split["validation"]),"dev_holdout":len(split["test"])},"row_counts":{k:len(v) for k,v in all_rows.items()},"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"git_worktree_dirty":bool(__import__('subprocess').check_output(["git","status","--porcelain"],text=True).strip()),"runner_sha256":hashlib.sha256(HERE.read_bytes()).hexdigest(),"run1_base_model_sha256":hashlib.sha256((model_run/"retrained_no_s.model.json").read_bytes()).hexdigest(),"semantic_rules_sha256":hashlib.sha256((HERE.parent.parent/"T0c_LIGHT"/"compiled_semantics_v1.json").read_bytes()).hexdigest(),"scipy_version":__import__('scipy').__version__,"started_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"duration_seconds":time.time()-started,"python_version":platform.python_version(),"numpy_version":np.__version__}
    (args.output/"run2_summary.json").write_text(json.dumps({"manifest":manifest,"summary":summary},indent=2)+"\n",encoding="utf8"); print(json.dumps({"manifest":manifest,"summary":summary},indent=2))

if __name__ == "__main__": main()
