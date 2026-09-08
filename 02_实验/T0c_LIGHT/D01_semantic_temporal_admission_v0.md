# LIGHT D01｜semantic / temporal admission v0

核查日期：2026-09-08  
数据版本：`light-dialog-processed-small7.pkl`，SHA-256 与全量 manifest 对应  
范围：source/replay/已有审计产物的只读核查；未训练、未修改 Theory-S、未修改 Terra strict-v2。

## Verdict

**NO-GO（针对“LIGHT 足以支持完整六维 X → Theory-S → next-action development training”这一 D01 GO 定义）。**

这不是说 LIGHT 不能再用。它可以保留为：

- actor-local history / temporal-boundary 的接口测试与失败案例；
- 经过明确标注后，部分 `X` 字段的 development diagnostic；
- source next-action 与 observed-source candidate list 的结构性审计。

但当前不能把 LIGHT 直接宣布为合法的完整 3D Theory-S development-training 数据。原因是：相邻 physical-action 行经常属于不同 actor；source `O` 只是 processed `context` 的逐 turn 拷贝，尚未完成可作为 actor observation 的人工语义准入；六维 X 中有字段明确无 source 支撑；现有 Terra annotation 是 model-assisted source diagnostic，且严格准入批次尚未完成，不能替代人工 semantic audit。

## 1. Source inventory and quarantine

全量 extraction 报告给出：

| 项目 | 数量 |
|---|---:|
| source episodes | 10,268 |
| 有 physical actions 的 trajectories | 7,258 |
| physical-action steps | 25,001 |
| 每条 trajectory steps（min / median / max） | 1 / 3 / 14 |
| action 在 source `available_actions` 中（casefold） | 24,999 / 25,001 |
| source anomaly episodes | 2（episode 486、778） |
| quarantine 后 trajectories / steps | 7,256 / 24,999 |

episode 486、778 具有 `actor_not_in_source_agents` 与 `action_not_in_candidates_casefold` 异常，已由现有 `build_mechanism_dev_view.py` 按 `source_episode_context.quarantine == true` 排除。其余数据不得因为 casefold 命中率高就自动视为语义已准入。

已有 `FULL_SEMANTIC_ANNOTATION_STATUS.md` 和 `STRICT_V2_RUN_STATUS.md` 明确：Terra 的 v1 前缀、持续 session 的 v2 prefix 都不是 admissible strict source-only admission；fresh-session strict-v2 目前只有 800 / 24,999 行，且仍是 model-assisted annotation，不是 human audit 或 final admission mask。因此本报告不把 ADMIT/AMBIGUOUS/REJECT 标签提升为事实。

## 2. Actor / turn alignment

### 2.1 What the source actually records

`export_replay.py` 对每个原始 turn `t` 做以下复制：

- `character[t]` → step actor；
- `context[t]` → `source_O`；
- `action[t]` → `source_action_A_star`；
- `available_actions[t]` → `candidate_set_factual`；
- `room_objects[t]`、`room_agents[t]`、`carrying[t]`、`wearing[t]`、`wielding[t]` → source step context。

这保留了 source provenance，但没有证明 `context[t]` 是严格意义上仅该 actor 可见的 observation，也没有把 actor-specific private information、persona、world state 与可见内容分成已验证字段。`persona_P` 与 `W` 仍为 `null`，source agents/persona 只保留在 episode context。

### 2.2 Read-only source counts

对本地 `light_data.pkl` 的只读统计：

- 7,258 条有 action 的 trajectory 中，4,280 条含多个 physical-action actor，2,978 条只有一个 actor；
- physical-action 行之间有 17,743 个相邻 pair：6,706 个同 actor，11,037 个不同 actor；
- 也就是说，约 **62.2%** 的相邻 physical-action pair 不能直接解释为同一 actor 的连续决策历史；
- 只有 2 个 actor 不在 episode-level source agents 中，对应已有 quarantine episode；
- 25,001 个 physical-action step 都有非空 `context`、`room_objects`、`room_agents`、possessions 字段和 source `available_actions`，但“字段存在”不等于其观察可见性与时间语义已经验证。

### 2.3 Legal actor-local history definition

若未来继续使用 LIGHT，合法 history 必须按以下规则构造：

```text
H^obs_<t(actor) = { (O_i, A*_i) : i < t,
                    character[i] == character[t],
                    i 为同一 trajectory，且未 quarantine }
```

当前 step 的 `A*_t` 永远不进入当前预测输入。其他 actor 的 action 可以作为环境中“发生过的 source event”另行保留，但不能塞进当前 actor 的 action history，除非另有明确的 multi-agent observation/causal protocol。episode-level persona 也不能因出现在 source agents 而自动提升为当前 actor 的可见 `P`。

按上述定义，actor-local history 在数据结构上可构造；但连续同 actor step 之间可能隔着其他 actor 的 action，因而它不是默认的单步世界 transition。

## 3. Prediction-time `O_t` boundary

| source 内容 | 当前可用状态 | 说明 |
|---|---|---|
| 当前 actor 的 processed `context[t]` | **source-observed candidate** | 可作为最小 `source_O` 输入；只能说 source 提供了该 actor turn 的 context，尚未完成人工 observation audit。|
| `context[t]` 中明确写出的 setting/room description、visible objects、visible agents | **possibly actor-observed, audit required** | 文本上通常属于当前场景描述；不能把 parser 读到的每个世界字段都自动升级为 O。|
| 当前 `character[t]` / actor identity | **observed source alignment** | 用于 actor-local filtering；必须经过 episode/turn consistency 检查。|
| 同一 actor 的过去 `context[i]`、过去 `A*_i`（`i<t`） | **legal past history** | 仅限同一 trajectory、同一 actor、非 quarantine。|
| 其他 actor 的过去 action | **world/source context only** | 不得作为当前 actor 的 action history；是否被当前 actor观察到未标注。|
| `room_agents[t]` / `room_objects[t]` | **world/source context; audit required** | 它们是 step context 的原字段，不能直接称为完整可见 agents/objects。|
| episode `setting` / `all_descriptions` | **world/source context only** | 可用于 source-preserving scene snapshot；不能整体复制进 O。|
| `carrying` / `wearing` / `wielding` | **source possession context; audit required** | 可保留作 source evidence；不自动等于 actor 当前可知 inventory。|
| source agents/persona | **world/source context only** | 当前 `persona_P` 为 null；不作为预测时 actor-visible P。|
| 当前 action、current click/action subtype、未来 context/action | **forbidden** | 只能在预测后用于 A* scoring 或事后审计。|

因此，当前最小合法边界是 `source_O = processed context[t]` 加上已经发生的、同 actor 的 source history；setting、room graph、source agents/persona 和其他 actor action 只能保持分层 provenance，不能“全图入 O”。

## 4. Temporal transition and index rule

冻结的索引应为：

```text
O_(t-1, actor), A*_(t-1, actor), O_(t, actor)
    → ΔO_t(actor) → X_t → S_t → predict A*_t(actor)
```

这里的 `t-1` 指 **该 actor 的上一个合法 physical-action observation**，不是原始 episode 中简单的上一行。若使用全局相邻行：

- 当相邻行 actor 相同，可作为候选 single-actor local boundary，但仍需检查 observation/action 对齐；
- 当相邻行 actor 不同，不能把 `A*_(t-1)` 当作当前 actor 的过去 action；至少要跳过该边或构造成显式 multi-agent event；
- 若跳过不同 actor 行后使用上一个同 actor step，`ΔO` 跨越了中间事件，必须标记为 actor-local accumulated transition，而不能称作单一 action effect。

现有 Replay exporter 仅保存原始 `t` 和逐 turn字段；现有 transition/scene diagnostic 在 41 条 trajectory、140 steps 上按 replay boundary 运行，且 README 明确仍为 dev diagnostic。代码没有在 ReplayRecord 层强制 actor-local predecessor，也没有为跨 actor gap 编码 delta-time/event bundle。因此“transition compiler 可运行”不等于当前全量 LIGHT 已通过 temporal admission。

## 5. Six-dimensional X capability

| X field | 判定 | 合法 provenance / 缺口 |
|---|---|---|
| `effort_load` | **unavailable** | source 没有 effort、时长、资源消耗或可靠时间戳；不能从 action 文本硬造连续 effort。|
| `goal_relevance` | **semantic annotation required** | setting/task-like context 与 action target 可提供文本证据，但“与当前 actor goal 的相关性”没有 observed goal/state label；若使用，必须是版本化 annotation，不是 source truth。|
| `positive_conduciveness` | **semantic annotation required** | 可用过去/当前 scene evidence 与 action semantics 做受限语义标注；source 没有 outcome/goal completion ground truth。现有 transition audit 只有 15 个 positive trace rows、41 个 expected-effect rows，且是 compiled diagnostic，不是 LIGHT admission。|
| `negative_conduciveness` | **semantic annotation required, with current support failure** | obstruction/negative effect 需要语义判断；现有 audit 中该 channel nonzero = 0，不能据此声称不存在负面事件。|
| `social_opportunity` | **semantic annotation required** | `room_agents` 可提供候选社会对象的 source context，但“可用社会机会”不是简单 agent count；当前没有冻结的 observed label。|
| `recovery_cue` | **unavailable** | source 没有可靠疲劳/恢复/休息或时间间隔信号；setting 中出现休息语句不能直接成为 actor recovery cue。|

结论：至少两个字段明确 unavailable，四个字段需要另行语义标注（其中 negative channel 当前诊断为零不能作为证据）。因此当前 source 不支持不加说明地构造冻结的完整六维 X。

## 6. A* status

- `source_action_A_star` 是 processed source 中非空的 next physical action；在预测协议上可以作为当前 row 的 held-out target。
- 它与我们的 candidate generator 不是同一生成器；其 source provenance 可独立保留。
- 当前全量的 casefold membership 为 24,999 / 25,001，两个异常 episode 已 quarantine；这只说明 source action 与 source list 的字符串关系，不证明 list 是角色真实可知的 `A^O`。
- 不允许用 current A* 反向修改当前 row 的 `source_O`、X、候选集或 semantic normalization。

因此 A* 作为 observed source next-action 的 status：**可用于 held-out scoring / temporal interface audit**；作为完整 Theory-S development target：仍受 actor/semantic admission gate 限制。

## 7. `source available_actions` boundary

`candidate_set_factual` 只审计为 **observed-source candidate list / post-hoc diagnostic**。它来自 source 的 `available_actions[t]`，可以报告 candidate count、字符串 membership 和 support miss；不得把它升级为 `A^O`，不得用它替代 actor-visible affordance reconstruction，也不得用 miss 后补 gold。

现有 scene snapshot 已正确保留：`candidate_status = observed_source_only_not_A_O`。这一点在 D01 中维持不变。

## 8. Quarantine 后可用范围

quarantine 后可安全保留的范围：

1. **source-preserving data/interface work**：actor-local filtering、opaque trajectory IDs、字段 provenance、未来 strict semantic audit 的输入准备；
2. **held-out A* structural checks**：在不把 candidate list 当 A^O 的前提下，检查 action timing、source membership 和 replay schema；
3. **small diagnostic semantic slices**：仅当每条 X 都明确标为 source-observed / deterministic-derived / annotated / unavailable，并且不把 Terra diagnostic labels 当 final admission；
4. **negative-control / failure decomposition**：可研究不同 actor gap、缺失 X、quarantine 与 source anomaly 如何影响可用性。

当前不应做：

- 用全量 24,999 rows 直接 fit 六维 X 驱动的 Theory-S；
- 把 `available_actions` 当 A^O 并做 canonical candidate-set claim；
- 把 Terra 的 800-row strict-v2 annotation 当人工准入 mask；
- 把 compiled transition audit 的 positive/zero negative channel 当真实 LIGHT behavior result；
- 用相邻不同 actor 行传播同一个 S，或把其他 actor action 放入当前 actor history。

## 9. What would be needed to reopen D01

D01 不是靠继续修改 Theory-S 解决。若要从 NO-GO 重新评估，至少需要：

1. 完成并冻结 actor/observation semantic audit，明确每个 step 的 actor-local visible boundary；
2. 在 Replay/transition compiler 中显式编码同 actor predecessor、跨 actor gap 和 trajectory reset；
3. 为每个 X 字段预注册 source/derived/annotation/unavailable 协议，不用 annotation 填补 `effort_load` 或 `recovery_cue` 的缺失事实；
4. 明确是缩减 X 诊断还是换数据集，不得悄悄把缺失字段填 0 后继续宣称完整 Theory-S；
5. 单独冻结 candidate provenance；source `available_actions` 继续保持 observed-only。

在这些条件满足前，LIGHT 适合作为 D01 的失败边界与接口审计资产，不适合作为第一次真实 3D Theory-S gradient training 的合法主数据。

