#!/usr/bin/env python3
"""Capacity-matched generic history versus naive persistent compression benchmark."""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from Replay.replay_features_v1 import compile_candidate_v1, vectorize, FEATURE_VERSION
from Replay.replay_probe_v1 import fit_no_state

SEED = 20260909

def bucket(x):
    return int(hashlib.sha256(x.encode()).hexdigest()[:8], 16) % 10

def snap(o):
    return {'actor_observation': o, 'entities': [], 'possessions': []}

def action_vec(action, observation, rules):
    f, _, _ = compile_candidate_v1(str(action or ''), snap(observation), rules)
    return np.asarray(vectorize(f), dtype=float)

def target_rows(rows, rules):
    """Compile candidate, raw local history, and cumulative persistent state."""
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[r['trajectory_id'] + '::' + r['actor']].append(r)
    out = []
    for unit, seq in by_unit.items():
        seq.sort(key=lambda r: int(r['target_step_index']))
        prior = []
        for r in seq:
            cand = r.get('candidate_set_factual') or []
            action = str(r.get('source_action_A_star') or '')
            gold = next((i for i, c in enumerate(cand) if str(c).casefold() == action.casefold()), None)
            if gold is None or not cand:
                continue
            prev = action_vec(r.get('previous_source_action_A_star'), r.get('previous_source_O'), rules)
            prev2 = action_vec(r.get('previous2_source_action_A_star'), r.get('previous2_source_O'), rules)
            # The first eligible target already has one prior action outside this view.
            # Seed the persistent history with it before computing S_t.
            if not prior:
                prior.append(prev)
            # State is a fixed, non-fitted cumulative mean of all prior same-actor actions.
            state = np.mean(np.stack(prior), axis=0)
            fs = []
            for c in cand:
                cv = action_vec(c, r.get('source_O'), rules)
                fs.append({
                    'current': cv,
                    'raw_prev': np.concatenate([cv, cv * prev]),
                    'raw_last2': np.concatenate([cv, cv * prev, cv * prev2]),
                    'persistent_mean': np.concatenate([cv, cv * state]),
                })
            out.append({
                'target_id': f"{r['trajectory_id']}::{r['target_step_index']}",
                'group_key': unit,
                'features': fs,
                'persistent_state': state.tolist(),
                'gold_index': int(gold),
                'exact_previous_pair': bool(r.get('exact_previous_pair')),
                'history_surface': r.get('history_surface'),
            })
            prior.append(action_vec(action, r.get('source_O'), rules))
    return out

def permute_states(rows):
    """Capacity-matched control: cyclically permute persistent state vectors by target."""
    ordered = sorted(rows, key=lambda r: hashlib.sha256(r['target_id'].encode()).hexdigest())
    if len(ordered) <= 1:
        return rows
    shifted = [np.asarray(r['persistent_state'], dtype=float) for r in ordered[1:] + ordered[:1]]
    remap = {r['target_id']: s for r, s in zip(ordered, shifted)}
    out = []
    for r in rows:
        fs = []
        state = remap[r['target_id']]
        for item in r['features']:
            cv = item['current']
            fs.append({'current': cv, 'raw_prev': item['raw_prev'], 'raw_last2': item['raw_last2'], 'persistent_mean': np.concatenate([cv, cv * state])})
        q = dict(r); q['features'] = fs; q['permuted_persistent_state'] = state.tolist(); out.append(q)
    return out

def evaluate(model, groups):
    nll = mrr = top = 0.0; units = defaultdict(list)
    means = np.asarray(model['means']); scales = np.asarray(model['scales']); theta = np.asarray(model['weights_theta'])
    for rs in groups.values():
        row = rs[0]; x = (np.asarray(row['features'], dtype=float) - means) / scales
        z = x @ theta; z -= z.max(); p = np.exp(z); p /= p.sum(); gold = row['gold_index']; order = np.argsort(-p).tolist()
        loss = -math.log(max(float(p[gold]), 1e-300)); nll += loss; mrr += 1 / (order.index(gold) + 1); top += int(order[0] == gold); units[row['group_key']].append(loss)
    return {'rows': len(groups), 'mean_nll': nll / len(groups), 'mean_nll_bits': nll / math.log(2) / len(groups), 'mrr': mrr / len(groups), 'top1': top / len(groups), 'unit_count': len(units), '_units': {k: sum(v) / len(v) for k, v in units.items()}}

def delta_boot(base, other, seed=SEED, draws=2000):
    ids = sorted(set(base) & set(other)); rng = random.Random(seed); d = [other[i] - base[i] for i in ids]; vals = []
    for _ in range(draws):
        vals.append(sum(d[rng.randrange(len(d))] for _ in d) / len(d))
    vals.sort(); mean = sum(d) / len(d)
    return {'units': len(ids), 'mean_delta_nll': mean, 'ci95': [vals[int(.025 * draws)], vals[int(.975 * draws)]], 'delta_bits': mean / math.log(2)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('full_view', type=Path); ap.add_argument('rules', type=Path); ap.add_argument('out', type=Path); ap.add_argument('--runner-commit', required=True); a = ap.parse_args()
    raw = [json.loads(x) for x in a.full_view.open(encoding='utf-8') if x.strip()]
    rules = json.loads(a.rules.read_text(encoding='utf-8')); rows = target_rows(raw, rules)
    units = sorted({r['group_key'] for r in rows}); train = {u for u in units if bucket(u) < 7}; test = {u for u in units if bucket(u) >= 9}
    result = {'schema_version': 'light_actor_local_compression_benchmark_v0', 'runner_commit': a.runner_commit, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'feature_compiler_sha256': hashlib.sha256((Path(__file__).parents[1] / 'Replay/replay_features_v1.py').read_bytes()).hexdigest(), 'probe_sha256': hashlib.sha256((Path(__file__).parents[1] / 'Replay/replay_probe_v1.py').read_bytes()).hexdigest(), 'rules_sha256': hashlib.sha256(a.rules.read_bytes()).hexdigest(), 'full_view_sha256': hashlib.sha256(a.full_view.read_bytes()).hexdigest(), 'feature_version': FEATURE_VERSION, 'protocol': {'raw_prev': 'current 13D + current⊙previous 13D = 26D', 'persistent_mean': 'current 13D + current⊙cumulative-mean prior same-actor action 13D = 26D; first eligible target seeds history with previous_source_action_A_star', 'persistent_permuted': 'same 26D persistent feature with deterministic cyclic no-self state permutation separately inside train and test', 'raw_last2': 'current 13D + previous interaction 13D + previous2 interaction 13D = 39D', 'state_update': 'fixed cumulative mean; no fitted state, LLM, ontology, X, or candidate reconstruction'}, 'train_unit_count': len(train), 'test_unit_count': len(test), 'rows': len(rows), 'conditions': {}, 'paired_unit_bootstrap_delta_nll': {}}
    # Permute only within each split, so no donor state crosses the train/test boundary.
    perm = permute_states([r for r in rows if r['group_key'] in train]) + permute_states([r for r in rows if r['group_key'] in test])
    all_conditions = {'raw_prev': rows, 'persistent_mean': rows, 'persistent_permuted': perm, 'raw_last2': rows}
    saved = {}
    for name, source in all_conditions.items():
        train_rows = [dict(r, features=[dict(x) for x in r['features']]) for r in source if r['group_key'] in train]
        test_rows = [dict(r, features=[dict(x) for x in r['features']]) for r in source if r['group_key'] in test]
        tg = defaultdict(list); vg = defaultdict(list)
        for r in train_rows: tg[r['target_id']].append(r)
        for r in test_rows: vg[r['target_id']].append(r)
        feature_key = 'persistent_mean' if name.startswith('persistent') else name
        train_sets = [{'features': [x[feature_key].tolist() for x in rs[0]['features']], 'gold_index': rs[0]['gold_index']} for rs in tg.values()]
        # For permuted persistent, train on the same permuted state distribution and test on its held-out counterpart.
        model = fit_no_state(train_sets, 1e-2)
        groups = {'full': vg, 'nontrivial': {k: v for k, v in vg.items() if not v[0]['exact_previous_pair']}, 'contiguous': {k: v for k, v in vg.items() if v[0]['history_surface'] == 'CONTIGUOUS_SAME_ACTOR'}, 'gapped': {k: v for k, v in vg.items() if v[0]['history_surface'] == 'GAPPED_SAME_ACTOR'}}
        result['conditions'][name] = {}; saved[name] = {}
        for view, subset in groups.items():
            eval_rows = [dict(v[0], features=[x[feature_key].tolist() for x in v[0]['features']]) for v in subset.values()]
            ev = evaluate(model, {r['target_id']: [r] for r in eval_rows}); saved[name][view] = ev.pop('_units'); result['conditions'][name][view] = ev
    for view in ('full', 'nontrivial', 'contiguous', 'gapped'):
        result['paired_unit_bootstrap_delta_nll'][view] = {'persistent_vs_raw_prev': delta_boot(saved['raw_prev'][view], saved['persistent_mean'][view]), 'persistent_permuted_vs_persistent': delta_boot(saved['persistent_mean'][view], saved['persistent_permuted'][view]), 'raw_last2_vs_raw_prev': delta_boot(saved['raw_prev'][view], saved['raw_last2'][view])}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=lambda x: x.tolist() if hasattr(x, 'tolist') else x) + '\n', encoding='utf-8'); print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
