# 跨数据集 Replay 接口 v0（草案，不冻结）

目的：让 OPeRA、LIGHT、玩家日志和未来自建数据通过同一内部回放接口进入开发循环；不改写原数据，也不把推断字段提升为事实。

## 最小记录

```yaml
Episode:
  trajectory_id: required
  subject_id: required_or_unknown
  group_id: optional
  split_id: required
  persona_P: optional
  source_dataset: required
  source_license: required_or_unknown
  steps:
    - t: required
      source_O: required_or_unknown
      source_event: optional
      source_action_A_star: required_or_unknown
      source_context: optional
      W: optional
      state_label: optional
      candidate_set_factual: optional
      candidate_set_expanded: optional
      timestamp: optional
      provenance: observed | annotated | llm_inferred | synthetic_diagnostic | unknown
      provenance_detail: optional
```

## 不可逾越的边界

- `source_*` 永远保留；语义标准化另存，不覆盖原字段。
- `W`、`O`、candidate set 缺失就留空或 `unknown`；LLM 生成的只能命名为 `inferred_W` / `llm_inferred`。
- `candidate_set_factual` 只能来自数据或可复核环境；`candidate_set_expanded` 是诊断干预，不提供真人 ground truth。
- factual replay 与 expanded diagnostic 分开报告，后者不能用于证明真人选择。
- 任何根据某批数据改过机制的批次都降为 dev；untouched test 不得回看调参。

## 当前不做

不冻结 40 类继承体系，不启动大规模下载，不把 OPeRA action subtype 直接升级为 Paper-0 目标。先以数据资产登记和小型 adapter 骨架验证字段可映射性。
