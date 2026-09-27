# Character Dynamics Lab｜角色动力学实验室

> 一个面向可持续运行 NPC 的角色动力学框架：让常规决策由可审计的局部观察、持续状态与廉价策略完成，只在必要时调用开放语义模型，并同时优化长期行为质量与运行成本。

当前已有规则化 C++ 参考模拟与批量日志；**Continuous Runtime / Engine v1 已 `CLOSED / FROZEN`**：统一时钟、RunningAction、事件/信息边界、DecisionGate、typed rejection、scheduler-native fixtures、trace、case-isolated CTest 与 CI 已闭环。Evaluator、Objective、Optimizer 与 Paper-0 科研验证仍未完成。具体版本与证据只在[当前实现进度](00_研究设计/当前实现进度.md)维护。

## 从这里进入

| 要找什么 | 唯一维护位置 |
|---|---|
| 系统主线、Engine / Evaluator / Optimizer 与研究支线 ownership | [系统愿景](00_研究设计/Character_Dynamics_System_Vision_v0.md) |
| Runtime / Engine v1 的冻结边界与可执行验收 | [Runtime Scheduler](00_研究设计/Runtime_Scheduler_v1.md)；[Closure Matrix](00_研究设计/Runtime_Closure_Acceptance_Matrix.md) |
| 第一个可展示 Demo（单人房间 Runtime Visualizer v0） | [Demo README](Demo%20codex-generated/demo/single_room_v0/README.md)；构建后生成 Deadline / Stale Phone / Commitment traces |
| Demo 长时程行为审计与人格/历史 fork 对照 | [core behavior evaluation v0](Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；仅为 demo development evidence |
| 本机 Laya typed policy（O/S/P 驱动的可回放 policy A/B） | [Laya typed policy](Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；本机运行数据在 `outputs/laya_runs/`（Git 忽略），只连 loopback 本地 checkpoint，不进入科研线 |
| 整体机制、各层职责、任务/承诺、时间与低耦合 | [完整机制说明](00_研究设计/完整机制说明_v0.md) |
| 研究问题、Forward/Inverse、候选创新及评价边界 | [研究问题](00_研究设计/前台问题与候选创新.md) |
| 尚未定下的计算、具体机制/实现缺口 | [未决问题](00_研究设计/未决问题与机制候选.md) |
| 下一动作、依赖与验收 | [TODO](00_研究设计/TODO.md)；当前仅推进 M2 candidate-set admission |
| Self-Play / Self-Evaluation v0 | [评测协议](02_实验/Self_Evaluation_v0.md)；[scorecard runner](tools/self_evaluation_v0.py)；[scenario manifest](tools/self_evaluation_scenarios_v0.json) |
| 实验导出器、切片与可复现记录 | [实验总路由](02_实验/README.md)；[跨数据集 Replay 接口草案](02_实验/跨数据集Replay接口_v0.md)；[机制识别循环与反事实诊断](02_实验/机制识别循环与反事实诊断_v0.md) |
| 文献 PDF、职责级阅读与证据 | [文献库](01_文献/README.md) |
| 用户原话、模型提案、对话与来源 | [原始材料](90_原始材料/README.md) |

仓库治理护栏：[ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md)；廉价健康检查可运行 `python tools/repo_health_check.py`，ReplayRecord 样例可用 `python tools/validate_replay_record.py <record.json>` 校验。护栏只预警文件膨胀/重复归档，明确的 schema、CTest 和 provenance 错误才阻断对应检查。

新想法只在直接服务“维护行为相关状态／预测生成行为”时进入当前主线。效率—效果与可控性是第二评价维度，比较对象必须包含强 summary，不能用便宜或能跑替代研究证明。

## 代码与材料的归属

- [Demo codex-generated](Demo%20codex-generated/README.md)：独立的 Codex C++17 控制台参考实现；构建、运行命令和源码阅读顺序在其 README。
- `E:\Character Dynamics Demo`：用户亲写代码，独立维护，不由本仓库参考实现读取、复制或替代；未核对时不推断其进度。
- [00_研究设计](00_研究设计/README.md)：活动文档各自唯一职责；旧工作稿已移出前台，完整保存于[设计归档](00_研究设计/归档/README.md)。
- `01_文献` 为论文及阅读证据，`90_原始材料` 为原始对话和来源；`tmp/` 为可再生成的本地缓存，不进 Git。

## 维护边界

用户原话是一手方向；模型赞扬、公式、文献线索和新颖性判断不是已证实结论。已有可运行 demo 不代表有经验证研究结果，定向文献库也不能保证没人做过。

按[项目规则](AGENTS.md)和[研究设计路由](00_研究设计/README.md)维护；修改后保存配置、版本、错误和负结果。本地验证后提交，只有用户本轮明确要求才推送。
