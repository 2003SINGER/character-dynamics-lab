# Character Dynamics Lab｜角色动力学实验室

> 长期目标：把作者不同抽象程度、不同控制粒度的创作意图，落实为持续游戏世界中合理、可执行的未来，并随真实反馈调整。角色自己的 Planner 可以承担自驱动；规划层可使用高层语义，不要求每个概念都成为游戏变量。角色与作者规划的目标、信息和控制来源须区分，实际动作仍由游戏结算。详细定义由 [F0/F1](00_研究设计/CharacterDynamics_FormalProblem_v0.md) 唯一维护；旧 C++ 的 OHXSP 不是通用必需 schema，LLM × 成熟规划是待验证路线。

本机唯一 canonical checkout 位于 `/Users/2003singer/Workspace/Research/character-dynamics-lab`；`webgpt-sync` 是项目 review branch owner。工作分支随任务变化，分支归属以 Git 当前状态为准，不在项目总览中固定本地任务分支。实验条件、run ID 与本地原始产物按路径分别保留；迁移映射和 Git 历史说明见[本地工作区布局](02_实验/Local_Workspace_Layout.md)。

旧 C++ **Continuous Runtime / Engine v1 已 `CLOSED / FROZEN`**，其时钟、RunningAction、事件/信息边界与 trace 是该参考实现的工程边界，不定义所有游戏的系统结构。Evaluator、Objective、Optimizer 与旧 Paper-0 科研验证仍未完成。具体版本与证据只在[当前实现进度](00_研究设计/当前实现进度.md)维护。

P1/P2、P3-A/B、P3-C0/C1a 与 P4-0 保留各自历史结果 owner。P5 Author Bundle 为 **READY_FOR_INDEPENDENT_REVIEW**（未 CLOSED）；12 场 development 结果、11/12 结构审计及一个真实 shared-supply 失败见唯一 [P5 RESULTS](02_实验/Native_Platform_P5_v0/RESULTS.md)。P5 的间接 Director 只是一个有限候选模式，不是全系统权限原则；不自动扩展后续阶段。

2026-10-12 **System Baseline v0 当前为 `PARTIAL`**：M1 是 `READY_FOR_INDEPENDENT_REVIEW`，M2 为 `INVALID`；没有 native LLM candidate execution。本阶段在此停止，不进入 P6。唯一状态与运行证据归 [System Baseline v0 RESULTS](02_实验/System_Baseline_v0/RESULTS.md)，当前指针见 [TODO](00_研究设计/TODO.md)；M2 原始调用证据与逐文件 manifest 见[小型证据包](02_实验/System_Baseline_v0/public_evidence/llm-binding-20261012.tar.gz)和[manifest](02_实验/System_Baseline_v0/public_evidence/llm-binding-20261012.manifest.json)。

2026-10-13 **Mature-Methods Integration v1 的 M1–M5 / E1–E4 有界工作包已交付，状态为 `DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW`**。未来新增交接剧情点与失败负控有原生证据；严格历史匹配、工作条件驱动的方法取舍仍未证实。当前代码入口是[持续站点说明](tools/native_platform_v0/p5/ongoing_station/README.md)，运行、失败与对照只见[唯一 RESULTS](02_实验/Mature_Methods_Integration_v1/RESULTS.md)，下一动作见 [TODO](00_研究设计/TODO.md)。本包实施停止，不自动新增阶段；原 S1–S4、S2 权限拒绝、10-12 便条归档、早期站点及[旧 Planner Adapter 结果](02_实验/Planner_Adapter_Integration_v1/RESULTS.md)保留。

**Character Dynamics System Integration 首轮有界实施与原生运行已交付（`bf30d4c`）**：现有站点接入真实共享工具、物资验收/入库与设施检修，接通角色自身过程和作者未来锁；这些是人工新增的限定游戏内容，不是 Evennia 自带玩法、Planner 自行发明规则或通用剧情生成。具体通过项、历史对照未成立及全部失败只见[唯一 RESULTS](02_实验/Mature_Methods_Integration_v1/RESULTS.md)。2026-10-14 的 `872292c` / `8ca0a45` 只修订设计；后续新增实施授权与当前状态见 [TODO](00_研究设计/TODO.md)，接口见[持续站点说明](tools/native_platform_v0/p5/ongoing_station/README.md)。

**2026-10-14 首个外部完整游戏：Open Adventure 1.22 已原样构建并完成三个原生短回放，DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW。**它与 Evennia 手写站点是不同用途的资产：前者已有完整玩法/NPC，后者是引擎上的项目测试内容。该 `354d7ba` 检查点只接整局命令回放，不接 Planner/LLM 或隐藏状态 API。[原结果与能力缺口](02_实验/OpenAdventure_Native_v0/RESULTS.md)记录官方测试、原始输出与原生机制；[薄入口](tools/open_adventure_v0/README.md)提供复现。旧站点重复定义的独立清理见[维护记录](02_实验/Mature_Methods_Integration_v1/MAINTENANCE_20261014.md)，旧 PARTIAL 不升级。

同日后续授权的 **Open Adventure P1 在线闭环已交付，DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW**：同进程逐次输入、合法文字观察、真实拒绝后的程序分支与精确回放已运行，有限检查点已获独立接受；G1–G8、原始记录及失败/修正只见[唯一 P1 RESULTS](02_实验/OpenAdventure_Online_P1_v0/RESULTS.md)。它仍是独立有限接口检查点，不代表全系统 CLOSED。**Open Adventure Planning B0** 已完成，状态为 `DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW`，本轮停止；概况、协议和唯一结果 owner 见 [TODO](00_研究设计/TODO.md)、[PROTOCOL](02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md) 与 [RESULTS](02_实验/OpenAdventure_Planning_B0_v0/RESULTS.md)。三方法比较整体仍为 `PARTIAL`，B1/B2 为 `DEFERRED_BY_USER`，B0本身无模型调用，不自动启动正式模型对照或新游戏。输入请求边界不是 tick 或动作成功。

**LLM-Admission v0（同日后续授权）已交付并停止，READY_FOR_INDEPENDENT_REVIEW**：完成三次真实Luna-in-Codex调用，标为`AGENT_CONFOUNDED`；E未通过固定绑定验收，不补答案、不运行原版任务，G缺口分析保留。请求、原样输出、身份/工具审计和时间语义分歧仅由[唯一 RESULTS](02_实验/LLM_Admission_v0/RESULTS.md)维护。不是正式B1/B2对照或模型优势证据。

**Author Constraint Diagnostic v0（2026-10-15）已交付并停止，READY_FOR_INDEPENDENT_REVIEW**：原四原子未补全，经冻结搜索与一次原版执行通过明确的作者时间语义；原Admission FAIL保留。本轮零模型调用，结果、归属反例和局限仅见[唯一 RESULTS](02_实验/Author_Constraint_Diagnostic_v0/RESULTS.md)，不自动恢复B1/B2或扩展平台。

`c228301` 已收到研究主轴方向的外部通过意见；不是新系统能力验收。[有界强近邻机制对照](01_文献/算法积木/05_游戏世界规划近邻审计_2026-10-11/全量近邻精读总表_2026-10-11.md)作为历史审查检查点保留。原始 P0 A/B 与 LLM/embedding/Qwen 比较的暂停边界见[原始 P0 RESULTS](02_实验/Planner_P0_v0/RESULTS.md)。**P0 Baseline Gate 三场景开发比较已完成，DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW（未 CLOSED）**；唯一结果入口是 [RESULTS](02_实验/Planner_P0_Baseline_Gate_v0/RESULTS.md)。P0-Integration 的独立有限检查点仍见 [RESULTS](02_实验/Planner_P0_Integration_v0/RESULTS.md)。这不表示完整传统系统、独立 NPC agency 或 P5 shared-supply 问题已完成。CI 只验证离线契约；原生运行证据见各自 RESULTS，exact-head workflow 状态以 GitHub Actions 为准。下一步见 [TODO](00_研究设计/TODO.md)。

## 从这里进入

2026-10-16 当前工作为 [Veloren v0.18.0 原生世界纵向验证](02_实验/Veloren_Vertical_Slice_v0/RESULTS.md)：官方 client 与单人 world 已启动，状态为 `ENVIRONMENT_PREPARED`；NPC 程序采集 `NOT_ESTABLISHED`，外部目标闭环 `NOT_RUN`。用户已撤销 GUI baseline 路径，授权有限 server 源码观测与 typedgoal 程序闭环；不使用 GUI、作者节点或 LLM。实施状态仅见 [TODO](00_研究设计/TODO.md) 与唯一 RESULTS；OpenXRay/RimWorld 探索冻结，F0/F1及旧实验不动。

2026-10-09 新授权已撤销“仅外围维护”：按用户目标 TXT 开发的 [NPC System Integration v0](tools/npc_system_v0/README.md) 已贯通有限作者点/线、受限世界规划、独立演员状态/承诺、GOAP/HTN 与真实执行/监测。它是 E1 之上的 **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW** 应用样机，不改冻结 C++ Kernel，也不是完整系统、LLM 高层规划或研究收益。具体能力与限制见[唯一结果](02_实验/NPC_System_Integration_v0/RESULTS.md)；旧语义草案中的未开工叙述按其记录日期理解，当前授权看 [TODO](00_研究设计/TODO.md)。

先看[五分钟现状](00_研究设计/项目现状速览_通俗版.md)，再查[已有结果与复用边界](00_研究设计/研究重建审计_2026-10-06.md#现有结果的成熟度与复用账本截至-2026-10-08)。研究问题与执行语义读[F0/F1草案](00_研究设计/CharacterDynamics_FormalProblem_v0.md)，原算法读[算法积木](01_文献/算法积木/README.md)；不要把候选设计、工程通过和实验结论混成一种进度。

| 要找什么 | 唯一维护位置 |
|---|---|
| 原版游戏逐次观察/行动/反馈、程序 smoke 与 P1 失败 | [Online P1 RESULTS](02_实验/OpenAdventure_Online_P1_v0/RESULTS.md)；[session API 用法](02_实验/OpenAdventure_Online_P1_v0/IMPLEMENTATION.md)，不是模型/规划效果实验 |
| Open Adventure 固定规则下的作者目标与因果规划 B0 | [B0 固定协议](02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md)；运行、失败与成本见[唯一 RESULTS](02_实验/OpenAdventure_Planning_B0_v0/RESULTS.md)。B1/B2 暂缓 |
| 原版完整文字游戏、原生 NPC/因果机制与三条短回放 | [Open Adventure RESULTS](02_实验/OpenAdventure_Native_v0/RESULTS.md)；[命令回放入口](tools/open_adventure_v0/README.md)。不是新规划器实验 |
| System Vision 中的长期研究版图与研究支线 ownership | [系统愿景](00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)；现行问题定义见 F0/F1 |
| Runtime / Engine v1 的冻结边界与可执行验收 | [Runtime Scheduler](00_研究设计/Runtime_Scheduler_v1.md)；[Closure Matrix](00_研究设计/Runtime_Closure_Acceptance_Matrix.md) |
| 第一个可展示 Demo（单人房间 Runtime Visualizer v0） | [Demo README](Demo%20codex-generated/demo/single_room_v0/README.md)；构建后生成 Deadline / Stale Phone / Commitment traces |
| Demo 长时程行为审计与人格/历史 fork 对照 | [core behavior evaluation v0](Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；仅为 demo development evidence |
| 本机 Laya typed policy（O/S/P 驱动的可回放 policy A/B） | [Laya typed policy](Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；可公开的运行证据见下方审阅索引，只连 loopback 本地 checkpoint，不进入科研线 |
| 旧 C++ / Paper-0 参考机制的模块实例与工程语义 | [完整机制说明](00_研究设计/完整机制说明_v0.md)；游戏无关问题定义见 [F0/F1](00_研究设计/CharacterDynamics_FormalProblem_v0.md) |
| 旧行为预测 / Paper-0 分支的 Forward/Inverse、候选创新及评价边界 | [分支研究问题](00_研究设计/前台问题与候选创新.md)；当前系统问题另见下方 F0/F1 |
| 项目历史失败、科研证据距离与研究重建顺序 | [研究重建审计（2026-10-06）](00_研究设计/研究重建审计_2026-10-06.md) |
| 尚未定下的计算、具体机制/实现缺口 | [未决问题](00_研究设计/未决问题与机制候选.md) |
| 下一动作、候选 / 暂停状态、依赖与验收 | [TODO](00_研究设计/TODO.md)；LIGHT 来源条件预测支线的任务及结果另由 [SourceRanking README](02_实验/LIGHT_SourceRankingV1/README.md) / [INPUT_REVIEW](02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)维护，不代表全项目下一动作 |
| Self-Play / Self-Evaluation v0 | [评测协议](02_实验/Self_Evaluation_v0.md)；[scorecard runner](tools/self_evaluation_v0.py)；[scenario manifest](tools/self_evaluation_scenarios_v0.json) |
| 实验导出器、切片与可复现记录 | [实验总路由](02_实验/README.md)；[跨数据集 Replay 接口草案](02_实验/跨数据集Replay接口_v0.md)；[机制识别循环与反事实诊断](02_实验/机制识别循环与反事实诊断_v0.md) |
| P3-A/B 历史证据 | [Native Platform P3](02_实验/Native_Platform_P3_v0/README.md)；[RESULTS](02_实验/Native_Platform_P3_v0/RESULTS.md) |
| P3-C1a 历史阶段证据 | [Native Platform P3-C1a](02_实验/Native_Platform_P3_C1a_v0/README.md)；[RESULTS](02_实验/Native_Platform_P3_C1a_v0/RESULTS.md) |
| P4-0 历史阶段结果 | [README](02_实验/Native_Platform_P4_0_v0/README.md)；[RESULTS 与完整证据](02_实验/Native_Platform_P4_0_v0/RESULTS.md) |
| 当前 P5 Author Bundle 阶段 | [P5 README](02_实验/Native_Platform_P5_v0/README.md)；[唯一 RESULTS](02_实验/Native_Platform_P5_v0/RESULTS.md)；[核心 API](tools/native_platform_v0/p5/README.md) |
| E0 钥匙—账本有限基线的固定协议、代码和实际证据 | [冻结协议](00_研究设计/E0_KeyLedger_Protocol_v0.md)；[代码与复现](tools/e0_keyledger_v0/README.md)；[实验入口](02_实验/E0_KeyLedger_v0/README.md)。独立有限 Executor，不等于 C++ Runtime 集成、NPC 自主性或新方法效果 |
| E1 局部信息与独立 B 策略 | [E1-0 有限协议](00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md)；[E1-1 代码入口](tools/e1_keyledger_v0/runner.py)；[唯一结果 owner](02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)。E1-1 独立开发包已交付；实际状态与证据只查唯一结果 owner。正式实验与 E1-2 未授权 |
| 可运行的有限整合开发样机 | [NPC System Integration v0](tools/npc_system_v0/README.md)；[开发结果与 TXT 映射](02_实验/NPC_System_Integration_v0/RESULTS.md)。实际世界干预、模型/规划替换、director-off 与玩家扰动；不是完整通用系统 |
| WebGPT 审阅：实验报告、逐条结果、失败记录、文献审计及上传排除清单 | [公开审阅索引（2026-10-07）](02_实验/PUBLIC_REVIEW_INDEX_2026-10-07.md) |
| 文献 PDF、职责级阅读与证据 | [文献库](01_文献/README.md) |
| 作者约束下游戏世界在线规划与控制的问题定义 | [F0/F1](00_研究设计/CharacterDynamics_FormalProblem_v0.md)是唯一问题定义 owner；[System Vision](00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)维护长期研究版图；[Pilot](00_研究设计/AuthorialTrajectoryPilotV0.md)只维护局部 TypedIR/reference 契约；原算法见[算法积木](01_文献/算法积木/README.md) |
| 用户原话、模型提案、对话与来源 | [原始材料](90_原始材料/README.md) |

仓库治理护栏：[ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md)；廉价健康检查可运行 `python tools/repo_health_check.py`，ReplayRecord 样例可用 `python tools/validate_replay_record.py <record.json>` 校验。健康脚本只提供文件大小、重复材料及部分 manifest 告警，不验证文档链接、术语或现状声明；CI 通过也不等于文档语义一致。实现、规格、结果与历史的权威范围见[项目规则](AGENTS.md)。

当前没有新机制、组合增益或人类可信度证据。2026-10-12 新定向审阅指出的独立方法选择缺口，已通过用户授权的同阶段便条归档增量进行有限原生实现与开发验收；其状态为 `DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW`。实现边界见[故事过程代码说明](tools/native_platform_v0/p5/story_process/README.md)，事实和限制只见唯一[本轮 RESULTS](02_实验/Mature_Methods_Integration_v1/RESULTS.md)，执行指针见 [TODO](00_研究设计/TODO.md)。不据此主张方法收益或玩家可信度，不改写历史候选、旧有限实例和 P5 结果。Paper-0 的独立 `A*` 准入只约束旧预测分支，不是当前游戏规划目标的前置门。

## 代码与材料的归属

- [Demo codex-generated](Demo%20codex-generated/README.md)：独立的 Codex C++17 控制台参考实现；构建、运行命令和源码阅读顺序在其 README。
- `E:\Character Dynamics Demo`：用户亲写代码，独立维护，不由本仓库参考实现读取、复制或替代；未核对时不推断其进度。
- [00_研究设计](00_研究设计/README.md)：活动文档各自唯一职责；旧工作稿已移出前台，完整保存于[设计归档](00_研究设计/归档/README.md)。
- `01_文献` 为论文及阅读证据，`90_原始材料` 为原始对话和来源；`tmp/` 为可再生成的本地缓存，不进 Git。

## 维护边界

用户原话是一手方向；模型赞扬、公式、文献线索和新颖性判断不是已证实结论。已有可运行 demo 不代表有经验证研究结果，定向文献库也不能保证没人做过。

按[项目规则](AGENTS.md)和[研究设计路由](00_研究设计/README.md)维护；修改后保存配置、版本、错误和负结果。Verified scoped edits 按 AGENTS.md 提交并推送至 `webgpt-sync`；`main` 受保护，除非对该分支的该次操作有明确授权。
