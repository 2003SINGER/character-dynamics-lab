# Stage 0b duplicate-structure sensitivity

This analysis reuses the exact committed runner (`017b9669af76b271328ed8b968ad06c9b80b7178`, SHA-256 `78b2bae43543dd704ec5d50da7210a2f9e47cd8e37f5606967a2f87cda733de7`) and the frozen fixture SHA-256 `1151ad7867e0d724098be188b625f6ea221cd312f5e30013ded8d4c5009b5a7a`. It does not modify the model, target, split, optimizer, or source replay.

The stratification is applied to the 384-row trajectory-disjoint test set, not to all 4,000 fixture rows: 190 rows are exact target/previous `(O,A*)` duplicates and 194 are non-duplicates.

| condition | exact-duplicate pair | non-duplicate pair |
|---|---:|---:|
| `O_ONLY` | 0.3421 | 0.3144 |
| `O + PREV_VERB` | 0.9474 | 0.3144 |
| `O + LAST2_VERB_HISTORY` | 0.9579 | 0.3454 |

The previous-verb gain is therefore overwhelmingly concentrated in exact duplicate pairs. On the current four-way stratification, the corrected macro-F1 is reported in the JSON (the earlier all-zero macro-F1 artifact was a label-type bug and is superseded). On genuine transitions, `O + PREV_VERB` is below `O_ONLY`; `LAST2` is only modestly higher. This does not prove that all non-duplicate history is useless, but it blocks interpreting the overall 62–65% result as evidence for a persistent character state. See [Stage 0c](stage0c_nonduplicate_protocol.md) for the frozen analysis view.

The machine-readable output is `stage0b_duplicate_sensitivity.json`; the analysis procedure is `analyze_stage0b_duplicate_sensitivity.py`. No deduplication has been applied to the source or fixture.
