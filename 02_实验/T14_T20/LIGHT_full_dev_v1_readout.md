# LIGHT Full Development Gradient Run v1：结果读出

## 状态

这是 development split 的第一次 gradient diagnostic，不是 Paper-0 formal test。代码、feature、S 定义、eta、lambda grid 与 split 均保持冻结。

## 当前证据

- Activity-S dev-holdout NLL：`2.139865`
- ActionSupport-S：`2.150897`
- Theory-S：`2.154609`
- retrained-no-S：`2.154677`
- uniform：`2.200459`
- Theory zeroed − correct（paired）：`-0.000365`
- Theory permuted − correct（paired）：`+0.004610`

当前最克制的读法是：持久的一维状态在该 development split 上可能带来预测收益，但收益主要出现在朴素 Activity-S；Theory-S 与 no-S 几乎持平。Theory-S 对同 horizon 的错误历史置换敏感，但零化状态并未造成损失，因此当前结果不支持 Theory-S 的独特性或必要性。

Activity-S 的 NLL 最好，而 ActionSupport-S 的 top-1 略高；因此不能把 Activity-S 概括为所有 ranking 指标都更好，NLL 仍是主指标。

## 状态覆盖混淆

全 development rows 的非零比例为：Activity-S `68.6%`、ActionSupport-S `54.3%`、Theory-S `17.8%`。Activity 优势同时混合了 representation 与 activation density，不能直接归因于语义结构。

## 下一步（不回改 Run 1）

1. **Run 1b：固定已训练模型，只做 Activity/ActionSupport/Theory 的 correct/zeroed/same-horizon-permuted intervention**，比较各自的历史归属敏感性。
2. **Run 2：frozen-base incremental probe**。先用 no-S 拟合并冻结 `theta_0`，三种 S 只拟合 `w`，检验 S interaction 在共同 base policy 上的增量价值。

两步完成前，不把 Activity 的优势写成一般性状态结论，也不扩展 Theory-S 维度或修改 appraisal。

## Run 1b：同构 intervention（已完成）

Run 1b 直接复用 Run 1 的三个已训练模型；未发生任何重新拟合。三种条件都在同一 dev holdout 上，以同 horizon、其他 trajectory 的循环 donor 做 permutation。每种条件的 paired intervention rows 均为 `3771`。

| condition | ΔNLLzero = zeroed − correct | ΔNLLperm = permuted − correct |
|---|---:|---:|
| Activity-S | `+0.032105` | `+0.000840` |
| ActionSupport-S | `+0.006478` | `−0.002087` |
| Theory-S | `−0.000365` | `+0.004610` |

当前最克制的读法：

- **Activity-S**：置零明显伤害，但同 horizon 置换只增加 `0.000840`；因此 Activity 的收益目前更像“状态幅度/近期活跃程度”而不是强 trajectory-specific history。它仍显示出 correct 相对 zero 的净贡献，但 Run 1b 不能区分这是 S 的增量信息还是 joint refit 后的 `theta` 改善。
- **ActionSupport-S**：置零有小幅损失，但 permutation 不差、反而略好；尚无 trajectory-specific history 证据，甚至可能存在弱的 generic magnitude 效应或噪声。
- **Theory-S**：复现此前结论：错误历史会伤害，但正确状态相对 zero 没有净增益。

Run 1b 的结果加强了 Run 2 的必要性，但不替代它：只有 frozen-`theta_0`、只拟合 `w`，才能检验三个 S 在共同 base policy 上的额外信息价值。Run 2 尚未启动。
