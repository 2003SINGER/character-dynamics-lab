# Character Dynamics Lab｜角色动力学实验室

> 目标愿景：面向可持续运行、世界中心的 NPC，用可审计的观察、状态与执行机制支持可信行为和作者控制。局部策略、规划与开放语义模型的组合仍是候选路线，不是已经证明的低成本方法。

本机唯一 canonical checkout 位于 `/Users/2003singer/Workspace/Research/character-dynamics-lab`；`webgpt-sync` 是项目 review branch owner。本地本轮 P3 开发 checkout 位于 `codex/native-agency-p3-20261010`，不应将其描述成 `webgpt-sync` checkout。实验条件、run ID 与本地原始产物按路径分别保留；迁移映射和 Git 历史说明见[本地工作区布局](02_实验/Local_Workspace_Layout.md)。

当前已有规则化 C++ 参考模拟与批量日志；**Continuous Runtime / Engine v1 已 `CLOSED / FROZEN`**：统一时钟、RunningAction、事件/信息边界、DecisionGate、typed rejection、scheduler-native fixtures、trace、case-isolated CTest 与 CI 已闭环。Evaluator、Objective、Optimizer 与 Paper-0 科研验证仍未完成。具体版本与证据只在[当前实现进度](00_研究设计/当前实现进度.md)维护。

2026-10-10 当前路线：**Evennia 为主平台、Ensemble 为首个原生人物机制参照**。P1/P2 已完成；P3-A 单自主 NPC、P3-B 原生 Ensemble 双 NPC 交互当前为 **DEVELOPMENT_VERIFIED（限定场景）**，不是生产就绪或全项目关闭。状态/证据唯一维护于 [Native Platform P3](02_实验/Native_Platform_P3_v0/README.md) / [RESULTS](02_实验/Native_Platform_P3_v0/RESULTS.md)。P1/P2 历史验收和 LIGHT `NO_GO_WITHIN_THIS_TIMEBOX` 保留于[历史结果](02_实验/Native_Platform_P1P2_v0/RESULTS.md)，LIGHT 不阻塞。真人试玩是可选体验反馈、尚未确认，不是技术 gate 或全局 blocker；P4 未授权。旧[技术准入报告](01_文献/技术准入_传统全链基线与文字平台_2026-10-10.md)是候选审查快照；Minecraft/MC 挖煤仍延期。

## 从这里进入

2026-10-09 新授权已撤销“仅外围维护”：按用户目标 TXT 开发的 [NPC System Integration v0](tools/npc_system_v0/README.md) 已贯通有限作者点/线、受限世界规划、独立演员状态/承诺、GOAP/HTN 与真实执行/监测。它是 E1 之上的 **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW** 应用样机，不改冻结 C++ Kernel，也不是完整系统、LLM 高层规划或研究收益。具体能力与限制见[唯一结果](02_实验/NPC_System_Integration_v0/RESULTS.md)；旧语义草案中的未开工叙述按其记录日期理解，当前授权看 [TODO](00_研究设计/TODO.md)。

先看[五分钟现状](00_研究设计/项目现状速览_通俗版.md)，再查[已有结果与复用边界](00_研究设计/研究重建审计_2026-10-06.md#现有结果的成熟度与复用账本截至-2026-10-08)。研究问题与执行语义读[F0/F1草案](00_研究设计/CharacterDynamics_FormalProblem_v0.md)，原算法读[算法积木](01_文献/算法积木/README.md)；不要把候选设计、工程通过和实验结论混成一种进度。

| 要找什么 | 唯一维护位置 |
|---|---|
| 系统主线、Engine / Evaluator / Optimizer、长期研究版图与研究支线 ownership | [系统愿景](00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图) |
| Runtime / Engine v1 的冻结边界与可执行验收 | [Runtime Scheduler](00_研究设计/Runtime_Scheduler_v1.md)；[Closure Matrix](00_研究设计/Runtime_Closure_Acceptance_Matrix.md) |
| 第一个可展示 Demo（单人房间 Runtime Visualizer v0） | [Demo README](Demo%20codex-generated/demo/single_room_v0/README.md)；构建后生成 Deadline / Stale Phone / Commitment traces |
| Demo 长时程行为审计与人格/历史 fork 对照 | [core behavior evaluation v0](Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；仅为 demo development evidence |
| 本机 Laya typed policy（O/S/P 驱动的可回放 policy A/B） | [Laya typed policy](Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；可公开的运行证据见下方审阅索引，只连 loopback 本地 checkpoint，不进入科研线 |
| 整体机制、各层职责、任务/承诺、时间与低耦合 | [完整机制说明](00_研究设计/完整机制说明_v0.md) |
| 旧行为预测 / Paper-0 分支的 Forward/Inverse、候选创新及评价边界 | [分支研究问题](00_研究设计/前台问题与候选创新.md)；当前系统问题另见下方 F0/F1 |
| 项目历史失败、科研证据距离与研究重建顺序 | [研究重建审计（2026-10-06）](00_研究设计/研究重建审计_2026-10-06.md) |
| 尚未定下的计算、具体机制/实现缺口 | [未决问题](00_研究设计/未决问题与机制候选.md) |
| 下一动作、候选 / 暂停状态、依赖与验收 | [TODO](00_研究设计/TODO.md)；LIGHT 来源条件预测支线的任务及结果另由 [SourceRanking README](02_实验/LIGHT_SourceRankingV1/README.md) / [INPUT_REVIEW](02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)维护，不代表全项目下一动作 |
| Self-Play / Self-Evaluation v0 | [评测协议](02_实验/Self_Evaluation_v0.md)；[scorecard runner](tools/self_evaluation_v0.py)；[scenario manifest](tools/self_evaluation_scenarios_v0.json) |
| 实验导出器、切片与可复现记录 | [实验总路由](02_实验/README.md)；[跨数据集 Replay 接口草案](02_实验/跨数据集Replay接口_v0.md)；[机制识别循环与反事实诊断](02_实验/机制识别循环与反事实诊断_v0.md) |
| 当前 Evennia 原生人物实施状态与 P3-A/B 结果 | [Native Platform P3](02_实验/Native_Platform_P3_v0/README.md)；[RESULTS](02_实验/Native_Platform_P3_v0/RESULTS.md) |
| E0 钥匙—账本有限基线的固定协议、代码和实际证据 | [冻结协议](00_研究设计/E0_KeyLedger_Protocol_v0.md)；[代码与复现](tools/e0_keyledger_v0/README.md)；[实验入口](02_实验/E0_KeyLedger_v0/README.md)。独立有限 Executor，不等于 C++ Runtime 集成、NPC 自主性或新方法效果 |
| E1 局部信息与独立 B 策略 | [E1-0 有限协议](00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md)；[E1-1 代码入口](tools/e1_keyledger_v0/runner.py)；[唯一结果 owner](02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)。E1-1 独立开发包已交付；实际状态与证据只查唯一结果 owner。正式实验与 E1-2 未授权 |
| 可运行的有限整合开发样机 | [NPC System Integration v0](tools/npc_system_v0/README.md)；[开发结果与 TXT 映射](02_实验/NPC_System_Integration_v0/RESULTS.md)。实际世界干预、模型/规划替换、director-off 与玩家扰动；不是完整通用系统 |
| WebGPT 审阅：实验报告、逐条结果、失败记录、文献审计及上传排除清单 | [公开审阅索引（2026-10-07）](02_实验/PUBLIC_REVIEW_INDEX_2026-10-07.md) |
| 文献 PDF、职责级阅读与证据 | [文献库](01_文献/README.md) |
| 作者约束系统的问题定义与执行语义（F0/F1） | [Character Dynamics｜系统问题与执行语义 v0](00_研究设计/CharacterDynamics_FormalProblem_v0.md)：DRAFT / READY_FOR_INDEPENDENT_REVIEW，算法无关的唯一问题定义 owner；[System Vision 长期研究版图](00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)保留完整研究方向；[04 综合](01_文献/算法积木/04_统一问题与成熟基线准入.md)维护有限实例的问题与基线准入判断；[AuthorialTrajectoryPilotV0](00_研究设计/AuthorialTrajectoryPilotV0.md)仅为候选 F2 及 TypedIR / 预实验下层 owner，不定义全系统；[算法积木](01_文献/算法积木/README.md)保留具体原算法；[独立reference](tools/trajectory_constraints_v0/README.md)不等于Director或NPC实验 |
| 用户原话、模型提案、对话与来源 | [原始材料](90_原始材料/README.md) |

仓库治理护栏：[ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md)；廉价健康检查可运行 `python tools/repo_health_check.py`，ReplayRecord 样例可用 `python tools/validate_replay_record.py <record.json>` 校验。健康脚本只提供文件大小、重复材料及部分 manifest 告警，不验证文档链接、术语或现状声明；CI 通过也不等于文档语义一致。实现、规格、结果与历史的权威范围见[项目规则](AGENTS.md)。

当前应用目标由用户确认是“NPC 在玩家眼中在游戏里面活起来”，不要求先拟合真实人物心理。[既有近邻与共同小场景检查点](00_研究设计/研究重建审计_2026-10-06.md#已完成执行检查点近邻原件与共同小场景)的 Praxish 原件解释与[共同小场景](02_实验/Praxish_Activity_Pilot_v0/README.md)已有执行证据；2026-10-07 授权的第 3 步已形成[活动组织与独立参数化 utility 的匹配比较结果](02_实验/Praxish_Utility_Comparison_v0/RESULTS.md)，保留真实失败与修改账本，待外审。当前小场景未显示活动组织行为优势；原件 bug 不作为方法收益，不据此开发新心理机制，尚无玩家比较结果。既有 coursework/历史 LLM 探针保留，PredictionBaselineV1 / SourceRankingV1 只作有限来源预测开发证据，不是 NPC 可置信性、心理状态 `S` 或 Runtime policy 训练证据；Paper-0 的独立 `A*` 准入只约束该冻结分支。不能用便宜、能跑或自有评分器的分数替代独立研究证明。作者约束系统的算法无关 F0/F1 定义仍为草案；A（规划/执行能力）与 B（稀疏作者控制）只是近期为基线讨论抽取的研究组合，04 的 Q1–Q3 是有限实例下的候选问题，不代表完整研究任务；长期方向见[System Vision 研究版图](00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)。这些候选分类本身不是新颖性或自动开工承诺；2026-10-09 用户已另行明确授权本页上方的有限应用集成。

## 代码与材料的归属

- [Demo codex-generated](Demo%20codex-generated/README.md)：独立的 Codex C++17 控制台参考实现；构建、运行命令和源码阅读顺序在其 README。
- `E:\Character Dynamics Demo`：用户亲写代码，独立维护，不由本仓库参考实现读取、复制或替代；未核对时不推断其进度。
- [00_研究设计](00_研究设计/README.md)：活动文档各自唯一职责；旧工作稿已移出前台，完整保存于[设计归档](00_研究设计/归档/README.md)。
- `01_文献` 为论文及阅读证据，`90_原始材料` 为原始对话和来源；`tmp/` 为可再生成的本地缓存，不进 Git。

## 维护边界

用户原话是一手方向；模型赞扬、公式、文献线索和新颖性判断不是已证实结论。已有可运行 demo 不代表有经验证研究结果，定向文献库也不能保证没人做过。

按[项目规则](AGENTS.md)和[研究设计路由](00_研究设计/README.md)维护；修改后保存配置、版本、错误和负结果。Verified scoped edits 按 AGENTS.md 提交并推送至 `webgpt-sync`；`main` 受保护，除非对该分支的该次操作有明确授权。
