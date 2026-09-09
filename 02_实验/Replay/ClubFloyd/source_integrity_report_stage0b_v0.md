# ClubFloyd Stage 0b source-integrity report

This is a diagnostic audit, not a deduplication pass. The lossless raw replay is unchanged.

## Fixture findings

On the immutable 400-row v0 fixture (220 trajectories, 16 history steps):

| check | result |
|---|---:|
| adjacent history `(O,A*)` exact duplicate rate | 2,998 / 6,000 = **49.97%** |
| target action equals immediately previous action | 227 / 400 = **56.75%** |
| target `O` equals immediately previous `O` | 214 / 400 = **53.50%** |
| target `(O,A*)` equals immediately previous pair | 211 / 400 = **52.75%** |

The deterministic 20-case spot check resolves the sampled pairs against the corresponding cleaned CALM HTML at the same step indices. The duplicated pairs are present in the raw transcript representation; there is no evidence in this audit that the adapter introduced them. This does not establish that every repeated command is non-behavioural, so no collapse is performed.

The machine-readable evidence is `source_integrity_stage0b_v0.json`; the procedure is `source_integrity_stage0b.py`.

## Frozen handling rule

Keep the lossless source replay. Any future analysis view may collapse records only under a separately versioned, evidence-backed rule that distinguishes systematic duplicate records from a player's genuine repeated command. The current Stage 0b fixture therefore retains all rows.
