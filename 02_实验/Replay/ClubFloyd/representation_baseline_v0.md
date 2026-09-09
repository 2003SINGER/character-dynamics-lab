# ClubFloyd Representation Baseline Stage 0

Status: frozen structured development diagnostic. No LLM predictor, summarizer, updater, Theory-S training, or formal Paper-0 test.

## Question

Does observable history improve prediction of the next observed chosen action `A*` at the structured command-verb level, and can a capacity-controlled persistent representation retain that value?

## Target and canary

- Target: `verb(A*_t)`, extracted deterministically from raw command with frozen `command_schema_v0` vocabulary; raw command remains preserved.
- Fixture: `representation_baseline_v0.fixture.jsonl`, deterministic SHA-256-ranked command-like targets, at least 16 same-trajectory past steps, no post/future fields. It is a bounded development canary, not a full-population estimate.
- Split: trajectory-disjoint train/validation/dev; target rows and labels are identical across conditions.

## Fixed-capacity representations

Every condition emits the same 256-dimensional vector and uses the same multinomial linear softmax probe, optimizer, seed, and regularization.

- `C0_O_ONLY`: deterministic hashed bag of current `source_O_t` only.
- `C1_RAW_HISTORY`: current `source_O_t` plus ordered last 16 `(source_O, source_action_A_star)` pairs, position-weighted into the same 256 dimensions.
- `C2_NAIVE_PERSISTENT`: causal EMA state `R_{t+1}=0.85 R_t+0.15 hash(O_t,A_t)` over the same trajectory, combined with current `source_O_t` under the same 256-dimensional budget. This is generic engineering state, not Theory-S.
- `C3_PERMUTED_STATE`: same `C2` construction with a fixed trajectory permutation of past observations, a negative control for causal history alignment.

No candidate set, `A^O`, `A^W`, natural-language generation, LLM, or post-state is used.

## Metrics and frozen gates

Primary metric: verb accuracy. Secondary metrics: macro-F1 and row-level paired bootstrap 95% CIs (10,000 deterministic resamples) for `C1-C0`, `C2-C0`, `C2-C1`, and `C3-C2`.

- `HISTORY_SIGNAL_PRESENT` iff the lower CI of `C1-C0` is > 0.
- Only if history signal is present: `PERSISTENT_COMPRESSION_SUPPORTED` iff the lower CI of `C2-C0` is > 0 and the lower CI of `C2-C1` is >= -0.03.
- `C3` must not beat causally aligned `C2`; it is an alignment/leakage diagnostic.

Positive results mean only that a fixed structured probe can exploit information in the corresponding representation. They do not establish psychological state, Theory-S validity, or that persistent state contains more information than raw history.
