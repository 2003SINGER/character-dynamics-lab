#!/usr/bin/env python3
"""LIGHT H0b: generic Replay action-transition interaction probe with permutation control."""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]))
from Replay.replay_features_v1 import compile_candidate_v1, vectorize, FEATURE_VERSION
from Replay.replay_probe_v1 import fit_no_state

SEED=20260909
def bucket(x): return int(hashlib.sha256(x.encode()).hexdigest()[:8],16)%10
def snap(o): return {'actor_observation':o,'entities':[],'possessions':[]}
def action_vec(action, observation, rules):
    f,_,_=compile_candidate_v1(str(action or ''),snap(observation),rules); return vectorize(f)
def prepare(rows,rules,kind,permuted=False):
    items=list(rows)
    if permuted:
        ordered=sorted(items,key=lambda r:hashlib.sha256((r['trajectory_id']+'::'+str(r['target_step_index'])).encode()).hexdigest())
        prev=[r.get('previous_source_action_A_star') for r in ordered]; prev2=[r.get('previous2_source_action_A_star') for r in ordered]
        if len(ordered)>1: prev=prev[1:]+prev[:1]; prev2=prev2[1:]+prev2[:1]
        remap={id(r):(prev[i],prev2[i]) for i,r in enumerate(ordered)}
    out=[]
    for r in items:
        cand=r.get('candidate_set_factual') or []; action=str(r.get('source_action_A_star') or ''); gold=next((i for i,c in enumerate(cand) if str(c).casefold()==action.casefold()),None)
        if gold is None or not cand: continue
        pa,p2=(remap[id(r)] if permuted else (r.get('previous_source_action_A_star'),r.get('previous2_source_action_A_star')))
        prevv=action_vec(pa,r.get('previous_source_O'),rules); prev2v=action_vec(p2,r.get('previous2_source_O'),rules)
        fs=[]
        for c in cand:
            cv=np.asarray(action_vec(c,r.get('source_O'),rules),float); pieces=[cv.tolist()]
            if kind in ('L1','L2'): pieces.append((cv*np.asarray(prevv)).tolist())
            if kind=='L2': pieces.append((cv*np.asarray(prev2v)).tolist())
            fs.append([z for part in pieces for z in part])
        out.append({'target_id':f"{r['trajectory_id']}::{r['target_step_index']}",'group_key':r['trajectory_id']+'::'+r['actor'],'features':fs,'gold_index':gold,'exact_previous_pair':bool(r.get('exact_previous_pair')),'history_surface':r.get('history_surface')})
    return out
def evaluate(model,groups):
    nll=mrr=top=0; n=0; units=defaultdict(list)
    for rs in groups.values():
        x=np.asarray(rs[0]['features']); means=np.asarray(model['means']); scales=np.asarray(model['scales']); theta=np.asarray(model['weights_theta']); z=((x-means)/scales)@theta; z-=z.max(); p=np.exp(z); p/=p.sum(); gold=rs[0]['gold_index']; order=np.argsort(-p).tolist(); loss=-math.log(max(float(p[gold]),1e-300)); nll+=loss; mrr+=1/(order.index(gold)+1); top+=int(order[0]==gold); n+=1; units[rs[0]['group_key']].append(loss)
    return {'rows':n,'mean_nll':nll/n,'mean_nll_bits':nll/math.log(2)/n,'mrr':mrr/n,'top1':top/n,'unit_count':len(units),'_units':{k:sum(v)/len(v) for k,v in units.items()}}
def delta_boot(base,other,seed=SEED,draws=2000):
    ids=sorted(set(base)&set(other)); rng=random.Random(seed); d=[other[i]-base[i] for i in ids]; vals=[]
    for _ in range(draws): vals.append(sum(d[rng.randrange(len(d))] for _ in d)/len(d))
    vals.sort(); return {'units':len(ids),'mean_delta_nll':sum(d)/len(d),'ci95':[vals[int(.025*draws)],vals[int(.975*draws)]],'delta_bits':sum(d)/len(d)/math.log(2)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('full_view',type=Path); ap.add_argument('rules',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--runner-commit',required=True); a=ap.parse_args(); rows=[json.loads(x) for x in a.full_view.open(encoding='utf-8') if x.strip()]; rules=json.loads(a.rules.read_text(encoding='utf-8')); units=sorted({r['trajectory_id']+'::'+r['actor'] for r in rows}); tr_units={u for u in units if bucket(u)<7}; te_units={u for u in units if bucket(u)>=9}
    result={'schema_version':'light_h0b_transition_probe_v0','runner_commit':a.runner_commit,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'feature_compiler_sha256':hashlib.sha256((Path(__file__).parents[1]/'Replay/replay_features_v1.py').read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256((Path(__file__).parents[1]/'Replay/replay_probe_v1.py').read_bytes()).hexdigest(),'rules_sha256':hashlib.sha256(a.rules.read_bytes()).hexdigest(),'full_view_sha256':hashlib.sha256(a.full_view.read_bytes()).hexdigest(),'feature_version':FEATURE_VERSION,'train_unit_count':len(tr_units),'test_unit_count':len(te_units),'conditions':{},'paired_unit_bootstrap_delta_nll':{}}
    saved={}
    for kind in ('L0','L1','L2'):
        for mode in ('correct','permuted'):
            rr=prepare(rows,rules,kind,permuted=(mode=='permuted')); tr=[r for r in rr if r['group_key'] in tr_units]; te=[r for r in rr if r['group_key'] in te_units]; tg=defaultdict(list); vg=defaultdict(list)
            for r in tr: tg[r['target_id']].append(r)
            for r in te: vg[r['target_id']].append(r)
            train_sets=[{'features':rs[0]['features'],'gold_index':rs[0]['gold_index']} for rs in tg.values()]; model=fit_no_state(train_sets,1e-2); groups={'full':vg,'nontrivial':{k:v for k,v in vg.items() if not v[0]['exact_previous_pair']},'contiguous':{k:v for k,v in vg.items() if v[0]['history_surface']=='CONTIGUOUS_SAME_ACTOR'},'gapped':{k:v for k,v in vg.items() if v[0]['history_surface']=='GAPPED_SAME_ACTOR'}}; key=f'{kind}_{mode}'; result['conditions'][key]={}; saved[key]={}
            for name,subset in groups.items():
                ev=evaluate(model,subset); saved[key][name]=ev.pop('_units'); result['conditions'][key][name]=ev
    for kind in ('L1','L2'):
        for name in ('full','nontrivial','contiguous','gapped'):
            result['paired_unit_bootstrap_delta_nll'][kind]={} if name=='full' else result['paired_unit_bootstrap_delta_nll'][kind]
            result['paired_unit_bootstrap_delta_nll'][kind][name]={'correct_vs_L0':delta_boot(saved['L0_correct'][name],saved[f'{kind}_correct'][name]),'correct_vs_permuted':delta_boot(saved[f'{kind}_permuted'][name],saved[f'{kind}_correct'][name])}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
