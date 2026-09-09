# LIGHT Actor-Local History Eligibility Gate v0

This is a development-only eligibility gate. It does not validate `A^O`, Theory-S, six-dimensional `X`, or a psychological claim.

## Frozen boundary and audit

Input is the existing non-quarantine LIGHT physical-action replay. A legal past action is restricted to the same trajectory, same actor, and earlier physical-action row. Other actors never enter the action-history features. The two analysis surfaces are:

- **FULL**: all eligible actor-local targets;
- **NONTRIVIAL**: the same targets excluding exact previous `(source_O, source_action_A_star)` repeats.

Audit result: 13,463 eligible targets across 6,869 actor-trajectory units; history depth ≥1/2/3/4 = 13,463 / 6,594 / 2,871 / 1,067. Contiguous same-actor targets: 6,706; gapped same-actor targets: 6,757. Gap counts 0/1/2/3/4+ are 6,706 / 5,679 / 919 / 136 / 23. `source_O` is non-empty for 100%; observed `A*` is in the source candidate list for 100%; previous same-actor `A*` remains in the current source list for 29.59%. Raw previous-action repeat is 5.37%; exact previous `(O,A*)` repeat is 4.65%.

The source candidate list is treated only as observed support, never as `A^O`. Raw replay is unchanged. Machine-readable audit: `light_actor_local_history_gate_v0.json`; surfaces: `light_actor_local_full_v0.jsonl` and `light_actor_local_nontrivial_v0.jsonl`.

## Low-order probe

The generic frozen Replay feature/readout (`replay-raw-features-v1` plus candidate-specific previous-action indicators) was reused; no LIGHT action ontology, new `X` field, candidate reconstruction, or Theory-S state was introduced. Actor-trajectory units are split deterministically; 4,823 train units and 684 test units.

| condition | full NLL bits | nontrivial NLL bits | nontrivial MRR | nontrivial top-1 |
|---|---:|---:|---:|---:|
| L0 `O_ONLY` | 3.3080 | 3.3501 | 0.3440 | 0.1582 |
| L1 `O + PREV_SAME_ACTOR_ACTION` | 3.3050 | 3.3676 | 0.3095 | 0.1083 |
| L2 `O + LAST2_SAME_ACTOR_HISTORY` | 3.3044 | 3.3672 | 0.3120 | 0.1130 |

On the full view, L1/L2 improve NLL only slightly. On the predeclared nontrivial view they worsen NLL: paired actor-unit bootstrap ΔNLL is +0.01341 nats (95% CI `[+0.01044,+0.01638]`) for L1 and +0.01403 nats (95% CI `[+0.01021,+0.01794]`) for L2. Uniform support baseline is 3.3287 bits; repeat-last uses a frozen ε=0.001 smoothing for NLL and has 12.99% top-1.

## Verdict

The earlier `NO_CLEAR_ACTOR_LOCAL_HISTORY_SIGNAL` verdict is superseded as **`LIGHT_H0_INCONCLUSIVE_HISTORY_FEATURE_TOO_NARROW`**. The equality-bit probe only tested whether a current candidate exactly repeated the previous action; it did not represent the previous action's generic semantics. Do not route to OPeRA from this artifact alone. See the H0b transition probe.
