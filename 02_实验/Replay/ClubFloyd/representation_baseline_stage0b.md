# ClubFloyd Representation Baseline — Stage 0b

Stage 0b is a probe-sanity and source-integrity checkpoint. It is development-only and does not authorize a Theory-S bridge.

## Frozen protocol

- Fixture: `representation_baseline_stage0b.fixture.jsonl`, 4,000 deterministic targets, 417 trajectories, maximum 10 targets per trajectory, minimum 16 past steps; trajectory-disjoint train/test split, 2,871/384 rows.
- Target: canonical verb family of observed `source_action_A_star`; raw command remains retained.
- Canonicalization: reuse `command_schema_v0.canonical_verb_family`; aliases `get→take`, `x→examine`, `i/inv→inventory`, and compass/direction shorthands→`navigation`. Rules are frozen from the command schema, not selected from v0 scores.
- Conditions to run next: `O_ONLY`, `O + PREV_VERB`, and `O + LAST_K_VERB_HISTORY` under one fixed-capacity linear probe. The prior `C1_RAW_HISTORY` is renamed conceptually to `C1_HASHED_HISTORY_16`: it is a 256-D hashed compression, not a raw-history benchmark.
- No LLM predictor, Theory-S state, candidate reconstruction, evaluator tuning, or provenance-free deduplication.

## Trivial sanity baselines

`stage0b_baselines.json` reports the no-training checks. On the frozen 4,000-row slice:

| baseline | accuracy | macro-F1 |
|---|---:|---:|
| B0 global majority | 0.3177 | 0.0185 |
| B1 previous canonical verb | 0.6120 | 0.5730 |
| B2 first-order Markov | 0.6198 | 0.5281 |

B1/B2 are far above the majority baseline. Therefore the old v0 learned probe did not establish “no history signal”; it failed its own sanity check. The valid current interpretation is only that the measurement instrument/protocol was defective and requires the low-order Stage 0b probe before any persistent-state comparison.
