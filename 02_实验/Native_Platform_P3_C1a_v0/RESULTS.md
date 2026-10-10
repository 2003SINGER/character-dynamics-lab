# Native Platform P3-C1a｜结果

状态：**READY_FOR_INDEPENDENT_REVIEW**（限定 native-server DEVELOPMENT 已验收；尚未 CLOSED）。范围见 [README](README.md)。以下是有限运行与读回证据，不代表完整恢复机制、生产就绪、长期生活连续性或心理效度。

## C1a 两场景

| 场景 | 真实运行与独立 readback |
|---|---|
| `C1a-blocked-switch` | [run](runs/p3-c1a-C1a-blocked-switch-seed20261010-20261010T070436Z-297678.json)；[SQLite/ORM DB export](runs/p3-db-evidence-20261010070436-062285-20261010T070604Z-20f22a.json)；[audit PASS](runs/p3-c1a-audit-20261010T070703Z-e3c7f3.json)。12 callbacks：本地观察暂缺时一次 native `get` 被实际世界拒绝，delivery contract 保留，随后完成 5 次 patrol 移动；audit 核对该场景 8 个对象。暂时缺少可用 `get` 不被归类为 `NO_PLAN`、`BUDGET` 或全局 `UNREACHABLE`。 |
| `C1a-observed-resume` | [run](runs/p3-c1a-C1a-observed-resume-seed20261010-20261010T070443Z-48e7cd.json)；[SQLite/ORM DB export](runs/p3-db-evidence-20261010070443-c80417-20261010T070611Z-614369.json)；[audit PASS](runs/p3-c1a-audit-20261010T070712Z-775251.json)。16 callbacks：callback 2 的一次 `get` 被拒；callback 4 向 east 巡查；玩家归还物品后，callback 5 hidden-return 负控仍选择 patrol；callback 6 向 west 返回，callback 7 本地观察恢复，HTN 继续执行 `get`/`move`/`drop`（callbacks 8/10/12），成功配送恰好一次，callbacks 14/16 继续巡查。audit 核对该场景 8 个对象。 |

两份 run manifest 均记录 C1a/server commit `caf327baf5219aef2e47f1855d8728929db59502` 与 10 个源文件 SHA-256。MCP 字段修复 commit `82891c2953ef704e897ecdeb3e970eca58e66bcb`（MCP smoke manifest 实录）的独立校验产物另记录其实际源码哈希。

## C0、P3-A/B 与 MCP 复核

- C0 原始 RESULTS 未改；这轮隔离 run 的证据为：[no-delivery run](runs/p3-c0-C0-no-delivery-seed20261010-20261010T070750Z-39b56c.json) / [DB](runs/p3-db-evidence-20261010070749-2d15be-20261010070750-7ed0a3-20261010T071132Z-8ed17a.json) / [audit PASS](runs/p3-c0-audit-20261010T071132Z-354ea4.json)（6 moves、锁门拒绝 1、重试 0）；[delivery-priority run](runs/p3-c0-C0-delivery-priority-seed20261010-20261010T070750Z-431242.json) / [DB](runs/p3-db-evidence-20261010070750-5f1b4f-20261010T071132Z-386766.json) / [audit PASS](runs/p3-c0-audit-20261010T071132Z-537fdb.json)（1 drop、3 patrol）；[after-delivery run](runs/p3-c0-C0-after-delivery-seed20261010-20261010T070751Z-a6e49c.json) / [DB](runs/p3-db-evidence-20261010070750-3ca497-20261010T071132Z-9c360c.json) / [audit PASS](runs/p3-c0-audit-20261010T071132Z-40c1be.json)（1 drop、7 patrol）。
- MCP stdio smoke 与后续读取/审计：[stdio artifact](runs/p3-c1a-mcp-smoke-seed20261010-20261010T071034Z-9e496e.json)、[C0 extraction run](runs/p3-c0-C0-delivery-priority-seed20261010-20261010T071131Z-c552b4.json)、[DB export](runs/p3-db-evidence-20261010071034-a95b39-20261010T071132Z-04d3da.json)、[audit PASS](runs/p3-c0-audit-20261010T071132Z-6e75e7.json)。CLI runner 与 stdio 传输是不同路径；未声明 MCP 全局注册。
- 旧 A/B 四个手动场景及其 [subset parent audit PASS](runs/p3-c0-audit-20261010T071251Z-aca537.json)：[Aclean](runs/p3-headless-Aclean-seed20261010-20261010T070751Z-d1f59c.json)、[Asteal-return](runs/p3-headless-Asteal-return-seed20261010-20261010T070752Z-9d0d6f.json)、[Bclean](runs/p3-headless-Bclean-seed20261010-20261010T070752Z-cdac50.json)、[Bsteal-resident-parcel](runs/p3-headless-Bsteal-resident-parcel-seed20261010-20261010T070753Z-d37e41.json)。独立 DB readback 对六个 NPC 核对 receipts/log/task/location；这是四场景 subset，不冒充历史完整七场景 suite。

本地验证记录 [p3-c1a-audit-20261010T071357Z-9b8fc4.json](runs/p3-c1a-audit-20261010T071357Z-9b8fc4.json) 保留命令、stdout/stderr、exit code、manifest 与 repository health 输出：P3 tests 40/40、bridge tests 9/9、repo health 命令均 exit 0；health 的 11 条 warnings 为 ignored vendor/既有重复提示，不是失败。

## 保留的失败与边界

- 初次 MCP smoke 结果写入器失败诊断 [p3-c1a-audit-20261010T070825Z-9b4828.json](runs/p3-c1a-audit-20261010T070825Z-9b4828.json) 保留：缺少顶层 seed 导致 `KeyError`，发生在写 artifact 前，不是 Evennia 行为或工具拒绝；修复后新的 stdio smoke 已保存。
- 实际 HTN 源未修改；本场景通过普通 key 执行 `get`，不将 `#dbref` 当作普通 key。机制仅为固定 priority/HTN 与基于本地重新观察的受限恢复。
- 本轮完成后停止，不自动扩展 P3-C1/C2 或进入 P4。截至本地验收（推送前），远端 `0943421` 的旧 runtime-regression 仍有 E0 固定预算失败；本地 40/40 与 bridge 9/9 不替代推送后 exact-head CI，后者应以 Actions 记录为准。真人体验与研究效果不在本验收内。
