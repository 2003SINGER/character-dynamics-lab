# History-fork persistence by checkpoint

Each row compares the same actor's actual S/commitment against a neutral reset or prior-day S/commitment. W/O/P, RunningAction, policy RNG state and future external event tape are held fixed at the fork. Immediate JS is measured once at that checkpoint; later gaps are separate trajectories, not a new JS score.

| Day | Alternative | Immediate JS | Top-1 changed | 6h/24h/72h absolute study gap (min) | 72h state L1 | 72h commitment changed |
|---:|---|---:|---:|---:|---:|---:|
| 7 | reset | 0.203 | 48.4% | 44.4/19.5/71.4 | 1.149 | 56.2% |
| 7 | stale_24h | 0.500 | 93.8% | 30.7/18.7/69.4 | 1.085 | 57.8% |

A cumulative study-time gap at 72h does not alone prove that the current state remains different; use the 72h state and commitment columns for that claim. All numbers describe this Demo under its synthetic life tape only.
