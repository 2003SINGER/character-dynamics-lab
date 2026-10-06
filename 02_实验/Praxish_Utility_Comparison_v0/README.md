# Praxish utility comparison v0

**Status: READY_FOR_INDEPENDENT_REVIEW** — implementation and local tests are complete. The raw cancellation case preserves a verified upstream candidate-alias failure; explicit-binding variants isolate its effect. This is not `CLOSED`, not evidence that either organization is superior, and not player validation.

Start with [results and research decision](RESULTS.md), then [independent parent review](PARENT_REVIEW.md) for exact run IDs and the requirement-by-requirement audit. The bounded research decision is **NO_GO for an activity-organization behavioral-advantage claim in this shared fixture**. This follows the goal's negative-decision branch, not a claim of player meaning, author-cost savings, or a new general mechanism gap. Implementation tests alone do not establish those claims.

The [offline shared viewer](presentation/README.md) projects existing traces into the same anonymous A/B presentation, including targets, public states and events. It is development inspection, not a player experiment; the source identity can be explicitly revealed.

This compares the AIIDE 2023 release's activity-grouped action definitions against a separately authored, flat, parameterized one-step utility baseline. Both use the same turn/event schedule, action effects, role bindings, absolute post-state goal utility, actor order, seeded LCG tie-break, and public fact projection. The baseline does not import or translate Praxish practice/action definitions. Its reusable action templates, bindings, preconditions/effects, and goal factors are in [utility_baseline.json](utility_baseline.json); shared schedules and actor order are in [cases.json](cases.json); the world rules are in [world_contract.json](world_contract.json).

The comparison is intentionally narrow: matched goal-based one-step utility selection. It does not reproduce the full Dragon Age/Dual Utility systems, and adds no response curves, inertia, learning, or multi-step planning. Since Praxish itself already has utility scoring, this asks whether its activity organization changes authoring/behavior relative to a fair flat utility content representation—not whether it beats all utility methods. Equal observable traces are a null result, not something to explain away. The experiment does not establish authoring-time savings: the human author time and labor cost are unknown; the saved before/after snapshots and diffs are descriptive records, not an author-cost benchmark.

## Run

From the repository root, with the pinned release already fetched by the Activity Pilot:

```sh
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" fetch
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" test
node "02_实验/Praxish_Utility_Comparison_v0/tools/compare.mjs" test
node "02_实验/Praxish_Utility_Comparison_v0/tools/compare.mjs" run --run-id <fresh-id>
```

Use a new run ID every time. `test` also injects an explicitly labeled CLI preservation-test failure after writing artifacts, then verifies its manifest/error/traces remain and that a repeated ID cannot overwrite them. This synthetic CLI fault is not scenario evidence. Run output lives in ignored `outputs/praxish_utility_comparison_v0/runs/<id>/`; each manifest records Node version, seed, runner/config hashes, and the verified source pin. The CLI uses Node built-ins and is intended to run on Node 22+. It resolves paths from its own file, not the current working directory.

Each run includes `case_results.json` with every turn's typed pre-state, candidates, roles, per-goal match counts and contributions, selected action and post-state. Selected candidate identity is checked using the concrete practice instance and role bindings, and the score reported by the original tick is checked against that exact candidate. It also includes a common-label timeline (`typed_timeline.json`), 32 tie seeds, actual negative-control parity issues, closure hard-constraint audit, and before/after inputs plus replay-checked structural JSON Pointer diffs for each extension. Each snapshot contains both behavior inputs and the common schedule/world contract. The timeline deliberately hides method and utility details. Full numerical evidence stays in the case traces.

The normal CLI exits successfully only with status `succeeded_with_documented_upstream_behavioral_divergence`: the two cancellation mismatches are accepted only after an exact signature gate verifies the pinned-source alias, its low-motivation Wait/Cancel divergence, and both explicit-binding parity controls. They remain marked `passed: false` in those case records. Any other parity mismatch, unexpected timeline mismatch, tie mismatch, or undetected negative control fails the run.

## Cases and present boundary

- `no_request`, `request`, `lowpriority`: same authored world and actions; the event only inserts a pending request. The preference case changes only the authored request weight.
- `request_cancellation`: adds a visitor cancellation action/goal. The untouched release's `getAllPossibleActions(visitor)` returns two candidate entries that are the same object (`a[0] === a[1]`) and both become `Cancel`; the flat baseline retains distinct wait/cancel candidates. It is labeled as an observed upstream failure, not silently repaired or counted as parity. The `request_cancellation_low_motivation` paired case gives Cancel utility `-1`: the flat baseline waits (0 > -1), while the aliased release selects Cancel. Two separately authored explicit-`Status`-binding workaround cases restore distinct actions and paired behavior at both preferences. They do not alter upstream bytes. See `debug_evidence.json` and [PROVENANCE.md](PROVENANCE.md).
- `second_worker_visitor_pair`: adds another worker and visitor while reusing the same flat templates and practice definitions; each worker's goal references that worker's own work and a variable visitor. This case uses its declared 12-turn horizon so both workers can respond and finish their finite work.
- `multiple_requests_one_worker`: one worker gets two distinct pending requests. The service goal uses a variable visitor binding in both authored inputs; after the first is served, serving the second has two absolute satisfied matches, so that goal contributes 20 (plus the separate working goal where applicable). This case also uses 12 turns so both requests and the worker's finite task can complete.
- `workspace_closure_unadapted`: the common contract says finishing while closed is illegal. Both decision procedures are left unchanged; the selected finish is recorded as a constraint violation, not rolled back.
- `workspace_closure_adapted`: each side receives only the matching finish precondition. Work remains unfinished while closed and can be finished after reopening.
- `equal_score_tie`: at least 32 seeds check candidate ordering, RNG parity, selected action and state; both tied choices must occur.

The base and short extension fixtures use 8 turns; the two expanded multi-entity cases explicitly use 12. These finite horizons are not evidence of long-term life plausibility; empty-action terminal turns are fixture-horizon outcomes. No player recruitment or human-validity comparison has occurred. The reference release's source pin and license caveat are documented in [PROVENANCE.md](PROVENANCE.md); the upstream files are neither vendored nor edited here.
