# LIGHT Source-Record Conditional Command Ranking V1

Status: **TASK_AND_CHANNEL_SPEC_PARENT_ACCEPTED / TRAINER_NOT_ADMITTED**  
`training_authorized=false`  
The parent has accepted the task, channels, and proposed training specification below. This README freezes those protocol choices; it does not record projection implementation or acceptance status. That evidence is maintained separately in `INPUT_REVIEW.md`, which this document does not create. Nothing here should be read as a PASS. This is not an official LIGHT reproduction, an actor-visible pre-output forecast, a trained runtime policy, or Paper-0 evidence.

## Question and estimand

On the existing fixed cohort of 13,463 rows whose source record has a nonempty physical command, evaluate two distinct conditional-ranking increments on the frozen episode split:

1. **History relative to context-only:** does the core prior-history condition improve ranking over `context_only`?
2. **Ordered history relative to pooled history:** does `gru_core` improve ranking over `pooled_core`?

The estimand is conditional on inclusion in this source-filtered cohort and on each row's recorded support. It is not the probability that a character acts, the probability of a successful world effect, or performance over a complete population of turns. Since eligibility requires a nonempty recorded physical command, this cohort cannot answer whether to act or not. The source-filtering path is inherited, not redefined here; its conditionality must remain visible in all claims.

The target is a **nonempty recorded command attempt**. It is not verified successful behavior or a validated `A*`. The first comparison tests history's incremental ranking value over recorded context; the second tests whether this specified ordered encoder helps over this specified pooled encoder. Neither is a complete Paper-0 summary comparison. These tests do not establish psychological state `S` or authorize an actor-facing policy.

## Evidence boundary and channel permissions

`raw_turn_index < target_raw_turn_index` defines strict temporal ordering in the processed source arrays. It does not prove when a field was shown, whether it was actor-visible, whether a command succeeded, or whether a partner observed the raw command. Unknown timing and source/context provenance remain unknown. Do not promote a field to actor-visible on the basis of this protocol.

| Channel or field | Protocol treatment | Permission and interpretation |
|---|---|---|
| Target `recorded_environment_snapshot` (`context` at target) | Candidate input, conditionally admitted for this source-record task | Recorded environment snapshot only. Its action-pre time is unverified; not asserted to be actor-visible `O` or complete `O`. Include a snapshot-only condition and preserve this qualification. |
| Target `recorded_support` (`available_actions` at target) | Candidate ranking surface, kept byte/content faithful to source | A recorded support list, not reconstructed legal set `A^O`. Preserve the original list and ordering. Do not add the target, normalize/merge entries, or repair missing/ambiguous support. |
| Self persona | Candidate input condition, isolated in ablation | Use only the uniquely matched target actor's recorded persona. This is a source-record conditional feature, not proven to be visible at prediction time. Never use partner persona. |
| Strict-past self speech | History channel, separately ablatable | Recorded speech on raw turns strictly before target. Temporal eligibility only; actor visibility/timing remains unverified. |
| Strict-past self emote | History channel, separately ablatable | Recorded emote on raw turns strictly before target. Temporal eligibility only; actor visibility/timing remains unverified. |
| Strict-past self command | History channel, separately ablatable | Recorded raw command attempt only; not proof of successful behavior or state change. |
| Strict-past partner speech | History channel, separately ablatable | Recorded speech on strictly earlier raw turns. Do not infer that every item was delivered/visible at the target decision. |
| Strict-past partner emote | History channel, separately ablatable | Recorded emote on strictly earlier raw turns. Do not infer delivery/visibility beyond the source record. |
| Strict-past partner raw command | **Excluded from primary core.** In the explicitly named `plus_partner_raw_commands` diagnostic ablation, expose it as a separate channel only. | Observer-unverified surrogate. It is not the actual result message shown to the other participant; historical interaction code indicates physical action results were described from the world, while raw commands were not simply broadcast. Even strict-past placement does not make it observed by the target actor or a legal `O`. In core, mask partner command text but retain the original turn/group structure and role; do not drop an otherwise empty turn. This does not claim all potential observer-unverified structural information is removed, nor reconstruct actor observation. |
| Current-target speech, action, emote | Prohibited input | Same-turn co-recording does not establish pre-output availability. Target action is supervision only. |
| Any future turn/channel | Prohibited input | No future values in features, candidate construction, vocabulary fitting, or model selection. |
| Partner persona | Prohibited | Outside the proposed information boundary. |
| `all_descriptions` / global descriptions | Prohibited | Outside the candidate payload. |
| Independent metadata identity/split/index | Provenance only; prohibited as features | Includes episode/trajectory IDs, actor/speaker names as metadata, source refs, raw/physical indices, and split bucket. Keep these only for joins, audits, grouping, and reporting. Do not embed, hash, or derive model features from them. Persona, context, and dialogue text may themselves contain character names; those source-text contents remain, so identity/narrative leakage is not claimed to be eliminated. |

The parent channel decision for this draft is: core history contains strict-past self/partner speech and emote plus strict-past self command; partner raw command stays masked as described above. This is a source-record condition, not a legal-observation ruling. Exact timing, identity, visibility, and failure/settlement remain unresolved.

## Cohort, labels, support, and split

Retain the existing 13,463-row source-filtered cohort exactly. Do not add/remove rows based on diagnostic labels, label position, text overlap, inferred success, snapshot consistency, or model behavior. Report that this is a filtered cohort conditional on nonempty recorded physical command and upstream eligibility.

Keep source `recorded_action` as supervision, separate from all candidate inputs. Match using only `.strip().casefold()`: do not collapse internal whitespace or otherwise canonicalize. A row is scoreable only if its recorded command maps uniquely to one untouched recorded-support entry under this rule. Missing targets, empty/bad support, and normalized ambiguous matches get separate counts and no manufactured target index. Preserve `recorded_support` exactly; do not inject a gold command, deduplicate case variants, combine ambiguous items, or silently canonicalize the source. Label semantics remain command-attempt semantics.

Use the frozen whole-episode SHA-256 split: `int(SHA256(trajectory_id UTF-8).hexdigest()[:8], 16) % 10`; buckets `<7` train, `7–8` validation, `9` excluded. Preserve expected counts of 9,530 train, 2,717 validation, and 1,216 bucket-9 excluded, subject to exact source/hash reproduction. Bucket 9 is not a test set and is neither trained nor scored. No row-level random split or split tuning.

## Comparisons and objective

The two estimands are not interchangeable. `gru_core` and `pooled_core` share input features, candidate scorer/head, eligible rows, objective, optimizer, training budget, split, and checkpoint rule. They are **not parameter-count matched**; report actual trainable parameters and make no equal-capacity claim. `context_only` estimates the reference for the history-relative-to-context comparison: it retains the same persona and current recorded context as core, but uses zero history state. It is a current-record condition, not a strong history baseline. `gru_no_context` diagnoses reliance on recorded context, without resolving its timing gate.

Deep Sets (Zaheer et al., [arXiv:1703.06114v3](https://arxiv.org/html/1703.06114v3), §2.2/Theorem 2 and §3.1) motivates per-element transformation, sum pooling, and a readout for permutation-invariant set inputs. Only this mechanism and theorem boundary were checked for this protocol; it is not a full-paper reading or task reproduction, and its universal-representation theorem is not claimed for these finite hashed features or this dataset.

Use row-wise candidate softmax and standard cross-entropy / conditional negative log-likelihood for uniquely matched recorded labels. Optimize by gradient-based training on train rows only; choose checkpoints using validation only. Report ranking metrics alongside NLL, with metrics computed on identical eligible rows per comparison. Do not tune on bucket 9 or on diagnostic subgroups.

The sequence condition preserves raw-turn order and groups co-recorded channels by turn without inventing within-turn ordering. Empty turns are retained. The following is the parent-frozen **training candidate specification**, for implementation and independent review; it does not grant training authorization.

### Required conditions and ablations

Primary core channels are fixed: prior self/partner speech and emote, plus prior self command; partner raw command is masked while its turn slot remains. Fit only this fixed condition set; do not launch separate fits for every individual channel:

1. `context_only`.
2. `last2_core`.
3. `pooled_core`.
4. `gru_core`.
5. `gru_no_context`.
6. `gru_no_dialogue`: mask all prior speech and emote while preserving each turn's role, position, and self command.
7. `gru_no_persona`.
8. `gru_plus_partner_raw_commands`: explicitly observer-unverified diagnostic only; the added partner raw command is never part of core and never treated as legal `O`.
9. `uniform`.

Conditions differ only by the named masks/addition. For `gru_no_context`, zero the context vector; for `gru_no_persona`, zero the persona vector. All otherwise permitted inputs and turn slots stay unchanged. No per-channel refitting beyond this fixed set. Ablation scores cannot retrospectively change cohort membership or justify a stronger observation claim.

### Frozen candidate feature and model specification

- Text features: signed BLAKE2b feature hashing over Unicode unigrams and adjacent bigrams, L2-normalized, following the old PredictionBaselineV1 feature algorithm but with separate channel slots. Null/empty text maps to a zero vector; presence masks distinguish nonempty text.
- Static input: persona 256 + recorded context 256 = 512 dimensions. Candidate text: 256 dimensions.
- Each history turn: speech 256 + command 128 + emote 64 + role one-hot 2 + three nonempty-text presence masks = 453 dimensions. Use role for self/partner. Preserve turns even when channels are masked or the turn becomes empty. Co-recorded channels occupy separate slots on one turn; do not invent an order among them.
- `gru_core`: standard PyTorch GRU, input 453, hidden 16, zero initial state. This is not an exact Cho implementation or reproduction.
- `pooled_core`: `φ = Linear(453,32) → tanh → Linear(32,32) → tanh`; sum all turn embeddings, concatenate `log1p(n_turns)`, then `ρ = Linear(33,16) → tanh`. Empty prefix has zero pooled sum and count zero, while `ρ` bias remains active.
- `last2_core`: concatenate the latest two 453-dimensional turns, left-zero-padding as needed; Linear 906→16 followed by tanh.
- Shared candidate scorer: concatenate static 512, state 16, candidate 256 (784 total); Linear 784→32 → tanh → Linear 32→1. Static persona/context inputs are identical across conditions except `gru_no_persona`, which zeroes persona; `gru_no_context` zeroes context. `context_only` retains persona and context and uses zero history state. `uniform` assigns equal probability to every recorded support candidate.
- Objective/training candidate: row-wise candidate softmax cross-entropy / NLL; CPU, one thread, deterministic settings, seeds 7/19/31; Adam learning rate 0.001, no weight decay/scheduler/dropout, batch size 32, 15 epochs. Select the epoch with lowest mean validation NLL, earliest epoch on ties. These settings reuse the old baseline defaults to limit search; they are not asserted optimal. Report actual parameter counts. This specification is frozen for implementation review; training remains unauthorized.

## Reporting, uncertainty, and cost

For every split report source rows, episodes, actor trajectories, unique/ambiguous/missing support targets, empty/bad support, scored rows, and counts by split bucket. Include channel availability/missingness and strict-past history depth by role and channel. Distinguish event counts from unique event counts when one history event appears in multiple target prefixes.

Report NLL, top-1 accuracy, and MRR with all metrics using the same eligible-row denominator. For ties, use stable original candidate-list order; candidate position is not a model feature. Report both primary paired comparisons and every seed separately. For uncertainty, average each row's losses over seeds first, then compute paired condition differences with an episode-cluster bootstrap: 2,000 draws, seed 104729. Also report per-seed differences. These are post-selection development intervals, not generalization intervals. Predeclare strata by prior raw-turn group depth 1–4, 5–8, and ≥9. This is **prior group depth**, not physical-history depth. Do not use the legacy `exact_previous_pair` flag: it is absent from the new source view and does not justify expanding the source join. Do not change strata based on results. Include row/episode counts and mark sparse/unstable strata. Do not imply long-run behavior from a short physical-history window.

Record actual trainable parameter counts, wall-clock training and inference time, process peak RSS where available, runtime/library versions, device, and artifact sizes. Cost claims must be measured on the same inputs and hardware conditions; a compact latent vector or fewer parameters alone is not evidence of runtime efficiency. Do not claim deployment, closed-loop performance, or runtime-policy training.

## Artifacts, provenance, and no-overwrite

This folder owns the protocol and, after separate authorization, the implementation-facing schema contract and experiment README. It does not own upstream source data, the old baseline protocol/results, or canonical research-wide conclusions. Source rows, labels, support, raw materials, and prior fitted artifacts remain immutable.

Any future run must write to a new, exclusive output directory under an explicitly named run root. Existing output paths are errors; never reuse, overwrite, or append into a prior run. Snapshot and hash the exact protocol, implementation, input source, and configuration used. Record source and builder hashes, cohort/split digests and episode identifiers in a provenance manifest; keep metadata/provenance out of model tensors. Preserve raw predictions/losses, checkpoint selection evidence, logs, environment versions, uncertainty computation, and negative results. A run is not reproducible from a summary table alone.

Do not alter PredictionBaselineV1 protocols, snapshots, checkpoints, results, or historical run directories to fit this comparison. Training remains unauthorized. The source-record candidate builder is a structural artifact, not itself an actor-observation contract. Projection implementation evidence and acceptance are maintained in `INPUT_REVIEW.md`; this protocol cannot establish their status.

## Stop criterion and next action

After projection/schema acceptance and separately authorized training, if history is not stable relative to `context_only`, or `gru_core` is not stable relative to `pooled_core`, make no claim that sequence order is necessary in this view; do not tune repeatedly to chase a gain. Assess stability from paired ΔNLL and per-seed results under the frozen analysis. A development gain does not upgrade Paper-0 admission. No practical-significance epsilon is set here; without one, make no practical non-inferiority claim. If the schema/temporal noninterference contract or provenance fails, stop and do not fit.

**Next:** before training, the input projection and trainer synthetic contract must pass independent implementation review; current progress is recorded in `INPUT_REVIEW.md`.
