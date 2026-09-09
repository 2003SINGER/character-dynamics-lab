#!/usr/bin/env python3
"""Mechanism-vector evaluator; deliberately emits no aggregate naturalness score."""
import argparse, csv, json
from pathlib import Path

def rows(path):
    return list(csv.DictReader(Path(path).open(encoding='utf-8', newline='')))
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--deadline', type=Path, required=True); ap.add_argument('--commitment', type=Path, required=True); ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    d, c = rows(a.deadline), rows(a.commitment)
    seeds = sorted({int(r['scenario_seed']) for r in d})
    hidden_step = {s: min(int(r['step']) for r in d if int(r['scenario_seed']) == s and r['branch'] == 'hidden' and r['discovery_event'] == '1') for s in seeds}
    hidden_pre = {str(s): max(float(r['policy_tv_vs_control']) for r in d if int(r['scenario_seed']) == s and r['branch'] == 'hidden' and int(r['step']) < hidden_step[s]) for s in seeds}
    visible_disc = [r for r in d if r['branch'] == 'visible' and r['discovery_event'] == '1']
    hidden_disc = [r for r in d if r['branch'] == 'hidden' and r['discovery_event'] == '1']
    result = {
        'schema_version': 'character_dynamics_self_evaluation_v1',
        'hard_gates': {
            'deadline_hidden_pre_discovery_tv_zero': all(v == 0 for v in hidden_pre.values()),
            'deadline_visible_discovery_nonzero_policy': all(float(r['policy_tv_vs_control']) > 0 for r in visible_disc),
            'deadline_hidden_discovery_nonzero_policy': all(float(r['policy_tv_vs_control']) > 0 for r in hidden_disc),
            'commitment_active_setup': c[0]['commitment_status'] == 'active',
            'commitment_suspended': c[1]['commitment_status'] == 'suspended',
            'commitment_resumed_active': c[-1]['commitment_status'] == 'active',
        },
        'mechanism_metrics': {
            'deadline': {'seeds': len(seeds), 'hidden_pre_discovery_max_tv': hidden_pre, 'visible_discovery_count': len(visible_disc), 'hidden_discovery_count': len(hidden_disc), 'visible_policy_tv': [float(r['policy_tv_vs_control']) for r in visible_disc], 'hidden_policy_tv': [float(r['policy_tv_vs_control']) for r in hidden_disc]},
            'commitment': {'preserved_vs_ablated_policy_tv': float(c[2]['preserved_vs_ablated_policy_tv']), 'recovery_fatigue': float(c[2]['fatigue'])},
        },
        'behavior_telemetry': {'not_scored': ['believability', 'naturalness', 'character differentiation as quality']},
        'efficiency_telemetry': {'model_calls': 0, 'decision_count': len(d), 'calls_per_decision': 0.0},
    }
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
