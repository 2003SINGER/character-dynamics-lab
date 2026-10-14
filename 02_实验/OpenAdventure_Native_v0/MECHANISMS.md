# Open Adventure 1.22：原生状态与 NPC 机制审计

状态：`READY_FOR_INDEPENDENT_REVIEW`（未 CLOSED）。

审计对象是隔离目录 `_local_data/external_games/open_adventure/upstream` 中的 Open Adventure 1.22，tag `1.22` 解析到 commit `e6160529e70a8c7a06b9a5f190d69aa35c4c62f5`（tag object `a58e03033307122cd56cb2c60259c377b49230dd`）。本报告是源码审计和上游 fixture 选型，不声称下列回放已由本报告作者执行，也不声称游戏具有人类式记忆或独立人格。源码链接固定到该完整 commit。上游许可证为 BSD-2-Clause，许可证文本在该版本 `COPYING`；没有把上游完整源码或游戏资源复制进项目报告。

## 状态读写与可观察边界

| 机制/状态 | 状态由谁写入 | 后续由谁消费、何时触发 | 普通玩家/runner 合法可见性 | 缺项与解释边界 |
|---|---|---|---|---|
| 洞穴矮人 `dwarves[i].{loc,oldloc,seen}` | `dwarfmove()` 按可达洞穴路径更新位置；与玩家相遇时设定 `seen`。 | 主循环每轮先运行 `do_move()` 再运行 `do_command()`；`do_move()` 会调用 `dwarfmove()`，即使 `newloc == loc` 也无条件调用。随后由 `dwarfmove()` 内部的 `LOC_NOWHERE`、forced location、`COND_NOARRR` 等 guard 决定是否提前返回。深洞中曾见玩家的矮人继续追踪；`do_move()` 还用 `oldloc` 和 `seen` 检查矮人是否挡路。 | 可见地点描述、矮人出现/投刀/死亡文本、被挡路反馈；正常文本接口不显示 `seen`、`oldloc` 或精确 NPC 坐标。 | 这是有限的遭遇与追踪 latch，不记录角色传记、承诺、关系或对事件的解释；离开深洞条件后，`seen` 不持续作为长期关系记忆。行为受主循环和 LCG 随机选择驱动，不等于 NPC 自主目标规划。 |
| 矮人阶段 `game.dflag` | `dwarfmove()` 在玩家到达深洞、遭遇首个矮人、矮人首次投刀时递增/切换。 | 主循环每轮调用 `do_move()`；其中无条件调用 `dwarfmove()`，而具体阶段处理受该函数开头的内部 guard 控制。`dflag` 决定是否激活、矮人移动与投刀命中率。无效/澄清输入可能在 `do_command()` 内重复读取；forced movement 也可能无需新输入而回到主循环，因此不能把一次输入等同一个世界 tick。 | 会看到遭遇、投刀及命中/落空等输出；阶段整数本身不在普通输出中。 | 单一世界级阶段/强度标志，不是逐个 NPC 的好感、信任、合同或持续意图。 |
| 海盗与宝物、宝箱状态 | `spotted_by_pirate()` 根据玩家位置、`tally`、宝箱是否已发现、玩家携带/所在位置的 treasure 和 lamp 状态移动宝箱/留言并转移宝物；重置海盗的位置和 `seen`。 | 同一 `do_move() → dwarfmove()` 链在符合海盗遭遇条件时处理，玩家位置不必改变；读取当前物品与宝箱状态决定是否偷取或移动宝箱。 | 玩家能看到海盗出现/抢夺的文字、物品离开库存或出现在洞穴中的反馈。普通接口不暴露内部判断值。 | 读取的是当前游戏/物品进度状态，不是海盗对特定人的信任、关系或借还经历。不能将“会偷宝物”表述成有持续敌意建模或目的性计划。 |
| 物品属性与位置 `objects[obj].{prop,place,fixed}` | 原生动作 handler（如 `vcarry`、`discard`、`wave`、`fill`、`pour`）和世界过程（如海盗）更新属性与位置；对象/初值来自游戏数据。 | `action()` 把解析后的动词/宾语分派到 handler；handler 按前置条件改变状态或返回解释文本。移动结果还进入 `playermove()` / `do_move()`。例如 rod、自由鸟与所在位置共同决定 `wave rod` 是否取回 jade 或搭建/撤销裂隙桥。 | 地点/库存描述、行动成功与失败文本、可见物品与通路状态。 | 这是上游游戏作者设计的状态转移和谜题组合。规划器可以组合合法原生命令，但组合本身不证明新的规划算法、原创剧情规划或 LLM 语义能力。 |
| 回合和随机数 `turns`、`lcg_x` | `do_command()` 每次从 `get_command_input()` 成功取得命令后增加 `turns`；yes/no 响应不计为命令回合。`randrange()` 读取并推进 `lcg_x`。初始化取时间种子，显式 `seed` 命令可重置 LCG，并生成鸟的魔法词。 | `turns` 用于计分/阈值等回合条件；`randrange` 在矮人出现、选路、攻击命中、海盗提示等分支被消费。主循环每轮先 `do_move()` 后 `do_command()`；因此不能据此把每条输入解释为单独一次 NPC tick。 | 普通游戏可显示回合数和结果文本；不显示内部 PRNG 游标或全部世界结构。测试日志中的 `seed` 是复现控制，不是 planner 可选的剧情动作。 | 对随机游戏，声称可复现必须固定完整游戏状态（含 LCG 游标、隐藏 flags、位置/道具、turn 等）、同一二进制/数据/设置及相同未来输入。只有相同可见文本并不足以推出相同未来。源码支持把 `game_t` 整体写入 save，但不代表任何外部 adapter 已暴露该状态。 |

主要源码路径：[`advent.h` 游戏状态结构](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/advent.h#L179-245)、[`main.c` dwarfmove 与海盗状态转移](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/main.c#L231-474)、[`main.c` 玩家移动到 NPC 更新链与内部 guard](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/main.c#L1199-1247)、[`main.c` 命令回合和 action dispatch](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/main.c#L1302-1430)、[`main.c` 每轮 `do_move()` 后 `do_command()` 的主循环](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/main.c#L1578-1588)、[`misc.c` LCG 与 seed](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/misc.c#L750-776)、[`saveresume.c` 保存完整 `game` 结构](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/saveresume.c#L32-43)。物品例子见 [`actions.c` 携带鸟条件](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/actions.c#L386-425)、[`actions.c` 放飞鸟和攻击蛇](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/actions.c#L561-586)、[`actions.c` rod、鸟、裂隙与 jade](https://gitlab.com/esr/open-adventure/-/blob/e6160529e70a8c7a06b9a5f190d69aa35c4c62f5/actions.c#L1360-1400)。

## 最多三个上游 fixture 回放建议

以下均为**源码/已提交输入输出 fixture 选型**，不是本报告新运行的实验或运行结果。`*.log` 含实际输入和随机种子，配套 `*.chk` 是该版本上游期望输出；runner 应运行后对比 `.chk`，并在自己证据中记录实际输出、退出码及版本。

| 用途 | 固定输入与期望输出 | 已有种子 | 源码核对点与建议观察 |
|---|---|---:|---|
| 物品前置与谜题组合（正反均在一条 fixture 内） | `tests/dropcagedbird.log` → `tests/dropcagedbird.chk` | `1495951709` | 测试先在持有 rod 时尝试抓鸟，失败；放下 rod 后成功。随后在 dome steps 释放鸟并挥 rod，鸟取回 jade。对应 `actions.c` 携带鸟与 `wave()` 条件。只把它解释为上游固有条件组合。 |
| 原生 NPC 世界过程 | `tests/pirate_carry.log` → `tests/pirate_carry.chk` | `1837473132` | 上游说明为 carried treasure 被 pirate 偷走的 fuzzed replay。对应 `spotted_by_pirate()` 检查 carried treasure 并移动到 pirate chest 的条件。它证明的是物件/地图后果，不是关系历史。 |
| 矮人移动、遭遇与投刀负面/正面结果 | `tests/dwarf.log` → `tests/dwarf.chk` | `1494912171` | 固定种子、长路线触发矮人现身、投刀、阻路及死亡；适合核对逐步文本与 `dflag`/`seen` 代码路径。死亡结果是游戏规则，不是 planner 成功指标。 |

建议命令：在已构建的隔离源码根目录运行 `make check`；单独复放可运行 `cd tests && make run-regress-dropcagedbird run-regress-pirate_carry run-regress-dwarf`。上游 `tests/Makefile` 的 regression target 由 `*.log` 生成，将本地 `advent` 输出交给 `tapdiffer` 与同名 `.chk` 比较；执行应由 runner agent 记录，不将 `-d` 调试输出或直接读出的 `game_t` 字段提供给 planner。输入、期望回执和目标定义由游戏公开；隐藏内部状态只用于源码审计与解释，不是玩家合法 observation。

## 能力归属

| 游戏已有 | Planner 可能组合 | 尚缺的作者叙事语义 |
|---|---|---|
| 原生命令解析、地图/通路、物品状态、谜题前置条件、矮人/海盗脚本、游戏回合与伪随机转移。 | 在 observation 与合法命令约束内安排动作序列，利用现成物品状态和因果链达成目标；需要以实际 adapter 和回放验证。 | 对人物承诺、互惠关系、信任变化、事件归因、原因理解、目标冲突与持续主观意图的叙事。当前不能通过加几个 flag 或把敌对脚本改名为 intent 来声称已实现。若 LLM 提议新增机制，那属于规则/内容扩展建议；批准、实现并以新版本验证之前不能在固定 1.22 中作为已存在能力执行。 |

## 后续候选（局部官方来源核验，未运行/非当前阶段）

若后续问题必须涉及 NPC 社会关系，可把 [Cataclysm: Dark Days Ahead 官方 NPC 文档](https://github.com/CleverRaven/Cataclysm-DDA/blob/master/doc/JSON/NPCs.md#opinion-changes) 与 [任务成功/失败源码](https://github.com/CleverRaven/Cataclysm-DDA/blob/master/src/npctalk_funcs.cpp#L2396-L2459)列为下一项**只读候选审计**。父代理于 2026-10-14 核读了这两份官方页面：文档明确 opinion 中 trust/value/fear/anger 被后续劝说、命令与敌意规则消费；`mission_success` 增加 value、降低 anger，`mission_failure` 降低 trust/value、增加 anger。它是 tile-based roguelike/生存模拟，不是纯文本冒险，观察与动作载体明显不同；其 `master` 未固定 commit，页面快照可能随时间变化。本轮没有下载、构建、运行，也未确认它是否保存和消费足以支持“丰富事件历史”的记忆。因此这是有原生状态读写依据的候选，不是已证明满足本项目研究要求的替代游戏。
