# LIGHT Run 4：Theory-S failure decomposition

## 运行边界

Run 4 只审问 Run 2 已冻结的 Theory-S interaction，不训练任何参数。对每个 dev-holdout row 计算

`L_i(s) = -log softmax(theta_0^T f_i + s * w^T f_i)[gold]`

并记录 correct state 的 `zero_delta = L_i(0) − L_i(S_i)`、`slope0 = dL_i/ds |_{s=0}`，以及区间 `[0, max(1, 2*max(S_i, fresh_signal_i))]` 上的逐行最优 `s*`。

## 总体结果

- rows：`3772`
- Theory state nonzero：`19.96%`
- fresh signal (`positive_conduciveness > 0`)：`7.79%`
- overall `zero_delta` mean：`+0.000015353`
- overall `zero_delta` median：`0`
- rows helped (`zero_delta > 0`)：`11.72%`
- rows hurt (`zero_delta < 0`)：`8.24%`

平均净效应接近 0，主要是两类非零状态的抵消，而不是每一行都完全无效。

## Fresh / residual / zero 分解

| category | rows | state mean | zero_delta mean | median | helps | hurts | slope0 mean | s* mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fresh (`x_t>0`) | `294` | `0.370277` | `+0.011161` | `+0.063202` | `69.39%` | `30.61%` | `−0.067171` | `1.240003` |
| residual (`x_t=0,S_t>0`) | `459` | `0.161684` | `−0.007023` | `+0.002561` | `51.85%` | `48.15%` | `+0.041146` | `0.477878` |
| zero (`S_t=0`) | `3019` | `0` | `0` | `0` | `0%` | `0%` | `−0.012428` | `0.520570` |

Fresh rows 的平均 slope 为负且平均明显受益；residual rows 的平均 slope 为正且平均受损。这支持一个具体的 failure hypothesis：新确认的 Theory signal 方向大体有用，但 EMA 残留把旧状态继续施加到不再适合的 rows 上。

## 状态配对关系

- Overall `corr(S, slope0)`：Pearson `−0.0199`，Spearman `−0.0007`。
- Overall `corr(S, s*)`：Pearson `+0.2803`，Spearman `+0.0916`。
- Fresh 内部 `corr(S, slope0)`：Pearson `−0.0025`，Spearman `−0.0371`。
- Residual 内部 `corr(S, slope0)`：Pearson `−0.0701`，Spearman `−0.0733`。

因此当前没有看到一个简单的“状态越大，零点 slope 越适合”的校准关系；`S` 与逐行最优幅度有弱 Pearson 关系，但 rank 关系很弱，不能据此宣称幅值校准已经正确。

逐行完整分解保存在 `theory_row_decomposition.csv`，可按 trajectory、fresh/residual 类别、zero_delta、slope0 和 s* 继续审计。

结果 artifact：`outputs/experiments/T14_T20_LIGHT_run4_theory_decomposition_20260907/decomposition_summary.json`。
