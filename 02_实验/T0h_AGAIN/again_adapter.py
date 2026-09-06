#!/usr/bin/env python3
"""AGAIN telemetry adapter with causal (past-only) arousal alignment.

The annotation is retained as ``source_arousal_proxy``. It is never promoted
to source_O, state_label, or action ground truth, and future annotations are
never used for a telemetry row.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

def fnum(x):
    try: return float(x)
    except (TypeError,ValueError): return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source",type=Path); ap.add_argument("out",type=Path); ap.add_argument("--limit-sessions",type=int,default=20); args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    raw=args.source/"raw_data"; ann=defaultdict(list)
    with (raw/"raw_annotation.csv").open(encoding="utf-8-sig",newline="") as h:
      for r in csv.DictReader(h):
        if r.get("validity") not in {"1","1.0"}: continue
        k=(r.get("[control]player_id"),r.get("[control]session_id"),r.get("[control]game")); t=fnum(r.get("[control]time_stamp")); a=fnum(r.get("arousal_value"))
        if t is not None and a is not None: ann[k].append((t/1000.0,a,r.get("[control]video_name")))
    for v in ann.values(): v.sort()
    grouped=defaultdict(list); all_keys=[]
    with (raw/"raw_data.csv").open(encoding="utf-8-sig",newline="") as h:
      for r in csv.DictReader(h):
        k=(r.get("[control]player_id"),r.get("[control]session_id"),r.get("[control]game"))
        if k not in grouped: all_keys.append(k)
        grouped[k].append(r)
    if args.limit_sessions:
      by_game=defaultdict(list)
      for k in all_keys: by_game[k[2]].append(k)
      keys=[]
      while len(keys)<args.limit_sessions and any(by_game.values()):
        for game in sorted(by_game):
          if by_game[game] and len(keys)<args.limit_sessions: keys.append(by_game[game].pop(0))
    else: keys=all_keys
    replay=args.out/"AGAIN_dev.replay.jsonl"; review=[]; steps=0; aligned=0; future_guard=True
    with replay.open("w",encoding="utf-8") as out:
      for k in keys:
        rows=sorted(grouped[k],key=lambda r:fnum(r.get("[control]epoch")) or 0); av=ann.get(k,[]); ats=[x[0] for x in av]; st=[]
        for i,r in enumerate(rows):
          t=fnum(r.get("[control]time_stamp")); j=bisect_right(ats,t)-1; match=av[j] if j>=0 else None
          if match: aligned+=1; future_guard &= match[0] <= t
          payload={name:value for name,value in r.items() if not name.startswith("[control]") and name not in {"[string]key_presses"}}
          epoch=fnum(r.get("[control]epoch")); step={"t":i,"source_O":None,"source_event":None,"source_action_A_star":None,"source_step_context":{"telemetry":payload,"player_id":k[0],"session_id":k[1],"game":k[2],"epoch_ms":epoch,"time_stamp":t,"engine_tick":fnum(r.get("[control]engine_tick"))},"source_arousal_proxy":match[1] if match else None,"arousal_alignment":{"matched_annotation_time_stamp":match[0] if match else None,"lag_time_stamp":t-match[0] if match else None,"video_name":match[2] if match else None,"policy":"latest valid annotation at or before session-relative telemetry time_stamp; no future interpolation"},"state_label":None,"W":None,"timestamp":t,"provenance":"observed_telemetry_plus_causal_annotation_proxy"}
          st.append(step)
          if len(review)<300 and (i in {0,len(rows)//2,len(rows)-1} or match): review.append({"review_id":f"again::{k[0]}::{k[1]}::{k[2]}::step-{i}","source_dataset":"AGAIN","source_record_ref":f"{k[0]}:{k[1]}:{k[2]}:step:{i}","raw":{"telemetry":r,"annotation_match":match},"transformed":step,"mapping_notes":{"source_arousal_proxy":"latest valid annotation at or before telemetry time; never future value","source_O":"null","source_action_A_star":"null","state_label":"null"}})
        out.write(json.dumps({"trajectory_id":f"again::{k[0]}::{k[1]}::{k[2]}","subject_id":k[0],"source_dataset":"AGAIN","split_id":"again_dev","source_episode_context":{"game":k[2],"session_id":k[1],"boundary":"dataset session key; no invented gameplay boundary"},"steps":st},ensure_ascii=False,separators=(",",":"))+"\n"); steps+=len(st)
    rp=args.out/"AGAIN_dev_review_v0.jsonl"; rp.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8")
    manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"AGAIN","role":"telemetry_with_causal_arousal_proxy","session_count":len(keys),"games":sorted({k[2] for k in keys}),"step_count":steps,"aligned_step_count":aligned,"review_fixture_count":len(review),"source_O":"null","source_action_A_star":"null","state_label":"null","annotation_time_unit":"milliseconds in raw annotation; divided by 1000 to session seconds","causal_alignment":"latest valid annotation time_stamp <= telemetry time_stamp within session; no future interpolation","future_guard_pass":future_guard,"replay_sha256":hashlib.sha256(replay.read_bytes()).hexdigest(),"review_sha256":hashlib.sha256(rp.read_bytes()).hexdigest()}
    (args.out/"AGAIN_dev.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (args.out/"AGAIN_dev.qa.json").write_text(json.dumps({"manifest":manifest,"hard_checks":{"future_annotation_never_used":future_guard,"source_O_all_null":True,"source_action_A_star_all_null":True,"state_label_all_null":True}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
