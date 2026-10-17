# PowerWash Simulator｜event/state projection

本机原始资产位于 canonical 项目的 `_local_data/PowerWash/`；原 Windows 路径 `D:\desk\科研\character-dynamics\_local_data\PowerWash` 是历史来源：

- `data.zip`（OSF WPEH6）
- `codebook.xlsx`
- `raw/data/`（按需解压缓存；源包内16个CSV及2个SQL文件）

2026-10-17 按用户要求清理重复解压缓存：16个CSV均与保留ZIP的对应成员做完整流式SHA-256及长度比对，两次独立核验一致后删除，共8,160,396,040 bytes。`data.zip`、`codebook.xlsx`、`pilot_100/`、两个SQL文件及仓库实验结果保留。不是删除原始数据资产或更改历史试点结果；本地逐文件核验清单在 `_local_data/maintenance/csv_cleanup_20261017/`。

需要重跑转换时先恢复CSV（需预留约8.2GB解压空间），在项目根目录执行：

```sh
unzip -n _local_data/PowerWash/data.zip 'data/*.csv' -d _local_data/PowerWash/raw
```

`pilot_bucket_pipeline.py` 是当前采用的 100 名参与者试点管线：先按 pid 分到 256 个桶，再桶内排序、按登录/退出切 session，并将相同时间戳打包（不宣称包内因果顺序）。它保留完整事件与可辨识的游戏遥测状态于 `source_step_context.source_state_fields`；`source_O`、`source_action_A_star`、`state_label` 均保持 null，不把遥测冒充主观观察、真实动作或标签。

试点已完成（2026-09-06）：100 participants / 366,660 raw rows / 1,220 segments（1,135 normal sessions + 85 orphan segments）/ 344,248 steps / 312 review fixtures / 7,015 anchors，覆盖 15 类事件。本机试点产物在 `_local_data/PowerWash/pilot_100/`；版本控制内只保留 manifest、QA、脚本与 review fixture。历史 Windows D/E 盘全量产物的位置见旧 manifest，本轮未复核。源包 SHA-256：`1B4D1F7DAF61548D9F40B9B0B6AC9FE3E44ED0DFF5D0D496FC002D08AC3AEC41`。

2026-09-06 修复了 session 边界：同 timestamp bundle 在 sessionize 之前形成；含 `exited_game` 的 bundle 整体作为最后一步；login 前/exit 后遥测保留为 `pre_login_orphan` / `post_exit_orphan`，不计入 normal session；anchor 的 past window 严格早于 anchor timestamp，并显式记录同秒事件及其未知顺序。

历史 Windows 试点复现命令（输入与输出均放 D 盘；本机需使用上述 canonical 路径并先恢复CSV）：

```powershell
py -3 02_实验/T0g_PowerWash/pilot_bucket_pipeline.py `
  D:\desk\科研\character-dynamics\_local_data\PowerWash\raw\data `
  D:\desk\科研\character-dynamics\_local_data\PowerWash\pilot_100 `
  --participants 100 --buckets 256
```

pilot 结构审计已通过；全量转换仍需分层 review 与 manifest/QA 审计。保留原始 `data.zip`、`codebook.xlsx` 和试点/审计产物；与ZIP完整校验一致的解压CSV可以按需恢复，不再要求长期保留两份相同数据。
