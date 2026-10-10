# Native Platform P3-C0｜结果

状态：**READY_FOR_INDEPENDENT_REVIEW（有限 DEVELOPMENT 已实测；尚未 CLOSED）**。C0 授权范围和边界见 [README](README.md)。三组正式 CLI run、独立只读 DB export 与逐例 audit 均已完成；这只验证限定开发场景，不代表生产就绪、完整 NPC 自治或科研创新。CI 状态尚未更新，不在此处预写。

## 正式有限 DEVELOPMENT 结果（2026-10-10）

正式代码 commit：`108f563534ddc7dfe77ccd0ffaad58d2155d20de`。三个 run 的 manifest 均记录该 commit 为基线 revision，且对实际运行的 10 个相关源文件记录 SHA-256；manifest 明确 hash 覆盖运行时工作树字节。

| 用例 | 正式 run 与父级 CLI audit |
|---|---|
| 无配送任务 | [run](runs/p3-c0-C0-no-delivery-seed20261010-20261010T035340Z-c9215f.json)；[audit PASS](runs/p3-c0-audit-20261010T035416Z-5bf45d.json)：primary 完成 6 次巡查移动；锁门负控被 Evennia 原生拒绝 1 次，重试 0 次。 |
| 配送优先 | [run](runs/p3-c0-C0-delivery-priority-seed20261010-20261010T035340Z-c21705.json)；[audit PASS](runs/p3-c0-audit-20261010T035416Z-946a9c.json)：1 个 settled drop receipt，随后 3 次巡查移动。 |
| 配送后巡查 | [run](runs/p3-c0-C0-after-delivery-seed20261010-20261010T035340Z-afb15c.json)；[audit PASS](runs/p3-c0-audit-20261010T035416Z-b17fb3.json)：同一 actor 有 1 个 settled drop receipt，随后 7 次巡查移动。 |

三份正式 run 对应的独立只读 SQLite/ORM 导出为 [p3-db-evidence-…-a04914.json](runs/p3-db-evidence-20261010035339-c7a7e8-20261010035339-5ac8f9-20261010035340-020688-20261010035340-afce88-20261010T035358Z-a04914.json)：覆盖 4 个场景、30 个对象。每份 audit 检查对应 DB actor rows 并记录 run/DB 输入 SHA-256。27/27 个 P3 单测与 9/9 个 bridge 测试通过（父级已执行）；CI 状态未更新，不预写。上述结论限于这三种固定场景与有限 callback；callback 次数不代表真实经过的游戏时间。

实际 MCP stdio transport 核验记录：[p3-headless-MCPstdio-C0-transport-seed20261010-20261010T035534Z-33130c.json](runs/p3-headless-MCPstdio-C0-transport-seed20261010-20261010T035534Z-33130c.json)。该记录验证 initialize、tools/list（11 tools）及 observe_actor 调用；`run_c0_scenario` 可列出，但未全局注册。它与三组 C0 CLI run 走同一认证 RPC handler 不同，不应描述成 CLI 经 MCP stdio 调用。

## 首轮 exploratory snapshot（保留，不覆盖）

三次 C0 run 都是 `manual` drive；callback 次数不代表真实经过的游戏时间。

| 用例 | run 与观测结果 |
|---|---|
| 无配送任务 | [p3-headless-C0-no-delivery-seed20261010-20261010T032734Z-cdbc4d.json](runs/p3-headless-C0-no-delivery-seed20261010-20261010T032734Z-cdbc4d.json)：primary 12 callbacks、6 次真实移动；锁门负控 10 callbacks，仅第一次 `east` 被原生 Evennia 拒绝，之后 8 callbacks 均为 `PATROL_WAITING`，无重试、无 settled 移动 receipt。 |
| 配送优先 | [p3-headless-C0-delivery-priority-seed20261010-20261010T032754Z-e24a3f.json](runs/p3-headless-C0-delivery-priority-seed20261010-20261010T032754Z-e24a3f.json)：HTN 完成真实 get/move/drop，随后 3 次 patrol 移动。 |
| 配送后巡查 | [p3-headless-C0-after-delivery-seed20261010-20261010T032755Z-acf275.json](runs/p3-headless-C0-after-delivery-seed20261010-20261010T032755Z-acf275.json)：同一 actor 共 20 callbacks，一次 drop 后 7 次 patrol，无作者介入。 |
| 旧场景回归 | [`legacy_regression/`](runs/legacy_regression/) 下保留 Aclean、Asteal-return、Bclean、Bsteal-resident-parcel 四个旧场景；首轮报告均完成，每个 actor 3 个 settled receipt。旧 P3 原始证据未覆盖。 |

三份 C0 run 的 `source_revision` 均记录基线 `d5023e08c2e30f8f5dba5941aa050c7be351a4b8`；每份 run 含 8 个相关源文件的 SHA-256，表示实际运行源码快照，不等于声称该 revision 已包含这些工作树改动。独立只读数据库导出为 [p3-db-evidence-8-scenes-20261010T032920Z-c39d7f.json](runs/p3-db-evidence-8-scenes-20261010T032920Z-c39d7f.json)，通过 SQLite `query_only` 读取 8 个场景、64 个对象；细节以原始证据为准。

## 解释边界

- 锁门拒绝后若出口 fingerprint 不变，即使之后锁状态恢复也继续 wait；这是当前 C0 stop/wait 边界，自动重试留待以后授权阶段，不视为本轮缺陷。
- 旧 exploratory run 与 DB 导出保持原样作为历史材料，不与正式 run 混用。
- P3-C1/C2、P4、自然生活连续性、真人体验反馈和研究收益/创新均不在本阶段结论内。真人试玩仍是可选且未确认，不是技术 gate。
