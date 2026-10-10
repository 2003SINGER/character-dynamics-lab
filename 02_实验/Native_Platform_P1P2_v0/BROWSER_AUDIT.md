# 父级浏览器交互验收

本文件只记录 P1/P2 现场证据。“用户亲自试玩尚未确认”是该次记录状态，不是 P3 技术 gate 或全局 blocker；真人试玩属于可选体验反馈。P3-A/B 当前状态见 [Native Platform P3](../Native_Platform_P3_v0/README.md)。以下操作记录不因路线更新而改写。

2026-10-10 本机会话；这是代理实际操作，不是用户亲自试玩，也不是伪造的服务器完整 stdout。下列回显来自官方 Web 客户端的可见 UI，SQL 回读来自正在运行游戏的 SQLite 数据库（只读连接）。测试账号凭据不公开。

入口：`http://127.0.0.1:14001/webclient/`；只监听 loopback。原生连接屏显示 `nativep1, version 6.0.0`。

| 步骤 / 实际输入 | 可见返回 / 独立回读 |
|---|---|
| 登录既有本地测试账号 | `You become p1admin.`；`Limbo(#2)` |
| `create P1BrowserToken` | `You create a new Object: P1BrowserToken.`（测试夹具准备，不当作普通玩家能力） |
| `batchcode evadventure.build_techdemo` | 原生 Batch-code 自动模式，4/4 段完成；`Batchfile 'evadventure.build_techdemo' applied.` |
| `inventory` | `You are carrying: a P1BrowserToken` |
| `drop P1BrowserToken`；`look` | `You drop a P1BrowserToken.`；`Limbo(#2)` / `You see: a P1BrowserToken` |
| drop 后 SQL | `#3 P1BrowserToken db_location_id=2`（房间）；`#1 p1admin db_location_id=2` |
| `get P1BrowserToken` | `You pick up a P1BrowserToken.` |
| get 后 SQL | `#3 P1BrowserToken db_location_id=1`（玩家库存）；玩家仍在房间 #2 |
| `techdemo` | `Techdemo Hub(#4)`；`Central hub for EvAdventure tech demo.`；出口 `Back to Limbo, combat test, and dungeon test` |

SQL 指令（项目根执行，当前测试对象 IDs 是本次实际值，不作为重建时固定 ID）：

```sh
sqlite3 -readonly _local_data/native_platform_v0/evennia/nativep1/server/evennia.db3 \
  'SELECT id, db_key, db_typeclass_path, db_location_id FROM objects_objectdb WHERE id IN (1,2,3,4,7,10,13);'
```

原 builder 读回：Hub #4 为 `EvAdventureRoom`、Arena #7 为 `EvAdventurePvPRoom`、Dummy #10 为官方 `EvAdventureMob`、Dungeon #13 为 `EvAdventureDungeonStartRoom`。浏览器未替换 builder/FSM。

父级另在浏览器执行原 `AIHandler.set_state("roam")` 和最小 `DefaultScript` 定时接线。独立读回 script 5 秒、active=1，但原样 wheel 的 `npcs.py:331` 出现 `NameError: name 'random' is not defined`；故**定时器存在不算 NPC 行动成功**。原样错误和兼容后实际行动证据须分别报告，最终状态见本目录结果入口。

用户亲自试玩：尚未确认，已发出本地入口与移动命令，不将代理操作计为人类玩家证据。

## 原样失败与兼容后自主行动

原 `npcs.py` 没有被改写；安装文件 SHA-256 为
`9a84dd3683cd5761b2eaaffb2b326561950cd6b54e457a42ecc5173e208b6e6f`。
最小 ticker 仅补 `npcs.random = random` 并调用原 `.ai.run()`。重启后父级在浏览器
重新 `ic`，实际看到 `Training Dummy is leaving Techdemo Hub` 与 `arrives ...`
消息，目的地包含 Limbo、Combat Arena、Dungeon start room。

父级另读回持久 tick 23–29，位置为 `#4→#2→#4→#7→#4→#2→#4→#13`。
公开 [movement.json](evidence/evennia/movement.json) 保留随后捕获的最近 40 条真实记录，
不把计时器创建成功或单次 `look` 当成移动证据。只有这套兼容配置为 `ADAPTED_PASS`；
原样 NameError 仍为 FAIL，见 [server.log](evidence/evennia/server.log)。

## 真实桥接：失败也保留

父级从已登录浏览器执行 `run_live_probe.run(me)`，内部对独立 Character 测试对象调用
实际 `execute_cmd`，不是另写状态转移模拟。首轮误把 Command 直接加入 cmdsethandler，
产生 `Only CmdSets can be added to the cmdsethandler!`；夹具 #34–37 保留，没有便笺交付。
修为真正的 `EnsembleBridgeTestCmdSet` 后第二轮三条验收已执行成功：

| 原始现场路径 | 实际结果 |
|---|---|
| 提案后目标从 #38 移到 #39，再 settle | 世界拒绝；便笺数 `0→0`；没有 receipt，没有 Ensemble commit |
| 目标回 #38，重新提案并 settle | Evennia 创建 #42，转入目标 #41 库存，之后才 commit 原 JS 社会效果 |
| 同提案再次 settle | 便笺数 `1→1`，复用结算，不再创建 |

第二轮末尾输出失败于 `_SaverList is not JSON serializable`，不掩盖这个记录缺陷。
三条执行结果已先保存在玩家 #1 的 `ensemble_bridge_rawlog` Attribute；父级用原生
`evennia.utils.dbserialize.deserialize` 读取该**既存**日志，浏览器回显 `status=PASS`，
SQL 另确认 #42 的 `db_location_id=41`。这次读回没有重新执行交付。
完整原件由 DB 导出为 `outputs/native_platform_p1p2_v0/bridge_20261010/first-live-success.json`；
公开副本及最终代码回归见 [RESULTS](RESULTS.md)，不能把此早期日志冒充最终代码输出。

`writeLoveNoteReject` 是 Ensemble 原例中的叙事/社交拒绝，**不是**世界动作验证失败；
成功送达便笺后发生这种原例回应合法。位置只用于实际执行验证，不推断角色情感。
桥接是独立窄命令探针，没有替换或冒称官方 EvAdventure FSM 已调用 Ensemble。

## 最终代码四场景回归

父级终止仅该桥接的旧 Node 子进程，reload 两个窄适配模块，随后在浏览器调用
`me.msg(run_live_probe.run_json(me))`；没有重建官方地图或重启游戏服务器。
回显 `status=PASS`，room #65、away #66、actor #67、target #68。
此次真实四条路径是：过期位置拒绝；便笺 #69 实际交付给 #68 后 commit；重复反馈无新物品；
成功后驱逐桥接进程内 completed 缓存并恢复原 pending，复用 #69 重新确认，
`doActionCalled/triggerCalled/nextStepCalled` 全为 false、物品数 `1→1`。
这是**同进程缓存缺口测试**，不是服务重启/磁盘恢复测试。

已从玩家持久 Attribute 导出[最终 rawlog](evidence/bridge/final-live-20261010T1735Z/rawlog.json)，
SQL [独立回读](evidence/bridge/final-live-20261010T1735Z/world-readback.txt) 确认 #67/#68
同在 #65、#69 `db_location_id=68`；导出副本与原件逐字节相同并附 SHA-256。
初轮成功日志保留未覆盖；最终序列化没有再出现 SaverList 错误。
