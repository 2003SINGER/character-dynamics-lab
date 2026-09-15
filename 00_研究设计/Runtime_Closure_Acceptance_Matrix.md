# Continuous Runtime v1 Closure 验收矩阵

当前状态：**NOT_CLOSED**。本矩阵只记录可由仓库现有测试支持的边界，不把尚未实现的语义写成 PASS。

| Gate | 当前 | 证据/说明 |
|---|---|---|
| A1 canonical boundary/action owner | PASS | vertical fixture 已完全改走 `ContinuousRuntime::execute_next_boundary`；低层调用仅保留在 scheduler unit smoke |
| A2 boundary order | PASS | owner API 固定 continuous → completion/invalidation → O → X → S impulse → gate |
| B1 authoritative clock | PASS | adapter 强制 W time == scheduler clock；reference/vertical smoke |
| B2 automatic W boundary | PASS | owner 每步续订；scheduler dedupe |
| B3 earliest event + deadline | PASS | closure acceptance smoke 覆盖 deadline 早于 message |
| B4 bounded threshold opportunity | PASS | `max_runtime_step_minutes` + `NeedThresholdCrossed` smoke |
| C1 start validation | PASS | `submit_action_intent` 唯一 owner API；typed provenance |
| C2/C3 completion provenance | PASS | actual elapsed 与 settlement clock advance 分离 |
| C4 invalidation | PASS | `invalidate_running_action` → typed plan-invalidated outcome smoke |
| D actor-local perception | PARTIAL | weather curtain、phone visibility 已守住；alarm/temperature/channel 仍需逐类验收 |
| E typed rejection | PASS (v1 payload) | scheduler rejection event 携带 `RuntimeRejection` typed payload，并在下一 transition 进入 O；仍未建模完整 WorldOutcome 对象跨边界序列化 |
| F continuous/impulse | PASS (v1 adapter) | `advance_continuous_state` 与 `apply_appraisal_impulse` 分离；chunk equivalence smoke |
| G decision gate | PARTIAL | weak event continue、threshold opportunity 已有；完整 hidden-event gate matrix 待补 |
| H docs/regression | PARTIAL | 6/6 CTest 通过，矩阵与顶层 Vision/TODO 已同步；仍需逐项独立 acceptance binaries 与最终审计 |

## Executable evidence

当前 CTest：`character_dynamics_reference_smoke`、`core_experiment_smoke`、`runtime_scheduler_smoke`、`runtime_vertical_slice_smoke`、`runtime_closure_acceptance_smoke`、`replay_core_version`，共 6/6 PASS。

在 A1、D、E、G、H 的 PARTIAL 项全部转为 PASS 前，不得写 `CONTINUOUS_RUNTIME_V1 = CLOSED`，也不得迁移 Deadline/Phone/Commitment fixture。
