# 研究设计：唯一维护入口

整理日期：2026-10-10

## 项目架构定位

2026-10-10 当前路线：**Evennia 为主平台、Ensemble 为首个原生人物机制参照**；P1/P2、P3-A/B、P3-C0/C1a 与 P4-0 均保留各自历史 owner。当前有限阶段 P5 Author Bundle 集成状态为 **READY_FOR_INDEPENDENT_REVIEW**（未 CLOSED）；唯一状态/结果见 [P5 README](../02_实验/Native_Platform_P5_v0/README.md) / [RESULTS](../02_实验/Native_Platform_P5_v0/RESULTS.md)，核心 API 见[代码 README](../tools/native_platform_v0/p5/README.md)。P5 只新增有限、条件性的作者机会 AND/OR 候选枚举；不等于完整 DM，11/12 结构检查通过不代表整套目标均满足。

2026-10-09 用户在新目标讨论后明确从外围维护切换为实现：[NPC System Integration v0](../tools/npc_system_v0/README.md)是获授权的有限应用整合，不是 E1-2 或重开冻结 C++ Runtime。授权/下一动作见 [TODO](TODO.md)，能力/验收只看[唯一结果](../02_实验/NPC_System_Integration_v0/RESULTS.md)。下方旧草案的“未开发 Director”不能再作为禁止本应用实现的当前规则。

`PredictionBaselineV1` 的 development fit 与独立 seed 复现已完成，当前为 `DEVELOPMENT_TRAINED_REPRODUCIBLE / READY_FOR_INDEPENDENT_REVIEW`；数值与训练细节只维护在[RESULTS](../02_实验/PredictionBaselineV1/RESULTS.md)。`SourceRankingV1` 的九条件来源条件比较也已完成，结果与下一动作只维护在[INPUT_REVIEW](../02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)；它不是 actor forecast、心理状态 `S` 或 Runtime policy 的训练证据。完整心理 dynamics / Paper-0 分支仍受 LIGHT 行动前 `O`、候选与独立标签的准入限制，但用户确认的玩家可置信 NPC 目标不以此为必经前提。`ResearchDynamicsV1` 是手写数值 fixture/candidate，不是已训练科学模型；旧 C++ `ReferenceRuleDynamicsV0` 统一称 `LegacyReferenceRuleDynamicsV0`，旧 Python `Theory-S_v2` 统一称 `ExpectedEffectEMAProxyV0` 历史诊断 proxy。失败证据和当前推进边界以[研究重建审计](研究重建审计_2026-10-06.md)为准；[Pre-V1 validity audit](PRE_V1_EXPERIMENT_VALIDITY_AUDIT.md)记录的是 2026-09 阶段状态，冲突时服从本次审计。

Shared Runtime Kernel 保持工程冻结：它负责时间、世界、动作执行、观察边界、验证、gate 与 trace。完整机制说明中已确认的内容是工程语义与模块契约，不是已验证心理规律。Dynamics Model 不等于 Runtime：C++ `ReferenceRuleDynamicsV0` 是冻结的工程基线，不是科学真理；Demo Living 手写 dynamics 只属于 application/demo，不能作为已训练规律。Paper-0 正式验证仍 blocked，但方法开发正在重建，不再把 M2 当作所有开发学习的唯一入口。详情见[Runtime / Dynamics / Demo 架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md)与[研究重建审计](研究重建审计_2026-10-06.md)。

当前只维护按职责归属的活动文档；数量不是稳定契约。按内容归属维护，不再按“某天新对话／某个模型的新总结”新增并列总纲。

| 文件 | 唯一职责 | 不在这里维护 |
|---|---|---|
| **[项目现状速览（通俗版）](项目现状速览_通俗版.md)** | **大白话入口**：在做什么、走到哪、有没有走偏、待拍板事项 | 新论证；术语定义 |
| **[研究重建审计](研究重建审计_2026-10-06.md)** | **唯一综合审计**：确证失败、证据强度、科学距离与重建顺序 | 易变 TODO 与逐项代码进度 |
| [完整机制说明 v0](完整机制说明_v0.md) | 已确认的 W/O/X/S/P/D/A 工程语义、任务承诺、场景/动作、时间、低耦合及消融约束 | 心理规律已验证的声明；未采纳公式、代码完成清单 |
| [前台问题与候选创新](前台问题与候选创新.md) | 旧行为预测 / Paper-0 分支的课题锚、Forward/Inverse、研究候选与评价边界 | 全系统当前研究问题；再写一套机制总说明 |
| [未决问题与机制候选](未决问题与机制候选.md) | 具体缺口、备选计算、用户原意、决策条件 | 把提案写成已实现或已验证 |
| **[Character Dynamics｜系统问题与执行语义 v0](CharacterDynamics_FormalProblem_v0.md)** | **唯一 F0/F1 owner**：算法无关的问题定义与执行语义；状态对象/权限、时间、转移、作者意图/绑定、规划器/导演、性质/反例及近期 A/B 研究组合；状态 DRAFT / READY_FOR_INDEPENDENT_REVIEW | 长期研究版图、算法选型、实现完成或研究有效性主张 |
| [AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md) | 候选 F2 与 TypedIR / 预实验的较低层 owner；保留已有语义契约和 reference 证据 | 整个系统的正式定义；把候选写成获批路线或将 reference 测试冒充 Director/多 NPC 方法结果 |
| [E0 Key Ledger Protocol v0](E0_KeyLedger_Protocol_v0.md) | 唯一有限钥匙账本 E0 执行定义与 fixture/search/monitor acceptance protocol；PROTOCOL_FROZEN / E0-KeyLedger-v0；实现与逐例验收状态见 [E0 实验入口](../02_实验/E0_KeyLedger_v0/README.md) | F0/F1 总设计、Pilot Monitor/reference 契约、未验收的实现能力或实验结果 |
| [E1 局部信息与独立角色协议 v0](E1_KeyLedger_LocalAgency_Protocol_v0.md) | E1-0 有限域与协议；E1-1 独立开发包已交付。实际状态与证据只查唯一结果 owner：[RESULTS](../02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)；代码入口：[runner](../tools/e1_keyledger_v0/runner.py) | E0 冻结规则；将开发验证写成正式实验、新颖性声明；自动授权正式实验/E1-2 |
| [NPC System Integration v0](../02_实验/NPC_System_Integration_v0/RESULTS.md) | 新授权应用 vertical slice 的唯一开发结果；实现与协议见[代码 README](../tools/npc_system_v0/README.md) | 全系统正式语义、冻结 E1 结果、心理验证或玩家评价 |
| [IntegrationBlueprint v0 §07](草案/IntegrationBlueprint_v0/07_INTEGRATION_GAPS.md) | 当前传统基线接线边界；历史 MC 候选与 C++ 证据桥分区保留 | 原件复现结果、已集成能力或实施授权 |
| [Native Platform P3-C1a](../02_实验/Native_Platform_P3_C1a_v0/README.md) | P3-C1a 临时不可观察/恢复历史结果入口；P3-C0/A/B 保留各自 owner | 后续扩展、P4、玩家效度或研究收益结论 |
| [Native Platform P4-0](../02_实验/Native_Platform_P4_0_v0/README.md) | 历史有限 native-server opportunity 与原生 note-response 结果 owner；audit、完整压缩证据和复现入口见 RESULTS | P4-1、完整 DM、心理/玩家效度或新颖性结论 |
| [Native Platform P5](../02_实验/Native_Platform_P5_v0/README.md) | 当前 Author Bundle 有限集成与阶段结果唯一 owner；运行状态见 RESULTS | 完整 DM、保证 NPC 响应/到达、或将内容型 storylet 当作可执行剧情 |
| [Native Platform P1/P2](../02_实验/Native_Platform_P1P2_v0/README.md) | 已完成 P1/P2 的历史验收、失败记录与复现指针 | 当前 P3 状态；玩家效度或研究收益结论 |
| [传统全链基线与文字平台技术准入](../01_文献/技术准入_传统全链基线与文字平台_2026-10-10.md) | 此前只读候选审查的源码事实、未知项及历史候选 | 当前选型、安装/运行状态或研究结论 |
| [04 统一问题与成熟基线准入](../01_文献/算法积木/04_统一问题与成熟基线准入.md) | 有限统一实例下的成熟方法综合、候选问题与方法准入判断 | 全部长期研究方向、已确认研究缺口或实验通过结论 |
| **[整合系统视角复核](审核_整合系统视角复核_2026-09-05.md)** | **判断复核**：回到实现核对旧判断的前提是否成立 | 文献层面的重新论证 |
| **[文献比较方法与阶段缺口复核](审核_文献比较方法与阶段缺口_2026-09-05.md)** | **方法纪律**：13 维机制比较模板、冻结母问题、科研流程阶段缺口。含**我自己的认错清单** | 具体论文的逐篇内容 |
| **[对外表述（中英对照）](对外表述.md)** | **旧行为预测 / Paper-0 分支表达材料**：abstract/intro 原料、术语与禁用表述 | 新作者约束路线的论文定位；技术细节与实验结论 |
| [TODO](TODO.md) | 下一动作、依赖、验收、完成状态 | 长篇机制论证 |
| [后置机制候选｜AU 考古](后置机制候选_AU考古.md) | 保存暂不进入主线的 AU 候选及升格条件 | 当前 runtime、Paper-0 主张与主线 TODO |
| [当前实现进度](当前实现进度.md) | 代码版本、实际能力、未实现项、验证证据 | 从目标设计推断完成 |
| **[System Vision v0](Character_Dynamics_System_Vision_v0.md)** | Runtime Kernel / Dynamics Model / Evaluator / Optimizer / Applications 的边界、runtime 三流模型与长期研究版图 | 把 Kernel 冻结误写为全系统完成；把候选方向误写为已承诺任务或研究缺口 |
| **[Runtime Scheduler v1](Runtime_Scheduler_v1.md)** | 已冻结的统一时间、RunningAction、DecisionGate 与 outcome contract | 新研究目标或 batch/evaluator 迁移授权 |
| **[Runtime Closure Matrix](Runtime_Closure_Acceptance_Matrix.md)** | Runtime / Engine v1 closure 的 gate 与可执行证据 | 心理机制或科研有效性结论 |
| [Runtime Semantic Audit Matrix](Runtime_Semantic_Audit_Matrix.md) | runtime channel 的 W/O/X/S 消费边界 | 增加新 runtime 功能 |
| [Runtime Stabilization Audit](Runtime_v1_Stabilization_Audit_2026-09-15.md) | 历史 anti-patch-debt checkpoint 与已解决事项 | 当前待办列表 |
| [System Phase Checkpoint](System_Phase_Checkpoint_2026-09-10.md) | Evaluator / Objective / Optimizer 暂停边界 | Runtime closure 状态 |
| [Objective Readiness v0](Objective_Readiness_v0.md) | objective 为什么尚不可用于质量排序/优化 | 用 telemetry 声称自然度 |
| [Optimizer v0](Optimizer_v0.md) | optimizer 的开发护栏与 no-selection 状态 | 开始参数搜索的授权 |
| [Development Split v1](Development_Split_v1.md) | synthetic train/holdout 的冻结 split 协议 | 正式外部 test 声明 |
| [ParameterConfig v0](ParameterConfig_v0.md) | 参数 owner、序列化与 sensitivity 边界 | 心理学参数解释 |
| **[Paper-0 问题卡](Paper-0问题卡.md)** | 冻结的行为预测研究分支、A* / O / candidate-set admission 前提 | 全部游戏 NPC 目标的统一前置要求；系统工程完成宣称 |
| [Theory-S M1 冻结决策](Theory-S_M1冻结决策_2026-09-07.md) | pre-training 的语义与协议冻结边界 | Theory-S 已训练/有效的声明 |
| [Existing Dataset Pool Routing](Existing_Dataset_Pool_Routing_v1_2026-09-08.md) | 历史数据集 routing、已 superseded 的 benchmark next-action | 新 dataset 搜索或训练授权 |
| [Architecture Audit Policy](architecture_audit_policy.md) | AI-heavy 工程的审计范围、已知债与不授权重构边界 | 当前 Runtime 的待办 |
| 本 README | 阅读路由与维护规则 | 复制其他页面的内容 |

## 从哪里读

**先看**：[项目现状速览（通俗版）](项目现状速览_通俗版.md) —— 五分钟建立整体印象，含当前风险与待拍板事项。

准备对外说／写论文：先查[结果成熟度与复用账本](研究重建审计_2026-10-06.md#现有结果的成熟度与复用账本截至-2026-10-08)；[对外表述（中英对照）](对外表述.md)仅是旧行为预测分支材料，不是新作者约束路线的论文定案。

新会话只需先回答四问，再按需进入细节：

| 问题 | 从哪里取答案 |
|---|---|
| 系统长期研究方向、当前候选问题分别是什么？ | [System Vision 长期研究版图](Character_Dynamics_System_Vision_v0.md#长期研究版图) → [现状速览](项目现状速览_通俗版.md) → [F0/F1 §1、§8](CharacterDynamics_FormalProblem_v0.md#8-研究问题细分阶段与当前成熟度)；近期 A/B 组合和有限实例 Q1–Q3 另见 [04 综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) |
| 已实现什么，哪些只是设计？ | [实现进度的当前事实](当前实现进度.md#2-当前实际执行链) + 对应源码/测试；[F0/F1 接口核对](CharacterDynamics_FormalProblem_v0.md#现行接口映射与未接入接缝) |
| 得到过什么正面或负面证据？ | [结果成熟度账本](研究重建审计_2026-10-06.md#现有结果的成熟度与复用账本截至-2026-10-08) → 各实验 RESULTS / 原始产物 |
| 修改模块服从哪份规格、不能破坏什么？ | [项目规则](../AGENTS.md)的权威边界 → [架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md)、[Runtime contract](Runtime_Scheduler_v1.md)或对应分支 owner |

完成 / 候选 / 暂停及下一动作只查 [TODO](TODO.md)。四问能准确回答即足够，不为历史材料措辞统一再新增总纲或重构冻结实现。

继续研究开发：先看[研究重建审计的用户目标校正](研究重建审计_2026-10-06.md#用户目标校正游戏中的可置信-npc)，再看[NPC 评测定向核查](../01_文献/定向核查_NPC可置信性评测_2026-10-06.md)。先选择能检验玩家感知的场景、比较基线与评价方法，不以真人动作预测作为统一前置任务。M2 candidate-set admission 仍阻止旧 Paper-0 formal test；PredictionBaselineV1 / SourceRankingV1 保留为有限开发证据。Runtime 已冻结，不因行为模型问题重开 Engine。

查具体论文：[文献库](../01_文献/README.md)；还原用户想法：[原始材料](../90_原始材料/README.md)。

当前作者约束线的问题定义唯一维护于 [F0/F1](CharacterDynamics_FormalProblem_v0.md)，候选 F2 / TypedIR / 预实验由 [Pilot](AuthorialTrajectoryPilotV0.md)维护；完整研究方向见 [System Vision 长期研究版图](Character_Dynamics_System_Vision_v0.md#长期研究版图)。A（规划/执行能力）与 B（稀疏作者控制）是近期选基线时抽取的研究组合；[04 综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md)的 Q1–Q3 是有限实例下的候选问题，不代表完整研究版图，也未决定研究缺口、方法或开工路线。Node/Maze 与 LLM/HTN 是替换候选；Minecraft 最新路线见上方入口，尚未集成。TypedIR 不是作者 UI。本轮有限语义返修已完成，待独立复核；当前下一动作及状态见 [TODO](TODO.md)。现有有限 Director 仅在新授权 NPC System Integration v0 应用中开发；冻结 C++ Runtime 不改。

例如本次三项想法分别落位：分段逆映射保留原话于问题 Q01；低耦合的确定边界在完整机制 §8，未落实方案在 Q03；Object/Scene/W 动作职责在完整机制 §4，具体实现缺口在 Q05。TODO 只链接并安排验证，不再复制三遍原理。

## 决策变成事实时怎么维护

1. 用户/证据确认语义：现行工程语义归完整机制与 Runtime owner；作者约束问题定义归 F0/F1 草案；算法/TypedIR 归 Pilot。按 owner 更新，不把新愿景直接写成现行实现；问题页保留尚未解决的差异和决策来源。
2. 形成具体下一动作：写 TODO；提案不会因为写入 TODO 就自动获得编码授权。
3. 实际改代码并验收：更新实现进度与 TODO，附代码版本/测试/产物，不用架构文档宣称完成。
4. 新文献改变研究判断：证据留 01_文献，研究问题页只写结论边界并链接；不要复制完整文献报告。
5. 新对话先保留原始材料，再按内容分别更新唯一所有者。不因为会话发生就新建“完整框架 v2”。

## 历史稿去哪了

原 13 份工作稿均保留在[整合前快照与逐项去向](归档/README.md)。旧稿只作为历史推理/证据，不继续维护现行结论；旧路径引用按“当前入口”或“历史证据”分别处理。

用户亲写的 `E:\Character Dynamics Demo` 不在本轮范围；本次修改应用 Python 与 owner 文档，未修改参考 C++。历史记录：此前曾采用“本地提交，不自动推送”的阶段性约定；当前版本控制操作遵循项目 `AGENTS.md`，已验证项目改动应提交并推送至 `webgpt-sync`，不得直接推送 `main`。
