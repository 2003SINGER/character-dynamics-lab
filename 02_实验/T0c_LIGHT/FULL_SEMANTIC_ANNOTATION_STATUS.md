# Full LIGHT semantic annotation status

## Current checkpoint — 2026-09-07

- Reviewer: Terra, source-only model annotation (not human review).
- Input cohort: 24,999 non-quarantine mechanism-dev action rows.
- Completed: 6,800 rows, shards `0001`–`0136`.
- Resume point: `shard-0137.jsonl`, offset `0`.
- Validator: 6,800 unique output IDs match 6,800 input IDs; no missing or extra IDs in the completed prefix.
- Current labels (descriptive only; do not treat as admission result): ADMIT 5,805; REJECT 993; AMBIGUOUS 2.

## Boundary

The reviewer receives only current-step source evidence (`actor`, `source_O`,
`source_action_A_star`, `candidate_set_factual`) plus deterministic structural
checks. It must not consume prior/future steps, Run1–4 output, older reviewer
results, or the earlier blind-50 diagnostic. The external asset payload and
checkpoint remain Git-ignored; use the local paths documented in the full
annotation protocol to review them.

## Review request

Assess whether the shard generator, source-only boundary, JSONL schema,
checkpoint/resume behavior, and validation rule are adequate before resuming
from shard 0137. This is a development model-assisted annotation pipeline; it
must not be described as a human semantic audit.
