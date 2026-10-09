# 实验路由

面向 WebGPT 的报告、原始结果/逐条预测、历史失败、文献审计和精确上传/排除清单统一见[公开审阅索引](PUBLIC_REVIEW_INDEX_2026-10-07.md)。`outputs/` 仍默认忽略；清单中批准的结果按原路径显式跟踪，不因此公开数据集输入或构建缓存。

## 当前状态与结果复用

2026-10-09 用户另行明确授权按目标 TXT 改系统：[NPC System Integration v0](NPC_System_Integration_v0/RESULTS.md) 已形成有限 DEVELOPMENT 应用闭环，含合法世界干预、演员状态/承诺、GOAP/HTN、director-off 和玩家扰动。它是新的有限软件开发验收，不是 NPC 玩家实验、E1-2 formal、心理训练或冻结 Runtime 改动；下方 E1-1 交付时的范围不禁止该新应用。

截至 2026-10-09，NPC 玩家实验、训练、玩家招募和冻结 Runtime 修改均未新增/授权。**独立的小型有限域软件验收例外**包括已冻结的 E0-KeyLedger-v0，以及已获用户授权并已交付独立开发包的 E1-1；E1 正式实验和 E1-2 未授权。E0 的实现与结果只维护在 [E0 实验入口](E0_KeyLedger_v0/README.md)。E1 协议见[有限协议](../00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md)，代码入口见[开发 runner](../tools/e1_keyledger_v0/runner.py)，实际状态与证据只查唯一结果 owner：[E1 RESULTS](E1_KeyLedger_LocalAgency_v0/RESULTS.md)。不将其扩展为 NPC 效度或心理机制证据。各既有科研结果的成熟度、已回答问题、可复用边界、未补证据和唯一 owner 统一见[研究重建审计的结果复用账本](../00_研究设计/研究重建审计_2026-10-06.md#现有结果的成熟度与复用账本截至-2026-10-08)。作者约束系统的当前设计入口是 [F0/F1 草案](../00_研究设计/CharacterDynamics_FormalProblem_v0.md)（DRAFT / READY_FOR_INDEPENDENT_REVIEW）；AuthorialTrajectoryPilotV0 是候选 F2 / TypedIR 与预实验下层 owner，不是全系统定义。

本机工作区、历史 checkout 与运行产物的路径边界见[本地工作区布局](Local_Workspace_Layout.md)。迁移不改变实验条件或 run ID，也不授权启动新实验。

已有玩家 NPC 小场景比较的结果入口：[Praxish 与参数化 utility 的匹配比较](Praxish_Utility_Comparison_v0/RESULTS.md)记录了有界 **DEVELOPMENT / NO_GO**：不支持以活动组织本身改善该共同场景行为为理由立项，不是否定整个方向。前两步原件运行/机制解释与“自有工作＋外来请求”场景由[Praxish Activity Pilot v0](Praxish_Activity_Pilot_v0/README.md)保留。比较采用原件离散 turn 和全共享知识，不接 ContinuousRuntime、不训练，也不把条件演示当作方法胜出；作者成本和玩家意义仍未验证。既有 coursework/历史 LLM 探针保留但不混入该比较。

旧 continuity pilot 的[阶段 1—3 DEVELOPMENT 检查点](../Demo%20codex-generated/applications/npc_continuity_v0/STAGE3_CHECKPOINT.md)已交付并保留：utility 与历史 LLM 的小窗条件、短轨迹和匿名回放不归零；该任务在阶段 3 检查后停止，未进入阶段 4。它不是玩家效度结论，也不代表本轮启动或批准了新实验。后续若讨论是否推进，先按结果复用账本补齐基线、呈现和准入问题。

已有方法开发结果入口：[PredictionBaselineV1](PredictionBaselineV1/README.md) 的 DEVELOPMENT fit 与独立 seed 复现已完成，待外审；唯一数值结果见[RESULTS](PredictionBaselineV1/RESULTS.md)。这不是本轮新拟合授权。它是 DEVELOPMENT 条件预测基座，不是已学习的心理 `S` 或 Runtime policy；研究重建顺序与证据边界见[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)。`ResearchDynamicsV1` 是手写固定-law fixture，当前机制验收不足，未作为 admitted science model。旧 `Theory_S_v2` 是 `ExpectedEffectEMAProxyV0` 历史诊断 proxy；不得把它写成已验证角色动力学。

本目录是实验路由索引，不宣布全项目当前阶段。Canonical layers are: `Replay/` for source-neutral records/features, `PredictionBaselineV1` for the fitted and reproducible development prediction method base awaiting independent review, `ExpectedEffectEMAProxyV0` for historical Theory-S diagnostics, and `T14_T20/` for the frozen 1D development harness. Source action labels and source candidate lists retain dataset provenance; source candidates are not character `A^O`. New method work must use episode-grouped train/validation. All previously exposed datasets are development data, not untouched formal test.

当前数据 gate：[LIGHT source/任务准入审计](../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)，完整 actor-visible contract 仍未准入。[LIGHT_SourceRankingV1](LIGHT_SourceRankingV1/README.md)是另立的 DEVELOPMENT 来源记录条件排名协议；[INPUT_REVIEW](LIGHT_SourceRankingV1/INPUT_REVIEW.md)唯一维护输入/训练器验收、单独执行准入与实际运行进度；不替代 Paper-0 或调 Runtime。

`PredictionBaselineV1` compares standard categorical cross-entropy O-only, low-order history, mean-history, and executable sequence baselines such as GRU. This is not a total-capacity-matched comparison and does not claim psychological semantics or Paper-0 formal PASS. Development fit and exact seed reproduction are complete; independent review is pending. Paper-0 candidate-set admission remains a formal blocker but no longer prevents development method learning.

Mechanism 表达力与候选集边界的独立工程验收见 [Mechanism Sanity v1](Mechanism_Sanity_v1/README.md) 与 [v1.2 trajectory sanity](Mechanism_Sanity_v1_2/README.md)。它们不启动正式 NLL/Experiment B，不读取或修改 T14/T20 的 strict-v2 protocol/validator/shards/status/results。

- **Run 1 / full-refit**：`T14_T20/run_rank_matched_probe_v1.py`，各 condition 同时拟合 `theta + w`。
- **Run 1b / frozen-model intervention**：`T14_T20/run_rank_matched_intervention_v1.py`，复用 Run 1 模型，不训练，做 correct/zeroed/permuted。
- **Run 2 / frozen-theta incremental**：`T14_T20/run_frozen_base_incremental_v1.py`，读取 Run 1 no-S 的 frozen `theta_0`，只拟合 `w`。
- **Run 3 / trajectory bootstrap**：`T14_T20/run_trajectory_bootstrap_v1.py`，不训练，按 trajectory 对 Run 2 的 paired effects 做 bootstrap CI。
- **Run 3b / permutation-assignment robustness**：`T14_T20/run_permutation_assignment_robustness_v1.py`，不训练，跨多套合法 same-horizon donor assignment 检验 permutation effect 的稳健性。
- **Run 4 / Theory-S failure decomposition**：`T14_T20/run_theory_failure_decomposition_v1.py`，不训练，只解析已有 frozen Theory-S 的逐行 loss、fresh/residual 状态来源与幅值匹配。

该 runner 输出 `development_only` 且 `formal_test=false`；正式行为真值准入前不得把 dev holdout 当 Paper-0 test。

本地外部实验/基准 payload 位于 [`outputs/external_assets_2026-09-06`](../outputs/external_assets_2026-09-06/)；其 provenance 与原始复核/对话证据分开维护。该归档不代表任何数据集已经通过本项目的 adapter、语义准入或 Paper-0 candidate/action-surface gate。

`T14_T20_rank_matched_probe_v1.md`、`Replay/replay_features_v1.py`、`Replay/replay_probe_v1.py` 是既有 1D development 协议与训练设施；不构成正式独立验证。H0b/compression 的旧 actor-unit split 有 episode overlap：见 [read-only split audit](../outputs/research_reset_audit_20261006/split_audit_v3.json)，旧数值/artifact 保留但泛化强度降级。`Theory_S_v2/` 保留为历史 proxy implementation/repro path，不是当前已训练模型。其他数据集按各自 README 的 admission 状态维护。
# 历史研究与 Demo 边界记录（2026-09-16）

这段保留 2026-09-16 的阶段描述，不再定义当前 research candidate。当前方法入口与状态以本 README 上文及[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)为准。C++ `ReferenceRuleDynamicsV0` 是工程/reference baseline，`DemoLivingDynamicsV0` 与 `FREE_RUN_6H` 是 application-only；共用 Runtime contract 不等于研究证据。
