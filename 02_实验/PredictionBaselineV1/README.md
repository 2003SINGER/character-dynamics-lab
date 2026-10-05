# Prediction Baseline V1 — development protocol

Protocol freeze: **parent accepted; isolated synthetic contract tests passed; development fit authorized**. The pre-run README hash is preserved in both run manifests/snapshots; this post-run edit only records status and routes readers to [RESULTS.md](RESULTS.md), without changing the frozen protocol. Current status: **internal implementation, deterministic reproduction, and statistical audit passed; READY_FOR_INDEPENDENT_REVIEW / DEVELOPMENT ONLY**. This remains neither a formal test nor validation of the project's larger Paper-0 claims.

## Question and scope

Can a small, ordinary conditional behavioral-cloning model use a learned recurrent summary of actor-local observed history to predict the next recorded action better than O-only and fixed-history representations on a predeclared LIGHT development split? The GRU is a standard trainable sequence encoder, not a proposed psychological mechanism or novelty claim. Cho et al. provide a primary-method precedent for recurrent hidden-state updates, conditional softmax likelihood, and gradient training (arXiv:1406.1078v3, §§2.1–2.3, Eqs. 1–8; experiments §4; architecture Appendix A). This implementation is simpler than their sequence encoder-decoder and does not reproduce their translation model.

The source is the already-existing `../T0c_LIGHT/light_actor_local_full_v0.jsonl` (expected 13,463 eligible target rows). It is actor-local and excludes quarantined trajectories according to its upstream gate. It is **development data only**: prior diagnostics already read this dataset. Whole `trajectory_id` hash buckets `<7` train, `7–8` validation/checkpoint selection, and `9` neither train nor score. Bucket is `int(SHA256(trajectory_id UTF-8).hexdigest()[:8], 16) % 10`, matching the existing project split audit. Bucket 9 is not an untouched test. Never report validation as test or use these results to claim generalization.

## Prediction contract

For a target row, inputs are only current `source_O`, its recorded `candidate_set_factual`, and already-occurred `(source_O, source_action_A_star)` pairs from earlier physical-action rows with the same `trajectory_id` and same actor. The target is `source_action_A_star`, independent of the candidate list. Candidate lists are observed support only, **not** reconstructed `A^O`. The first target's initial legal history pair is supplied by `previous_source_O` / `previous_source_action_A_star`; it must be retained. After producing that target's logits, its O/A pair may enter later history for that same actor. Other actors and other episodes never enter history. `trajectory_id`, actor names, indices, and split bucket are metadata only and are not model features. Since `source_O` may itself contain character names/narrative, this protocol does not claim identity or narrative leakage has been eliminated.

`P`, `X`, and real `Δt` are unavailable and are not inferred. This baseline learns a task-specific predictive hidden vector `h`, but does not train or validate the project's named psychological `S` or RuntimeDynamics, causal psychology, appraisal, hidden-W invariance, or the full Paper-0 question. It predicts recorded actions conditional on released O and observed candidate support. `source_action_A_star` is never appended to candidates. Matching strips whitespace and case-folds strings. A target with zero matches is `target_absent_from_normalized_support` (`support_miss`); a target with multiple normalized matches (for example `Bone` and `bone`) is separately counted as `normalized_gold_ambiguity`. Both have no unique target index and are excluded from cross-entropy, but ambiguity is not mislabeled as absence. Neither case repairs, deduplicates, or expands the recorded candidate list.

## Fixed representation and models

Text features use deterministic signed BLAKE2b feature hashing over case-folded Unicode word unigrams and adjacent bigrams. No learned vocabulary, target-derived vocabulary, embedding pretraining, or external model is used. Each text vector is an L2-normalized signed count vector. Dimensions are fixed: current O = 256; each candidate text = 256; each history O = 256 and action = 256; recurrent hidden state = 16. History pair input is `[hash(O,256), hash(A,256)]` (512). Fixed-state baselines consume this same pair representation: last-action zeros the O half and uses fixed signed projection 512→16; fixed-mean averages all pair vectors then uses that projection. Last2 concatenates the latest two pair vectors in order, left-zero-padding if needed, then uses fixed signed projection 1024→16. Learned-mean and learned-last2 use the corresponding mean (512) or ordered last2 (1024) input followed by a trainable Linear→16 + tanh.

Every trained condition uses the same candidate scorer over `[O(256), state(16), candidate(256)]`: Linear 528→32, tanh, Linear 32→1. The readout is therefore structurally shared; total trainable parameter counts are reported separately, and the GRU condition has additional recurrent parameters. This is **not** a parameter-matched comparison.

Conditions, all scored over each row's variable-length recorded candidate set with row-wise softmax cross-entropy:

1. `o_only`: zero state vector.
2. `last_action`: latest 512-dimensional pair input with O zeroed, followed by a deterministic fixed signed 512→16 projection.
3. `last2`: order-aware concatenation of the latest two prior 512-dimensional `(O,A)` vectors, left-zero-padded when only one exists, followed by deterministic fixed signed 1024→16 projection.
4. `fixed_mean`: arithmetic mean of all prior 512-dimensional `(O,A)` vectors, followed by that same fixed projection.
5. `learned_mean`: arithmetic mean of all prior 512-dimensional vectors, followed by trainable Linear 512→16 + tanh and the common readout.
6. `learned_last2`: the same ordered, left-padded 1024-dimensional two-pair input, followed by trainable Linear 1024→16 + tanh and common readout.
7. `gru`: trainable one-layer PyTorch GRU over every prior same-actor 512-dimensional `(O,A)` pair, starting from zero; gradients backpropagate through the full available history and into the common trainable readout.
8. `uniform`: no fitted parameters; probability `1 / candidate_count`.

`learned_mean` and `learned_last2` control for learned projections without recurrence; this is still not total-parameter matched. Strong learned summary and full-history nonrecurrent baselines remain required before broad state-sufficiency or efficiency claims. PyTorch's `nn.GRU` is an ordinary library implementation; its reset-gate application differs in detail from Cho et al.'s Eq. (8) encoder formula (`U(r ⊙ h)`), so this is not a parameter-level or implementation reproduction of Cho's cell.

## Fixed optimization and selection

CPU only; PyTorch deterministic algorithms enabled; one CPU thread; seeds exactly `7, 19, 31`; hidden size 16; batch size 32; Adam learning rate 0.001; no weight decay or scheduler; at most 15 epochs. Epoch permutations use the fixed seed. Select the checkpoint with the lowest validation mean NLL; ties keep the earliest epoch. No result-dependent grid search, feature changes, or condition selection. Validation is evaluated under `no_grad`; it never contributes optimizer gradients. The chosen checkpoint is reloaded and re-evaluated deterministically; mismatch is a hard failure. Record per-epoch train/validation NLL and separate state-encoder/readout gradient norms. For conditions without trainable state encoders, record the state gradient norm as null. Because validation both selects and evaluates checkpoints, all reported validation metrics are post-selection development descriptions, not independent generalization estimates. The three seeds are repeated fits, not independent person/episode samples; do not calculate a training-population CI across them.

## Diagnostics and uncertainty

After checkpoint selection only, score the GRU validation rows with (a) recurrent state forced to zero and (b) histories permuted across different validation episodes within the same actor-history-depth stratum. Use a one-to-one row permutation when a complete cross-episode assignment exists; otherwise mark the affected depth stratum ineligible and preserve the donor mapping/reason. These are diagnostics only: they do not refit, tune, or select checkpoints.

Report actual row, episode, actor-trajectory, target-absent support-miss, normalized-gold-ambiguity, empty-candidate, and scored counts by split; bucket-ID digests; per-row validation NLL; per-seed/condition summaries; actual trainable parameter counts; elapsed time and process peak RSS when available; checkpoint and input hashes. Predeclared validation reporting strata are history depth `==1`, `>=2`, `>=4`, and exclusion of rows marked `exact_previous_pair`; compare conditions on the same eligible row intersection within each stratum and report row/episode counts. Sparse `>=4` results cannot support a long-run claim. Report GRU versus O-only, GRU versus learned-mean, GRU state-zero, and GRU cross-episode-permuted-state NLL and paired episode-cluster bootstrap intervals within each stratum; use the permutation-eligible row intersection. The fixed bootstrap targets the row-weighted mean paired loss difference while resampling episodes. If a metric cannot be computed, emit an explicit null/reason rather than a fabricated value.

The learned vector is only a latent predictive state for this conditional prediction task; it is not the project's named psychological `S` or RuntimeDynamics. The scorer is a conditional candidate model, not a closed-loop policy trained with reinforcement learning. A single cross-entropy fit must not be described as completing or training the project's runtime policy. This script re-encodes each full observed prefix rather than integrating an online Runtime cache; inference work grows with history length. The 16-float vector is 64 bytes only as a theoretical retained latent-state payload, not evidence of actual total memory, latency, or cost advantage.

## Outputs, rerun, and no-overwrite rule

The requested `--out` directory is created with exclusive `mkdir`; an existing path is an error and is never reused or overwritten. At run start, snapshot the exact protocol, train source, and test source bytes into the new output directory and hash them, preserving the reviewed version even if the working files later change. Record the input file SHA-256, protocol/config and README/code/test hashes, Python/PyTorch/NumPy versions, actual seed(s), split metadata and episode IDs, epoch log, per-row validation losses, summaries, and state dictionaries with architecture metadata. Default seeds are 7/19/31; optional `--reproduction-seed` accepts only one of them for an exact rerun in a separate fresh directory, never seed selection. The selected state dictionaries are loaded into fresh model instances and validation predictions checked exactly before success. Do not run on Runtime, LLM, external services, or downloaded models.

Commands from the canonical repository root (test is synthetic-only; each fit output directory must be new):

```bash
/opt/homebrew/opt/python@3.12/bin/python3.12 02_实验/PredictionBaselineV1/test_prediction_baseline_v1.py
/opt/homebrew/opt/python@3.12/bin/python3.12 02_实验/PredictionBaselineV1/train.py --out outputs/prediction_baseline_v1_20261006/run_v1
/opt/homebrew/opt/python@3.12/bin/python3.12 02_实验/PredictionBaselineV1/train.py --reproduction-seed 7 --out outputs/prediction_baseline_v1_20261006/reproduction_seed7_v1
```

The two training commands above document the completed runs and must not be rerun into those existing directories; the exclusive output-path check will refuse them. Use fresh, explicitly named directories for any separately authorized rerun.

## Cho 2014 evidence boundary

Cho et al. §2.1 defines recurrent hidden state and conditional softmax sequence probabilities (Eqs. 1–3); §2.2 trains conditional log-likelihood by gradient-based optimization (Eq. 4); §2.3 defines reset/update gates that modulate past-state use (Eqs. 5–8). Experiments §4 evaluate WMT'14 English–French phrase-pair scoring; Table 1 reports downstream phrase-based SMT BLEU, while the recurrent model supplies an added phrase score (§§3.1, 4.2). Appendix A specifies a zero-initialized encoder recurrence and the decoder's target-prefix conditioning and softmax. This is ordinary algorithmic precedent only, not an action-prediction benchmark or validation of this dataset, split, model, or interpretation.

Primary full text: [Cho et al., arXiv:1406.1078v3](https://arxiv.org/html/1406.1078v3). The repository PDF inventory was checked; no local Cho PDF was found, so this note relies on the canonical full-text HTML rather than an unverified local filename. Appendix B is representation visualization (Figs. 6–7), not additional behavioral evaluation.

## Review gate

The approved synthetic contract test file passed before fitting. Both development runs exited successfully. The parent independently verified the reproduction manifests, input/source/protocol hashes, split and counts, all 36 checkpoint tensors, all 105 epoch records, and all 27,070 per-row loss fields as exact seed-7 rerun matches. A separate statistical audit also checked the cohort, buckets, checkpoint selection, and episode-cluster intervals. Status is therefore **READY_FOR_INDEPENDENT_REVIEW / DEVELOPMENT ONLY**; see [RESULTS.md](RESULTS.md). This is not `CLOSED`, does not validate Paper-0, and does not authorize a commit.
