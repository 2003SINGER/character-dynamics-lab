#!/usr/bin/env python3
"""Parse FarmQuest telemetry by source order and project explicit action proxies."""
from __future__ import annotations
import argparse, hashlib, json, re, statistics
from pathlib import Path

EVENT_TYPES={
 "Event":["SessionStart","Day"], "QuestAlgorithm":["Passage","RLAID","Random"],
 "Transition":["TutorialQuestBoard","TutorialShop","QuestBoard","Shop","Home","Main","Tutorial"],
 "Interaction":["HarvestMushroom","HarvestBerry","HarvestCrop","PlaceFurniture","RotateFurniture","PickupFurniture","Plant","Cook"],
 "Shop":["AvailableFurniture","AvailableSeed","AvailableRecipe","TriedBought","Bought","Sold","TriedPay","StartCoins","Pay"],
 "Quest":["PositionQuest","AvailableQuest","Accept","Submit"], "QuestBoardState":["Submit","accept"], "Quests":["QuestBoardState"]}
ACTION_TYPES={"Interaction","Shop","Quest"}; NON_ACTION_PREFIXES={"Available","StartCoins","PositionQuest","AvailableQuest"}

def parse_line(raw:str,index:int)->dict:
    payload, sep, raw_ts=raw.rpartition(";"); payload=(payload if sep else raw).strip(); raw_ts=raw_ts.strip() if sep else None
    if ":" not in payload: return {"raw":raw,"event_class":None,"event_type":None,"value":None,"raw_timestamp":raw_ts,"source_order":index,"parse_status":"ambiguous"}
    cls,rest=payload.split(":",1)
    # The released data contains nested ``Quests:QuestBoardState:Accept`` lines.
    if cls == "Quests" and rest.startswith("QuestBoardState:"):
        rest = rest
    known=EVENT_TYPES.get(cls,[]); typ=next((x for x in sorted(known,key=len,reverse=True) if rest.startswith(x)),None)
    if typ is None: return {"raw":raw,"event_class":cls,"event_type":None,"value":rest or None,"raw_timestamp":raw_ts,"source_order":index,"parse_status":"ambiguous"}
    value=rest[len(typ):].lstrip(": ") or None
    return {"raw":raw,"event_class":cls,"event_type":typ,"value":value,"raw_timestamp":raw_ts,"source_order":index,"parse_status":"ok"}

def is_action(e): return e["event_class"] in ACTION_TYPES and not (e["event_type"] or "").startswith(tuple(NON_ACTION_PREFIXES)) and e["event_type"] not in ("StartCoins",)

def sessions(events):
    out=[]; cur=[]
    for local_i, e in enumerate(events):
        if e["event_class"]=="Event" and e["event_type"]=="SessionStart" and cur: out.append(cur); cur=[]
        cur.append(e)
    if cur: out.append(cur)
    return out

def make_record(pid,si,events,source):
    steps=[]; prev_action=-1; algorithm=None; location=None
    for local_i, e in enumerate(events):
        if e["event_class"]=="QuestAlgorithm": algorithm=e["event_type"]
        if e["event_class"]=="Transition": location=e["event_type"]
        if not is_action(e): continue
        # events is session-local; source_order remains participant-global.
        preceding=events[prev_action+1:local_i]
        if any(x["source_order"] >= e["source_order"] for x in preceding):
            raise AssertionError(f"future leakage at {pid} session {si}: {e['source_order']}")
        action={"class":e["event_class"],"type":e["event_type"],"value":e["value"],"raw":e["raw"]}
        source_ref = (f"{pid}:events:{preceding[0]['source_order']}-{preceding[-1]['source_order']}" if preceding else f"{pid}:events:empty-before-{e['source_order']}")
        steps.append({"t":len(steps),"source_O":None,"source_event":preceding,"source_action_A_star":action,"source_step_context":{"event_index":e["source_order"],"preceding_source_events":preceding,"quest_algorithm":algorithm,"current_location":location,"raw_timestamp":e["raw_timestamp"],"timestamp_semantics":"unusable_for_ordering"},"W":None,"state_label":None,"candidate_set_factual":None,"candidate_set_expanded":None,"timestamp":None,"provenance":"observed","provenance_detail":"Telemetry event documented as player action proxy; timestamp is retained as raw metadata only.","field_provenance":{"source_action_A_star":{"kind":"observed","source_ref":f"{pid}:event:{e['source_order']}","uncertainty":"action proxy, not independently verified command"},"source_event":{"kind":"observed","source_ref":source_ref}}})
        prev_action=local_i
    return {"trajectory_id":f"farmquest::{pid}::session-{si:03d}","subject_id":pid,"group_id":None,"split_id":"farmquest_full_2026-09-06","source_dataset":"FarmQuest","source_revision":"kristenYu/FarmQuest-Player-Telemetry-Dataset@main","source_record_id":f"{pid}:session:{si}","source_license":"Repository LICENSE (MIT); survey/privacy and redistribution boundaries require separate review.","persona_P":None,"source_episode_context":{"participant_id":pid,"survey_raw":{k:source.get(k) for k in ("demographic_data","short_survey_1_data","short_survey_2_data","comparison_data")},"timestamp_semantics":"unusable_for_ordering","source_order_authority":"telemetry line index","session_boundary":"Event:SessionStart"},"steps":steps}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("path",type=Path); ap.add_argument("out_dir",type=Path); ap.add_argument("--review-limit",type=int,default=250); args=ap.parse_args(); data=json.loads(args.path.read_text(encoding="utf-8")); args.out_dir.mkdir(parents=True,exist_ok=True); records=[]; parsed_total=0; ambiguous=[]; review=[]
    required_seen=set()
    for pid,source in data.items():
        if not isinstance(source,dict) or "telemetry_data" not in source: continue
        ev=[parse_line(x,i) for i,x in enumerate(source["telemetry_data"].splitlines()) if x.strip()]; parsed_total+=len(ev); ambiguous.extend([x for x in ev if x["parse_status"]!="ok"])
        for si,ss in enumerate(sessions(ev)):
            rec=make_record(pid,si,ss,source)
            if rec["steps"]: records.append(rec)
            for e in ss:
                required_key=(e.get("event_class"),e.get("event_type"))
                required = required_key not in required_seen and required_key[0] in {"Event","QuestAlgorithm","Transition","Interaction","Shop","Quest","QuestBoardState","Quests"}
                if e["parse_status"]!="ok" or is_action(e) or required:
                    required_seen.add(required_key)
                    if len(review)<args.review_limit: review.append({"review_id":f"farmquest::{pid}::event-{e['source_order']}","source_dataset":"FarmQuest","source_record_ref":f"{pid}:event:{e['source_order']}","generator_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"raw":{"participant_key":pid,"session_index":si,"event_index":e["source_order"],"telemetry_line":e["raw"]},"parsed":e,"transformed":next((s for s in rec["steps"] if s["source_step_context"]["event_index"]==e["source_order"]),None),"mapping_notes":{"timestamp":"raw_timestamp retained; timestamp is null because source README marks it unusable for ordering.","source_O":"null; telemetry history is not automatically actor observation.","source_action_A_star":"Only explicit Interaction/Shop/Quest action proxy events are projected; Transition/availability events are not A*."}})
    out=args.out_dir/"farmquest_full.replay.jsonl"; out.write_text("".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in records),encoding="utf-8"); (args.out_dir/"farmquest_review_v0.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in review),encoding="utf-8")
    m={"schema_version":"replay_adapter_manifest_v0","dataset":"FarmQuest","role":"full_lossless_event_projection","source_artifact":"processed.json","source_repository_revision":"kristenYu/FarmQuest-Player-Telemetry-Dataset@main","source_artifact_sha256":hashlib.sha256(args.path.read_bytes()).hexdigest(),"parser":"02_实验/T0f_FarmQuest/export_replay.py","participant_count":len(data),"parsed_event_count":parsed_total,"ambiguous_event_count":len(ambiguous),"session_trajectory_count":len(records),"action_step_count":sum(len(r["steps"]) for r in records),"review_fixture_count":len(review),"output_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"timestamp_semantics":"unusable_for_ordering","semantic_audit":"pending","mechanism_use":False}
    (args.out_dir/"farmquest_full.manifest.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (args.out_dir/"farmquest_full.qa.json").write_text(json.dumps({"manifest":m,"ambiguous_examples":ambiguous[:100]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(m,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
