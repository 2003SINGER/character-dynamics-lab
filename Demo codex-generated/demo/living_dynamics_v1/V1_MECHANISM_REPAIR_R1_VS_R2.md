# DemoLivingV1 batch comparison

Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.
Before artifact: `demo-living-v1-mechanism-repair` at `685ec6a`.
After artifact: `demo-living-v1-mechanism-repair-r2` at `f829d57`.

| Metric | Before | After |
|---|---:|---:|
| `fatigue_mean` mean | 0.5543 | 0.5827 |
| `anxiety_mean` mean | 0.1688 | 0.1707 |
| `satisfaction_mean` mean | 0.7169 | 0.7288 |
| `task_pressure_mean` mean | 0.4445 | 0.4070 |
| `study_minutes` mean | 406.3047 | 431.0312 |
| `sleep_minutes` mean | 508.8125 | 631.0781 |
| `meal_count` mean | 3.4844 | 3.2578 |
| `bathroom_count` mean | 3.1484 | 3.0625 |

## Diagnostics

| Flag | Before actors | After actors |
|---|---:|---:|
| `ANXIETY_LOW_SATURATION` | 9 | 0 |
| `EXCESSIVE_SLEEP` | 0 | 1 |
| `FATIGUE_HIGH_SATURATION` | 1 | 0 |
| `FATIGUE_LOW_SATURATION` | 7 | 0 |
| `SATISFACTION_HIGH_SATURATION` | 0 | 1 |
| `SCREEN_STRAIN_UNRESPONSIVE` | 77 | 0 |
| `UNMET_BATHROOM` | 11 | 0 |
| `UNMET_HUNGER` | 11 | 0 |

## Interpretation boundary

This comparison records a mechanism-repair checkpoint, not a fitted behavioral target. The after batch uses the current event and continuous audit semantics; any historical diagnostic whose definition changed must be read as contextual rather than a calibrated delta.
