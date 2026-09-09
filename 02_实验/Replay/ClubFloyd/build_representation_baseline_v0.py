#!/usr/bin/env python3
"""Build deterministic bounded ClubFloyd representation-baseline canary."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from collections import defaultdict

def rank(x): return int(hashlib.sha256(x.encode()).hexdigest()[:16],16)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('replay',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--limit',type=int,default=400); args=ap.parse_args()
    candidates=[]; traj_count=defaultdict(int); seen=set()
    with args.replay.open(encoding='utf-8') as f:
        for line in f:
            rec=json.loads(line); tid=rec.get('trajectory_id') or rec.get('source_record_id'); steps=rec.get('steps',[])
            for i,s in enumerate(steps):
                q=s.get('source_step_context',{}).get('source_action_quality')
                raw=s.get('source_action_A_star','')
                if q!='command-like' or not raw.strip() or i<16: continue
                key=f'{tid}::{s.get("t",i)}::{i}'
                candidates.append((rank(key),key,rec, i)); seen.add(tid)
    rows=[]
    for rank_value,key,rec,i in sorted(candidates):
        tid=rec.get('trajectory_id') or rec.get('source_record_id')
        if traj_count[tid]>=10: continue
        steps=rec['steps']; target=steps[i]
        history=[{'t':x.get('t',j),'source_O':x.get('source_O',''),'source_action_A_star':x.get('source_action_A_star','')} for j,x in enumerate(steps[max(0,i-16):i],start=max(0,i-16))]
        rows.append({'target_id':f'{tid}::step-{i}','trajectory_id':tid,'step_index':i,'source_O':target.get('source_O',''),'source_action_A_star':target.get('source_action_A_star',''),'history':history,'selection_rank':rank_value,'selection_key':key})
        traj_count[tid]+=1
        if len(rows)>=args.limit: break
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('w',encoding='utf-8',newline='\n') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    manifest={'schema_version':'representation_baseline_fixture_v0','source':'clubfloyd_full.replay.jsonl','selection':'sha256 rank; command-like; >=16 past; <=10 targets/trajectory','target_count':len(rows),'trajectory_count':len({x['trajectory_id'] for x in rows}),'max_targets_per_trajectory':max(traj_count.values()) if traj_count else 0,'min_history':min((len(x['history']) for x in rows),default=0),'fixture_sha256':hashlib.sha256(args.out.read_bytes()).hexdigest(),'non_population_estimate':True}
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
