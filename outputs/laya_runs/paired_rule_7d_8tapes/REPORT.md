# Same-world character evaluation — 7 days

Policy: `rule-policy-v0`. Demo engineering evidence only.

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 221.9 | 256.3 | 369.1 | 378.3 | 0.304 |
| disciplined | 217.7 | 253.9 | 367.8 | 375.6 | 0.304 |
| procrastinating | 224.6 | 262.2 | 370.6 | 378.7 | 0.286 |
| rest_seeking | 210.3 | 265.4 | 385.2 | 363.5 | 0.304 |
| stimulation_seeking | 219.5 | 266.0 | 352.6 | 384.1 | 0.286 |
| anxious | 214.3 | 261.1 | 387.9 | 368.4 | 0.286 |
| body_sensitive | 213.6 | 257.6 | 346.3 | 390.5 | 0.321 |
| spontaneous | 218.1 | 264.0 | 364.5 | 378.7 | 0.286 |

## Persistence, commitment and action patterns

Action bouts are keyed by RunningAction start time, not boundary count. Commitment duration is attributed to its pre-boundary status. Entropy and repeats use selected action starts, without a pathology threshold.

| Profile | Mean bout min | P90 bout min | Active I min/day | Suspended I min/day | Entropy bits | Switches/day | Max same-action streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced | 33.3 | 60.0 | 376.7 | 222.9 | 3.184 | 33.6 | 7.5 |
| disciplined | 33.1 | 60.0 | 365.9 | 196.3 | 3.143 | 33.3 | 8.8 |
| procrastinating | 33.9 | 60.0 | 394.7 | 234.1 | 3.215 | 33.4 | 8.6 |
| rest_seeking | 33.1 | 60.0 | 360.6 | 179.0 | 3.168 | 33.4 | 8.9 |
| stimulation_seeking | 33.2 | 60.0 | 375.6 | 236.3 | 3.172 | 34.3 | 8.1 |
| anxious | 33.8 | 60.0 | 371.2 | 214.2 | 3.210 | 33.6 | 6.8 |
| body_sensitive | 32.4 | 60.0 | 377.0 | 191.2 | 3.124 | 33.9 | 10.0 |
| spontaneous | 33.4 | 60.0 | 379.9 | 241.0 | 3.177 | 33.3 | 7.9 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.2032 | 48.4% | 44.4 min | 0.479 |
| reset | 24h | 0.2032 | 48.4% | 19.5 min | 0.000 |
| reset | 72h | 0.2032 | 48.4% | 71.4 min | 1.109 |
| stale_24h | 6h | 0.4998 | 93.8% | 30.7 min | 0.415 |
| stale_24h | 24h | 0.4998 | 93.8% | 18.7 min | 0.000 |
| stale_24h | 72h | 0.4998 | 93.8% | 69.4 min | 1.164 |

## Unseen-tape profile identification

Leave-one-tape-out nearest centroid: 20/64 = 31.2%; eight-way chance = 12.5%. This is a diagnostic, not a calibrated human validity metric.

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
