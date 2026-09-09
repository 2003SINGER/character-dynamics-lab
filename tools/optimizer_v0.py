#!/usr/bin/env python3
"""Small deterministic optimizer-plumbing smoke; no holdout access."""
import argparse, hashlib, json, random, subprocess, sys, time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--batch',type=Path,required=True); ap.add_argument('--phone',type=Path,required=True); ap.add_argument('--deadline',type=Path,required=True); ap.add_argument('--commitment',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--source-revision',default='unknown'); ap.add_argument('--candidates',type=int,default=16); a=ap.parse_args()
    rng=random.Random(20260909); base={"state_accumulation":1.0,"state_recovery_strength":1.0,"state_decay":1.0,"task_pressure_coupling":1.0,"study_fatigue_penalty":1.0,"task_drive_coefficient":1.0,"distraction_weight":1.0,"commitment_bonus":1.0,"recovery_drive_coefficient":1.0}
    configs=[base]+[{k:round(v*rng.uniform(.9,1.1),6) for k,v in base.items()} for _ in range(max(0,a.candidates-1))]; records=[]; started=time.perf_counter()
    for i,cfg in enumerate(configs):
        blob=json.dumps(cfg,sort_keys=True,separators=(',',':')); ch=hashlib.sha256(blob.encode()).hexdigest()[:16]
        cmd=[sys.executable,str(Path(__file__).with_name('self_evaluation_v1.py')),'--batch',str(a.batch),'--phone',str(a.phone),'--deadline',str(a.deadline),'--commitment',str(a.commitment),'--out',str(a.out.parent/(f'_candidate_{i}.json')),'--source-revision',a.source_revision]
        run=subprocess.run(cmd,capture_output=True,text=True); result=json.loads(Path(cmd[cmd.index('--out')+1]).read_text(encoding='utf-8')) if run.returncode==0 else {'hard_gate_pass':False}
        records.append({'candidate_id':f'candidate_{i:03d}','config':cfg,'config_hash':ch,'source_revision':a.source_revision,'fixture_hard_gate_pass':all(result.get('hard_gates',{}).values()),'train_evaluator_result':result,'runtime_seconds':0.0})
    valid=[r for r in records if r['fixture_hard_gate_pass']]; selection='BASELINE_RETAINED / NO_SELECTION' if not valid or len(valid)==1 else valid[0]['candidate_id']
    out={'schema_version':'character_dynamics_optimizer_v0_smoke','optimizer_seed':20260909,'selection_frozen_before_holdout':False,'holdout_read_during_search':False,'selection':selection,'candidates':records,'runtime_seconds':time.perf_counter()-started,'provenance':{'source_revision':a.source_revision,'train_batch':str(a.batch)}}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'optimizer_smoke.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'selection':selection,'candidates':len(records)},ensure_ascii=False))
if __name__=='__main__':main()
