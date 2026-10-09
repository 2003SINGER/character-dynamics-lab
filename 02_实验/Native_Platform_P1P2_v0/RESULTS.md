# Native Platform P1/P2 v0｜实际结果

日期：2026-10-10（Asia/Shanghai）。状态：**技术交付 READY_FOR_INDEPENDENT_REVIEW；用户亲自试玩 UNCONFIRMED**。
起点 `976658b92195af0cff6b8cb9d1453171950636fe`，独立开发分支
`codex/native-platform-p1p2-20261010`；本次只做 P1/P2 原生复现、最窄互通及 LIGHT 限时探针。
代码工作委托 Luna，父级审查实际接口、重跑 JS 测试并实际操作原生浏览器。
这不是玩家实验、完整人物系统、心理效度或新方法结果；没有实施 P3/P4。

## Gate 与明确判断

| Gate | 实际结果 | 证据与边界 |
|---|---|---|
| P1-env | PASS / isolated | Python 3.12.14、Evennia 6.0.0、Django 6.0.9、Twisted 24.11.0；44 项 [lock](../../tools/native_platform_v0/evennia/requirements.lock)。[bootstrap.log](evidence/evennia/bootstrap.log) 是既存环境复验，不是首次安装全日志 |
| P1-native basic game | PASS | 原 `evennia --init`/migrate；浏览器原 builder `batchcode evadventure.build_techdemo` 4/4 完成，DB 读回官方房间和 NPC 类型 |
| P1-native roaming, unchanged | **FAIL** | 官方 `npcs.py` 导入 `choice` 却调用 `random.choice`，真实 NameError；[原日志](evidence/evennia/server.log) 保留 |
| P1-native roaming, minimal shim | **ADAPTED_PASS** | 本地 ticker 补模块名、5 秒调用原 `.ai.run()`；原 wheel 字节未改，持久 [40 条 movement](evidence/evennia/movement.json)，父级看到自主进入/离开消息 |
| P1-player agent operation | PASS | 原 Web client 登录、`get/drop/look/techdemo`；对象位置 SQL 独立回读；[父级浏览器审计](BROWSER_AUDIT.md) |
| P1-player human operation | **UNCONFIRMED** | 已把本机客户端交给用户；没有“已亲自试玩”确认，代理操作不能替代真人 gate |
| P2-original example | PASS / original JS in Node VM | 原 LoversAndRivals 六个 JSON 与原 bundle；volition→动作→效果→显式 trigger→下一 step。[原件及调用方式](../../tools/native_platform_v0/ensemble/README.md) |
| P2-upstream tests | 45/45 groups PASS | 原 test source/bundle；最小 DOM append shim。ExternalApplicationTest 未运行，legacy doAction test 原仓库注释停用，不将它们计作 PASS |
| P2-new interface tests | 28 assertions PASS | 父级独立重跑。全批 schema/cast/range 预校验、stale revision、source ID、authorize、伪造 HMAC 拒绝、receipt/action 约束及重复提交；这是新增探针，不是原件测试 |
| Bridge actual world seam | **4/4 live cases PASS** | 父级从浏览器实际执行最终代码；拒绝 `0→0`，交付 receipt #69（库存 #68），重复 `1→1`，同进程 cache-gap 恢复仍 `1→1` / doAction=false；[最终 rawlog](evidence/bridge/final-live-20261010T1735Z/rawlog.json) 与 [独立 DB 回读](evidence/bridge/final-live-20261010T1735Z/world-readback.txt)。首轮 #42 原件另存，不冒充最终回归 |
| LIGHT no-model admission | **NO_GO_WITHIN_THIS_TIMEBOX** | 固定原源码，依赖解析长期回溯取消；原入口真实失败 `No module named hydra`。无 look/action/世界变化；[失败及捕获缺口](evidence/light/RESULT.md)。不据此判算法不可用，不阻塞主线 |
| Existing asset reuse / P3 plan | DELIVERED / not implemented | [源码级复用矩阵与 P3 清单](REUSE_AND_P3.md)。旧 Executor 不再结算新世界，TypedIR coverage 不补造；不自动扩村庄/Director |

**工程决策：Evennia + Ensemble 继续保留为后续 P3 候选基座，技术 GO 有边界；
完整玩家 gate 未关、独立复核未完成，不自行 CLOSED。LIGHT 本轮 NO_GO，停止依赖改造。**
现在降低的是“原平台/原算法能否在本机真实运行、最窄接缝是否可执行”的不确定性，
不是“组合系统是否有生命感、低作者成本或科研贡献”的不确定性。

## 原件、适配和物理执行的归属

Ensemble 固定原件 `ensemble-engine/ensemble@8b74bdec4ba2ef4e14795b7591df3b5d73f283e3`
（1.1.1，BSD-4-Clause），Node v26.8.2。没有以 Python 社交规则仿制品冒充复现。
`hero→love closeness` volition 权重 20，原动作候选 `writeLoveNoteReject` / `kissFail`。
探针按动作名选择前者，不冒充一般自主采样。原 `doAction` 写 closeness=10 和 romantic-failure；
显式 `runTriggerRules` 才写 rival confident 与 love→rival closeness=10；下一 step 将 mood duration 3→2。

Evennia 独占房间、库存、便笺对象与物理执行。桥接保留命令事件和结算 receipt，Node 只拥有
共享 social record；它不是角色私有 O。存储的 hero/love 元数据才被投影为原 schema facts，
位置用于世界验证，不凭位置推断情绪。提案阶段的 `socialRecordUnchanged` 仅表示**事实投影后**
计算 volition/actions 不改记录；不表示整个 propose（含投影）完全不写 social record。

世界不允许执行时，没有 receipt、便笺或社会动作 effects；原例 `writeLoveNoteReject`
则是**合法送达后的叙事回应**，不同于世界验证拒绝。社会 commit 要匹配 event/action/receipt
并由可信游戏桥接签名。成功社会变化不再次创建物理便笺；重复回执只复用，不重复调用 effects。
桥接测试是单独 CmdSet，**没有把官方 NPC FSM 重写为 Ensemble AI**。

## 已修缺陷、证据缺口及未承诺能力

- 原 EvAdventure 缺失模块名由最小 shim 处理，原 wheel hash
  `9a84dd3683cd5761b2eaaffb2b326561950cd6b54e457a42ecc5173e208b6e6f` 前后不变。
  它只证明官方 roaming 能运行，不是长期生活、关系/任务自主系统。
- 桥接首次 Command/CmdSet 接线失败和随后 SaverList 日志渲染失败均记录于
  [BROWSER_AUDIT](BROWSER_AUDIT.md)；首轮已成功的 DB 日志导出后才开始后续回归，不覆盖原件。
- 事实输入采用整批预校验，原 setter 仍逐项写入，**不是数据库事务**。
  revision 在实际写入前递增，失败也让旧提案失效；不声称部分写入可原子回滚。
- 幂等账本与提案为进程内状态。匹配的 committed authorization 可重复确认，支持同进程
  完成缓存缺口后的回执复用；不承诺服务/Node 重启后的恢复或跨进程事务。
- 物理交付已发生、社会提交失败时保留实际便笺与 pending journal，不回滚世界历史。
  生产级崩溃恢复、全局社会 record 的角色访问权限、动作持续进度和自主感知属于后续设计，
  不作为本次 P1/P2 已实现能力。
- 首次安装/migrate 与部分启动错误没有完整原始文件；后续 bootstrap 是实际复验。
  Django 模型/migration warning 保留，不自行生成上游 migrations。LIGHT 依赖解析 stdout
  也未完整落盘；真正入口的 stderr/stdout 已保留。所有这些缺口不补造日志。
- 公开的 `movement_capture_failure.log` 为零字节，不能支持 run note 中“失败保存于该文件”的
  说法；首次错误只在工具回显中观察到。成功 movement JSON 独立有效，空 stdout 也不算运行成功。
- 浏览器使用隔离 builder 超级用户，仅此次准备/验收；普通账号权限未验。
  测试 Telnet helper 和无登录记录的临时 p1builder 账号已移除，可重建；游戏对象/失败夹具保留。

## 复现与交付

- [Evennia 安装/启动/停止与原命令](../../tools/native_platform_v0/evennia/README.md)
- [Ensemble 固定原件与测试](../../tools/native_platform_v0/ensemble/README.md)
- [桥接调用与实际日志](../../tools/native_platform_v0/bridge/README.md)
- [公开小型证据目录与哈希](evidence/README.md)：只提交无凭据的具体日志/JSON；原件缓存、
  venv、SQLite、secret_settings、完整原始目标对话不公开。
- 本机实际客户端：`http://127.0.0.1:14001/webclient/`，输入 `look`、`back`、`techdemo`。
  原生服务所有接口只监听 127.0.0.1，14000/14001/14002/14005/14006；没有占用 QQ 的 4001。

父级最终静态/语法检查、JS tests 与证据 hash 通过；repo_health exit=0，11 warnings
来自忽略目录中的依赖大文件与既存原始材料重复，未修无关内容。
本次不重跑/修改 frozen C++、E0/E1，也未混入既有脏 CMake/配对实验源码。
CI 只能按对应提交的实际状态报告；既有 CI 不运行这次 Evennia 现场交互，不能替代上述证据。
公开材料既有两个契约单测各 10/10，inventory/projection 检查通过；首次在只读沙箱中
运行需要临时目录的单测受到权限拒绝，获准临时写入后重跑通过，不当作算法失败。
代码/维护文档 diff whitespace 检查通过；原始 `evadventure_npcs_roam.log` 的 EOF 空行
保留字节原样，因此全量 `git diff --check` 有该条警告，不为格式修改原始证据。

**停止：等待独立审阅与用户试玩确认；P3 只给清单，不自动实施。**
