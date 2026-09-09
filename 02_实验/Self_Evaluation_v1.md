# Self-Evaluation v1 (frozen protocol)

The evaluator emits mechanism vectors, hard gates, and descriptive telemetry;
it never emits a total naturalness or believability score.

## Categories

- **HARD_GATE** — a violation invalidates a candidate.
- **OPTIMIZER_ELIGIBLE** — only an audited, directionally interpretable metric may enter development selection.
- **TELEMETRY_ONLY** — report for diagnosis; do not optimize directly.
- **NOT_SCORED** — no evidence in this repository.

| metric | estimand / formula | source | direction | category | cannot claim |
|---|---|---|---|---|---|
| world integrity | parse, support, probability, time, effort and task-status violations | batch `trajectories.csv` | zero violations | HARD_GATE | psychological validity |
| phone information integrity | hidden/visible retention, typed absent probe, correction and affordance revocation | phone fixture | all gates pass | HARD_GATE | phone realism |
| deadline state dynamics | pre-discovery TV, X contribution, pressure/study gap, post-discovery trajectory | `paired_deadline.csv` | gates pass; persistence descriptive | HARD_GATE + TELEMETRY_ONLY | deadline psychology |
| commitment/recovery | Active→Suspended→Active, preserved/ablated equality and policy TV, completion boundary | commitment `trace.csv` | gates pass | HARD_GATE | intention or agency |
| action diversity | entropy, dominant share, repeats and run lengths | batch | descriptive | TELEMETRY_ONLY | more diversity is better |
| differentiation | per-personality distributions and pairwise JS | batch | descriptive | TELEMETRY_ONLY | difference is quality |
| event reactivity | action-change rate after an event | batch | descriptive | TELEMETRY_ONLY | causal estimate |
| efficiency | decisions, calls, calls/decision, runtime, decisions/sec | runner metadata | descriptive | TELEMETRY_ONLY | zero calls is quality |

Believability, external naturalness, psychological validity, and Theory-S
validity are **NOT_SCORED**. `SELF_EVALUATION_V1 = FROZEN`; the fresh train and
holdout regressions pass all hard gates. This still does not establish
psychological or external validity.
