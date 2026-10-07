"""Independent artifact readback; never fits or uses trainer reporting helpers."""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / '02_实验/LIGHT_SourceRankingV1'
sys.path.insert(0, str(HERE))
import train

RUN = Path(sys.argv[1]).resolve()
assert ROOT / 'outputs' in RUN.parents
manifest = json.loads((RUN / 'provenance.json').read_text())
report = json.loads((RUN / 'report.json').read_text())
assert report == json.loads((RUN / 'synthetic_report.json').read_text())
assert manifest['training_authorized'] is False
assert report['research_evidence'] is False and report['real_source_loaded'] is False
assert report['run_kind'] == manifest['run_kind'] == 'SYNTHETIC_CONTRACT_ONLY'
sha = lambda b: hashlib.sha256(b).hexdigest()
files = {p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file()}
assert files - {'provenance.json'} == set(manifest['output_files_sha256'])
for name, digest in manifest['output_files_sha256'].items():
    assert sha((RUN / name).read_bytes()) == digest, name
for name in ('train.py', 'test_train.py', 'project_inputs.py', 'test_project_inputs.py', 'README.md'):
    assert (RUN / 'snapshots' / name).read_bytes() == (HERE / name).read_bytes(), name
rows = [json.loads(line) for line in (RUN / 'snapshots/synthetic_input.jsonl').read_text().splitlines()]
assert len(rows) == 8
config = manifest['config']
assert config['seeds'] == [7, 19, 31] and config['max_epochs'] == 15
assert config['bootstrap_replicates'] == 2000 and config['bootstrap_seed'] == 104729

def hashed(text, width):
    words = re.findall(r'\w+', (text or '').casefold(), re.UNICODE)
    tokens = ['u:' + w for w in words] + ['b:' + a + chr(31) + b for a, b in zip(words, words[1:])]
    out = np.zeros(width, dtype=np.float32)
    for token in tokens:
        d = hashlib.blake2b(token.encode(), digest_size=16, person=b'PredHashV1').digest()
        out[int.from_bytes(d[:8], 'big') % width] += 1 if d[8] & 1 else -1
    norm = np.linalg.norm(out)
    return out / norm if norm else out

def feature(row, condition):
    static = row['static_condition']
    persona = hashed(static['self_persona'], 256)
    context = hashed(static['recorded_environment_snapshot'], 256)
    if condition == 'gru_no_persona': persona[:] = 0
    if condition == 'gru_no_context': context[:] = 0
    view = 'diagnostic_plus_partner_raw_commands' if condition == 'gru_plus_partner_raw_commands' else 'core'
    groups = []
    for g in row['history_views'][view]:
        speech, action, emote = g['speech'], g['action'], g['emote']
        if condition == 'gru_no_dialogue': speech = emote = None
        groups.append(np.concatenate((hashed(speech, 256), hashed(action, 128), hashed(emote, 64),
            np.asarray([g['role'] == 'self', g['role'] == 'partner', bool(speech), bool(action), bool(emote)], dtype=np.float32))))
    return {'persona': persona, 'context': context,
        'history': np.stack(groups) if groups else np.zeros((0, 453), dtype=np.float32),
        'candidates': np.stack([hashed(x, 256) for x in row['candidate_surface']['recorded_support']])}

counts = {'context_only': 25153, 'last2_core': 39665, 'pooled_core': 41281, 'uniform': 0}
predictions = {}
checkpoint_count = epoch_count = prediction_count = 0
torch.set_num_threads(1)
for condition in config['conditions']:
    predictions[condition] = {}
    for run in report['conditions'][condition]:
        seed = run['seed']
        records = [json.loads(line) for line in (RUN / run['prediction_file']).read_text().splitlines()]
        assert len(records) == len(rows)
        predictions[condition][seed] = {r['source_row']: r for r in records}
        assert len(predictions[condition][seed]) == len(rows)
        prediction_count += len(records)
        if condition == 'uniform':
            model = None
            assert run['checkpoint_file'] is None and run['best_epoch'] is None
        else:
            checkpoint_count += 1
            model = train.RankingModel(condition).eval()
            saved = torch.load(RUN / run['checkpoint_file'], map_location='cpu', weights_only=True)
            assert saved['condition'] == condition and saved['seed'] == seed
            model.load_state_dict(saved['state_dict'], strict=True)
            assert sum(p.numel() for p in model.parameters()) == counts.get(condition, 47761)
            vals = run['validation_nll_by_epoch']
            assert len(vals) == len(run['epoch_log']) == 15
            expected_epoch = min(range(15), key=lambda i: (vals[i], i)) + 1
            assert run['best_epoch'] == saved['best_epoch'] == expected_epoch
            assert run['selected_validation_nll'] == vals[expected_epoch - 1]
            for idx, log in enumerate(run['epoch_log']):
                assert log['epoch'] == idx + 1 and log['mean_validation_nll'] == vals[idx]
                assert math.isfinite(log['mean_train_nll']) and log['mean_preclip_gradient_norm'] > 0
            epoch_count += len(vals)
        assert run['trainable_parameters'] == counts.get(condition, 47761)
        for i, row in enumerate(rows, 1):
            expected_features = feature(row, condition)
            encoded = train.FeatureEncoder().features(row, condition)
            for key in expected_features:
                np.testing.assert_array_equal(encoded[key], expected_features[key])
            support = row['candidate_surface']['recorded_support']
            matches = [j for j, c in enumerate(support) if c.strip().casefold() == row['supervision']['recorded_action'].strip().casefold()]
            assert len(matches) == 1
            gold = matches[0]
            with torch.no_grad():
                scores = torch.zeros(len(support)) if model is None else model.logits(expected_features)
                probs = torch.softmax(scores, 0).tolist()
            raw = predictions[condition][seed][i]
            assert raw['probabilities_in_source_order'] == probs
            order = sorted(range(len(support)), key=lambda j: (-float(scores[j]), j))
            assert raw['gold_candidate_index'] == gold and raw['gold_rank'] == order.index(gold) + 1
            numerical = np.asarray(scores.tolist(), dtype=np.float64)
            expected_nll = float(numerical.max() + math.log(np.exp(numerical - numerical.max()).sum()) - numerical[gold])
            assert abs(raw['nll'] - expected_nll) < 1e-6
            prov = row['provenance']
            bucket = int(sha(prov['trajectory_id'].encode())[:8], 16) % 10
            expected_split = 'train' if bucket < 7 else 'validation' if bucket < 9 else 'excluded_bucket9'
            assert expected_split != 'excluded_bucket9'
            assert raw['split'] == expected_split and raw['trajectory_id'] == prov['trajectory_id']
            assert raw['actor'] == prov['actor'] and raw['prior_group_depth'] == len(row['history_views']['core'])
        for split in ('train', 'validation'):
            sub = [r for r in records if r['split'] == split]
            metric = run['metrics'][split]
            assert metric['n'] == len(sub) == 4
            assert abs(metric['nll'] - np.mean([r['nll'] for r in sub])) < 1e-12
            assert metric['top1_accuracy'] == np.mean([r['gold_rank'] == 1 for r in sub])
            assert metric['mrr'] == np.mean([1 / r['gold_rank'] for r in sub])

def comparison(keys, left, right, observed):
    assert observed['n'] == len(keys)
    if not keys:
        assert observed['mean_delta_nll'] is None and observed['ci95'] is None
        return
    groups = {}
    for key in keys:
        l = [predictions[left][s][key]['nll'] for s in config['seeds']]
        r = [predictions[right][s][key]['nll'] for s in config['seeds']]
        tid = predictions[left][7][key]['trajectory_id']
        groups.setdefault(tid, []).append(float(np.mean(l) - np.mean(r)))
    assert observed['episodes'] == len(groups)
    point = np.mean([d for ds in groups.values() for d in ds])
    assert abs(observed['mean_delta_nll'] - point) < 1e-12
    rng = np.random.default_rng(104729)
    names = sorted(groups)
    draws = []
    for _ in range(2000):
        selected = rng.integers(0, len(names), size=len(names))
        vals = [d for j in selected for d in groups[names[j]]]
        draws.append(np.mean(vals))
    np.testing.assert_allclose(observed['ci95'], np.quantile(draws, [0.025, 0.975]), rtol=0, atol=1e-12)
    for seed in config['seeds']:
        expected = np.mean([predictions[left][seed][k]['nll'] - predictions[right][seed][k]['nll'] for k in keys])
        assert abs(observed['per_seed_delta_nll'][str(seed)] - expected) < 1e-12

pairs = {'gru_core_vs_context_only': ('gru_core', 'context_only'), 'gru_core_vs_pooled_core': ('gru_core', 'pooled_core')}
for name, (left, right) in pairs.items():
    keys = [k for k, r in predictions[left][7].items() if r['split'] == 'validation']
    comparison(keys, left, right, report['paired_comparisons'][name])
for split in ('train', 'validation'):
    for band in ('1-4', '5-8', '>=9'):
        sub = report['strata'][f'{split}:{band}']
        keys = [k for k, r in predictions['gru_core'][7].items() if r['split'] == split and
                ((1 <= r['prior_group_depth'] <= 4) if band == '1-4' else (5 <= r['prior_group_depth'] <= 8) if band == '5-8' else (r['prior_group_depth'] >= 9))]
        assert sub['rows'] == len(keys)
        for name, (left, right) in pairs.items():
            comparison(keys, left, right, sub['paired_primary_comparisons'][name])
assert checkpoint_count == 24 and epoch_count == 360 and prediction_count == 216
print(json.dumps({'independent_artifact_audit': 'PASS', 'rows': len(rows), 'checkpoints': checkpoint_count,
    'epoch_records': epoch_count, 'predictions': prediction_count, 'real_fit': False,
    'provenance_sha256': sha((RUN / 'provenance.json').read_bytes())}))
