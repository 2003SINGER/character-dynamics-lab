# TODO｜active research queue

更新时间：2026-09-07。此页只保留 ID、状态、下一动作、验收条件和链接；历史论证与已完成批次见[TODO 原版快照](归档/2026-09-07_TODO瘦身/TODO_原版_2026-09-07.md)。

## ACTIVE

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| M1 | **已完成（pre-training gate）** | 已冻结 anchor 语义边界、sign-violation 协议、decision-step 时间尺度、neutral 初始化与 trajectory reset；不再扩展机制 | [M1 冻结决策](Theory-S_M1冻结决策_2026-09-07.md)、[Theory-S v2](../02_实验/Theory_S_v2/README.md)；不得把候选实现写成心理学验证 |
| M2 | 进行中 | 完善 SceneSnapshot → affordance → generated `A^O` 的最小 ontology 与实例绑定 | 生成不读 source `A*`；source support 仅 post-hoc 诊断；[Mechanism Sanity v1](../02_实验/Mechanism_Sanity_v1/README.md) |
| M3 | 进行中 | 按 owner audit 完成数据集语义准入，而非继续扩张 routing 表 | [capability matrix](../02_实验/Theory_S_v2/capability_matrix.md)；proxy/telemetry 不升级为 A* |
| T0d | 进行中 | 完成 OPeRA semantic admission；冻结 user/session-disjoint split 与第一轮标签口径 | 通过 O/action/candidate/provenance 审计后才可 pilot；[OPeRA README](../02_实验/T0d_OPeRA/README.md) |
| D01 | 进行中 | 完成 LIGHT actor/turn/persona/world/history/action 对齐和 O 边界人工审查 | restricted dev 资产不作为 formal benchmark；[LIGHT README](../02_实验/T0c_LIGHT/README.md) |
| T0c-TR | 进行中 | 审核 expected-effect 与 transition trace 后再决定是否进入外部 pilot | `ΔO → X → S` 语义与时间边界可追溯；不调参冒充结果 |
| M4 | 未开始 | 独立 `A*` 准入后，冻结 data/split/feature/state protocol，再做 formal gate | 未满足前不启动 Experiment B、正式 test 或论文结果 |

## COMPLETED CHECKPOINTS

- **M0**：Mechanism Sanity v1；固定 `W/O/P/generated A^O` 的 S intervention 通过，见 [README](../02_实验/Mechanism_Sanity_v1/README.md)。
- **M5**：Mechanism Sanity v1.2 trajectory sanity；effort/progress/obstruction/recovery 工程回归通过，见 [README](../02_实验/Mechanism_Sanity_v1_2/README.md)。
- **T14/T20 development chain**：Run 1、1b、2、3、3b、4 已封口；均为 development-only，不是 formal test。
- **T0b**：SOTOPIA 30-episode 外部合成 pilot 结构审计完成，但 provenance/action surface 限制使其不能作为真人 A*。
- **T0c-SC**：Replay → SceneSnapshot bridge 已接通；`source available_actions` 不等于 `A^O`。

## BLOCKED / NO-GO

- 候选集不能冻结、角色 O 无法重建、split 有未来/身份泄漏、或外部 A* 不独立：停止 formal baseline。
- 本阶段不新增 S 字段、另造 X schema、设计 hard topology benchmark、改变 P、做 P drift、启动 multi-agent/ToM 或重构 `simulation.cpp`。
- `Theory_S_v2` 是 canonical Python research dynamics operator；Replay 是 canonical feature/baseline layer；dataset adapter 只做 raw → ReplayRecord/SceneSnapshot/X-compatible input，不复制 Theory-S。

## DEFERRED

- Paper-0 正式比较：`history / summary / no-S / theory-S / naive-S / trajectory-permuted-S`，使用同一 candidate-set NLL 和冻结 protocol。
- T20 attribution：generic/naive-S、理论语义与压缩收益的区分；不是当前机制主线。
- 更复杂 commitment、multi-task、inverse、叙事抽取、live LLM semantics、UI/异步，等首轮 external trajectory protocol 冻结后再评估。

## SOURCE OF TRUTH

- 当前事实：[当前实现进度](当前实现进度.md)
- 当前入口：[项目现状速览](项目现状速览_通俗版.md)
- 冻结研究问题：[Paper-0问题卡](Paper-0问题卡.md)
- 实验索引：[实验 README](../02_实验/README.md)
- 架构边界：[ARCHITECTURE_RULES](../ARCHITECTURE_RULES.md)
