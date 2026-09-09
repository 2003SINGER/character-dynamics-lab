# LIGHT generic history-compression benchmark v0

This is the first compression gate after `HISTORY_SIGNAL_PRESENT`. It is a generic Replay diagnostic, not a Theory-S experiment.

## Capacity-matched protocol

- `raw_prev`: current 13D feature vector plus current×previous interaction = 26 dimensions.
- `persistent_mean`: current 13D feature vector plus current×fixed cumulative-mean prior same-actor action interaction = 26 dimensions.
- `persistent_permuted`: the same 26-dimensional persistent representation after a deterministic cyclic no-self state permutation performed separately within train and test.
- `raw_last2`: current plus previous and previous-2 interactions = 39 dimensions; this is a higher-capacity reference, not the matched comparison.

The state update is fixed and non-fitted. The first eligible target seeds its history with its already available `previous_source_action_A_star`; later targets append the preceding chosen action. Each row stores the resulting `persistent_state` directly. The benchmark uses the same actor-trajectory split, candidate support, generic feature compiler, linear probe, and paired actor-unit bootstrap for every condition.

## Nontrivial held-out view

| condition | dimensions | NLL bits | MRR | top-1 |
|---|---:|---:|---:|---:|
| raw previous | 26 | 3.3437 | .3475 | .1645 |
| persistent cumulative mean | 26 | 3.3416 | .3516 | .1707 |
| persistent permuted | 26 | 3.3510 | .3410 | .1543 |
| raw last-2 reference | 39 | 3.3416 | .3600 | .1738 |

Paired actor-unit bootstrap, nontrivial view:

- persistent mean − raw previous: **−0.00189 bits**, 95% CI `[-0.00429,+0.00067]`.
- persistent permuted − persistent mean: **+0.00984 bits**, 95% CI `[+0.00411,+0.01511]`.
- raw last-2 − raw previous: **−0.00306 bits**, 95% CI `[-0.00589,+0.00181]`.

## Gate reading

After the implementation repair, the cumulative-mean persistent representation is slightly better than raw-previous in point estimate, but the paired interval crosses zero. The aligned persistent state is clearly better than its within-split no-self permutation. The higher-capacity raw-last-2 reference remains only weakly different from raw-previous.

Verdict: **`COMPRESSION_V0_CORRECTED_INCONCLUSIVE`**. The corrected run supports an aligned persistent representation carrying the history signal, but does not establish a formal compression/non-inferiority claim because no margin was pre-frozen. Do not route to Theory-S, add X, reconstruct candidates, or reopen H0.
