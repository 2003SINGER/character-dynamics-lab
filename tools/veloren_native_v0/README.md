# Veloren native TalkToNpc patch

This experimental local patch targets the official Veloren GitLab source commit
`1d12f35edd6cdbfc1fb921c167cdd7beeeffe248` (`v0.18.0`). It changes nine Rust
files and does not alter dependency versions or `Cargo.lock`. The upstream
source remains under `GPL-3.0-or-later`; this is not an upstream release.
Frozen final A patch SHA-256: `4174287ddd467804e7efbfe7bb6868736475597f0225067c2030aaa17c709610` (earlier attempt hashes remain in their evidence).
Changed paths: `common/src/rtsim.rs`; `rtsim/src/data/npc.rs`,
`rtsim/src/rule/npc_ai/mod.rs`, `rtsim/src/rule/simulate_npcs.rs`;
`server-cli/src/main.rs`; `server/src/lib.rs`, `server/src/rtsim/mod.rs`,
`server/src/rtsim/tick.rs`, `server/src/sys/agent/behavior_tree/mod.rs`.

Current verification: **A = PASS_BY_NATIVE_TRACE / A_FROZEN**, limited to the
final native Talk interface and cancellation evidence, not recipient acceptance
or a complete planning system. The earlier A-Closure cancel-admission failure
is retained as history, not the current result. The new high-level recruitment
work has its own [result owner](../../02_实验/Veloren_Native_Decision_Integration_v1/RESULTS.md)
and does not rerun or alter this A interface. Rust checks and focused tests are
reported with their actual patch versions. See
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

A-Closure records the existing single short-circuited random draw in a local
boolean; it does not draw again or change its branch. Request-scoped
`native_talk_branch` distinguishes the native route and `early_cut`/`continue`.
`native_action_handoff` is emitted only after the tagged Say is actually pushed
to the Agent queue. `native_action_filtered` records an actual native rtsim
filter and its reason, not an inferred Agent refusal. The Agent speech logic
is unchanged from the previous patch. These diagnostics are runtime-only.

Only `TalkToNpc` is supported. Both UIDs must resolve to distinct, alive,
civilised, Loaded NPCs no more than 8 XY world units apart in the historical
server admission guard added by this experimental patch, not an NPC social
decision or Agent speech result. The A-Closure harness additionally requires fresh
actual ECS **3D** distance ≤8; the XY guard alone is not that proof. Request polling is
disabled unless both paths are set:

- `VELOREN_NATIVE_REQUESTS=/absolute/path/requests.jsonl`
- `VELOREN_NATIVE_EVENTS=/absolute/path/events.jsonl`
- `VELOREN_NATIVE_OBSERVE=1` enables bounded catalog and baseline telemetry;
  observation is off by default.
- `VELOREN_NATIVE_OBSERVE_UIDS=uid1,uid2` selects fixed real NPCs for 1 Hz
  baseline samples. A-Closure also samples at most 16 distinct UIDs cached from
  the existing catalog's eight Loaded pairs, with alive, active-lease and native
  `agent_allowed_to_speak` fields. This does not move or spawn NPCs.
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

For the bounded control/probe, prepare an existing empty request file and a new
or empty event file. Start the helper before the server. It never launches or
stops Veloren. It waits at most 120 seconds for the first baseline, then uses
60-second candidate windows requiring five continuous seconds of fresh,
living, Loaded, native-speaking, 3D-nearby samples with no active sender lease.
The preferred pair is used when eligible; fallback is restricted to published
catalog pairs sorted by fresh 3D distance and UID. One atomic two-line cancel
control must reach exactly `cancelled_before_native_action`, with no tagged
intent, handoff or Agent effect, before any positive submission.

`--max-positive` defaults to one and is hard-capped at six actual submissions;
rejected and no-speech attempts count. Each uses a new ID and verified input
prefix, up to 80 seconds of feedback and 20 seconds of subsequent observation.
An unclosed feedback window stops the run. The first Agent effect also stops
further requests after its continuation check; missing evidence is not repaired
by retrying. Output is a separate harness transcript, not server events or a
game verdict. The exact two-launch A-Closure protocol is in RESULTS.

```sh
python3 tools/veloren_native_v0/run_talk_probe.py \
  --events /absolute/path/events.jsonl \
  --requests /absolute/path/empty-requests.jsonl \
  --npc-uid 445 --target-uid 465 --source native-probe \
  --cancel-id probe-cancel-001 --request-id probe-positive --max-positive 6
```

The ten standard-library probe tests use temporary files only. Run both file
interfaces (15 tests, no game):
`python3 -B -m unittest discover -s tools/veloren_native_v0 -p 'test*.py' -v`.

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

The A-Closure focused suite totals 14 passing tests (common 1, rtsim 8, server 5).
The preceding `1ccf5c1…` patch had 12; those historical results are not relabeled.
Package-selected checks/build in the official full workspace are recorded under
the ignored local
`_local_data/external_games/veloren_0_18_0/evidence/server_build_20261017/`;
the source archive and game data are not committed.

## Native run conclusion

`A=PARTIAL`; `A-Closure=BLOCKED_CANCEL_ADMISSION`; `B=NOT_STARTED_A_GATE`.
The new patch built and passed 14 Rust / 15 file-interface tests. Two isolated
servers ran and exited normally. The new cancel-control input was rejected as
`pair_not_live_loaded_civilised_nearby`, followed by `not_found`, so cancellation
was not exercised. There were **zero positive submissions**. Fresh pre-submit
ECS samples met the protocol, while a later sample exceeded its distance
limit; the composite rejection does not identify the precise failed guard.
The controller was manually interrupted under the stop rule (exit 130), not
an automatic abort or success. No code was changed during the runs.

The prior `3a82cd0` run remains a separate partial result: it had a valid cancel
and one Brain terminal without speech, with no observed RNG draw or Agent
result. This round does not explain that historical no-speech outcome. The new
branch/handoff diagnostics were not reached by a positive request. No Agent,
relationship, recipient-acceptance or planning success is claimed. All inputs,
deviations and evidence are owned by
[RESULTS.md](../../02_实验/Veloren_Vertical_Slice_v0/RESULTS.md). Both permitted
launches were used; this work package has stopped without retries or B work.
