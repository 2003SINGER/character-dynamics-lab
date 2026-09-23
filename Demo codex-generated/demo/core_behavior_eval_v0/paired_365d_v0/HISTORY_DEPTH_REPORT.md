# History-fork persistence by checkpoint

Each row compares the same actor's actual S/commitment against a neutral reset or prior-day S/commitment. W/O/P, RunningAction, policy RNG state and future external event tape are held fixed at the fork. Immediate JS is measured once at that checkpoint; later gaps are separate trajectories, not a new JS score.

| Day | Alternative | Immediate JS | Top-1 changed | 6h/24h/72h absolute study gap (min) | 72h state L1 | 72h commitment changed |
|---:|---|---:|---:|---:|---:|---:|
| 7 | reset | 0.203 | 48.4% | 44.4/19.5/71.4 | 1.149 | 56.2% |
| 7 | stale_24h | 0.500 | 93.8% | 30.7/18.7/69.4 | 1.085 | 57.8% |
| 30 | reset | 0.335 | 89.1% | 139.8/91.0/49.3 | 0.656 | 0.0% |
| 30 | stale_24h | 0.248 | 73.4% | 51.7/56.5/56.6 | 0.615 | 0.0% |
| 60 | reset | 0.343 | 82.8% | 137.1/108.1/59.0 | 0.726 | 0.0% |
| 60 | stale_24h | 0.253 | 54.7% | 46.6/65.5/51.2 | 0.644 | 0.0% |
| 120 | reset | 0.340 | 78.1% | 133.0/98.0/59.0 | 0.632 | 0.0% |
| 120 | stale_24h | 0.249 | 56.2% | 56.1/77.3/46.2 | 0.628 | 0.0% |
| 180 | reset | 0.323 | 79.7% | 127.8/88.1/62.0 | 0.663 | 0.0% |
| 180 | stale_24h | 0.252 | 53.1% | 51.1/66.8/55.8 | 0.633 | 0.0% |

A cumulative study-time gap at 72h does not alone prove that the current state remains different; use the 72h state and commitment columns for that claim. All numbers describe this Demo under its synthetic life tape only.
