#!/usr/bin/env python3
"""Build LIGHT actor-local history surfaces and audit eligibility (no model fitting)."""
from __future__ import annotations
import argparse, collections, hashlib, json
from pathlib import Path

def norm(x): return str(x or '').strip().casefold()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('replay',type=Path); ap.add_argument('out_dir',type=Path); a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    full=a.out_dir/'light_actor_local_full_v0.jsonl'; non=a.out_dir/'light_actor_local_nontrivial_v0.jsonl'
    counts=collections.Counter(); gap=collections.Counter(); cand=collections.Counter(); actor_units=set(); rows=0; nonrows=0; exact=0; raw_repeat=0; cand_hits=0; prev_cand_hits=0; o_nonempty=0; depth_counts=collections.Counter(); contiguous=0; gapped=0
    with a.replay.open(encoding='utf-8') as src, full.open('w',encoding='utf-8',newline='\n') as ff, non.open('w',encoding='utf-8',newline='\n') as nf:
        for line in src:
            if not line.strip(): continue
            rec=json.loads(line); ctx=rec.get('source_episode_context') or {}
            if ctx.get('quarantine'): counts['quarantined_trajectories']+=1; continue
            physical=[(i,s) for i,s in enumerate(rec.get('steps') or []) if norm(s.get('source_action_A_star')) and norm((s.get('source_step_context') or {}).get('actor'))]
            by_actor=collections.defaultdict(list)
            for pos,(i,s) in enumerate(physical):
                actor=norm((s.get('source_step_context') or {}).get('actor')); hist=by_actor[actor]; prev=hist[-1] if hist else None; prev2=hist[-2] if len(hist)>1 else None
                if prev is None: hist.append((pos,i,s)); continue
                actor_units.add((rec.get('trajectory_id'),actor)); rows+=1; depth=len(hist); depth_counts[min(depth,4)]+=1
                current_o=s.get('source_O'); action=s.get('source_action_A_star'); candidates=s.get('candidate_set_factual') if isinstance(s.get('candidate_set_factual'),list) else []
                prev_s=prev[2]; prev_action=prev_s.get('source_action_A_star'); same_o=current_o==prev_s.get('source_O'); same_raw=action==prev_action; exact_pair=same_o and same_raw
                intervening=pos-prev[0]-1; other=sum(1 for _,x in physical[prev[0]+1:pos] if norm((x.get('source_step_context') or {}).get('actor'))!=actor)
                surface='CONTIGUOUS_SAME_ACTOR' if intervening==0 else 'GAPPED_SAME_ACTOR'; contiguous+=surface.startswith('CONTIGUOUS'); gapped+=surface.startswith('GAPPED'); gap[min(intervening,4)]+=1
                cand[len(candidates)]+=1; o_nonempty+=int(bool(str(current_o or '').strip())); cand_hits+=int(norm(action) in {norm(x) for x in candidates}); prev_cand_hits+=int(norm(prev_action) in {norm(x) for x in candidates}); raw_repeat+=int(same_raw); exact+=int(exact_pair)
                row={'trajectory_id':rec.get('trajectory_id'),'actor':actor,'target_step_index':i,'previous_same_actor_t':prev[1],'previous2_same_actor_t':prev2[1] if prev2 else None,'actor_history_depth':depth,'intervening_physical_rows':intervening,'intervening_other_actor_rows':other,'history_surface':surface,'source_O':current_o,'source_action_A_star':action,'candidate_set_factual':candidates,'previous_source_O':prev_s.get('source_O'),'previous_source_action_A_star':prev_action,'previous2_source_O':prev2[2].get('source_O') if prev2 else None,'previous2_source_action_A_star':prev2[2].get('source_action_A_star') if prev2 else None,'exact_previous_pair':exact_pair,'raw_action_repeat':same_raw,'a_star_in_source_candidates':norm(action) in {norm(x) for x in candidates},'previous_a_star_in_current_candidates':norm(prev_action) in {norm(x) for x in candidates}}
                ff.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
                if not exact_pair: nf.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n'); nonrows+=1
                hist.append((pos,i,s))
    report={'schema_version':'light_actor_local_history_gate_v0','replay_sha256':hashlib.sha256(a.replay.read_bytes()).hexdigest(),'full_view_path':full.name,'nontrivial_view_path':non.name,'actor_trajectory_units':len(actor_units),'eligible_targets':rows,'nontrivial_targets':nonrows,'history_depth_ge_1':rows,'history_depth_ge_2':sum(v for k,v in depth_counts.items() if k>=2),'history_depth_ge_3':sum(v for k,v in depth_counts.items() if k>=3),'history_depth_ge_4':sum(v for k,v in depth_counts.items() if k>=4),'contiguous_targets':contiguous,'gapped_targets':gapped,'gap_distribution':dict(gap),'source_O_nonempty_rate':o_nonempty/rows if rows else 0,'candidate_count_distribution':dict(cand),'a_star_in_source_candidates_rate':cand_hits/rows if rows else 0,'previous_a_star_in_current_candidates_rate':prev_cand_hits/rows if rows else 0,'raw_previous_action_equals_current_rate':raw_repeat/rows if rows else 0,'exact_previous_pair_rate':exact/rows if rows else 0,'quarantined_trajectories':counts['quarantined_trajectories'],'protocol':'same trajectory, same actor, non-quarantine, prior physical-action row only; other actor actions never enter action history; source candidate list remains observed support, not A^O'}
    (a.out_dir/'light_actor_local_history_gate_v0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
