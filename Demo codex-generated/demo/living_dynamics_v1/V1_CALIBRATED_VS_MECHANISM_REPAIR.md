# DemoLivingV1 batch comparison

Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.
Before artifact: `demo-living-v1-calibrated` at `555aca9`.
After artifact: `demo-living-v1-mechanism-repair` at `685ec6a`.

| Metric | Before | After |
|---|---:|---:|
| `fatigue_mean` mean | 0.4101 | 0.5543 |
| `anxiety_mean` mean | 0.2891 | 0.1688 |
| `satisfaction_mean` mean | 0.6934 | 0.7169 |
| `task_pressure_mean` mean | 0.4072 | 0.4445 |
| `study_minutes` mean | 439.0781 | 406.3047 |
| `sleep_minutes` mean | 861.8984 | 508.8125 |
| `meal_count` mean | 3.6250 | 3.4844 |
| `bathroom_count` mean | 3.0312 | 3.1484 |

## Diagnostics

| Flag | Before actors | After actors |
|---|---:|---:|
| `ANXIETY_HIGH_SATURATION` | 2 | 0 |
| `ANXIETY_LOW_SATURATION` | 77 | 9 |
| `EXCESSIVE_SLEEP` | 36 | 0 |
| `FATIGUE_HIGH_SATURATION` | 0 | 1 |
| `FATIGUE_LOW_SATURATION` | 51 | 7 |
| `HUNGER_HIGH_SATURATION` | 1 | 0 |
| `SCREEN_STRAIN_LOW_SATURATION` | 116 | 0 |
| `SCREEN_STRAIN_UNRESPONSIVE` | 0 | 77 |
| `TASK_PRESSURE_HIGH_SATURATION` | 48 | 0 |
| `TASK_PRESSURE_LOW_SATURATION` | 79 | 0 |
| `UNMET_BATHROOM` | 26 | 11 |
| `UNMET_HUNGER` | 21 | 11 |

## Interpretation boundary

This comparison records a mechanism-repair checkpoint, not a fitted behavioral target. The after batch uses the current event and continuous audit semantics; any historical diagnostic whose definition changed must be read as contextual rather than a calibrated delta.
