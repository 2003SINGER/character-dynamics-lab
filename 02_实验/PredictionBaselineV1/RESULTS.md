# PredictionBaselineV1 — development fit results

Status: **internal implementation, deterministic reproduction, and statistical audit passed; READY_FOR_INDEPENDENT_REVIEW / DEVELOPMENT ONLY**. This is not an untouched test, an accepted paper result, evidence for a named psychological state, or completion of Paper-0.

The 14 contract tests also passed an independent local rerun. The repository's existing runtime-regression workflow does not execute training or contract tests for this new Torch baseline; remote CI results are separate engineering evidence and do not substitute for baseline-specific testing, fitting, and reproduction.

## Frozen run and data accounting

- Full fit: `outputs/prediction_baseline_v1_20261006/run_v1`; 7 trained conditions × seeds 7/19/31 × 15 epochs (315 epoch records), plus uniform and frozen diagnostics. Total elapsed time recorded by the runner: 177.70 s.
- Independent seed-7 rerun: `outputs/prediction_baseline_v1_20261006/reproduction_seed7_v1`; process exited 0 and wrote 105 epoch records. Parent independently checked both manifests, source/protocol/input hashes, counts and split; all 36 checkpoint state tensors across the seven trained conditions, all 105 epoch records, and all 27,070 validation loss fields (2,707 rows × 10 losses) were exactly equal to the corresponding full-run seed-7 outputs. A separate statistical audit checked cohort, buckets, checkpoint selection, and episode-cluster intervals. This is a deterministic rerun check, not new evidence.
- Input: existing full actor-local LIGHT JSONL, 13,463 rows, SHA-256 `e6f214b91ed644b60543cf442fdae4255ff177d26a25fccd750ab5c7381ba195`. Frozen trainer SHA-256 `b06e5192e72dc50c4da7a34c6664a77537830ac9f92cc75f6355c0ff92fde854`; protocol README SHA-256 `a7acbb81f543790cddb1e821ab8009656ddfb41dd1f98a81e94b32035f08259e`; functional test source SHA-256 `ca3bd753226f2153a8030197954e7d1f148218b50d5d4873f0adb78c5dc16fa1`.
- Run environment recorded in `run_v1/config.json`: Python 3.12.14, PyTorch 2.14.0, NumPy 2.5.3, macOS 27.0.1 arm64; CPU-only, one Torch thread, deterministic algorithms enabled.
- Split is by whole `trajectory_id`: `int(SHA256(id)[:8],16) % 10`; buckets 0–6 train, 7–8 development validation, bucket 9 excluded from both. Counts from the frozen run config:

  | Partition | Episodes | Rows | Scored | Normalized-gold ambiguities | Gold absent from recorded support |
  |---|---:|---:|---:|---:|---:|
  | Train | 3,490 | 9,530 | 9,488 | 42 | 0 |
  | Validation | 986 | 2,717 | 2,707 | 10 | 0 |
  | Bucket 9 excluded | 468 | 1,216 | 1,211 | 5 | 0 |

  The normalized-match ambiguities are excluded from scoring rather than deduplicated or repaired. Bucket 9 had been read by earlier development diagnostics; it is not an untouched formal test. Validation checkpoint selection and validation reporting use the same partition, so all validation metrics below are post-selection descriptive development metrics.

## Main results

NLL in nats, lower is better. Each triplet is the result for seeds **7 / 19 / 31** on the same scored validation rows. “Learned mean” is a trainable 512→16 projection of mean history; “GRU” is a learned predictive history encoder. The repeated seeds are repeated fits, not independent episode samples.

| Condition | All validation rows, NLL by seed |
|---|---|
| Uniform | 2.333493 (not trained) |
| O-only | 2.288914 / 2.287347 / 2.289976 |
| Last action | 2.288775 / 2.281660 / 2.289102 |
| Fixed ordered last-2 | 2.288889 / 2.282243 / 2.289886 |
| Fixed mean history | 2.288909 / 2.282961 / 2.289826 |
| Learned mean history | 2.278479 / 2.275963 / 2.278588 |
| Learned ordered last-2 | 2.287788 / 2.285611 / 2.287694 |
| GRU learned history | 2.282451 / 2.276331 / 2.278623 |

The across-seed descriptive mean is 2.288746 for O-only, 2.279135 for GRU, and 2.277676 for learned mean. GRU is modestly better than O-only on the complete validation slice on average, but each seed’s paired episode-cluster 95% CI for GRU−O-only includes zero: seed 7 −0.006463 [−0.021362, 0.008154], seed 19 −0.011016 [−0.023330, 0.001986], seed 31 −0.011353 [−0.027552, 0.004508]. GRU is not distinguishable here from the learned-mean baseline: paired GRU−learned-mean deltas are +0.003973 [−0.002692, 0.011096], +0.000368 [−0.006421, 0.007042], and +0.000035 [−0.008052, 0.008165], respectively.

The frozen `nontrivial_not_exact_previous_pair` slice contains 2,577 rows across 958 episodes. Mean NLL is 2.308314 for O-only, 2.311072 for GRU, and 2.310150 for learned mean. GRU−O-only deltas are positive for all seeds (+0.004905, +0.000093, +0.003275); their episode-cluster intervals include zero. Thus the apparent all-row gain is not robust to this predeclared exclusion, and this baseline does **not** establish a general history advantage. The stronger trainable learned-mean comparator is at least as good overall.

| Predeclared validation slice | Rows / episodes | O-only mean NLL | Learned-mean mean NLL | GRU mean NLL | GRU−O-only paired episode-cluster 95% CI by seed (7 / 19 / 31) |
|---|---:|---:|---:|---:|---|
| All | 2,707 / 985 | 2.288746 | 2.277676 | 2.279135 | [−.021362,.008154] / [−.023330,.001986] / [−.027552,.004508] |
| History depth = 1 | 1,392 / 984 | 2.223126 | 2.243510 | 2.238781 | [−.000397,.035512] / [−.006124,.024078] / [.000877,.039133] |
| History depth ≥ 2 | 1,315 / 586 | 2.358208 | 2.313844 | 2.321852 | [−.054777,−.010067] / [−.051930,−.012001] / [−.068827,−.019710] |
| History depth ≥ 4 | 220 / 149 | 2.579382 | 2.481852 | 2.490528 | [−.153091,−.041750] / [−.109925,−.012931] / [−.172712,−.043814] |
| Not exact previous O/A pair | 2,577 / 958 | 2.308314 | 2.310150 | 2.311072 | [−.008831,.018568] / [−.011961,.012042] / [−.011432,.017925] |

The stratified NLL triplets for the three focal conditions (seed order 7/19/31) are:

| Slice | O-only | Learned mean | GRU |
|---|---|---|---|
| All | 2.288914 / 2.287347 / 2.289976 | 2.278479 / 2.275963 / 2.278588 | 2.282451 / 2.276331 / 2.278623 |
| Depth = 1 | 2.221138 / 2.226211 / 2.222028 | 2.239716 / 2.241102 / 2.249712 | 2.238942 / 2.235516 / 2.241885 |
| Depth ≥ 2 | 2.360658 / 2.352063 / 2.361903 | 2.319511 / 2.312866 / 2.309154 | 2.328509 / 2.319536 / 2.317511 |
| Depth ≥ 4 | 2.589296 / 2.555879 / 2.592970 | 2.492246 / 2.480971 / 2.472339 | 2.491974 / 2.492924 / 2.486687 |
| Not exact previous O/A pair | 2.307467 / 2.309309 / 2.308166 | 2.308642 / 2.308687 / 2.313122 | 2.312372 / 2.309402 / 2.311441 |

The apparent GRU improvements at depth ≥2 and ≥4 are descriptive slices, and the learned-mean baseline is similarly strong. Depth ≥4 is only 220 rows/149 episodes; do not interpret it as long-run evidence. Because checkpoint selection used these same validation rows, the CIs quantify episode-cluster variation conditional on selected fits; they do not correct for checkpoint-selection optimism or provide an untouched generalization estimate. Bootstrap is paired and row-weighted, sampling episodes; seeds are not pooled as population replicates.

## State diagnostics, parameters, and cost

State-zero and depth-matched cross-episode permutation diagnostics were computed without refitting. For every seed, GRU had lower NLL than both diagnostics on all validation rows (GRU−state-zero about −0.109 to −0.115; GRU−permuted about −0.039 to −0.055 nats, with episode-cluster intervals excluding zero). This indicates sensitivity of this selected predictor to its supplied history/state under these interventions; it is not evidence that the state represents a psychological construct or that history improves over fair trainable alternatives. Diagnostic permutations were aligned across the eligible validation intersection; no model selection used them.

The trainer recorded non-null state-encoder gradient norms across 45 epoch×seed observations for each trainable encoder: learned mean mean 0.173826 (range 0.000692–0.309153), learned last-2 mean 0.219372 (0.003910–0.411750), GRU mean 0.188070 (0.000576–0.409316). These are mean batch gradient norms from the training log, not evidence of useful or psychologically interpretable learning.

| Condition family | State-encoder params | Shared readout params | Total trainable params |
|---|---:|---:|---:|
| O-only / last-action / fixed last-2 / fixed mean | 0 | 16,961 | 16,961 |
| Learned mean | 8,208 | 16,961 | 25,169 |
| Learned last-2 | 16,400 | 16,961 | 33,361 |
| GRU | 25,440 | 16,961 | 42,401 |

Parameter counts are actual architecture counts; total capacity is not matched. Inference re-encodes each row’s full prefix, and online runtime memory/latency was not measured. The reported 64 bytes for a 16-float32 state is only theoretical retained-vector storage, not end-to-end memory or speed evidence. PyTorch GRU uses its own reset-gate placement variant; this is a standard-method adaptation, not a faithful implementation reproduction of Cho et al. (2014).

## Interpretation boundary / next decision

This is ordinary candidate-set conditional behavioral cloning with a learned latent predictive history representation, not a closed-loop RL-trained character policy. It does not train or validate the project’s named psychological `S` or `RuntimeDynamics`, does not establish causal psychological evidence, and does not test `A^O`, `P`, `X`, counterfactual persona changes, or real elapsed-time effects. The [source/task admission audit](../../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md) confirms that current O is an environmental snapshot, and history contains only prior same-actor physical O/A pairs. Dialogue, emotes, partner-action history and persona were omitted from this view; their presence upstream does not establish their pre-action availability. Consequently this is not a comparison using full LIGHT-observed history, and a weak result is not evidence that full history or psychological state is useless. Environment narratives may still contain identity cues. A strong learned full-history non-recurrent summary has not been implemented. No Runtime/demo coefficients or previous artifacts were changed.

The result supports only this bounded conclusion: the baseline was actually gradient-trained and its seed-7 rerun was exact under the recorded checks, but the frozen development comparison does not show a robust advantage of recurrent history over O-only on the nontrivial slice, and GRU does not beat a learned-mean history projection. Independent review and a future genuinely untouched evaluation are required before stronger claims. Novelty has not been verified.

Raw per-row losses, epoch metrics, split IDs, configs, checkpoints, snapshots, and manifests remain in the ignored run directories above.
