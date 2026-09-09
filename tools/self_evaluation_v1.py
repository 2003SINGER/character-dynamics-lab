#!/usr/bin/env python3
"""Character Dynamics internal evaluator v1 (no aggregate naturalness score)."""
import argparse,csv,json,math,statistics,time
from collections import Counter,defaultdict
from pathlib import Path
EPS=1e-5
def rows(p):
    with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def num(r,k,d=float('nan')):
    try:return float(r[k])
    except (KeyError,TypeError,ValueError):return d
def finite(x):return math.isfinite(x)
def integrity(rs):
    v=Counter();last_t={};last_e={};done=set();pcs=sorted({k for r in rs for k in r if k.startswith('p_')});kcs=sorted({k for r in rs for k in r if k.startswith('known_')})
    for r in rs:
        key=(r.get('personality_index',''),r.get('scenario_seed',''));acc=r.get('accepted','')
        if acc not in {'0','1'}:v['accepted_not_binary']+=1
        ps=[num(r,k) for k in pcs]
        if any(not finite(x) for x in ps):v['probability_not_finite']+=1
        if any(x < -EPS for x in ps):v['probability_negative']+=1
        if ps and abs(sum(ps)-1)>EPS:v['probability_sum']+=1
        a=r.get('chosen_action','')
        if a and num(r,'p_'+a,0)<=0:v['chosen_probability_nonpositive']+=1
        if a and kcs and r.get('known_'+a) not in {'1','1.0'}:v['chosen_outside_support']+=1
        t=num(r,'simulation_total_minutes',num(r,'decision_total_minutes'))
        if finite(t) and key in last_t and t<last_t[key]-EPS:v['time_not_monotone']+=1
        if finite(t):last_t[key]=t
        e=num(r,'post_task_effort',num(r,'task_effort'))
        if finite(e) and key in last_e and e<last_e[key]-EPS:v['task_effort_regressed']+=1
        if finite(e):last_e[key]=e
        s=r.get('post_task_status',r.get('task_status',''))
        if s=='completed':done.add(key)
        if key in done and s=='active':v['completed_reactivated']+=1
        if ('failure_reason' in r or 'rejection_reason' in r) and acc=='0' and not r.get('failure_reason',r.get('rejection_reason','')):v['rejection_without_reason']+=1
    return {'hard_gate_pass':not v,'rows_checked':len(rs),'violation_count':sum(v.values()),'violations_by_type':dict(v),'probability_columns':len(pcs),'support_columns':len(kcs),'time_check_observable':bool(last_t),'rejection_reason_check_observable':any('failure_reason' in r for r in rs)}
def aligned_deadline(rs):
    by={(r.get('scenario_seed'),int(r.get('step',0)),r.get('branch')):r for r in rs};seeds=sorted({r.get('scenario_seed') for r in rs}); pre={}; discovery={}; post={}; xvals=[]
    for s in seeds:
        rows_s=[r for r in rs if r.get('scenario_seed')==s]; hidden_steps=[int(r.get('step',0)) for r in rows_s if r.get('branch')=='hidden' and r.get('discovery_event')=='1']; visible_steps=[int(r.get('step',0)) for r in rows_s if r.get('branch')=='visible' and r.get('discovery_event')=='1']; cut=min(hidden_steps or [10**9]);
        pre[s]=max([num(r,'policy_tv_vs_control',0) for r in rows_s if r.get('branch')=='hidden' and int(r.get('step',0))<cut] or [0]); discovery[s]={}
        for branch,steps in [('visible',visible_steps),('hidden',hidden_steps)]:
            if not steps:continue
            step=min(steps); b=by.get((s,step,branch)); ctrl=by.get((s,step,'control'))
            if b and ctrl: discovery[s][branch]={'step':step,'deadline_pressure_contribution':num(b,'deadline_pressure_contribution',0),'task_pressure_gap_vs_control':num(b,'pre_task_pressure')-num(ctrl,'pre_task_pressure'),'study_probability_gap_vs_control':num(b,'study_probability')-num(ctrl,'study_probability'),'policy_tv_vs_control':num(b,'policy_tv_vs_control',0)};xvals.append(num(b,'deadline_pressure_contribution',0))
        post[s]={}
        for branch in ('visible','hidden'):
            start=min((discovery[s].get(branch,{}).get('step',10**9),),default=10**9);traj=[]
            for step in sorted({int(r.get('step',0)) for r in rows_s}):
                if step<=start:continue
                b=by.get((s,step,branch));ctrl=by.get((s,step,'control'))
                if b and ctrl:
                    gap=num(b,'pre_task_pressure')-num(ctrl,'pre_task_pressure');traj.append({'step':step,'state_gap':gap,'abs_state_gap':abs(gap),'policy_tv_vs_control':num(b,'policy_tv_vs_control',0)})
            first=next((x['step'] for x in traj if x['abs_state_gap']<=EPS),None);post[s][branch]={'trajectory':traj,'mean_abs_state_gap':statistics.mean([x['abs_state_gap'] for x in traj]) if traj else 0,'area_abs_state_gap':sum(x['abs_state_gap'] for x in traj),'nonzero_points':sum(x['abs_state_gap']>EPS for x in traj),'first_convergence_step':first,'later_convergence_flag':first is not None}
    hidden_post=[x for s in post.values() for x in [s.get('hidden',{})] if x]; vals=[x['mean_abs_state_gap'] for x in hidden_post]
    return {'seeds':len(seeds),'hidden_pre_discovery_tv':pre,'discovery_metrics':discovery,'deadline_specific_X_contribution_at_discovery':statistics.mean(xvals) if xvals else 0,'post_discovery_state_persistence':post,'mean_abs_state_gap':statistics.mean(vals) if vals else 0,'later_convergence_flag':all(x['later_convergence_flag'] for x in hidden_post) if hidden_post else False}
def js(p,q):
    keys=set(p)|set(q);m={k:(p.get(k,0)+q.get(k,0))/2 for k in keys}
    def kl(a):return sum(v*math.log(v/m[k]) for k,v in a.items() if v and m[k])
    return .5*kl(p)+.5*kl(q)
def behavior(rs):
    groups=defaultdict(list)
    for r in rs:groups[(r.get('personality_index'),r.get('scenario_seed'))].append(r)
    runs=[];repeats=[];events=0;changes=0
    for q in groups.values():
        q.sort(key=lambda r:int(r.get('step',0)));acts=[r.get('chosen_action','') for r in q];repeats += [a==b for a,b in zip(acts,acts[1:])];run=1;prev=None
        for a in acts:
            if a==prev:run+=1
            else:
                if prev is not None:runs.append(run)
                prev,run=a,1
        if prev is not None:runs.append(run)
        for i,r in enumerate(q[:-1]):
            if r.get('event_ids'):
                events+=1;changes+=q[i+1].get('chosen_action')!=r.get('chosen_action')
    per=defaultdict(Counter)
    for r in rs:per[r.get('personality_index','')][r.get('chosen_action','')]+=1
    dists={k:{a:v/sum(c.values()) for a,v in c.items()} for k,c in per.items()};vals=[js(dists[a],dists[b]) for i,a in enumerate(dists) for b in list(dists)[i+1:]]
    c=Counter(r.get('chosen_action','') for r in rs);n=len(rs)
    return {'diversity':{'normalized_shannon_entropy':-sum(v/n*math.log(v/n) for v in c.values() if v)/math.log(max(2,len(c))) if n and len(c)>1 else 0,'dominant_action_share':max(c.values(),default=0)/max(1,n),'action_repeat_probability':statistics.mean(repeats) if repeats else 0,'mean_same_action_run_length':statistics.mean(runs) if runs else 0,'max_same_action_run_length':max(runs,default=0),'unique_action_count':len(c)},'character_differentiation':{'per_personality_action_distribution':dists,'pairwise_JS_divergence':{'mean':statistics.mean(vals) if vals else 0,'median':statistics.median(vals) if vals else 0,'min':min(vals) if vals else 0,'max':max(vals) if vals else 0},'difference_is_not_quality':True},'event_reactivity_telemetry':{'event_rows':events,'action_change_rate':changes/max(1,events),'causal_estimate':False}}
def phone(path):
    rs=rows(path);hidden=[r for r in rs if r.get('branch')=='hidden'];absent=[r for r in hidden if r.get('phone_world_present')=='0'];cor=sum(r.get('failure_reason') in {'failed_direct_interaction','target_absent'} for r in rs);leak=sum(r.get('phone_known')=='0' and r.get('phone_fact_status')=='known' for r in absent)
    return {'hard_gate_pass':bool(rs) and leak==0 and cor>0,'rows_checked':len(rs),'hidden_belief_retention':sum(r.get('phone_known')=='1' for r in absent)/max(1,len(absent)),'visible_absence_detection':sum(r.get('phone_known')=='0' and r.get('phone_world_present')=='0' for r in rs if r.get('branch')=='visible')/max(1,sum(r.get('phone_world_present')=='0' for r in rs if r.get('branch')=='visible')),'hidden_pre_discovery_W_to_O_leakage_count':leak,'typed_TargetAbsent_probe':cor>0,'failed_direct_interaction_correction':cor,'affordance_action_revocation':sum(r.get('phone_fact_status')=='stale' for r in rs)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch',type=Path);ap.add_argument('--phone',type=Path);ap.add_argument('--deadline',type=Path,required=True);ap.add_argument('--commitment',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-revision',default='unknown');a=ap.parse_args();start=time.perf_counter();d=rows(a.deadline);c=rows(a.commitment);br=[];bd=None
    if a.batch:bd=a.batch if a.batch.is_dir() else a.batch.parent;p=bd/'trajectories.csv';br=rows(p) if p.exists() else []
    wi=integrity(br) if br else {'hard_gate_pass':False,'rows_checked':0,'violation_count':1,'violations_by_type':{'batch_missing':1}}
    dm=aligned_deadline(d);pm=phone(a.phone) if a.phone else {'hard_gate_pass':False,'status':'not_provided'};snap=next((r for r in c if r.get('phase')=='recovered_after_rest'),{});eq={k:(bool(snap.get(k)) and snap.get(k)==snap.get('ablated_'+k)) for k in ['world_hash','observation_hash','continuous_state_hash','personality_hash','ao_hash']};eq={'same_W':eq.get('world_hash',False),'same_O':eq.get('observation_hash',False),'same_continuous_S':eq.get('continuous_state_hash',False),'same_P':eq.get('personality_hash',False),'same_AO':eq.get('ao_hash',False)};eq['only_commitment_differs']=all(eq.values())
    gates={'deadline_hidden_pre_discovery_tv_zero':all(x<=EPS for x in dm['hidden_pre_discovery_tv'].values()),'deadline_discovery_metrics_present':bool(dm['discovery_metrics']),'commitment_active_setup':bool(c and c[0].get('commitment_status')=='active'),'commitment_suspended':any(r.get('commitment_status')=='suspended' for r in c),'commitment_resumed_active':any(r.get('phase')=='resumed_active' and r.get('commitment_status')=='active' for r in c),'commitment_completion_observable_closes':any(r.get('phase')=='completed_observable' and r.get('commitment_status')=='none' for r in c),'commitment_completion_hidden_preserved':any(r.get('phase')=='completed_hidden' and r.get('commitment_status')=='active' for r in c),'commitment_equality_audit':eq['only_commitment_differs'],'world_integrity':wi['hard_gate_pass'],'phone_information_integrity':pm.get('hard_gate_pass',False)}
    recovery={'source':'engine state dynamics fixture','pre_meal_fatigue':next((num(r,'fatigue') for r in c if r.get('phase')=='setup_active'),None),'post_meal_hunger':next((num(r,'hunger') for r in c if r.get('phase')=='interrupted_after_meal'),None),'pre_rest_fatigue':next((num(r,'fatigue') for r in c if r.get('phase')=='deferred_before_rest'),None),'post_rest_fatigue':next((num(r,'fatigue') for r in c if r.get('phase')=='recovered_after_rest'),None),'defer_gate':next((r.get('reconsideration') for r in c if r.get('phase')=='deferred_before_rest'),None),'permit_gate':next((r.get('reconsideration') for r in c if r.get('phase')=='recovered_after_rest'),None),'recovery_action_count':sum(r.get('phase') in {'interrupted_after_meal','recovered_after_rest'} for r in c),'recovery_elapsed_minutes':(num(next((r for r in c if r.get('phase')=='recovered_after_rest'),{}),'simulation_total_minutes',0)-num(next((r for r in c if r.get('phase')=='interrupted_after_meal'),{}),'simulation_total_minutes',0))}
    out={'schema_version':'character_dynamics_self_evaluation_v1','provenance':{'source_revision':a.source_revision,'deadline_csv':str(a.deadline),'commitment_csv':str(a.commitment),'phone_csv':str(a.phone) if a.phone else None,'batch':str(bd) if bd else None},'hard_gates':gates,'world_integrity':wi,'mechanism_metrics':{'phone':pm,'deadline':dm,'commitment':{'rows':len(c),'preserved_vs_ablated_policy_tv':next((num(r,'preserved_vs_ablated_policy_tv') for r in c if r.get('phase')=='recovered_after_rest'),None),'equality_audit':eq},'recovery':recovery},'behavior_telemetry':behavior(br) if br else {},'efficiency_telemetry':{'model_calls':0,'decision_count':len(br) or len(d),'calls_per_decision':0.0,'evaluator_runtime_seconds':time.perf_counter()-start,'evaluator_rows_per_second':(len(br) or len(d))/max(1e-9,time.perf_counter()-start),'engine_batch_wall_time_seconds':None,'engine_decisions_per_second':None},'not_scored':{'Believability':'no evidence','external_naturalness':'no evidence','psychological_validity':'no evidence','Theory_S_validity':'no evidence'}};out['hard_gate_pass']=all(gates.values());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'hard_gate_pass':out['hard_gate_pass'],'world_integrity':wi['hard_gate_pass'],'phone_information_integrity':pm.get('hard_gate_pass',False)}))
if __name__=='__main__':main()
