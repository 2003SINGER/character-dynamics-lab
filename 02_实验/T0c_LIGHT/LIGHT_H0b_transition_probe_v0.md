# LIGHT H0b generic action-transition history probe

H0b repairs the H0 feature defect without introducing a LIGHT-specific ontology. For each candidate, the frozen generic Replay feature vector `f(a_t)` is combined with elementwise interactions against the generic feature vector of the previous same-actor action and, for L2, the previous-2 same-actor action. A capacity-matched history permutation is run with the same feature dimensions and split. No LLM, Theory-S state, new X field, candidate reconstruction, or source mutation is used.

Provenance is machine-locked in `light_h0b_transition_probe_v0.json`: runner commit `9dbee3c8834ecc931ccfebd5669e1e3348b5f742`, runner SHA, generic feature compiler SHA, generic probe SHA, rules SHA, and full-view SHA.

## Nontrivial actor-unit test results

| condition | NLL bits | MRR | top-1 |
|---|---:|---:|---:|
| L0 `O_ONLY` | 3.3501 | 0.3440 | 0.1582 |
| L1 correct previous-action interaction | 3.3437 | 0.3474 | 0.1645 |
| L2 correct last-2 interaction | 3.3418 | 0.3599 | 0.1754 |
| L1 permuted history | 3.3506 | 0.3453 | 0.1590 |
| L2 permuted history | 3.3512 | 0.3447 | 0.1582 |

Paired actor-unit bootstrap on the nontrivial view:

- L1 vs L0: ΔNLL `-0.00451` nats, 95% CI `[-0.00732,-0.00150]`, Δbits `-0.00651`.
- L2 vs L0: ΔNLL `-0.00676` nats, 95% CI `[-0.01098,-0.00223]`, Δbits `-0.00975`.
- L1 correct vs permuted: ΔNLL `-0.00480` nats, 95% CI `[-0.00806,-0.00157]`.
- L2 correct vs permuted: ΔNLL `-0.00797` nats, 95% CI `[-0.01246,-0.00295]`.

The aligned transition interaction beats both O-only and the capacity-matched permuted control in the nontrivial view. Verdict: **`HISTORY_SIGNAL_PRESENT`** for this generic source-support diagnostic. The next permitted step is a generic/raw-history versus naive persistent-compression comparison; do not jump directly to Theory-S.
