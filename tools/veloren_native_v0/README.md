# Veloren native TalkToNpc patch

This local patch targets Veloren `v0.18.0` commit
`1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`. The modified upstream files are
covered by Veloren's `GPL-3.0-or-later` license. This patch is experimental and
is not an upstream release.

Verification status: the file-only CLI tests pass. The Rust patch has not yet
compiled or run; native NPC observation and TalkToNpc behavior are unverified.

Enable the relevant features only for a server process by setting their
environment variables before launch. Request polling requires both request and
event paths; observation-only mode requires `VELOREN_NATIVE_OBSERVE=1` and an
event path, and can be enabled without request polling:

- `VELOREN_NATIVE_REQUESTS=/absolute/path/requests.jsonl`
- `VELOREN_NATIVE_EVENTS=/absolute/path/events.jsonl`
- `VELOREN_NATIVE_OBSERVE=1` enables bounded baseline observation.
- `VELOREN_NATIVE_OBSERVE_UIDS=uid1,uid2` selects up to two actual NPCs for
  one-second baseline samples; first run with observation enabled to inspect the
  limited catalog, then set the selected UIDs on the next run.
- `VELOREN_NATIVE_PERSISTER_NPC_UIDS=uid1,uid2` optionally asks the headless
  CLI to load chunks around those existing civilised NPC positions; this uses
  Veloren's native persister and does not move the NPCs or players.

When `VELOREN_NATIVE_REQUESTS` is unset, request polling is skipped. The
request file is append-only JSONL and new complete lines are consumed by byte
cursor on server ticks; terminate each line with `\n` and keep each unread
batch below 1 MiB. Each request ID is accepted at most once per server process. A changed
payload with the same ID is rejected as a conflict. One active external lease
per NPC is allowed; TTL is in seconds and bounded to 0.1–60.0.
Append `{"cancel_request_id":"<request_id>"}` as a separate line to cancel
before the native speech intent is queued. A cancellation after that point is
reported as too late and does not retract a native action already handed to
the agent.

The lease TTL/cancellation boundary is the native Brain action, not guaranteed
speech emission: `native_intent_queued` records the point at which Veloren's
native Brain produced a matching Say action. If another long-running native
Brain action is already active, the request stays pending until native
scheduling reaches the external action; cancellation/expiry is not an
out-of-band interruption of that existing action. A Say already handed to the
agent may be emitted later; the event log timestamps intent queueing separately
from `native_speech_emitted` or `speech_blocked`.

Only `TalkToNpc` is supported. Both UIDs must resolve to distinct, alive,
loaded, civilised NPCs no more than 8 world units apart. Baseline observation
is disabled unless explicitly enabled; the catalog is capped at 24 living
civilised NPCs and is emitted every 10 seconds, while selected baselines are
sampled at 1 Hz. The request only
selects Veloren's existing native `talk_to` behavior. Native interruption,
dialogue content, speech gating, and world validation remain authoritative.

An example request line is in
`request_talk.jsonl.example`; the cancellation format is shown above. `native_speech_emitted` means the server emitted
the native chat event; it does not prove recipient delivery, acceptance, or a
completed conversation. The patch does not create NPCs, move entities, or
write game-world outcomes.

`native_talk.py` is a file-only helper. For example, after choosing real UIDs
from the bounded catalog and starting a server configured with those paths:

```sh
python3 tools/veloren_native_v0/native_talk.py request \
  --requests /absolute/path/requests.jsonl --source local-harness \
  --request-id run-001 --npc-uid 123 --target-uid 456 --ttl 20
python3 tools/veloren_native_v0/native_talk.py events \
  --events /absolute/path/events.jsonl --request-id run-001 --follow
python3 tools/veloren_native_v0/native_talk.py cancel \
  --requests /absolute/path/requests.jsonl --request-id run-001
```

The helper only appends/prints records; server acceptance and native outcome
must be read from the event log. It never starts the world or manufactures
feedback.

The file-only helper tests use Python's standard library:

```sh
python3 tools/veloren_native_v0/test_native_talk.py -v
```

They exercise temporary JSONL files only; captured output is preserved under
`offline_evidence/python_cli_unittest.txt`. These tests do not run Veloren.

## Source/build reproduction boundary

Use the official **GitLab** source commit above, not the differently pinned
GitHub mirror tag. Apply `veloren-native-talk.patch` to that source checkout;
the patch changes eight Rust files and does not alter dependency versions.
Use the source's `nightly-2025-09-08` toolchain. The current attempt selected:

```sh
cargo check --locked -p veloren-server-cli --no-default-features \
  --features worldgen,persistent_world --jobs 2
```

The full upstream workspace also resolves client-only dependencies. The
experiment therefore used a separate build copy with only workspace membership
restricted to `server-cli`; see the preserved
[build-scope diff](../../02_实验/Veloren_Vertical_Slice_v0/evidence/server_build_20261016/server-build-scope.patch).
Keep the original checkout and lockfile unchanged. Original and build-copy
`Cargo.lock` both hash to
`cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`.
This is a build-scope adaptation, separate from the NPC interface patch, not a
new game mechanic.

No modified server binary has been built. The final recorded dependency fetch
failed resolving `index.crates.io` for the `rusqlite` index entry. Raw attempts
and exact process-local settings are in the
[build evidence index](../../02_实验/Veloren_Vertical_Slice_v0/evidence/server_build_20261016/attempt_index.json).
After dependency access is restored, compile and test before using the request
example; then run observation-only against an independent copy of the original
world and choose real NPC UIDs. Never substitute the example UIDs for discovered
identities, or count these file tests as native execution.
