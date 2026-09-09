# TODO｜active research queue

更新时间：2026-09-09。此页只保留 ID、状态、下一动作、验收条件和链接；历史论证与已完成批次见[TODO 原版快照](归档/2026-09-07_TODO瘦身/TODO_原版_2026-09-07.md)。

## ACTIVE

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| SYSTEM | **主线切换：Character Dynamics Engine / Evaluator / Optimizer** | Phone information-boundary 与 deadline state-dynamics 已 CLOSED；commitment/recovery v0 = PASS；下一步才进入 development split 参数搜索设计 | [系统愿景](Character_Dynamics_System_Vision_v0.md)、[Self-Evaluation v0](../02_实验/Self_Evaluation_v0.md)、[scenario manifest](../tools/self_evaluation_scenarios_v0.json)；内部 score 不等于外部自然性 |
| M1 | **已完成（pre-training gate）** | 已冻结 anchor 语义边界、sign-violation 协议、decision-step 时间尺度、neutral 初始化与 trajectory reset；不再扩展机制 | [M1 冻结决策](Theory-S_M1冻结决策_2026-09-07.md)、[Theory-S v2](../02_实验/Theory_S_v2/README.md)；不得把候选实现写成心理学验证 |
| M2 | 进行中 | 完善 SceneSnapshot → affordance → generated `A^O` 的最小 ontology 与实例绑定 | 生成不读 source `A*`；source support 仅 post-hoc 诊断；[Mechanism Sanity v1](../02_实验/Mechanism_Sanity_v1/README.md) |
| M3 | **已完成（owner audit v0）** | 保留审计边界；若要重开 D01，先完成 actor-local observation audit、跨 actor gap 编码和 X 字段准入 | [capability matrix](../02_实验/Theory_S_v2/capability_matrix.md)、[D01 LIGHT](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)、[OPeRA candidate reconstruction](../02_实验/T0d_OPeRA/candidate_reconstruction_feasibility_v0.md)；proxy/telemetry 不升级为 A* |
| POOL | **已完成（routing v1；2026-09-09 superseded）** | 按 routing update 转入 LIGHT actor-local history eligibility gate；ClubFloyd Stage 0c paused，AGAIN 仍仅是 external proxy | [routing v1 + superseding update](Existing_Dataset_Pool_Routing_v1_2026-09-08.md)；不得把旧 ClubFloyd #1 排名当作当前主线 |
| CLUBFLOYD | **Stage 0c non-duplicate view completed；当前 estimand 无正向增量** | 暂停 ClubFloyd persistent-compression / Theory-S bridge；保留 lossless source 与 analysis view；不得继续调参追分 | [Stage 0c protocol](../02_实验/Replay/ClubFloyd/stage0c_nonduplicate_protocol.md)；1,964-row view / 194 test rows |
| LIGHT-H0 | **已封口：`HISTORY_SIGNAL_PRESENT`；`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE`** | 不再扩展 H0/H0b/H0c/H0d；仅保留为 generic representation development diagnostic，转回系统 evaluator 主线 | [H0b report](../02_实验/T0c_LIGHT/LIGHT_H0b_transition_probe_v0.md)、[compression report](../02_实验/T0c_LIGHT/LIGHT_compression_benchmark_v0.md)、[result](../02_实验/T0c_LIGHT/light_compression_benchmark_v0.json) |
| AGAIN-DYN | **completed development audit；不升级** | 保留 proxy persistence 结果；不训练 Theory-S 参数，不继续设计新 event/tau | [AGAIN audit result](../02_实验/T0h_AGAIN/dynamics_audit_v0_result.md)；event-driven relaxation 不稳定，arousal 仅 external proxy |
| T0d | **LIMITED-GO（v1 single-target failed; set route unresolved）** | routing v1 已完成；不再把该旧待办当 blocker。仅在 LIGHT actor-local gate 为 NO-GO 后，按 OPeRA protocol 重新冻结 set route | v1 每 step 恰好 1 candidate，10/30（33.3%）是 target selection accuracy；canonical 13D readout 仍不兼容；[OPeRA protocol](../02_实验/T0d_OPeRA/OPeRA_pilot_protocol_v0.md)、[v1 correction](../02_实验/T0d_OPeRA/terra_candidate_spike_v1_result.md) |
| D01 | **NO-GO（完整六维训练）** | 保留 actor-local / temporal boundary 失败边界；重开前完成 observation audit、predecessor/gap 编码与 X 字段协议 | [D01 semantic/temporal admission](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)；LIGHT 不作为第一次完整 Theory-S gradient training 主数据 |
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
