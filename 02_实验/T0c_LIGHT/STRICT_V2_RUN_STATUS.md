# Strict v2 fresh-session run status

This is the admissible v2 run candidate. Each completed task was handled by a
separate fresh Terra reviewer session; no session processed more than one task.
The older v1 6,800-row prefix and v2 persistent-session 400-row prefix remain
diagnostics and are not merged here.

## Checkpoint — 2026-09-07 (fresh-session strict run)

- Completed: `task-0001.jsonl`–`task-0040.jsonl`
- Rows: 800 / 24,999
- Next task: `task-0041.jsonl`
- Validation: passed strict v2 schema, exact task order, opaque IDs, and one trajectory per reviewer task.
- Labels: ADMIT 522; AMBIGUOUS 249; REJECT 29.
- Output is model-assisted source semantic annotation, not human audit or final admission mask.

The private opaque-ID mapping and reviewer input shards remain Git-ignored.
