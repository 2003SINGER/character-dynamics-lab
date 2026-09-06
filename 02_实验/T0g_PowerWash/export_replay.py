#!/usr/bin/env python3
"""Project PowerWash event tables into ReplayRecord state/event trajectories.

This dataset is state/event-centric: no synthetic next-action is created.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sqlite3, time
from pathlib import Path

EVENT_FILES = ["player_logged_in","game_saved","subtask_completed","task_completed","job_started","job_resumed","job_exited","job_completed","item_purchased","exited_game","update_current_state","study_prompt_answered","mood_reported","study_reward_claimed","study_reward_unlocked"]
STATE_FIELDS = {"CurrentPosition","CrouchState","CurrentWasher","CurrentNozzle","CurrentExtension","CurrentGameMode","CurrentJobName","LevelProgressionAmount","CampaignProgressionAmount","CurrentSessionLength","IsIdleInGame","IsInMenu"}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("raw_dir",type=Path); ap.add_argument("out_dir",type=Path); ap.add_argument("--review-limit",type=int,default=300); ap.add_argument("--reuse-index",action="store_true"); args=ap.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True); index_path=args.out_dir/"powerwash_index.sqlite"; db=sqlite3.connect(index_path); db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF"); db.execute("PRAGMA temp_store=FILE"); existing=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ev'").fetchone()
    if not (args.reuse_index and existing):
      db.execute("DROP TABLE IF EXISTS ev"); db.execute("CREATE TABLE ev(pid TEXT, time_utc TEXT, event_name TEXT, source_file TEXT, row_no INTEGER, payload TEXT)")
    total=0
    for stem in EVENT_FILES if not (args.reuse_index and existing) else []:
        p=args.raw_dir/f"{stem}.csv"
        if not p.exists(): continue
        with p.open(encoding="utf-8",newline="") as f:
            rd=csv.DictReader(f); batch=[]
            for row_no,row in enumerate(rd,1):
                pid=row.get("pid") or ""; payload={k:v for k,v in row.items() if k!="pid"}
                batch.append((pid,row.get("Time_utc") or row.get("Time") or "",stem,stem, row_no,json.dumps(payload,ensure_ascii=False,separators=(",",":")))); total+=1
                if len(batch)>=10000: db.executemany("INSERT INTO ev VALUES (?,?,?,?,?,?)",batch); batch=[]
            if batch: db.executemany("INSERT INTO ev VALUES (?,?,?,?,?,?)",batch)
    db.commit(); db.execute("CREATE INDEX ev_pid_order ON ev(pid,time_utc,source_file,row_no)"); db.commit()
    out=args.out_dir/"powerwash_full.replay.jsonl"; review=[]; trajectories=steps=0
    with out.open("w",encoding="utf-8",newline="\n") as dst:
      current_pid=None; rec_steps=[]; chunk_no=0; t=0; chunk_size=50000
      def flush(pid, chunk, no):
        nonlocal trajectories, steps
        if not chunk: return
        trajectories+=1; steps+=len(chunk); dst.write(json.dumps({"trajectory_id":f"powerwash::{pid}::chunk-{no:04d}","subject_id":pid,"group_id":None,"split_id":"powerwash_full_2026-09-06","source_dataset":"PowerWash","source_revision":"OSF WPEH6","source_record_id":f"{pid}:chunk:{no}","source_license":"CC-0 data/codebook per OSF record; verify study terms before redistribution.","persona_P":None,"source_episode_context":{"event_order":"time_utc, source_file, source_row deterministic tie-break","source_tables":EVENT_FILES,"observation_boundary":"Only source state columns are projected into source_O; compact event fields stay in source_event; raw zip is source of truth.","action_semantics":"no direct action command available","chunking":"50,000 ordered events per trajectory chunk"},"steps":chunk},ensure_ascii=False,separators=(",",":"))+"\n")
      cursor=db.execute("SELECT pid,time_utc,event_name,source_file,row_no,payload FROM ev WHERE pid<>'' ORDER BY pid,time_utc,source_file,row_no")
      for pid,ts,event,source_file,row_no,payload_s in cursor:
          if current_pid is not None and pid != current_pid:
            flush(current_pid,rec_steps,chunk_no); rec_steps=[]; chunk_no=0; t=0
          current_pid=pid
          payload=json.loads(payload_s); state={k:v for k,v in payload.items() if k in STATE_FIELDS and v not in (None,"")}; compact={k:v for k,v in payload.items() if k in STATE_FIELDS or k in {"LastSubtaskCompleted","LastTaskCompleted","RewardId","response","EventName"} and v not in (None,"")}
          step={"t":t%chunk_size,"source_O":state or None,"source_event":{"event_name":event,"payload":compact},"source_action_A_star":None,"source_step_context":{"event_name":event,"time_utc":ts,"source_file":source_file,"source_row":row_no,"payload_fields":sorted(payload)},"W":None,"state_label":event,"candidate_set_factual":None,"candidate_set_expanded":None,"timestamp":ts,"provenance":"observed","provenance_detail":"PowerWash research-edition event/state record; no synthetic next-action inferred.","field_provenance":{"source_O":{"kind":"observed","source_ref":f"{source_file}:{row_no}"},"source_event":{"kind":"observed","source_ref":f"{source_file}:{row_no}"},"source_action_A_star":{"kind":"not_available","reason":"state/event-centric source; no direct action command field"}}}
          rec_steps.append(step); t+=1
          if len(rec_steps)>=chunk_size:
            flush(current_pid,rec_steps,chunk_no); rec_steps=[]; chunk_no+=1
          if len(review)<args.review_limit or event in {"subtask_completed","task_completed","job_completed","study_prompt_answered","mood_reported"}:
            review.append({"review_id":f"powerwash::{pid}::step-{t-1}","source_dataset":"PowerWash","source_record_ref":f"{pid}:{source_file}:{row_no}","generator_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"raw":{"pid":pid,"event_name":event,"time_utc":ts,"payload":payload},"parsed":{"event_name":event,"time_utc":ts,"payload":payload},"transformed":step,"mapping_notes":{"source_O":"Only state fields present in this event are projected; absent state remains null.","source_action_A_star":"null by design; this source is event/state-centric, not a next-action log.","survey":"study_prompt_answered and mood_reported remain observed event records, not P/S inference."}})
      flush(current_pid,rec_steps,chunk_no)
    db.close(); manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"PowerWash","role":"full_lossless_event_state_projection","source_artifact":"OSF WPEH6 data.zip","source_artifact_sha256":hashlib.sha256((args.raw_dir.parent/"data.zip").read_bytes()).hexdigest() if (args.raw_dir.parent/"data.zip").exists() else None,"trajectory_count":trajectories,"step_count":steps,"raw_event_row_count":total,"review_fixture_count":len(review),"review_fixture_sha256":None,"output_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"index_path":str(index_path),"semantic_admission":"event/state proxy only; no verified A_star","semantic_audit":"pending","mechanism_use":False}
    review_path=args.out_dir/"powerwash_review_v0.jsonl"; review_path.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8"); manifest["review_fixture_sha256"]=hashlib.sha256(review_path.read_bytes()).hexdigest(); (args.out_dir/"powerwash_full.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(manifest,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
