# NPC continuity application v0 — stage 2 contract slice

Status: **IMPLEMENTATION_VERIFIED / DEVELOPMENT**, not stage 2 complete, player validation, a new dynamics mechanism, or an independent milestone closure.

This application uses the frozen `ContinuousRuntime` and delegates X/S updates to `ReferenceRuleDynamicsV0`. It does **not** call the reference/Demo decision scorer. The application rebuilds O-known, hard-admissible candidates and assigns a uniform placeholder distribution; `UtilityPolicyV0` independently scores them. A new known `room.alarm=ringing` delta gives every future policy the same reconsideration opportunity. It does not physically preempt an action or select the answer.

## Baseline definition

The engineering reference is David “Rez” Graham, *An Introduction to Utility Theory*, Game AI Pro (2013), §§9.2/9.4–9.7, pp.113–122; [official chapter](https://www.gameaipro.com/GameAIPro/GameAIPro_Chapter09_An_Introduction_to_Utility_Theory.pdf), local `01_文献/PDF/2013_Utility_Theory_Introduction_GameAIPro.pdf`. Luna and the parent read the 14-page chapter. This is an industry chapter, not a peer-reviewed player experiment or a reproduction of its combat demo.

For hard-admissible actions, use a neutral floor of `0.05`; known active coursework adds `0.60 * clamp(1-effort/target,0,1)` to coursework actions (fallback `0.60` when progress is unknown). A known ringing alarm adds `0.90` to turning it off. The current running action adds `0.14`; the last accepted actor episode adds `0.08` to the same action. Choose argmax; ties follow the existing candidate enumeration order. The scores are author-defined development settings, not learned coefficients, outcome-calibrated expected utilities or psychological laws. No Demo coefficient was changed.

The continuation contract deliberately uses a higher running inertia (`2.0`) to demonstrate that the **same gate can retain the original RunningAction/progress**. This is not a tuned behavior result. Utility ignores S/P; body needs, competing long-term goals and a full autonomous daily routine are not scored in this slice. Do not label it a comprehensive or validated strong utility baseline.

## Actual fixture and output

`World(0)`, existing legacy tape, start `08:45`, policy seed `17`, natural coursework target `8.0`. Initial StudyFocused is explicit `scenario_setup`, submitted through World validation, **not an autonomous policy goal-init result**. At `09:00` the real World alarm enters O and opens reconsideration; the default utility selects TurnOffAlarm. At `09:01` it selects StudyAtComputer. Later completion feedback reaches O; coursework finishes at `14:51`, and the next choice is Idle. The trace stops there; it does not count the newly selected Idle as already executed time.

The original 15 minutes of StudyFocused are interrupted without partial task-effort settlement, under the existing frozen execution semantics. This is recorded action cost, not task progress or an invented Runtime fix.

Parent run: `outputs/npc_continuity_v0/stage2_contract_20261006_xCwPkM/utility_alarm.jsonl` (local, ignored), 17/17 JSONL records parse. Compiled revision `987904d` identifies the pre-code-commit checkout; header explicitly does not certify a clean build. Source hashes in the same run directory identify the inspected implementation. This single deterministic fixture proves an execution/data contract, not general behavior quality. Six simulated hours of uninterrupted work particularly must not be presented as a natural daily-life result.

Trace records clock, RunningAction before/after with elapsed/planned time, gate reasons, policy evaluation, selected target, O deltas, candidate signature, actual selection-time score provenance and task settlement. It includes W debug fields and condition identities: **not a player-blind payload**. Scores are not recomputed after policy replacement changes history.

## Reproduce from repository root

```sh
cmake -S "Demo codex-generated" -B "Demo codex-generated/build/npc-continuity-v0" -G Ninja
cmake --build "Demo codex-generated/build/npc-continuity-v0" --parallel 4
ctest --test-dir "Demo codex-generated/build/npc-continuity-v0" -R npc_continuity --output-on-failure
"Demo codex-generated/build/npc-continuity-v0/character_dynamics_npc_continuity_harness" alarm
```

Contract coverage: candidate surface unaffected by S/P; no hidden-W input to candidate/scoring/reconsideration functions; known constraints remove candidates; visible alarm permits policy replacement; observed completion does not force resume; scheduler-backed same-intent reconsideration retains progress. The hidden-W case is **consumer-level with unchanged O**, not a complete hidden/visible paired Runtime experiment. The CLI additionally checks alarm→replacement→coursework→completion ordering.

Parent verification also built every target in this build directory, ran the full CTest suite (**51/51 passed**, including frozen-source parity), and ran `character_dynamics_reference --verify` successfully. Existing socket tests required loopback permission outside the execution sandbox. These are regression/contract checks, not 51 independent NPC behavior experiments or live LLM inference.

## History LLM interface — actual local probe

`HistoryLlmPolicyV0` now overrides the real Runtime history entry point. It serializes O-known/stale facts, a **known numeric current O clock**, the complete supplied actor-visible ledger (Runtime already prunes it to 48h), RunningAction and the same application hard candidates. It does not send S/P, hidden W or utility scores. Candidates include targets, nominal duration and remaining duration/progress retention for a continuing intent. Ambiguous multiple targets for one ActionType are rejected because the current PolicySelection cannot express that choice. Prompt principles concern goals/events/continuation, not an alarm answer.

The application-only Python worker uses standard-library JSON/HTTP/SHA256, fixed argv via `posix_spawn`, no shell, no system proxy, and loopback-only HTTP without redirects. It journals canonical request hashes, responses, API usage, latency and errors. Strict candidate-ID JSON schema and parsing remain mandatory; no JSON repair, automatic retry or utility fallback. Transport is currently POSIX (Mac/Linux), not verified on Windows.

Parent artifacts: `outputs/npc_continuity_v0/stage2_live_llm_20261006_4htWYT/` (local, ignored). Qwen3-4B Q4_K_M SHA256 `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`; llama-server build10809 / `5266f24da`, context 16384, one slot, no context shift, temperature 0, thinking disabled. These settings do not guarantee cross-platform determinism.

The first v0 call failed: the model returned bare `c5`, strict parsing rejected it, and no policy intent executed. Its raw trace/call journal remain separate. The installed [backend parser](https://github.com/ggml-org/llama.cpp/blob/5266f24da/tools/server/server-common.cpp#L1091-L1104) reads `response_format.json_schema.schema`; the initial flat `response_format.schema` did not supply that schema. v1 uses the actual nested contract and an explicit JSON-format instruction; tests guard against the old shape.

v1 `trace_v1.jsonl` / `live_v1/history_llm_calls.jsonl` contain **3 real decisions over exactly 90 simulated minutes**, ending at the horizon, not task completion. At 09:00 the LLM chose StudyHalfhearted; at 09:35 and 10:10 it chose StudyAtComputer. It did not turn off the alarm. Parent checked canonical hashes, known text/numeric clock against each boundary, candidate ID→action/target→World validation, durations, temporal increments and growing history. All 3 selections were accepted. API totals: 4963 prompt tokens + 24 completion tokens; summed HTTP wall time 20.693s (not total application runtime). Total live calls including the failed v0 call: 4. The service was stopped after the probe. This difference is a development observation, **not a paired effect, a pathology diagnosis or a strong LLM baseline result**.

Reproduce with an already running verified loopback model and a **nonexistent** child run directory (no live-model CTest):

```sh
"Demo codex-generated/build/npc-continuity-v0/character_dynamics_npc_history_llm_harness" --run-directory outputs/npc_continuity_v0/NEW_RUN --model-id npc-qwen3-4b-q4km --max-calls 7
```

The two new CTest contracts distinguish fake transport/HTTP responses from a real worker connection-failure check (port 1, no model inference). They test history, current-clock admission, hard candidate mapping, no S/P scores, same-action remaining time, ambiguous targets, strict response failures/no retry and journal hashes/usage. They are not human or behavioral validation.

After the final v1 protocol and trace edits, parent rebuilt all targets and reran the entire suite: **53/53 CTest passed**; Reference `--verify` and repository health also passed (three existing health warnings remain). Live inference is the separate probe above, not part of CTest. `source_sha256.txt` in the run root identifies the inspected pre-commit source bytes; the compiled revision remains `7ace737`, not a claim that the new code was already committed at execution time.

## Remaining stage 2 work

Matched multi-condition input/gate audits, adequate baseline breadth and unified watchable/player-facing presentation remain. The existing Player View toggle still exposes O/S/π; it is not a blind participant interface. World only supplies its prearranged event tape: no player-event injection API was found. Do not fake interaction by writing directly into O or mutating the player display. A true player input seam requires a separate scoped interface decision; no Runtime/World source was changed here. This CLI is not interactive. The small model probe does not automatically establish a strong LLM baseline, and the minimal utility is still a single-task contract.

Research status and the stop-after-stage-3 decision are owned by [the research audit](../../../00_研究设计/研究重建审计_2026-10-06.md#玩家目标的第一个可比较问题). Do not add a new psychological mechanism because this contract passes.
