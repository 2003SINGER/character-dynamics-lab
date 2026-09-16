import json, pathlib, subprocess, sys
root=pathlib.Path(sys.argv[1]); exe=sys.argv[2]
seeds=[(17,101),(29,202),(43,303),(61,404),(89,505)]
traces=root/'traces'; traces.mkdir(parents=True,exist_ok=True)
lines=['# FREE_RUN_6H report','', 'Development/demo engineering diagnostics; not a realism claim.','']
for i,(scenario,policy) in enumerate(seeds):
    p=traces/f'free_run_{chr(65+i)}.json'; subprocess.run([exe,str(scenario),str(policy),str(p)],check=True)
    replay=p.with_suffix('.replay.json'); subprocess.run([exe,str(scenario),str(policy),str(replay)],check=True)
    if p.read_bytes()!=replay.read_bytes(): raise SystemExit(f'non-deterministic replay: {p.name}')
    replay.unlink()
    data=json.loads(p.read_text())
    required = {'timestamp','elapsed','world_events','observation','observation_deltas','continuous_state_delta','impulse_state_delta','state','decision_gate','policy_evaluated','candidates','running_action_before','running_action_after','selected_action','pre_policy_outcome','post_policy_outcome','validation','provenance','dynamics_model','demo_only'}
    if any(not required.issubset(frame) for frame in data): raise SystemExit(f'incomplete boundary trace: {p.name}')
    if any(frame.get('dynamics_model') != 'demo-living-v1' or frame.get('demo_only') is not True for frame in data): raise SystemExit(f'model provenance missing: {p.name}')
    if any(data[i]['timestamp'] <= data[i-1]['timestamp'] or data[i]['elapsed'] <= 0 for i in range(1, len(data))): raise SystemExit(f'non-monotonic boundary: {p.name}')
    actions=[x['selected_action'] for x in data if x['selected_action']]
    if data[-1]['timestamp'] < 840: raise SystemExit(f'run shorter than six hours: {p.name}')
    if any(not (0 <= x['state'][k] <= 1) for x in data for k in ('hunger','fatigue','bathroom_urge')): raise SystemExit(f'S out of range: {p.name}')
    counts={a:actions.count(a) for a in sorted(set(actions))}
    lines += [f'## Run {chr(65+i)} (scenario={scenario}, policy={policy})',f'- time range: {data[0]["timestamp"]}–{data[-1]["timestamp"]}',f'- boundaries: {len(data)}',f'- action counts: `{counts}`',f'- final task effort: {data[-1]["task_effort"]}', '']
(root/'FREE_RUN_6H_report.md').write_text('\n'.join(lines)+'\n')
all_actions = set()
for i,(scenario,policy) in enumerate(seeds):
    data = json.loads((traces/f'free_run_{chr(65+i)}.json').read_text())
    all_actions.update(x['selected_action'] for x in data if x['selected_action'])
required_families = ({'study_focused'}, {'get_meal','go_to_bathroom'}, {'rest_at_bed','sleep_at_bed'}, {'use_phone','use_computer','idle'})
if not all(any(a in all_actions for a in family) for family in required_families):
    raise SystemExit(f'free-run action diversity insufficient: {sorted(all_actions)}')
