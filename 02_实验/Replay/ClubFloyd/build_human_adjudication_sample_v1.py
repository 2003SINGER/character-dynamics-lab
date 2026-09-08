#!/usr/bin/env python3
"""Build a small human adjudication sheet from reviewer disagreements."""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path

def rank(x: str) -> int:
    return int(hashlib.sha256(x.encode()).hexdigest()[:16], 16)

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("sample", type=Path); ap.add_argument("review1", type=Path); ap.add_argument("review2", type=Path); ap.add_argument("out", type=Path)
    a = {json.loads(x)["audit_id"]: json.loads(x) for x in ap.parse_args().sample.open(encoding="utf-8")}
    r1 = {json.loads(x)["audit_id"]: json.loads(x) for x in ap.parse_args().review1.open(encoding="utf-8")}
    r2 = {json.loads(x)["audit_id"]: json.loads(x) for x in ap.parse_args().review2.open(encoding="utf-8")}
    # Re-open through parsed namespace to avoid relying on iteration order.
    args = ap.parse_args()
    groups: dict[str, list[dict]] = defaultdict(list)
    for aid, row in a.items():
        x, y = r1.get(aid, {}), r2.get(aid, {})
        if x.get("semantic_label") == y.get("semantic_label"): continue
        key = f"{x.get('semantic_label','missing')}->{y.get('semantic_label','missing')}"
        groups[key].append({"audit_id": aid, "raw_action": row.get("raw_action",""), "pre_action_state": row.get("pre_action_state",""),
            "reviewer1": x.get("semantic_label"), "reviewer2": y.get("semantic_label"), "reviewer1_note": x.get("note"), "reviewer2_note": y.get("note"),
            "final_label": "", "note": "", "disagreement_group": key})
    priority = ["ambiguous_command->valid_command", "meta_command->valid_command", "chat_or_commentary->valid_command", "valid_command->ambiguous_command", "valid_command->meta_command", "valid_command->chat_or_commentary"]
    selected=[]
    for key in priority:
        selected.extend(sorted(groups.pop(key, []), key=lambda z: rank(z["audit_id"]))[:15])
    rest=[]
    for rows in groups.values(): rest.extend(rows)
    selected.extend(sorted(rest, key=lambda z: rank(z["audit_id"]))[:max(0, 60-len(selected))])
    selected=selected[:60]; selected.sort(key=lambda z:z["audit_id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for row in selected: f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"))+"\n")
    print(json.dumps({"schema_version":"command_admission_human_adjudication_v1","sample_count":len(selected),"groups":{k:sum(x["disagreement_group"]==k for x in selected) for k in priority},"final_label_blank":all(not x["final_label"] for x in selected)},ensure_ascii=False,indent=2))
if __name__ == "__main__": raise SystemExit(main())
