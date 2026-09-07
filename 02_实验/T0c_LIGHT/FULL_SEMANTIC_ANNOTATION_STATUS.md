# Full LIGHT semantic annotation status

## Current checkpoint — 2026-09-07 (frozen; NO-GO)

- Reviewer: Terra, source-only model annotation (not human review).
- Input cohort: 24,999 non-quarantine mechanism-dev action rows.
- Completed diagnostic prefix: 6,800 rows, shards `0001`–`0136`.
- Frozen resume point: `shard-0137.jsonl`, offset `0`. Do not resume this run.
- Validator: 6,800 unique output IDs match 6,800 input IDs; no missing or extra IDs in the completed prefix.
- Current labels (diagnostic only; never treat as an admission result): ADMIT 5,805; REJECT 993; AMBIGUOUS 2.

## Boundary

The reviewer payload nominally contains only current-step source evidence
(`actor`, `source_O`, `source_action_A_star`, `candidate_set_factual`) plus
deterministic structural checks. However, v1 shards expose trajectory and
step identifiers and may contain multiple rows from a trajectory in one task;
therefore the completed prefix does **not** satisfy a strict current-step
source-only blindness boundary. The rubric also did not operationally define
when insufficient evidence must become `AMBIGUOUS` rather than `REJECT`.
The prefix is retained as a failed-protocol diagnostic, not an admission mask.

## Review request

Before a v2 restart, use opaque reviewer IDs, expose no trajectory/time
metadata, ensure at most one row per trajectory in a reviewer-visible task,
define executable label and reason-code rules, and validate strict shard
completion/checkpoint provenance. This remains development model-assisted
annotation and must not be described as a human semantic audit.

## V2 smoke and containment correction

The v2 calibration smoke uses 60 globally trajectory-distinct rows in three
20-row tasks, opaque IDs, and only the five allowed reviewer fields. It passed
strict schema validation and demonstrated use of `AMBIGUOUS` under the revised
rubric (13 ADMIT / 47 AMBIGUOUS / 0 REJECT).

An attempted v2 full prefix of 400 rows is retained only as a diagnostic. The
input files are task-isolated, but one persistent Terra session processed
multiple tasks, so it could retain evidence from earlier tasks and encounter a
trajectory again later in the same session. It is therefore not an admissible
strict current-step run. A full strict v2 run requires one fresh reviewer
session per task (or another mechanism that makes model context nonpersistent),
not merely one trajectory per JSONL file.
