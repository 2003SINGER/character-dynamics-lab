#!/usr/bin/env python3
"""Deterministic development-only 0.8x/1.0x/1.2x parameter audit."""
import argparse,csv,hashlib,json,subprocess,statistics
from pathlib import Path
PARAMS=['state_accumulation','state_recovery_strength','state_decay','task_pressure_coupling','study_fatigue_penalty','task_drive_coefficient','distraction_weight','commitment_bonus','recovery_drive_coefficient']
def run(engine,config,manifest,out):
    out.mkdir(parents=True,exist_ok=True);p=out/'config.json';p.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8');
    subprocess.run([str(engine),'--batch',str(out/'batch'),'--config',str(p),'--split-manifest',str(manifest),'--split','optimizer_train'],check=True,capture_output=True)
    t=next((out/'batch').glob('run_*/trajectories.csv'));rs=list(csv.DictReader(t.open(encoding='utf-8',newline='')));return rs,(t.parent/'metadata.txt').read_text(encoding='utf-8')
def summary(rs):
    return {'mean_fatigue':statistics.mean(float(r['pre_fatigue']) for r in rs),'mean_task_pressure':statistics.mean(float(r['pre_task_pressure']) for r in rs),'mean_study_probability':statistics.mean(sum(float(r.get('p_'+a,0)) for a in ('study_at_computer','study_focused','study_halfhearted')) for r in rs),'mean_recovery_probability':statistics.mean(sum(float(r.get('p_'+a,0)) for a in ('rest_at_bed','sleep_at_bed')) for r in rs),'mean_distraction_probability':statistics.mean(sum(float(r.get('p_'+a,0)) for a in ('use_phone','shop_on_phone','use_computer')) for r in rs),'mean_effort':statistics.mean(float(r['post_task_effort']) for r in rs),'chosen_actions': [r['chosen_action'] for r in rs]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-revision',default='unknown');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);manifest=a.out/'manifest.json';manifest.write_text(json.dumps({'optimizer_train_world_seeds':[1101],'internal_holdout_world_seeds':[2101]}),encoding='utf-8');base={k:1.0 for k in PARAMS};cases=[('default',None,1.0)]+[(f'{p}_{label}',p,value) for p in PARAMS for label,value in [('low',.8),('high',1.2)]];results=[];cache={}
    for name,param,value in cases:
        cfg=dict(base)
        if param:cfg[param]=value
        rs,metadata=run(a.engine,cfg,manifest,a.out/name);s=summary(rs);cache[name]=s;results.append({'case':name,'parameter':param,'value':value,'config':cfg,'engine_config_hash':next((x.split('=',1)[1] for x in metadata.splitlines() if x.startswith('parameter_config_hash=')),None),'summary':{k:v for k,v in s.items() if k!='chosen_actions'}})
    base_s=cache['default']; expected={'state_accumulation':('mean_task_pressure',1),'state_recovery_strength':('mean_fatigue',-1),'state_decay':('mean_task_pressure',-1),'task_pressure_coupling':('mean_task_pressure',1),'study_fatigue_penalty':('mean_study_probability',-1),'task_drive_coefficient':('mean_study_probability',1),'distraction_weight':('mean_distraction_probability',1),'commitment_bonus':('mean_study_probability',1),'recovery_drive_coefficient':('mean_recovery_probability',1)}
    for r in results:
        if r['parameter']:
            s=cache[r['case']];r['delta_vs_default']={k:s[k]-base_s[k] for k in ('mean_fatigue','mean_task_pressure','mean_study_probability','mean_recovery_probability','mean_distraction_probability','mean_effort')};r['chosen_action_difference_count']=sum(x!=y for x,y in zip(s['chosen_actions'],base_s['chosen_actions']));metric,sign=expected[r['parameter']];r['intended_estimand']=metric;r['expected_direction']='increase' if sign>0 else 'decrease';r['direction_pass']=(r['delta_vs_default'][metric]*sign)>1e-8
    direction_cases=[r for r in results if r['parameter']];all_hashes=all(r.get('engine_config_hash') for r in results);all_directions=all(r.get('direction_pass',False) for r in direction_cases);out={'schema_version':'character_dynamics_parameter_sensitivity_v0','source_revision':a.source_revision,'probe_seed':1101,'personality_count':32,'cases':results,'status':'PASS' if all_hashes and all_directions else ('PARTIAL' if all_hashes else 'FAIL'),'direction_failures':[r['case'] for r in direction_cases if not r.get('direction_pass',False)],'holdout_read':False};(a.out/'sensitivity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':out['status'],'cases':len(results),'direction_failures':len(out['direction_failures'])}))
if __name__=='__main__':main()
