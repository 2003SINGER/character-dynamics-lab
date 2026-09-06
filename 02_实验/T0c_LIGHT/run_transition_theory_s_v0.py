"""140-step transition -> appraisal -> persistent theory-S diagnostic."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, random, statistics, subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
base = load("base", HERE.with_name("run_compiled_semantics_v0.py"))
ta = load("ta", HERE.parents[1] / "Replay" / "transition_appraisal_v0.py")

def snapshots(rec):
    return [base.compile_light_step(rec, s) for s in rec.get("steps", [])]

def build(rec, rules, condition, donor_states=None):
    lines=[f"RESET\t{rec['trajectory_id']}"]; rows=[]; prev=ta.zero_state(); ss=snapshots(rec); steps=rec.get("steps", [])
    for i, step in enumerate(steps):
        cur=ss[i]; prior=ss[i-1] if i else cur
        action=steps[i-1].get("source_action_A_star") if i else None
        x=ta.appraise_transition(prior,cur,action) if i else {"goal_relevance":0.0,"positive_conduciveness":0.0,"negative_conduciveness":0.0,"evidence":[],"transition_events":[],"matched_effect_events":[],"expected_effect":None}
        before=dict(prev); after=ta.update_state(prev,x) if condition=="theory-S" else ta.zero_state()
        if condition=="permuted-S" and donor_states is not None:
            after=dict(donor_states[i] if i < len(donor_states) else donor_states[-1]) if donor_states else ta.zero_state()
        prev=after; action_now=step.get("source_action_A_star"); candidates=step.get("candidate_set_factual")
        if not isinstance(candidates,list) or not candidates or action_now is None: continue
        gold=base.gold_index(candidates,action_now)
        if gold is None: continue
        compiled=[]; bindings=[]
        for c in candidates:
            feat, group, bias, flags=base.compile_candidate_scene_aware(c,cur,rules)
            if condition in {"theory-S","permuted-S"}: feat=ta.apply_state_to_candidate(feat,after)
            compiled.append(feat); bindings.append({"id":c,"scene":flags,"scene_bias":bias})
        lines.append(f"PREDICT\t{rec['trajectory_id']}\t{step['t']}\t{len(candidates)}")
        for feat, binding in zip(compiled, bindings):
            lines.append("C\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(feat['goal_progress'],feat['stimulation'],feat['recovery'],feat['hunger_relief'],feat['bathroom_relief'],feat['short_term_reward'],feat['environment_control'],feat['context_relevance'],binding['scene_bias']))
        rows.append({"trajectory_id":rec["trajectory_id"],"t":step["t"],"snapshot_prev_ref":i-1,"snapshot_current_ref":i,"previous_action":action,"transition_events":x["transition_events"],"matched_effect_events":x["matched_effect_events"],"expected_effect":x["expected_effect"],"X":x,"S_before":before,"S_after":after,"candidate_scene_bindings":bindings,"candidate_semantics":compiled,"gold_index":gold})
    return "\n".join(lines)+"\n", rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("core",type=Path); ap.add_argument("out",type=Path); ap.add_argument("--max-trajectories",type=int,default=50); args=ap.parse_args()
    rules=json.loads((HERE.parent/"compiled_semantics_v0.json").read_text(encoding="utf8")); selected=[]
    for rec in base.iter_records(args.replay):
        if rec.get("source_dataset")=="LIGHT" and not rec.get("source_episode_context",{}).get("quarantine"): selected.append(rec)
        if len(selected)>=args.max_trajectories: break
    protocols={}; all_rows={}
    for cond in ("zero-S","theory-S"):
        protocols[cond]=[]; all_rows[cond]=[]
        for rec in selected:
            p,r=build(rec,rules,cond); protocols[cond].append(p); all_rows[cond].extend(r)
    traces={rec["trajectory_id"]: build(rec,rules,"theory-S")[1] for rec in selected}; ids=list(traces)
    # Permute states within decision index, preserving each index's marginal.
    rng=random.Random(20260906); donor={tid:[] for tid in ids}; max_len=max((len(v) for v in traces.values()), default=0)
    for i in range(max_len):
        pool=[traces[tid][i]["S_after"] for tid in ids if i < len(traces[tid])]; rng.shuffle(pool)
        eligible=[tid for tid in ids if i < len(traces[tid])]
        for tid, state in zip(eligible, pool): donor[tid].append(state)
    protocols["permuted-S"]=[]; all_rows["permuted-S"]=[]
    for rec in selected:
        ds=donor[rec["trajectory_id"]]; p,r=build(rec,rules,"permuted-S",ds); protocols["permuted-S"].append(p); all_rows["permuted-S"].extend(r)
    args.out.mkdir(parents=True,exist_ok=True); summaries={}
    for cond in protocols:
        result=base.run_core(args.core,"".join(protocols[cond])); rows=[]
        result=base.score_results(result, {(r["trajectory_id"], int(r["t"])): r for r in all_rows[cond]})
        for row in all_rows[cond]:
            row=dict(row); row.update(result[(row["trajectory_id"],int(row["t"]))]); rows.append(row)
        trace=args.out/f"LIGHT_{cond.replace('-','_')}.trace.jsonl"; trace.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in rows),encoding="utf8")
        summaries[cond]={"scored_steps":len(rows),"mean_nll":sum(x["nll"] for x in rows)/len(rows),"mean_rank":sum(x["rank"] for x in rows)/len(rows),"permutation_seed":20260906 if cond=="permuted-S" else None}
    rows_for_metrics=all_rows["theory-S"]
    summaries["transition_metrics"]={
        "expected_effect_supported":sum(r["expected_effect"] is not None for r in rows_for_metrics),
        "expected_effect_confirmed":sum(r["X"]["positive_conduciveness"]>0 for r in rows_for_metrics),
        "expected_effect_unconfirmed":sum(r["expected_effect"] is not None and r["X"]["positive_conduciveness"]==0 for r in rows_for_metrics),
        "positive_conduciveness_nonzero":sum(r["X"]["positive_conduciveness"]>0 for r in rows_for_metrics),
        "negative_conduciveness_nonzero":sum(r["X"]["negative_conduciveness"]>0 for r in rows_for_metrics),
        "channel_stats":{k:{"mean":statistics.fmean(r["S_after"][k] for r in rows_for_metrics),"variance":statistics.pvariance(r["S_after"][k] for r in rows_for_metrics),"nonzero":sum(r["S_after"][k]>0 for r in rows_for_metrics)} for k in ta.zero_state()}
    }
    revision=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    manifest={"schema_version":"character_dynamics_transition_experiment_manifest_v0","git_revision":revision,"git_worktree_dirty":bool(subprocess.check_output(["git","status","--porcelain"],text=True).strip()),"source_replay":str(args.replay),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"semantic_rules_sha256":hashlib.sha256((HERE.parent/"compiled_semantics_v0.json").read_bytes()).hexdigest(),"replay_core_version":subprocess.check_output([str(args.core),"--version"],text=True).strip(),"eta":0.35,"delta_t":"1 decision boundary","interaction_coefficient":0.20,"permutation_seed":20260906,"conditions":["zero-S","theory-S","permuted-S","uniform"]}
    (args.out/"LIGHT_transition_theory_s_v0.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    summaries["uniform"]={"mean_nll":1.4126475597150339,"note":"same candidate support; analytic baseline from paired v0/v1 runs"}
    (args.out/"LIGHT_transition_theory_s_v0.summary.json").write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+"\n",encoding="utf8"); print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
