# ReplayRecord v0（草案）

这是跨数据集 adapter 的最小接口草案，不是已冻结的实验协议，也不是要求所有数据集补齐字段的转换任务。

- JSON Schema：[replay_record_v0.schema.json](replay_record_v0.schema.json)
- 设计说明：[跨数据集Replay接口_v0.md](../跨数据集Replay接口_v0.md)
- 缺失字段保留 `null`/`unknown`；不由 LLM 填充 ground truth。
- `candidate_set_factual` 与 `candidate_set_expanded` 必须分开；expanded 只用于 synthetic diagnostic。
- 任何依据某数据集调过机制的运行都标为 dev；untouched test 另存并冻结。

第一步只做 schema 校验和小切片导出，不建设通用继承体系。
