# Veloren Native Decision v1

This isolated package adapts the local GTPyhop HTN pattern to the frozen, actor-local Pirate recruitment view. `adapter.py` produces at most one prediction-only `RecruitMember` task per current observation; `run_pair.py` can supervise one OFF and one ON server using independent prebuilt userdata copies, but requires a parent-reviewed freeze file and explicit invocation. It is not a port of an Evennia game instance and does not execute a hire.

`veloren-native-decision.patch` is a derivative modification of Veloren, whose upstream code is `GPL-3.0-or-later`; apply it after the pinned frozen A patch, not directly to an unrelated release. The original NPC task and settlement rules remain upstream behavior, not a new project method.

Run offline unit tests with the existing pinned environment:

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -B -m unittest tools.veloren_native_decision_v1.tests.test_adapter tools.veloren_native_decision_v1.tests.test_runner_contract -v
```

`run_pair.py` refuses to run without pinned source/patch/lock/binary hashes, an existing installed assets directory, independent prebuilt OFF/ON userdata manifests, loopback settings, and matching observer lists. It never creates or modifies a world copy. Assets are checked by path/existence, not by a complete content hash; see the result owner's reproducibility limit. `PROTOCOL.md` is the frozen prelaunch protocol, not a live status page.

Current result (2026-10-18): **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**. One OFF/ON pair actually ran. ON made six native recruitment attempts, five expired after Controller message enqueue and the sixth was still pending at the fixed cap; no attributable `Job::Hired` was observed. A Loaded native Msg routing gap was traced in the pinned upstream source; it was not repaired during this run. Do not treat `message_sent` as recipient delivery or success. The [unique result owner](../../02_实验/Veloren_Native_Decision_Integration_v1/RESULTS.md) contains the raw evidence, independent review and limits. No new run is automatic.

The runner is invoked as a module from the repository root (`python -m tools.veloren_native_decision_v1.run_pair ...`) so the package import resolves consistently. `TEST_ATTEMPTS.md` records development attempts; final local gates were 35/35 new Python, 25/25 old A Python and 7/7 focused Rust tests. These gates do not establish a successful hire.
