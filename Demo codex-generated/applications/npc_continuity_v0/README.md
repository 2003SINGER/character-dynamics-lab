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

## Remaining stage 2 work

Actual history LLM selection, matched multi-condition input/gate audit, player-generated World input and a unified watchable/player-facing presentation are still absent. This CLI is not interactive and does not implement a fake player button or use cassette/mock choices as live model evidence. Local Mac Qwen3-4B assets were found, but this slice did not start a model or make inference calls; that small checkpoint is not automatically a strong LLM baseline.

Research status and the stop-after-stage-3 decision are owned by [the research audit](../../../00_研究设计/研究重建审计_2026-10-06.md#玩家目标的第一个可比较问题). Do not add a new psychological mechanism because this contract passes.
