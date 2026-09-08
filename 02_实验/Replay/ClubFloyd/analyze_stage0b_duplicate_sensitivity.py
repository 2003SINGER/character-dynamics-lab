#!/usr/bin/env python3
"""Stratify the frozen Stage-0b probe by exact target/previous pair equality."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import run_stage0b_probe as probe
from command_schema_v0 import canonical_verb_family

def scores(gold,pred,labels):
    out={'rows':len(gold),'accuracy':sum(a==b for a,b in zip(gold,pred))/len(gold) if gold else 0}
    fs=[]
    for k in range(len(labels)):
        tp=sum(a==b==k for a,b in zip(pred,gold)); fp=sum(a==k and b!=k for a,b in zip(pred,gold)); fn=sum(a!=k and b==k for a,b in zip(pred,gold)); fs.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    out['macro_f1']=sum(fs)/len(fs) if fs else 0
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixture',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--runner-commit',required=True); a=ap.parse_args()
    rows=[json.loads(x) for x in a.fixture.open(encoding='utf-8') if x.strip()]; _,te=probe.split(rows); labels=sorted({canonical_verb_family(r['source_action_A_star']) for r in rows}); lid={x:i for i,x in enumerate(labels)}; vocab={x:i for i,x in enumerate(labels)}; vocab['<UNK>']=len(vocab); tr,_=probe.split(rows)
    groups={'EXACT_DUPLICATE_PAIR':[],'ACTION_REPEAT_ONLY':[],'OBSERVATION_REPEAT_ONLY':[],'GENUINE_TRANSITION':[]}
    for r in te:
        h=r.get('history',[]); prev=h[-1] if h else None
        if not prev: groups['GENUINE_TRANSITION'].append(r); continue
        same_o=r['source_O']==prev['source_O']; same_raw=r['source_action_A_star']==prev['source_action_A_star']; same_verb=canonical_verb_family(r['source_action_A_star'])==canonical_verb_family(prev['source_action_A_star'])
        if same_o and same_raw: g='EXACT_DUPLICATE_PAIR'
        elif (not same_o) and same_raw: g='ACTION_REPEAT_ONLY'
        elif same_o and (not same_raw): g='OBSERVATION_REPEAT_ONLY'
        else: g='GENUINE_TRANSITION'
        groups[g].append(r)
    subgroups={'RAW_ACTION_REPEAT':[],'CANONICAL_VERB_REPEAT_RAW_DIFFERENT':[],'CANONICAL_VERB_TRANSITION':[]}
    for r in te:
        h=r.get('history',[]); p=h[-1] if h else None
        if not p: continue
        same_raw=r['source_action_A_star']==p['source_action_A_star']; same_verb=canonical_verb_family(r['source_action_A_star'])==canonical_verb_family(p['source_action_A_star'])
        if same_raw: subgroups['RAW_ACTION_REPEAT'].append(r)
        elif same_verb: subgroups['CANONICAL_VERB_REPEAT_RAW_DIFFERENT'].append(r)
        else: subgroups['CANONICAL_VERB_TRANSITION'].append(r)
    result={'schema_version':'clubfloyd_stage0b_duplicate_sensitivity_v0','runner_commit':a.runner_commit,'runner_sha256':hashlib.sha256(probe.Path(probe.__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(a.fixture.read_bytes()).hexdigest(),'test_rows':len(te),'groups':{k:len(v) for k,v in groups.items()},'subgroups':{k:len(v) for k,v in subgroups.items()},'conditions':{}}
    for kind in ('O_ONLY','O_PLUS_PREV_VERB','O_PLUS_LAST2_VERB_HISTORY'):
        model=probe.train([probe.feats(r,kind,vocab) for r in tr],[lid[canonical_verb_family(r['source_action_A_star'])] for r in tr],len(labels)); W,b=model
        def predict(r):
            x=probe.feats(r,kind,vocab); return max(range(len(W)),key=lambda k:sum(a*c for a,c in zip(W[k],x))+b[k])
        result['conditions'][kind]={}
        for g,rs in groups.items(): result['conditions'][kind][g]=scores([lid[canonical_verb_family(r['source_action_A_star'])] for r in rs],[predict(r) for r in rs],labels)
        result['conditions'][kind]['subgroups']={g:scores([lid[canonical_verb_family(r['source_action_A_star'])] for r in rs],[predict(r) for r in rs],labels) for g,rs in subgroups.items()}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
