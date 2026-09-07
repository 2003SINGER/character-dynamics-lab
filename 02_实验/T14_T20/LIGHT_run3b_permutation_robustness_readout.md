# LIGHT Run 3b：permutation-assignment robustness

## 运行边界

Run 3b 不训练任何模型。固定 Run 2 的 frozen-`theta_0`、learned-`w`、dev holdout 和 correct-S，只改变 same-horizon、other-trajectory、no-self 的 donor assignment。共使用 `512` 个 assignment seeds（`20260909`–`20261420`），每个 condition 每套 assignment 都有 `3771` 个 paired rows。

## 跨 assignment 的 `permuted − correct` 分布

区间为 assignment distribution 的 2.5%–97.5% percentile interval，不是 trajectory bootstrap CI。

| condition | mean | median | 2.5%–97.5% interval | fraction > 0 | min | max |
|---|---:|---:|---:|---:|---:|---:|
| Activity-S | `+0.000734889` | `+0.000823283` | `[-0.000400222, +0.001279775]` | `0.9355` | `−0.000827538` | `+0.001541966` |
| ActionSupport-S | `−0.000301793` | `−0.000286316` | `[-0.001669277, +0.001187651]` | `0.3789` | `−0.002261584` | `+0.001500182` |
| Theory-S | `+0.002216673` | `+0.002224560` | `[+0.000822368, +0.003687868]` | `1.0000` | `+0.000344621` | `+0.004473706` |

## 当前读法

- **Theory-S** 的 permutation penalty 跨 assignment 仍稳定为正：均值 `+0.00222`，整个 95% assignment interval 高于 0，`512/512` assignments 为正。因此 Run 3 的 Theory 结论不是某一个 donor assignment 的偶然结果：错误历史归属确实稳定伤害预测。
- **Activity-S** 多数 assignment 为正，但 interval 仍跨 0；其历史归属敏感性弱且不够稳。
- **ActionSupport-S** 没有跨 assignment 的稳定正向 permutation effect。

这进一步巩固了当前结构：Theory-S 对错误历史有稳定敏感性，但正确 Theory-S 仍没有净 predictive gain。暂不修改 Theory representation；下一步才进入“为什么错历史会伤、对历史不增益”的 failure analysis。

结果 artifact：`outputs/experiments/T14_T20_LIGHT_run3b_permutation_robustness_20260907/permutation_robustness_summary.json`。
