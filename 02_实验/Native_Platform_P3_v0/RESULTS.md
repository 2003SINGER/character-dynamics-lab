# Native Platform P3 v0｜结果记录

状态：**DEVELOPMENT_VERIFIED（限定场景）**。P3-A 单自主 NPC、P3-B 原生 Ensemble 双 NPC 交互、定时驱动、MCP stdio 与限定 SQLite 回读均有实际证据。本状态不是生产就绪、玩家体验有效性或全项目关闭。当前停在本开发交付点，等待独立复核与后续明确授权；P4 未授权。真人试玩可选且未确认，不是技术 gate 或全局 blocker。

## 源码冻结后的现场运行

下列四个主场景 run 的源文件哈希一致，记录于各 JSON 的 `source_sha256`。这些是实际 Evennia 运行时 trace，不是 planner import、自测模拟或仅凭当前状态推断；每个受控 NPC 的 `native_receipts` 均为自身合法 `get → move → drop`，最终目标状态基于自身 settled drop receipt。

| 场景 | 证据与实际结果 |
|---|---|
| `Aclean` | [run](runs/p3-headless-Aclean-seed20261010-20261010T023515Z-6879f1.json)：courier 在 tick 7 前完成配送并进入 `ACTOR_DELIVERY_SETTLED`。|
| `Asteal-return` | [run](runs/p3-headless-Asteal-return-seed20261010-20261010T023515Z-6b8971.json)：玩家先取走物品；NPC 的陈旧 get 被 `WORLD_VALIDATION_REJECTED`，无成功转移；parcel held 时本地观察为 absent/未持有并 blocked；玩家放回后 NPC 自己重新 get/move/drop。|
| `Bclean` | [run](runs/p3-headless-Bclean-seed20261010-20261010T023516Z-0fcc76.json)：两个 NPC 分别投递各自物品。原生 Ensemble 候选 `writeLoveNoteReject` 与 `kissFail` 权重均为 20，固定 seed 选中 `kissFail`；Evennia 原生失败动作 receipt 后，原 Ensemble commit 到 revision 1。resident 自己的 social proposal 是 `NO_CANDIDATE`。|
| `Bsteal-resident-parcel` | [run](runs/p3-headless-Bsteal-resident-parcel-seed20261010-20261010T023516Z-e11e53.json)：玩家拿走 resident parcel 时 resident 的局部观察未泄漏 parcel，social event 列表为空；stale get 被拒绝并 blocked；放回后 resident 自己完成配送，courier 独立完成自身配送。|

另有前一源码快照的 [Bstale-target 负控](runs/p3-headless-Bstale-target-negative-control-seed20261010-20261010T023154Z-7bf8ef.json)：提案后移动目标，旧 proposal 以 `WORLD_VALIDATION_REJECTED` 结束，`receipt_created=false`、`ensemble_commit_called=false`；后续是一个独立的新 proposal/event 并提交。该运行保留为历史负控，其哈希与上述冻结源码快照不同；不将它标成同一源码版本的复跑。social commit 事件会记录到双方参与者的共享社会历史，不表示 resident 主动发起或成功提案；该场景 resident 的自身提案仍为 `NO_CANDIDATE`。

## Timer、MCP 与持久读回

- [Timer run](runs/p3-headless-Aunattended-timer-seed20261010-20261010T023506Z-531fd1.json)：Evennia timer drive，间隔 2 秒；没有 `step_world` 调用或控制器干预，实际 callbacks 推进 courier 完成 get/move/drop，scene 随后暂停。其持久对象状态为 `PAUSED`，完成日志和最终 drop receipt 保留。
- [MCP stdio audit](runs/p3-headless-MCPstdio-live-seed20261010-20261010T023506Z-10ad46.json)：实际 stdio 子进程完成 initialize、tools/list 和 health；服务健康为 `READY`，仅绑定 `127.0.0.1:14011`。验证没有全局 Codex MCP 注册。
- [SQLite ORM readback](runs/p3-db-evidence-6-scenes-20261010T023709Z-1c1717.json)：独立 Evennia ORM 查询在 SQLite `query_only` 下，对显式 allowlist 的六个场景导出 51 个生成对象；核对 actor receipt、任务物品持久位置和目标房间。其场景包括前述四主场景、timer 与历史 Bstale 负控；MCP stdio 不创建场景。没有导出全局账号或无关世界对象。
- [独立审计器](../../tools/native_platform_v0/p3/audit_evidence.py)逐场景验证真实 receipt、拒绝门、事件 ID 边界、timer/MCP 契约与六场景 DB readback，生成唯一简短 audit JSON 和输入文件 SHA-256。与下列命令完全匹配的[审计结果](runs/p3-audit-20261010T024204Z-ef79e9.json)可复查；更早 `runs/p3-audit-*.json` 也保留。

按上述精确文件名复跑审计：

```sh
RUNS='02_实验/Native_Platform_P3_v0/runs'
python3 tools/native_platform_v0/p3/audit_evidence.py \
  --runs "$RUNS/p3-headless-Aclean-seed20261010-20261010T023515Z-6879f1.json" \
         "$RUNS/p3-headless-Asteal-return-seed20261010-20261010T023515Z-6b8971.json" \
         "$RUNS/p3-headless-Bclean-seed20261010-20261010T023516Z-0fcc76.json" \
         "$RUNS/p3-headless-Bsteal-resident-parcel-seed20261010-20261010T023516Z-e11e53.json" \
         "$RUNS/p3-headless-Bstale-target-negative-control-seed20261010-20261010T023154Z-7bf8ef.json" \
         "$RUNS/p3-headless-Aunattended-timer-seed20261010-20261010T023506Z-531fd1.json" \
         "$RUNS/p3-headless-MCPstdio-live-seed20261010-20261010T023506Z-10ad46.json" \
  --db "$RUNS/p3-db-evidence-6-scenes-20261010T023709Z-1c1717.json"
```

复核时可执行：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/install_headless_service.py --check
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/headless_runner.py --scenario Asteal-return --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.mcp_stdio
```

上述 headless runner 需先有本地 Evennia 服务及已安装的 scoped hook；服务入口为 `tools/native_platform_v0/evennia/start_loopback.sh`。复制场景后，应将 runner 输出的新 run 路径与 `export_evidence.py --scene-id <该次场景ID>` 生成的 DB readback 一并提供给审计器；审计器要求精确七份输入，包括当前四场景、timer、MCP 和历史 stale-target 负控。真实 callback 次数不等于经过了同等数量的游戏内时间；场景只验证一个作者给定配送目标及其完成后的单次 social 尝试，不构成日常生活自治。Ensemble 共用记录含三个符号人物，Evennia 中实际控制的只有两个 NPC；仅支持本次验证的两种原生 social action。

CI/本地测试边界：当前 P3 Python contract suite 为 19/19，bridge social suite 为 9/9，父级对原 runner wrapper assertions 28 项通过。源码提交 [`a214817`](https://github.com/2003SINGER/character-dynamics-lab/commit/a2148170262181c7238f7b573229b37cd8854b7b) 的 [native-platform-p3 workflow #38018330610](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38018330610) 成功。独立 [runtime-regression workflow #38018330609](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38018330609) 总体失败，但其余 5 个 job 成功；唯一失败为既有 `e0-keyledger-contract`：GitHub Ubuntu CI 日志 37/38 unit、13/14 fixture 通过，H02 实际 `planner status BUDGET` 与预期 `UNREACHABLE` 不符。该有限预算差异保留为未解决 E0 失败；本轮没有修改 E0、没有把它改写成 P3 失败，也没有据此宣称全仓 runtime regression 全绿。精简证据快照见[CI 记录](evidence/ci_runtime_regression_20261010.md)。

## 启动缺陷、依赖与来源

首次 headless service 启动于 `2026-10-10T02:14:12Z` 失败：`EvenniaServerService` 是 Twisted `MultiService`，实现错误地调用 `app.services.addService(service)`，而 `.services` 实际为 list，抛出 `AttributeError`。按运行中的 Evennia `service.py` API 改为 `service.setServiceParent(app)` 后成功重载并完成上述场景。失败是已修复的集成缺陷，保留为真实负结果，不覆盖原 traceback。

HTN 调用 GTPyhop 2.0.2（打包 fork `PCfVW/GTPyhop`；BSD Clear 许可；作者 Dana Nau、Eric Jacopin）。本项目实现的是有限任务、人物适配与 Evennia 世界接口；使用该算法不主张原创 HTN 方法贡献。每份 run 的 `source_sha256` 是其运行时源码快照，而不是后续文档修改后的当前文件哈希。

## 未证明与历史边界

- 这里只验证了上述有限角色、场景和动作，不证明生产部署、长时稳定性、任意 Ensemble 动作支持、开放世界覆盖或玩家感知有效性。
- 真人试玩反馈尚未确认且不是技术 gate；P4、完整 Director/GOAP/TypedIR 集成、训练与 formal E1-2 均未授权/未验收。P3 的 HTN 是已接通的有限场景依赖，不等于上述未完成范围。
- P1/P2 原始失败与最窄 shim 适配、LIGHT `NO_GO_WITHIN_THIS_TIMEBOX` 均保留于[历史结果](../Native_Platform_P1P2_v0/RESULTS.md)，本阶段不改写它们。
