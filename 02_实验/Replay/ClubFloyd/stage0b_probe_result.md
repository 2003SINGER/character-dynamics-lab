# Stage 0b low-order probe result

`stage0b_probe_result.json` records the deterministic run on fixture SHA-256 `1151ad7867e0d724098be188b625f6ea221cd312f5e30013ded8d4c5009b5a7a` (2,871 train rows, 384 trajectory-disjoint test rows).

| condition | accuracy | macro-F1 |
|---|---:|---:|
| `O_ONLY` | 0.3281 | 0.0358 |
| `O + PREV_VERB` | 0.6276 | 0.5376 |
| `O + LAST2_VERB_HISTORY` | 0.6484 | 0.5266 |

The probe now reads the obvious temporal signal. This repairs the Stage-0 measurement gate. It does not show that ClubFloyd has a persistent psychological state, and it does not validate Theory-S; it only establishes that canonical low-order action history contains incremental predictive information after current `O`.
