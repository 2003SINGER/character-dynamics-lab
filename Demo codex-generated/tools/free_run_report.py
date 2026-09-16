import json, pathlib, subprocess, sys
root=pathlib.Path(sys.argv[1]); exe=sys.argv[2]
seeds=[(17,101),(29,202),(43,303),(61,404),(89,505)]
traces=root/'traces'; traces.mkdir(parents=True,exist_ok=True)
lines=['# FREE_RUN_6H report','', 'Development/demo engineering diagnostics; not a realism claim.','']
for i,(scenario,policy) in enumerate(seeds):
    p=traces/f'free_run_{chr(65+i)}.json'; subprocess.run([exe,str(scenario),str(policy),str(p)],check=True)
    data=json.loads(p.read_text()); actions=[x['action'] for x in data if x['action']]
    counts={a:actions.count(a) for a in sorted(set(actions))}
    lines += [f'## Run {chr(65+i)} (scenario={scenario}, policy={policy})',f'- time range: {data[0]["timestamp"]}–{data[-1]["timestamp"]}',f'- boundaries: {len(data)}',f'- action counts: `{counts}`',f'- final task effort: {data[-1]["task_effort"]}', '']
(root/'FREE_RUN_6H_report.md').write_text('\n'.join(lines)+'\n')
