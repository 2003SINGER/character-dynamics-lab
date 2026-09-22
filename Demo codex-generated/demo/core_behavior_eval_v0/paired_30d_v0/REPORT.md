# Same-world character evaluation — 30 days

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 177.7 | 273.8 | 390.0 | 372.6 | 0.333 |
| disciplined | 178.4 | 269.6 | 381.5 | 372.0 | 0.333 |
| procrastinating | 188.4 | 269.7 | 385.2 | 377.2 | 0.333 |
| rest_seeking | 177.0 | 275.7 | 390.6 | 372.5 | 0.333 |
| stimulation_seeking | 183.1 | 276.7 | 358.9 | 390.5 | 0.333 |
| anxious | 181.5 | 272.6 | 380.9 | 375.0 | 0.333 |
| body_sensitive | 176.0 | 272.2 | 390.2 | 367.2 | 0.333 |
| spontaneous | 184.4 | 271.9 | 367.1 | 385.4 | 0.333 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.2602 | 62.5% | 106.2 min | 1.646 |
| reset | 24h | 0.2602 | 62.5% | 69.9 min | 0.787 |
| reset | 72h | 0.2602 | 62.5% | 57.6 min | 0.495 |
| stale_24h | 6h | 0.3913 | 81.2% | 42.7 min | 0.624 |
| stale_24h | 24h | 0.3913 | 81.2% | 33.1 min | 0.409 |
| stale_24h | 72h | 0.3913 | 81.2% | 62.3 min | 0.679 |

## Unseen-tape profile identification

Leave-one-tape-out nearest centroid: 8/24 = 33.3%; eight-way chance = 12.5%. This is a diagnostic, not a calibrated human validity metric.

## Single-axis P interventions

Each row holds all other P dimensions, W and RNG fixed; values are 0.2/0.5/0.8.

- `procrastination` study min/day: 174.1 / 175.0 / 188.5; rest min/day: 385.3 / 375.3 / 370.3
- `self_control` study min/day: 171.5 / 175.0 / 173.6; rest min/day: 416.7 / 375.3 / 424.7
- `rest_preference` study min/day: 186.5 / 175.0 / 186.7; rest min/day: 372.4 / 375.3 / 427.1
- `stimulation_seeking` study min/day: 186.7 / 175.0 / 183.5; rest min/day: 406.4 / 375.3 / 383.2
- `task_anxiety_sensitivity` study min/day: 185.3 / 175.0 / 185.4; rest min/day: 393.6 / 375.3 / 397.7
- `screen_strain_sensitivity` study min/day: 175.0 / 175.0 / 175.0; rest min/day: 375.3 / 375.3 / 375.3
- `need_response` study min/day: 181.4 / 175.0 / 178.8; rest min/day: 426.7 / 375.3 / 363.7
- `action_noise` study min/day: 177.1 / 175.0 / 173.8; rest min/day: 396.9 / 375.3 / 359.4

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
