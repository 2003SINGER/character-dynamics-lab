"""Independent full-cohort acceptance; does not call the projector or train."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).parent / 'contract_v1'
SOURCE = ROOT / 'outputs/light_before_turn_20261006/run_v1/before_turn_candidates.jsonl'
sha = lambda b: hashlib.sha256(b).hexdigest()
source_bytes = SOURCE.read_bytes()
source_digest = sha(source_bytes)
assert source_digest == 'b414f176bf7c6d0e1f47536bab8c251ae7d39ead5b40550310127294f74e5646'
source = [json.loads(x) for x in source_bytes.splitlines()]
output_bytes = (RUN / 'projected_inputs.jsonl').read_bytes()
output = [json.loads(x) for x in output_bytes.splitlines()]
manifest = json.loads((RUN / 'manifest.json').read_text())
assert len(source) == len(output) == manifest['rows'] == 13463
assert sha(output_bytes) == manifest['output_sha256']
assert manifest['training_authorized'] is False and manifest['actor_forecast_admitted'] is False
for name, digest in manifest['output_files_sha256'].items():
    assert sha((RUN / name).read_bytes()) == digest
for saved, current in [('protocol_snapshot.md', 'README.md'),
                       ('project_inputs_snapshot.py', 'project_inputs.py'),
                       ('test_project_inputs_snapshot.py', 'test_project_inputs.py')]:
    assert (RUN / saved).read_bytes() == (ROOT / '02_实验/LIGHT_SourceRankingV1' / current).read_bytes()

spec = importlib.util.spec_from_file_location('tested_projection', ROOT / '02_实验/LIGHT_SourceRankingV1/project_inputs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class NoMetadata(dict):
    def __getitem__(self, key):
        if key in {'supervision', 'provenance', 'admission'}:
            raise AssertionError('forbidden feature read: ' + key)
        return super().__getitem__(key)

splits = collections.defaultdict(list)
keys = set()
partner_command_rows = 0
for line, (old, row) in enumerate(zip(source, output), 1):
    p = old['candidate_model_payload']; prov = old['provenance']
    key = (prov['trajectory_id'], prov['target_physical_index'], prov['actor'].casefold())
    assert key not in keys; keys.add(key)
    bucket = int(hashlib.sha256(prov['trajectory_id'].encode()).hexdigest()[:8], 16) % 10
    split = 'train' if bucket < 7 else 'validation' if bucket < 9 else 'excluded_bucket9'
    assert prov['split'] == split and prov['split_bucket'] == bucket
    history = p['prior_interaction_history']
    refs = prov['payload_history_turn_refs']
    turns = [r['raw_turn_index'] for r in refs]
    assert len(turns) == len(history) and turns == sorted(set(turns))
    assert all(0 <= t < prov['target_raw_turn_index'] for t in turns)
    core = [{'role': g['role'], 'speech': g['speech'], 'emote': g['emote'],
             'action': g['action'] if g['role'] == 'self' else None} for g in history]
    expected = {
        'schema': 'light_source_ranking_input_contract_v1',
        'static_condition': {'self_persona': p['self_persona'], 'recorded_environment_snapshot': p['recorded_environment_snapshot']},
        'history_views': {'core': core, 'diagnostic_plus_partner_raw_commands': history},
        'candidate_surface': old['candidate_surface'],
        'supervision': {'recorded_action': old['supervision']['recorded_action']},
        'provenance': {**prov, 'source_row_line': line, 'source_input_sha256': source_digest},
        'admission': {'training_authorized': False, 'actor_forecast_admitted': False,
                      'warning': 'DEVELOPMENT_SOURCE_CONDITIONAL_COMMAND_RANKING; Paper-0 remains NOT ADMITTED'},
    }
    assert row == expected, line
    for view in ('core', 'diagnostic_plus_partner_raw_commands'):
        wanted = {'self_persona': p['self_persona'], 'history': core if view == 'core' else history,
                  'recorded_environment_snapshot': p['recorded_environment_snapshot'],
                  'recorded_support': old['candidate_surface']['recorded_support'], 'view': view}
        assert module.features(NoMetadata(row), view) == wanted
        no_context = {k: v for k, v in wanted.items() if k != 'recorded_environment_snapshot'}
        assert module.features(NoMetadata(row), view, include_context=False) == no_context
    partner_command_rows += any(g['role'] == 'partner' and g['action'] is not None for g in history)
    # A permitted prior-dialogue mutation must alter features (positive control).
    changed_core = [dict(g) for g in core]
    changed_core[0]['speech'] = (changed_core[0]['speech'] or '') + ' AUDIT_PRIOR_MUTATION'
    changed = {**row, 'history_views': {**row['history_views'], 'core': changed_core}}
    assert module.features(changed) != module.features(row)
    splits[split].append(expected)

for split, rows in splits.items():
    observed = manifest['splits'][split]
    assert observed['rows'] == len(rows)
    assert observed['episodes'] == len({r['provenance']['trajectory_id'] for r in rows})
    assert observed['actor_trajectories'] == len({(r['provenance']['trajectory_id'], r['provenance']['actor']) for r in rows})
    depths = collections.Counter(len(r['history_views']['core']) for r in rows)
    assert observed['groups'] == sum(k*v for k, v in depths.items())
    assert observed['history_depth_distribution'] == {str(k): v for k, v in depths.items()}
    for view in ('core', 'diagnostic_plus_partner_raw_commands'):
        for role in ('self', 'partner'):
            for channel in ('speech', 'action', 'emote'):
                values = [g[channel] for r in rows for g in r['history_views'][view] if g['role'] == role]
                assert observed['channel_items'][view][role][channel] == {'present': sum(v is not None for v in values), 'null': sum(v is None for v in values)}
    elig = collections.Counter()
    for row in rows:
        gold = row['supervision']['recorded_action'].strip().casefold()
        matches = sum(c.strip().casefold() == gold for c in row['candidate_surface']['recorded_support'])
        elig['unique' if matches == 1 else 'ambiguous' if matches > 1 else 'absent'] += 1
    assert manifest['supervision_eligibility'][split] == {k: elig[k] for k in ('unique', 'absent', 'ambiguous', 'missing_or_invalid')}
assert sha('\n'.join(sorted('|'.join(map(str, k)) for k in keys)).encode()) == manifest['cohort_key_digest']
assert sha('\n'.join(sorted(r['provenance']['target_source_ref'] for r in output)).encode()) == manifest['source_key_digest']
print(json.dumps({'parent_full_cohort_audit': 'PASS', 'rows': len(output),
                  'partner_command_rows_core_masked': partner_command_rows,
                  'input_sha256': source_digest, 'output_sha256': sha(output_bytes),
                  'training_performed': False, 'actor_forecast_admitted': False}))
