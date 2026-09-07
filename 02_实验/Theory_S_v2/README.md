# Theory-S v2：literature-constrained trainable slice

This directory freezes the next engineering contract after the v1/v1.2
mechanism sanity checks. It is a dataset-neutral trainable module, not a
psychological validation or a formal experiment.

## Contract

\[
S_{t+1}=g(\alpha\odot S_t+(M_{XS}\odot W_{XS})X_t),\qquad
z(a)=z_{base}(O,P,a)+S_{t+1}^T(M_{SA}\odot W_{SA})f(a).
\]

`X` has six fields: effort load, goal relevance, positive conduciveness,
negative conduciveness, social opportunity, and recovery cue. `S` has three
fields: fatigue, engagement (broad behavioral involvement, not mere
pleasure), and tension. `g=sigmoid` bounds the state. Fixed topology and signs
are explicit hypotheses in `theory_s_v2.py`; magnitudes are trainable through
signed softplus parameters and `alpha` is trainable through sigmoid logits.

The module receives an explicit action-feature basis (`stimulation`, `social`,
`conflict`, `recovery`) and `z_base`. It does not read source candidates,
`A*`, action IDs, or labels; candidate generation/support remains upstream.

## Permuted-S control

`permuted_s()` permutes state rows while preserving X/action dimensions,
non-zero edge count, parameter count, bounded persistence, and training
protocol. It is therefore an equal-capacity topology control rather than a
smaller baseline.

## Verification

`synthetic_gradient_smoke()` is a gradient-path smoke only. It checks bounded
states, fixed signs/masks, equal parameter capacity, and non-zero gradients
through `loss → W_SA → S → W_XS/alpha`. It uses synthetic tensors and is not a
training result. Run:

```powershell
py -m unittest discover -s 02_实验/Theory_S_v2 -p 'test_*.py'
py 02_实验/Theory_S_v2/theory_s_v2.py
```

The intended future two-stage protocol is: (1) fit `z_base` and transition
parameters on a train split with frozen topology; (2) evaluate on trajectory /
episode-disjoint validation and test splits with raw history, structured
history, summary, theory-S, naive-S, and Permuted-S under matched capacity.
No stage-2 formal training is run in this commit.
