#!/usr/bin/env python3
"""Deterministic Stage-0b verb-family trivial and low-order history baselines."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from command_schema_v0 import canonical_verb_family

def split(rows):
    # trajectory-disjoint deterministic split, frozen before looking at metrics
    def bucket(t): return int(hashlib.sha256(t.encode()).hexdigest()[:8],16)%10
    return ([r for r in rows if bucket(r['trajectory_id'])<7],[r for r in rows if bucket(r['trajectory_id'])>=9])
def score(gold,pred,labels):
    acc=sum(a==b for a,b in zip(gold,pred))/len(gold) if gold else 0
    fs=[]
    for k in labels:
        tp=sum(a==b==k for a,b in zip(pred,gold)); fp=sum(a==k and b!=k for a,b in zip(pred,gold)); fn=sum(a!=k and b==k for a,b in zip(pred,gold)); fs.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    return {"accuracy":acc,"macro_f1":sum(fs)/len(fs) if fs else 0}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixture',type=Path); ap.add_argument('out',type=Path); args=ap.parse_args()
    rows=[json.loads(x) for x in args.fixture.open(encoding='utf-8') if x.strip()]; tr,te=split(rows); labels=sorted({canonical_verb_family(r['source_action_A_star']) for r in rows}); maj=Counter(canonical_verb_family(r['source_action_A_star']) for r in tr).most_common(1)[0][0]
    prev_map=defaultdict(Counter); markov=defaultdict(Counter)
    for r in tr:
        h=r.get('history',[])
        if h:
            p=canonical_verb_family(h[-1]['source_action_A_star']); y=canonical_verb_family(r['source_action_A_star'])
            markov[p][y]+=1
    def prev(r):
        h=r.get('history',[]); return canonical_verb_family(h[-1]['source_action_A_star']) if h else maj
    def pred_markov(r):
        p=prev(r); return markov[p].most_common(1)[0][0] if markov[p] else maj
    gold=[canonical_verb_family(r['source_action_A_star']) for r in te]
    preds={"B0_GLOBAL_MAJORITY":[maj]*len(te),"B1_PREVIOUS_VERB":[prev(r) for r in te],"B2_FIRST_ORDER_MARKOV":[pred_markov(r) for r in te]}
    result={"schema_version":"clubfloyd_stage0b_baselines_v0","fixture_sha256":hashlib.sha256(args.fixture.read_bytes()).hexdigest(),"target_rows":len(rows),"train_rows":len(tr),"test_rows":len(te),"trajectory_count":len({r['trajectory_id'] for r in rows}),"train_trajectory_count":len({r['trajectory_id'] for r in tr}),"test_trajectory_count":len({r['trajectory_id'] for r in te}),"labels":labels,"train_class_counts":dict(Counter(canonical_verb_family(r['source_action_A_star']) for r in tr)),"test_class_counts":dict(Counter(gold)),"train_test_unseen_classes":sorted(set(gold)-set(canonical_verb_family(r['source_action_A_star']) for r in tr)),"baselines":{k:score(gold,v,labels) for k,v in preds.items()},"protocol":"B1 reads immediately preceding canonical verb; B2 estimates p(v_t|v_t-1) on train trajectories and falls back to global majority."}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
