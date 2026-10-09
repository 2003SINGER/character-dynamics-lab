# IntegrationBlueprint v0｜全系统装配草案

状态：DRAFT / READY_FOR_INDEPENDENT_REVIEW。源码核对基线：`webgpt-sync@19e5b373303b1504b7fa46f6e01af4563947171a`；本轮只新增本目录的设计文件，不实现功能、不训练、不运行 E1-2、不改冻结 Runtime 与实验结果，不进入下一阶段。

## 要恢复的目标

用有限机制、成熟算法和稀疏作者劳动，形成玩家能理解其过去、看到其现在、影响其未来的角色世界。NPC 默认按自己的认识、需求、目标和承诺生活；作者可以引导世界机会，也可以使用明确授权并可追溯的策略引导、状态覆写和亲写片段。任务成功率不是人物价值的唯一指标，错误、拖延、误会和放弃可以是有因果依据的表现。

本目录是思想→数据流→源码接缝的装配图，不是第二份 F0/F1、第二套实现或新算法规范。唯一语义 owner 仍是 [F0/F1](../../CharacterDynamics_FormalProblem_v0.md)、[完整机制](../../完整机制说明_v0.md)；作者 IR/预实验 owner 是 [Pilot](../../AuthorialTrajectoryPilotV0.md)。分歧和未决项保留在这些 owner，本草案不裁决。

目标来源：本轮用户指定 `pasted-text-1.txt`，SHA256 `c481d2359f924098cb0f8a427d003d5cef2327dc439aba847140f2151e1d71d3`；其中网页模型给出的状态判断按其 `8f4fb7b` 历史时点解释，任务要求经用户本轮明确采纳。思想自身是否 USER_CONFIRMED 单独查来源，不因采纳蓝图任务而全数升格。完整私有原文不复制进本目录，附件原件保持不动：本轮“只新增设计草案”的范围优先于普通归档清理流程。上一轮有限应用已存在，但不是本轮蓝图的替代物。

## 阅读顺序与文件职责

| 文件 | 回答什么 | 下游调用/交叉链接 |
|---|---|---|
| [01 思想账本](01_IDEA_LEDGER.md) | 原意、来源、确认程度、源码落点、近邻、缺口 | 各伪代码以思想项为追踪入口 |
| [02 世界与 Runtime](02_WORLD_RUNTIME.pseudo.md) | 谁推进时间、启动/结算、合法观察、真实证据 | 调用 03，向 05 提交证据，向 04 发失败/变化 |
| [03 角色动力](03_ACTOR_DYNAMICS.pseudo.md) | O/X/U/S/P/D、记忆、目标/承诺、反应与质量 | 调用 04，最终只向 02 提交请求 |
| [04 规划桥](04_PLANNING_BRIDGES.pseudo.md) | 高层候选、低层规划、角色 gap、未来依赖修复 | 服务 03/05；不拥有执行权 |
| [05 作者与 Director](05_AUTHOR_DIRECTOR.pseudo.md) | 四类控制、绑定、监测、合法机会、覆写 | 调用 04 预测，向 02/03 权威写入入口提案 |
| [06 完整轨迹](06_END_TO_END_TRACES.md) | A 日常/B 引导/C 玩家修复/D 显式创作控制如何穿过全部模块 | 手推而非实际运行记录 |
| [07 源码与缺口](07_INTEGRATION_GAPS.md) | Adapter/Coordinator/域/动力/科学/用户选择，最小下一接缝 | 提案，不自动开工 |

## 证据等级和共同符号

`EXISTING` = 当前实读源码有此路径；`PARTIAL` = 仅有限域、单 actor 或缺某个契约；`PROPOSED` = 蓝图接口，不存在同名可调用 API。伪代码块除明确写出的真实签名外均为 PROPOSED；名称看起来像程序不代表现成函数。

| 对象 | 唯一语义 owner / 生命周期 | 边界 |
|---|---|---|
| `W`、世界任务/关系事实 | World / 持久 | NPC 不直读；显示名不是实体 ID |
| `K`、`Run_i` | Runtime 时钟与动作生命周期 / 持久 | 本目标多主体映射尚缺；现行 C++ 一个 running slot |
| `O_i`、`H_i`、二阶信念 | actor-local 观察/历史视图 / 持久 | 只含已授权观察；Known 不保证真实，缺值不是 false |
| `X_i` | 所选解释模型 / 事件级可修订 | 不是任意 StateDelta，不读隐藏 W |
| `S_i`、承诺、私有关系态度 | actor state store / 持久，model-pinned | 字段更新由声明的 updater；覆写走独立许可入口 |
| `P_i` | 人物响应配置 / 本次自然运行固定 | 人格小传≠更新参数；显式作者换版不是自然学习 |
| `D_i` | Goal/Action Selector / 一次决策 | 不与持久 S 混写 |
| `Q_i`、future graph | planner / 可撤回预测 | 不成为 WorldTask、承诺或已发生历史 |
| `AuthorBundle` | 作者确认的规格 / 带版本 | planner 子目标不冒充作者硬目标 |
| `L`、实际回执 | execution evidence sink / append-only 目标契约 | 现有 C++ trace 是材料，不是全世界永久账本 |
| `Forecast` | 隔离模型 / 候选未来 | 不送 committed Monitor；fork 能力需单独证明 |

统一消息信封（拟议，不要求现在增加框架）：`run_id, stable_entity_ids, message_id, simulation_minute, sequence, producer/version, domain/model/registry pins, input_frontier, source_refs, field_provenance, assumptions, requested_vs_applied`。模拟时间只有 K 推进；`sequence` 仅排序同刻提交，wall latency/call index/叙事阶段不推进 K。

## 共同运行与已有系统的区别

```text
W/K 的时间、自然事件、玩家控制 ──02──→ 合法 O/反馈 ──03──→ 自己的 X/U/S/目标/承诺
          ↑                                           │
          └──── validated Intent ← Action Selector ← 04 actor-local Planner
          │
          └→ committed 证据 ──05 Monitor──→ 风险/断链 ──04 repair/forecast
作者意图 ──05 bind/permission──→ World Director ──04 proposals──→ 02 合法世界控制
              └→ AUTHORED 控制通道 ──→ 02/03 授权创作控制（独立标签，不伪装自主）
已提交历史 ──02 presentation read view──→ 演出/UI；不反写事实
```

这不是每 tick 同步流水线。自然过程、已有动作、NPC 日常和作者监测可有不同触发频率；心理字段独立消费实际 Δt。Director off 和无 LLM 都是完整运行模式。调用高层规划器时世界可继续，过期候选到达后重验，不回拨时间。

当前有两个不能相加冒充统一系统的执行基线：C++ [ContinuousRuntime](../../../Demo%20codex-generated/Inc/continuous_runtime.h) 与独立 Python [E0/E1](../../../tools/e1_keyledger_v0/README.md)。[npc_system_v0](../../../tools/npc_system_v0/README.md)复用 Python Executor，已贯通有限世界引导/角色/监测，但不是 C++ 集成、通用并发、二阶知识、关系模型或高层 LLM。未来选一个宿主权威路径并只做 adapter，不能把两个真实时钟互相同步后称单时钟。具体不足见 07。

## 来源读取与解释纪律

必读材料已按任务核对：完整机制、Q01–Q10、System Vision、F0/F1、Pilot、前台问题、当前实现进度、2026-10-06 重建审计、算法积木四卡及入口、相关历史机制与来源索引；当前 C++ headers/ContinuousRuntime 调用路径、Python E0/E1/TypedIR/有限应用接口。精确来源与能力映射分别在 01/07，不复制 owner 全文。算法近邻沿用已核读本地方法卡的证据范围，本轮不是新一轮论文全文审计或查新。

历史材料中的“多角色暂不做”只限定当年 v0/Paper-0，不删除全系统多角色目标；“二阶工业界未做”等旧宽泛断言不作为本蓝图事实；现有动作拆分、history hook、有限 Director 以当前源码为准。USER_CONFIRMED 设计不是科学证明。Mimesis 2013 可编辑部分潜史的权限不引入本项目 future-only 修复。

本机在 `D:/desk/科研/character-dynamics` 实读并写草案。AGENTS/README 另记 Mac canonical 路径，本轮没有迁移、改路由或创建平行根；核对以当前 Windows checkout 的 Git revision 和文件为证据，不宣称它是 Mac 当前状态。

## 验收、回读和停止

完成要求：八文件齐全；每条重要思想可追来源与确认状态；每个接缝给输入/输出、所有权、权限、失败与版本；四类 trace 全链且区分现码/拟议；单权威时间与执行，不用预测当历史；一个源码出发的最小实施提案；保留创作权和未决项。

父级已独立回读源码与新草案，核查思想是否被“Dynamics 插件”概括掉、源码能力是否虚构、目标/Planner/Policy 是否偷换、隐 W 是否进角色、有没有第二时钟/执行器，以及历史/合法进度/未知、创作来源和版本边界。机械链接/范围检查只辅助，不替代语义回读。

本轮三项 Luna 子任务分别完成思想来源台账、四条流程及源码缺口；父级负责共同调用契约和独立核验。审阅中已修正：不相关的文献指向、两个章节锚点、Runtime 外围重复执行的歧义、Policy 二次采样误述、AUTHORED 与 Director 权限混线，以及把 model pins 误列为结果内现成字段的问题。

| 目标文本验收项 | 本轮交付落点 |
|---|---|
| 完整思想来源与确认边界 | 01 共 34 条，每条均有状态、原意、出处、现码/缺口、近邻、接缝、未决及蓝图落点；原件保留，不公开全文 |
| 共同世界与合法人物信息 | 02/03 明示 W/O/X/U/S/P、affordance、任务/承诺、长期动作、单次 canonical 推进与未实现的多主体协调 |
| 规划、创作权及预测/提交分界 | 04/05 分开 Goal Selector/GOAP/HTN、高层候选、五类可行性、独立 Director 与 AUTHORED 通道 |
| 四条完整运行轨迹 | 06 的 A 日常中断恢复/放弃、B NOOP 与两个机会比较、C 玩家破坏与无关动作保留、D 条件锁定后 abort；均为纸面例 |
| 真正缺口与一个下一切口 | 07 的六类缺口及唯一 C++ 实际证据→Python TypedIR 只读监测提案，不另造时钟或执行器 |
| 范围与停止 | 本轮新增八份草案；不更改现有源码/规范 owner/实验结果，不运行新实验，待独立审阅，不标 CLOSED |

本轮不自动实现最小切口、不跑新实验、不替现有结果改 CI、不宣布整体架构 CLOSED。仅按项目规则提交并推送 `webgpt-sync`，等待用户和独立审阅。
