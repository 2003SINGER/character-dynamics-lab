# PowerWash Simulator｜event/state projection

原始外挂资产位于 `E:\library\科研\PowerWash`：

- `data.zip`（OSF WPEH6）
- `codebook.xlsx`
- `raw\data\`（18 张事件表）

`export_replay.py` 保留 PowerWash 的事件/状态性质：只将源表中的状态字段投影到 `source_O`，完整事件字段保留在 `source_event`，不伪造 next-action 或 `verified_action_A_star`。输出目录应放在 E 盘，避免占用项目盘：

```powershell
py -3 02_实验/T0g_PowerWash/export_replay.py `
  E:\library\科研\PowerWash\raw\data `
  E:\library\科研\PowerWash
```

当前全量导出尚未完成：直接展开全部事件 payload 会产生多 GB 冗余 JSON；下一步应改成按事件表/participant 增量导出后再生成 review fixture。
