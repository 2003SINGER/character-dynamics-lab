#!/usr/bin/env python3
"""Stream all ClubFloyd cleaned transcripts to ignored JSONL + QA/review files."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, statistics
from pathlib import Path

def load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("clubfloyd_adapter", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("raw_dir", type=Path); ap.add_argument("out_dir", type=Path); ap.add_argument("--review-limit", type=int, default=300)
    args = ap.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    mod = load_adapter(Path(__file__).parents[1] / "clubfloyd_adapter.py")
    generator_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    files = sorted(args.raw_dir.glob("*.html")); lengths=[]; failed=[]; anomalies=[]; review=[]; seen=set()
    out_path=args.out_dir/"clubfloyd_full.replay.jsonl"
    with out_path.open("w",encoding="utf-8",newline="\n") as out:
        for p in files:
            try: rec=mod.parse_file(p,"clubfloyd_full_2026-09-06")
            except Exception as exc: failed.append({"file":p.name,"error":repr(exc)}); continue
            if rec["trajectory_id"] in seen: anomalies.append({"file":p.name,"kind":"duplicate_trajectory_id"})
            seen.add(rec["trajectory_id"]); n=len(rec["steps"]); lengths.append(n)
            if not n: anomalies.append({"file":p.name,"kind":"empty_transcript"})
            for s in rec["steps"]:
                if not s["source_action_A_star"].strip(): anomalies.append({"file":p.name,"t":s["t"],"kind":"empty_action"})
            picks={0, max(0,n//2), max(0,n-1)}
            if n: picks |= {max(range(n),key=lambda i:len(rec["steps"][i]["source_O"])), max(range(n),key=lambda i:len(rec["steps"][i]["source_action_A_star"]))}
            for i in sorted(picks):
                if len(review)<args.review_limit:
                    step=rec["steps"][i]
                    review.append({"review_id":f"clubfloyd::{rec['source_record_id']}::step-{i}","source_dataset":"ClubFloyd","source_record_ref":f"{rec['source_record_id']}#step-{i}","generator_sha256":generator_sha256,"raw":{"source_file":rec["source_record_id"],"raw_state":step["source_O"],"raw_action":step["source_action_A_star"]},"parsed":{"format":"CALM_markers","state_marker":"[STATE]","action_marker":"[ACTION]","state_text":step["source_O"],"action_text":step["source_action_A_star"]},"transformed":step,"mapping_notes":{"source_O":"Copied from raw [STATE] segment before this action.","source_action_A_star":"Copied from raw [ACTION] segment; no action ontology normalization.","W":"unknown because transcript does not provide authoritative world state.","persona_P":"null because transcript does not provide Character Dynamics response parameters."}})
            out.write(json.dumps(rec,ensure_ascii=False,separators=(",",":"))+"\n")
    manifest={"schema_version":"replay_adapter_manifest_v0","dataset":"ClubFloyd","role":"full_lossless_extraction","split_id":"clubfloyd_full_2026-09-06","source_artifact":"calm/lm_data.zip cleaned_corpora/*.html","parser":"02_实验/Replay/clubfloyd_adapter.py","source_revision":"calm-textgame@3c111c0102c27e258f596ace18540db22f97f1da","trajectory_count":len(lengths),"step_count":sum(lengths),"empty_trajectory_count":sum(n==0 for n in lengths),"failed_file_count":len(failed),"marker_parse_anomaly_count":len(anomalies),"min_steps":min(lengths) if lengths else None,"median_steps":statistics.median(lengths) if lengths else None,"max_steps":max(lengths) if lengths else None,"output_sha256":hashlib.sha256(out_path.read_bytes()).hexdigest(),"semantic_audit":"pending","mechanism_use":False}
    (args.out_dir/"clubfloyd_full.manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.out_dir/"clubfloyd_review_v0.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in review),encoding="utf-8")
    (args.out_dir/"clubfloyd_full.qa.json").write_text(json.dumps({"manifest":manifest,"failed":failed,"anomalies":anomalies},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:manifest[k] for k in ("trajectory_count","step_count","empty_trajectory_count","failed_file_count","marker_parse_anomaly_count","min_steps","median_steps","max_steps","output_sha256")},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
