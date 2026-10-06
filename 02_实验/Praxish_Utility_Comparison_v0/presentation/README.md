# Shared trajectory viewer v0

Status: development inspection only. This viewer helps inspect the existing paired traces; it does not establish player-visible meaning, usability, authoring cost, or a research gap. It is not a blinded study or a recruitment interface.

The exporter reads a successful comparison `case_results.json` and its manifest, then writes a new, non-overwriting bundle under `outputs/praxish_utility_comparison_v0/presentation/<presentation-id>/`. The bundle contains a standalone `viewer.html`, a separate `reviewer_metadata.json` identity key, and a manifest with source-run hashes, generator/template hashes, Git HEAD, and presentation seed. Errors are retained in `error.json`; an existing output ID is never reused.

The public projection is deliberately small and shared across both inputs:

- worker phase (`waiting`, `working`, `complete`);
- worker/visitor request state (`pending`, `served`, `cancelled`);
- workspace state (`open`, `closed`) when the trace records that world property.

Each displayed side-turn contains only the turn number, neutral actor label, mapped Chinese action label and any recorded bound target, recorded pre-state, event labels with their recorded before/after snapshots, and recorded post-state. Action actor/target labels must agree with the source turn and its role bindings. Request events show the changed visitor-to-worker pair from the recorded event snapshots. The state panel says “参与角色：访客”; the trace has no visitor-presence predicate, so the viewer does not claim they are physically present. The pre-state heading marks that it is after the turn's event tape and before its action. Empty-action turns are retained. Unknown facts, event IDs, actions, actors, malformed bindings, or conflicting same-entity states stop export and preserve the failed output record instead of being silently dropped. The exporter does not render goals, scores, candidate lists, methods, internal IDs, dialogue, emotion, durations, or unrecorded effects.

The low-motivation raw-cancellation alias is shown as recorded: the selected cancellation leaves the request `cancelled`, and subsequent work/request state is allowed to diverge from the utility baseline. The projection does not merge those states or infer why a player should care. A deterministic presentation seed counterbalances A/B assignment; the mapping is in `reviewer_metadata.json` and can also be revealed in-page. Because identity is discoverable, this is explicitly a developer inspection, not blinding.

## Reproduce

From the repository root, with the comparison release and successful run already available:

```sh
node "02_实验/Praxish_Utility_Comparison_v0/presentation/export.mjs" \
  --run-id comparison-final-contract-audit-20261007-01 \
  --presentation-id <fresh-presentation-id> \
  --presentation-seed 20261007

PRESENTATION_RUN_ID=comparison-final-contract-audit-20261007-01 \
  node --test "02_实验/Praxish_Utility_Comparison_v0/presentation/projection.test.mjs"
```

The test command accepts another successful run ID through `PRESENTATION_RUN_ID`. It also creates a uniquely named, synthetic unknown-action failure under the presentation output root to verify that `error.json` is retained and a repeated ID cannot overwrite it. No HTTP server, package installation, browser download, or network request is needed to open `viewer.html`. The small DOM smoke test exercises previous/next, playback, dropdown selection, source reveal, and empty-action display; final visual acceptance should still be done in a real browser.

The checked development source run has 12 cases: 11 case pairs have identical projected public trajectories; the raw low-motivation cancellation case is the single divergent pair (7 of its 8 turn pairs differ downstream). This is a trace fact, not evidence of preference, validity, or superiority. The three base cases (`no_request`, `request`, `lowpriority`) remain identical pairwise. The 12-turn second-worker case, empty turns, and adapted closed/reopened workspace are retained for inspection.
