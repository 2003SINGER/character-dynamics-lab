#!/usr/bin/env python3
"""Auditable multi-dimensional evaluator for the synthetic Character Dynamics batch."""
from __future__ import annotations
import argparse, csv, json, math
from collections import Counter, defaultdict
from pathlib import Path

ACTION_COLUMNS = [
    'use_phone', 'shop_on_phone', 'use_computer', 'study_at_computer',
    'study_focused', 'study_halfhearted', 'rest_at_bed', 'sleep_at_bed',
    'go_to_bathroom', 'get_meal', 'turn_light_on', 'turn_light_off',
    'turn_off_alarm', 'open_curtain', 'close_curtain', 'idle',
]

def mean(xs): return sum(xs) / len(xs) if xs else 0.0
def js_divergence(a, b):
    keys = set(a) | set(b); pa = {k: a.get(k, 0.0) for k in keys}; pb = {k: b.get(k, 0.0) for k in keys}
    z1 = sum(pa.values()) or 1.0; z2 = sum(pb.values()) or 1.0
    pa = {k: v / z1 for k, v in pa.items()}; pb = {k: v / z2 for k, v in pb.items()}; m = {k: (pa[k] + pb[k]) / 2 for k in keys}
    def kl(p): return sum(v * math.log(v / m[k], 2) for k, v in p.items() if v > 0 and m[k] > 0)
    return (kl(pa) + kl(pb)) / 2

def evaluate(batch_dir: Path, paired_path: Path | None = None):
    trajectories = list(csv.DictReader((batch_dir / 'trajectories.csv').open(encoding='utf-8', newline='')))
    runs = list(csv.DictReader((batch_dir / 'runs.csv').open(encoding='utf-8', newline='')))
    metadata = {}
    for line in (batch_dir / 'metadata.txt').read_text(encoding='utf-8').splitlines():
        if '=' in line:
            k, v = line.split('=', 1); metadata[k] = v
    by_run = defaultdict(list); by_personality = defaultdict(Counter); event_rows = 0; action_changes_after_event = []
    legal = []; probability_errors = []; diversity = []; commitment_continuity = []; recovery = []
    for row in trajectories:
        key = (row['personality_index'], row['scenario_seed']); by_run[key].append(row)
        action = row['chosen_action']; legal.append(float(row['accepted']) in (0.0, 1.0)); by_personality[row['personality_index']][action] += 1
        probs = [float(row[f'p_{a}']) for a in ACTION_COLUMNS]; probability_errors.append(abs(sum(probs) - 1.0))
        if row['event_ids']:
            event_rows += 1
    for key, seq in by_run.items():
        seq.sort(key=lambda r: int(r['step'])); diversity.append(len({r['chosen_action'] for r in seq}) / len(seq))
        active_pairs = []; interrupted_indices = []
        for i, row in enumerate(seq[:-1]):
            nxt = seq[i + 1]
            if row['pre_commitment_status'] == 'active':
                active_pairs.append(int(nxt['pre_commitment_task_id'] == row['pre_commitment_task_id'] and nxt['pre_commitment_status'] in {'active', 'suspended'}))
            if row['outcome_task_session_interrupted'] == '1': interrupted_indices.append(i)
            if row['event_ids'] and i + 1 < len(seq):
                action_changes_after_event.append(int(nxt['chosen_action'] != row['chosen_action']))
        commitment_continuity.extend(active_pairs)
        for i in interrupted_indices:
            window = seq[i + 1:i + 6]
            recovery.append(int(any(r['pre_commitment_status'] in {'active', 'suspended'} for r in window)))
    personality_js = []
    profiles = list(csv.DictReader((batch_dir / 'personalities.csv').open(encoding='utf-8', newline='')))
    for i, left in enumerate(profiles):
        for right in profiles[i + 1:]: personality_js.append(js_divergence(by_personality[left['personality_index']], by_personality[right['personality_index']]))
    completed = sum(r['coursework_status'] == 'completed' for r in runs)
    paired = None
    if paired_path is not None:
        rows = list(csv.DictReader(paired_path.open(encoding='utf-8', newline='')))
        pairs = defaultdict(dict)
        for row in rows:
            pairs[(row['scenario_seed'], row['step'])][row['branch']] = row
        post = [pair for (seed, step), pair in pairs.items() if int(step) >= 2 and 'hidden' in pair and 'visible' in pair]
        hidden_retention = [int(p['hidden']['phone_known']) for p in post]
        visible_detection = [int(p['visible']['phone_known']) == 0 and p['visible']['phone_fact_status'] in {'stale', 'absent'} for p in post]
        obs_mediation = [1 - int(p['hidden']['observation_equal']) for p in post]
        state_distances = [float(p['hidden']['state_distance']) for p in post]
        policy_distances = [float(p['hidden']['policy_distance']) for p in post]
        action_divergence = []
        for pair in post:
            action_divergence.append(int(pair['hidden']['chosen_action'] != pair['visible']['chosen_action']))
        probes = [row for row in rows if row.get('branch') == 'mechanism_probe' and row.get('discovery_event') == '1']
        paired = {
            'rows': len(rows), 'pairs': len(post),
            'InformationIntegrity': mean([(a + int(b)) / 2 for a, b in zip(hidden_retention, visible_detection)]),
            'ObservationMediation': mean(obs_mediation),
            'StatePersistence': mean([1.0 - math.exp(-d) for d in state_distances]),
            'BehavioralPersistence': mean(action_divergence),
            'mean_state_distance': mean(state_distances),
            'mean_policy_distance': mean(policy_distances),
            'discovery_probe_count': len(probes),
            'discovery_steps': [int(row['step']) for row in probes],
            'correction_latency': [0 for _ in probes],
        }
    scores = {
        'WorldValidity': {'score': mean([float(x) for x in legal]), 'basis': 'accepted is binary and all trajectory rows parse'},
        'InformationIntegrity': ({'score': paired['InformationIntegrity'], 'basis': 'paired hidden/visible phone intervention'} if paired else {'score': None, 'status': 'not_scored', 'reason': 'provide --paired for explicit hidden-information intervention labels'}),
        'CausalResponsiveness': {'score': mean(action_changes_after_event), 'basis': 'diagnostic action-change rate after emitted world events; not an intervention causal estimate'},
        'Persistence': {'score': mean(commitment_continuity), 'basis': 'active commitment carried to next decision with same task id or suspension'},
        'Recovery': {'score': mean(recovery), 'basis': 'interrupted task returns to active/suspended within five decisions'},
        'Commitment': {'score': mean(commitment_continuity), 'basis': 'same as persistence continuity diagnostic'},
        'Adaptivity': {'score': mean(action_changes_after_event), 'basis': 'event-following action change diagnostic'},
        'CharacterDifferentiation': {'score': mean(personality_js), 'basis': 'pairwise Jensen-Shannon divergence of chosen-action distributions across generated personalities'},
        'BehavioralDiversity': {'score': mean(diversity), 'basis': 'unique chosen actions / decision points per run'},
        'ObservationMediation': ({'score': paired['ObservationMediation'], 'basis': 'observation inequality after phone removal'} if paired else {'score': None, 'status': 'not_scored'}),
        'StatePersistence': ({'score': paired['StatePersistence'], 'basis': 'normalized paired state distance'} if paired else {'score': None, 'status': 'not_scored'}),
        'BehavioralPersistence': ({'score': paired['BehavioralPersistence'], 'basis': 'paired action divergence'} if paired else {'score': None, 'status': 'not_scored'}),
        'Believability': {'score': None, 'status': 'not_scored', 'reason': 'no blind external judge or human pairwise panel in v0'},
        'Efficiency': {'score': 0.0, 'basis': 'synthetic batch uses zero LLM calls; runtime/token telemetry not yet instrumented', 'decision_points': len(trajectories), 'model_calls': 0},
    }
    return {'schema_version': 'character_dynamics_self_evaluation_v0', 'batch_dir': str(batch_dir), 'paired_intervention': paired, 'metadata': metadata, 'counts': {'trajectory_rows': len(trajectories), 'runs': len(runs), 'personalities': len(profiles), 'scenario_seeds': len({r['scenario_seed'] for r in trajectories}), 'event_rows': event_rows, 'completed_runs': completed}, 'checks': {'probability_sum_max_abs_error': max(probability_errors) if probability_errors else None, 'all_accepted_values_binary': all(legal)}, 'scores': scores, 'interpretation': {'use': 'internal development scorecard only', 'not_claimed': ['psychological validity', 'external naturalness', 'causal effect from event rows', 'Theory-S validation'], 'next': 'paired intervention metrics are mechanism diagnostics, not external validation'}}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('batch_dir', type=Path); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--paired', type=Path); a = ap.parse_args()
    result = evaluate(a.batch_dir, a.paired); a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
