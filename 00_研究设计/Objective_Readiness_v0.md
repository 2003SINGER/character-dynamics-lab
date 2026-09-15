# Objective Readiness v0

## Decision

`OBJECTIVE_READINESS = NOT_READY`.

The current evaluator can invalidate broken candidates and expose descriptive
telemetry, but it cannot justify a quality ordering among valid candidates.
Entropy, JS differentiation, event reactivity, persistence duration, and
efficiency are telemetry-only; maximizing any of them would encode an
unsupported preference. The current optimizer therefore correctly reports
`BASELINE_RETAINED / NO_SELECTION`.

## What is already usable

- world/information/commitment hard gates;
- deterministic parameter sensitivity and trajectory-difference audits;
- explicit pathological-run telemetry;
- frozen train/holdout separation and one-shot holdout firewall.

## Next evidence layer

Before proposing an engineering pathology objective, inspect the frozen
`optimizer_train` trajectories to find actual failure modes. The development
casebook may use descriptive screeners (repetition, zero-duration actions,
unmet-need exposure, task-pressure / study mismatch, task stagnation, and
commitment suspension) to select traces for review; these screeners are not
penalties, thresholds, or a candidate ranking.

The first casebook is generated locally at
`outputs/behavior_audit_casebook_v0/` from the baseline train batch only. It
contains 52 complete trajectories and explicitly does not read holdout. Early
review already rejects two shortcuts: a long action repeat can be contextual
and harmless when time advances and needs are low, while a repeated zero-minute
action loop can stall simulated time and is a plausible engineering defect.
The current batch does not expose `deadline_remaining`, so task pressure must
not be mislabeled as deadline non-response.

Only after reviewers label development cases as true/false positives/negatives
should candidate metrics be written, attacked with contextual counterexamples,
and frozen as Objective v0. Only then may a candidate ordering be enabled.

Human or LLM-assisted coherence/believability judgments and independent A*
candidate-set NLL remain separate later evidence layers; neither is activated
here, and no LIGHT workaround chain is reopened.
