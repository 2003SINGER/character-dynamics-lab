"""Read-only evidence for completed context seeds; not whole-run acceptance."""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_实验/LIGHT_SourceRankingV1'))
import train

RUN = ROOT / 'outputs/light_source_ranking_v1_20261006/trainer_runs/source_conditional_dev_c8acd05_20261006_v1'
payload = (RUN / 'snapshots/projected_input.jsonl').read_bytes()
assert hashlib.sha256(payload).hexdigest() == '2d839c62ddf2194b1968fe5b22913db9950aa10bd3647fe2179745b6b4efcef5'
rows = [json.loads(x) for x in payload.splitlines()]
expected = {}
for i, r in enumerate(rows, 1):
    p = r['provenance']
    bucket = int(hashlib.sha256(p['trajectory_id'].encode()).hexdigest()[:8], 16) % 10
    support = r['candidate_surface']['recorded_support']
    matches = [j for j, c in enumerate(support) if c.strip().casefold() == r['supervision']['recorded_action'].strip().casefold()]
    if bucket < 9 and len(matches) == 1:
        expected[i] = (p['trajectory_id'], 'train' if bucket < 7 else 'validation', matches[0], len(support))
assert len(expected) == 12195
progress = [json.loads(x) for x in (RUN / 'progress.jsonl').read_text().splitlines()]
torch.set_num_threads(1)
for seed in (7, 19, 31):
    logs = [r for r in progress if r['event'] == 'epoch_complete' and r['condition'] == 'context_only' and r['seed'] == seed]
    assert len(logs) == 15 and [r['epoch'] for r in logs] == list(range(1, 16))
    assert all(math.isfinite(r['mean_train_nll']) and r['mean_preclip_gradient_norm'] > 0 for r in logs)
    best = min(logs, key=lambda r: (r['mean_validation_nll'], r['epoch']))
    saved = torch.load(RUN / f'checkpoint_context_only_seed{seed}.pt', map_location='cpu', weights_only=True)
    assert saved['best_epoch'] == best['epoch'] and saved['run_kind'] == 'SOURCE_CONDITIONAL_DEVELOPMENT'
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    initial = train.RankingModel('context_only').state_dict()
    assert any(not torch.equal(initial[k], saved['state_dict'][k]) for k in initial)
    preds = [json.loads(x) for x in (RUN / f'predictions_context_only_seed{seed}.jsonl').read_text().splitlines()]
    assert len(preds) == len(expected) and {r['source_row'] for r in preds} == set(expected)
    for r in preds:
        assert (r['trajectory_id'], r['split'], r['gold_candidate_index'], r['candidate_count']) == expected[r['source_row']]
        probs = r['probabilities_in_source_order']
        assert len(probs) == r['candidate_count'] and abs(sum(probs) - 1) < 1e-6
        assert abs(-math.log(probs[r['gold_candidate_index']]) - r['nll']) < 1e-6
    assert abs(np.mean([r['nll'] for r in preds if r['split'] == 'validation']) - best['mean_validation_nll']) < 1e-6
print(json.dumps({'partial_actual_fit_audit': 'PASS', 'scope': 'context_only completed seeds only',
                  'seeds': [7, 19, 31], 'epoch_records': 45, 'predictions': 36585,
                  'full_comparison_pass': False}))
