#!/usr/bin/env python3
"""Full filtered-OPeRA trajectory structure statistics; no model fitting."""
import argparse, hashlib, json
from collections import Counter
from math import log2
from pathlib import Path
import pandas as pd

REVISION = "6f26a2c5cc69084f1714e39db9776e61791344d6"

def entropy(values):
    c = Counter(values); n = sum(c.values())
    return -sum((v/n) * log2(v/n) for v in c.values()) if n else 0.0

def main():
    p = argparse.ArgumentParser(); p.add_argument('--raw-dir', type=Path, required=True); p.add_argument('--out', type=Path, required=True); a=p.parse_args()
    sessions = pd.concat([pd.read_parquet(a.raw_dir/'session-train.parquet'), pd.read_parquet(a.raw_dir/'session-test.parquet')], ignore_index=True)
    action_paths = sorted(a.raw_dir.glob('train-*.parquet')) + sorted(a.raw_dir.glob('test-*.parquet'))
    actions = pd.concat([pd.read_parquet(x, columns=['session_id','action_type','click_type']) for x in action_paths], ignore_index=True)
    lengths = sessions.action_count.astype(int)
    thresholds = {f'>={k}': int((lengths >= k).sum()) for k in (10,20,30,50,100)}
    user_counts = sessions.groupby('user_id').size()
    user_long = {str(k): int(sessions.loc[lengths >= k, 'user_id'].nunique()) for k in (10,20,30)}
    user_order = sorted(user_counts.index, key=lambda u: (hashlib.sha256(str(u).encode()).hexdigest(), str(u)))
    test_users = set(user_order[:max(1, round(len(user_order)*0.2))]); split = sessions.user_id.map(lambda u: 'test' if u in test_users else 'train')
    long_label = actions.session_id.isin(set(sessions.loc[lengths >= 20, 'session_id']))
    long_actions = actions[long_label]
    result = {
      'purpose':'T0d+ full filtered OPeRA trajectory structure statistics; no training or Paper-0 result',
      'source':{'dataset':'NEU-HAI/OPeRA','revision':REVISION,'license':'CC-BY-4.0'},
      'all_sessions':{'count':int(len(sessions)),'length_min':int(lengths.min()),'p25':float(lengths.quantile(.25)),'median':float(lengths.median()),'p75':float(lengths.quantile(.75)),'p90':float(lengths.quantile(.90)),'max':int(lengths.max()),'threshold_counts':thresholds},
      'users':{'count':int(user_counts.size),'sessions_per_user_min':int(user_counts.min()),'median':float(user_counts.median()),'p75':float(user_counts.quantile(.75)),'p90':float(user_counts.quantile(.90)),'max':int(user_counts.max()),'users_with_2plus_sessions':int((user_counts>=2).sum()),'users_with_5plus_sessions':int((user_counts>=5).sum()),'users_with_10plus_sessions':int((user_counts>=10).sum()),'users_with_long_sessions':user_long},
      'deterministic_user_disjoint_80_20':{'method':'SHA-256 user-id rank; lowest 20% users test','train_users':int(len(user_order)-len(test_users)),'test_users':int(len(test_users)),'train_sessions':int((split=='train').sum()),'test_sessions':int((split=='test').sum()),'thresholds_train':{f'>={k}':int(((lengths>=k)&(split=='train')).sum()) for k in (10,20,30)},'thresholds_test':{f'>={k}':int(((lengths>=k)&(split=='test')).sum()) for k in (10,20,30)}},
      'long_session_label_entropy':{'definition':'all actions in sessions with >=20 actions; descriptive only','action_count':int(len(long_actions)),'action_type_entropy_bits':entropy(long_actions.action_type.astype(str)),'action_type_counts':dict(Counter(long_actions.action_type.astype(str))), 'click_type_entropy_bits':entropy([str(x) for x in long_actions.click_type.tolist() if pd.notna(x)]),'click_type_counts':dict(Counter(str(x) for x in long_actions.click_type.tolist() if pd.notna(x)))},
      'interpretation_boundary':{'persistent_state':'length alone does not prove state accumulation; >=20 sessions are a feasibility pool, not evidence of S','candidate_set':'these are observed labels, not per-step UI candidate sets','split':'the split is deterministic and user-disjoint but must be frozen in the pilot protocol'}
    }
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()
