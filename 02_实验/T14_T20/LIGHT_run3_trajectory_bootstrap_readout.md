# LIGHT Run 3：trajectory-level paired bootstrap

## 运行边界

Run 3 不训练任何模型；直接读取 Run 2 的 frozen-`theta_0` + learned-`w` artifacts，在同一 dev holdout、同一 paired intervention rows 上进行 trajectory-level 有放回抽样。每次 bootstrap 保留被抽中 trajectory 的全部 decision rows。`B=2000`，trajectory 数 `1089`，paired rows `3771`。

## 结果

95% CI 为 percentile CI；`fraction(Δ>0)` 是 bootstrap replicate 中差值为正的比例。

| condition | quantity | point Δ | bootstrap mean | 95% CI | fraction Δ>0 |
|---|---|---:|---:|---:|---:|
| Activity-S | zero − correct | `+0.002426693` | `+0.002260019` | `[-0.002930628, +0.006770502]` | `0.8195` |
| Activity-S | perm − correct | `+0.000834690` | `+0.000834488` | `[-0.000376120, +0.002713446]` | `0.8560` |
| Activity-S | frozen-base − correct | `+0.002426693` | `+0.002379695` | `[-0.003010151, +0.006694102]` | `0.8260` |
| ActionSupport-S | zero − correct | `+0.000058474` | `+0.000021811` | `[-0.002639718, +0.002217220]` | `0.5330` |
| ActionSupport-S | perm − correct | `−0.001065189` | `−0.001087295` | `[-0.002245749, +0.000025490]` | `0.0280` |
| Theory-S | zero − correct | `+0.000015357` | `−0.000019162` | `[-0.002300173, +0.001976268]` | `0.5080` |
| Theory-S | perm − correct | `+0.004105825` | `+0.004088965` | `[+0.001809099, +0.006384313]` | `0.9990` |

## 当前读法

- **Activity-S**：point estimate 支持净增量和轻微 permutation penalty，但两个 CI 都跨 0；在当前 dev cohort 上尚不能把这两个小效应称为稳定现象。
- **ActionSupport-S**：zero effect centered near 0；permutation point estimate 为负，bootstrap 也几乎总为负，但 CI 仍触及 0，暂不主张历史归属价值。
- **Theory-S**：zero effect 仍稳定在 0 附近；但 `perm − correct` 的 CI 完全高于 0，trajectory-level evidence 支持“错误历史归属会伤害”。这仍不等于正确 Theory-S 有净 predictive gain。

因此当前最稳妥的二维读法是：Activity 的净收益尚不稳；ActionSupport 没有可靠增量；Theory 没有可靠 zero-vs-correct 增量，但有较稳定的 trajectory-specific permutation sensitivity。暂不修改 Theory representation。

结果 artifact：`outputs/experiments/T14_T20_LIGHT_run3_trajectory_bootstrap_20260907/bootstrap_summary.json`。
