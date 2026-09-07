#!/usr/bin/env python3
"""Inspect FarmQuest JSON schema and telemetry vocabulary without reordering events."""
from __future__ import annotations
import argparse, collections, json
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("path",type=Path); ap.add_argument("output",type=Path); args=ap.parse_args()
    data=json.loads(args.path.read_text(encoding="utf-8")); participants=[]; classes=collections.Counter(); lines=0
    for pid, rec in data.items():
        if not isinstance(rec,dict) or "telemetry_data" not in rec: continue
        participants.append(pid)
        for line in rec["telemetry_data"].splitlines():
            if not line.strip(): continue
            lines+=1; payload=line.rsplit(";",1)[0].strip(); classes[payload.split(":",1)[0] if ":" in payload else "unknown"]+=1
    out={"dataset":"FarmQuest","source_file":args.path.name,"participant_count":len(participants),"telemetry_line_count":lines,"event_class_counts":dict(classes),"timestamp_semantics":"unusable_for_ordering","survey_fields":["demographic_data","short_survey_1_data","short_survey_2_data","comparison_data"]}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
