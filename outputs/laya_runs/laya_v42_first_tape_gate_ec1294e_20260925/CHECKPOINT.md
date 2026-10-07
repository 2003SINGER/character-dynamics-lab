# First-tape v4.2 gate checkpoint

Status: INCOMPLETE; stop requested by parent while usage was low. This is not a gate pass or a behavioral result. No 64-actor run was started.

## Frozen source and artifacts

- Repo: `/Users/2003singer/Workspace/Research/character-dynamics-laya-work`, branch `webgpt-sync`, exact HEAD `ec1294e09376d0843ca3a7829c9be63ebb632813`; repo was clean at the check after stopping.
- Fresh Release executable: `build/character_dynamics_long_horizon`, SHA-256 `8971ef07d6d6787bf4f0199553929d7de408710ec482d6ecaa0446f13b440d27`. It was built from this HEAD, outside the repo, with `CHARACTER_DYNAMICS_GIT_REVISION` set to the full hash.
- Proxy source: `Demo codex-generated/tools/laya_typed_proxy.py`, SHA-256 `885dcd23da80529f70e821a4bbfad991b34295195d320f81c6b110ad9fd33c32`.
- Checkpoint: `convaiinnovations/laya-typed-decisions`, revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`; local `model.safetensors` SHA-256 `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`. Tokenizer `tokenizer.json` SHA-256 `6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30`; `tokenizer_config.json` SHA-256 `08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1`.
- Artifact root: `/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/`.

## Completed work

- Rule arm used the same direct executable, seed `1000`, policy seed `5000`, `balanced`, one day, boundaries enabled (runtime begins at total minute 480 / 08:00). Trace: `rule/trace.jsonl`, 48 lines, SHA-256 `c77e13c4f70d3eb6b69f04e11076140ebc4ea4fd782e4a7bde5543badf70ce92`.
- The actual local checkpoint loaded. Its library warned that bundled temperatures include invalid/out-of-range values, so confidence for affected entries is uncalibrated; MPS was unavailable, so the library fell back to CPU.
- The first no-history live arm was started with its own initially absent cassette. It reached ten raw policy cassette rows and eight trace lines before being stopped. The trace ends mid-JSON and is incomplete; do not parse it as a finished run. Partial trace SHA-256 `2b50301b5a7a4238fcd49e36600f872c4346fe5b02230944b5090da44cc669bf`; partial cassette SHA-256 `0edf1b3c5445df89d4241b67336fa1d503cf5836297643a6b2f73ad8bea2feb1`.
- The ten cassette requests contain raw typed choices/probabilities and tokenizer audit fields. The last complete logged request has state tokens 507/784, complete input 747/1024, and complete question head 118/138. The observed first eight boundaries include `rest_at_bed`, bathroom trips, study, and idle; this partial segment is not enough to assess day-level behavior.
- No-history replay, history live/replay, cassette equality, meal/task/need analysis, or final trace audit has been completed. No valid same-command/version Rule baseline was found; the earlier seed-17 six-hour SHA and prior pre-final attempts are not comparable and were not used.

## Commands and stop cause

Build command:

```sh
cmake -S 'Demo codex-generated' -B '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/build' -DCMAKE_BUILD_TYPE=Release -DCHARACTER_DYNAMICS_GIT_REVISION=ec1294e09376d0843ca3a7829c9be63ebb632813
cmake --build '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/build' --target character_dynamics_long_horizon -j4
```

Rule command:

```sh
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/rule/trace.jsonl' boundaries
```

No-history proxy and run commands (the latter was interrupted by parent instruction):

```sh
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/no_history/live-cassette.jsonl' --device mps --port 8744
'/Users/2003singer/Workspace/Research/_character-dynamics-laya-runs/laya_v42_first_tape_gate_ec1294e_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v42_first_tape_gate_ec1294e_20260925/no_history/live-trace.jsonl' boundaries --laya-port 8744 --laya-no-history
```

The first proxy start was denied by the sandbox on loopback bind (`PermissionError: Operation not permitted`). The exact proxy command was then allowed via escalation. The subsequent Laya executable command was also run through escalation. Stop was requested before replay or further model calls because account usage was nearly exhausted. Both proxy and executable were interrupted; the proxy has been shut down.

## Safe continuation

Preserve this partial attempt unchanged. For the no-history arm, create a new uniquely named attempt directory and a new empty cassette; restart from the beginning with the same executable, seeds, profile, and flags. Do not append to, replay, or overwrite the partial cassette/trace. Then perform strict offline replay from that completed attempt's cassette and require byte-identical trace. Give the history arm its own new directory, empty live cassette, and proxy; run without `--laya-no-history`, then strictly replay and compare bytes. Only after both Laya arm replays and all request/time/budget/behavior checks pass should the gate be considered complete. Keep Rule as the already completed same-world reference. Leave the older failed `93e454f` run and the invalid v1/v2 cassettes untouched.
