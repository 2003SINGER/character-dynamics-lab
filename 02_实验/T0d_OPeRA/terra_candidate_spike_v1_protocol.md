# T0d｜OPeRA Terra candidate spike v1 protocol (pre-registered)

核查日期：2026-09-08（结果 reveal 前冻结）

## Purpose

This is the **one allowed follow-up** to v0. It tests only whether preserving
raw-element identity fixes v0's ambiguity failure. It does not modify the
frozen OPeRA pilot protocol, Theory-S, action features, or training state.

## Generator contract

Input is a fresh deterministic 30-step fixture (10 SHA-256-ranked eligible
sessions, ranks 11–20; steps first / middle / penultimate). Terra may select,
rank, or describe raw interactables, but every emitted candidate must contain:

```text
action: click|type|select|submit|open|navigate (or the observed page-control verb)
target_source_index: one concrete index from the raw interactive-element list
target_text: copied/normalized text or attribute from that exact raw element
reason: short semantic justification
ambiguity: true only if the exact target remains unresolved; never merge distinct
raw elements into one candidate
```

Multiple candidates may be semantically similar, but each remains separately
bound to its own `target_source_index`. No free-form candidate may be emitted
without raw-element provenance. Current gold fields remain prohibited until the
evaluator stage.

## Evaluator and stopping rule (frozen before reveal)

Strict support requires both: (1) the candidate's bound raw-element identity
matches the controlled gold target identity, and (2) the candidate is not
`ambiguity=true`. Intent-family coverage without target identity is not strict
support. The evaluator reports exact, identity-mismatch/semantic, ambiguous,
miss, candidate count, duplicate identity, no-candidate, and invariant checks.

After this v1 fixture, the route is hard-stopped:

- **Conditional pass:** strict support ≥ 70% and ambiguous gold matches ≤ 25%;
  only then may a separate design discussion consider action-readout
  compatibility.
- **Fail/close:** otherwise OPeRA candidate reconstruction is closed. OPeRA
  remains coarse click-type/history auxiliary only, and no v2/v3 prompt repair
  or Theory-S training is allowed under this route.

The thresholds and fresh fixture are fixed before Terra generation and cannot be
changed after seeing evaluator results.
