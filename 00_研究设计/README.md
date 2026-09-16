# 研究设计：唯一维护入口

整理日期：2026-09-16

## 项目架构定位

当前研究对象：`ResearchDynamicsV1`（未冻结候选）。旧 C++ `ReferenceRuleDynamicsV0` 统一称 `LegacyReferenceRuleDynamicsV0`，旧 Python `Theory-S_v2` 统一称 `ExpectedEffectEMAProxyV0` 历史 proxy。边界与证据分类见 [Pre-V1 validity audit](PRE_V1_EXPERIMENT_VALIDITY_AUDIT.md)。

Shared Runtime Kernel 已工程冻结：它负责时间、世界、动作执行、观察边界、验证、gate 与 trace。Dynamics Model 不等于 Runtime：C++ `ReferenceRuleDynamicsV0` 是冻结的工程基线，不是科学真理；Python `Theory-S_v2` 仍是当前 canonical research dynamics candidate；`DemoLivingDynamicsV0` 只属于 application/demo，可为了生活感调优且没有科研证据权。科研当前按实际状态保持 PAUSED；详情见[Runtime / Dynamics / Demo 架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md)。

当前只维护按职责归属的活动文档；数量不是稳定契约。按内容归属维护，不再按“某天新对话／某个模型的新总结”新增并列总纲。

| 文件 | 唯一职责 | 不在这里维护 |
|---|---|---|
| **[项目现状速览（通俗版）](项目现状速览_通俗版.md)** | **大白话入口**：在做什么、走到哪、有没有走偏、待拍板事项 | 新论证；术语定义 |
| [完整机制说明 v0](完整机制说明_v0.md) | 已确认的 W/O/X/S/P/D/A 语义、任务承诺、场景/动作、时间、低耦合及消融约束 | 未采纳公式、代码完成清单 |
| [前台问题与候选创新](前台问题与候选创新.md) | 课题锚、Forward/Inverse、研究候选、评价、近邻边界及后续分支 | 再写一套机制总说明 |
| [未决问题与机制候选](未决问题与机制候选.md) | 具体缺口、备选计算、用户原意、决策条件 | 把提案写成已实现或已验证 |
| **[整合系统视角复核](审核_整合系统视角复核_2026-09-05.md)** | **判断复核**：回到实现核对旧判断的前提是否成立 | 文献层面的重新论证 |
| **[文献比较方法与阶段缺口复核](审核_文献比较方法与阶段缺口_2026-09-05.md)** | **方法纪律**：13 维机制比较模板、冻结母问题、科研流程阶段缺口。含**我自己的认错清单** | 具体论文的逐篇内容 |
| **[对外表述（中英对照）](对外表述.md)** | **论文表达锚点**：abstract/intro 原料、定位三层拆分、术语表与禁用表述 | 技术细节与实验结论 |
| [TODO](TODO.md) | 下一动作、依赖、验收、完成状态 | 长篇机制论证 |
| [后置机制候选｜AU 考古](后置机制候选_AU考古.md) | 保存暂不进入主线的 AU 候选及升格条件 | 当前 runtime、Paper-0 主张与主线 TODO |
| [当前实现进度](当前实现进度.md) | 代码版本、实际能力、未实现项、验证证据 | 从目标设计推断完成 |
| **[System Vision v0](Character_Dynamics_System_Vision_v0.md)** | Engine / Evaluator / Optimizer 的系统边界与 runtime 三流模型 | 把 Engine 冻结误写为全系统完成 |
| **[Runtime Scheduler v1](Runtime_Scheduler_v1.md)** | 已冻结的统一时间、RunningAction、DecisionGate 与 outcome contract | 新研究目标或 batch/evaluator 迁移授权 |
| **[Runtime Closure Matrix](Runtime_Closure_Acceptance_Matrix.md)** | Runtime / Engine v1 closure 的 gate 与可执行证据 | 心理机制或科研有效性结论 |
| [Runtime Semantic Audit Matrix](Runtime_Semantic_Audit_Matrix.md) | runtime channel 的 W/O/X/S 消费边界 | 增加新 runtime 功能 |
| [Runtime Stabilization Audit](Runtime_v1_Stabilization_Audit_2026-09-15.md) | 历史 anti-patch-debt checkpoint 与已解决事项 | 当前待办列表 |
| [System Phase Checkpoint](System_Phase_Checkpoint_2026-09-10.md) | Evaluator / Objective / Optimizer 暂停边界 | Runtime closure 状态 |
| [Objective Readiness v0](Objective_Readiness_v0.md) | objective 为什么尚不可用于质量排序/优化 | 用 telemetry 声称自然度 |
| [Optimizer v0](Optimizer_v0.md) | optimizer 的开发护栏与 no-selection 状态 | 开始参数搜索的授权 |
| [Development Split v1](Development_Split_v1.md) | synthetic train/holdout 的冻结 split 协议 | 正式外部 test 声明 |
| [ParameterConfig v0](ParameterConfig_v0.md) | 参数 owner、序列化与 sensitivity 边界 | 心理学参数解释 |
| **[Paper-0 问题卡](Paper-0问题卡.md)** | 当前科研主问题、A* / O / candidate-set admission 前提 | 系统工程完成宣称 |
| [Theory-S M1 冻结决策](Theory-S_M1冻结决策_2026-09-07.md) | pre-training 的语义与协议冻结边界 | Theory-S 已训练/有效的声明 |
| [Existing Dataset Pool Routing](Existing_Dataset_Pool_Routing_v1_2026-09-08.md) | 历史数据集 routing、已 superseded 的 benchmark next-action | 新 dataset 搜索或训练授权 |
| [Architecture Audit Policy](architecture_audit_policy.md) | AI-heavy 工程的审计范围、已知债与不授权重构边界 | 当前 Runtime 的待办 |
| 本 README | 阅读路由与维护规则 | 复制其他七页的内容 |

## 从哪里读

**先看**：[项目现状速览（通俗版）](项目现状速览_通俗版.md) —— 五分钟建立整体印象，含当前风险与待拍板事项。

准备对外说／写论文：先读 [对外表述（中英对照）](对外表述.md) —— 先固定能说什么、不能说什么，再扩成 abstract / intro。

理解项目：研究问题 → 完整机制。

继续改造：先看系统愿景与 Runtime closure；Runtime 已冻结时，直接读 Paper-0 问题卡 → TODO 的 M2，不重开 Engine。

查具体论文：[文献库](../01_文献/README.md)；还原用户想法：[原始材料](../90_原始材料/README.md)。

例如本次三项想法分别落位：分段逆映射保留原话于问题 Q01；低耦合的确定边界在完整机制 §8，未落实方案在 Q03；Object/Scene/W 动作职责在完整机制 §4，具体实现缺口在 Q05。TODO 只链接并安排验证，不再复制三遍原理。

## 决策变成事实时怎么维护

1. 用户/证据确认语义：将已定部分合入完整机制，问题页保留尚未解决的差异和决策来源。
2. 形成具体下一动作：写 TODO；提案不会因为写入 TODO 就自动获得编码授权。
3. 实际改代码并验收：更新实现进度与 TODO，附代码版本/测试/产物，不用架构文档宣称完成。
4. 新文献改变研究判断：证据留 01_文献，研究问题页只写结论边界并链接；不要复制完整文献报告。
5. 新对话先保留原始材料，再按内容分别更新唯一所有者。不因为会话发生就新建“完整框架 v2”。

## 历史稿去哪了

原 13 份工作稿均保留在[整合前快照与逐项去向](归档/README.md)。旧稿只作为历史推理/证据，不继续维护现行结论；旧路径引用按“当前入口”或“历史证据”分别处理。

用户亲写的 `E:\Character Dynamics Demo` 不在本轮范围；本次仅整理研究文档，未修改参考 C++。本地提交，不自动推送。
