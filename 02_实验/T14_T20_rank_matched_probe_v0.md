# T14/T20：rank-matched 1D state necessity protocol v0

## 目的与边界

当前 LIGHT 140-step smoke 中，`relevance_trace == positive_conduciveness_trace` 且 `negative_conduciveness_trace == 0`。因此本阶段不宣称三维 theory-S；先把可观测的理论状态压成一个 confirmed-effect trace，比较历史信息选择，而不是比较心理学维度数量。

## 三个同容量状态

对每条 trajectory 按同一 decision boundary、同一 `eta=0.35`、同一 EMA 更新：

```text
Theory-S:         x_t = 1 iff previous action has an expected effect and ΔO confirms it
Activity-S:       x_t = 1 iff ΔScene/O contains any transition event
ActionSupport-S:  x_t = 1 iff previous action matches a supported expected-effect template
S_{t+1} = S_t + 0.35 * (x_t - S_t)
```

首次实验固定一维状态、相同历史权限（只能用 `<t`）、相同 candidate semantics 与候选集。当前 140-step LIGHT slice 仅是 development set，不能作为正式 test；正式实验必须使用 trajectory/episode-disjoint train/validation/test，若 persona 在多条 trajectory 重复，则优先按 persona/episode 分组并报告是否存在身份泄漏。

`no-S` 分成两个不同对照：`retrained no-S` 重新训练只有 `beta_0 + beta^T phi` 的最佳无状态模型；`Theory probe + zeroed-S` 保持已训练的 Theory probe、`beta/w/phi` 全部不变，仅在 test 将 `S_t=0`。后者与 `Theory probe + permuted-S`（同 horizon 的其他 trajectory 状态）同属 test-time intervention，不能重新训练 intervention 条件。

## 统一 action head

不再为 theory-S 手写专用的 `S → goal_progress` 规则。所有条件使用同一 conditional linear probe：

```text
z(t,a) = betaᵀ phi(t,a) + S_t * wᵀ phi(t,a)
pi(a) = softmax(z(t,a))
```

其中 `phi` 是冻结的 candidate semantics（含 scene bias 的固定字段），`beta` 与 `w` 在训练集拟合；三种状态使用相同参数量、正则化、优化流程和训练预算。报告每个主效应与 `S × phi` 交互权重，不把 probe 训练结果写成心理机制成立。

### Frozen probe specification

`phi(t,a)` 的 v0 顺序固定为：

```text
[goal_progress, stimulation, recovery, hunger_relief,
 bathroom_relief, short_term_reward, environment_control,
 context_relevance, scene_bias]
```

所有字段先按 train split 的均值/标准差标准化（零方差字段的标准差取 1）；标准化统计量只由 train split 估计并应用到 validation/test。`beta_0` 是唯一 intercept；不把 `scene_bias` 预先并入 logit，也不增加其他交叉项。缺失或非有限值在进入 probe 前记为 0，并记录计数；任何字段顺序或处理变化都必须递增 `probe_feature_version`。

优化规则固定为 conditional multinomial NLL + L2 penalty（不惩罚 intercept），L-BFGS，`max_iter=1000`、`gtol=1e-8`、`seed=20260907`。`lambda` 只能在 train 上拟合、validation 选择，候选网格固定为 `{1e-4, 1e-3, 1e-2, 1e-1, 1}`，并以 validation NLL 最小为准；并列取较大 lambda。三种 S 使用同一网格和选择规则，test 只评估一次。

## 评估与置换

主指标为 held-out action NLL，并报告 Δbits、MRR、top-1 与按候选集大小分层结果。先训练正确 Theory-S probe，再在同一 probe 上评估正确 Theory-S 与同 horizon 的 trajectory-permuted Theory-S；这是 necessity permutation，不重新训练置换模型。另报告 Activity-S、ActionSupport-S、no-S 的独立 probe 结果。

解释顺序固定为：`Theory > Activity` 才支持超出一般活动记忆；`Theory > ActionSupport` 才支持 outcome-confirmation 结构的增量价值；若近似相等，保留“收益来自动作类别/压缩”解释，不写心理学增益。所有比较限定为当前数据、容量、候选集和 split。

Activity-S 的 `x_t` 必须直接读取与 Theory-S 相同的 frozen transition compiler 输出的全部 transition-event 集合（不另加、删或重命名 event type）；即使其中 observed-entity matching 噪声较大，也作为预注册 naive baseline 保留。

## 暂不做

在 appraisal 数据出现非零 negative channel、且理论状态经验 rank 真正超过一维前，不做 3D theory-S vs 3D naive-S。raw history/strong summary 属于 sufficiency 实验，另列为 Experiment B，不与本协议混合。
