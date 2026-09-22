# Same-world character evaluation — 30 days

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 183.3 | 271.4 | 383.5 | 375.7 | 0.333 |
| disciplined | 178.2 | 268.4 | 389.5 | 367.8 | 0.333 |
| procrastinating | 184.4 | 273.3 | 376.4 | 380.2 | 0.333 |
| rest_seeking | 180.1 | 272.5 | 395.3 | 367.4 | 0.333 |
| stimulation_seeking | 184.3 | 275.7 | 364.0 | 386.8 | 0.333 |
| anxious | 180.8 | 272.3 | 390.8 | 371.7 | 0.333 |
| body_sensitive | 177.2 | 270.9 | 388.2 | 368.8 | 0.333 |
| spontaneous | 185.9 | 271.4 | 377.9 | 378.2 | 0.333 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.2690 | 68.8% | 92.1 min | 1.389 |
| reset | 24h | 0.2690 | 68.8% | 55.2 min | 0.675 |
| reset | 72h | 0.2690 | 68.8% | 60.4 min | 0.555 |
| stale_24h | 6h | 0.3741 | 83.6% | 41.2 min | 0.631 |
| stale_24h | 24h | 0.3741 | 83.6% | 37.6 min | 0.519 |
| stale_24h | 72h | 0.3741 | 83.6% | 63.0 min | 0.582 |

## Unseen-tape profile identification

Leave-one-tape-out nearest centroid: 31/64 = 48.4%; eight-way chance = 12.5%. This is a diagnostic, not a calibrated human validity metric.

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
