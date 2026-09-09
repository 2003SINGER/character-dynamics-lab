# LIGHT H0b generic action-transition history probe

H0b tests generic action-transition history without introducing a LIGHT-specific ontology. For each candidate, the frozen Replay feature vector `f(a_t)` is combined with elementwise interactions against the generic feature vector of the previous same-actor action and, for L2, the previous-2 same-actor action. The L2 observation source is explicitly `previous2_source_O`; the gate artifact preserves that field. A capacity-matched history permutation is run with the same feature dimensions and split. No LLM, Theory-S state, new X field, candidate reconstruction, or source mutation is used.

Provenance is machine-locked in `light_h0b_transition_probe_v0.json`. The corrected run uses the full actor-local view with 4,823 train units and 684 test units.

## Nontrivial actor-unit test results

| condition | NLL bits | MRR | top-1 |
|---|---:|---:|---:|
| L0 `O_ONLY` | 3.3501 | 0.3440 | 0.1582 |
| L1 correct previous-action interaction | 3.3437 | 0.3475 | 0.1645 |
| L2 correct last-2 interaction | 3.3416 | 0.3600 | 0.1738 |
| L1 permuted history | 3.3506 | 0.3453 | 0.1590 |
| L2 permuted history | 3.3522 | 0.3448 | 0.1582 |

Paired actor-unit bootstrap on the nontrivial view:

- L1 vs L0: ΔNLL `-0.00451` nats, 95% CI `[-0.00732,-0.00150]`, Δbits `-0.00651`.
- L2 vs L0: ΔNLL `-0.00663` nats, 95% CI `[-0.01078,-0.00221]`, Δbits `-0.00957`.
- L1 correct vs permuted: ΔNLL `-0.00480` nats, 95% CI `[-0.00806,-0.00157]`.
- L2 correct vs permuted: ΔNLL `-0.00841` nats, 95% CI `[-0.01294,-0.00351]`.

The aligned transition interaction beats O-only and the capacity-matched permuted control in the nontrivial view. The effect is small, so the verdict remains **`HISTORY_SIGNAL_PRESENT`** only for this generic source-support diagnostic. The next permitted step is the rank/capacity-matched generic/raw-history versus naive persistent-compression benchmark; do not jump directly to Theory-S.
