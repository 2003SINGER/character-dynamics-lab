# 现有资产复用与 P3 实施清单

状态：源码接缝审阅；P3 **未实施、未授权自动开始**。本轮只做原生 P1/P2 与最窄互通探针，不把规划、人物观察、作者约束全部移植进新世界。

## 复用不是把旧 Executor 再运行一遍

| 现有资产 / 实际接口 | 可复用的具体机制 | 在 Evennia 中必须替换的部分 | 本轮状态 |
|---|---|---|---|
| `tools/e1_keyledger_v0/planner.py::uniform_cost_search` | h=0 堆排序搜索、累计动作时间、扩展/墙钟预算、预算不足与不可达区分 | 钥匙账本 `_key`/算子/公开 B 合作预测不是通用域；输入须改为独立角色合法观察，不能把 Evennia DB 全量快照传入 | 只审阅，不移植 |
| `tools/npc_system_v0/planners.py::propose(view, implementation, max_expansions, wall_seconds)` | GOAP/HTN 选择接缝；真实 GTPyhop domain/session；方法分解和预算检查 | `return_tool/offer_loan/unlock/take_ledger` 方法与预测算子全属旧有限域。新移动、交互、取得物品须注册新领域，规划效果永远只是预测 | 只审阅，不移植 |
| `tools/npc_system_v0/system.py::actor_decision` | 目标选择→角色自己的策略/规划→请求；不等于全知中央控制 | 串行 A/B 槽位、stress 字段、deadline=10 与旧 checkpoint 结构不能直接作为持续游戏 NPC | 只审阅 |
| 同文件 `world_proposal` / `System.execute` | fork rollout、有限候选比较、真实执行后反馈的实验思路 | 会 fork 并运行旧 Python 世界；不可用于 Evennia 结算，也不能复制进第二个物理 W/时钟。完整 Director 留给 P4 | 禁止直接接入 |
| `tools/npc_system_v0/executor.py` 与 E0/E1 Executor | 启动验证、原子效果、append-only receipt、真实事件与预测分离的契约 | 具体实现拥有旧 W；Evennia 将成为新世界唯一执行者。新 receipts 必须来自实际命令/对象变化，而不是旧 Executor 的模拟结算 | 旧实现保留冻结 |
| `tools/npc_system_v0/author.py::registry/requirements/monitor` | TypedIR 类型检查、真实证据优先、事件约束与状态约束分开 | 固定 ledger/loan/stress refs、t=2..10、每分钟完整 snapshot/seal 假设不可照搬；需定义新生产者/事件/值覆盖契约 | 只审阅 |
| `tools/trajectory_constraints_v0/trace.py` 与 `monitor.py` | `Point/Event` 的 identity/time/sequence/version/provenance；认证 segment；coverage seal；不完整窗口保持 unknown；MonitorSession checkpoint/fork | Evennia 适配器须提供真实事件与被证明的覆盖。稀疏 DB 采样不能冒充连续轨迹，缺字段不得补造 seal | 复用底层 reference，未接游戏 |
| 官方 EvAdventure `AIHandler` | idle/roam/combat/flee 原生状态方法，作为最低限度自主行为参照 | 示例 FSM 不等于认知/人物规划。自动调度须显式接线，不新增心理规则 | P1 原生验收 |
| 官方 Ensemble social record / volition / ActionLibrary | 社会事实条件匹配→volition 规则累加→动作绑定/排序→提交社会效果与 trigger | shared social record 不是角色私有 O；游戏位置/物品/权限仅 Evennia 结算。提案不调用 doAction，拒绝不提交，成功反馈有去重 ID | P2 + 最窄探针 |
| 冻结 C++ Kernel / Dynamics / Laya | 既有工程回归、单时钟/信息边界与失败证据 | 不作为 Evennia 下游第二个时钟/执行器；不把旧单人房间 trace 拼成新游戏事实 | 完全不修改 |

## P3：授权后才执行的第一条完整链

1. 固定小村庄三名 NPC、四个地点的创作实例；列出角色日常目标、可用对象、允许玩家扰动。先明确每个领域动作，不造通用插件框架。
2. Evennia 持久对象拥有位置、库存、资源与游戏事件序列；定义实际动作起止/失败/完成 receipt。选择并记录游戏时间 owner，不能把 planner 墙钟或 Ensemble timestep 当游戏时间。
3. 为每名角色生成独立 O 视图：所见、所闻、自己反馈及知识来源。数据库可查询不代表 NPC 可知；缺失信息保留 unknown，shared social record 的知识访问需单独决定。
4. 把一项任务接到成熟 GOAP/HTN：先手算路径与不可达反例，再注册新预测算子/HTN 方法；Planner 输出请求，不写 W。用相同领域与信息预算比较，不沿用账本公开 B 策略假设。
5. 在同一个世界中运行 NPC 感知→目标→提案→Evennia 再验证→真实反馈→更新局部 O/社会记录。只有真实结算成功能提交 Ensemble 社会效果；stale proposal、玩家先取走物品、拒绝、重复反馈必须保留原始结果。
6. 定义任务/承诺的开始、暂停、继续、完成；合法在途进度不得因普通 reconsideration 重置。若选用的平台动作没有持续进度机制，明确缺口，不称已具备。
7. 浏览器玩家实际移动/改物品/传消息；核验 NPC 无玩家时活动与玩家扰动后的未来调整。保留失败录像/命令/世界前后，不导演一条预定成功轨迹。
8. 将有限真实事件投影给 TypedIR，只在 receipt 前缀完整时 seal 事件，值覆盖另记。P3 不要求完整 Director；P4 才引入有限作者目标及合法世界机会候选。

停止标准：同一 Evennia W 中一条可重放角色链与扰动反例，而不是完整 RPG。P1/P2 技术 GO 只说明原件及接缝可用；不证明新算法、角色生命感、低创作成本或社会心理有效性。
