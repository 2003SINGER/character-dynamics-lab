#!/usr/bin/env python3
import csv, json, sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1])
rows = list(csv.DictReader(path.open(encoding='utf-8', newline='')))
seeds = sorted({int(r['scenario_seed']) for r in rows})
by = defaultdict(list)
for r in rows:
    by[(int(r['scenario_seed']), r['branch'])].append(r)
def first(seed, branch, predicate):
    return next(r for r in by[(seed, branch)] if predicate(r))
visible = [first(s, 'visible', lambda r: r['discovery_event'] == '1') for s in seeds]
hidden = [first(s, 'hidden', lambda r: r['discovery_event'] == '1') for s in seeds]
pre_max = {}
for s, h in zip(seeds, hidden):
    pre_max[str(s)] = max(float(r['policy_tv_vs_control']) for r in by[(s, 'hidden')] if int(r['step']) < int(h['step']))
def values(items, key):
    return [float(r[key]) for r in items]
result = {
    'source_csv': str(path), 'seeds': len(seeds), 'rows': len(rows),
    'visible_discovery_steps': [int(r['step']) for r in visible],
    'hidden_discovery_steps': [int(r['step']) for r in hidden],
    'hidden_pre_discovery_max_policy_tv_vs_control': pre_max,
    'visible_discovery': {k: values(visible, k) for k in ['urgency', 'deadline_pressure_contribution', 'policy_tv_vs_control', 'study_probability']},
    'hidden_discovery': {k: values(hidden, k) for k in ['urgency', 'deadline_pressure_contribution', 'policy_tv_vs_control', 'study_probability']},
    'gates': {
        'hidden_pre_discovery_policy_tv_zero_all_seeds': all(v == 0.0 for v in pre_max.values()),
        'visible_policy_nonzero_all_seeds': all(float(r['policy_tv_vs_control']) > 0 for r in visible),
        'hidden_policy_nonzero_after_discovery_all_seeds': all(float(r['policy_tv_vs_control']) > 0 for r in hidden),
        'shared_time_rows_present': all('simulation_total_minutes' in r for r in rows),
    }
}
out = path.parent / 'aggregate.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
