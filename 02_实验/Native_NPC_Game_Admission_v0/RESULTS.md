# Mature Native NPC Game Admission v0 — RESULTS

日期：2026-10-15。P0 状态：**DOCUMENTARY_ADMISSION / READY_FOR_INDEPENDENT_REVIEW**。P0 只完成文献/源码层准入审查；**当前环境没有获准入 P1 的游戏（NO_GO_THIS_ENVIRONMENT）**。P1 `NOT_RUN`；P2 未定义；P3–P5 未启动。没有新增游戏 AI、模拟器或适配器，没有下载安装、启动游戏或新模型调用。

起始代码检查点：feature branch `codex/open-adventure-online-20261014`，HEAD `f6be3d0a5e08e61148c48959e780cdd66a4aee07`；不是本报告提交后的 HEAD。网络恢复后 fresh-fetch 已确认远端 `webgpt-sync` 仍为该提交。应用目录、默认 Steam 安装库及项目外部游戏目录未发现三候选安装；这不证明其他设备或路径不存在安装，也不推断 Sims 的账号许可。公开报告不包含 Steam 原配置、账号信息或其他游戏清单。工作树原有更改未触碰。该报告不改写既有实验结果。

环境核查：Mac `arm64`，macOS `27.0.1`；没有候选游戏在 PATH 上，也未发现项目内可复用安装。RimWorld 的缺失另经用户直接确认。CDDA 的可用 arm64 发布资产、依赖及固定 tag 许可正文尚未完成核验；未下载、构建或安装。商业游戏许可、DLC 与模组政策不能由“能找到下载链接”代替。上述均为当前检查范围，不是全盘穷尽。

## 准入比较

证据等级：`OFFICIAL-DOC` 为官方页面描述；`SOURCE` 为指定版本源码审读；`RUNTIME` 为本机实际运行。三款本轮均 `RUNTIME: NOT_RUN`。官方描述不证明当前安装版本行为；源码命中不证明存档中的运行行为。

| 候选 / 本轮判读 | A 原生行为 | B producer → persistence → consumer | C 接入 |
|---|---|---|---|
| **RimWorld：优先调查候选，未选定运行版本** | `OFFICIAL-DOC`：游戏官网描述需求/心情、个人背景影响可做事项、角色 opinion 影响恋爱/婚姻/争斗、环境经历影响心情。不是当前 build 的运行轨迹。 | 当前仅有官方机制概述；未核对商业源码中的具体状态生产、存档保存及行为消费者链。 | 用户确认本机没有 RimWorld。官方博客称截至 2026-10-12 主线为 1.6、1.7 为 unstable；无法据此确定本机可取得/授权的 build。C# 模组仅为接口候选；只读 API、玩家等价控制、存档/RNG恢复均未验证。`NO_GO_THIS_ENVIRONMENT`。 |
| **The Sims 4：有限机制线索，未选** | `OFFICIAL-DOC`：Growing Together 下，负面互动/打斗可能提供 Distant 选项，不保证出现或自动获得；`awful compatibility` 与 `Difficult/Distant` 会影响自主互动。 | 官方更新说明描述 relationship-scored follow-up 在 `directutility <= 0` 时跳过，自主路径与玩家直接指令有别；但本机存档持久化、日志/API 及 producer→consumer 链均未测。 | 2026-09-22 官方更新页版本 `1.128.90.1230` 是已审来源版本，不是本机安装或当前最新版。DLC 未确认。EA Mods Policy 是分发规范，不是 runtime API 或逆向许可。`NOT_ADMITTED`。 |
| **Cataclysm: Dark Days Ahead：LIMITED_SOURCE_FIT；本轮不选** | `SOURCE`：固定 tag `0.I-1` 可见需求响应、寻物、危险应对及失窃反应；非盟友 NPC 的睡眠存在简化。不是无导演运行证据。 | `savegame_json.cpp` 保存 `attitude/op_of_u`；`known_stolen_item` 的持久化未证。普通活动 AI 受加载范围限制，不能推出所有离屏角色都停止演化。`opinion` 主要描述对玩家的看法，不足以证明通用 NPC-NPC 社会史。 | 官方编译说明有 Mac/ncurses/tiles 路线，未实测构建。许可正文与 Mac 发布资产未核完，未进入 P1。回合制可用合法 wait 推进；未测试自动提交，不能因此说 NPC 不自主。 |

RimWorld 官方来源：[官网](https://rimworldgame.com/)；[Ludeon 2026-10-12 公告](https://ludeon.com/blog/2026/10/announcing-the-waylith-engine-and-update-1-7/)（分支说明亦在成功读取的[官方博客](https://ludeon.com/blog/)正文；单篇直连未成功）。Sims 来源：[EA 2026-09-22 更新](https://www.ea.com/games/the-sims/the-sims-4/news/update-9-22-2026)；[EA Mods Policy](https://help.ea.com/en/articles/the-sims/the-sims-4/mods-policy/)。CDDA 版本锚为[官方 0.I-1 发布页](https://github.com/CleverRaven/Cataclysm-DDA/releases/tag/0.I-1)、短提交 `7b2efa5`；仅为源码版本，不是已安装游戏的二进制哈希。

### CDDA 固定源码的具体因果链

| 步骤 | 源码定位与成立范围 |
|---|---|
| 产生状态 | [npcmove.cpp:1872](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/src/npcmove.cpp#L1872)：`witness_thievery()` 记录 `known_stolen_item`，普通分支将态度改成 `NPCATT_RECOVER_GOODS`；商店管理员有提前返回例外。 |
| 保存状态 | [savegame_json.cpp:2129](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/src/savegame_json.cpp#L2129)：NPC store 保存 attitude 等字段，load 也读取；未证实该被盗物指针跨存档保留。 |
| 消费状态 | [npcmove.cpp:2466](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/src/npcmove.cpp#L2466)：`address_player()` 在该态度及可见等条件下选择接近/跟随/交谈。是源码因果链，不是实测恢复后的记忆链。 |
| 适用边界 | [npcmove.cpp:2407](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/src/npcmove.cpp#L2407)：需求可触发消费；2447 的非盟友困倦分支清零 sleepiness。[game.cpp:1214](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/src/game.cpp#L1214)加载邻近 NPC、1292 卸载；专门离屏任务另论。 |

域语义：[NPCs.md](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/doc/JSON/NPCs.md)；[MISSIONS_JSON.md](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/doc/JSON/MISSIONS_JSON.md)。后者的 `MGOAL_TALK_TO_NPC` 等是玩家任务里程碑，不可当作 NPC 自主作者目标。环境入口：[官方编译说明](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/doc/c%2B%2B/COMPILING.md)；[许可文件定位（正文未成功读取）](https://github.com/CleverRaven/Cataclysm-DDA/blob/0.I-1/LICENSE.txt)。没有以源码可编译或 `cata_test` 替代原生游戏基线。

## 候选节点与不可绑定反例

- 可支持、待运行验证的节点候选：在确认 Growing Together DLC、固定游戏 build 与存档后，观察一次原生负面互动是否使关系界面出现 Distant 选项，以及之后自主社交选择是否改变。获得选项非保证；不能提前记作 PASS，也不能用玩家直接选择冒充自主变化。
- `UNSUPPORTED_AT_CURRENT_BINDING`：要求“A、B 在两天内真正原谅彼此”，但没有将“原谅”绑定为该游戏已定义的状态、原生事件或经过核验的识别规则。不得凭好感度或文本代判满足。这是当前绑定未支持，不是证明三款游戏均不存在相关机制；如果还要求撤销已发生历史，则另与本项目未来修复权限冲突。
- P0 不要求先证明作者节点有两条路线才准入 P1。多因果路线尚未确认是 P2/P3 场景缺口，不是将 CDDA 全局判为不支持的理由。

## 旧模块复用图

| 代码入口 | 可复用职责 | 搬迁条件 / 不可搬迁假设 |
|---|---|---|
| `tools/npc_system_v0/system.py`: `actor_decision`, `System.actor_step/world_proposal`; `executor.py`: `start`, `_finish`, `advance_minute` | 决策/预测与真实执行分层、校验后才结算、失败与证据区分。 | 其 key/ledger/toy world、单一 actor 状态 schema、手造心理响应与小域规划器是开发样机内容；不能作为外部游戏 API 或原生 AI。 |
| `tools/native_platform_v0/p3/agency.py`: `observe_actor`, `choose_goal`, `make_decision`, `_dispatch_pending`, `_settle_pending`, `step_actor` | 合法 actor-local 观察、pending action 身份、世界验证与 receipt-based settlement 的职责模式。 | 代码直接依赖 Evennia ObjectDB、attrs、rooms/exits/inventory、命令及 P3 角色/任务绑定。跨游戏须重新定义原生观察和合法执行接缝，不能拷贝实体/任务词表。 |
| `tools/native_platform_v0/p3/p4_world.py`: `clock_for_actor`, `advance_clock`, `append_event`; `p3/control_service.py`: `step_world`, `observe_actor`, `get_trace` | 单一时钟 owner、事件序号、actor 只读时钟、外部控制面与状态导出的接口分工。 | 这是 Evennia P4/P5 的 simulated-minute。不能假定等于目标游戏 tick、调用周期或现实时间；自动 wait 是否可作原生时间接口尚未测试。 |
| `tools/native_platform_v0/p5/ongoing_station/{actor.py,goals.py,native.py,controller.py}` | commitment 生命周期、future-only/CAS 编辑、source constraint 与 grant provenance、提案不等于执行。 | 站点的维修/储存/借还、角色别名、实体 ID、repair-before-storage 及派发规则均为手写域内容。P5 12 场 11/12 结构审计通过且保留 1 个 shared-supply 失败；不是通用 NPC 策略。 |
| `tools/author_obligation_planning_v0/{contracts.py,search.py,native.py}` | 严格版本化约束、真实事件与预测分离、原生 receipt 后推进历史义务、有限预算失败保留。 | 仅适配 Open Adventure 手工 B0 状态、算子差分与 bridge 事件词表。作者要求与 planner 依赖是不同对象；在新游戏必须由实际语义 owner 绑定，不能把搜索前提当作者约束，亦不能把作者文本自动当游戏能力。 |

跨游戏共通入口只能先定为 adapter responsibilities：游戏拥有的状态/时钟、合法角色观察、原生状态 producer、持久化、后续 consumer、授权操作、真实结算回执和规则版本。需逐项证实，不能直接复用旧 schema。保存日志不证明历史影响行为；需找到后续规则读取者。相同 seed、重开和加载同一存档也不等价；除非检查点包含并验证完整状态、RNG 游标、规则版本与未来输入，否则不宣称重放确定。

## 八项交付问题

1. **最终游戏？**没有。RimWorld 仍是用户优先调查候选，但缺本机安装、固定运行版本和原生 producer/persist/consumer 实证，不能称已选定主实验游戏。
2. **无作者时 NPC 如何活动？**尚未实际运行任何候选；RimWorld 为官方机制描述，CDDA 为固定源码路径，不是 runtime 观察。
3. **哪些持久状态影响未来行为？**没有运行层端到端证明。CDDA 的 attitude 有生产、序列化和消费者源码，具体被盗物指针的跨存档保存未闭合；Sims/RimWorld 仍只有官方机制描述，不能升级为本机实证。
4. **合法外部干预？**候选模组/命令面未被本机验证。不得把直写关系值、隐藏状态或玩家直控当作 NPC 自主行为。
5. **多路线作者场景？**未设计/未验证；P0 不以路线数作 P1 准入门槛，留给观察原生能力后的 P2。
6. **运行到哪？**仅 P0 documentary admission；所有候选 runtime `NOT_RUN`，P1 `NOT_RUN`。
7. **最小下一步？**仅在另行确认授权安装与固定版本后，建立无导演只读基线：固定版本/规则与合法来源、原生存档哈希、角色稳定 ID、原生时钟/事件、已授权的 actor-visible 状态、动作/结算回执及 producer→persist→consumer 对照；记录只读轨迹与原生存档读回。尚不写规划器、导演或玩法。
8. **复用边界？**复用职责分离和审计契约；Evennia、Open Adventure 与 toy-domain 适配器、时钟、状态和动作语义保留在旧域，不强行搬迁。

## P1 停止标准与本轮边界

当前 `NO_GO_THIS_ENVIRONMENT` 的具体含义：没有一款同时通过授权/安装、固定实际 build、可合法只读取证与稳定身份、原生存档/时间语义检查的候选。用户确认无 RimWorld 安装；Sims 实际安装及 DLC 未确认；CDDA 仅审读源码，Mac build、许可和实机行为未验证。此状态不是三款游戏的全球 NO-GO。

若未来条件满足，P1 的最薄只读面应包括 `game/version/mods + save hash`、native clock、stable actor IDs、授权 observation/events/action receipt 的只读快照、存档读回，以及每个被声称影响行为的状态 producer→persistence→consumer 引用。读接口若推进世界，必须把推进操作和采样间隔明确记录；不能把观察动作隐藏成控制。seed/reload 可复现性单独标注并实测，不作为假设。

停止或降级相应主张的条件：无合法访问/许可，或需要改 AI/社交规则、注入作者目标才能得到声称的原生行为时，不启动该 P1；固定 build、状态来源或信息权限无法核实时，不进入规划控制。仅缺某个事件回执、持久字段消费者或精确重放时，可保留有限观察，但对应主张必须为 `UNKNOWN/UNVERIFIED`，不要求把整个 P1 都刷成 PASS 才保留轨迹，也不去 Evennia 造替代驿站。

验证与发布：本轮仅文档/源码核查及文件检查，**无新 native run**；文档检查不代表新游戏测试或 CI 通过。Git 原配置指向失效旧端口，直连也失败；用户告知改用 ZodAccess 后，按系统代理信息使用单次命令覆盖，fresh-fetch 成功，未修改全局代理。公开内容仅该报告与导航/任务状态，提交后的推送/CI 以远端实际记录为准。原始对话私有归档，不提交游戏源码、资产、商业程序集或账号资料。旧 C++、E0、main、历史实验与原有脏文件不动。

本地检查：`git diff --check` 通过；5 处新增准入入口链接可解析，引用的本地适配器路径存在；原文与可恢复副本 SHA-256 一致且 `_private/` 被 Git 忽略。`tools/repo_health_check.py --top 3` 正常结束并报告 5 项警告（3 个本地依赖大文件、TODO 体积、1 组既有原文重复），不据此声称源码机制或新游戏测试通过。父级独立复读修正了三处 CDDA 来源路径、状态持久化表述和“未验证不等于不支持”的准入边界。
