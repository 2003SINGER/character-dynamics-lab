#!/usr/bin/env python3
"""Prepare a fixed, model-blind 50-row LIGHT semantic-admission package."""
from __future__ import annotations
import argparse, csv, hashlib, json, random, re, subprocess
from collections import Counter
from pathlib import Path

SEED=20260907
FORBIDDEN=("Theory","Activity","ActionSupport","state value","zeroed","permuted","NLL","probability","rank","model prediction")

def load_rows(path):
    rows=[]
    with path.open(encoding="utf8") as fh:
        for rec in map(json.loads,fh):
            ctx=rec.get("source_episode_context",{})
            if ctx.get("quarantine"): continue
            steps=rec.get("steps",[])
            for i,step in enumerate(steps):
                candidates=step.get("candidate_set_factual"); action=step.get("source_action_A_star"); sc=step.get("source_step_context") or {}
                if action is None or not isinstance(candidates,list) or not candidates or not sc.get("actor"): continue
                prev=steps[i-1] if i else None; nxt=steps[i+1] if i+1<len(steps) else None
                length=len(steps); horizon_bucket="first" if i==0 else ("late" if i>=max(1,length-2) else "middle")
                verb=str(action).split(" ",1)[0].lower(); context=step.get("source_O") or ""
                rows.append({"trajectory_id":str(rec["trajectory_id"]),"episode_id":str(rec.get("source_record_id",rec["trajectory_id"])),"horizon_index":i,"t":step.get("t"),"actor":sc.get("actor"),"source_O":context,"source_episode_context":ctx,"source_action_A_star":action,"candidate_set_factual":candidates,"previous":prev,"next":nxt,"length":length,"horizon_bucket":horizon_bucket,"candidate_count":len(candidates),"verb":verb,"context_chars":len(context)})
    return rows

def length_bin(n): return "1-2" if n<=2 else ("3-4" if n<=4 else "5+")
def candidate_bin(n): return str(n) if n<5 else "5+"
def context_bin(n): return "short" if n<180 else ("medium" if n<420 else "long")

def select(rows, count=50):
    rng=random.Random(SEED); rows=list(rows); rng.shuffle(rows)
    by_stratum={}
    for r in rows:
        key=(length_bin(r["length"]),candidate_bin(r["candidate_count"]),r["horizon_bucket"],r["verb"],context_bin(r["context_chars"]))
        by_stratum.setdefault(key,[]).append(r)
    keys=list(by_stratum); rng.shuffle(keys); chosen=[]; used=set()
    # First pass: maximize structural/verb coverage while keeping one row per trajectory.
    for key in keys:
        options=[r for r in by_stratum[key] if r["trajectory_id"] not in used]
        if options:
            r=options[0]; chosen.append(r); used.add(r["trajectory_id"])
            if len(chosen)>=count: break
        if len(chosen)>=count: break
    # Fill deterministically from remaining unique trajectories only if needed.
    if len(chosen)<count:
        for r in rows:
            if r["trajectory_id"] in used: continue
            chosen.append(r); used.add(r["trajectory_id"])
            if len(chosen)>=count: break
    if len(chosen)<count: raise RuntimeError(f"only {len(chosen)} unique trajectories available")
    chosen.sort(key=lambda r:(r["trajectory_id"],r["horizon_index"]))
    for i,r in enumerate(chosen,1): r["review_id"]=f"LIGHT-BLIND50-{i:03d}"
    return chosen

def audit_context(step, label):
    if step is None: return {"availability":label,"present":False}
    return {"availability":label,"present":True,"t":step.get("t"),"actor":(step.get("source_step_context") or {}).get("actor"),"source_O":step.get("source_O"),"source_action_A_star":step.get("source_action_A_star"),"candidate_set_factual":step.get("candidate_set_factual")}

def package_row(r):
    return {"review_id":r["review_id"],"trajectory_id":r["trajectory_id"],"episode_id":r["episode_id"],"horizon_index":r["horizon_index"],"t":r["t"],"actor":r["actor"],"source_O":r["source_O"],"source_episode_context":json.dumps(r["source_episode_context"],ensure_ascii=False,sort_keys=True),"source_action_A_star":r["source_action_A_star"],"candidate_set_factual":json.dumps(r["candidate_set_factual"],ensure_ascii=False),"audit_previous_context":json.dumps(audit_context(r["previous"],"AUDIT-ONLY PREVIOUS CONTEXT"),ensure_ascii=False),"audit_future_context":json.dumps(audit_context(r["next"],"AUDIT-ONLY FUTURE INFORMATION"),ensure_ascii=False),"human_label":"","reason_actor_mismatch":"","reason_turn_alignment_unclear":"","reason_future_leakage":"","reason_observation_boundary_unclear":"","reason_action_actor_unclear":"","reason_action_candidate_mismatch":"","reason_candidate_semantics_unclear":"","reason_source_context_inconsistent":"","reason_other":"","a_star_support_alignment":"","candidate_estimand_usability":"","human_note":""}

def render_md(rows, path):
    lines=["# LIGHT semantic admission — blind 50","","本文件只展示 source 证据与审核空白字段；AUDIT-ONLY 上下文不可作为预测时刻输入。","","人工主标签：`ADMIT` / `REJECT` / `AMBIGUOUS`。","","---",""]
    for r in rows:
        lines += [f"## {r['review_id']}","",f"- trajectory_id: `{r['trajectory_id']}`",f"- episode_id: `{r['episode_id']}`",f"- horizon_index / t: `{r['horizon_index']}` / `{r['t']}`",f"- actor: `{r['actor']}`","", "### current source evidence", "", "**source_O (actor-specific; candidate input evidence only)**", "", "```text", r["source_O"], "```", "", f"**source_action_A_star:** `{r['source_action_A_star']}`", "", f"**candidate_set_factual (source-provided; not assumed to equal A^O):** `{json.dumps(r['candidate_set_factual'],ensure_ascii=False)}`", "", "**source episode context (audit only; not automatically O):**", "", "```json", json.dumps(r["source_episode_context"],ensure_ascii=False,indent=2,sort_keys=True), "```", "", "**previous context (AUDIT-ONLY):**", "", "```json", json.dumps(audit_context(r["previous"],"AUDIT-ONLY PREVIOUS CONTEXT"),ensure_ascii=False,indent=2), "```", "", "**future context (AUDIT-ONLY FUTURE INFORMATION):**", "", "```json", json.dumps(audit_context(r["next"],"AUDIT-ONLY FUTURE INFORMATION"),ensure_ascii=False,indent=2), "```", "", "### human review fields (blank)", "", "- human_label:", "- reasons: actor_mismatch / turn_alignment_unclear / future_leakage / observation_boundary_unclear / action_actor_unclear / action_candidate_mismatch / candidate_semantics_unclear / source_context_inconsistent / other", "- A* support semantic alignment: YES / NO / UNCLEAR", "- candidate-set estimand usability: USABLE / NOT_USABLE / UNCLEAR", "- human_note:", "", "---", ""]
    path.write_text("\n".join(lines),encoding="utf8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("replay",type=Path); ap.add_argument("output_dir",type=Path); args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True); rows=select(load_rows(args.replay)); packaged=[package_row(r) for r in rows]
    csv_path=args.output_dir/"light_semantic_admission_blind50_20260907.csv"; md_path=args.output_dir/"light_semantic_admission_blind50_20260907.md"; manifest_path=args.output_dir/"light_semantic_admission_blind50_20260907.manifest.json"
    fields=list(packaged[0])
    with csv_path.open("w",newline="",encoding="utf8") as fh: w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(packaged)
    render_md(rows,md_path)
    texts=[csv_path.read_text(encoding="utf8"),md_path.read_text(encoding="utf8")]; hits={term:[] for term in FORBIDDEN}
    for term in FORBIDDEN:
        for label,text in zip(("csv","md"),texts):
            if term.lower() in text.lower(): hits[term].append(label)
    manifest={"schema_version":"character_dynamics_light_semantic_admission_blind50_manifest_v1","source_replay":str(args.replay),"source_replay_sha256":hashlib.sha256(args.replay.read_bytes()).hexdigest(),"selection_seed":SEED,"selection_rule":"non-quarantine action rows; deterministic stratum coverage; max one row per trajectory; no model/state fields","sampled_trajectory_count":len(set(r["trajectory_id"] for r in rows)),"sampled_row_count":len(rows),"candidate_count_distribution":dict(Counter(candidate_bin(r["candidate_count"]) for r in rows)),"trajectory_length_distribution":dict(Counter(length_bin(r["length"]) for r in rows)),"horizon_distribution":dict(Counter(r["horizon_bucket"] for r in rows)),"review_fields_blank":True,"blindness_check":{"forbidden_terms":list(FORBIDDEN),"hits_in_package":hits,"status":"source-origin hits must be manually classified; no model-derived fields generated"},"git_revision":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"package_sha256":hashlib.sha256(csv_path.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"manifest":manifest,"paths":{"csv":str(csv_path),"markdown":str(md_path),"manifest":str(manifest_path)}},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
