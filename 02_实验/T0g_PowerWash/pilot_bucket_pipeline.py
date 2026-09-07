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
    ap=argparse.ArgumentParser(); ap.add_argument("raw_dir",type=Path); ap.add_argument("out_dir",type=Path); ap.add_argument("--participants",type=int,default=100,help="0 selects all participants"); ap.add_argument("--buckets",type=int,default=256); args=ap.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True); part_file=args.raw_dir/"demographics.csv"; pids=[]
    with part_file.open(encoding="utf-8",newline="") as f:
      all_pids=sorted({r["pid"] for r in csv.DictReader(f) if r.get("pid")}); pids=all_pids if args.participants==0 else all_pids[:args.participants]
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
    is_full=args.participants==0; tag="full" if is_full else f"dev_{len(pids)}"; split_id=f"powerwash_{tag}_2026-09-06"
    replay=args.out_dir/f"PowerWash_{tag}.replay.jsonl"; review=[]; review_seen=set(); orphan_review_seen=defaultdict(int); orphan_available=defaultdict(int); anchors=[]; trajectories=steps=0; normal_sessions=orphan_segments=0; event_classes=defaultdict(int)
    with replay.open("w",encoding="utf-8",newline="\n") as out:
      for bp in sorted(part_dir.glob("bucket=*.jsonl")):
        rows=[json.loads(x) for x in bp.open(encoding="utf-8")]; rows.sort(key=lambda r:(r["pid"],r["Time_utc"] or "",r["source_file"],r["source_row"]))
        for pid in sorted({r["pid"] for r in rows}):
          pr=[r for r in rows if r["pid"]==pid]; session_no=0; segment_no=0
          # Bundle equal timestamps before sessionization: a boundary event may
          # share its timestamp with trailing telemetry and must stay together.
          bundles=[]; i=0
          while i<len(pr):
            j=i+1
            while j<len(pr) and pr[j]["Time_utc"]==pr[i]["Time_utc"]: j+=1
            bundles.append(pr[i:j]); i=j
          def emit(bundle_list,closed,boundary_status="complete",normal=True):
            nonlocal trajectories,steps,session_no,segment_no,review,review_seen,orphan_review_seen,orphan_available,normal_sessions,orphan_segments
            if not bundle_list: return
            status="complete" if closed else "partial"
            if not normal: status=boundary_status
            st=[]
            for t,bundle in enumerate(bundle_list):
              evs=[]
              for r in bundle:
                event_classes[r["event_name"]]+=1; evs.append({"event_name":r["event_name"],"payload":r["payload"],"source_row_key":r["source_row_key"],"source_file":r["source_file"],"source_row":r["source_row"]})
              state={k:v for r in bundle for k,v in r["payload"].items() if k in STATE_FIELDS and v not in (None,"")}
              step={"t":t,"source_O":None,"source_event":evs,"source_action_A_star":None,"source_step_context":{"source_state_fields":state or None,"within_timestamp_order":"unknown" if len(bundle)>1 else "not_applicable","time_utc":bundle[0]["Time_utc"],"source_row_keys":[r["source_row_key"] for r in bundle]},"W":None,"state_label":None,"candidate_set_factual":None,"candidate_set_expanded":None,"timestamp":bundle[0]["Time_utc"],"provenance":"observed","provenance_detail":"PowerWash source event/state projection; no subjective O, action, P, S or W inferred.","field_provenance":{"source_O":{"kind":"unknown","reason":"source game state is not assumed to be subjective observation"},"source_action_A_star":{"kind":"unknown","reason":"no direct command field"}}}
              st.append(step)
              names={e["event_name"] for e in evs}; required=set(EVENT_FILES); special=bool(names & required - review_seen)
              orphan_kind="pre_login_orphan" if boundary_status=="pre_login_orphan" else "post_exit_orphan"
              force_orphan=(not normal and orphan_review_seen[orphan_kind] < 8)
              if len(review)<300 or special or force_orphan:
                kind="session" if normal else "orphan"; idx=session_no if normal else segment_no
                review.append({"review_id":f"powerwash::{pid}::{kind}-{idx}::step-{t}","source_dataset":"PowerWash","source_record_ref":f"{pid}:{kind}:{idx}:step:{t}","boundary_status":boundary_status if not normal else "normal_session","raw":bundle,"parsed":{"timestamp":bundle[0]["Time_utc"],"events":evs},"transformed":step,"mapping_notes":{"source_O":"null in pilot; telemetry state retained under source_step_context.source_state_fields.","source_action_A_star":"null; no direct command field.","state_label":"null; event_name stays in source_event.","within_timestamp_order":"serialization order is not causal order."}}); review_seen.update(names & required)
                if not normal: orphan_review_seen[orphan_kind]+=1
              for anchor_name in {"mood_reported","study_prompt_answered"} & {e["event_name"] for e in evs}:
                anchors.append({"pid":pid,"session":session_no if normal else None,"segment":segment_no,"t":t,"timestamp":bundle[0]["Time_utc"],"anchor_target_event":anchor_name,"anchor_events":evs,"co_timestamp_events":[e for e in evs if e["event_name"]!=anchor_name],"co_timestamp_order":"unknown","past_event_window":[x for x in st[max(0,t-20):t] if x["timestamp"] < bundle[0]["Time_utc"]]})
            rec={"trajectory_id":f"powerwash::{pid}::{'session' if normal else 'orphan'}-{session_no if normal else segment_no}","subject_id":pid,"group_id":None,"split_id":split_id,"source_dataset":"PowerWash","source_revision":"OSF WPEH6","source_record_id":f"{pid}:{'session' if normal else 'orphan'}:{session_no if normal else segment_no}","source_license":"CC-0 data/codebook per OSF record; verify study terms before redistribution.","persona_P":None,"source_episode_context":{"session_boundary_status":status,"participant_sequence_index":session_no if normal else None,"participant_segment_index":segment_no,"event_order":"Time_utc; equal timestamps bundled, no causal order claimed","source_tables":EVENT_FILES,"observation_boundary":"source game state is retained as telemetry, not subjective O","action_semantics":"source_action_A_star=null"},"steps":st}
            out.write(json.dumps(rec,ensure_ascii=False,separators=(",",":"))+"\n"); trajectories+=1; steps+=len(st); segment_no+=1
            if normal: normal_sessions+=1; session_no+=1
            else: orphan_segments+=1; orphan_available[boundary_status]+=1
          active=[]; orphan=[]; mode="pre_login"
          for bundle in bundles:
            names={r["event_name"] for r in bundle}
            if "player_logged_in" in names:
              if active: emit(active,False,"partial",True); active=[]
              if orphan: emit(orphan,False,"pre_login_orphan" if mode=="pre_login" else "post_exit_orphan",False); orphan=[]
              active=[bundle]; mode="active"
            elif mode=="active":
              active.append(bundle)
              if "exited_game" in names:
                emit(active,True,"complete",True); active=[]; mode="post_exit"
            else:
              orphan.append(bundle)
          if active: emit(active,False,"partial",True)
          if orphan: emit(orphan,False,"pre_login_orphan" if mode=="pre_login" else "post_exit_orphan",False)
    anchor_path=args.out_dir/f"PowerWash_{tag}.anchors.jsonl"; anchor_path.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in anchors),encoding="utf-8")
    # Compute QA from the emitted replay; do not write a passing QA file unless
    # every invariant is actually observed in the artifact.
    qa={"source_O_all_null":True,"source_action_A_star_all_null":True,"state_label_all_null":True,"equal_timestamp_bundled":True,"bundle_never_split_across_sessions":True,"boundary_bundle_closed_together":True,"orphan_segments_separate":True,"participant_sequence_monotonic":True,"anchor_past_strictly_prior":all(all(x["timestamp"] < a["timestamp"] for x in a["past_event_window"]) for a in anchors),"orphan_review_coverage":all(orphan_review_seen[k]>=min(5,orphan_available[k]) for k in ("pre_login_orphan","post_exit_orphan"))}
    boundaries=defaultdict(list); seqs=defaultdict(list); seen_timestamps={}
    for line in replay.open(encoding="utf-8"):
      rec=json.loads(line); ctx=rec["source_episode_context"]; normal=ctx["session_boundary_status"] in {"complete","partial"}; seqs[rec["subject_id"]].append(ctx["participant_sequence_index"] if normal else -1)
      if not normal: qa["orphan_segments_separate"] &= ctx["participant_sequence_index"] is None
      if normal: qa["boundary_bundle_closed_together"] &= bool(rec["steps"]) and any(e["event_name"]=="player_logged_in" for e in rec["steps"][0]["source_event"]) and not any(any(e["event_name"]=="exited_game" for e in s["source_event"]) for s in rec["steps"][:-1])
      for s in rec["steps"]:
        qa["source_O_all_null"] &= s["source_O"] is None; qa["source_action_A_star_all_null"] &= s["source_action_A_star"] is None; qa["state_label_all_null"] &= s["state_label"] is None
        key=(rec["subject_id"],s["timestamp"]); loc=(rec["trajectory_id"],s["t"]); qa["equal_timestamp_bundled"] &= key not in seen_timestamps or seen_timestamps[key]==loc; seen_timestamps[key]=loc
      if rec["steps"]: boundaries[rec["subject_id"]].append((rec["steps"][0]["timestamp"],rec["steps"][-1]["timestamp"],{e["event_name"] for e in rec["steps"][-1]["source_event"]},{e["event_name"] for e in rec["steps"][0]["source_event"]}))
    for pid,items in boundaries.items():
      items.sort(key=lambda x:(x[0],x[1])); qa["bundle_never_split_across_sessions"] &= all(not (items[i][1]==items[i+1][0] and ({"exited_game","player_logged_in"}&(items[i][2]|items[i+1][3]))) for i in range(len(items)-1))
      normal_seq=[x for x in seqs[pid] if x>=0]; qa["participant_sequence_monotonic"] &= normal_seq==list(range(len(normal_seq)))
    assert all(qa.values()), f"PowerWash QA failed: {[k for k,v in qa.items() if not v]}"
    source_root=args.raw_dir.parent.parent; manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"PowerWash","role":"source_preserving_event_state_projection","split_id":split_id,"participant_count":len(pids),"raw_event_row_count":total,"trajectory_count":trajectories,"normal_session_count":normal_sessions,"orphan_segment_count":orphan_segments,"step_count":steps,"event_counts":dict(event_classes),"review_fixture_count":len(review),"anchor_count":len(anchors),"source_order":"Time_utc; equal timestamps bundled before sessionization; no causal order within bundle","source_O":"null","source_action_A_star":"null","state_label":"null","semantic_admission":"full extraction pending semantic audit" if is_full else "pilot only; semantic audit pending","source_archive":str(source_root/"data.zip"),"source_archive_sha256":"1B4D1F7DAF61548D9F40B9B0B6AC9FE3E44ED0DFF5D0D496FC002D08AC3AEC41","review_fixture_repo_path":f"02_实验/Replay/review_samples/PowerWash_review_v0.jsonl"}
    review_path=args.out_dir/f"PowerWash_{tag}_review_v0.jsonl"; review_path.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8"); manifest.update({"output_sha256":hashlib.sha256(replay.read_bytes()).hexdigest(),"review_fixture_sha256":hashlib.sha256(review_path.read_bytes()).hexdigest()}); (args.out_dir/f"PowerWash_{tag}.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (args.out_dir/f"PowerWash_{tag}.qa.json").write_text(json.dumps({"manifest":manifest,"by_file":by_file,"hard_checks":qa},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
