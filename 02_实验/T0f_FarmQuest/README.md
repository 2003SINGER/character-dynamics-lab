# FarmQuest T0f｜telemetry → action-proxy Replay

原始 `processed.json` 位于 ignored `outputs/external_assets_2026-09-06/FarmQuest/`。本 adapter 保留 telemetry raw line、按 line index 排序，不使用 timestamp 排序。

- 42 participants；29,328 non-empty telemetry lines
- 122 `Event:SessionStart`-切分的 session trajectories
- 10,844 strong action-proxy steps
- QA hard assertion：每个 `source_event.source_order` 均严格小于当前 action 的 `source_order`；session-local slice 不再使用 participant-global index
- 792 `Quests:QuestBoardState:Accept` nested records 已按 source 结构解析，不再计为 ambiguous
- survey 原文置于 `source_episode_context.survey_raw`，不映射到 `P`
- `source_O = null`；telemetry history 不自动宣布为角色观察
- `timestamp = null`；每步保留 `raw_timestamp`，并标注 `timestamp_semantics=unusable_for_ordering`

审计/导出：

```powershell
py -3 02_实验/T0f_FarmQuest/inspect_source.py outputs/external_assets_2026-09-06/FarmQuest/processed.json outputs/external_assets_2026-09-06/FarmQuest/farmquest_source_audit.json
py -3 02_实验/T0f_FarmQuest/export_replay.py outputs/external_assets_2026-09-06/FarmQuest/processed.json outputs/external_assets_2026-09-06/FarmQuest
```

当前状态是 restricted dev；action 是 source telemetry action proxy，不是已验证的人类命令 ground truth。语义审核待做。
