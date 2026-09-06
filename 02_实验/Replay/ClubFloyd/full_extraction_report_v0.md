# ClubFloyd full lossless extraction｜QA v0

运行日期：2026-09-06。完整 JSONL、QA JSON 与 review slice 位于 Git 忽略目录 `outputs/external_assets_2026-09-06/ClubFloyd/`，本仓库不提交 transcript 原文。

| 指标 | 结果 |
|---|---:|
| cleaned HTML files | 425 |
| trajectory records | 425 |
| steps | 438,188 |
| empty trajectories | 5 |
| parse failures | 0 |
| marker anomalies | 5（均为空 transcript） |
| steps/trajectory min · median · max | 0 · 704 · 8,934 |

JSONL 输出 SHA-256：`56fa742e898ef4c2362336fc6e0606428abf75a610d21e6b842b3e7c8b129ed7`。

处理仍是 lossless：`[STATE] → source_O`、`[ACTION] → source_action_A_star`，不生成 `X/S/W/P` 或候选集。`source_action_A_star` 只表示 source-labeled action；已加入 command-like / chat/commentary-like / meta-command / ambiguous 质量审计，不能直接视为 `verified_action_A_star`。本轮计数：command-like 218,575；ambiguous 219,524；chat/commentary-like 47；meta-command 42。
