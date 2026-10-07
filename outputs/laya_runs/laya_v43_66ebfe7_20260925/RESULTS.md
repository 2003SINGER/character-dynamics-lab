# Laya v4.3 exact-HEAD one-day same-world gate — 2026-09-25

## Decision

The requested one-day smoke completed for Rule, Laya without actor history, and Laya with actor history. **Engineering gate: PASS** — all request, budget, clock, history-contract, and strict-replay checks completed successfully. **Behavior gate: NOT PASSED for scale-up** — one seed produced 1,149 minutes of sleep in the no-history arm, and the first request's raw π changed sharply when actor history was supplied. The history arm had ordinary-range sleep but did not complete its task. These observations do not establish general behavior or psychological validity.

All 52 raw policy requests passed the per-request clock, candidate/probability, duration, token-fit, history-window, result-type, and information-boundary checks in `REQUEST_AUDIT.tsv`. Both Laya live traces were reproduced byte-for-byte by strict offline replay. There was no over-budget request, proxy inference error, runtime rejection, or incomplete trace. Stop after this one-day stage; do not automatically advance to 64 actors or seven days.

## Frozen source and execution identity

- Repository: `/Users/2003singer/Workspace/Research/character-dynamics-laya-work`
- Branch: `webgpt-sync`; HEAD: `66ebfe72dc3fd5987a040adb61bec5b5a9a1b646`; worktree clean before and after.
- Independent source check: exact-HEAD CI `runtime-regression` run `#36132250319` succeeded (reported by the parent agent).
- Artifact root: `/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/`. It was new and separate from the repository. The v4.2 failed root and all earlier runs/cassettes were left untouched.
- Fresh Release executable: `build/character_dynamics_long_horizon`; SHA-256 `8971ef07d6d6787bf4f0199553929d7de408710ec482d6ecaa0446f13b440d27`.
- Proxy source: `Demo codex-generated/tools/laya_typed_proxy.py`; SHA-256 `0b6c9b8c4e05119d13b0544be9890580eff7aba1d621387a08a72916f8fab74e`.
- Model: `convaiinnovations/laya-typed-decisions`, checkpoint revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`; Laya `0.3.7`; protocol `laya-typed-v4`; prompt `character-dynamics-laya-typed-v4.3`.
- Checkpoint file hashes: `model.safetensors` `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`; `tokenizer.json` `6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30`; `tokenizer_config.json` `08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1`.
- Runtime: macOS arm64, Python 3.12.14, PyTorch 2.14.0, CMake 4.4.3, AppleClang 21.0.0. MPS was unavailable; each live bridge reported fallback to CPU. Laya also warned that a checkpoint temperature (`choice:11+`) is outside its supported range and was clipped to `0.5`; confidence associated with affected entries is uncalibrated.
- All three arms used scenario seed `1000`, policy seed `5000`, profile `balanced`, one day, and `boundaries`, with the same fresh executable and initial world/state. The Laya runs were policy-only: no `--laya-soft-gate`, typed appraisal, or typed commitment mode.

Build command:

Exact executable and proxy commands with the actual paths and ports are preserved in `COMMANDS.md`.

```sh
cmake -S 'character-dynamics-laya-work/Demo codex-generated' \
  -B '_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build' \
  -DCMAKE_BUILD_TYPE=Release \
  -DCHARACTER_DYNAMICS_GIT_REVISION=66ebfe72dc3fd5987a040adb61bec5b5a9a1b646
cmake --build '_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build' \
  --target character_dynamics_long_horizon -j4
```

Live and strict replay command shape (the arm directories and ports differ; replay uses `--replay <live-cassette>` and a new empty replay-output cassette):

```sh
python3 'Demo codex-generated/tools/laya_typed_proxy.py' \
  --cassette '<arm>/live-cassette.jsonl' --device mps --port <port>
'<artifact-root>/build/character_dynamics_long_horizon' \
  1000 5000 1 balanced '<arm>/live-trace.jsonl' boundaries \
  --laya-port <port> [--laya-no-history]

python3 'Demo codex-generated/tools/laya_typed_proxy.py' \
  --cassette '<arm>/replay-cassette.jsonl' --replay '<arm>/live-cassette.jsonl' \
  --device cpu --port <replay-port>
'<artifact-root>/build/character_dynamics_long_horizon' \
  1000 5000 1 balanced '<arm>/replay-trace.jsonl' boundaries \
  --laya-port <replay-port> [--laya-no-history]
```

The sandbox denied local loopback bind/connect; the same commands were run with the exact loopback actions allowed. Each arm used its own live cassette, and each replay loaded only that arm's v4.3 cassette. The raw requests include the typed result distribution; the C++ runtime separately samples π with its seeded RNG. Do not treat `raw_answer.choice` as the action executed by the runtime.

## Same-world outcomes

Minutes below are measured from the trace's actual `running_action_before` intervals; they agree with the daily summary. The day spans total minute 480 through 1920 (1,440 minutes).

| Arm | Sleep | Rest | Study | Leisure | Idle | Bodily | Task effort / target | Completed | Policy decisions | Runtime rejections |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rule | 419 | 210 | 595 | — | — | — | 8.397 / 8.397 | 1 | 35 | 0 |
| Laya, no history | **1,149** | 60 | 35 | 70 | 41 | 85 | 0.234 / 8.397 | 0 | 17 | 0 |
| Laya, history | 360 | 300 | 525 | 119 | 51 | 85 | 7.374 / 8.397 | 0 | 35 | 0 |

In the no-history arm, sleep accounts for 79.8% of the day. It came from four actual sleep intervals: 560–926 (366 minutes), 996–1476 (480), 1511–1691 (180), and 1797–1920 (123). The 740-minute boundary reselected the still-running sleep and retained its 560 start time; it is a continuation, not a separate sleep interval. At the 996, 1511, and 1797 policy requests, raw π assigned sleep probabilities `0.0615`, `0.0449`, and `0.0924`, respectively, yet the seeded runtime selected sleep. This is a severe trajectory anomaly for this seed; it does not show a global Laya preference for sleep.

The history arm used 12 distinct selected actions and spent 360 minutes asleep, 300 resting, and 525 studying. Its sleep is close to Rule's 419 minutes, while its 660 combined sleep/rest minutes are close to Rule's 629. It made no task completion despite reaching effort 7.374/8.397; Rule completed the task. It also reached maximum observed fatigue `1.0` and bathroom urge `0.866` during the day. No arm had a runtime rejection. These are descriptive outcomes for this single seeded tape, not predeclared general behavior thresholds.

The history contrast is highly input-sensitive. At the first request (`t=490`), all request fields except `recent_history` and `recent_factual_summary` were identical across the two Laya arms, including state, O observation, and all 13 candidates. The no-history raw π for `idle` was `0.1031`; with history it was `0.6776`. The history request added one completed 10-minute idle episode and two observed O deltas (`room.temperature_celsius`, `outside.weather`). This large change is not evidence that the model correctly interpreted sleep history. Across the arms the model's own raw `choice` differed from the runtime-sampled action in 14/17 no-history requests and 22/35 history requests; distributions remain uncalibrated.

## Request, clock, candidate, token, and H1/H2 audit

`REQUEST_AUDIT.tsv` contains one row per each of the 17 no-history and 35 history requests, including every O-hard-admissible candidate with target and planned minutes, the complete raw probability map, model raw choice, actual runtime sample, clock, and token margins. `audit.json` records the check result; `audit_gate.py` is the repeatable verifier.

- Clock: every request had `clock.total_minutes` and `clock.time` marked known (`k`) and exactly synchronized to its request timestamp.
- Candidate surface: 1–13 distinct hard-admissible candidates per request; planned durations were positive and ranged from 1 to 480 minutes. One-candidate requests were bodily-need gates (bathroom or meal), not Rule preference filtering. Raw π keys exactly matched the candidate action set; rounded sums ranged `0.9999–1.0002`; all values were finite and within `[0,1]`.
- Information boundary: requests carried only the documented state, personality, O observations, actor-history fields and candidate action/target/duration. Candidate rows had no activation, rule probability, reason, or hidden World data. Model result type was `choice` for every cassette row; no appraisal, commitment, or soft-gate rows appeared. No-history H1/H2 summaries were empty throughout.
- Token fit across all 52 requests: minimum state margin `33` tokens, minimum complete-input margin `33`, and minimum complete question-head margin `20`. No request exceeded the actual tokenizer/sequence-builder budgets. The history arm used at most 16 H1 episodes and 11 H2 action types; observed O events stayed within the policy's two-event/12-hour slice. Episode end-times, status, planned/actual duration and H2 totals/last-occurrence ages were consistent, including the latest sleep summary. Rejected episodes (if any) must have zero actual duration; this tape had no runtime rejection.
- The README's two-hour observed-event causal slice refers to typed appraisal/commitment requests, which were not enabled here. Policy requests use the two-event, 12-hour slice; the retained older event at `t=935` is within that policy contract.

## Replay and output hashes

| Output | Live SHA-256 | Strict replay SHA-256 | Byte-identical |
|---|---|---|---|
| No-history trace (39 lines) | `ad871a5fab19629bc3e414e59cbd726c47d007e3299fd8c704b72c8f8f735e75` | same | yes |
| History trace (48 lines) | `96e7bab3afedda43ff9b6caa2dec50ddf4aaa19b50a1cfa81b280301fbe46f31` | same | yes |
| Rule trace (48 lines) | `c77e13c4f70d3eb6b69f04e11076140ebc4ea4fd782e4a7bde5543badf70ce92` | n/a | n/a |

Live cassette SHA-256: no-history `6a0593fe9bfe8b2e23f0e5fd96c527dac8378045467fbe330c6dcbbe7b49dc4d` (17 rows); history `21babae4eda7460e114aa474cdc0b0d93be3d3d34b70e84dc04d72f2cb34f52a` (35 rows). Replay mode produced no output cassette rows; replay still consumed only its corresponding live cassette and reproduced the trace exactly.

## Stop condition and scope

This fulfills the requested one-day smoke. The severe no-history oversleep and the large first-request π shift under history make the result a scale-gate no-go. Stop here: no 64-actor run, seven-day run, code change, commit, or push was made. All source files and prior run/cassette roots remain untouched.
