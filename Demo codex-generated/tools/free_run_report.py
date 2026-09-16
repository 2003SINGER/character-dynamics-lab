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
    for frame in data:
        frame.setdefault('pre_policy_outcome', None)
        frame.setdefault('post_policy_outcome', None)
        frame.setdefault('continuous_state_delta', {})
        frame.setdefault('impulse_state_delta', {})
        frame.setdefault('provenance', 'free_run_runtime_boundary')
    p.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    actions=[x.get('action', x.get('selected_action')) for x in data if x.get('action', x.get('selected_action'))]
    if data[-1]['timestamp']-data[0]['timestamp'] < 360: raise SystemExit(f'run shorter than six hours: {p.name}')
    if any(not (0 <= x[k] <= 1) for x in data for k in ('hunger','fatigue','bathroom_urge')): raise SystemExit(f'S out of range: {p.name}')
    counts={a:actions.count(a) for a in sorted(set(actions))}
    lines += [f'## Run {chr(65+i)} (scenario={scenario}, policy={policy})',f'- time range: {data[0]["timestamp"]}–{data[-1]["timestamp"]}',f'- boundaries: {len(data)}',f'- action counts: `{counts}`',f'- final task effort: {data[-1]["task_effort"]}', '']
(root/'FREE_RUN_6H_report.md').write_text('\n'.join(lines)+'\n')
