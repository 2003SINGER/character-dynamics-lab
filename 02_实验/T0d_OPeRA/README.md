# T0d｜OPeRA 数据准入审计

目的：先对 30 个确定性抽取的 OPeRA filtered session 做字段审计，再对全量 527 sessions 做长轨迹结构统计，判断是否具备进入 Paper-0 pilot 的数据条件。它不是训练、baseline 或 Paper-0 结果。

本轮实际运行（下载的原始 parquet 与 `pyarrow` 仅在 Git 忽略的 outputs 下）：

```powershell
$env:PYTHONPATH = Resolve-Path ..\..\outputs\opera_t0d_2026-09-06\python_packages
& "C:\Users\2003SINGER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\audit_local_parquet.py --raw-dir ..\..\outputs\opera_t0d_2026-09-06\raw --out-dir ..\..\outputs\opera_t0d_2026-09-06\slice --count 30
```

`audit_opera.py` 保留为只读 datasets-server API 版本；公共 API 对批量 session filter 有临时 TLS 断连时，使用本轮实际采用的 pinned local-parquet 版本。两者都不下载截图或保存浏览内容到版本库；输出仅保存 hashed session/user ID 与结构诊断。原始数据版本、许可、抽样方法和审计结论以结果页及 `manifest.json` 为准。

全量统计复现：

```powershell
& "C:\Users\2003SINGER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\long_trajectory_stats.py --raw-dir ..\..\outputs\opera_t0d_2026-09-06\raw --out ..\..\outputs\opera_t0d_2026-09-06\slice\long_trajectory_stats.json
```

结果：[2026-09-06_准入审计结果.md](2026-09-06_准入审计结果.md)；机器可读 JSON 位于 Git 忽略的 `outputs/opera_t0d_2026-09-06/slice/long_trajectory_stats.json`。全量结果显示 69 条 session ≥20 actions，但 user-disjoint test 仅 10 条；因此当前不授权直接进入 Paper-0 pilot。

准入标准：可重放的 O（HTML/URL）、时间排序和 action ID 必须完整；session/user split 必须可冻结且不泄漏；必须能在不伪造候选集的情况下定义第一轮预测标签与 NLL。若 exact UI target 没有可枚举候选集，只能考虑 action-type/click-type 的受限协议，不能宣称和当前 `A^O` 等价。
