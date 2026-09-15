# 实验路由

本目录是实验路由索引，不宣布全项目当前阶段。Canonical layers are: `Replay/` for source-neutral records/features/baselines, `Theory_S_v2/` for the single Python trainable dynamics candidate, and `T14_T20/` for the frozen 1D historical development harness. New external training must compose these layers rather than copy Theory-S per dataset.

Mechanism 表达力与候选集边界的独立工程验收见 [Mechanism Sanity v1](Mechanism_Sanity_v1/README.md) 与 [v1.2 trajectory sanity](Mechanism_Sanity_v1_2/README.md)。它们不启动正式 NLL/Experiment B，不读取或修改 T14/T20 的 strict-v2 protocol/validator/shards/status/results。

- **Run 1 / full-refit**：`T14_T20/run_rank_matched_probe_v1.py`，各 condition 同时拟合 `theta + w`。
- **Run 1b / frozen-model intervention**：`T14_T20/run_rank_matched_intervention_v1.py`，复用 Run 1 模型，不训练，做 correct/zeroed/permuted。
- **Run 2 / frozen-theta incremental**：`T14_T20/run_frozen_base_incremental_v1.py`，读取 Run 1 no-S 的 frozen `theta_0`，只拟合 `w`。
- **Run 3 / trajectory bootstrap**：`T14_T20/run_trajectory_bootstrap_v1.py`，不训练，按 trajectory 对 Run 2 的 paired effects 做 bootstrap CI。
- **Run 3b / permutation-assignment robustness**：`T14_T20/run_permutation_assignment_robustness_v1.py`，不训练，跨多套合法 same-horizon donor assignment 检验 permutation effect 的稳健性。
- **Run 4 / Theory-S failure decomposition**：`T14_T20/run_theory_failure_decomposition_v1.py`，不训练，只解析已有 frozen Theory-S 的逐行 loss、fresh/residual 状态来源与幅值匹配。

该 runner 输出 `development_only` 且 `formal_test=false`；正式行为真值准入前不得把 dev holdout 当 Paper-0 test。

本地外部实验/基准 payload 位于 [`outputs/external_assets_2026-09-06`](../outputs/external_assets_2026-09-06/)；[`_external_datasets_2026-09-08`](_external_datasets_2026-09-08/) 只保留 tracked provenance/readme 层，与 `90_原始材料` 的原始复核/对话证据分开。该归档不代表任何数据集已经通过本项目的 adapter、语义准入或 Paper-0 candidate/action-surface gate。

`T14_T20_rank_matched_probe_v1.md`、`Replay/replay_features_v1.py`、`Replay/replay_probe_v1.py` 是既有 1D 候选协议与训练设施；`Theory_S_v2/` 是后续 trainable dynamics candidate，但尚未进入真实 development training。v0 协议、`drive-linear-v0` 与 C++ `replay_core_cli` 仅作历史 diagnostic/repro path。其他数据集按各自 README 的准入状态维护。
