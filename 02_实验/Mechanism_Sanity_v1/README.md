# Mechanism Sanity v1

日期：2026-09-07

状态：**已完成工程 sanity；不是正式 NLL、Experiment B、心理学验证或数据集准入。**

本切片冻结一个最小可解释 Theory-S、一个不读取 `A*` 的 SceneSnapshot→affordance→generated `A^O` 生成器，以及五个 LIGHT development fixtures。它不读取、不修改 Terra strict-v2 的 protocol、validator、shards、status 或 results，也不复活旧 `intents-research`。

## 1. 研究问题与边界

本轮只问两个工程问题：

1. 给定外部数据投影出的 SceneSnapshot，能否从对象/agent 的已知存在生成候选动作，而不把 source `available_actions` 偷渡成 `A^O`？
2. 固定 Scene/O/P/生成的 `A^O` 后，只改变 S，能否改变 action score/probability，而不改变动作支持集？

LIGHT 的 `source_O`、场景对象、场景 agent 与 `available_actions` 有记录，但没有可靠的跨轮目标、事件结果或持久心理标签。因此 LIGHT 适合本轮接口与反事实工程检查，不适合据此识别 persistent-S 或启动正式行为预测。PowerWash、FarmQuest、AGAIN 当前主要是 telemetry/event projection，没有可用的主观 O 与动作真值，故没有硬构造成 S fixture。

本轮没有启动正式 NLL / Experiment B，也没有根据 Run1–4 调 Theory-S。

## 2. Theory-S v1

### 2.1 文献来源与可搬边界

| S field | X/appraisal 输入与职责 | 动力学（本轮冻结） | P 调制 | 如何进入 action score | 证据边界 |
|---|---|---|---|---|---|
| `fatigue` | `effort_load`、`negative_conduciveness`、`recovery_cue`；表示持续努力/恢复负荷，不替代任务压力 | 一阶松弛至 target；`recovery_cue` 拉低 target；[0,1] 饱和 | `recovery_preference` 调整恢复速度 | 降低 stimulation/conflict 的即时表达，提升 object inspection 的相对吸引力 | FAtiMA/PSI 的连续 drive 与 clamp、TCN 的一阶松弛提供可搬形式；该字段及参数不是文献已证实的人类量表 |
| `engagement` | `goal_relevance`、`positive_conduciveness`、`social_opportunity`；表示当前投入/参与，不等同 trait | 一阶松弛；正向目标/社会线索提高 target；自然向 target 衰减 | `stimulation_seeking` 调整 ramp-up/decay 速度 | 放大 stimulation/social reward 的 score | MAMID 仅定性支持 trait 调 ramp-up/decay/max；此字段命名与跨数据集语义是本项目工程选择 |
| `tension` | `negative_conduciveness`、`goal_relevance`、`recovery_cue`；表示当前受阻/威胁张力 | 较慢一阶松弛；负向后果提高 target，恢复线索降低 target；[0,1] 饱和 | `threat_sensitivity` 调更新率与 conflict salience | 提升冲突候选 salience，同时提高环境控制/检查的相对权重；不增删候选 | EMA 的 appraisal/coping 分层、FAtiMA 的 Big Five→Weight/threshold/decay、MAMID 的 ramp/decay/max 提供接口依据；不宣称文献给出本项目数值 |

X 是只读结构化 appraisal；它不直接写 S。这个分离有 EMA 2009 的直接依据（appraisal 作为持续 feature detectors，状态写入由 coping/解释更新完成）。TCN 2018 的一阶松弛、FAtiMA 2012 的 `clamp(previous + effect × Weight)`、MAMID 2004 关于 ramp-up/decay/max 的定性描述共同约束了本轮的最小形状。Broekens et al. 2008 提醒双极 conduciveness 跨轮相消会造成不可辨识，因此本轮使用正/负单极字段，不把它们相加成一个符号值。

这些文献都不能证明这三个字段是“正确心理状态”，也不能提供本轮参数的经验估计；本实现是可审计的 engineering operator。EMA 的历史 confirmed expected-effect→EMA 一维 probe 只保留为 development probe，本轮不将其升格为 Theory-S。

### 2.2 动作合法性不变量

`generate_action_candidates(snapshot)` 只使用 `actor` 与 `entities` 的 `kind/id/label`。对象只生成 `inspect`，因为缺少事实不能推出可携带、所有权或可成功操作；其他 agent 只生成一般性的 `hug`/`hit` contact affordance。生成候选中的 `required_facts` 保持为空，代表“尚未有成功条件投影”，不是“动作必然成功”。

P/S 只进入 score，绝不参与候选生成、support mask、动作合法性或 W 结算。source `available_actions` 在生成完成后才进入 `support_diagnostic`，仅报告 hit/miss。

## 3. SceneSnapshot→generated `A^O`

代码：[`candidate_generation_v1.py`](candidate_generation_v1.py)。

数据流固定为：

```text
dataset fields → canonical SceneSnapshot → entities(objects/agents) + possessions + observable facts
             → type-only affordances → generated A^O
             → (post-hoc) source available_actions support hit/miss
```

`source_candidates` 和 `source_action_A_star` 没有进入生成函数签名；`test_generator_never_reads_source_candidates` 用拒绝读取的 mapping 验证了这一点。生成器保留重复对象的第一个实例，避免仅凭同名文本伪造实例关系；该去重是候选 UI 的最小工程选择，不是事实合并。

## 4. Fixtures 与 S intervention

运行器：[`run_sanity_v1.py`](run_sanity_v1.py)。机器可读 fixture：[`fixtures.jsonl`](fixtures.jsonl)。结果：[`intervention_results.json`](intervention_results.json)。

| fixture | 场景 | generated `|A^O|` | source available_actions | 适用判断 |
|---|---|---:|---:|---|
| `episode-00001:turn-3` | Port Tavern | 6 | 4 | 适合对象/agent affordance sanity；source 的 `get` 缺少可携带事实，故为后验 miss |
| `episode-00002:turn-2` | Prison room | 5 | 4 | 适合；同上，不把 `get` 偷渡为生成规则 |
| `episode-00010:turn-2` | Underground Chamber | 4 | 5 | 适合；source 对同一 lion 有别名/动作词，显示实例语义仍不足 |
| `episode-00017:turn-6` | Castle | 4 | 5 | 适合；`put/drop/give` 需要 possessions/ownership/effect facts，本轮不脑补 |
| `episode-00019:turn-2` | Bazaar | 7 | 7 | 适合；贸易对象丰富，但 source 的 `get` 与场景角色别名仍仅作诊断 |

每个 fixture 固定 scene/O/P/generated `A^O`，before/after 仅把 S 从 `(fatigue=.05, engagement=.95, tension=.05)` 改到 `(.95,.05,.95)`，并用相同温度、相同候选排序计算 score/prob。结果 JSON 包含 before/after S、每个候选 score/prob、Δprob、rank、TV 与方向解释。

本轮工程阈值预先固定为：关键动作 `|Δprob| > .10` 或 TV `> .015`。五个 fixture 的 TV 约为 `0.049–0.068`，均触发 sanity；最大单动作概率变化约 `0.045–0.068`，未达到 `.10` 的单动作阈值。故结论是：**S 对分布有稳定但中等幅度的可见影响；没有靠改变 support 达成。** 所有 fixture 的 generated action ids before/after 相同，support invariant 为真。

这不是行为方向的外部真实性证据：本轮没有从 LIGHT 推断角色目标/人格，也没有将 source action 当作训练标签。

## 5. 测试与复现

在本目录执行：

```powershell
py -3 run_sanity_v1.py
py -3 test_mechanism_sanity_v1.py
```

`pytest` 不属于当前环境，第二条是无依赖的轻量测试脚本；测试覆盖：生成器不读 `source_candidates`、source support 只后验检查、S intervention 不改变候选集合且改变概率分布。结果工件由第一条命令重新生成。

## 6. 负结果与下一步

- LIGHT 不足以识别 persistent-S：没有稳定的跨轮结果/目标/心理标签，且 `available_actions` 的语义不等于 `A^O`。本轮不扩充 S 字段，不启动正式 NLL。
- PowerWash/FarmQuest/AGAIN 当前缺少可信的 subject-facing O 与 action ground truth，不能为了凑 fixture 把 telemetry 当心理状态。
- 当前生成器的 contact affordance 仍是工程候选，不代表社会许可或动作成功；下一步若要进入正式预测，必须为数据集单独提供可审计的 object/agent action ontology、实例绑定与前置条件。
- 若后续要冻结 Theory-S 进入科学实验，先用独立、时序充分、可标注的轨迹检验字段定义及 inertial/recovery 参数，再预注册对照与 NLL 判定；不要用本轮 sanity 结果调参。
