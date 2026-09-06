# PowerWash Simulator｜event/state projection

原始外挂资产位于项目盘 `D:\desk\科研\character-dynamics\_local_data\PowerWash`：

- `data.zip`（OSF WPEH6）
- `codebook.xlsx`
- `raw\data\`（18 张事件表）

`pilot_bucket_pipeline.py` 是当前采用的 100 名参与者试点管线：先按 pid 分到 256 个桶，再桶内排序、按登录/退出切 session，并将相同时间戳打包（不宣称包内因果顺序）。它保留完整事件与可辨识的游戏遥测状态于 `source_step_context.source_state_fields`；`source_O`、`source_action_A_star`、`state_label` 均保持 null，不把遥测冒充主观观察、真实动作或标签。

试点已完成（2026-09-06）：100 participants / 366,660 raw rows / 1,220 segments（1,135 normal sessions + 85 orphan segments）/ 344,248 steps / 312 review fixtures / 7,015 anchors，覆盖 15 类事件。可复核大体量产物在 `D:\desk\科研\character-dynamics\_local_data\PowerWash\pilot_100`，仓库只保留 manifest、QA、脚本与 review fixture；全量产物另放 E 盘。源包 SHA-256：`1B4D1F7DAF61548D9F40B9B0B6AC9FE3E44ED0DFF5D0D496FC002D08AC3AEC41`。

2026-09-06 修复了 session 边界：同 timestamp bundle 在 sessionize 之前形成；含 `exited_game` 的 bundle 整体作为最后一步；login 前/exit 后遥测保留为 `pre_login_orphan` / `post_exit_orphan`，不计入 normal session；anchor 的 past window 严格早于 anchor timestamp，并显式记录同秒事件及其未知顺序。

试点复现命令（输入与输出均放 D 盘）：

```powershell
py -3 02_实验/T0g_PowerWash/pilot_bucket_pipeline.py `
  D:\desk\科研\character-dynamics\_local_data\PowerWash\raw\data `
  D:\desk\科研\character-dynamics\_local_data\PowerWash\pilot_100 `
  --participants 100 --buckets 256
```

pilot 结构审计已通过；全量转换可写入独立 E 盘目录，仍需分层 review 与 manifest/QA 审计。不要删除原始 `data.zip`、`codebook.xlsx` 或 `raw\data`。
