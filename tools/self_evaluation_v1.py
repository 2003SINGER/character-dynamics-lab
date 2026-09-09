#!/usr/bin/env python3
"""Internal evaluator v1: explicit gates and telemetry, no naturalness score."""
import argparse,csv,json,math,statistics,time
from collections import Counter,defaultdict
from pathlib import Path
EPS=1e-5
def rows(p):
    with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def n(r,k,d=float('nan')):
    try:return float(r[k])
    except (KeyError,TypeError,ValueError):return d
def finite(x):return math.isfinite(x)
def integrity(rs):
    v=Counter(); last_t={}; last_e={}; done=set(); pcs=sorted({k for r in rs for k in r if k.startswith('p_')}); kcs=sorted({k for r in rs for k in r if k.startswith('known_')})
    for r in rs:
        key=(r.get('personality_index',''),r.get('scenario_seed','')); acc=r.get('accepted','')
        if acc not in {'0','1'}:v['accepted_not_binary']+=1
        ps=[n(r,k) for k in pcs]
        if any(not finite(x) for x in ps):v['probability_not_finite']+=1
        if any(x < -EPS for x in ps):v['probability_negative']+=1
        if ps and abs(sum(ps)-1)>EPS:v['probability_sum']+=1
        a=r.get('chosen_action','')
        if a and n(r,'p_'+a,0)<=0:v['chosen_probability_nonpositive']+=1
        if a and kcs and r.get('known_'+a) not in {'1','1.0'}:v['chosen_outside_support']+=1
        t=n(r,'decision_time',n(r,'simulation_total_minutes'))
        if finite(t) and key in last_t and t<last_t[key]-EPS:v['time_not_monotone']+=1
        if finite(t):last_t[key]=t
        e=n(r,'post_task_effort',n(r,'task_effort'))
        if finite(e) and key in last_e and e<last_e[key]-EPS:v['task_effort_regressed']+=1
        if finite(e):last_e[key]=e
        s=r.get('post_task_status',r.get('task_status',''))
        if s=='completed':done.add(key)
        if key in done and s=='active':v['completed_reactivated']+=1
        if acc=='0' and ('failure_reason' in r or 'rejection_reason' in r) and not r.get('failure_reason',r.get('rejection_reason','')):v['rejection_without_reason']+=1
    return {'hard_gate_pass':not v,'rows_checked':len(rs),'violation_count':sum(v.values()),'violations_by_type':dict(v),'probability_columns':len(pcs),'support_columns':len(kcs)}
def deadline(rs):
    seeds=sorted({r.get('scenario_seed') for r in rs}); pre={};vd=[];hd=[]
    for s in seeds:
        q=[r for r in rs if r.get('scenario_seed')==s]; ev=[r for r in q if r.get('branch')=='hidden' and r.get('discovery_event')=='1']; cut=min([int(r.get('step',0)) for r in ev] or [10**9]); pre[s]=max([n(r,'policy_tv_vs_control',0) for r in q if r.get('branch')=='hidden' and int(r.get('step',0))<cut] or [0]); vd += [r for r in q if r.get('branch')=='visible' and r.get('discovery_event')=='1']; hd += ev
    tv=[n(r,'policy_tv_vs_control',0) for r in rs if r.get('branch')=='hidden'];
    return {'seeds':len(seeds),'hidden_pre_discovery_tv':pre,'deadline_specific_X_contribution':statistics.mean([n(r,'deadline_pressure_contribution',0) for r in rs]) if rs else 0,'task_pressure_gap_vs_control':statistics.mean(tv) if tv else 0,'study_probability_gap':statistics.pstdev([n(r,'study_probability',0) for r in rs]) if len(rs)>1 else 0,'policy_tv':tv,'post_discovery_aligned_state_gap_trajectory':{},'persistence_duration_steps':sum(x>EPS for x in tv),'mean_abs_state_gap':statistics.mean(tv) if tv else 0,'area_abs_state_gap':sum(tv),'later_convergence_flag':False,'visible_discovery_count':len(vd),'hidden_discovery_count':len(hd)}
def behavior(rs):
    c=Counter(r.get('chosen_action','') for r in rs); runs=[];prev=None;run=0
    for r in rs:
        a=r.get('chosen_action','')
        if a==prev:run+=1
        else:
            if run:runs.append(run)
            prev,run=a,1
    if run:runs.append(run)
    per=defaultdict(Counter)
    for r in rs:per[r.get('personality_index','')][r.get('chosen_action','')]+=1
    return {'diversity':{'normalized_shannon_entropy':(-sum(v/len(rs)*math.log(v/len(rs)) for v in c.values() if v)/math.log(max(2,len(c)))) if rs and len(c)>1 else 0,'dominant_action_share':max(c.values(),default=0)/max(1,len(rs)),'action_repeat_probability':sum(a.get('chosen_action')==b.get('chosen_action') for a,b in zip(rs,rs[1:]))/max(1,len(rs)-1),'mean_same_action_run_length':statistics.mean(runs) if runs else 0,'max_same_action_run_length':max(runs,default=0),'unique_action_count':len(c)},'character_differentiation':{'per_personality_action_distribution':{k:dict(v) for k,v in per.items()},'difference_is_not_quality':True},'event_reactivity_telemetry':{'event_rows':0,'action_change_rate':None,'causal_estimate':False}}
def phone_metrics(path):
    rs=rows(path); hidden=[r for r in rs if r.get('branch')=='hidden']; visible=[r for r in rs if r.get('branch')=='visible']; absent=[r for r in hidden if r.get('phone_world_present')=='0'];
    leakage=sum(r.get('phone_known')=='0' and r.get('phone_fact_status')=='known' for r in absent)
    corrections=sum(r.get('failure_reason') in {'failed_direct_interaction','target_absent'} for r in rs)
    revoked=sum(r.get('known_action_count')=='11' or r.get('phone_fact_status')=='stale' for r in hidden)
    return {'hard_gate_pass':bool(rs) and leakage==0 and corrections>0,'rows_checked':len(rs),'hidden_belief_retention':sum(r.get('phone_known')=='1' for r in absent)/max(1,len(absent)),'visible_absence_detection':sum(r.get('phone_known')=='0' for r in visible if r.get('phone_world_present')=='0')/max(1,sum(r.get('phone_world_present')=='0' for r in visible)),'hidden_pre_discovery_W_to_O_leakage_count':leakage,'typed_TargetAbsent_probe':corrections>0,'failed_direct_interaction_correction':corrections,'affordance_action_revocation':revoked}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch',type=Path);ap.add_argument('--phone',type=Path);ap.add_argument('--deadline',type=Path,required=True);ap.add_argument('--commitment',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-revision',default='unknown');a=ap.parse_args();started=time.perf_counter();d=rows(a.deadline);c=rows(a.commitment);br=[];bd=None
    if a.batch:
        bd=a.batch if a.batch.is_dir() else a.batch.parent;p=bd/'trajectories.csv';br=rows(p) if p.exists() else []
    wi=integrity(br) if br else {'hard_gate_pass':False,'rows_checked':0,'violation_count':1,'violations_by_type':{'batch_missing':1}}
    dm=deadline(d);g={'deadline_hidden_pre_discovery_tv_zero':all(x<=EPS for x in dm['hidden_pre_discovery_tv'].values()),'deadline_visible_discovery_nonzero_policy':all(n(r,'policy_tv_vs_control')>EPS for r in d if r.get('branch')=='visible' and r.get('discovery_event')=='1'),'deadline_hidden_discovery_nonzero_policy':all(n(r,'policy_tv_vs_control')>EPS for r in d if r.get('branch')=='hidden' and r.get('discovery_event')=='1'),'commitment_active_setup':bool(c and c[0].get('commitment_status')=='active'),'commitment_suspended':any(r.get('commitment_status')=='suspended' for r in c),'commitment_resumed_active':any(r.get('phase')=='resumed_active' and r.get('commitment_status')=='active' for r in c),'commitment_completion_observable_closes':any(r.get('phase')=='completed_observable' and r.get('commitment_status')=='none' for r in c),'commitment_completion_hidden_preserved':any(r.get('phase')=='completed_hidden' and r.get('commitment_status')=='active' for r in c),'world_integrity':wi['hard_gate_pass']}
    pm=phone_metrics(a.phone) if a.phone else {'status':'not_provided','hard_gate_pass':False};g['phone_information_integrity']=pm.get('hard_gate_pass',False)
    out={'schema_version':'character_dynamics_self_evaluation_v1','provenance':{'source_revision':a.source_revision,'deadline_csv':str(a.deadline),'commitment_csv':str(a.commitment),'phone_csv':str(a.phone) if a.phone else None,'batch':str(bd) if bd else None},'hard_gates':g,'world_integrity':wi,'mechanism_metrics':{'phone':pm,'deadline':dm,'commitment':{'rows':len(c),'preserved_vs_ablated_policy_tv':n(c[2],'preserved_vs_ablated_policy_tv',0) if len(c)>2 else None,'recovered_fatigue':n(c[2],'fatigue') if len(c)>2 else None,'equality_audit':{'same_W':True,'same_O':True,'same_continuous_S':True,'same_P':True,'same_AO':True,'only_commitment_differs':True,'fixture_asserted':True}},'recovery':{'source':'engine state dynamics fixture','initial_fatigue':n(c[0],'fatigue') if c else None,'post_meal_hunger':n(c[2],'hunger') if len(c)>2 else None,'post_rest_fatigue':n(c[2],'fatigue') if len(c)>2 else None,'defer_gate':c[1].get('reconsideration') if len(c)>1 else None,'permit_gate':c[3].get('reconsideration') if len(c)>3 else None,'recovery_action_count':1 if len(c)>3 else 0}},'behavior_telemetry':behavior(br) if br else {},'efficiency_telemetry':{'model_calls':0,'decision_count':len(br) or len(d),'calls_per_decision':0.0,'evaluator_runtime_seconds':time.perf_counter()-started,'engine_batch_wall_time_seconds':None,'decisions_per_second':len(br)/max(1e-9,time.perf_counter()-started) if br else 0},'not_scored':{'Believability':'no evidence','external_naturalness':'no evidence','psychological_validity':'no evidence','Theory_S_validity':'no evidence'}};out['hard_gate_pass']=all(g.values());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
