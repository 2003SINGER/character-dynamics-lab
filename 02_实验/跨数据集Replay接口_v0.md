# 跨数据集 Replay 接口 v0（草案，不冻结）

目的：让 OPeRA、LIGHT、玩家日志和未来自建数据通过同一内部回放接口进入开发循环；不改写原数据，也不把推断字段提升为事实。

## 最小记录

```yaml
Episode:
  trajectory_id: required
  subject_id: required_or_unknown
  group_id: optional
  split_id: required
  source_revision: optional_or_unknown
  source_record_id: optional
  persona_P: optional
  source_dataset: required
  source_license: required_or_unknown
  source_episode_context: optional
  steps:
    - t: required
      source_O: required_or_unknown
      source_event: optional
      source_action_A_star: required_or_unknown
      source_step_context: optional
      W: optional
      state_label: optional
      candidate_set_factual: optional
      candidate_set_expanded: optional
      timestamp: optional
      provenance: observed | annotated | llm_inferred | synthetic_diagnostic | unknown
      provenance_detail: optional
      field_provenance: optional per-field map with kind/source_ref/model/prompt_version/confidence
```

## 不可逾越的边界

- `source_*` 永远保留；语义标准化另存，不覆盖原字段。
- `source_episode_context` 与 `source_step_context` 分开命名；不得用一个含义模糊的 `source_context`。
- `source_revision` 与 `source_record_id` 记录数据版本和原始行/轨迹标识；未知时显式写 `unknown`/`null`。
- step 级 `provenance` 只是来源摘要；`field_provenance[field].kind` 才是字段级事实边界。
- `W`、`O`、candidate set 缺失就留空或 `unknown`；LLM 生成的只能命名为 `inferred_W` / `llm_inferred`。
- `candidate_set_factual` 只能来自数据或可复核环境；`candidate_set_expanded` 是诊断干预，不提供真人 ground truth。
- factual replay 与 expanded diagnostic 分开报告，后者不能用于证明真人选择。
- 任何根据某批数据改过机制的批次都降为 dev；untouched test 不得回看调参。

## Semantic frontend boundary

长期可替换链条保持为：`ΔO/O/S/P → X（semantic interpretation）→ U（explicit updater）→ S' → π(A)`。

- 当前 `X` 可以是 rule-based placeholder；未来可以替换为 LLM 或 hybrid，但不得折叠成 event 直接写数值 `StateDelta`。
- LLM 只读取角色可获得的 `O`、`ΔO`、`S`、`P`，不得读取隐藏 `W`、未来 observation 或后续 action。
- LLM 输出结构化 `X`，不直接任意修改 `S`；正式运行记录 model/version、prompt version、decoding config、input hash、structured output 和 raw response/reference。
- 机制识别阶段允许用多个 dev 数据集迭代字段、updater、utility、timing；冻结后不得用 test 反向修改。
- 泛化阶段至少区分：`frozen mechanism + fixed semantics`、`frozen mechanism + live LLM semantics`、`LLM-direct/no-dynamics`，另保留 state ablation/permutation。
- 第一阶段先采用 `compiled semantics`：由人工/离线 AI 辅助形成版本化、确定性的语义规则表，运行时关闭 LLM；规则可依据 dev 失败迭代，但不得按单条 `A*` 或未来信息打补丁。
- 冻结时同时冻结语义规则表、`X` schema、`S` 字段、`U`、utility、参数和 timing。冻结后才允许用 live LLM 替换语义前端，并保持动力学完全相同。

这是一条接口与实验边界，不是本轮真实 LLM 调用授权。

## 当前不做

不冻结 40 类继承体系，不启动大规模下载，不把 OPeRA action subtype 直接升级为 Paper-0 目标，不在当前阶段接入 runtime LLM。先以数据资产登记、小型 adapter 骨架和版本化 compiled semantic rules 验证字段可映射性。
