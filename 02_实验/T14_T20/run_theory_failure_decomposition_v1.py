#!/usr/bin/env python3
"""Run 4: analytic decomposition of the frozen Theory-S interaction."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp
from scipy.stats import pearsonr, spearmanr

HERE=Path(__file__).resolve()
sys.path.insert(0,str(HERE.parent.parent/"Replay")); sys.path.insert(0,str(HERE.parent.parent/"T0c_LIGHT")); sys.path.insert(0,str(HERE.parent))
import replay_features_v1 as rf
import run_rank_matched_probe_v1 as runner
import scene_snapshot_v0 as scene
import transition_appraisal_v0 as ta

ETA=runner.ETA

def rows_with_signal(rec, rules):
    snaps=[scene.compile_light_step(rec,s) for s in rec.get("steps",[])]
    previous=0.0; rows=[]
    for i,step in enumerate(rec.get("steps",[])):
        cur=snaps[i]; prior=snaps[i-1] if i else cur; prev_action=rec.get("steps",[])[i-1].get("source_action_A_star") if i else None
        appraisal=ta.appraise_transition(prior,cur,prev_action) if i else {"positive_conduciveness":0.0}
        signal=float(appraisal.get("positive_conduciveness",0.0))
        previous=previous+ETA*(signal-previous)
        candidates=step.get("candidate_set_factual"); action=step.get("source_action_A_star")
        if not isinstance(candidates,list) or not candidates or action is None: continue
        gold=runner.base.gold_index(candidates,action)
        if gold is None: continue
        compiled=[rf.vectorize(rf.compile_candidate_v1(c,cur,rules)[0]) for c in candidates]
        rows.append({"trajectory_id":str(rec["trajectory_id"]),"horizon_index":i,"t":int(step["t"]),"features":compiled,"gold_index":gold,"state":previous,"fresh_signal":signal})
    return rows

def row_analysis(model, row):
    means=np.asarray(model["means"],float); scales=np.asarray(model["scales"],float); theta=np.asarray(model["weights_theta"],float); w=np.asarray(model["weights_w"],float)
    x=(np.asarray(row["features"],float)-means)/scales; base=x@theta; g=x@w; y=int(row["gold_index"]); s=float(row["state"])
    def loss(q): return float(logsumexp(base+q*g)-(base[y]+q*g[y]))
    p=np.exp(base-logsumexp(base)); slope=float(np.dot(p,g)-g[y])
    bound=max(1.0,float(np.max([s,row["fresh_signal"],0.0]))*2.0)
    opt=minimize_scalar(loss,bounds=(0.0,bound),method="bounded",options={"xatol":1e-10})
    return {"base_nll":loss(0.0),"correct_nll":loss(s),"zero_delta":loss(0.0)-loss(s),"slope0":slope,"s_opt":float(opt.x),"s_opt_nll":float(opt.fun),"s_opt_delta":loss(0.0)-float(opt.fun),"g_gold":float(g[y]),"g_range":float(np.max(g)-np.min(g))}

def corr(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)<2 or np.std(x)==0 or np.std(y)==0: return {"pearson":None,"spearman":None}
    return {"pearson":float(pearsonr(x,y).statistic),"spearman":float(spearmanr(x,y).statistic)}

def summarize(rows):
    out={}
    for category in ("fresh","residual","zero"):
        sub=[r for r in rows if r["category"]==category]
        if not sub: out[category]={"rows":0}; continue
        d=np.asarray([r["zero_delta"] for r in sub]); s=np.asarray([r["state"] for r in sub]); slope=np.asarray([r["slope0"] for r in sub]); opt=np.asarray([r["s_opt"] for r in sub])
        out[category]={"rows":len(sub),"fraction_of_rows":len(sub)/len(rows),"state_mean":float(s.mean()),"state_std":float(s.std()),"zero_delta_mean":float(d.mean()),"zero_delta_median":float(np.median(d)),"zero_delta_std":float(d.std()),"fraction_helps":float(np.mean(d>0)),"fraction_hurts":float(np.mean(d<0)),"slope0_mean":float(slope.mean()),"s_opt_mean":float(opt.mean()),"state_vs_slope0":corr(s,slope),"state_vs_s_opt":corr(s,opt)}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("run1",type=Path); ap.add_argument("run2_output",type=Path); ap.add_argument("output",type=Path); args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()): raise RuntimeError(f"output directory is non-empty: {args.output}")
    run1_manifest=json.loads((args.run1/"training_manifest.json").read_text(encoding="utf8")); run2_summary=json.loads((args.run2_output/"run2_summary.json").read_text(encoding="utf8"));
    if hashlib.sha256(args.replay.read_bytes()).hexdigest()!=run1_manifest["source_replay_sha256"]: raise RuntimeError("replay SHA does not match Run 1")
    split=run2_summary["manifest"]["split"]; rules=json.loads((HERE.parent.parent/"T0c_LIGHT/compiled_semantics_v1.json").read_text(encoding="utf8")); records=runner.load_records(args.replay,100000); test_ids=set(split["test"])
    model=json.loads((args.run2_output/"theory_s_frozen.model.json").read_text(encoding="utf8")); all_rows=[]
    for rec in records:
        if str(rec["trajectory_id"]) not in test_ids: continue
        all_rows.extend(rows_with_signal(rec,rules))
    analyzed=[]
    for row in all_rows:
        a=row_analysis(model,row); signal=float(row["fresh_signal"]); state=float(row["state"])
        category="fresh" if signal>0 else ("residual" if state>0 else "zero")
        analyzed.append({**{k:row[k] for k in ("trajectory_id","horizon_index","t","state","fresh_signal","gold_index")},"category":category,**a})
    summary={"rows":len(analyzed),"state_mean":float(np.mean([r["state"] for r in analyzed])),"state_std":float(np.std([r["state"] for r in analyzed])),"state_nonzero_fraction":float(np.mean([r["state"]>0 for r in analyzed])),"fresh_signal_positive_fraction":float(np.mean([r["fresh_signal"]>0 for r in analyzed])),"overall":summarize(analyzed),"state_vs_slope0":corr([r["state"] for r in analyzed],[r["slope0"] for r in analyzed]),"state_vs_s_opt":corr([r["state"] for r in analyzed],[r["s_opt"] for r in analyzed]),"zero_delta_mean":float(np.mean([r["zero_delta"] for r in analyzed])),"zero_delta_median":float(np.median([r["zero_delta"] for r in analyzed])),"fraction_helps":float(np.mean([r["zero_delta"]>0 for r in analyzed])),"fraction_hurts":float(np.mean([r["zero_delta"]<0 for r in analyzed]))}
    args.output.mkdir(parents=True,exist_ok=True)
    fields=["trajectory_id","horizon_index","t","state","fresh_signal","category","gold_index","base_nll","correct_nll","zero_delta","slope0","s_opt","s_opt_nll","s_opt_delta","g_gold","g_range"]
    with (args.output/"theory_row_decomposition.csv").open("w",newline="",encoding="utf8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(analyzed)
    manifest={"schema_version":"character_dynamics_theory_failure_decomposition_manifest_v1","run":"Run 4","fitted":False,"source_run2":str(args.run2_output),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"split":split,"analysis":"row-wise frozen Theory-S loss curve; no training","eta":ETA,"git_revision":__import__('subprocess').check_output(["git","rev-parse","HEAD"],text=True).strip(),"runner_sha256":hashlib.sha256(HERE.read_bytes()).hexdigest(),"numpy_version":np.__version__}
    (args.output/"decomposition_summary.json").write_text(json.dumps({"manifest":manifest,"summary":summary},indent=2)+"\n",encoding="utf8")
    print(json.dumps({"manifest":manifest,"summary":summary},indent=2))

if __name__=="__main__": main()
