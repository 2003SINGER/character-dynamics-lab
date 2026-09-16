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
| F continuous/impulse | PASS (v1 adapter) | `advance_continuous_state` 与 `apply_appraisal_impulse` 分离；chunk equivalence smoke |
| G decision gate | PASS | weak/hidden event closed；completion/invalidation/rejection open；threshold crossing evaluates policy immediately and preserves the running action unless an explicit interruption occurs |
| H docs/regression | PASS | 基础、closure、trace、mechanism fixture registrations 均通过；reference `--verify`、repo health 与 CI 配置通过 |

## Executable evidence

当前 CTest 包含基础、closure、trace、mechanism fixture、channel coverage，以及以 `runtime_case_smoke --case <name>` 逐 case 执行的 gate-labelled registrations。

`RUNTIME_V1_CLOSURE_AND_PROJECT_STABILIZATION = CLOSED / FROZEN`。π selection、completion/rejection exactly-once、threshold continue/replace、physical preemption distinction均有可执行证据。后续不再扩 Runtime；下一条 active research work 为 M2 candidate-set admission。
# Responsibility split (2026-09-16)

Runtime Closure 只保证正确时间调用 model continuous/appraisal/policy hooks、O/W ownership、gate ordering、W validation、hidden-W 不泄漏和 model identity trace；不保证 fatigue rate、commitment law、π 权重或 hunger/mood coupling 合理。新增 Gate I：Dynamics-model isolation（显式 model 选择、Engine 不链接 Demo、Reference parity frozen、Demo tuning 不改变 Reference fixtures）。
