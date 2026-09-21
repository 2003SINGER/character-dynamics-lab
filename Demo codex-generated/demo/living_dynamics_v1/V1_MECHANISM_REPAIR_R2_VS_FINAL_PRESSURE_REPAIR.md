# DemoLivingV1 batch comparison

Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.
Before artifact: `demo-living-v1-mechanism-repair-r2` at `f829d57`.
After artifact: `demo-living-v1-final-pressure-repair` at `baf29b5`.

| Metric | Before | After |
|---|---:|---:|
| `fatigue_mean` mean | 0.5827 | 0.5798 |
| `anxiety_mean` mean | 0.1707 | 0.1901 |
| `satisfaction_mean` mean | 0.7288 | 0.7290 |
| `task_pressure_mean` mean | 0.4070 | 0.5098 |
| `study_minutes` mean | 431.0312 | 430.0312 |
| `sleep_minutes` mean | 631.0781 | 613.8047 |
| `meal_count` mean | 3.2578 | 3.2891 |
| `bathroom_count` mean | 3.0625 | 3.0859 |

## Diagnostics

| Flag | Before actors | After actors |
|---|---:|---:|
| `EXCESSIVE_SLEEP` | 1 | 0 |
| `SATISFACTION_HIGH_SATURATION` | 1 | 1 |
| `UNMET_BATHROOM` | 0 | 1 |

## Interpretation boundary

This comparison records a mechanism-repair checkpoint, not a fitted behavioral target. The after batch uses the current event and continuous audit semantics; any historical diagnostic whose definition changed must be read as contextual rather than a calibrated delta.
