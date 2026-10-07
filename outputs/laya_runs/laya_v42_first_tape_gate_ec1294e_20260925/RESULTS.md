# Exact-HEAD v4.2 first-tape gate — 2026-09-25

Status: **INCOMPLETE / FAIL-CLOSED**. No 64-actor run was started. Repository code was not changed.

## Frozen identity

- Repository: `/Users/2003singer/Workspace/Research/character-dynamics-laya-work`
- Branch / HEAD: `webgpt-sync` / `ec1294e09376d0843ca3a7829c9be63ebb632813`
- Final repository check: clean, still at the same HEAD.
- Executable: `build/character_dynamics_long_horizon`, SHA-256 `8971ef07d6d6787bf4f0199553929d7de408710ec482d6ecaa0446f13b440d27`
- Proxy: `Demo codex-generated/tools/laya_typed_proxy.py`, SHA-256 `885dcd23da80529f70e821a4bbfad991b34295195d320f81c6b110ad9fd33c32`
- Checkpoint: `convaiinnovations/laya-typed-decisions`, revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`; Laya `0.3.7`; protocol `laya-typed-v4`; prompt `character-dynamics-laya-typed-v4.2`.
- Runtime warned that checkpoint temperatures include invalid/out-of-range values; affected confidence is uncalibrated. `torch.backends.mps.is_available()` returned `False`; the proxy was requested with `--device mps`, which follows the checkpoint's CPU fallback path.
- World/profile/seed/flags: seed `1000`, policy seed `5000`, `balanced`, one day, `boundaries`; policy-only Laya. No soft gate, typed appraisal, or typed commitment intervention was enabled.

## No-history arm — complete

Fresh attempt: `no_history_fresh_01/`; its cassette began empty. Live and strict offline replay both exited successfully with the same frozen executable and `--laya-no-history`. The traces compare byte-for-byte.

- Live/replay trace SHA-256: `056c1ab70b99661e6c1ad71b91abf7c2ce7f17d68fcf6210629a4b4cff557ec4`
- Live cassette SHA-256: `70fa9502b76c021a3787615e41fa43d68049eaa13a049dad16e36787520d8c0d` (50 typed-choice rows)
- Empty replay-output cassette SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Trace: 60 lines (run + 58 boundaries + daily summary); simulated interval 480–1920, totaling 1,440 minutes.
- Request audit: all 50 clocks had matching known `clock.total_minutes` and formatted `clock.time`; H episodes, observed-event history, and 48-hour factual summary were empty. Each request had 10–13 distinct candidates, positive planned durations (range 1–480 minutes), exact candidate/probability key correspondence, normalized π, and a sampled action with positive π support. All token checks passed; smallest state margin 252 tokens and smallest question-head margin 20 tokens.
- Day summary: 140 study minutes, 2.5766/8.3974 task effort, 0 task completions, 427 sleep minutes, 240 rest minutes, two meal actions, five bathroom actions, 128 idle minutes. Twelve actions were selected; mean normalized policy entropy was 0.9519; 41 of 49 adjacent policy decisions switched actions; no runtime rejections.
- Same-world Rule reference in the checkpoint: 595 study minutes, 419 sleep minutes, 210 rest minutes, 8.3974 task effort and one completion. Descriptive single-tape difference only.
- These observations show a broad, non-single-action policy distribution in this tape; they do not establish that the resulting behavior is informative about, or valid for, human psychology. Low task progress and only two meal actions are notable descriptive outcomes, not predeclared failure thresholds.

## History arm — stopped at the first budget failure

Fresh attempt: `history_fresh_01/`; its live cassette began empty. The executable was invoked with the same settings but without `--laya-no-history`. It exited with status 1 on the next Laya request:

```text
long_horizon: Laya typed proxy rejected request: cannot verify Laya input token budget: Laya state exceeds model input budget: state_tokens=789, state_budget=784, max_len=1024
```

This was request 11, before inference and before that request could be appended to the cassette. The valid prefix contains requests 1–10 only; all ten have clock agreement, known observations, v4.2 identity, and own-action/O-event history fields. Their state tokens rise from 525 to 742; the last saved input was 982 tokens. The oversized request was correctly rejected before being written. No retry was made, so history live/replay and the paired history comparison remain incomplete.

- Partial trace SHA-256: `7b00bf995c1ed0a0179aee0d9887cfa3716b1c67aa784d40448f4bc574642cbf` (13 valid JSON lines)
- Partial cassette SHA-256: `f384c10a791315cdbec6ca62e7f569531a3f24ac9c807ae4cc1509194074c85d` (10 valid typed-choice rows)

## Commands

Proxy live (each arm used a separate cassette and the same loopback port after the prior proxy was stopped):

```sh
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '<attempt>/live-cassette.jsonl' --device mps --port 8744
```

No-history live:

```sh
'<artifact-root>/build/character_dynamics_long_horizon' 1000 5000 1 balanced '<artifact-root>/no_history_fresh_01/live-trace.jsonl' boundaries --laya-port 8744 --laya-no-history
```

No-history strict replay used `--cassette '<attempt>/replay-cassette.jsonl' --replay '<attempt>/live-cassette.jsonl' --device cpu --port 8745`, then the same executable command with output `replay-trace.jsonl` and port `8745`.

History live:

```sh
'<artifact-root>/build/character_dynamics_long_horizon' 1000 5000 1 balanced '<artifact-root>/history_fresh_01/live-trace.jsonl' boundaries --laya-port 8744
```

All partial and completed source artifacts, including the original `no_history/live-*` partial and Rule trace, remain intact. No repository files were edited, and no commit or push was made.
