# Stage 0b low-order probe result

`stage0b_probe_result.json` records the deterministic run produced by committed runner `017b9669af76b271328ed8b968ad06c9b80b7178` (runner SHA-256 `78b2bae43543dd704ec5d50da7210a2f9e47cd8e37f5606967a2f87cda733de7`) on fixture SHA-256 `1151ad7867e0d724098be188b625f6ea221cd312f5e30013ded8d4c5009b5a7a` (2,871 train rows, 384 trajectory-disjoint test rows). `O_DIM=64`, `epochs=4`, seed `20260908`.

| condition | accuracy | macro-F1 |
|---|---:|---:|
| `O_ONLY` | 0.328125 | 0.0358257843 |
| `O + PREV_VERB` | 0.6276041667 | 0.5375584155 |
| `O + LAST2_VERB_HISTORY` | 0.6484375000 | 0.5265836799 |

Feature dimensions are respectively 64, 91, and 118. Two independent runs from this same committed runner are bitwise identical; see `stage0b_probe_reproducibility.json`.

The probe now reads the obvious temporal signal. This repairs the Stage-0 measurement gate. It does not show that ClubFloyd has a persistent psychological state, and it does not validate Theory-S; it only establishes that canonical low-order action history contains incremental predictive information after current `O`.
