#!/usr/bin/env python3
"""End-to-end development smoke: config -> C++ engine -> batch -> evaluator."""
import argparse,hashlib,json,random,subprocess,sys,time
from pathlib import Path
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--batch-root',type=Path,required=True);ap.add_argument('--phone',type=Path,required=True);ap.add_argument('--deadline',type=Path,required=True);ap.add_argument('--commitment',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-revision',default='unknown');ap.add_argument('--candidates',type=int,default=4);a=ap.parse_args();rng=random.Random(20260909);base=json.loads(Path('tools/parameter_config_v0.json').read_text(encoding='utf-8'));keys=['state_accumulation','state_recovery_strength','state_decay','task_pressure_coupling','study_fatigue_penalty','task_drive_coefficient','distraction_weight','commitment_bonus','recovery_drive_coefficient'];configs=[]
    for i in range(a.candidates):
        c={k:float(base[k]) for k in keys}
        if i:c[rng.choice(keys)]=round(rng.uniform(.8,1.2),6)
        configs.append(c)
    a.out.mkdir(parents=True,exist_ok=True);records=[];started=time.perf_counter()
    for i,cfg in enumerate(configs):
        root=a.out/f'candidate_{i:03d}';root.mkdir(parents=True,exist_ok=True);cfg_path=root/'config.json';blob=json.dumps(cfg,sort_keys=True,separators=(',',':'));ch=hashlib.sha256(blob.encode()).hexdigest()[:16];cfg_path.write_text(json.dumps({'schema_version':'parameter_config_v0','config_hash':ch,**cfg},indent=2)+'\n',encoding='utf-8')
        batch_root=root/'batch';cmd=[str(a.engine),'--batch',str(batch_root),'--config',str(cfg_path),'--split-manifest',str(a.manifest),'--split','optimizer_train'];t=time.perf_counter();run=subprocess.run(cmd,capture_output=True,text=True);runtime=time.perf_counter()-t;batch=list(batch_root.glob('run_*/trajectories.csv'))
        hard=False;ev={};err=''
        if run.returncode==0 and batch:
            batch_dir=batch[0].parent;phone=root/'phone.csv';deadline=root/'deadline.csv';commitment=root/'commitment.csv';
            subprocess.run([str(a.engine),'--paired-phone',str(phone),'--config',str(cfg_path)],check=True,capture_output=True);subprocess.run([str(a.engine),'--paired-deadline',str(deadline),'--config',str(cfg_path)],check=True,capture_output=True);subprocess.run([str(a.engine),'--paired-commitment',str(commitment),'--config',str(cfg_path)],check=True,capture_output=True)
            ep=root/'evaluation.json';er=subprocess.run([sys.executable,'tools/self_evaluation_v1.py','--batch',str(batch_dir),'--phone',str(phone),'--deadline',str(deadline),'--commitment',str(commitment),'--out',str(ep),'--source-revision',a.source_revision],capture_output=True,text=True);ev=json.loads(ep.read_text(encoding='utf-8')) if er.returncode==0 else {};hard=bool(ev.get('hard_gate_pass'))
        else:err=run.stderr[-1000:]
        metadata=(batch[0].parent/'metadata.txt').read_text(encoding='utf-8') if batch else ''
        engine_hash=next((line.split('=',1)[1].strip() for line in metadata.splitlines() if line.startswith('parameter_config_hash=')),None)
        assert (not batch) or engine_hash, 'candidate config hash missing from batch metadata'
        records.append({'candidate_id':f'candidate_{i:03d}','requested_config_hash':ch,'engine_config_hash':engine_hash,'config':cfg,'batch':str(batch[0].parent) if batch else None,'fixture_hard_gate_pass':hard,'train_evaluator_result':ev,'engine_runtime_seconds':runtime,'error':err})
    valid=[r for r in records if r['fixture_hard_gate_pass']];selection='BASELINE_RETAINED / NO_SELECTION' if not valid or len(valid)<2 else 'BASELINE_RETAINED / NO_SELECTION'
    result={'schema_version':'character_dynamics_optimizer_v0_end_to_end_smoke','optimizer_seed':20260909,'selection':selection,'candidates':records,'holdout_read_during_search':False,'provenance':{'source_revision':a.source_revision,'manifest':str(a.manifest)},'runtime_seconds':time.perf_counter()-started}
    (a.out/'optimizer_smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'selection':selection,'candidates':len(records),'distinct_batches':len({r['batch'] for r in records if r['batch']})}))
if __name__=='__main__':main()
