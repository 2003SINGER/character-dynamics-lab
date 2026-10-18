# Loaded Msg repair — independent static audit

Scope: the nine-file incremental Rust patch `tools/veloren_native_decision_v1/veloren-native-loaded-msg-repair.patch`, SHA-256 `4883c461895833d493b130143df5f0dd3245b31d00a8324e8b87e90d6ea84ee1`, plus the paired Python runner control path. This is a source-level review, not native-run evidence.

## Static finding

The intended provenance path is connected end to end: request metadata is attached to the exact native `Msg` action index; action retention and Loaded handoff preserve/remap sidecars by that same index; `Msg` remains in RTSim while other actions keep their existing Agent handoff order. `SimulateNpcs` keeps the pre-existing NPC-to-NPC routing and filtering, attaching metadata only when sender UID matches. The recipient inbox still contains the original `NpcInput`; the existing `RequestHire` handler checks the mapped sender/target identities, records consumption, then executes the existing response and `set_newly_hired(..., infinity)` setter before recording its effect receipt. Server readback requires the matching real `Job::Hired(Actor::Npc(leader), until)` and matching receipt metadata before emitting an attributable Job observation.

No source-level change was found to native recruitment admission conditions, the `RequestHire` setter, RNG draws, or global rule ordering. Ordinary Say correlation remains on its separate Say-index sidecar; the new recruitment provenance is attached only by the request-scoped native recruitment action.

## Limits and acceptance rule

This static review cannot establish that the native path executes in a live world. For the upcoming pair, evaluate each request from raw events through retained Msg, inbox delivery, input consumption, setter receipt, and actual Job readback. Any provenance violation makes the final result FAIL, even if a `trusted_hires` entry was previously recorded. A repeated Job observation after a completed chain is therefore an explicit failure condition; do not suppress it because the first observation was trusted.

Parent-reported Rust/Python test results are not represented here as independently reproduced evidence. The sole OFF/ON run remains pending; no outcome is claimed.
