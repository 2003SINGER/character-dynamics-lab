# LIGHT generic history-compression benchmark v0

This is the depth × nontrivial closure of the compression gate after `HISTORY_SIGNAL_PRESENT`. It is a generic Replay diagnostic, not a Theory-S experiment.

## Capacity-matched protocol

- `raw_prev`: current 13D feature vector plus current×previous interaction = 26 dimensions.
- `persistent_mean`: current 13D feature vector plus current×fixed cumulative-mean prior same-actor action interaction = 26 dimensions.
- `persistent_permuted`: the same 26-dimensional persistent representation after a deterministic cyclic no-self state permutation separately within train/test and within depth bins, with a different actor-unit donor.
- `raw_last2`: current plus previous and previous-2 interactions = 39 dimensions; this is a higher-capacity reference, not the matched comparison.

The state update is fixed and non-fitted. The first eligible target seeds its history with its already available `previous_source_action_A_star`; later targets append the preceding chosen action. Each row stores the resulting `persistent_state` directly. The benchmark uses the same actor-trajectory split, candidate support, generic feature compiler, linear probe, and paired actor-unit bootstrap for every condition.

## Nontrivial × depth held-out views

| view | rows / units | raw-prev bits | persistent bits | permuted bits |
|---|---:|---:|---:|---:|
| depth=1 | 647 / 647 | 3.2794 | 3.2767 | 3.2867 |
| depth≥2 | 636 / 373 | 3.4092 | 3.4076 | 3.4177 |
| depth≥3 | 274 / 183 | 3.4647 | 3.4661 | 3.4705 |
| depth≥4 | 92 / 74 | 3.5844 | 3.5837 | 3.5856 |

These views all exclude exact `(O_t,A*_t) == (O_prev,A*_prev)` repeats. The primary compression view is **nontrivial × depth≥2**.

Paired actor-unit bootstrap (Δ is second condition minus first):

- depth≥2 persistent − raw-prev: **−0.00219 bits**, 95% CI `[-0.00746,+0.00301]`.
- depth≥2 permuted − persistent: **+0.01020 bits**, 95% CI `[+0.00367,+0.01661]`.
- depth≥3 persistent − raw-prev: **+0.00040 bits**, 95% CI `[-0.01192,+0.01129]`.
- depth≥3 permuted − persistent: **+0.00429 bits**, 95% CI `[-0.00504,+0.01369]`.
- depth≥4 persistent − raw-prev: **−0.00529 bits**, 95% CI `[-0.03512,+0.01489]`.
- depth≥4 permuted − persistent: **+0.00488 bits**, 95% CI `[-0.00863,+0.01764]`.

The depth=1 view is not a compression test because `S_t` is exactly the one available previous action. In the primary nontrivial × depth≥2 view, cumulative persistent is slightly better than raw-prev in point estimate with an interval crossing zero, and the depth-matched aligned state is clearly better than its permutation. Deeper strata are small and inconclusive.

Verdict: **`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE`**. A fixed cumulative state carries aligned multi-step signal after exact-repeat shortcuts are excluded, but no formal non-inferiority/compression margin was pre-frozen. Do not route to Theory-S, add X, reconstruct candidates, or reopen H0.
