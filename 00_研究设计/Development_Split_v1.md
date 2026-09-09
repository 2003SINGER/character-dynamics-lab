# Development Split v1

Frozen synthetic Character Dynamics internal split. It is separate from LIGHT,
ClubFloyd, AGAIN, and every external replay asset.

- `optimizer_train`: world seeds 1101–1128 (28 disjoint seeds)
- `internal_holdout`: world seeds 2101–2112 (12 disjoint seeds)
- personality/world combinations are disjoint across the two sets
- phone, deadline, and commitment fixtures are regression hard gates, never rewards
- split seeds and gate definitions are protocol inputs, not optimizer parameters

The current smoke runner uses the checked-in batch as a plumbing fixture; it
does not claim a trained or generalizing model. `DEVELOPMENT_SPLIT_V1 = FROZEN / NOT_READY`
until a fresh seed-controlled engine batch is recorded for both partitions.
