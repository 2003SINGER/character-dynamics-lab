# TODO｜active research queue

更新时间：2026-10-09。此页只保留 ID、状态、下一动作、验收条件和链接；历史论证与已完成批次见[TODO 原版快照](归档/2026-09-07_TODO瘦身/TODO_原版_2026-09-07.md)。总体失败证据和证据边界以[研究重建审计](研究重建审计_2026-10-06.md)为准。

## SYSTEM / APPLICATION TRACK

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| BOUNDARY-V1 | **CLOSED / FROZEN** | Kernel / Dynamics / Demo ownership 与依赖边界已完成复核 | [架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md) |
| RUNTIME | **Shared Runtime Kernel v1：CLOSED / FROZEN** | 不因 Demo naturalness 重开；仅处理 execution invariant | [Closure Matrix](Runtime_Closure_Acceptance_Matrix.md) |
| DEMO-LIVING | **ACTIVE / DEMO ONLY** | 保留历史批次为实现诊断。Laya v4.3 一日工程 gate 通过、行为 scale gate 未通过：no-history 单 seed 睡眠 1,149 分钟且历史输入使首请求分布大幅变化；停止扩成 64 actors / 7 days | [core behavior eval](../Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；[Laya typed policy](../Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；[v4.3 audit](../outputs/laya_runs/laya_v43_66ebfe7_20260925/RESULTS.md) |
| RESEARCH-DYNAMICS | **TOY_NOT_ADMITTED / 未训练** | 不把四字段手写 law、相对分数 policy 或当前不足的干预测试称作机制通过；不运行会覆盖 artifacts 的生成器 | [研究重建审计](研究重建审计_2026-10-06.md)；[ResearchDynamicsV1 source](../02_实验/ResearchDynamicsV1/README.md) |

## ACTIVE

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| PRAXISH-ACTIVITY-PILOT | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW** | 前两步执行证据与原件保持不变；后续比较另立输入和 outputs，不覆盖旧结果 | [原件运行与验收 owner](../02_实验/Praxish_Activity_Pilot_v0/README.md)；[原文/源码证据](../01_文献/精读_Praxish论文与原始实现_2026-10-06.md) |
| PRAXISH-UTILITY-COMPARISON | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；有界立项 NO_GO** | 原执行目标已产出否定分支：不以活动组织本身改善该共同场景行为立项。作者成本/玩家偏好仍未知；下一问题待准入，不自动扩方法/训练/招募 | [唯一结果与研究判断](../02_实验/Praxish_Utility_Comparison_v0/RESULTS.md)；[公共 viewer](../02_实验/Praxish_Utility_Comparison_v0/presentation/README.md)；[逐项完成审计](../02_实验/Praxish_Utility_Comparison_v0/PARENT_REVIEW.md#原-thread-goal-逐项完成审计) |
| NPC-CONTINUITY-PILOT | **阶段1—3 DEVELOPMENT / READY_FOR_DISCUSSION，保留** | 三案例×两policy短轨迹与匿名回放已交付，未进入阶段4；本轮不扩展，也不把未提交paired源码混入提交 | [唯一检查点](../Demo%20codex-generated/applications/npc_continuity_v0/STAGE3_CHECKPOINT.md)；[原问题与限制](研究重建审计_2026-10-06.md#玩家目标的第一个可比较问题)。无玩家评价 |
| WORLD-NPC-PERIPHERAL | **算法级首轮已交付；部分原算法未公开/待核** | 保留现有知识缺项；仅在具体有限协议或研究问题需要时核对相应原算法，不主动扩成新一轮大综述、不跑新批次或改 Runtime | [算法、版本与当前边界](../01_文献/算法拆解_NPC方法与生产系统_2026-10-07.md)；长期方向见[系统愿景研究版图](Character_Dynamics_System_Vision_v0.md#长期研究版图) |
| AUTHOR-CONSTRAINT-AUDIT | **E0 有界单次验收 PASS / 外部审阅已收到；CI 成功与预算失败均保留** | 停止非阻断 E0 改进，完整成功/失败证据和固定预算保留，正式 CLOSED 仍待用户明确确认。后续 CI 的具体结果只由结果 owner 维护，不重跑刷绿、不暗改预算；E1-1 是另行授权的开发工作，不改 E0 | [唯一 E0 结果](../02_实验/E0_KeyLedger_v0/RESULTS.md)；[实验入口与审阅边界](../02_实验/E0_KeyLedger_v0/README.md)；[冻结协议](E0_KeyLedger_Protocol_v0.md) |
| E1-LOCAL-AGENCY | **E1-1 DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW** | 最小实现与开发验证已交付，到此停止，等待用户/GPT 审阅。实际轨迹、oracle、负控与 CI 证据只见结果 owner；不自行 CLOSED。正式预算尚未冻结，正式实验、E1-2、Director、训练均未启动 | [唯一结果](../02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)；[协议 v0.r1](E1_KeyLedger_LocalAgency_Protocol_v0.md)；[代码](../tools/e1_keyledger_v0/README.md)。E0 / C++ Runtime 未改，不预设 novelty 或玩家体验收益 |
| PREDICTION-BASELINE-V1 | **DEVELOPMENT_TRAINED_REPRODUCIBLE / READY_FOR_INDEPENDENT_REVIEW** | 保留旧 fits 与冻结协议，不将旧 physical-history view 冒称完整观察；新比较另由 SOURCE-RANKING-V1 维护 | [唯一旧数值结果](../02_实验/PredictionBaselineV1/RESULTS.md)；[LIGHT 来源准入审计](../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)。完整 actor-visible contract / 人工准入未过，已暴露数据不是 untouched formal test |
| SOURCE-RANKING-V1 | **DEVELOPMENT_TRAINED / PARENT_ARTIFACT_AUDIT_PASS / READY_FOR_INDEPENDENT_REVIEW** | 复核固定比较并确定下一可识别问题；不调参挽救假设，不替代 Paper-0 | [冻结任务/通道规格](../02_实验/LIGHT_SourceRankingV1/README.md)；[唯一结果与下一动作](../02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)，执行准入与 actor-visible 准入分开 |
| SYSTEM | **Shared Runtime Kernel v1：CLOSED / FROZEN** | Continuous Runtime ownership、threshold/W validation、typed rejection、fixtures、trace、case-isolated CTest、explicit DynamicsModel injection 与 isolation guard 已闭环。此状态只关闭执行 Kernel，不代表任何行为模型、Evaluator、Objective、Optimizer 或 Paper-0 完成。 | [Runtime Scheduler v1](Runtime_Scheduler_v1.md)、[Closure 验收矩阵](Runtime_Closure_Acceptance_Matrix.md)、[架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md) |
| M1 | **历史 proxy 已审计；不作为新研究模型** | 保留旧 Theory-S 结果为 `ExpectedEffectEMAProxyV0` diagnostic，不延伸其心理解释 | [研究重建审计](研究重建审计_2026-10-06.md)；[Pre-V1 validity audit（2026-09阶段边界）](PRE_V1_EXPERIMENT_VALIDITY_AUDIT.md) |
| M2 | **Paper-0 formal blocker；不是全部开发的前置门** | 为正式 Paper-0 补齐 SceneSnapshot → affordance → generated actor-local `A^O` 的最小 ontology 与实例绑定 | 生成不得读 source `A*`；source support 仅 post-hoc 诊断；[Mechanism Sanity v1](../02_实验/Mechanism_Sanity_v1/README.md) |
| M3 | **已完成（owner audit v0）** | 保留审计边界；若要重开 D01，先完成 actor-local observation audit、跨 actor gap 编码和 X 字段准入 | [capability matrix](../02_实验/Theory_S_v2/capability_matrix.md)、[D01 LIGHT](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)、[OPeRA candidate reconstruction](../02_实验/T0d_OPeRA/candidate_reconstruction_feasibility_v0.md)；proxy/telemetry 不升级为 A* |
| POOL | **已完成（routing v1；2026-09-09 superseded）** | 按 routing update 转入 LIGHT actor-local history eligibility gate；ClubFloyd Stage 0c paused，AGAIN 仍仅是 external proxy | [routing v1 + superseding update](Existing_Dataset_Pool_Routing_v1_2026-09-08.md)；不得把旧 ClubFloyd #1 排名当作当前主线 |
| CLUBFLOYD | **Stage 0c non-duplicate view completed；当前 estimand 无正向增量** | 暂停 ClubFloyd persistent-compression / Theory-S bridge；保留 lossless source 与 analysis view；不得继续调参追分 | [Stage 0c protocol](../02_实验/Replay/ClubFloyd/stage0c_nonduplicate_protocol.md)；1,964-row view / 194 test rows |
| LIGHT-H0 | **历史探索性结果；episode-independent signal 未证** | 不再按旧 actor-unit CI 声称泛化；旧数值/artifact 保留。审计发现 H0b/compression train/test 共享 279 episode，三组 pairwise overlap 合计 912 | [split audit](../outputs/research_reset_audit_20261006/split_audit_v3.json)、[H0b report](../02_实验/T0c_LIGHT/LIGHT_H0b_transition_probe_v0.md)、[compression report](../02_实验/T0c_LIGHT/LIGHT_compression_benchmark_v0.md) |
| AGAIN-DYN | **completed development audit；不升级** | 保留 proxy persistence 结果；不训练 Theory-S 参数，不继续设计新 event/tau | [AGAIN audit result](../02_实验/T0h_AGAIN/dynamics_audit_v0_result.md)；event-driven relaxation 不稳定，arousal 仅 external proxy |
| T0d | **LIMITED-GO（v1 single-target failed; set route unresolved）** | routing v1 已完成；不再把该旧待办当 blocker。仅在 LIGHT actor-local gate 为 NO-GO 后，按 OPeRA protocol 重新冻结 set route | v1 每 step 恰好 1 candidate，10/30（33.3%）是 target selection accuracy；canonical 13D readout 仍不兼容；[OPeRA protocol](../02_实验/T0d_OPeRA/OPeRA_pilot_protocol_v0.md)、[v1 correction](../02_实验/T0d_OPeRA/terra_candidate_spike_v1_result.md) |
| D01 | **NO-GO（完整六维训练）** | 保留 actor-local / temporal boundary 失败边界；重开前完成 observation audit、predecessor/gap 编码与 X 字段协议 | [D01 semantic/temporal admission](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)；LIGHT 不作为第一次完整 Theory-S gradient training 主数据 |
| T0c-TR | PAUSED | 等待 M2 candidate-set admission；不单独推进外部 pilot | `ΔO → X → S` 语义与时间边界可追溯；不调参冒充结果 |
| M4 | 未开始 | 独立 `A*` 准入后，冻结 data/split/feature/state protocol，再做 formal gate | 未满足前不启动 Experiment B、正式 test 或论文结果 |

## 研究重建顺序与范围护栏

- **当前检查点**：完整研究方向由[系统愿景版图](Character_Dynamics_System_Vision_v0.md#长期研究版图)维护；F0/F1 定系统语义，Pilot 定候选 F2 / TypedIR，04 定原方法综合。A/B 与 Q1–Q3 都不是完整研究目录。E0 已达到有界验收停止条件且收到外部收口建议，数值/成功/失败仅由[结果 owner](../02_实验/E0_KeyLedger_v0/RESULTS.md)维护；不继续完善 E0。2026-10-09 用户明确授权[E1-1 最小实现与开发验证](E1_KeyLedger_LocalAgency_Protocol_v0.md)，完成后停止；正式实验、E1-2、Director、训练或全面方法比较未授权，正式 milestone CLOSED 仍需用户明确确认。非阻断存储/稳定性增强进入 backlog；外围待核算法不扩成综述。Praxish 否定分支与 SourceRanking 开发结果仍由各自 owner 维护，不追分救假设、不否定整个 NPC 方向。Runtime 继续 frozen。
- **Paper-0 formal gates**：persistent `S`、legal actor-local `O`、independent `A*`、可复核有限 `A^O`、episode/user-disjoint split 和预注册指标；M2 是 candidate-set formal admission 工作，不阻塞开发方法基座。
- **PAUSED**：Objective readiness、Evaluator ranking、Optimizer、旧 proxy training、外部数据集扩展；ResearchDynamicsV1 不作为已训练模型，仅记录为尚未准入的 toy/fixture。
- **DEFERRED SYSTEM/RESEARCH BRANCH**：ToM、multi-agent、Inverse、P drift、Q01 advanced response curves、Scene Manager 与 live LLM semantics。
- 所有开发结果标为 DEVELOPMENT；任何已暴露数据都不是 untouched formal test。独立行为标签、actor-local O、可重建 `A^O` 与 episode/user split 是旧 Paper-0 预测主张的缺口，不自动成为玩家可置信性目标的前置门；后者也不能以模型裁判得分冒称玩家认可。不靠 dataset tourism 或重开 Runtime 绕过对应证据要求。

## COMPLETED CHECKPOINTS

- **M0**：Mechanism Sanity v1；固定 `W/O/P/generated A^O` 的 S intervention 通过，见 [README](../02_实验/Mechanism_Sanity_v1/README.md)。
- **M5**：Mechanism Sanity v1.2 trajectory sanity；effort/progress/obstruction/recovery 工程回归通过，见 [README](../02_实验/Mechanism_Sanity_v1_2/README.md)。
- **T14/T20 development chain**：Run 1、1b、2、3、3b、4 已封口；均为 development-only，不是 formal test。
- **LIGHT H0b / compression**：结果 artifact 保留；2026-10-06 split audit 发现 episode 跨 actor 分入不同 split，原有泛化与 actor-unit CI 结论降级为开发切片探索。
- **T0b**：SOTOPIA 30-episode 外部合成 pilot 结构审计完成，但 provenance/action surface 限制使其不能作为真人 A*。
- **T0c-SC**：Replay → SceneSnapshot bridge 已接通；`source available_actions` 不等于 `A^O`。

## BLOCKED / NO-GO

- 候选集不能冻结、角色 O 无法重建、split 有未来/身份泄漏、或外部 A* 不独立：停止 formal baseline。
- 本阶段不新增 S 字段、另造 X schema、设计 hard topology benchmark、改变 P、做 P drift、启动 multi-agent/ToM 或重构 `simulation.cpp`。
- `ResearchDynamicsV1` 是 `TOY_NOT_ADMITTED` 的手写 fixture；`Theory_S_v2` 是 `ExpectedEffectEMAProxyV0` 历史 proxy；Replay 是 canonical feature layer；PredictionBaselineV1 是已拟合并复现、待独立外审的 DEVELOPMENT 预测方法基座，不代表已学到心理 `S` 或 Runtime policy；dataset adapter 只做 raw → ReplayRecord/SceneSnapshot/X-compatible input，不复制 proxy。

## DEFERRED

- Paper-0 正式比较：`history / summary / no-S / theory-S / naive-S / trajectory-permuted-S`，使用同一 candidate-set NLL 和冻结 protocol。
- T20 attribution：generic/naive-S、理论语义与压缩收益的区分；不是当前机制主线。
- 更复杂 commitment、multi-task、inverse、叙事抽取、UI/异步，等首轮 external trajectory protocol 冻结后再评估。`LayaTypedPolicyV0` 是受限的本机 Demo policy adapter，不属于此研究 protocol。

## SOURCE OF TRUTH

- 研究历史失败、当前科学证据与方法重建顺序：[研究重建审计](研究重建审计_2026-10-06.md)
- 当前事实：[当前实现进度](当前实现进度.md)
- 当前入口：[项目现状速览](项目现状速览_通俗版.md)
- 冻结研究问题：[Paper-0问题卡](Paper-0问题卡.md)
- 实验索引：[实验 README](../02_实验/README.md)
- 架构边界：[ARCHITECTURE_RULES](../ARCHITECTURE_RULES.md)
