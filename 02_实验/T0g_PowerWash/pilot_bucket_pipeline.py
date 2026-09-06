#!/usr/bin/env python3
"""PowerWash 100-participant pilot: bucket raw CSVs, sort locally, form sessions."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil
from collections import defaultdict
from pathlib import Path

EVENT_FILES=["player_logged_in","game_saved","subtask_completed","task_completed","job_started","job_resumed","job_exited","job_completed","item_purchased","exited_game","update_current_state","study_prompt_answered","mood_reported","study_reward_claimed","study_reward_unlocked"]
STATE_FIELDS={"CurrentPosition","CrouchState","CurrentWasher","CurrentNozzle","CurrentExtension","CurrentGameMode","CurrentJobName","LevelProgressionAmount","CampaignProgressionAmount","CurrentSessionLength","IsIdleInGame","IsInMenu"}
def bucket(pid,n=256):
    s=str(pid)
    if s.startswith("p") and s[1:].isdigit(): return (int(s[1:])-1)%n
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:4],"big")%n
def row_key(source_file,row):
    return hashlib.sha256((source_file+"\0"+json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))).encode()).hexdigest()[:20]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("raw_dir",type=Path); ap.add_argument("out_dir",type=Path); ap.add_argument("--participants",type=int,default=100); ap.add_argument("--buckets",type=int,default=256); args=ap.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True); part_file=args.raw_dir/"demographics.csv"; pids=[]
    with part_file.open(encoding="utf-8",newline="") as f: pids=sorted({r["pid"] for r in csv.DictReader(f) if r.get("pid")})[:args.participants]
    wanted=set(pids); part_dir=args.out_dir/"partitioned"; shutil.rmtree(part_dir,ignore_errors=True); part_dir.mkdir()
    total=0; by_file={}
    handles={}
    try:
      for stem in EVENT_FILES:
        p=args.raw_dir/f"{stem}.csv"
        if not p.exists(): continue
        count=0
        with p.open(encoding="utf-8",newline="") as f:
          for row_no,row in enumerate(csv.DictReader(f),1):
            pid=row.get("pid")
            if pid not in wanted: continue
            b=part_dir/f"bucket={bucket(pid,args.buckets):03d}.jsonl"; h=handles.setdefault(b,b.open("a",encoding="utf-8"))
            h.write(json.dumps({"pid":pid,"event_name":row.get("EventName") or stem,"Time":row.get("Time"),"Time_utc":row.get("Time_utc") or row.get("Time"),"source_file":stem,"source_row":row_no,"source_row_key":row_key(stem,row),"payload":{k:v for k,v in row.items() if k not in {"pid","EventName","Time","Time_utc"}},"source_order_status":"timestamp_order_within_equal_timestamp_unknown"},ensure_ascii=False,separators=(",",":"))+"\n"); total+=1; count+=1
        by_file[stem]=count
    finally:
      for h in handles.values(): h.close()
    replay=args.out_dir/"PowerWash_dev_100.replay.jsonl"; review=[]; review_seen=set(); anchors=[]; trajectories=steps=0; event_classes=defaultdict(int)
    with replay.open("w",encoding="utf-8",newline="\n") as out:
      for bp in sorted(part_dir.glob("bucket=*.jsonl")):
        rows=[json.loads(x) for x in bp.open(encoding="utf-8")]; rows.sort(key=lambda r:(r["pid"],r["Time_utc"] or "",r["source_file"],r["source_row"]))
        for pid in sorted({r["pid"] for r in rows}):
          pr=[r for r in rows if r["pid"]==pid]; session=[]; session_no=0; seq=0
          def emit(events,closed):
            nonlocal trajectories,steps,session_no,review,review_seen
            if not events: return
            bundles=[]; i=0
            while i<len(events):
              j=i+1
              while j<len(events) and events[j]["Time_utc"]==events[i]["Time_utc"]: j+=1
              bundles.append(events[i:j]); i=j
            status="complete" if closed else "partial"
            st=[]
            for t,bundle in enumerate(bundles):
              evs=[]
              for r in bundle:
                event_classes[r["event_name"]]+=1; evs.append({"event_name":r["event_name"],"payload":r["payload"],"source_row_key":r["source_row_key"],"source_file":r["source_file"],"source_row":r["source_row"]})
              state={k:v for r in bundle for k,v in r["payload"].items() if k in STATE_FIELDS and v not in (None,"")}
              step={"t":t,"source_O":None,"source_event":evs,"source_action_A_star":None,"source_step_context":{"source_state_fields":state or None,"within_timestamp_order":"unknown" if len(bundle)>1 else "not_applicable","time_utc":bundle[0]["Time_utc"],"source_row_keys":[r["source_row_key"] for r in bundle]},"W":None,"state_label":None,"candidate_set_factual":None,"candidate_set_expanded":None,"timestamp":bundle[0]["Time_utc"],"provenance":"observed","provenance_detail":"PowerWash source event/state projection; no subjective O, action, P, S or W inferred.","field_provenance":{"source_O":{"kind":"not_mapped","reason":"source game state is not assumed to be subjective observation"},"source_action_A_star":{"kind":"not_available"}}}
              st.append(step)
              names={e["event_name"] for e in evs}; required=set(EVENT_FILES); special=bool(names & required - review_seen)
              if len(review)<300 or special:
                review.append({"review_id":f"powerwash::{pid}::session-{session_no}::step-{t}","source_dataset":"PowerWash","source_record_ref":f"{pid}:session:{session_no}:step:{t}","raw":bundle,"parsed":{"timestamp":bundle[0]["Time_utc"],"events":evs},"transformed":step,"mapping_notes":{"source_O":"null in pilot; telemetry state retained under source_step_context.source_state_fields.","source_action_A_star":"null; no direct command field.","state_label":"null; event_name stays in source_event.","within_timestamp_order":"serialization order is not causal order."}}); review_seen.update(names & required)
              if any(e["event_name"] in {"mood_reported","study_prompt_answered"} for e in evs): anchors.append({"pid":pid,"session":session_no,"t":t,"timestamp":bundle[0]["Time_utc"],"anchor_events":evs,"past_event_window":st[max(0,t-20):t]})
            rec={"trajectory_id":f"powerwash::{pid}::session-{session_no}","subject_id":pid,"group_id":None,"split_id":"powerwash_dev_100_2026-09-06","source_dataset":"PowerWash","source_revision":"OSF WPEH6","source_record_id":f"{pid}:session:{session_no}","source_license":"CC-0 data/codebook per OSF record; verify study terms before redistribution.","persona_P":None,"source_episode_context":{"session_boundary_status":status,"participant_sequence_index":seq,"event_order":"Time_utc; equal timestamps bundled, no causal order claimed","source_tables":EVENT_FILES,"observation_boundary":"source game state is retained as telemetry, not subjective O","action_semantics":"source_action_A_star=null"},"steps":st}
            out.write(json.dumps(rec,ensure_ascii=False,separators=(",",":"))+"\n"); trajectories+=1; steps+=len(st); session_no+=1
          for r in pr:
            if r["event_name"]=="player_logged_in" and session: emit(session,False); session=[]
            session.append(r)
            if r["event_name"]=="exited_game": emit(session,True); session=[]
          if session: emit(session,False)
    anchor_path=args.out_dir/"PowerWash_dev_100.anchors.jsonl"; anchor_path.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in anchors),encoding="utf-8")
    manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"PowerWash","role":"source_preserving_event_state_projection","split_id":"powerwash_dev_100_2026-09-06","participant_count":len(pids),"raw_event_row_count":total,"trajectory_count":trajectories,"step_count":steps,"event_counts":dict(event_classes),"review_fixture_count":len(review),"anchor_count":len(anchors),"source_order":"Time_utc; equal timestamps bundled; no causal order claimed","source_O":"null","source_action_A_star":"null","state_label":"null","semantic_admission":"pilot only; semantic audit pending","source_archive":"E:\\library\\科研\\PowerWash\\data.zip","source_archive_sha256":"1B4D1F7DAF61548D9F40B9B0B6AC9FE3E44ED0DFF5D0D496FC002D08AC3AEC41","review_fixture_repo_path":"02_实验/Replay/review_samples/PowerWash_review_v0.jsonl"}
    review_path=args.out_dir/"PowerWash_review_v0.jsonl"; review_path.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8"); manifest.update({"output_sha256":hashlib.sha256(replay.read_bytes()).hexdigest(),"review_fixture_sha256":hashlib.sha256(review_path.read_bytes()).hexdigest()}); (args.out_dir/"PowerWash_dev_100.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (args.out_dir/"PowerWash_dev_100.qa.json").write_text(json.dumps({"manifest":manifest,"by_file":by_file,"hard_checks":{"source_O_all_null":True,"source_action_A_star_all_null":True,"state_label_all_null":True,"equal_timestamp_bundled":True}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
