# Architecture rules｜anti-patch-debt

These are guardrails for an AI-heavy research prototype. They are deliberately small; do not turn them into a framework.

## Runtime and experiment boundaries

1. Keep one canonical semantic path for `O refresh → X/appraisal → S update → π/action decision → settlement`.
2. Replay and experiments should call the runtime path or explicitly document every intentional difference and its semantic risk.
3. `Simulation::verify()` is for invariants and regression checks. `Simulation::run_e0()` is for the fixed E0 control fixtures. Do not put cross-dataset experiments, adapters, or baselines there.
4. Do not change runtime behavior under the pretext of repository cleanup.
5. Keep `prepare_decision` and `settle_action` local until a real replay use case requires a cross-file API.

## Data and provenance

6. Every external dataset adapter maps `raw source → dataset parser → ReplayRecord v0`.
7. Adapters may differ internally; only the output contract is shared.
8. Preserve raw fields. Never overwrite source data with a normalized or LLM-derived value.
9. Missing `W`, `O`, persona, state, or candidate sets remain `unknown`/missing.
10. Allowed provenance labels are `observed`, `annotated`, `llm_inferred`, `synthetic_diagnostic`, and `unknown`.
11. LLM output must retain source reference, model, prompt version, and confidence/uncertainty when available.
12. `llm_inferred` content cannot be relabelled as human ground truth.
13. `candidate_set_factual` and `candidate_set_expanded` are distinct; expanded candidates are diagnostic interventions, not observed facts.
14. Any data used to change S fields, update rules, utilities, timing, action ontology, or keep/delete decisions is `dev` thereafter.
15. Untouched test data must remain untouched after the mechanism is frozen.
16. Experiment metadata should record git revision, dataset/source revision, split definition, role, and purpose.

## Scope control

17. Define one small public ReplayRecord contract; do not build `IAdapter`, factories, registries, plugin managers, or dependency injection.
18. Do not create one independent experiment universe per dataset.
19. Apply the Rule of Three: only extract a shared helper after the same logic appears three times.
20. Do not add a field because it sounds psychological. Add it only with a stated input, updater, consumer, ablation, and evidence need.
21. Do not add a parameter merely to fit one episode.
22. Do not expand `simulation.cpp` with new datasets or measurements.
23. Do not split files solely to make them look clean; split when ownership or reuse is real.

## Tests and guards

24. CTest and `--verify` remain regression gates for the existing reference runtime.
25. Schema/provenance validators may fail on invalid records; size, duplication, and complexity checks warn only.
26. A warning is not evidence that a mechanism is wrong; it is a prompt for review.
27. Every new adapter needs a small schema-validating dev slice before larger downloads or model comparisons.
28. Preserve negative results, raw outputs, configuration, and errors.

## Documentation and review

29. TODO contains IDs, status, next action, completion condition, and links—not full literature arguments.
30. Raw dialogue is archived when it contains user decisions, original reasoning, or provenance-critical review; routine bug reviews need only commit/issue/decision/follow-up.
31. Record architecture audits at milestone triggers in `00_研究设计/architecture_audit_policy.md`.
32. Before a milestone handoff, independently reread the actual diff for duplicated pipelines, hidden side channels, schema drift, provenance loss, dev/test contamination, dead helpers, and document duplication.

## Current known baseline

- Anti-patch-debt baseline: `webgpt-sync@685c319`.
- `Demo codex-generated/Src/simulation.cpp` is about 58 KB and currently owns runtime orchestration, batch, CSV, verify, E0, and profile runs. This is known debt; this rule does not authorize a large refactor now.
- Typed `FactKey` coverage is partial. New adapters must not inject dataset-specific string keys into runtime `Observation`.
