# Same-world character evaluation — 180 days

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 180.7 | 269.3 | 390.8 | 375.4 | 0.333 |
| disciplined | 177.3 | 264.2 | 406.2 | 362.8 | 0.333 |
| procrastinating | 180.4 | 272.9 | 374.8 | 385.7 | 0.333 |
| rest_seeking | 178.6 | 268.3 | 412.8 | 362.9 | 0.333 |
| stimulation_seeking | 182.7 | 271.5 | 370.2 | 388.6 | 0.333 |
| anxious | 178.8 | 270.5 | 387.6 | 377.7 | 0.333 |
| body_sensitive | 177.4 | 267.8 | 403.8 | 365.4 | 0.333 |
| spontaneous | 183.0 | 270.1 | 382.9 | 379.4 | 0.333 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.3090 | 75.6% | 116.4 min | 1.815 |
| reset | 24h | 0.3090 | 75.6% | 80.9 min | 1.007 |
| reset | 72h | 0.3090 | 75.6% | 60.1 min | 0.222 |
| stale_24h | 6h | 0.3005 | 66.2% | 47.2 min | 0.798 |
| stale_24h | 24h | 0.3005 | 66.2% | 56.9 min | 0.862 |
| stale_24h | 72h | 0.3005 | 66.2% | 55.8 min | 0.233 |

## Unseen-tape profile identification

Leave-one-tape-out nearest centroid: 45/64 = 70.3%; eight-way chance = 12.5%. This is a diagnostic, not a calibrated human validity metric.

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
