# Native story-process fixed case table

Audit manifest: `02_实验/Mature_Methods_Integration_v1/runs/story-audit-manifest-20261012T151500Z-5c1a70/audit-manifest.json`
Explicit story-directory allowlist: 30 directories (including this manifest carrier).

| Case condition | Strategy | Scene | Run | Status / actual outcome |
|---|---|---|---|---|
| accepted-gtpyhop | gtpyhop | 20261012134847-eb06f1 | `story-accepted-gtpyhop-20261012T141710Z-f1fb7b` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| accepted-event-driven | event_driven | 20261012142011-381b55 | `story-accepted-event-driven-20261012T142011Z-bc9737` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| rejected-gtpyhop | gtpyhop | 20261012142107-90b886 | `story-rejected-gtpyhop-20261012T142107Z-7679dc` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| rejected-event-driven | event_driven | 20261012142134-b0d196 | `story-rejected-event-driven-20261012T142134Z-76c530` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| task-refusal-gtpyhop | gtpyhop | 20261012143735-f9b8ff | `story-task-refusal-gtpyhop-20261012T143735Z-7fac6a` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| task-refusal-event-driven | event_driven | 20261012143824-624c30 | `story-task-refusal-event-driven-20261012T143824Z-532788` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED; story-authorized-filer=SATISFIED |
| future-file-actor-edit | gtpyhop | 20261012151236-a53dcd | `story-future-file-actor-edit-20261012T151236Z-c1f420` | COMPLETE; v1 B offer invalidated by minute-18 CAS; v2 return-A selected; v1 stale ID persisted in trace and DB; no v1 task decision; goal SATISFIED |
| process-control | gtpyhop | 20261012143950-e6c315 | `story-process-control-20261012T143950Z-0aa86f` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED |
| direct-control | gtpyhop | 20261012144011-f867f5 | `story-direct-control-20261012T144011Z-0bef02` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED |
| locked-fragment | gtpyhop | 20261012144034-03df60 | `story-locked-fragment-20261012T150904Z-6cf8ad` | COMPLETE; story-note-archive-by-deadline=SATISFIED; story-response-before-archive=SATISFIED; story-note-handover-at-most-once=SATISFIED |
| no-task-authority | gtpyhop | — | `story-no-task-authority-20261012T144208Z-5b0286` | EXPECTED_RESET_REJECTION; INVALID_STORY_PROCESS_REQUEST; scene_created=false; missing A in grant; goal not evaluated |
| resource-held-by-player | gtpyhop | 20261012150924-91a985 | `story-resource-held-by-player-20261012T150924Z-ebd42a` | COMPLETE; SETTLED player get at minute 2; supply remains player-held at 24; A lacks resource; no native note bound; archive goal NOT_SATISFIED |
| absolute-deadline-negative | gtpyhop | 20261012150943-96dcb4 | `story-absolute-deadline-negative-20261012T150943Z-ad48bd` | COMPLETE; story-note-archive-by-deadline=VIOLATED; story-response-before-archive=VIOLATED; story-note-handover-at-most-once=SATISFIED |
| locked-refusal-abort | gtpyhop | 20261012151009-8696d2 | `story-locked-refusal-abort-20261012T151009Z-3c6e59` | COMPLETE; sealed LOCKED_ABORTED; exact holder-mismatch reason; core hash unchanged; zero task requests; goal VIOLATED; offline nested-shape audit PASS |

## Retained attempt and continuation accounting

- Unique case conditions: 14 (13 native scenes plus one precreate denial).
- Explicit `story-*` directories: 30; pre-manifest directories: 29.
- Non-complete/precreate attempt directories: 7; exact IDs in `preserved_failure_and_preflight_run_ids`.
- Accepted same-scene runner preflight failures: 4.
- Preserved GTP task-refusal failed attempts: 2.
- Same-scene continuation attempts: 5; completed continuations: 2.
- Lifecycle evidence directories: 7.
- The independent future-edit scene verifies stale-request telemetry after the metadata fix; it supplements rather than replaces the previous successful result with empty telemetry.
- Controller decisions, actually executed method callbacks, diagnostic-only alternative guards, native ledger/receipt counts, and wall time are separate. Wall time excludes service lifecycle; no performance ranking is claimed.
