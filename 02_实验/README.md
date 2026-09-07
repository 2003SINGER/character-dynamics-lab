# 实验路由

当前主线是 T14/T20 rank-matched 1D development harness：LIGHT Replay → SceneSnapshot → raw feature v1 → Activity/ActionSupport/Theory S → conditional linear probe → zeroed/permuted diagnostics。

- **Run 1 / full-refit**：`T14_T20/run_rank_matched_probe_v1.py`，各 condition 同时拟合 `theta + w`。
- **Run 1b / frozen-model intervention**：`T14_T20/run_rank_matched_intervention_v1.py`，复用 Run 1 模型，不训练，做 correct/zeroed/permuted。
- **Run 2 / frozen-theta incremental**：`T14_T20/run_frozen_base_incremental_v1.py`，读取 Run 1 no-S 的 frozen `theta_0`，只拟合 `w`。
- **Run 3 / trajectory bootstrap**：`T14_T20/run_trajectory_bootstrap_v1.py`，不训练，按 trajectory 对 Run 2 的 paired effects 做 bootstrap CI。
- **Run 3b / permutation-assignment robustness**：`T14_T20/run_permutation_assignment_robustness_v1.py`，不训练，跨多套合法 same-horizon donor assignment 检验 permutation effect 的稳健性。
- **Run 4 / Theory-S failure decomposition**：`T14_T20/run_theory_failure_decomposition_v1.py`，不训练，只解析已有 frozen Theory-S 的逐行 loss、fresh/residual 状态来源与幅值匹配。

该 runner 输出 `development_only` 且 `formal_test=false`；正式行为真值准入前不得把 dev holdout 当 Paper-0 test。

`T14_T20_rank_matched_probe_v1.md`、`Replay/replay_features_v1.py`、`Replay/replay_probe_v1.py` 是当前候选协议与训练设施；v0 协议、`drive-linear-v0` 与 C++ `replay_core_cli` 仅作历史 diagnostic/repro path，不是当前 T14/T20 policy。其他数据集按各自 README 的准入状态维护。
