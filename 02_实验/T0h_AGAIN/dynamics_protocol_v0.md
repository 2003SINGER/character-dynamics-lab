# AGAIN dynamics development audit protocol v0

状态：**development-only / frozen protocol / 不启动 formal test**  
冻结日期：2026-09-08  
数据 owner：`02_实验/T0h_AGAIN`

## 1. 目的与边界

本协议只审计一个窄问题：在 AGAIN 的 event/telemetry history 下，
`source_arousal_proxy` 是否呈现可重复的 **persistence、lag、decay、recovery**
形状，以及三类极简 dynamics family 能否在参与者和游戏留出时保持同一形状。

这里的 `source_arousal_proxy` 是 AGAIN 的连续 arousal annotation proxy，
不是 Character Dynamics 的 `source_O`，也不是行为真值。它**不等于** fatigue、
engagement 或 tension；本协议不把这些概念互换，也不从 key press 反推
`source_action_A_star`。

本轮不训练 `alpha`、`beta`、`b`、`W`，不估计 Theory-S 参数，不启动正式统计检验，
不据此宣称 Theory-S 或最终 character state 模型成立。结果只用于决定是否值得
设计下一份、带明确输入语义的实验协议。

## 2. 冻结的数据与时间语义

唯一输入 artifact：

- `02_实验/T0h_AGAIN/again_dev_20_v4/AGAIN_dev.replay.jsonl`
- manifest：`AGAIN_dev.manifest.json`
- QA：`AGAIN_dev.qa.json`
- review fixture：`AGAIN_dev_review_v0.jsonl`

manifest 冻结事实：20 sessions、9 games、9,302 steps、9,302 条已对齐步骤、
300 条 review fixture；这只是跨 9 游戏的 development slice，不是代表性统计样本。
Replay SHA-256：
`bb2707c1fac1a6f8b5c265953ccf49147d7bfda9c6c237a2a29a0fd6aaef870c`。

每条轨迹的边界是严格的
`(player_id, session_id, game)`；不得跨参与者、session 或 game 拼接历史。
telemetry `time_stamp` 使用 session-relative seconds。raw annotation 的时间戳为
milliseconds，已除以 1000；对每个 telemetry row 只匹配同一 key 下最新的
`valid=1` annotation 且 `annotation_time <= telemetry_time`。不得使用未来 annotation
或未来插值。现有 QA 的 `future_annotation_never_used`、三类 source null 检查和
step-count 检查必须保持为 true。

## 3. 输入、目标与可见历史

对目标时刻 `t`，定义可见历史：

```text
H_t = {telemetry at times <= t,
       observed source_arousal_proxy at times < t,
       player_id/session_id/game boundary metadata}
```

`H_t` 可以包含 telemetry 中已经观察到的输入、速度、碰撞/重生、idle、得分、
可见对象等字段；字段必须保留原始 provenance，不得因为与 arousal 相关就改名为
心理状态。当前 adapter 已将 `[string]key_presses` 排除出 telemetry payload，
因此不能在本协议里把它重新当成 action ground truth。

目标 `y_t` 仅为该时刻已有的 `source_arousal_proxy`。没有合法 annotation 的时刻
保持 missing；不向后填充，不用未来值补齐。模型输入不得读取目标时刻之后的
telemetry 或 annotation。评估阶段可以回看 `y_{t+1:t+k}` 来量度 lag/decay/recovery，
但这些 future values 只能是 outcome，不能进入特征、调参或阈值选择。

## 4. 三类 frozen development family

三类 family 都是诊断 comparator，不是最终模型。所有常数、窗口、lag grid 和
阈值必须在读取 held-out 结果前冻结；不允许看完结果后改 prompt、改字段或换 family。

### 4.1 No-state baseline

不维护内部状态，也不读取当前轨迹的未来信息。对每个 held-out fold，使用
**training portion 的 arousal proxy 中位数**作为常数预测；若要报告 session-local
last-value 结果，必须单列为描述性 persistence baseline，不得把它叫 no-state。

用途是回答：如果完全没有 dynamics state，跨参与者/跨游戏还能解释多少表面水平。

### 4.2 AR(1) carry-forward comparator

只使用最近一个合法的过去 proxy 值，按 native timestamp 计算 elapsed time；不使用
未来 annotation。系数不做本轮学习：预先固定一个透明的 `phi` grid（例如
`{0.0, 0.5, 0.8, 0.95}`），只报告各点的 sensitivity；不能为 participant、game
或 held-out fold 选择最优 `phi`。如果过去 proxy 不存在，该时刻退回 no-state baseline。

这不是 `alpha` 参数训练，也不是对 Theory-S 的 state transition 估计；它只是
检验“过去的 proxy 是否足以产生短期 persistence”的最低 comparator。

### 4.3 Frozen first-order relaxation family

先从 telemetry history 构造**预注册的事件脉冲/事件 envelope**，例如某一具体
字段在相邻 native rows 出现预定义的非零/变化事件；每个 telemetry channel 单独
审计，禁止临时学习加权的综合 arousal score。对每个 channel 使用固定的、事先列明
的 relaxation time constant `tau` grid，以

```text
s(t + dt) = exp(-dt/tau) * s(t)
            + (1 - exp(-dt/tau)) * event_envelope(t)
```

生成一个只由过去/当前 telemetry 事件驱动的 frozen response trace。`tau` 仅作为
预注册 sensitivity grid，不从 held-out participant/game 拟合；本 family 不学习
`alpha`、`beta`、`b` 或 `W`，也不把 `s` 命名为 arousal state。审计的是 event
response 的时间形状是否与随后观测到的 `source_arousal_proxy` 有稳定关系，
不是证明某个 telemetry 字段造成 arousal。

事件 envelope 的字段清单、事件定义、`tau` grid、事件后观察窗口必须在执行前写入
同一 protocol 的 append-only run record；没有预注册的字段不得事后加入。

## 5. 留出设计与泄漏控制

使用两组互补的 development-only grouped hold-out；结果分别报告，不能把两者混成
一个随机行级分数：

1. **participant-held-out**：整名 `player_id` 的所有 session 留出；训练端不得看到
   该参与者的 proxy 分布或 session-local baseline。
2. **game-held-out**：整款 `game` 的所有 session 留出；训练端不得看到该游戏的
   telemetry/proxy 记录。

若 participant/game 交叉导致某 fold 训练样本过少，保留 fold 身份并标记
`insufficient-development-support`，不得为了得到分数而回退到随机切分。每条轨迹
的内部时间顺序保持不变。所有 scaling、baseline、任何 family 选择均只能来自
training portion；held-out 只在 artifact 冻结后 reveal。

由于当前只有 20 sessions，本节输出是稳定性审计，不是 population estimate；不做
显著性检验、不报告 confidence claim、不把一次 fold 的优势写成泛化结论。

## 6. 指标定义

所有指标按 trajectory 先算、再汇总 median/IQR；同时报告每个 participant/game
fold，防止长 session 支配结论。

- **Persistence**：固定 lag grid 上的 proxy 自相关/保持率，以及 comparator 的
  one-step carry-forward error。必须注明使用的 native elapsed-time bin，不把等间隔
  AR 解释强加给不等间隔 telemetry。
- **Lag**：预注册 telemetry event 后，event envelope 与 proxy change 的
  cross-correlation peak 或 peak-window；只在 event 前后窗口完整且目标 proxy 合法
  时计算。lag 是描述性时间偏移，不是因果效应。
- **Decay**：事件后 proxy deviation 相对 event-window baseline 的下降曲线、半衰
  或固定窗口 retention；若曲线不支持单调衰减，报告 `non-monotone/undefined`，
  不强行拟合 exponential。
- **Recovery**：proxy 回到 event 前 baseline 的预注册容差带所需时间；若没有返回
  容差带或窗口结束，报告 censored/undefined。不得把 recovery 叫 fatigue recovery。
- **Predictive sanity**：可报告 one-step MAE/RMSE 或 rank correlation，但只能作为
  development comparator；它不替代四个 dynamics 指标，也不能产生正式模型准入。

所有缺失、censored、无事件或 proxy 平台期都保留计数。禁止把 missing 当 0，禁止
用插值制造 recovery，禁止只报告 pooled mean。

## 7. 交付物与停止条件

一次执行最多生成：

1. frozen run record（输入 SHA、fold、字段/事件定义、grid、软件版本）；
2. 按 family × hold-out 轴的 persistence/lag/decay/recovery 表；
3. 每个 fold 的轨迹图与 missing/censoring 清单；
4. 一页 development conclusion，明确哪些现象跨 participant、跨 game 重复，哪些
   只在单一 session/game 出现。

若发现 timestamp、future guard、source null 或边界完整性任一失败，立即停止并标记
`blocked-by-provenance`，不修数据后继续算分。若三类 family 的形状只在随机/单一
参与者或单一游戏中出现，结论为 `development signal not stable`；不升级为主数据、
不进入 Theory-S 训练。即使形状稳定，也只能提出下一步候选实验，仍不训练
`alpha, beta, b, W`，不启动 formal test。

## 8. 明确不做的事

- 不把 AGAIN arousal proxy 重命名为 `source_O`、fatigue、engagement、tension 或
  character state。
- 不从 key press、engine tick 或 telemetry 事件生成 `source_action_A_star`。
- 不把 event-to-proxy 的时间相关写成心理因果、Theory-S 验证或跨游戏普遍规律。
- 不把这 20-session slice 当作代表性样本，不扩展为全量 semantic admission。
- 不训练 `alpha`、`beta`、`b`、`W`，不调参到 held-out 结果，不启动正式检验。

