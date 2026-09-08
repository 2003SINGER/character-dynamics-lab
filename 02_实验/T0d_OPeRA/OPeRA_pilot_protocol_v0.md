# OPeRA pilot protocol v0｜LIMITED-GO

状态：**protocol frozen / LIMITED-GO**（2026-09-08）。本页冻结 OPeRA
能够承担的证据责任；它不是训练结果、formal test 或 Paper-0 主实验结果。

## 1. Routing decision

OPeRA 可作为**独立真人轨迹的 coarse-action auxiliary pilot**，但不能在不
改变 Paper-0 frozen mechanism / action representation 的前提下承担
canonical generated-`A^O` candidate-set 主实验。

理由：527 个 filtered sessions 有时序、真人 action、HTML/URL 和可重放
历史；但 release 没有每一步可枚举的 exact UI target candidate set，且
当前冻结的 Replay 13D action features 描述的是 verb/target 类 action，不能
自然描述 OPeRA 的 click-type。不能为了接入而新造 OPeRA-specific action
semantics。

因此本协议只允许一个受限 estimand：在 click decision 上预测 finite
observed `click_type`。它不等价于 subjective `A^O`，不预测 exact target，
不报告 support miss，也不与 LIGHT/generated-`A^O` NLL 直接合并。

## 2. Primary and secondary estimands

Primary auxiliary estimand：

`p(click_type_t | H^obs_<t, O_t, fixed metadata)`

其中 `click_type_t` 是独立真人 `A*_t` 的粗标签。允许比较 history、summary、
no-state 与 candidate-independent state representations，但只能解释为
coarse behavioral-choice prediction。

Secondary sanity estimand：

`p(action_type_t | H^obs_<t, O_t)`，只报告低熵的 `click/input/terminate`
分类结果；它不能支撑 persistent-S 的主要结论。`semantic_id`、exact UI
target、`input_text` target 和 exact action NLL 暂不授权。

## 3. Legal prediction boundary

对第 `t` 个 action，严格使用：

```text
H^obs_<t + O_t
        ↓
  representation / X / S
        ↓
      logits
        ↓
  reveal A*_t and compute loss
```

允许：当前 action 发生前可取得的 `simplified_html_t`、`url_t`、过去 action
行、过去合法 O/history；经过单独审计为 pre-session stable 的 user/session
metadata。未审计 metadata 保持 null。

禁止：当前 `A*_t`、`action_type_t`、`click_type_t`、`semantic_id_t`、当前
action-specific `input_text_t`、`rationale`、future HTML/URL、future action、
future session information，以及从 gold action 反向构造 candidate/feature。

`rationale` 与 action row 对齐，但没有 action 前取得的独立时间戳，因此只能
作揭示后诊断字段。

## 4. Candidate boundary

全局 observed `click_type` vocabulary 只是受限 categorical outcome space，
不是逐步生成的、也不是角色主观 `A^O`。本任务没有 finite source candidate
set；不能称 13 个 click types 为“当前可行动作集合”，不能据此报告 support
miss，不能将其 NLL 与 canonical finite-candidate `A^O` 结果混写。

当前冻结的 Replay 13D `FEATURE_NAMES` 不能自然描述 click-type；本 pilot 不
修改 Theory-S、不修改 action feature basis、不新增 OPeRA action ontology。
因此 OPeRA 不能直接训练冻结的 canonical `S→action` readout，只能承担
受限 auxiliary representation/history evidence，除非未来另行批准新的任务
协议。

## 5. Frozen eligibility and split

第一版门槛固定为 `session action_count >= 20`，不得看预测结果后改成 10/30/50。

当前审计事实：

| quantity | frozen value |
|---|---:|
| filtered sessions | 527 |
| release users | 52 |
| eligible sessions (≥20 actions) | 69 |
| eligible actions | 2,562 |
| eligible click actions | 2,355 |
| eligible input / terminate | 187 / 20 |
| observed click-type classes | 13 |
| click-type entropy | 2.929 bits |
| action-type entropy | 0.442 bits |
| eligible train/test under SHA-256 user-rank 80/20 | 59 / 10 sessions |
| eligible train/test users | 42 / 10 users overall split |

当前聚合 click rows 的 2,355 个 click-type 计数合计为 2,355；pilot 仍须按
split 重新报告 unknown/missing click-type 行、每类计数和 train-only/test-only
类别。若 test 出现 train 未见类别，记录 protocol failure，不事后合并标签。

唯一首轮 unseen-user 候选 split 是：按 user ID SHA-256 rank 的 deterministic
user-disjoint 80/20，同一 user 的全部 sessions 只能进入一个 partition。它
不是 formal test：eligible test 只有 10 sessions。same-user new-session
estimand 可以作为 deferred secondary，不能混入 unseen-user 数字；官方
train/test 的 user overlap 禁止直接使用。

## 6. Frozen mechanism compatibility audit

`O_(t-1), A_(t-1), O_t` 对当前六维 X 的可构造性：

| X field | status | reason |
|---|---|---|
| `effort_load` | unavailable | 当前审计没有可复核 effort/resource 语义 |
| `goal_relevance` | requires semantic annotation | page/task relation 可作为候选，但没有冻结 deterministic rule |
| `positive_conduciveness` | requires semantic annotation | 页面/action outcome 的正向可行性未由 source 直接标注 |
| `negative_conduciveness` | requires semantic annotation | obstruction/risk 语义未由 source 直接标注 |
| `social_opportunity` | unavailable | 当前 OPeRA audit 未建立社会互动机会字段 |
| `recovery_cue` | unavailable | 当前 audit 未建立 recovery/resource cue |

不允许用 LLM 填这些字段并称为 ground truth。若未来开发 pilot 使用 annotation，
必须保留 model/prompt/confidence/provenance，并把它标成 semantic-input
ablation，而非观察事实。

## 7. Evidence responsibility and stop conditions

OPeRA LIMITED-GO 可以回答：在独立真人 coarse click-type 轨迹上，合法历史
表示是否有描述性增量；不能回答：持久状态是否在 Paper-0 canonical
subjective-`A^O` candidate set 上近似充分、是否预测 exact target、或 Theory-S
心理机制是否成立。

在下列条件任一未满足前，不训练、不比较模型：split frozen、pre-action
字段审计完成、click-type unknown/class counts 复核完成、并明确报告这是
auxiliary coarse task。若目标是 canonical Paper-0 主实验，OPeRA 当前判定为
NO-GO，应转向 D01 LIGHT semantic/temporal admission，不继续“拯救 OPeRA”。
