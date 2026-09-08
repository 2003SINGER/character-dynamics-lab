# ClubFloyd Source-Command Development Protocol v0

> Boundary correction: this protocol is superseded on admission semantics by `command_admission_definition_v1.md`. ClubFloyd `[ACTION]` is observed `A*`; Stage A does not require objective `A^W` legality and does not claim source `A^O`.

冻结日期：2026-09-08  
状态：**development protocol only；未训练、未进入 Theory-S mechanism loop**

## Goal and estimand

Stage A evaluates:

```text
same-transcript pre-action state + past source states/actions
    → observed next player command
```

This is an open-text source-command task. It is not yet a finite-candidate
`A^O` NLL task, and it does not claim that ClubFloyd supplies complete `O/X/S/P`
or a legal candidate set.

## 1. Usable action subset: `verified_command_like_v0`

The full extraction has 425 trajectories / 438,188 steps. Existing mechanical
counts are 218,575 `command-like`, 219,524 `ambiguous`, 47
`chat/commentary-like`, and 42 `meta-command`. v0 does **not** silently promote
all `command-like` rows to ground truth.

For the first development slice, `verified_command_like_v0` is the conjunction:

1. existing deterministic quality class is exactly `command-like`;
2. first token is in the frozen verb lexicon in `command_schema_v0.py`;
3. canonicalization status is `parsed`;
4. raw command, source file, and source step reference are retained.

`ambiguous`, chat/commentary, meta-command, unknown-verb, empty, and malformed
rows are excluded from the Stage-A target but retained in the audit inventory.
This is a deterministic source filter, not a semantic proof. A later semantic
review may split or reject it, but may not rewrite raw commands.

## 2. Canonicalization

Every retained action stores:

```text
raw_command
normalized_command
parse_confidence
verb
target
modifier
parse_status
quality_class
```

`raw_command` is immutable. The normalized schema is `verb + target + optional
modifier`; commands that do not fit remain `unparsed` rather than being forced
into the 16-action ontology. Semantic-match rules and any top-k retrieval pool
must be frozen separately before looking at evaluation results.

## 3. Prediction-time boundary

Allowed input at step `t`: current pre-action `[STATE]_t`, previous source
states/actions from the same transcript, and transcript/trajectory metadata that
exists before the action. Forbidden: current `A*_t`, next `[STATE]`, future
commands, or post-action text copied backward. The adapter's `[STATE] → [ACTION]`
pair is retained as the boundary; no LLM is used to manufacture `source_O` or
`source_action_A_star`.

## 4. Split and leakage checks

Splits are by complete transcript/game trajectory, never by step. The fixture
uses a deterministic SHA-256 trajectory assignment to train (70%), validation
(15%), and development holdout (15%). The manifest must report trajectory
disjointness and whether game/domain identities cross splits; cross-game
generalization is reported, not optimized in v0.

## 5. First metrics

Stage A reports only metrics with a defined open-text target:

- exact normalized-command accuracy;
- verb accuracy;
- target accuracy;
- frozen semantic-command match;
- optional top-k retrieval/ranking only if a candidate pool is constructed
  without current-gold leakage.

There is no canonical candidate-set NLL in v0. If no reliable probability space
can be frozen, the report must say so rather than inventing a denominator.

## 6. Minimal fixture and acceptance

`build_command_dev_slice_v0.py` builds a deterministic 30-trajectory review
fixture and writes a manifest with parser, split, and future-boundary checks. It
is a protocol smoke test, not a model run. Acceptance requires:

- non-empty verified-command slice;
- all three trajectory-disjoint split labels present where the fixture permits;
- no trajectory in more than one split;
- every retained record has raw and canonical action fields;
- `future_state_in_input_all_false = true`.

## Decision

ClubFloyd **can form a legal open-text next-action development task** after this
source filter and split protocol. The largest current blocker is not history
leakage; it is semantic action admission/canonicalization and an evaluation
metric for open text. It is therefore **not yet ready for Theory-S representation
comparison**. The old next-action note is superseded by corrected `A*` admission v1 and the completed multi-LLM adjudication; the current gate is
**GO_TO_REPRESENTATION_BASELINE**.
`verified_command_like_v0` fixture and freeze semantic-match rules. Do not begin
Theory-S parameter training from this document alone.
