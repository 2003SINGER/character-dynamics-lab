# Mature-Methods Integration v1 — bounded native evidence

This is a bounded mixed-outcome integration record, not a system PASS, novelty claim, or performance comparison. The fixed four-pair matrix used one existing P5 world and eight unique native scenes; every arm used the same seed/preset/horizon and native P5 Director comparison, without extra observe_actor sampling.

- Suite SHA-256: `952ddb923d12b106628dca7b0cb13829659daf0aae25040b6ad630ce0df5554b`
- Base commit: `47d3ce7e445747c153c9ab4c5d3f34e2ebc12495`; execution source identities are preserved per arm in `index.json`.
- Indexed raw/source members: 1701 files; 579,810,974 bytes before compression.
- Lifecycle: one authorized stop/start of the same existing Evennia DB/ports before S1; raw stop/start logs are included and health READY was recorded by orchestration.

| Case | Result | Native scenes | GTP root calls (mature) | P5 snapshot calls (mature) |
|---|---|---|---:|---:|
| S1-result-only-reject | BOUNDED_CLOSED_LOOP_COMPLETE_WITH_TWO_RUNNER_FAILURES_AND_RESUMED_MATURE_ARM | 20261012075826-f0be07 / 20261012075840-41a78a | 5 | 26 |
| S2-edit-reselect-accept | NATIVE_PERMISSION_EDIT_UNSUPPORTED_RESELECTION_NOT_EXERCISED | 20261012083537-46a3b8 / 20261012083550-ae5dea | 5 | 25 |
| S3-player-get-drop-recovery-reject | NATIVE_PAIR_COMPLETE_AVAILABILITY_CHANGE_OBSERVED | 20261012083620-9e9dcc / 20261012083634-b57654 | 7 | 25 |
| S4-no-permission-safety-negative | NATIVE_SAFETY_NEGATIVE_COMPLETE | 20261012083657-3233d6 / 20261012083709-c849e5 | 2 | 25 |

S1 is the minimum closed-loop positive chain: native side-route receipt, NPC task execution/receipts, rejection branch, and all four hard obligations satisfied. The mature arm required preserving two failed runner attempts and a verified same-scene minute17→24 continuation. Valid method work aggregates the 0→17 and 17→24 segments to 5 GTP roots, 26 P5 snapshots (minute17 checkpoint counted in each segment), and 24 advances; all attempts including the initial wrong-interpreter import failure total 6 roots/27 snapshots/24 advances. Per-segment counts and timings are in `index.json`; the baseline used system Python and continuation used the project venv, so runtime comparison is invalid.

S2 is a native capability mismatch, not a successful stale-candidate/reselection case: the minute1 CAS was rejected with `PERMISSION_ESCALATION` because runtime edits cannot change permissions or author budget. Bundle version remained 1 and the side path stayed legal; no stale guard or main-route reselection was exercised.

S3 recorded player get@2/drop@6, the native availability transition, and a matched pair. S4 recorded no opportunity attempts and all hard obligations `VIOLATED`; it is a safety negative only, not a world-unreachability claim.

All raw attempts, failures, source snapshots (including the explicitly non-authoritative flattened copy), per-minute traces, RPC requests/responses, independent DB readbacks, and runner continuation links are retained in the archive. No files under the project's RESULTS.md were changed by this packager.
