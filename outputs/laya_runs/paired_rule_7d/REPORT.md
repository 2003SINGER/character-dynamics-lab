# Same-world character evaluation — 7 days

Policy: `rule-policy-v0`. Demo engineering evidence only.

Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, scenario seed, task/event tape and policy RNG seed. Only P changes within a case.

## Personality comparison

| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |
|---|---:|---:|---:|---:|---:|
| balanced | 255.9 | 239.0 | 321.9 | 410.3 | 0.286 |
| disciplined | 235.0 | 245.7 | 377.0 | 371.1 | 0.286 |
| procrastinating | 240.0 | 252.0 | 333.3 | 398.6 | 0.286 |
| rest_seeking | 223.1 | 265.9 | 368.6 | 368.9 | 0.286 |
| stimulation_seeking | 250.0 | 254.7 | 316.6 | 395.0 | 0.286 |
| anxious | 220.0 | 264.9 | 350.3 | 385.0 | 0.286 |
| body_sensitive | 252.3 | 244.7 | 394.3 | 358.7 | 0.286 |
| spontaneous | 255.0 | 238.0 | 400.6 | 367.6 | 0.286 |

## Persistence, commitment and action patterns

Action bouts are keyed by RunningAction start time, not boundary count. Commitment duration is attributed to its pre-boundary status. Entropy and repeats use selected action starts, without a pathology threshold.

| Profile | Mean bout min | P90 bout min | Active I min/day | Suspended I min/day | Entropy bits | Switches/day | Max same-action streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced | 34.2 | 60.0 | 447.1 | 141.0 | 3.154 | 32.3 | 6.0 |
| disciplined | 34.3 | 60.0 | 381.7 | 186.1 | 3.205 | 33.6 | 8.0 |
| procrastinating | 33.2 | 60.0 | 457.9 | 359.7 | 3.190 | 34.0 | 5.0 |
| rest_seeking | 32.9 | 60.0 | 299.0 | 212.1 | 3.194 | 34.3 | 5.0 |
| stimulation_seeking | 33.4 | 60.0 | 429.3 | 221.4 | 3.129 | 33.6 | 8.0 |
| anxious | 32.4 | 60.0 | 383.3 | 207.6 | 3.225 | 33.6 | 7.0 |
| body_sensitive | 34.3 | 60.0 | 384.6 | 373.1 | 3.325 | 34.9 | 7.0 |
| spontaneous | 35.6 | 60.0 | 359.0 | 329.0 | 3.319 | 31.9 | 8.0 |

## History forks

At each checkpoint, W/O/P and the policy RNG position are copied. Correct, neutral-reset and prior-day S/commitment receive the same future external tape.

| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |
|---|---:|---:|---:|---:|---:|
| reset | 6h | 0.2634 | 62.5% | 51.0 min | 0.667 |
| reset | 24h | 0.2634 | 62.5% | 8.8 min | 0.000 |
| reset | 72h | 0.2634 | 62.5% | 50.9 min | 1.311 |
| stale_24h | 6h | 0.5677 | 100.0% | 30.2 min | 0.381 |
| stale_24h | 24h | 0.5677 | 100.0% | 15.2 min | 0.000 |
| stale_24h | 72h | 0.5677 | 100.0% | 57.1 min | 1.775 |

## Limits

This tape reuses one room and deterministic recurring coursework every three days. It provides repeated opportunities, interruptions and deadlines, but does not model a full life. Strong or weak differentiation is a fact about this Demo and tape. The historical 48h batch was not paired and is not personality evidence.
