# 实验路由

本机工作区、历史 checkout 与运行产物的路径边界见[本地工作区布局](Local_Workspace_Layout.md)。迁移不改变实验条件或 run ID，也不授权启动新实验。

当前方法开发入口：[PredictionBaselineV1](PredictionBaselineV1/README.md) development fit 与独立 seed 复现已完成，待外审；唯一数值结果见[RESULTS](PredictionBaselineV1/RESULTS.md)。它是 DEVELOPMENT 条件预测基座，不是已学习的心理 `S` 或 Runtime policy；研究重建顺序与证据边界见[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)。`ResearchDynamicsV1` 是手写固定-law fixture，当前机制验收不足，未作为 admitted science model。旧 `Theory_S_v2` 是 `ExpectedEffectEMAProxyV0` 历史诊断 proxy；不得把它写成已验证角色动力学。

本目录是实验路由索引，不宣布全项目当前阶段。Canonical layers are: `Replay/` for source-neutral records/features, `PredictionBaselineV1` for the fitted and reproducible development prediction method base awaiting independent review, `ExpectedEffectEMAProxyV0` for historical Theory-S diagnostics, and `T14_T20/` for the frozen 1D development harness. Source action labels and source candidate lists retain dataset provenance; source candidates are not character `A^O`. New method work must use episode-grouped train/validation. All previously exposed datasets are development data, not untouched formal test.

当前数据 gate：[LIGHT source/任务准入审计](../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)。原始映射、before-turn 候选重建及全量代码信息流检查完成；当前源 context/support 的时点和 partner 动作可见表示仍未准入。下一动作是 source/observation contract 验收，不是追加训练或调 Runtime。

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
