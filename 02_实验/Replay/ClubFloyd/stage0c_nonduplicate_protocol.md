# ClubFloyd Stage 0c — non-duplicate sensitivity protocol

Stage 0c is a bounded development analysis. It does not alter the lossless source replay, canonical target rules, optimizer, or Theory-S status.

## Frozen strata

For each target with an immediately preceding history row:

- `EXACT_DUPLICATE_PAIR`: `O_t=O_{t-1}` and raw `A*_t=A*_{t-1}`.
- `ACTION_REPEAT_ONLY`: `O_t≠O_{t-1}` and raw action equal.
- `OBSERVATION_REPEAT_ONLY`: `O_t=O_{t-1}` and raw action different.
- `GENUINE_TRANSITION`: both observation and raw action differ.

An orthogonal diagnostic records `RAW_ACTION_REPEAT`, `CANONICAL_VERB_REPEAT_RAW_DIFFERENT`, and `CANONICAL_VERB_TRANSITION`. The raw source and Stage0b fixture remain untouched.

## Versioned non-duplicate analysis view

`representation_baseline_stage0c_nonduplicate.fixture.jsonl` excludes only exact target/previous pair repeats. This is an analysis view, not source deduplication. It contains 1,964 of the original 4,000 rows; 2,036 exact repeats are excluded by the predeclared rule. The view and source fixture hashes are recorded in its manifest.

The same committed Stage0b runner (`017b966`) and fixed `O_DIM=64`, seed, epochs, and trajectory-disjoint split are used.

## Results

On the original 384-row test split, corrected macro-F1 and accuracy are in `stage0b_duplicate_sensitivity.json`. The exact-repeat group is 190 rows; the four-way non-repeat groups are action-only 10, observation-only 6, and genuine transition 178. `O+PREV_VERB` reaches 0.3034 on genuine transitions versus `O_ONLY` 0.3315; `O+LAST2` reaches 0.3539.

On the independent versioned non-duplicate analysis view (194 test rows):

| condition | accuracy | macro-F1 |
|---|---:|---:|
| `O_ONLY` | 0.2990 | 0.0249 |
| `O + PREV_VERB` | 0.2835 | 0.0339 |
| `O + LAST2_VERB_HISTORY` | 0.2887 | 0.0405 |

The current low-order verb-family estimand therefore has no positive non-duplicate history increment in this bounded view. Do not proceed to history compression or Theory-S from this result. Stop here and decide whether a different data asset is required; any reopening must begin with a newly frozen protocol rather than repeated tuning of this slice.
