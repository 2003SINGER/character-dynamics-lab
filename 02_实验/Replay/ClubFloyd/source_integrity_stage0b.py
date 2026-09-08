#!/usr/bin/env python3
"""Audit duplicate structure and compare fixture pairs with raw CALM HTML."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

PAIR = re.compile(r"\[STATE\](.*?)\[ACTION\](.*?)(?=\[STATE\]|\Z)", re.S)
def pairs(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(s.strip(), a.strip()) for s,a in PAIR.findall(text) if a.strip()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("fixture",type=Path); ap.add_argument("raw_dir",type=Path); ap.add_argument("out",type=Path); ap.add_argument("--sample",type=int,default=20); args=ap.parse_args()
    rows=[json.loads(x) for x in args.fixture.open(encoding="utf-8") if x.strip()]
    def rate(n): return n/len(rows) if rows else 0
    metrics={"target_rows":len(rows),"trajectory_count":len({r['trajectory_id'] for r in rows}),"adjacent_history_pair_exact_duplicate_rate":None,"target_action_equals_previous_rate":None,"target_O_equals_previous_rate":None,"target_pair_equals_previous_rate":None}
    counts={k:0 for k in ("adjacent","action","obs","pair")}; adjacent_total=0; cases=[]
    for r in rows:
        h=r.get("history",[]); prev=h[-1] if h else None
        if prev:
            for i in range(1,len(h)):
                adjacent_total += 1
                if h[i].get("source_O")==h[i-1].get("source_O") and h[i].get("source_action_A_star")==h[i-1].get("source_action_A_star"): counts["adjacent"]+=1
            if r["source_action_A_star"]==prev["source_action_A_star"]: counts["action"]+=1
            if r["source_O"]==prev["source_O"]: counts["obs"]+=1
            if r["source_O"]==prev["source_O"] and r["source_action_A_star"]==prev["source_action_A_star"]: counts["pair"]+=1
            if len(cases)<args.sample and (r["source_O"]==prev["source_O"] or r["source_action_A_star"]==prev["source_action_A_star"]):
                cases.append({"target_id":r["target_id"],"trajectory_id":r["trajectory_id"],"step_index":r["step_index"],"target":{ "O":r["source_O"],"action":r["source_action_A_star"]},"previous":{ "O":prev["source_O"],"action":prev["source_action_A_star"]}})
    metrics.update({"adjacent_history_pair_exact_duplicate_rate":counts["adjacent"]/adjacent_total if adjacent_total else 0,"adjacent_history_pair_comparisons":adjacent_total,"target_action_equals_previous_rate":rate(counts["action"]),"target_O_equals_previous_rate":rate(counts["obs"]),"target_pair_equals_previous_rate":rate(counts["pair"]),"counts":counts})
    raw_checks=[]
    for c in cases:
        name=c["trajectory_id"].split("::",1)[-1]+".html"; p=args.raw_dir/name
        ps=pairs(p) if p.exists() else []
        t=c["step_index"]; exact=(t<len(ps) and ps[t][0]==c["target"]["O"] and ps[t][1]==c["target"]["action"])
        prev=(t>0 and ps[t-1]==(c["previous"]["O"],c["previous"]["action"]))
        raw_checks.append({"target_id":c["target_id"],"raw_file":name,"raw_file_exists":p.exists(),"target_pair_matches_raw_index":exact,"previous_pair_matches_raw_index":prev})
    result={"schema_version":"clubfloyd_source_integrity_stage0b_v0","fixture_sha256":hashlib.sha256(args.fixture.read_bytes()).hexdigest(),"metrics":metrics,"sample_size":len(cases),"sample_cases":cases,"raw_checks":raw_checks,"provenance_conclusion":"source_or_upstream_transcript_duplication" if raw_checks and sum(x["target_pair_matches_raw_index"] and x["previous_pair_matches_raw_index"] for x in raw_checks)>=len(raw_checks)*.8 else "requires_parser_followup","analysis_view_rule":"No deduplication applied; preserve lossless raw replay. Any future collapse requires separately versioned evidence-backed rule."}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result["metrics"],ensure_ascii=False,indent=2))
if __name__=='__main__': main()
