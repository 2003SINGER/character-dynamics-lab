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

ALIASES = {"i": "inventory", "inv": "inventory", "l": "look", "x": "examine",
           "get": "take", "grab": "take", "pick": "take", "inspect": "examine"}
ARTICLES = {"a", "an", "the"}

def semantic_signature(raw: Any) -> tuple[str, str, str]:
    """Frozen conservative equivalence key; no world/post-state inference."""
    toks = norm(raw).split()
    if not toks:
        return ("", "", "")
    verb = ALIASES.get(toks[0], toks[0])
    rest = [t for t in toks[1:] if t not in ARTICLES]
    # Preserve relation words because 'ask x about y' differs from 'ask x'.
    target = " ".join(rest)
    return (verb, target, "")

def derived(row: dict, name: str) -> Any:
    value = field(row, name)
    if value is not None:
        return value
    raw = field(row, "raw_command") or field(row, "raw_action")
    sig = semantic_signature(raw)
    return {"normalized_command": norm(raw), "verb": sig[0], "target": sig[1], "modifier": sig[2]}.get(name)

def score(pred: dict, gold: dict) -> dict[str, bool]:
    p_raw, g_raw = norm(field(pred,"raw_command") or field(pred,"raw_action")), norm(field(gold,"raw_command") or field(gold,"raw_action"))
    p_norm, g_norm = norm(derived(pred,"normalized_command")), norm(derived(gold,"normalized_command"))
    p_action = field(pred,"raw_command") or field(pred,"raw_action")
    g_action = field(gold,"raw_command") or field(gold,"raw_action")
    return {"raw_exact": p_raw == g_raw, "normalized_exact": p_norm == g_norm,
            "verb_exact": norm(derived(pred,"verb")) == norm(derived(gold,"verb")),
            "target_exact": norm(derived(pred,"target")) == norm(derived(gold,"target")),
            "modifier_exact": norm(derived(pred,"modifier")) == norm(derived(gold,"modifier")),
            "semantic_match": semantic_signature(p_action) == semantic_signature(g_action)}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("predictions",type=Path); ap.add_argument("gold",type=Path); ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args(); gold={json.loads(x)["audit_id"]:json.loads(x) for x in args.gold.open(encoding="utf-8")}; rows=[]
    for line in args.predictions.open(encoding="utf-8"):
        p=json.loads(line); g=gold.get(p["audit_id"]); 
        if g is None: continue
        rows.append({"audit_id":p["audit_id"], **score(p,g)})
    metrics={k:sum(r[k] for r in rows)/len(rows) if rows else None for k in ("raw_exact","normalized_exact","verb_exact","target_exact","modifier_exact","semantic_match")}
    payload={"schema_version":"command_evaluation_v1","equivalence":"conservative token signature with fixed aliases/articles; no self-reported labels or post-state", "row_count":len(rows),"metrics":metrics,"rows":rows}
    args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"schema_version":payload["schema_version"],"row_count":len(rows),"metrics":metrics},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
