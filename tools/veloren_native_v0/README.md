# Veloren native TalkToNpc patch

This experimental local patch targets the official Veloren GitLab source commit
`1d12f35edd6cdbfc1fb921c167cdd7beeeffe248` (`v0.18.0`). It changes nine Rust
files and does not alter dependency versions or `Cargo.lock`. The upstream
source remains under `GPL-3.0-or-later`; this is not an upstream release.
Patch SHA-256: `1ccf5c1db8d164743838b1bcb67a73adea88dd7a180f64c45b4c204c48097936`.
Changed paths: `common/src/rtsim.rs`; `rtsim/src/data/npc.rs`,
`rtsim/src/rule/npc_ai/mod.rs`, `rtsim/src/rule/simulate_npcs.rs`;
`server-cli/src/main.rs`; `server/src/lib.rs`, `server/src/rtsim/mod.rs`,
`server/src/rtsim/tick.rs`, `server/src/sys/agent/behavior_tree/mod.rs`.

Current verification (2026-10-17): `SERVER_BUILD=PASS`, native baseline
established, and **work package A = PARTIAL**. The sole positive request entered
the native Brain but completed without speech; no Agent speech/blocked result
was observed. Work package B has not started. Rust checks and focused tests are
reported with their actual patch versions, not relabeled as one final run. See
[RESULTS.md](../../02_实验/Veloren_Vertical_Slice_v0/RESULTS.md) for the
experiment status and evidence boundary.

## Patch behavior and limits

Request provenance is attached explicitly to the exact `Say` created by the
external native `talk_to` action. Ordinary native speech is never inferred to
belong to a request; the request ID travels beside its action and is reindexed
when native `simulate_npcs` filters the action queue. When provenance is empty,
the original `Vec::retain` path remains in use.

The read-only catalog scans all living civilised NPCs rather than taking the
first 24. Every 10 seconds it reports bounded summaries: up to eight nearby
pairs whose two NPCs are genuinely Loaded and whose loaded Agents both allow
speaking, plus up to eight nearby Simulated-pair hints. The catalog's 8-unit
pair distance is measured in XY only. This is a catalog filter, not proof of
3D proximity or of a live interaction; verify the actual NPC pair and vertical
separation during the native run. Simulated hints are not eligible request
targets. Catalog output does not spawn or teleport NPCs; optional native
persister loading is described below.

While an external request is pending, Brain telemetry is sampled at most once
per second. Once the native Brain action has an outcome, one
`native_brain_action_terminal` event is recorded instead of further per-tick
samples. Overall telemetry is opt-in and bounded by default to 10,000 records,
8 MiB, 600 seconds, and 64 KiB per record (`VELOREN_NATIVE_MAX_RECORDS`,
`VELOREN_NATIVE_MAX_BYTES`, and `VELOREN_NATIVE_MAX_SECONDS` can raise these
within code limits). Reaching a cap silently drops further events, so missing
terminal telemetry is not evidence of a successful outcome.

An accepted request may remain pending while an existing native Brain action
holds the slot. Cancellation or TTL expiry before the external action starts is
settled separately and does not interrupt that existing native action. Once the
external native action is active, the original cancellation, expiry, inbox,
enemy, and quest-timeout interruption path runs through native `StopIf` and
`on_cancel`. A matching `Say` already queued for the Agent cannot be retracted;
cancellation at that point is reported as too late. Queueing an intent is not
the same as emitting speech.

Veloren's native small-talk rule has a 20% random idle branch for NPC-to-NPC
talk. A valid request can therefore complete without a Say; record
`native_talk_completed_without_speech` as a partial/no-speech outcome. Do not
retry with a new seed or claim that the request guarantees speech. Likewise,
`native_speech_emitted` proves only that the sending Agent emitted the native
chat event; it does not prove recipient delivery, acceptance, or a completed
conversation. Native speech gating and world validation remain authoritative.

Only `TalkToNpc` is supported. Both UIDs must resolve to distinct, alive,
civilised, Loaded NPCs no more than 8 world units apart. Request polling is
disabled unless both paths are set:

- `VELOREN_NATIVE_REQUESTS=/absolute/path/requests.jsonl`
- `VELOREN_NATIVE_EVENTS=/absolute/path/events.jsonl`
- `VELOREN_NATIVE_OBSERVE=1` enables bounded catalog and baseline telemetry;
  observation is off by default.
- `VELOREN_NATIVE_OBSERVE_UIDS=uid1,uid2` selects up to two real NPCs for 1 Hz
  baseline samples.
- `VELOREN_NATIVE_PERSISTER_NPC_UIDS=uid1,uid2` optionally loads chunks around
  those existing NPC positions through Veloren's native persister; it does not
  move NPCs or players.

The append-only request JSONL consumes complete newline-terminated records on
server ticks. Keep each unread batch below 1 MiB; request IDs are unique per
server process and conflicting reuse is rejected. Only one active external
lease per sender NPC is allowed. TTL is 0.1–60 seconds and at most 16 external
requests may be active. After an intent is queued, the lease is no longer
active for admission purposes, but its queued Say may still await Agent handling.
Append
`{"cancel_request_id":"<request_id>"}` as a separate line to cancel.
`native_intent_queued` marks the matching Say entering the native action queue;
`speech_blocked` and `native_speech_emitted` describe later sender-side Agent
handling, not recipient receipt.

An example request is in `request_talk.jsonl.example`. `native_talk.py` only
appends or prints JSONL; it never starts the world or manufactures feedback:

```sh
python3 tools/veloren_native_v0/native_talk.py request \
  --requests /absolute/path/requests.jsonl --source local-harness \
  --request-id run-001 --npc-uid 123 --target-uid 456 --ttl 20
python3 tools/veloren_native_v0/native_talk.py events \
  --events /absolute/path/events.jsonl --request-id run-001 --follow
python3 tools/veloren_native_v0/native_talk.py cancel \
  --requests /absolute/path/requests.jsonl --request-id run-001
```

The file-only helper's standard-library tests are run with
`python3 tools/veloren_native_v0/test_native_talk.py -v`; saved output is in
`offline_evidence/python_cli_unittest.txt`. They do not run Veloren.

For a tightly gated one-time control/probe, prepare an existing empty request
file and configure the server to use it. Run this helper before or during the
native run; it can wait while the events file is not yet present. It never
launches or stops the server. It waits for a
fresh 5-second Loaded/speaking pair window, appends the cancellation request and
same-ID cancel in one OS write, and will not send the unique positive request
unless the server reports exactly `cancelled_before_native_action` with no
same-ID intent or Agent effect. This is the fixed native event outcome for a
request cancelled before its Brain action starts; the harness does not infer
it from a generic cancellation label. It then requires a newly qualified pair
before the single positive append. Output is a separate harness transcript,
not server events or a game verdict.

```sh
python3 tools/veloren_native_v0/run_talk_probe.py \
  --events /absolute/path/events.jsonl \
  --requests /absolute/path/empty-requests.jsonl \
  --npc-uid 445 --target-uid 465 --source native-probe \
  --cancel-id probe-cancel-001 --request-id probe-positive-001
```

The four standard-library probe tests use temporary files only:
`python3 tools/veloren_native_v0/test_run_talk_probe.py -v`.

## Reproducing the Rust checks

Use the official full workspace manifest and original lockfile in a separate
build copy. Do not prune workspace membership: the earlier server-only manifest
reduction caused Cargo to require a lockfile change and was abandoned. Select
only `veloren-server-cli` as the package; do not build the client. Use the
pinned `nightly-2025-09-08` toolchain, the same original `Cargo.lock`,
process-local `CARGO_INCREMENTAL=0`, and the official installation assets for
tests. The recorded successful check and focused test commands below omit the
`plugins` feature; they prove compile/test behavior, not a headless first-tick
run. The runtime build must include `plugins`: the first no-plugins headless
tick exited 134 because `RequestPluginsEvent` had no registered handler
(`information` handler is cfg-gated by `plugins`, while event type checking is
unconditional). That failed launch is preserved as evidence; assertions and
world data were not changed. Veloren's original server defaults include
`plugins`. No global Cargo or proxy configuration is required; the recorded
fetch used command-local registry replacement.

```sh
CARGO_INCREMENTAL=0 cargo --config 'source.crates-io.replace-with="rsproxy-sparse"' \
  --config 'source.rsproxy-sparse.registry="sparse+https://rsproxy.cn/index/"' \
  check --locked -p veloren-server-cli --no-default-features \
  --features worldgen,persistent_world --jobs 2

CARGO_INCREMENTAL=0 VELOREN_ASSETS=/absolute/path/to/original/install/assets \
  cargo --config 'source.crates-io.replace-with="rsproxy-sparse"' \
  --config 'source.rsproxy-sparse.registry="sparse+https://rsproxy.cn/index/"' \
  test --locked -p veloren-common --lib \
  rtsim::rtsim_controller_correlation_tests::native_say_before_external_say_keeps_request_id_on_its_own_action \
  -- --exact
CARGO_INCREMENTAL=0 VELOREN_ASSETS=/absolute/path/to/original/install/assets \
  cargo --config 'source.crates-io.replace-with="rsproxy-sparse"' \
  --config 'source.rsproxy-sparse.registry="sparse+https://rsproxy.cn/index/"' \
  test --locked -p veloren-rtsim --lib external_talk_tests
CARGO_INCREMENTAL=0 VELOREN_ASSETS=/absolute/path/to/original/install/assets \
  cargo --config 'source.crates-io.replace-with="rsproxy-sparse"' \
  --config 'source.rsproxy-sparse.registry="sparse+https://rsproxy.cn/index/"' \
  test --locked -p veloren-server --no-default-features \
  --features worldgen,persistent_world --lib native_request_tests

CARGO_INCREMENTAL=0 RUSTFLAGS='-C debuginfo=0' cargo --config 'source.crates-io.replace-with="rsproxy-sparse"' \
  --config 'source.rsproxy-sparse.registry="sparse+https://rsproxy.cn/index/"' \
  build --locked -p veloren-server-cli --no-default-features \
  --features worldgen,persistent_world,plugins --jobs 2
```

`RUSTFLAGS='-C debuginfo=0'` is process-local to the build command and reduces
debug-info disk use; it does not change the source manifest or lockfile. The
successful runtime-feature build produced the binary recorded in local build
evidence. Do not omit `plugins` when reproducing the headless run.

The recorded focused suite totals 12 tests (common 1, rtsim 6, server 5).
Full-workspace check/test/build evidence is under the ignored local
`_local_data/external_games/veloren_0_18_0/evidence/server_build_20261017/`;
the source archive and game data are not committed.

## Native run conclusion

`A=PARTIAL`; `B=NOT_STARTED_A_GATE`. The patched server built, the original-world
baseline was observed, and one real negative-control input reached the exact
`cancelled_before_native_action` terminal with no same-ID intent or Agent effect.
The single positive request was accepted and entered the native Brain; its
terminal outcome was `native_talk_completed_without_speech`. No
`native_speech_emitted` or `speech_blocked` event was observed for that request.
This is a valid no-speech outcome, not evidence of rejection. The static native
small-talk rule has a random idle branch, but this run did not record an RNG
draw, so that branch is not asserted as the cause.

The run demonstrates the build, baseline, request/cancel input path, and native
Brain continuation only. Agent handling beyond the observed event boundary is
not proven; the raw trace and final event counts remain subject to review in
[RESULTS.md](../../02_实验/Veloren_Vertical_Slice_v0/RESULTS.md) and its linked
manifest. The harness exited 0 because its observation workflow ended; that
exit code is not a game-success verdict. Do not retry, change the seed, or
promote this partial result to an A pass. B remains gated on A acceptance.
