# LIGHT T0c｜准入审计与 Replay slice

原始资产位于被 Git 忽略的 `outputs/external_assets_2026-09-06/LIGHT/`，与 ClubFloyd 和 runtime 分离。来源为 ParlAI LIGHT 的 `light-dialog-processed-small7.pkl`，文件 SHA-256 记录在 manifest 中。

## 已完成

- 审计前 50 个 episode：41 个含至少一个非空 physical action，共 140 个 physical action turns；606 个 turn 提供 `available_actions`。
- 导出 41 条 eligible trajectory / 140 steps，已通过 ReplayRecord v0 validator。
- 全量无损抽取已完成：7,258 条 trajectory / 25,001 physical-action steps；统计见 [full extraction QA](full_extraction_report_v0.md)，全量 JSONL 仅保存在 ignored external-assets。
- 每步只把 processed record 的 actor-specific `context` 作为 `source_O`；setting、room objects、room agents 保留在 episode/step source context，不把整个 world graph 复制进 `W` 或 `O`。
- `action`、persona、候选列表和 turn actor 原样保留；dialogue-only turns 不冒充 `A*`。

## 当前准入判断

**受限 dev 资产，不能作为已通过研究准入的真人行为 benchmark。** 数据结构能支持字段映射，但 actor、角色可见信息和环境 world state 的时间对齐仍需人工 semantic audit；当前 `W`、state label、timestamp 保持 unknown。候选列表仅按 source 的 `available_actions` 记录为 observed，不等同于角色实际可知集合 `A^O`。

复现：

```powershell
py -3 02_实验/T0c_LIGHT/audit_slice.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT/light_audit_50.json --limit 50
py -3 02_实验/T0c_LIGHT/export_replay.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT/light_dev_50.replay.json --limit 50
py -3 tools/validate_replay_record.py outputs/external_assets_2026-09-06/LIGHT/light_dev_50.replay.json
py -3 02_实验/T0c_LIGHT/extract_full.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT
```

全量 QA 已标记两个 source alignment anomaly episode（486、778：actor 不在 source agents，且 A* 在 case-normalized 后不在 candidates）；这两个 episode quarantine，不进入 mechanism loop。候选统计同时报告 exact miss=3、casefold miss=2（24,999/25,001 casefold 命中）。

机制开发视图必须用 `py -3 02_实验/Replay/build_mechanism_dev_view.py <full.replay.jsonl> <mechanism_dev.replay.jsonl>` 生成；脚本会硬排除 `source_episode_context.quarantine == true` 的 trajectory。

## Batch 4–5 dev diagnostic (2026-09-06)

已用 41 条非 quarantine trajectory / 140 steps 跑通 fixed compiled semantics → replay core → candidate scorer → held-out `A*` 链，并生成单事件 remove counterfactual（20 条 trajectory、52 对）。结果位于 `outputs/experiments/LIGHT_compiled_semantics_v0/`；该结果仍是 dev diagnostic，不构成 semantic admission 或 Paper-0 结论。
