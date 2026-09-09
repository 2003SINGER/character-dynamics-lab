#!/usr/bin/env python3
"""Regression guard for Simulation-owned ParameterConfig propagation."""
from pathlib import Path
src=Path(__file__).parents[1]/'Demo codex-generated'/'Src'/'simulation.cpp'
text=src.read_text(encoding='utf-8')
assert text.count('scenario.information_access,\n                                                             ActionType::Count, config_') >= 1
assert text.count('hidden_config.information_access,\n                ActionType::Count, config_') >= 1
assert text.count('control_config.information_access,\n                ActionType::Count, config_') >= 1
assert text.count('visible_config.information_access,\n                ActionType::Count, config_') >= 1
for needle in ('update_state(state, meal_appraisal, personality, meal.elapsed_minutes, config_)','update_state(state, rest_appraisal, personality, rest.elapsed_minutes, config_)','decide(deferred_observation, deferred_state, personality, config_)','decide(preserved_observation, state, personality, config_)'):
    assert needle in text, needle
print('config propagation guard: PASS')
