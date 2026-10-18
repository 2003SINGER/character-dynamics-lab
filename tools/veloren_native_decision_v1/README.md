# Veloren Native Decision v1

This isolated package adapts the local GTPyhop HTN pattern to the frozen, actor-local Pirate recruitment view. `adapter.py` produces at most one prediction-only `RecruitMember` task per current observation; `run_pair.py` can supervise one OFF and one ON server using independent prebuilt userdata copies, but requires a parent-reviewed freeze file and explicit invocation. It is not a port of an Evennia game instance and does not execute a hire.

`veloren-native-decision.patch` is a derivative modification of Veloren, whose upstream code is `GPL-3.0-or-later`; apply it after the pinned frozen A patch, not directly to an unrelated release. The original NPC task and settlement rules remain upstream behavior, not a new project method.

Run offline unit tests with the existing pinned environment:

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -B -m unittest tools.veloren_native_decision_v1.tests.test_adapter tools.veloren_native_decision_v1.tests.test_runner_contract tools.veloren_native_decision_v1.tests.test_loaded_msg_pair -v
```

`run_pair.py` refuses to run without pinned source/patch/lock/binary hashes, an existing installed assets directory, independent prebuilt OFF/ON userdata manifests, loopback settings, and matching observer lists. It never creates or modifies a world copy. Assets are checked by path/existence, not by a complete content hash; see the result owner's reproducibility limit. `PROTOCOL.md` is the frozen prelaunch protocol, not a live status page.

Historical pre-repair result (`ab6dad9`): **PARTIAL**. The old pair made six ON attempts with no attributable Hired; its frozen inputs, protocol deviation and failure evidence remain unchanged.

Current checkpoint (2026-10-18): **ROUTING/HIRE/FOLLOW finite PASS / READY_FOR_INDEPENDENT_REVIEW; stopped**. The separately authorized minimal repair retained Loaded Msg in RTSim and added read-only exact-message provenance. One new OFF/ON pair used the same repaired binary: ON submitted once, native UID442 became Hired by476 and executed its own native follow/Goto with 11.82m horizontal progress. This is not a completed party, raid, general Planner or research advantage. The [unique result owner](../../02_实验/Veloren_Native_Decision_Integration_v1/RESULTS.md) preserves raw evidence, the small timing overshoot and diagnostic-label limitations. No more runs or mechanism repairs are automatic.

`veloren-native-loaded-msg-repair.patch` applies **after** the old A and Decision patches. `loaded_msg_pair.py` and [LOADED_MSG_REPAIR_PROTOCOL.md](LOADED_MSG_REPAIR_PROTOCOL.md) are the new revision; they do not replace the frozen old runner/protocol. Unlike the old runner, the repair revision requires a nonempty, exact-complete assets content manifest, limits ON to six requests, terminates on qualified INSUFFICIENT_CHOICES, and stops submissions on the first fully attributed native Job. Its offline tests cover these contracts; actual fixed-pair evidence remains the authority for what happened.

Invoke the appropriate runner as a module from the repository root, with an explicitly reviewed freeze and a fresh non-overwriting output directory. The existing recorded pair must not be resumed or overwritten. Old development attempts remain in `TEST_ATTEMPTS.md`; new build/preflight failures and final 54 Python + 25 old Talk + 15 Rust passes are in the result owner's `evidence/loaded_msg_repair_v1/`. Offline gates alone do not establish a successful hire.
