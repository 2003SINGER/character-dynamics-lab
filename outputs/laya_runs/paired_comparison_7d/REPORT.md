# Paired policy comparison — 7 days

8 actor pairs; same World tape, initial W/O/S/I, P, RNG seed and Dynamics verified. Only policy changes.

| Metric | Laya − Rule |
|---|---:|
| study_minutes | -24.750 |
| leisure_minutes | -1.018 |
| rest_minutes | +176.250 |
| sleep_minutes | -101.018 |
| idle_minutes | -40.143 |
| bodily_minutes | -9.232 |
| task_completions | +0.000 |
| decision_count | -3.571 |
| mean_action_bout_minutes | +2.992 |
| median_action_bout_minutes | +4.375 |
| p90_action_bout_minutes | +0.000 |
| commitment_active_minutes_per_day | -11.143 |
| commitment_suspended_minutes_per_day | +184.411 |
| action_entropy_bits | -0.011 |
| switches_per_day | -2.000 |
| max_same_action_streak | -0.125 |
| repeat_transition_fraction | -0.021 |

## History fork delta

| Branch | Horizon | Δ immediate π JS | Δ top-1 change rate | Δ study gap min |
|---|---:|---:|---:|---:|
| reset | 6h | -0.0373 | +0.375 | +35.6 |
| reset | 24h | -0.0373 | +0.375 | +17.0 |
| reset | 72h | -0.0373 | +0.375 | +56.0 |
| stale_24h | 6h | -0.2230 | -0.375 | +24.2 |
| stale_24h | 24h | -0.2230 | -0.375 | +1.9 |
| stale_24h | 72h | -0.2230 | -0.375 | +26.1 |

Same synthetic one-room tape and seeded policy sampling. The Laya checkpoint was trained on other synthetic workflows; this is not human-character validity or calibrated probability evidence.
