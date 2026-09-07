# LIGHT full lossless extraction｜QA v0

运行日期：2026-09-06。完整 JSONL、QA JSON 与 review slice 位于 Git 忽略目录 `outputs/external_assets_2026-09-06/LIGHT/`，不提交原始 pickle 或全量转换文本。

| 指标 | 结果 |
|---|---:|
| source episodes scanned | 10,268 |
| trajectories with physical actions | 7,258 |
| physical action steps | 25,001 |
| steps/trajectory min · median · max | 1 · 3 · 14 |
| action ∈ source available_actions | 24,998 / 25,001（99.988%） |
| parse failures / duplicate ids | 0 / 0 |

JSONL 输出 SHA-256：`1b0ac05678333be8733c384e1785091825d662b54f26842d3736e65fbede2825`。

`persona_P` 保持 `null`；source agents/persona 原样留在 `source_episode_context`。`source_O` 只取 actor-specific `context`；setting、room objects、room agents 等留在 source context，`W` 保持 `null`。`available_actions` 只记录为 source-provided candidate list，不能直接当作 `A^O`。review generator 每条 trajectory 取首/中/尾及长 context，最多 300 steps；future leakage 与 actor/time alignment 仍需人工语义审核。
