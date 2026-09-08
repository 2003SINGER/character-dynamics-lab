#!/usr/bin/env python3
"""Frozen low-order Stage-0b probe: O vs O+previous verb vs last-2 verbs."""
from __future__ import annotations
import argparse, hashlib, json, math, random, re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from command_schema_v0 import canonical_verb_family

SEED=20260908; O_DIM=64; EPOCHS=4; LR=.08; L2=1e-4
def hv(s): return int(hashlib.blake2s(s.encode(),digest_size=8).hexdigest(),16)
def toks(s): return re.findall(r"[a-z0-9]+",(s or '').casefold())
def ovec(s):
    v=[0.0]*O_DIM; ts=toks(s)
    for n in (1,2):
        for i in range(max(0,len(ts)-n+1)):
            q=' '.join(ts[i:i+n]); j=hv(q)%O_DIM; v[j]+=1 if hv('sign:'+q)%2 else -1
    z=math.sqrt(sum(x*x for x in v)) or 1; return [x/z for x in v]
def split(rows):
    def b(t): return int(hashlib.sha256(t.encode()).hexdigest()[:8],16)%10
    return [r for r in rows if b(r['trajectory_id'])<7],[r for r in rows if b(r['trajectory_id'])>=9]
def feats(r,kind,vocab):
    v=ovec(r['source_O'])
    if kind!='O_ONLY':
        hist=r.get('history',[]); seq=[canonical_verb_family(x['source_action_A_star']) for x in hist]
        take=1 if kind=='O_PLUS_PREV_VERB' else 2
        for pos,x in enumerate(reversed(seq[-take:])):
            j=vocab.get(x,vocab['<UNK>']); v.extend(1.0 if j==k else 0.0 for k in range(len(vocab)))
    return [z for part in v for z in (part if isinstance(part,list) else [part])]
def train(X,y,K):
    d=len(X[0]); W=[[0.0]*d for _ in range(K)]; b=[0.0]*K; rng=random.Random(SEED); order=list(range(len(y)))
    for _ in range(EPOCHS):
        rng.shuffle(order)
        for i in order:
            z=[sum(a*c for a,c in zip(W[k],X[i]))+b[k] for k in range(K)]; m=max(z); ee=[math.exp(min(40,q-m)) for q in z]; ss=sum(ee); p=[q/ss for q in ee]
            for k in range(K):
                g=p[k]-(1 if y[i]==k else 0); b[k]-=LR*g
                for j in range(d): W[k][j]-=LR*(g*X[i][j]+L2*W[k][j])
    return W,b
def evaluate(y,p,K):
    acc=sum(a==b for a,b in zip(y,p))/len(y); fs=[]
    for k in range(K):
        tp=sum(a==b==k for a,b in zip(p,y)); fp=sum(a==k and b!=k for a,b in zip(p,y)); fn=sum(a!=k and b==k for a,b in zip(p,y)); fs.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    return {'accuracy':acc,'macro_f1':sum(fs)/K}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixture',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--runner-commit',required=True); a=ap.parse_args(); rows=[json.loads(x) for x in a.fixture.open(encoding='utf-8') if x.strip()]; tr,te=split(rows); labels=sorted({canonical_verb_family(r['source_action_A_star']) for r in rows}); lid={x:i for i,x in enumerate(labels)}; vocab={x:i for i,x in enumerate(labels)}; vocab['<UNK>']=len(vocab)
    result={'schema_version':'clubfloyd_stage0b_low_order_probe_v0','runner_commit':a.runner_commit,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(a.fixture.read_bytes()).hexdigest(),'train_rows':len(tr),'test_rows':len(te),'seed':SEED,'O_DIM':O_DIM,'epochs':EPOCHS,'conditions':{}}
    for kind in ('O_ONLY','O_PLUS_PREV_VERB','O_PLUS_LAST2_VERB_HISTORY'):
        Xtr=[feats(r,kind,vocab) for r in tr]; Xte=[feats(r,kind,vocab) for r in te]; model=train(Xtr,[lid[canonical_verb_family(r['source_action_A_star'])] for r in tr],len(labels)); pred=[]
        for x in Xte:
            W,b=model; pred.append(max(range(len(W)),key=lambda k:sum(a*c for a,c in zip(W[k],x))+b[k]))
        gold=[lid[canonical_verb_family(r['source_action_A_star'])] for r in te]; result['conditions'][kind]={**evaluate(gold,pred,len(labels)),'feature_dim':len(Xtr[0])}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
