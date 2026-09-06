# First real external replay v0

The one-room implementation is a demo/reference scene only. It may legitimately
collapse some mechanism slots to no-op. External experiments do not inherit the
room's `ActionType` ontology.

Runnable chain after batches 3A–5:

`ReplayRecord`
→ fixed compiled semantics
→ inspectable `X`
→ explicit `U`
→ persistent `S`
→ dataset-native candidate scorer
→ `pi(A)`
→ held-out human `A*`
→ NLL / rank

LIGHT's source `available_actions` remains `candidate_set_factual`; this document
does **not** claim it is the character's subjective `A^O`.

The stateful dev diagnostic is teacher-forced only from past human actions:
at prediction step `t`, `A*_t` is not used to construct `S_t` or its own candidate
features. It is revealed only for scoring.

Conditions:
- stateful past-action semantics;
- no-history state;
- uniform candidate baseline.

The counterfactual runner additionally removes exactly one previous action update
while holding the source trajectory, initial state, semantic rules, scorer, and all
other history fixed. It emits `Delta-S`, `Delta-p(A*)`, and `Delta-NLL`.

This is still a development/smoke stage, not a Paper-0 conclusion. Negative or flat
effects must be preserved.
