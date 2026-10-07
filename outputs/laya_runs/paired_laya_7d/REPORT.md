# Same-world character evaluation — 7 days

Policy: `laya-typed-policy-v0`. Demo engineering evidence only.

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 217.0 | 251.4 | 553.3 | 276.9 | 0.286 |
| disciplined | 207.0 | 242.1 | 574.0 | 254.1 | 0.286 |
| procrastinating | 220.0 | 254.3 | 547.1 | 267.0 | 0.286 |
| rest_seeking | 204.6 | 262.1 | 525.3 | 284.4 | 0.286 |
| stimulation_seeking | 234.0 | 243.4 | 483.9 | 317.1 | 0.286 |
| anxious | 214.6 | 239.4 | 529.6 | 294.1 | 0.286 |
| body_sensitive | 216.1 | 255.7 | 494.4 | 293.3 | 0.286 |
| spontaneous | 220.0 | 248.1 | 564.9 | 260.0 | 0.286 |

## Persistence, commitment and action patterns

Action bouts are keyed by RunningAction start time, not boundary count. Commitment duration is attributed to its pre-boundary status. Entropy and repeats use selected action starts, without a pathology threshold.

| Profile | Mean bout min | P90 bout min | Active I min/day | Suspended I min/day | Entropy bits | Switches/day | Max same-action streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced | 38.0 | 60.0 | 314.3 | 488.3 | 3.189 | 31.9 | 5.0 |
| disciplined | 36.7 | 60.0 | 322.1 | 497.6 | 3.175 | 31.3 | 5.0 |
| procrastinating | 37.9 | 60.0 | 382.6 | 457.7 | 3.198 | 31.1 | 7.0 |
| rest_seeking | 35.0 | 60.0 | 316.7 | 487.3 | 3.255 | 32.6 | 8.0 |
| stimulation_seeking | 37.3 | 60.0 | 509.4 | 260.4 | 3.247 | 29.7 | 7.0 |
| anxious | 37.5 | 60.0 | 356.4 | 463.1 | 3.214 | 31.0 | 7.0 |
| body_sensitive | 35.1 | 60.0 | 449.3 | 392.1 | 3.172 | 31.4 | 7.0 |
| spontaneous | 36.7 | 60.0 | 401.9 | 458.9 | 3.207 | 33.0 | 7.0 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.2261 | 100.0% | 86.6 min | 1.384 |
| reset | 24h | 0.2261 | 100.0% | 25.8 min | 0.000 |
| reset | 72h | 0.2261 | 100.0% | 106.9 min | 1.979 |
| stale_24h | 6h | 0.3447 | 62.5% | 54.5 min | 0.840 |
| stale_24h | 24h | 0.3447 | 62.5% | 17.1 min | 0.000 |
| stale_24h | 72h | 0.3447 | 62.5% | 83.2 min | 1.874 |

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
