# Veloren 原生因果网络：研究实例准入底图

日期：2026-10-18。状态：**当前实例 NO_GO / READY_FOR_INDEPENDENT_REVIEW**。NO_GO 只表示同一状态、同一权限下的两条合法因果方案尚未建立；不是 Veloren 全局不可能，也不是 planner 失败。未知状态仍为 UNKNOWN。

## 版本、运行与来源等级

官方源码锚点：Veloren `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。本地对象库已确认该 commit 与本文映射的文件路径；下列 GitLab 固定 commit URL 是源码定位链接，不表示本轮访问网页。所有图均为 **SOURCE_ONLY**，除明确指出的既有 RUN_NATIVE 事实外，未在这些路径上新运行。

既有运行分别引用[Talk 接口 A RESULTS](../Veloren_Vertical_Slice_v0/RESULTS.md)与[Native Decision Integration v1 RESULTS](../Veloren_Native_Decision_Integration_v1/RESULTS.md)：截至审阅基线 `a7a6e8f64f20e66a448db8f49ae23e37fbb5645f`，前者覆盖有限 Talk，后者覆盖 476→442 Hired/follow。它们不是两方案或作者中途编辑实例。Loaded Msg 修复使用[独立补丁](../../tools/veloren_native_decision_v1/veloren-native-loaded-msg-repair.patch)，SHA-256 `4883c461895833d493b130143df5f0dd3245b31d00a8324e8b87e90d6ea84ee1`，顺序应用于官方源码 + A + Decision；它修复路由/来源关联，不增加 Report 或 Quest 算法。带补丁运行版本与官方源码分账，本文不使用补丁偏移后的行号。

来源等级：`SOURCE_ONLY` = 固定源码中的可追踪机制，可支持研究设计准入但不代表新实跑；`RUN_NATIVE` = 已有原生运行回执，只限明示路径；`UNKNOWN` = 当前证据不能裁定；`NOT_ESTABLISHED` = 当前实例尚未建立该条件，不等于全局不存在。

## 因果图 1：两个角色各自的招募、Job 与跟随分支

```text
leader 分支：自身状态/合法候选
  → pirate AI 靠近候选
  → RequestHire 原生消息
  → receiver inbox 消费，安排约 2 秒响应等待
  → 原生 setter 写 Job::Hired(leader)

receiver 分支：Job::Hired
  → humanoid/hired 选择跟随任务
  → 原生跟随 / Goto
  → 事件可打断；没有自动 cancel 或旧 Job 栈恢复

leader 后续分支：独立旅行 / 当前活动（raid 本体是 villager 占位）
  → 回家流程
  → leader 发送 EndHire
  → receiver 当前 Hired Job 清除（不恢复被覆盖的旧 Job）
```

| 环节 | 前提 / 写入者 | 消费者、时间与中断恢复 | 固定源码位置 / 证据 |
|---|---|---|---|
| 产生请求 | leader 在 home、有 faction、附近目标站点 <10km、至少四名存活同派未受雇 Pirate(false)，通过随机门；接近候选到 <6m 后发 RequestHire | receiver 消费消息，约 2 秒响应等待后写 Job。该分支无收方 consent 或旧 Job guard；paid Character hire 是另一对话路径，不代表 NPC 协商 | [`npc_ai/mod.rs` Hire](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/mod.rs#L360-502)，SOURCE_ONLY |
| 设置与消费 Job | setter 写 Hired 可覆盖旧 Job，无旧 Job 栈；Controller reset 从 Npc.job 读取，AI 输出在 tick 后同步回 Npc.job | Job 改变时停止旧跟随；雇佣到期、对雇主达 RIVAL 或雇主不存在可清 Job。NPC RequestHire 写无限期限，不能套用玩家付费雇佣的到期路径。普通事件打断不等于取消 | [`data/npc.rs` reset/setter](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/data/npc.rs#L63-147)；`npc_ai/mod.rs` 603–636、1431–1458、1514–1522，SOURCE_ONLY；476→442 有限链为 RUN_NATIVE |
| 结束雇佣 | leader 完成旅行、60–120 秒 villager 占位活动及返家后，向 home population 中受其雇佣者发 EndHire；收方仅在 hirer 匹配时清 Job | 启动需至少四名合格候选；雇员 >3 才有随机停招分支，候选耗尽也可结束，不能断言受扰后必然雇足四人。raid 本体仍 TODO，本轮不扩四人/raid。Job 清空后重新选择职业活动，不恢复旧任务栈 | [`npc_ai/mod.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/mod.rs#L360-502)、1450–1458、1539–1555，SOURCE_ONLY |

## 因果图 2：伤害、报告、关系状态与后续反应

游戏里至少有两条不同的事件到 sentiment 写入路径；实际受伤产生 OnHealthChange 后写 sentiment，不经过 Report。

```text
直接 HP 变化（受伤）
  → simulate_npcs HPchange
  → sentiment 更新
  → RIVAL 等关系后果 / hiring 终止

真实 theft / death 事件
  → ReportEvents 产生报告
  ├─事件位置附近直接分发（Death 32m / Theft 24m）
  │   → 收件者检查未知且有效的 ID → 消费并记 known_reports
  │   → 职业兼容 / 既有敌意条件 → sentiment
  └─已知报告的 NPC 回到自己的 home
      → home site noticeboard 共享同一 ReportID
      → 其他 home NPC 各自消费并去重

sentiment 后续：
  ENEMY → Loaded 原生 Agent 尝试攻击（Simulated 下攻击动作会被丢弃）
  RIVAL → 可结束当前 hiring
  时间推进 → sentiment 衰减
```

| 环节 | 前提 / 写入者 | 消费者、时间与中断恢复 | 固定源码位置 / 证据 |
|---|---|---|---|
| 受伤直接路径 | HPchange 由实际伤害写入；`simulate_npcs` 另行读此事件写 sentiment，不需要 Report | 与报告路径分开；不能把 HPchange 说成 Report 的子步骤 | [`simulate_npcs.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/simulate_npcs.rs#L48-64)、[`entity_manipulation.rs` HP](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/server/src/events/entity_manipulation.rs#L278-297)，SOURCE_ONLY |
| 报告生产与直接分发 | 带位置 OnDeath 在 32m、OnTheft 在 24m 内创建并投递同一 ReportId；Theft 上游为 owned sprite 的 Collect 结算，未发现 NPC 自主偷窃生产链 | 不先写 home noticeboard；分发没有 LOS/faction 过滤，是原生信息规则而非人的视觉模型。killer=None 的死亡事件不能当谋杀证据 | [`entity_manipulation.rs` Death](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/server/src/events/entity_manipulation.rs#L1366-1394)、[`inventory_manip.rs` Theft](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/server/src/events/inventory_manip.rs#L354-390)、[`rule/report.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/report.rs#L19-75)，SOURCE_ONLY |
| 接收、home 分享 | NPC 处理未知且仍有效的 ID；Civilised 才消费 Death，Theft 须 site==home 才改态度。已知者回 home 后共享 ID，其他同 home NPC 再各自消费 | 共享 ID 不是独立证据；Say 不反向写知识。5 分钟只门控台词；有 killer 的 Death 保留15游戏日、无 killer 5日、Theft 1.5日。过期 ID 无效，态度另行衰减 | [`npc_ai/mod.rs` report](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/mod.rs#L1238-1423)、[`sync_npcs.rs` home site](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/sync_npcs.rs#L112-127)、[`data/report.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/data/report.rs#L31-77)，SOURCE_ONLY |
| sentiment 与敌意 | Report 的职业/敌意筛选路径及独立 HPchange 路径都可写 sentiment；`Sentiments::decay` 随时间衰减 | ENEMY 的 Loaded Agent 尝试攻击；Simulated 下攻击动作会被丢弃。RIVAL 可使当前 hiring 结束。不声称 sentiment 固定稳定时长 | [`data/sentiment.rs` thresholds/change](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/data/sentiment.rs#L124-170)、threshold check 208–215、decay 188–201；[`npc_ai/mod.rs` enemy/root](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/mod.rs#L1466-1478)、1487–1555；SOURCE_ONLY |

直接攻击把 RTSim `Attack` 映射为 hostile target；`permit_pvp` 未设通用 RTSim faction 拦截，非玩家且非同 owner 宠物的此项检查可放行。见 [`behavior_tree/mod.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/server/src/sys/agent/behavior_tree/mod.rs#L634-644)、[`melee.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/common/systems/src/melee.rs#L248-256)、[`combat.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/common/src/combat.rs#L1146-1208)。**源码**的 Hire 准入不排除预存非对称 ENEMY；`ENEMY → 实际攻击 → 受伤者 RIVAL / quit hire` 在机制上可能成立，并非既有 run 已证。当前缺同一世界初态的原生来源、命中/存活/期限及两方案同权限可择证据，保持 UNKNOWN；不额外要求“中性起点”。死亡 Report 对双方均为 Civilised Pirate/Cultist 的 `can_damage_killer=false` 只限制社会评价写入，不能外推禁止实际伤害。其他兼容组合会按死者是否敌人对 killer 加 +0.25 或 -0.75；home Theft 对 thief -0.2。直接受伤独立地对 cause -0.1，实际阈值按126刻度量化，不能把实数加法或报告条数当结算证据。

## 因果图 3：Character 发起 Quest 与 NPC escortee

```text
NPC merchant：无 Job；destination 距离 1000–5000m；deposit 可用
  → Character 对话 yes（不是 NPC 主动接单）
  → 扣押 deposit 成功
  → create Quest + Job
  → 原生 NPC escortee 跟随
      ├─到达 + 对话 → arbiter 单次 resolve → 完成并奖励
      └─期限到 → timeout resolve → 失败结算

NPC generic Actor ≠ 自主接受者；NPC smalltalk 是另一条有限对话路径。
```

| 环节 | 前提 / 写入者 | 消费者、时间与中断恢复 | 固定源码位置 / 证据 |
|---|---|---|---|
| 入口 | generic `quest_request` 由 Character 发起；NPC smalltalk 单独处理。Quest 要求 merchant 无 Job、目的地距离 1000–5000m、deposit 等条件 | Character yes 后创建 Quest 与 Job；generic Actor 类型不等于 NPC 自主规划/同意 | [`dialogue.rs` general/paid](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/dialogue.rs#L3-33)、260–316；[`npc_ai/mod.rs`入口/consumer](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/mod.rs#L218-230)、1524–1536；SOURCE_ONLY |
| 执行与结算 | Quest/Job 创建后由原生 NPC escortee 行为跟随 | 到达并对话后 arbiter 仅 resolve 一次并给奖励；期限到则 timeout resolve 并失败。NPC 作 escorter 的自主接受入口仍 TODO，不补造 | [`npc_ai/quest.rs`](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/rule/npc_ai/quest.rs#L116-196)、288–361；[`data/quest.rs`resolve](https://gitlab.com/veloren/veloren/-/blob/1d12f35edd6cdbfc1fb921c167cdd7beeeffe248/rtsim/src/data/quest.rs#L195-225)，SOURCE_ONLY |

Quest 的具体边界：目标站点须不是当前站点；候选目的地以15分钟时间桶固定选择，奖励按距离/25、期限按 `1 + 距离/80` 分钟计算。No、缺 deposit 或扣押失败不创建该任务。escortee 跟随约5m，落后超过20m可发等待台词；任务已被解决/删除时停止。旅行阶段的停止谓词也接受“目的站点不存在”，所以不能仅凭它停止移动就证明合法到达，必须核后续 arbiter resolution 与原生地点证据。序列化 Job/Quest 只证明存储结构存在，不证明读档后活动/对话进度恢复。除 Escort 外，当前 Quest 枚举另有 Slay，但其对话任务分配给 Character，未发现可据此补出自主 NPC 护送者的分支；不将它扩成第三候选。

## 既有成熟方法与复用边界

既有 [Author Obligation Planning 结果](../Author_Obligation_Planning_v0/RESULTS.md)记录 **14 个不同的可行作者任务有原生 PASS 证据**；有限手工域已展示过程约束可进入搜索、编辑后可据历史重规划。它不代表 Veloren 能力。既有 [Mature Methods 结果](../Mature_Methods_Integration_v1/RESULTS.md)的 GT/event-driven 配对在 T7 的规范化执行序列 diff=0；这不是速度比较，且 Evennia 手工内容不能搬作 Veloren 原生能力。

Mimesis、PDDL3/Porteous 仅复用既有算法卡：[Mimesis 卡](../../01_文献/算法积木/01_叙事修复与导演.md)、[PDDL3/Porteous 卡](../../01_文献/算法积木/02_人物意图与约束规划.md)。不在本轮扩展文献清单或声称重读全文。Mimesis 的 causal-link threat 可触发 accommodation，对未执行后缀重规划；作者需建动作前提/效果、因果链接、顺序与必要 failure modes。PDDL3 给轨迹约束语义，本身不是求解器；Porteous 以 PoV 选 landmark 并重规划当前子目标，需人工建模算子与约束图，无解恢复并非其保证。成熟方法可覆盖过程约束与未来重规划；是否足以解决本研究实例及其建模成本，要通过后续具体比较决定，不能据此宣称新问题无创新。

