# DemoLivingV1 before vs calibrated

Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.

| Metric | Frozen V1 | Calibrated |
|---|---:|---:|
| `fatigue_mean` mean | 0.3073 | 0.4101 |
| `anxiety_mean` mean | 0.0648 | 0.2891 |
| `satisfaction_mean` mean | 0.8660 | 0.6934 |
| `task_pressure_mean` mean | 0.3880 | 0.4072 |
| `study_minutes` mean | 451.3594 | 439.0781 |
| `sleep_minutes` mean | 615.4609 | 861.8984 |
| `meal_count` mean | 2.9219 | 3.6250 |
| `bathroom_count` mean | 2.8281 | 3.0312 |

## Saturation diagnostics

| Flag | Frozen V1 actors | Calibrated actors |
|---|---:|---:|
| `ANXIETY_HIGH_SATURATION` | 0 | 2 |
| `ANXIETY_LOW_SATURATION` | 119 | 77 |
| `BATHROOM_URGE_HIGH_SATURATION` | 1 | 0 |
| `EXCESSIVE_SLEEP` | 2 | 36 |
| `FATIGUE_LOW_SATURATION` | 114 | 51 |
| `HUNGER_HIGH_SATURATION` | 1 | 1 |
| `NO_SLEEP_48H` | 1 | 0 |
| `SATISFACTION_HIGH_SATURATION` | 107 | 0 |
| `SCREEN_STRAIN_LOW_SATURATION` | 103 | 116 |
| `TASK_PRESSURE_HIGH_SATURATION` | 48 | 48 |
| `TASK_PRESSURE_LOW_SATURATION` | 79 | 79 |
| `UNMET_BATHROOM` | 16 | 26 |
| `UNMET_HUNGER` | 17 | 21 |

## Interpretation boundary

The calibration removed the prior >80% same-extreme collapse for fatigue, anxiety and satisfaction without changing Runtime or the action surface. `EXCESSIVE_SLEEP` increases and remains a documented demo diagnostic; it is not tuned further in this milestone because no predefined sleep target is an acceptance objective.
