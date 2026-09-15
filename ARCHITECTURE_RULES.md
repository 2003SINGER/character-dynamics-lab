# Architecture rules｜anti-patch-debt

These are guardrails for an AI-heavy research prototype. They are deliberately small; do not turn them into a framework.

## Runtime and experiment boundaries

1. Scheduler-native runtime uses one authoritative simulation clock and incremental dataflow: persistent `W/O/S/P/RunningAction` nodes receive `Delta-t`, WorldEvent/Outcome, Delta-O, X, and DecisionGate deltas. Reference v0 is explicitly exempt. In scheduler-native code, actions never advance the clock; W mirrors it only through `WorldRuntimeAdapter`; no hidden W event may open a character gate; and fixtures must call the canonical bridge rather than hand-writing timestamps or duplicating dataflow.
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
13. Provenance is field-level: one step may contain observed `source_O`, observed `A*`, annotated state, and inferred `W` simultaneously. Keep `field_provenance[field].kind` plus source/model details.
14. `candidate_set_factual` and `candidate_set_expanded` are distinct; expanded candidates are diagnostic interventions, not observed facts.
15. Any data used to change S fields, update rules, utilities, timing, action ontology, or keep/delete decisions is `dev` thereafter.
16. Untouched test data must remain untouched after the mechanism is frozen.
17. Experiment metadata should record git revision, dataset/source revision, split definition, role, and purpose.

## Semantic-stage preservation

18. Preserve the research chain `ΔO/O/S/P → semantic interpretation X → explicit updater U → S' → π(A)` even when the current implementation is rule-based.
19. `X` is an inspectable intermediate product; do not permanently fold semantic interpretation into `event → numeric StateDelta`.
20. A future LLM or hybrid semantic frontend may replace the rule placeholder without changing the `U`/`S` boundary. Do not introduce a provider/factory framework just to reserve this hook.
21. A character-internal semantic frontend may read only legally available `O`, `ΔO`, `S`, and `P`; it must not read hidden `W` or future outcomes.
22. LLM semantics should emit structured `X`, not arbitrary direct writes to `S`; this keeps semantic errors separable from dynamics errors.
23. Semantic outputs must be traceable and replayable: model/version, prompt version, decoding config, input hash, structured output, and raw response/reference when available.
24. Keep rule-only, LLM-only, and hybrid semantic conditions independently switchable in future dev/test experiments.
25. During mechanism identification, dev data may guide changes to fields, updaters, utility, timing, or ontology. After freeze, test data must not guide those changes.
26. Generalization evaluations must separate frozen mechanism + fixed semantics, frozen mechanism + live LLM semantics, and LLM-direct/no-dynamics baselines.
27. If a semantic LLM replaces a hand-written rule, remove the redundant rule only after dev ablation/sensitivity evidence; do not retain duplicate mechanisms indefinitely for compatibility.
28. Stage 0/1 may use hand-written, AI-assisted semantic rules compiled into a versioned deterministic rule table; runtime experiments must not call an LLM in this stage.
29. Semantic rules may be revised from dev failures, but must be reusable causal/contextual hypotheses—not per-trajectory patches keyed to `A*` or future events.
30. Freeze the semantic rule table together with `X`, `S`, `U`, utility, parameters, and timing before testing generalization.
31. Only after freeze may a live LLM replace the fixed semantic frontend; keep dynamics identical so the semantic substitution is the tested variable.
32. The future minimum comparison is `fixed semantics + frozen dynamics` vs `LLM semantics + same frozen dynamics`, plus `LLM-direct/no-dynamics` and literature baselines.

## Scope control

33. Define one small public ReplayRecord contract; do not build `IAdapter`, factories, registries, plugin managers, or dependency injection.
34. Do not create one independent experiment universe per dataset.
35. Apply the Rule of Three: only extract a shared helper after the same logic appears three times.
36. Do not add a field because it sounds psychological. Add it only with a stated input, updater, consumer, ablation, and evidence need.
37. Do not add a parameter merely to fit one episode.
38. Do not expand `simulation.cpp` with new datasets or measurements.
39. Do not split files solely to make them look clean; split when ownership or reuse is real.

### Research semantic ownership (2026-09-07)

40. `02_实验/Theory_S_v2/` is the canonical Python research dynamics candidate; `Replay/` owns source-neutral records, canonical action features, and baseline probes. Dataset adapters may emit ReplayRecord/SceneSnapshot/X-compatible inputs, but must not copy or specialize Theory-S as `LIGHTTheoryS`, `OperaTheoryS`, or similar.
41. `Mechanism_Sanity_v1` and `v1_2` are frozen historical engineering fixtures. New development training composes the canonical operator and feature layer; it does not create another X→S→π implementation.

## Tests and guards

42. CTest and `--verify` remain regression gates for the existing reference runtime.
43. Schema/provenance validators may fail on invalid records; size, duplication, and complexity checks warn only.
44. A warning is not evidence that a mechanism is wrong; it is a prompt for review.
45. Every new adapter needs a small schema-validating dev slice before larger downloads or model comparisons.
46. Preserve negative results, raw outputs, configuration, and errors.
47. Adapter acceptance is two-stage: schema validation is necessary but not sufficient; a semantic audit must check W/O/X/S ownership, causal availability, action meaning, and provenance.
48. First adapter slices (roughly 20–50 trajectories) receive near-complete semantic review before scaling. Later batches use stratified sampling plus mandatory review of anomalies, new ontology values, low-confidence/unknown-heavy records, and validator edge cases.
49. The extraction script may be deterministic while semantic annotations are human/AI-assisted; after review, annotations are saved as versioned frozen data and runtime experiments do not call the reviewing model.
50. Semantic QA must record what the source says, what the transformation adds or loses, which fields are inferred, and whether any future information was used.

## Documentation and review

51. TODO contains IDs, status, next action, completion condition, and links—not full literature arguments.
52. Raw dialogue is archived when it contains user decisions, original reasoning, or provenance-critical review; routine bug reviews need only commit/issue/decision/follow-up.
53. Record architecture audits at milestone triggers in `00_研究设计/architecture_audit_policy.md`.
54. Before a milestone handoff, independently reread the actual diff for duplicated pipelines, hidden side channels, schema drift, provenance loss, dev/test contamination, dead helpers, and document duplication.

## Current known baseline

- Anti-patch-debt baseline: `webgpt-sync@685c319`.
- `Demo codex-generated/Src/simulation.cpp` is about 58 KB and currently owns runtime orchestration, batch, CSV, verify, E0, and profile runs. This is known debt; this rule does not authorize a large refactor now.
- Typed `FactKey` coverage is partial. New adapters must not inject dataset-specific string keys into runtime `Observation`.
