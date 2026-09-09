#!/usr/bin/env python3
"""LIGHT actor-local candidate-support probe using the frozen generic Replay readout."""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from collections import defaultdict, Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from Replay.replay_features_v1 import compile_candidate_v1, vectorize, FEATURE_VERSION
from Replay.replay_probe_v1 import fit_no_state, predict

def bootstrap_delta(base, other, seed=20260909, draws=2000):
    import random
    ids=sorted(set(base)&set(other)); rng=random.Random(seed); vals=[]
    for _ in range(draws):
        sample=[ids[rng.randrange(len(ids))] for _ in ids]; vals.append(sum(other[i]-base[i] for i in sample)/len(sample))
    vals.sort(); return {'units':len(ids),'mean_delta_nll':sum(other[i]-base[i] for i in ids)/len(ids),'ci95':[vals[int(.025*draws)],vals[int(.975*draws)]],'delta_bits':(sum(other[i]-base[i] for i in ids)/len(ids))/math.log(2)}

def bucket(unit):
    return int(hashlib.sha256(unit.encode()).hexdigest()[:8],16)%10

def snap(r):
    return {'actor_observation':r.get('source_O'),'entities':[],'possessions':[]}

def make_rows(rows,rules,kind):
    out=[]
    for r in rows:
        cand=r.get('candidate_set_factual') or []; action=str(r.get('source_action_A_star') or '')
        gold=next((i for i,c in enumerate(cand) if str(c).casefold()==action.casefold()),None)
        if gold is None or not cand: continue
        hist=[r.get('previous_source_action_A_star'),r.get('previous2_source_action_A_star')]
        for c in cand:
            f,_,_=compile_candidate_v1(str(c),snap(r),rules); v=vectorize(f)
            if kind in ('L1','L2'): v.append(float(str(c).casefold()==str(hist[0] or '').casefold()))
            if kind=='L2': v.append(float(str(c).casefold()==str(hist[1] or '').casefold()))
            out.append({'unit':f"{r['trajectory_id']}::{r['actor']}",'target_id':f"{r['trajectory_id']}::{r['target_step_index']}",'features':v,'gold_index':gold,'candidate_count':len(cand),'candidate':c,'prev_action':hist[0],'exact_previous_pair':bool(r.get('exact_previous_pair')),'history_surface':r.get('history_surface'),'group_key':r['trajectory_id']+'::'+r['actor']})
    return out

def evaluate_model(model, groups):
    nll=0; mrr=0; top=0; n=0; units=set(); unit_nll=defaultdict(list)
    for rs in groups.values():
        # The generic probe stores one candidate-set row; score its candidate matrix directly.
        import numpy as np
        xs=np.asarray([x['features'] for x in rs],float); means=np.asarray(model['means']); scales=np.asarray(model['scales']); theta=np.asarray(model['weights_theta']); z=((xs-means)/scales)@theta; z-=z.max(); p=np.exp(z); p/=p.sum(); gold=rs[0]['gold_index']; order=np.argsort(-p).tolist(); row_nll=-math.log(max(float(p[gold]),1e-300)); nll+=row_nll; mrr+=1/(order.index(gold)+1); top+=int(order[0]==gold); n+=1; units.add(rs[0]['group_key']); unit_nll[rs[0]['group_key']].append(row_nll)
    return {'rows':n,'mean_nll':nll/n if n else None,'mean_nll_bits':nll/math.log(2)/n if n else None,'mrr':mrr/n if n else None,'top1':top/n if n else None,'unit_count':len(units),'_unit_nll':{k:sum(v)/len(v) for k,v in unit_nll.items()}}

def baseline_uniform(groups):
    vals=[]; rr=[]; top=[]; rn=[]; rrr=[]; rt=[]
    for rs in groups.values():
        k=len(rs); gold=rs[0]['gold_index']; vals.append(math.log(k)); rr.append(1/k); top.append(1/k); prev=str(rs[0].get('prev_action') or '').casefold(); hit=next((i for i,x in enumerate(rs) if str(x['candidate']).casefold()==prev),None)
        if hit is None: rn.append(math.log(k)); rrr.append(1/k); rt.append(1/k)
        else: rn.append(-math.log(1-1e-3) if hit==gold else -math.log(1e-3/(k-1))); rrr.append(1.0 if hit==gold else 1/(sorted(range(k),key=lambda i:i!=hit).index(gold)+1)); rt.append(float(hit==gold))
    return {'uniform':{'rows':len(vals),'mean_nll':sum(vals)/len(vals),'mean_nll_bits':sum(vals)/len(vals)/math.log(2),'mrr':sum(rr)/len(rr),'top1':sum(top)/len(top)},'repeat_last_same_actor':{'rows':len(vals),'mean_nll':sum(rn)/len(rn),'mean_nll_bits':sum(rn)/len(rn)/math.log(2),'mrr':sum(rrr)/len(rrr),'top1':sum(rt)/len(rt),'nll_smoothing_epsilon':1e-3}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('full_view',type=Path); ap.add_argument('rules',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--runner-commit',required=True); a=ap.parse_args()
    rows=[json.loads(x) for x in a.full_view.open(encoding='utf-8') if x.strip()]; rules=json.loads(a.rules.read_text(encoding='utf-8')); units=sorted({r['trajectory_id']+'::'+r['actor'] for r in rows}); train_units={u for u in units if bucket(u)<7}; test_units={u for u in units if bucket(u)>=9}
    result={'schema_version':'light_actor_local_history_probe_v0','runner_commit':a.runner_commit,'full_view_sha256':hashlib.sha256(a.full_view.read_bytes()).hexdigest(),'rules_sha256':hashlib.sha256(a.rules.read_bytes()).hexdigest(),'feature_version':FEATURE_VERSION,'unit_count':len(units),'train_unit_count':len(train_units),'test_unit_count':len(test_units),'conditions':{},'baselines':{}}
    for kind in ('L0','L1','L2'):
        allr=make_rows(rows,rules,kind); tr=[x for x in allr if x['group_key'] in train_units]; te=[x for x in allr if x['group_key'] in test_units]; tg=defaultdict(list); vg=defaultdict(list)
        for x in tr: tg[x['target_id']].append(x)
        for x in te: vg[x['target_id']].append(x)
        train_sets=[{'features':[x['features'] for x in rs],'gold_index':rs[0]['gold_index']} for rs in tg.values()]
        model=fit_no_state(train_sets,1e-2); strata={'full':vg,'nontrivial':{k:v for k,v in vg.items() if not v[0]['exact_previous_pair']},'contiguous':{k:v for k,v in vg.items() if v[0]['history_surface']=='CONTIGUOUS_SAME_ACTOR'},'gapped':{k:v for k,v in vg.items() if v[0]['history_surface']=='GAPPED_SAME_ACTOR'}}; result['conditions'][kind]={name:evaluate_model(model,subset) for name,subset in strata.items()}; result['conditions'][kind]['candidate_count_bins']=dict(Counter('1-2' if len(v)<=2 else '3-5' if len(v)<=5 else '6-10' if len(v)<=10 else '11+' for v in vg.values()))
        if kind=='L0': result['baselines']=baseline_uniform(vg)
    base_maps={name:result['conditions']['L0'][name].pop('_unit_nll') for name in ('full','nontrivial','contiguous','gapped')}
    result['paired_unit_bootstrap_delta_nll']={}
    for kind in ('L1','L2'):
        result['paired_unit_bootstrap_delta_nll'][kind]={}
        for name in ('full','nontrivial','contiguous','gapped'):
            o=result['conditions'][kind][name].pop('_unit_nll'); result['paired_unit_bootstrap_delta_nll'][kind][name]=bootstrap_delta(base_maps[name],o)
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
