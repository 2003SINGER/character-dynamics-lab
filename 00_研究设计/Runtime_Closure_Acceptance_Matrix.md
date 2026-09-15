# Continuous Runtime v1 Closure 验收矩阵

当前状态：**NOT_CLOSED**。上一版 CLOSED 已被 end-to-end owner 审计撤回；本矩阵只记录可由仓库现有测试支持的边界。

| Gate | 当前 | 证据/说明 |
|---|---|---|
| A1 canonical boundary/action owner | PASS | vertical fixture 已完全改走 `ContinuousRuntime::execute_next_boundary` |
| A2 boundary order | PASS | owner 现按 continuous → W/event → completion/invalidation → O → X → S impulse → gate |
| B1 authoritative clock | PASS | adapter 强制 W time == scheduler clock；reference/vertical smoke |
| B2 automatic W boundary | PASS | owner 每步续订；scheduler dedupe |
| B3 earliest event + deadline | PASS | closure acceptance smoke 覆盖 deadline 早于 message |
| B4 bounded threshold opportunity | PASS | `max_runtime_step_minutes` + threshold detection；crossing schedules invalidation and next gate cycle |
| C1 start validation | PASS | `submit_action_intent` 唯一 owner API；typed provenance |
| C2/C3 completion provenance | PASS | actual elapsed 与 settlement clock advance 分离 |
| C4 invalidation | PASS | `invalidate_running_action` → typed plan-invalidated outcome smoke |
| D actor-local perception | PASS (current channels) | `World + InformationAccess` projector 覆盖 message/weather/alarm/temperature/reminder/deadline/evening；hidden phone/weather 不写入 O |
| E typed rejection | PASS | scheduler rejection event 携带 accepted/action/target/failure/actual_elapsed/provenance typed payload，并在下一 transition 进入 O |
| F continuous/impulse | PASS (v1 adapter) | `advance_continuous_state` 与 `apply_appraisal_impulse` 分离；chunk equivalence smoke |
| G decision gate | PASS | weak/hidden event closed；completion/invalidation/rejection open；threshold crossing triggers replacement/reconsideration cycle |
| H docs/regression | PASS | 17/17 CTest、reference `--verify` 通过；Vision/TODO/Runtime 文档与矩阵已同步 |

## Executable evidence

当前 CTest：基础 6 项加 11 个 closure gate 名称（均指向确定性的 acceptance binary），共 17/17 PASS。

`CONTINUOUS_RUNTIME_V1 = NOT_CLOSED`。π selection、exactly-once consumption 与 threshold reconsideration 已有 dedicated assertions；最终 CLOSED 仍需独立审计确认。
