# FarmQuest full extraction｜QA v0

| 指标 | 结果 |
|---|---:|
| participants | 42 |
| non-empty telemetry lines | 29,328 |
| session trajectories | 122 |
| action-proxy steps | 10,844 |
| ambiguous events | 0 |
| review fixture entries | 250 |

事件顺序权威源是 telemetry line `source_order`；timestamp 只作为 raw metadata 保存，不能用于排序。`source_O` 保持 null，`source_action_A_star` 仅对明确 Interaction/Shop/Quest action proxy 事件生成，Transition/availability/QuestAlgorithm/Day 等保留在 `source_event` 或上下文。

全量转换和 QA JSON 位于 ignored external-assets；review fixture 已提交到 `02_实验/Replay/review_samples/FarmQuest_review_v0.jsonl`。
