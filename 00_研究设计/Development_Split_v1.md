# Development Split v1

Frozen synthetic Character Dynamics internal split. It is separate from LIGHT,
ClubFloyd, AGAIN, and every external replay asset.

- `optimizer_train`: world seeds 1101–1128 (28 disjoint seeds)
- `internal_holdout`: world seeds 2101–2112 (12 disjoint seeds)
- personality/world combinations are disjoint across the two sets
- phone, deadline, and commitment fixtures are regression hard gates, never rewards
- split seeds and gate definitions are protocol inputs, not optimizer parameters

Fresh default-configuration train and holdout batches are now recorded under
`outputs/development_split_v1/`; the machine-readable audit reports zero seed
overlap and both evaluator regressions pass. `DEVELOPMENT_SPLIT_V1 = FROZEN / READY`.
