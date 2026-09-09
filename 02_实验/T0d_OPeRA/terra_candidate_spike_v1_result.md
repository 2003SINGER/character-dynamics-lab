# T0d｜OPeRA Terra candidate spike v1 result

结果日期：2026-09-08  
Protocol：[v1 frozen protocol](terra_candidate_spike_v1_protocol.md)

## Result

The one allowed follow-up was completed on a fresh 30-step blind fixture. Terra
was forced to bind every candidate to one concrete raw-element identity; it
could not merge distinct elements or emit an unbound abstract action.

| metric | result |
|---|---:|
| records / candidates | 30 / 30 |
| candidate count per record | exactly 1 |
| exact identity matches | 10/30 |
| identity-mismatch semantic family matches | 11/30 |
| ambiguous | 0/30 |
| misses | 9/30 |
| strict support recall | **10/30 = 33.3%** |
| family-only diagnostic support | 21/30 = 70.0% (not strict) |
| duplicate target identity | 0 |
| no-candidate | 0 |

Gold-blind/prohibited-key invariants passed, every emitted `target_source_index`
resolved to the frozen raw input, and the candidate artifact hash was stable on
repeat reads. No Terra regeneration was performed, so this is artifact stability,
not a rerun-equivalence claim.

## Validity correction

The v1 artifact emitted exactly one candidate per record (30 records / 30
candidates). The measured 10/30 figure is therefore **single-target identity
selection accuracy**, not candidate-set support recall. It cannot close the
broader `O_t → Ahat^O_t` question with a bounded 5–10 element set.

## Frozen stopping decision for the v1 task

The pre-registered conditional pass required strict support ≥70% **and**
ambiguous gold matches ≤25%. Ambiguity passed (0%), but strict support failed
(33.3%). Therefore the **v1 single-target task** is **FAIL/CLOSE**. OPeRA
remains a coarse click-type/history auxiliary for now. The multi-candidate
route is **UNRESOLVED**, not closed: a separately frozen 5–10 candidate
identity-preserving fixture would be a different experiment. No action-readout
compatibility discussion or Theory-S training is authorized before that routing
decision.

The result is informative: v1 removed the v0 ambiguity failure, but target
identity selection remains too inaccurate (11 family-only mismatches and 9
misses). This is not evidence that Terra cannot summarize pages; it is evidence
that this single-target spike does not provide reliable identity-preserving
next-action selection. It does not test whether a bounded multi-candidate set
can preserve support.

Machine artifacts are Git-ignored under
`outputs/opera_t0d_2026-09-08/terra_candidate_spike_v1/`.
