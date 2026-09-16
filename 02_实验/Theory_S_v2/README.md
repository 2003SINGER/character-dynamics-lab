# ExpectedEffectEMAProxyV0 (historical display name: Theory-S v2)

> Historical proxy identity. This module is not the current ResearchDynamicsV1
> and must not be described as validated character dynamics.

This is a gradient-formalization consolidation, not a new topology research
question. It joins per-field state dynamics from the mechanism design,
v1/v1.2 fatigue–engagement–tension transition plumbing, and the T14/T20
conditional-linear readout (`z = theta*f + S*W*f`). It is not a fitted model or
psychological validation.

## Contract

For each state field independently:

`target_t = sigmoid(b + beta X_t)`

`S_t = alpha * S_(t-1) + (1-alpha) * target_t`, with `alpha=sigmoid(alpha_raw)`.

This is bounded first-order target relaxation: repeated cues can accumulate,
cue removal leaves residual state that decays, and a neutral event returns
toward a field-specific baseline. There is no free 3×3 recurrent state matrix.
`fatigue`, `engagement` (broad behavioral involvement, not valence), and
`tension` remain candidate project definitions; predictive validity is
unverified. The six X fields are a compatibility input schema, not a claim that
the literature supplies one canonical six-dimensional appraisal model.

The action side directly reuses `Replay/replay_features_v1.py::FEATURE_NAMES`
(13 dimensions):

`z_t(a) = theta^T f_t(a) + S_t^T W f_t(a)`.

In the implementation the state term is centered as `S_t - sigmoid(b)`. A
field at its own neutral equilibrium therefore contributes zero state
modulation and cannot silently re-fit a static action preference already owned
by `theta`.

State identity is protected only by a small soft semantic prior: effort and
recovery anchor fatigue, negative and recovery anchor tension, and goal,
positive, and social cues anchor engagement. Uncertain edges remain free. This
is regularization metadata, not a hard topology or a claim that the literature
dictates a sparse matrix; its weight is chosen only by a future protocol via
`semantic_anchor_loss`. Its default `margin=0.0` is violation-only; any
positive margin must be passed explicitly as a development fixture and cannot
be inferred as a scientific effect-size requirement.

Candidate sets and support are upstream. The module receives O/P-derived
candidate feature vectors and never reads source candidates or A*. P remains
fixed in Paper-0; it enters through the stable/base preference interface and is
not given a new network in this slice.

## Training protocol (documented, not run)

Phase A fits only `theta` with conditional multinomial next-action NLL on each
candidate set (`z_base = theta^T f`). Phase B freezes `theta` and fits `b`,
`beta`, `alpha`, and `W` through the unrolled recurrence with the same
candidate-set NLL. This is the multi-dimensional, end-to-end continuation of
the earlier frozen-`theta_0` Run2 probe. Current-A* is revealed only after
`X_t = Appraise(O_(t-1), A_(t-1), O_t)`, `S_t`, and policy logits are formed.
Any semantic-anchor weight must be pre-registered on development data; the
smoke uses `0.05` only as a regression fixture, not as a scientific setting.

The synthetic smoke is only a regression: 10 time steps, four candidates per
decision, multinomial NLL, multi-step backpropagation, Phase-B theta freezing,
state bounds, b-gradient, and a short optimizer decrease. Tests additionally
cover Phase-A theta-only updates, gold-boundary separation, and trajectory
reset. It is not development training.

## Constraints and controls

There is no hard sparse signed topology in the core model. Edge priors remain
project uncertainty and may later be metadata, soft priors, or an attribution
ablation. A row-permuted state plumbing diagnostic is intentionally not used as
a theory control. The meaningful future control is the existing trajectory-
permuted-S evaluation (fixed weights, no-self donor); generic/naive-S remains a
future T20 attribution comparison.

Run the regression with:

```powershell
py -m unittest discover -s 02_实验/Theory_S_v2 -p 'test_*.py'
py 02_实验/Theory_S_v2/theory_s_v2.py
```
