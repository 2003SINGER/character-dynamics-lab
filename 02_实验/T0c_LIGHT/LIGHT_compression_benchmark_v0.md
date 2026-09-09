# LIGHT generic history-compression benchmark v0

This is the first compression gate after `HISTORY_SIGNAL_PRESENT`. It is a generic Replay diagnostic, not a Theory-S experiment.

## Capacity-matched protocol

- `raw_prev`: current 13D feature vector plus current×previous interaction = 26 dimensions.
- `persistent_mean`: current 13D feature vector plus current×fixed cumulative-mean prior same-actor action interaction = 26 dimensions.
- `persistent_permuted`: the same 26-dimensional persistent representation after a deterministic cyclic state permutation.
- `raw_last2`: current plus previous and previous-2 interactions = 39 dimensions; this is a higher-capacity reference, not the matched comparison.

The state update is fixed and non-fitted. The benchmark uses the same actor-trajectory split, candidate support, generic feature compiler, linear probe, and paired actor-unit bootstrap for every condition.

## Nontrivial held-out view

| condition | dimensions | NLL bits | MRR | top-1 |
|---|---:|---:|---:|---:|
| raw previous | 26 | 3.3437 | .3475 | .1645 |
| persistent cumulative mean | 26 | 3.3547 | .3488 | .1629 |
| persistent permuted | 26 | 3.3517 | .3406 | .1543 |
| raw last-2 reference | 39 | 3.3416 | .3600 | .1738 |

Paired actor-unit bootstrap, nontrivial view:

- persistent mean − raw previous: **+0.00732 bits**, 95% CI `[-0.00165,+0.01285]`.
- persistent permuted − persistent mean: **+0.00153 bits**, 95% CI `[-0.00706,+0.00749]`.
- raw last-2 − raw previous: **−0.00306 bits**, 95% CI `[-0.00589,+0.00181]`.

## Gate reading

The naive cumulative-mean persistent representation is not shown to be non-inferior to the 26D raw-previous representation. Its point estimate is slightly worse, but the paired interval crosses zero. The persistent permutation comparison is also inconclusive. The higher-capacity raw-last-2 reference is only weakly better and is not a compression win.

Verdict: **`COMPRESSION_NOT_ESTABLISHED`**. This does not revoke `HISTORY_SIGNAL_PRESENT`; it says only that this first fixed naive persistent state has not yet compressed the generic history signal without measurable loss. Do not route to Theory-S, add X, reconstruct candidates, or reopen H0.
