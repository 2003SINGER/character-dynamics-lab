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

The next mainline should be an engineering pathology objective, before any
naturalness score: define and preregister bounded penalties for infinite
repetition, unattended hunger/bathroom needs, deadline non-response, and task
completion failure. Validate thresholds on controlled development cases and
negative cases. Only after that should a candidate ordering be enabled.

Human or LLM-assisted coherence/believability judgments and independent A*
candidate-set NLL remain separate later evidence layers; neither is activated
here, and no LIGHT workaround chain is reopened.
