# LIGHT generic history-compression benchmark v0

This is the depth-stratified closure of the compression gate after `HISTORY_SIGNAL_PRESENT`. It is a generic Replay diagnostic, not a Theory-S experiment.

## Capacity-matched protocol

- `raw_prev`: current 13D feature vector plus current×previous interaction = 26 dimensions.
- `persistent_mean`: current 13D feature vector plus current×fixed cumulative-mean prior same-actor action interaction = 26 dimensions.
- `persistent_permuted`: the same 26-dimensional persistent representation after a deterministic cyclic no-self state permutation separately within train/test and within depth bins (depth 1, depth 2, depth 3, depth 4+), with a different actor-unit donor.
- `raw_last2`: current plus previous and previous-2 interactions = 39 dimensions; this is a higher-capacity reference, not the matched comparison.

The state update is fixed and non-fitted. The first eligible target seeds its history with its already available `previous_source_action_A_star`; later targets append the preceding chosen action. Each row stores the resulting `persistent_state` directly. The benchmark uses the same actor-trajectory split, candidate support, generic feature compiler, linear probe, and paired actor-unit bootstrap for every condition. Depth views are `depth=1`, `depth≥2`, `depth≥3`, and `depth≥4`.

## Nontrivial held-out view: depth stratification

| view / condition | raw-prev bits | persistent bits | permuted bits |
|---|---:|---:|---:|
| depth=1 | 3.2308 | 3.2298 | 3.2351 |
| depth≥2 | 3.3813 | 3.3780 | 3.3862 |
| depth≥3 | 3.4743 | 3.4719 | 3.4737 |
| depth≥4 | 3.6143 | 3.6100 | 3.6064 |

The depth≥2 view contains 665 targets from 380 held-out actor-units; depth≥3 contains 285 targets / 188 units; depth≥4 contains 97 targets / 77 units.

Paired actor-unit bootstrap (Δ is second condition minus first), nontrivial view:

- depth≥2 persistent − raw-prev: **−0.00393 bits**, 95% CI `[-0.00934,+0.00113]`.
- depth≥2 permuted − persistent: **+0.00894 bits**, 95% CI `[+0.00260,+0.01554]`.
- depth≥3 persistent − raw-prev: **−0.00477 bits**, 95% CI `[-0.01745,+0.00587]`.
- depth≥3 permuted − persistent: **+0.00317 bits**, 95% CI `[-0.00600,+0.01243]`.
- depth≥4 persistent − raw-prev: **−0.00803 bits**, 95% CI `[-0.03684,+0.01277]`.
- depth≥4 permuted − persistent: **−0.00069 bits**, 95% CI `[-0.01499,+0.01367]`.

Depth=1 is expected to be near-identical: `S_t` is exactly the one available previous action, so it is not a compression test. The real multi-step comparison is depth≥2. There, cumulative persistent is slightly better than raw-prev in point estimate with an interval crossing zero, while the depth-matched aligned state is clearly better than its permutation. Depth≥3/4 point estimates remain favorable but are underpowered and their permutation intervals cross zero.

Verdict: **`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE`**. The fixed cumulative state preserves aligned multi-step signal on depth≥2, but no formal non-inferiority/compression margin was pre-frozen and deeper strata are not decisive. Do not route to Theory-S, add X, reconstruct candidates, or reopen H0.
