#!/usr/bin/env python3
"""Stream all processed LIGHT episodes with physical actions to ignored JSONL."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, pickle, statistics
from pathlib import Path

def load_exporter():
    path=Path(__file__).with_name("export_replay.py"); spec=importlib.util.spec_from_file_location("light_export",path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("pickle_path",type=Path); ap.add_argument("out_dir",type=Path); ap.add_argument("--review-limit",type=int,default=300); args=ap.parse_args()
    data=pickle.loads(args.pickle_path.read_bytes()); mod=load_exporter(); args.out_dir.mkdir(parents=True,exist_ok=True)
    lengths=[]; failed=[]; anomalies=[]; review=[]; out_path=args.out_dir/"light_full.replay.jsonl"; seen=set(); candidate_hits=0; candidate_total=0
    with out_path.open("w",encoding="utf-8",newline="\n") as out:
      for idx,e in enumerate(data):
        try: rec=mod.record(e,idx,"light_full_2026-09-06")
        except Exception as exc: failed.append({"episode":idx,"error":repr(exc)}); continue
        n=len(rec["steps"])
        if not n: continue
        if rec["trajectory_id"] in seen: anomalies.append({"episode":idx,"kind":"duplicate_trajectory_id"})
        seen.add(rec["trajectory_id"]); lengths.append(n)
        for s in rec["steps"]:
          candidate_total+=1; c=s.get("candidate_set_factual") or []; candidate_hits += int(s["source_action_A_star"] in c)
        picks={0,n//2,n-1}; picks |= {max(range(n),key=lambda i:len(rec["steps"][i].get("source_O") or ""))}
        for i in sorted(picks):
          if len(review)<args.review_limit: review.append({"trajectory_id":rec["trajectory_id"],"source_record_id":rec["source_record_id"],"step":rec["steps"][i]})
        out.write(json.dumps(rec,ensure_ascii=False,separators=(",",":"))+"\n")
    manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"LIGHT","role":"full_lossless_extraction","split_id":"light_full_2026-09-06","source_artifact":"light-dialog-processed-small7.pkl","parser":"02_实验/T0c_LIGHT/export_replay.py","source_revision":"light-dialog-processed-small7","source_artifact_sha256":hashlib.sha256(args.pickle_path.read_bytes()).hexdigest(),"trajectory_count":len(lengths),"step_count":sum(lengths),"min_steps":min(lengths) if lengths else None,"median_steps":statistics.median(lengths) if lengths else None,"max_steps":max(lengths) if lengths else None,"failed_episode_count":len(failed),"duplicate_trajectory_count":len(anomalies),"candidate_action_membership_hits":candidate_hits,"candidate_action_membership_total":candidate_total,"candidate_action_membership_rate":(candidate_hits/candidate_total if candidate_total else None),"output_sha256":hashlib.sha256(out_path.read_bytes()).hexdigest(),"semantic_audit":"pending","mechanism_use":False}
    (args.out_dir/"light_full.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (args.out_dir/"light_review_v0.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8"); (args.out_dir/"light_full.qa.json").write_text(json.dumps({"manifest":manifest,"failed":failed,"anomalies":anomalies},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:manifest[k] for k in ("trajectory_count","step_count","min_steps","median_steps","max_steps","candidate_action_membership_rate","output_sha256")},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
