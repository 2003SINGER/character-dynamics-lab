# ClubFloyd Representation Baseline Stage 0 — invalidated checkpoint

> **Status: `STAGE0_V0_INCONCLUSIVE_PROBE_SANITY_FAILED`**

This historical run is retained, but its former `NO_CLEAR_HISTORY_SIGNAL` interpretation is invalidated. The implementation did not use the documented frozen canonicalizer; `C1_RAW_HISTORY` was a heavily compressed hashed representation rather than raw history; source duplication and trivial temporal baselines were not audited; and the 59-row test was too small for a strong positive-CI stop gate. See `representation_baseline_stage0b.md`, `source_integrity_report_stage0b_v0.md`, and `stage0b_baselines.json`.

Run artifact: `outputs/clubfloyd_representation_baseline_structured_v0/result.json`.

- Fixture: 400 deterministic command-like targets, 220 trajectories, minimum 16 past steps; SHA-256 is recorded in `result.json`.
- Target: structured command verb, not open-text command and not finite `A^O`.
- Probe: identical pure-Python 256-dimensional hashed representations and multinomial linear softmax readout; no LLM, no Theory-S, no post-state.
- Test split: 59 trajectory-disjoint targets.

| condition | verb accuracy | macro-F1 |
|---|---:|---:|
| `C0_O_ONLY` | 0.3729 | 0.0474 |
| `C1_RAW_HISTORY` | 0.3390 | 0.0183 |
| `C2_NAIVE_PERSISTENT` | 0.3729 | 0.0474 |
| `C3_PERMUTED_STATE` | 0.3729 | 0.0474 |

Paired semantic-verb accuracy deltas:

- `C1-C0`: mean -0.0339, bootstrap 95% CI [-0.0847, 0.0000]
- `C2-C0`: mean 0.0000, CI [0.0000, 0.0000]
- `C2-C1`: mean +0.0339, CI [0.0000, 0.0847]
- `C3-C2`: mean 0.0000, CI [0.0000, 0.0000]

## Gate

`HISTORY_SIGNAL_PRESENT = false` in this first bounded structured canary. Therefore the frozen gate is **NO_CLEAR_HISTORY_SIGNAL** and the ClubFloyd Theory-S bridge must stop here. This is a development diagnostic, not a population-level claim: the canary is command-like and deterministic, but the test split is only 59 targets and the fixed hash probe is intentionally simple.

Do not rescue this result by adding an LLM, changing the evaluator, changing aliases, or training Theory-S. Any follow-up must first revisit the structured estimand/probe or canary design as a separately frozen development run.
