#!/usr/bin/env python3
"""Pure-Python fixed-capacity verb probe; no LLM or Theory-S."""
from __future__ import annotations
import argparse, hashlib, json, math, random, re
from pathlib import Path

D=256; ALPHA=.85; EPOCHS=18; LR=.08; L2=1e-4; SEED=20260908
def h(s): return int(hashlib.blake2s(s.encode('utf-8'),digest_size=8).hexdigest(),16)
def toks(s): return re.findall(r"[a-z0-9]+", (s or '').casefold())
def add(v,s,w=1.0):
    ts=toks(s)
    for n in (1,2):
        for i in range(max(0,len(ts)-n+1)):
            key=' '.join(ts[i:i+n]); j=h(key)%D; v[j]+=w*(1 if h('sign:'+key)%2 else -1)
def norm(v):
    z=math.sqrt(sum(x*x for x in v)) or 1.0; return [x/z for x in v]
def feature(row,kind):
    v=[0.0]*D; add(v,row['source_O'],1.0); hist=row['history']
    if kind=='C1_RAW_HISTORY':
        for i,x in enumerate(hist): add(v,x['source_O']+' <ACT> '+x['source_action_A_star'],.35+.65*(i+1)/len(hist))
    elif kind in ('C2_NAIVE_PERSISTENT','C3_PERMUTED_STATE'):
        seq=list(hist)
        if kind=='C3_PERMUTED_STATE': seq=sorted(seq,key=lambda x:h(row['trajectory_id']+'::'+str(x['t'])))
        m=[0.0]*D
        for x in seq:
            q=[0.0]*D; add(q,x['source_O']+' <ACT> '+x['source_action_A_star']); q=norm(q); m=[ALPHA*a+(1-ALPHA)*b for a,b in zip(m,q)]
        v=[.5*a+.5*b for a,b in zip(v,m)]
    return norm(v)
def verb(raw):
    x=toks(raw); return x[0] if x else '<EMPTY>'
def softmax(z):
    m=max(z); e=[math.exp(min(40,x-m)) for x in z]; s=sum(e); return [x/s for x in e]
def train(X,y,K):
    W=[[0.0]*D for _ in range(K)]; b=[0.0]*K; rng=random.Random(SEED); order=list(range(len(y)))
    for _ in range(EPOCHS):
        rng.shuffle(order)
        for i in order:
            p=softmax([sum(a*c for a,c in zip(W[k],X[i]))+b[k] for k in range(K)])
            for k in range(K):
                g=p[k]-(1.0 if y[i]==k else 0.0); b[k]-=LR*g
                for j in range(D): W[k][j]-=LR*(g*X[i][j]+L2*W[k][j])
    return W,b
def predict(model,x):
    W,b=model; return max(range(len(W)),key=lambda k:sum(a*c for a,c in zip(W[k],x))+b[k])
def bootstrap(a,b,n=10000):
    d=[float(x)-float(y) for x,y in zip(a,b)]; rng=random.Random(SEED); vals=[]
    for _ in range(n): vals.append(sum(d[rng.randrange(len(d))] for _ in d)/len(d))
    vals.sort(); return [vals[int(.025*n)],vals[int(.975*n)]]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixture',type=Path); ap.add_argument('out',type=Path); args=ap.parse_args(); rows=[json.loads(x) for x in args.fixture.open(encoding='utf-8') if x.strip()]
    split={r['trajectory_id']:('train' if h(r['trajectory_id'])%10<7 else 'val' if h(r['trajectory_id'])%10<9 else 'test') for r in rows}; labels=sorted({verb(r['source_action_A_star']) for r in rows}); lid={x:i for i,x in enumerate(labels)}; result={}; preds={}
    for kind in ('C0_O_ONLY','C1_RAW_HISTORY','C2_NAIVE_PERSISTENT','C3_PERMUTED_STATE'):
        X=[feature(r,kind) for r in rows]; tr=[i for i,r in enumerate(rows) if split[r['trajectory_id']]=='train']; te=[i for i,r in enumerate(rows) if split[r['trajectory_id']]=='test']; model=train([X[i] for i in tr],[lid[verb(rows[i]['source_action_A_star'])] for i in tr],len(labels)); yp=[predict(model,X[i]) for i in te]; yg=[lid[verb(rows[i]['source_action_A_star'])] for i in te]; acc=sum(a==b for a,b in zip(yp,yg))/len(yg); per=[]
        for k in range(len(labels)):
            tp=sum(a==b==k for a,b in zip(yp,yg)); fp=sum(a==k and b!=k for a,b in zip(yp,yg)); fn=sum(a!=k and b==k for a,b in zip(yp,yg)); per.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
        result[kind]={'train_rows':len(tr),'test_rows':len(te),'verb_accuracy':acc,'macro_f1':sum(per)/len(per),'labels':labels,'feature_dim':D}; preds[kind]=[{'target_id':rows[i]['target_id'],'gold_verb':verb(rows[i]['source_action_A_star']),'predicted_verb':labels[yp[j]]} for j,i in enumerate(te)]
    def delta(a,b):
        pa={x['target_id']:x['predicted_verb']==x['gold_verb'] for x in preds[a]}; pb={x['target_id']:x['predicted_verb']==x['gold_verb'] for x in preds[b]}; ids=sorted(set(pa)&set(pb)); return {'mean':sum((pa[i]-pb[i]) for i in ids)/len(ids),'ci95':bootstrap([pa[i] for i in ids],[pb[i] for i in ids]),'paired_rows':len(ids)}
    summary={'schema_version':'representation_baseline_structured_v0','fixture_sha256':hashlib.sha256(args.fixture.read_bytes()).hexdigest(),'target_rows':len(rows),'trajectory_count':len(set(r['trajectory_id'] for r in rows)),'labels':labels,'conditions':result,'paired_deltas':{'C1_minus_C0':delta('C1_RAW_HISTORY','C0_O_ONLY'),'C2_minus_C0':delta('C2_NAIVE_PERSISTENT','C0_O_ONLY'),'C2_minus_C1':delta('C2_NAIVE_PERSISTENT','C1_RAW_HISTORY'),'C3_minus_C2':delta('C3_PERMUTED_STATE','C2_NAIVE_PERSISTENT')}}; d=summary['paired_deltas']; summary['gates']={'HISTORY_SIGNAL_PRESENT':d['C1_minus_C0']['ci95'][0]>0,'PERSISTENT_COMPRESSION_SUPPORTED':bool(d['C1_minus_C0']['ci95'][0]>0 and d['C2_minus_C0']['ci95'][0]>0 and d['C2_minus_C1']['ci95'][0]>=-.03)}
    args.out.mkdir(parents=True,exist_ok=True); (args.out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); [ (args.out/f'predictions_{k}.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in v),encoding='utf-8') for k,v in preds.items() ]; print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
