import pathlib, subprocess, sys

root = pathlib.Path(sys.argv[1])
repo = root.parent
for name in ('appraisal.cpp', 'state.cpp', 'decision.cpp'):
    expected = subprocess.check_output(['git', 'show', f'5d3c164:Demo codex-generated/Src/{name}'], cwd=repo)
    actual = (root / 'Src' / f'reference_{name}').read_bytes()
    if actual.rstrip(b'\n') != expected.rstrip(b'\n'):
        raise SystemExit(f'ReferenceRuleDynamicsV0 parity mismatch: {name}')
print('reference rule dynamics v0 parity: PASS (5d3c164 exact source match)')
