# Continuous Runtime v1 Closure 验收矩阵

当前状态：**CLOSED / FROZEN**（独立复核完成）。本矩阵记录 end-to-end owner 审计后的可执行证据；研究心理机制有效性仍不由该工程门槛推出。

| Gate | 当前 | 证据/说明 |
|---|---|---|
| A1 canonical boundary/action owner | PASS | vertical fixture 已完全改走 `ContinuousRuntime::execute_next_boundary` |
| A2 boundary order | PASS | owner 现按 continuous → W/event → completion/invalidation → O → X → S impulse → gate |
| B1 authoritative clock | PASS | adapter 强制 W time == scheduler clock；reference/vertical smoke |
| B2 automatic W boundary | PASS | owner 每步续订；scheduler dedupe |
| B3 earliest event + deadline | PASS | closure acceptance smoke 覆盖 deadline 早于 message |
| B4 bounded threshold opportunity | PASS | `max_runtime_step_minutes` + threshold detection；crossing opens an immediate reconsideration gate without resetting the running action |
| C1 start validation | PASS | `submit_action_intent` 唯一 owner API；typed provenance |
| C2/C3 completion provenance | PASS | actual elapsed 与 settlement clock advance 分离 |
| C4 invalidation | PASS | `invalidate_running_action` → typed plan-invalidated outcome smoke |
| D actor-local perception | PASS (current channels) | `World + InformationAccess` projector 覆盖 message/weather/alarm/temperature/reminder/deadline/evening；hidden phone/weather 不写入 O |
| E typed rejection | PASS | scheduler rejection event 携带 accepted/action/target/failure/actual_elapsed/provenance typed payload，并在下一 transition 进入 O |
| F continuous/impulse | PASS | Kernel 在正确 boundary 调用显式 Dynamics Model 的 continuous/appraisal/impulse hooks，并隔离 Δt、O、X、S 数据边界；chunk equivalence smoke；具体 state law 不属于 Kernel 验收 |
| G decision gate | PASS | Kernel 依据 typed reason 控制 gate；weak/hidden event closed，completion/invalidation/rejection open；threshold crossing 立即触发 model policy reconsideration，并保留 running action，除非模型明确产生 interruption |
| H docs/regression | PASS | 基础、closure、trace、mechanism fixture registrations 均通过；reference `--verify`、repo health 与 CI 配置通过 |
| I dynamics-model isolation | PASS | 调用方显式选择模型；Kernel 不链接 Demo 行为源；Reference parity 对齐冻结 commit；Demo 调参不改变 Reference fixtures |

## Executable evidence

当前 CTest 包含基础、closure、trace、mechanism fixture、channel coverage，以及以 `runtime_case_smoke --case <name>` 逐 case 执行的 gate-labelled registrations。

`RUNTIME_V1_CLOSURE_AND_PROJECT_STABILIZATION = CLOSED / FROZEN`。π selection、completion/rejection exactly-once、threshold continue/replace、physical preemption distinction均有可执行证据。后续不再扩 Runtime；下一条 active research work 为 M2 candidate-set admission。
本矩阵只验 Kernel 的执行契约与模型边界：不保证 fatigue rate、commitment law、π 权重或 hunger/mood coupling 的心理学合理性。Reference、Theory-S 与 Demo Living 的证据地位由各自研究/应用文档单独说明。
