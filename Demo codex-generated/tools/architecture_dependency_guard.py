import pathlib, sys

root = pathlib.Path(sys.argv[1])
cmake = (root / 'CMakeLists.txt').read_text()
engine_block = cmake.split('add_library(character_dynamics_engine', 1)[1].split('add_library(character_dynamics_reference', 1)[0]
for forbidden in ('Src/state.cpp', 'Src/appraisal.cpp', 'Src/decision.cpp', 'Src/living_dynamics.cpp', 'Src/simulation.cpp'):
    if forbidden in engine_block:
        raise SystemExit(f'engine target contains behavior source: {forbidden}')
engine = [root / 'Src' / 'continuous_runtime.cpp', root / 'Src' / 'runtime_scheduler.cpp', root / 'Src' / 'world.cpp', root / 'Src' / 'simulation.cpp']
for path in engine:
    text = path.read_text()
    if 'demo_living' in text or 'living_dynamics' in text or 'reference_rule_dynamics' in text:
        raise SystemExit(f'engine imports behavior model: {path}')
for path in [root / 'Src' / 'reference_rule_dynamics_v0.cpp']:
    if 'demo_living' in path.read_text():
        raise SystemExit(f'reference imports demo model: {path}')
if (root / 'Src' / 'free_run_v2.cpp').exists() or (root / 'Src' / 'free_run_v4.cpp').exists():
    raise SystemExit('stale free-run implementation remains')
print('architecture dependency guard: PASS')
