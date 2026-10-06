# Provenance and boundaries

The reference implementation is the publisher-provided Praxish AIIDE 2023 release, pinned through the Activity Pilot:

- tag `aiide-23`, commit `4729b0c469a7ecb423622f543ca116315616a76b`
- archive SHA-256 `a5418432db8f2af8387a8eead2e4ad1392465833d862eda9273c614b883a8c77`
- `db.js` SHA-256 `acb98656dcc0fe461ba7d6b2875bd3429ae4068735b1795297a5722d0469c46c`
- `praxish.js` SHA-256 `ef2f77999b08dd24c9893a531ae2096ef33189a9cf46bf342d024ffa44e1c088`
- `tests.js` SHA-256 `7b9a41281ec8620d43bcf0062b39cbcbaad22349483fe9cae55b3ef823486947`

The new harness imports the existing pilot's `verifyArtifact` and `runScenario` API. It does not edit or vendor the release sources. Upstream licensing remains as recorded in [the Activity Pilot provenance](../Praxish_Activity_Pilot_v0/PROVENANCE.md): no license file was found in the pinned release/tag inspection; the current upstream MIT license is not assumed to apply retroactively. Use is local to this research checkout; no upstream source is republished by this comparison.

The comparison-side activities, baseline templates, goals, shared world contract, and derived scenarios are our own authored experiment inputs. Both sides use the same authored goal generalization `Visitor` for a worker's own request records; with a second worker, the worker-specific path remains bound to that worker. The pinned `tests.js` is not changed.

An independent direct VM check of the pinned `getAllPossibleActions` confirms the raw cancellation case's two visitor results have object identity (`candidates[0] === candidates[1]`) and both action IDs resolve to Cancel. This is an upstream behavior in the pinned source, not an observer mutation: the direct check loads only the pinned `db.js` and `praxish.js`, adds the request instance, and inspects the candidate array before ticking. The low-cancel-motivation paired case exposes its behavioral effect. A separately authored cancellation condition that binds `Status` before testing `pending` produces distinct objects and restores the Wait/Cancel choices; this is retained as a workaround condition, not an upstream repair.

Extension snapshots in each ignored run include both authors' actual scenario/config inputs, the shared seed/turn/event/actor schedule, and the world contract. Their JSON Pointer add/remove/replace diffs are applied by the runner and checked to reconstruct the recorded after-inputs.

This is a constrained deterministic mechanism comparison, not a claim about NPC architecture in general, human authoring cost, long-duration behavior, player perception, player efficacy, or validity in a game. The shared VM runner records the original tick's output; it does not verify the browser UI. Do not interpret a common timeline as player-facing quality evidence.
