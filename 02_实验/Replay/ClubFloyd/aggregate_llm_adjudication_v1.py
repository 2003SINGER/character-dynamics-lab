#!/usr/bin/env python3
import argparse, collections, hashlib, json
from pathlib import Path

LABELS={'IN_WORLD_CHOICE','META_COMMAND','CHAT_OR_COMMENTARY','UNRESOLVED'}; CONF={'high','medium','low'}
def load(p): return {json.loads(x)['audit_id']:json.loads(x) for x in p.open(encoding='utf-8')}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('challenge',type=Path); ap.add_argument('a',type=Path); ap.add_argument('b',type=Path); ap.add_argument('c',type=Path); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--required-out',type=Path,required=True); args=ap.parse_args()
    base=load(args.challenge); rs=[load(args.a),load(args.b),load(args.c)]; rows=[]; required=[]
    for aid,x in base.items():
        ys=[r.get(aid,{}) for r in rs]; labels=[y.get('label') for y in ys]; conf=[y.get('confidence') for y in ys]
        violation=any(l not in LABELS or q not in CONF or not isinstance(y.get('reason'),str) or len(y.get('reason','').split())>45 for y,l,q in zip(ys,labels,conf))
        counts=collections.Counter(labels); top,n=counts.most_common(1)[0] if counts else ('UNRESOLVED',0)
        if violation or (n==1) or (n==2 and any(conf[i]=='low' for i,l in enumerate(labels) if l==top)):
            status='HUMAN_REVIEW_REQUIRED'; final=''
        elif n==3 and sum(q in {'high','medium'} for q in conf)>=2:
            status='MODEL_CONSENSUS'; final=top
        elif n==2:
            status='MODEL_MAJORITY'; final=top
        else:
            status='HUMAN_REVIEW_REQUIRED'; final=''
        row={'audit_id':aid,'reviewer_A_label':labels[0],'reviewer_A_confidence':conf[0],'reviewer_A_reason':ys[0].get('reason',''),'reviewer_B_label':labels[1],'reviewer_B_confidence':conf[1],'reviewer_B_reason':ys[1].get('reason',''),'reviewer_C_label':labels[2],'reviewer_C_confidence':conf[2],'reviewer_C_reason':ys[2].get('reason',''),'final_label':final,'adjudication_status':status,'disagreement_pattern':'|'.join(labels)}
        rows.append(row)
        if status=='HUMAN_REVIEW_REQUIRED': required.append({'audit_id':aid,'raw_action':x['raw_action'],'pre_action_state':x['pre_action_state'],'reviewer_A':{'label':labels[0],'confidence':conf[0],'reason':ys[0].get('reason','')},'reviewer_B':{'label':labels[1],'confidence':conf[1],'reason':ys[1].get('reason','')},'reviewer_C':{'label':labels[2],'confidence':conf[2],'reason':ys[2].get('reason','')},'final_label':'','note':''})
    args.out.parent.mkdir(parents=True,exist_ok=True); args.required_out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('w',encoding='utf-8',newline='\n') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    with args.required_out.open('w',encoding='utf-8',newline='\n') as f:
        for x in required:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    summary={'schema_version':'command_admission_llm_adjudication_v1','challenge_sha256':hashlib.sha256(args.challenge.read_bytes()).hexdigest(),'rows':len(rows),'consensus':sum(x['adjudication_status']=='MODEL_CONSENSUS' for x in rows),'majority':sum(x['adjudication_status']=='MODEL_MAJORITY' for x in rows),'human_required':len(required),'final_label_counts':dict(collections.Counter(x['final_label'] for x in rows if x['final_label'])),'status_counts':dict(collections.Counter(x['adjudication_status'] for x in rows))}
    args.out.with_suffix('.summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
