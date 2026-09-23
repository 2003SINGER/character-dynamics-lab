# Same-world character evaluation — 365 days

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 182.2 | 267.9 | 391.2 | 376.2 | 0.334 |
| disciplined | 179.1 | 262.5 | 405.6 | 363.8 | 0.334 |
| procrastinating | 181.3 | 271.7 | 378.3 | 384.9 | 0.334 |
| rest_seeking | 179.7 | 266.8 | 413.7 | 363.5 | 0.334 |
| stimulation_seeking | 184.0 | 270.0 | 369.2 | 389.2 | 0.334 |
| anxious | 180.2 | 268.6 | 392.2 | 376.0 | 0.334 |
| body_sensitive | 179.0 | 266.5 | 401.7 | 367.6 | 0.334 |
| spontaneous | 184.7 | 268.4 | 385.0 | 379.2 | 0.334 |

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

Leave-one-tape-out nearest centroid: 54/64 = 84.4%; eight-way chance = 12.5%. This is a diagnostic, not a calibrated human validity metric.

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
