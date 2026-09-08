#!/usr/bin/env python3
"""Frozen, deterministic command-evaluation metrics for ClubFloyd audits."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any

def norm(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x or "").strip().casefold())

def field(row: dict, name: str) -> Any:
    return row.get(name, row.get("parsed", {}).get(name))

def score(pred: dict, gold: dict) -> dict[str, bool]:
    p_raw, g_raw = norm(field(pred,"raw_command") or field(pred,"raw_action")), norm(field(gold,"raw_command") or field(gold,"raw_action"))
    p_norm, g_norm = norm(field(pred,"normalized_command")), norm(field(gold,"normalized_command"))
    return {"raw_exact": p_raw == g_raw, "normalized_exact": p_norm == g_norm,
            "verb_exact": norm(field(pred,"verb")) == norm(field(gold,"verb")),
            "target_exact": norm(field(pred,"target")) == norm(field(gold,"target")),
            "modifier_exact": norm(field(pred,"modifier")) == norm(field(gold,"modifier")),
            "semantic_match": bool(field(pred,"semantic_match") if "semantic_match" in pred else field(pred,"semantic_label") == field(gold,"semantic_label"))}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("predictions",type=Path); ap.add_argument("gold",type=Path); ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args(); gold={json.loads(x)["audit_id"]:json.loads(x) for x in args.gold.open(encoding="utf-8")}; rows=[]
    for line in args.predictions.open(encoding="utf-8"):
        p=json.loads(line); g=gold.get(p["audit_id"]); 
        if g is None: continue
        rows.append({"audit_id":p["audit_id"], **score(p,g)})
    metrics={k:sum(r[k] for r in rows)/len(rows) if rows else None for k in ("raw_exact","normalized_exact","verb_exact","target_exact","modifier_exact","semantic_match")}
    payload={"schema_version":"command_evaluation_v0","row_count":len(rows),"metrics":metrics,"rows":rows}
    args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"schema_version":payload["schema_version"],"row_count":len(rows),"metrics":metrics},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
