# Demo Living Batch 48h v0

这是 `DemoLivingDynamicsV0` 的 application/demo engineering diagnostic，不是研究证据，也不声称人格心理学有效。

- 128 个相互独立的 `World + Runtime + Character` 实例
- 8 个 demo engineering profiles，每个 16 个固定 actor seeds
- Day 1 08:00 至至少 Day 3 08:00（2880 simulated minutes）
- 唯一 scripted bootstrap：`Idle` 10 分钟；之后全部由 `O + S + P → π → Runtime validation` 产生
- 全部 actor 使用 `demo-living-v0`，不混入 Reference dynamics

`manifest.json` 和 `profiles.json` 是冻结配置；`compact_traces.jsonl` 保留每个 actor 的每个 boundary；`actor_summary.csv`、`profile_summary.csv`、`aggregate.json` 与 `BATCH_48H_REPORT.md` 均由 runner 从 trace 生成。`representative_traces/` 按每个 profile 的多维中位数最近 actor 与 diagnostic flags 最多 actor 自动选择，禁止人工挑选。

本批次只报告执行稳定性、行为分布和可疑模式；任何 flag 都是待人工审阅的诊断，不是自动修复或心理学结论。
