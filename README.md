# Character Dynamics Lab｜角色动力学实验室

> 一个面向可持续运行 NPC 的角色动力学框架：让常规决策由可审计的局部观察、持续状态与廉价策略完成，只在必要时调用开放语义模型，并同时优化长期行为质量与运行成本。

本机唯一 canonical checkout 位于 `/Users/2003singer/Workspace/Research/character-dynamics-lab`，当前活动分支为 `webgpt-sync`。实验条件、run ID 与本地原始产物按路径分别保留；迁移映射和 Git 历史说明见[本地工作区布局](02_实验/Local_Workspace_Layout.md)。

当前已有规则化 C++ 参考模拟与批量日志；**Continuous Runtime / Engine v1 已 `CLOSED / FROZEN`**：统一时钟、RunningAction、事件/信息边界、DecisionGate、typed rejection、scheduler-native fixtures、trace、case-isolated CTest 与 CI 已闭环。Evaluator、Objective、Optimizer 与 Paper-0 科研验证仍未完成。具体版本与证据只在[当前实现进度](00_研究设计/当前实现进度.md)维护。

## 从这里进入

| 要找什么 | 唯一维护位置 |
|---|---|
| 系统主线、Engine / Evaluator / Optimizer 与研究支线 ownership | [系统愿景](00_研究设计/Character_Dynamics_System_Vision_v0.md) |
| Runtime / Engine v1 的冻结边界与可执行验收 | [Runtime Scheduler](00_研究设计/Runtime_Scheduler_v1.md)；[Closure Matrix](00_研究设计/Runtime_Closure_Acceptance_Matrix.md) |
| 第一个可展示 Demo（单人房间 Runtime Visualizer v0） | [Demo README](Demo%20codex-generated/demo/single_room_v0/README.md)；构建后生成 Deadline / Stale Phone / Commitment traces |
| Demo 长时程行为审计与人格/历史 fork 对照 | [core behavior evaluation v0](Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；仅为 demo development evidence |
| 本机 Laya typed policy（O/S/P 驱动的可回放 policy A/B） | [Laya typed policy](Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；可公开的运行证据见下方审阅索引，只连 loopback 本地 checkpoint，不进入科研线 |
| 整体机制、各层职责、任务/承诺、时间与低耦合 | [完整机制说明](00_研究设计/完整机制说明_v0.md) |
| 研究问题、Forward/Inverse、候选创新及评价边界 | [研究问题](00_研究设计/前台问题与候选创新.md) |
| 项目历史失败、科研证据距离与研究重建顺序 | [研究重建审计（2026-10-06）](00_研究设计/研究重建审计_2026-10-06.md) |
| 尚未定下的计算、具体机制/实现缺口 | [未决问题](00_研究设计/未决问题与机制候选.md) |
| 下一动作、依赖与验收 | [TODO](00_研究设计/TODO.md)；[LIGHT source-conditional 冻结任务规格](02_实验/LIGHT_SourceRankingV1/README.md)；当前训练器验收、执行准入与运行进度只见[INPUT_REVIEW](02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)；[完整 actor-visible / Paper-0 准入](01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)仍未过 |
| Self-Play / Self-Evaluation v0 | [评测协议](02_实验/Self_Evaluation_v0.md)；[scorecard runner](tools/self_evaluation_v0.py)；[scenario manifest](tools/self_evaluation_scenarios_v0.json) |
| 实验导出器、切片与可复现记录 | [实验总路由](02_实验/README.md)；[跨数据集 Replay 接口草案](02_实验/跨数据集Replay接口_v0.md)；[机制识别循环与反事实诊断](02_实验/机制识别循环与反事实诊断_v0.md) |
| WebGPT 审阅：实验报告、逐条结果、失败记录、文献审计及上传排除清单 | [公开审阅索引（2026-10-07）](02_实验/PUBLIC_REVIEW_INDEX_2026-10-07.md) |
| 文献 PDF、职责级阅读与证据 | [文献库](01_文献/README.md) |
| 当前作者约束线：第一阶段算法地基与组合接缝 | [算法积木总表与唯一下一动作](01_文献/算法积木/README.md)；含12张主卡、权限/现行接口对照、手推及本人新理解栏；[前轮轨迹/执行世界续审](01_文献/专题调研_多层状态轨迹约束与可执行世界_2026-10-07.md)保留为依据；非新方法或已运行 benchmark |
| 用户原话、模型提案、对话与来源 | [原始材料](90_原始材料/README.md) |

仓库治理护栏：[ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md)；廉价健康检查可运行 `python tools/repo_health_check.py`，ReplayRecord 样例可用 `python tools/validate_replay_record.py <record.json>` 校验。护栏只预警文件膨胀/重复归档，明确的 schema、CTest 和 provenance 错误才阻断对应检查。

当前应用目标由用户确认是“NPC 在玩家眼中在游戏里面活起来”，不要求先拟合真实人物心理。[当前研究推进](00_研究设计/研究重建审计_2026-10-06.md#当前推进近邻原件与共同小场景)的 Praxish 原件解释与[共同小场景](02_实验/Praxish_Activity_Pilot_v0/README.md)已有执行证据；2026-10-07 授权的第 3 步已形成[活动组织与独立参数化 utility 的匹配比较结果](02_实验/Praxish_Utility_Comparison_v0/RESULTS.md)，保留真实失败与修改账本，待外审。当前小场景未显示活动组织行为优势；原件 bug 不作为方法收益，不据此开发新心理机制，尚无玩家比较结果。既有 coursework/历史 LLM 探针保留，PredictionBaselineV1 / SourceRankingV1 只作有限来源预测开发证据，不是 NPC 可置信性、心理状态 `S` 或 Runtime policy 训练证据；Paper-0 的独立 `A*` 准入只约束该冻结分支。不能用便宜、能跑或自有评分器的分数替代独立研究证明。

## 代码与材料的归属

- [Demo codex-generated](Demo%20codex-generated/README.md)：独立的 Codex C++17 控制台参考实现；构建、运行命令和源码阅读顺序在其 README。
- `E:\Character Dynamics Demo`：用户亲写代码，独立维护，不由本仓库参考实现读取、复制或替代；未核对时不推断其进度。
- [00_研究设计](00_研究设计/README.md)：活动文档各自唯一职责；旧工作稿已移出前台，完整保存于[设计归档](00_研究设计/归档/README.md)。
- `01_文献` 为论文及阅读证据，`90_原始材料` 为原始对话和来源；`tmp/` 为可再生成的本地缓存，不进 Git。

## 维护边界

用户原话是一手方向；模型赞扬、公式、文献线索和新颖性判断不是已证实结论。已有可运行 demo 不代表有经验证研究结果，定向文献库也不能保证没人做过。

按[项目规则](AGENTS.md)和[研究设计路由](00_研究设计/README.md)维护；修改后保存配置、版本、错误和负结果。Verified scoped edits 按 AGENTS.md 提交并推送至 `webgpt-sync`；`main` 受保护，除非对该分支的该次操作有明确授权。
