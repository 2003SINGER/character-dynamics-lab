# 实验路由

当前主线是 T14/T20 rank-matched 1D development harness：LIGHT Replay → SceneSnapshot → raw feature v1 → Activity/ActionSupport/Theory S → conditional linear probe → zeroed/permuted diagnostics。入口：`T14_T20/run_rank_matched_probe_v1.py`。

该 runner 输出 `development_only` 且 `formal_test=false`；正式行为真值准入前不得把 dev holdout 当 Paper-0 test。

`T14_T20_rank_matched_probe_v1.md`、`Replay/replay_features_v1.py`、`Replay/replay_probe_v1.py` 是当前候选协议与训练设施；v0 协议、`drive-linear-v0` 与 C++ `replay_core_cli` 仅作历史 diagnostic/repro path，不是当前 T14/T20 policy。其他数据集按各自 README 的准入状态维护。
