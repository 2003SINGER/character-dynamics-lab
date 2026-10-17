# Final-interface source and harness audit

This is a bounded static review plus file-only Python test run. It is not native-game evidence and does not claim the NPC control chain passed.

- Fixed source: official Veloren GitLab v0.18.0 commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`.
- Native source patch SHA-256: `4174287ddd467804e7efbfe7bb6868736475597f0225067c2030aaa17c709610`.
- Harness SHA-256 at the combined-test run: `6cbbf5605d84ce716510402dd6b22400dc84382629885d8103fcef6f8ca09333`.
- Harness-test SHA-256 at the combined-test run: `24f7eff33d8e7f0e091507242ca34e7a7f3f8a9dcd73bfbc4d03ab318d5e53a0`.
- Native CLI test SHA-256 at the combined-test run: `28ee35bce244a0a1405f7657588c6ab772d52ad6e8a1486670bd9762fa868df0`.
- Cargo.lock SHA-256: `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`.
- Successful server build binary SHA-256: `70e01a9f21dcabec68401ab6eccb130f8b38cca4568da4740a46fc53b7a77ff1`.

The existing admission condition remains the sole authority: distinct NPCs, alive, civilised, Loaded, and RTSim XY distance no greater than 8m. The added diagnostic reports those inputs and failed subconditions only; it neither substitutes ECS 3D distance nor changes admission, ordering, or native NPC behavior. The source change preserves the original single `request_rejected` outcome.

The harness checks the latest two per-NPC samples, requires loaded/alive/valid ECS positions for both samples, pairs samples within 0.1 game-time units, limits latest sample wall age to 1 second, and applies the previous/current 3D distance (6m/5m) and separation-speed (0.5m/s) criteria. Its startup prefix requires three distinct game times spanning at least 2 wall seconds while the request file remains empty. A rejection ends only the matching request's wait. A rejected cancel admission does not block positive requests; later correlated effects for the cancel ID remain monitored. Positive completion requires same-ID accepted, native branch, queued-intent terminal, Say handoff, Agent event, and observed native continuation. The fixed positive cap is six plus one cancel-control input.

Independent local run: `/opt/homebrew/bin/python3.12 -B -m unittest -v test_run_talk_probe test_native_talk` from `tools/veloren_native_v0`; 25 tests passed (20 harness + 5 native CLI), exit 0. The corresponding console transcript is `python_tests_25.transcript.txt`; JSON emitted inside a test was line-wrapped for readability, so this is not a byte-for-byte stdout capture. Server-side focused tests: 5 passed, 0 failed, 10 filtered. The three build records retain the two command/setup failures separately from the later successful compile.

Capability boundary: native source declares structured travel, dialogue, trade, quest/hire, gather, report, and sentiment paths, but these are not all demonstrated in a saved run. The only affirmative saved native behavior in the older no-request baseline is ordinary NPC travel. Loaded NPC Gather currently reaches a `TODO: Implement` branch that pushes Dance; simulated Gather is a TODO/no-op. This NPC Gather path does not imply player harvesting is absent. Chat/Say is not evidence of recipient acceptance, relationship change, commitment, or learned knowledge.

Original small-log hashes and sizes, before local-path redaction in the published excerpts:

| Raw log | Bytes | SHA-256 |
|---|---:|---|
| `build.stderr` (malformed Cargo `--config`) | 384 | `dbc2654e680fe97aef678938b373682e0326d0c080027ef35aa55f5a71b62d6e` |
| `build-v2.stderr` (wrong working directory) | 124 | `fb3916283e3ef0a04877e396f6781feacb9e0f69cbd1efb82f0909e0cad49c6c` |
| `build-v3.stderr` (successful compile) | 409 | `9dd038034a836fe34e066fcea279fbe4b51a3cff66b31fa783280a66f3fe0ce8` |
| `server-tests.stdout` | 605 | `7416c81e74f34b2d8a481aa27f3bf1636a374a77aece6f6ec8b58019518e5bd2` |
| `server-tests.stderr` | 436 | `a2716e1e63655d44d8f14501b00633238fae45989f257ea27ff1b1f1a5531348` |

The excerpts redact local absolute paths only. No HTTP trace, credentials, binary, world database, game assets, or private review text is included. This file records source/harness/build evidence only; the native run and independent readback are recorded separately in `native_run_readback.md` and the raw run artifacts.
