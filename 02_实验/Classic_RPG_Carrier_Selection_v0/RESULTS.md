# Classic RPG Research Carrier Selection v0｜P0

## 当前裁决：可复用行为与 OpenXRay 控制交接源码审查

2026-10-16 后续授权；项目基线 `551bc6e525cb84c7dbf16e184b202efdd87fbb06`。**SOURCE_REVIEW_DELIVERED / PARTIAL / READY_FOR_INDEPENDENT_REVIEW，未 CLOSED；NATIVE_RUN = NOT_RUN。**用户已确认**没有合法 Call of Pripyat 数据，先完成源码审查**。本轮据此停止于源码与原版实例待核，不安装、运行或开发适配器，不用替代关卡补空项。

**选材准则已修正：原游戏应提供可复用行为、前提和真实效果；角色/作者 Planner 负责组织新的行动过程。不要求游戏预先编好完整因果剧情。**Exult 的服务链仍是真实机制证据，但不足以决定研究首选；其工程优先级撤回。当前优先技术调查对象是 **Call of Pripyat 1.6.02 + OpenXRay**，**RimWorld 仅保留强备选**，不是第二个已启动的审查。下面旧三候选分数不用于本轮新排名，也不把其他游戏判为不适合研究。

本轮只做最终任务的三件事：查控制链、查目标接管/交还、核实是否具备原版实例材料。附件中的论文载体表、Radiant AI 考据及其他新增游戏只是讨论背景，未在本轮重新逐篇核验，不当作已核事实或继续扩大调查清单。两名 Luna 分查源码，父级复核关键 getter、operator 切换、smart-terrain移动与脚本依赖；这些是代理内部复读，不是外部独立验收。

### A. 固定版本、许可与材料

上游固定为 [OpenXRay/xray-16 `c62d9d343981d50f6ed176412b85d94c61b578b5`](https://github.com/OpenXRay/xray-16/tree/c62d9d343981d50f6ed176412b85d94c61b578b5)，本轮读取的 `dev` HEAD，**不是稳定发行版**。官网称支持 **CoP 1.6.02**，不支持 Legends of the Zone/Enhanced Edition；本轮不混 Anomaly、Call of Chernobyl 或其他Mod内容。项目称支持macOS及ARM64，不等于已验证当前Mac上的这个组合；开发分支也可能损坏。[R1–R2](SOURCE_INDEX.md#openxray)

`License.txt`将 OpenXRay 的修改/新增代码列为MIT，同时说明引擎衍生于GSC原引擎并要求遵循GSC EULA/内容指南；**不能将整个游戏、原始引擎与商业数据统称纯MIT**。本轮只读公开源码；少量副本在项目被Git忽略的 `_local_data/external_games/openxray_control_review_20261016/`，不发布代码副本、游戏资产或私人原文。[R1]

### B. 实际控制链：不是一条可以随意改写的“总任务队列”

| 层 / 已核路径 | 谁决定什么 | 外部角色规划的边界 |
|---|---|---|
| ALife更新：`CALifeUpdateManager::update → update_switch / update_scheduled` | 遍历对象在线/离线切换与scheduled registry，不在该函数里选择剧情目标。[R3] | 不能把控制全局ALife更新器当作“给某NPC一个任务”。 |
| Smart-terrain任务：`CStalkerPropertyEvaluatorSmartTerrainTask::evaluate` | 从ALife registry找对应server实体，调用`brain().select_task()`后检查`m_smart_terrain_id`。基类实现已分配terrain时直接返回；无分配、允许选任务且到选择间隔时，才按enabled/suitable选terrain并register NPC。**此evaluator可能触发任务选择，不是纯只读测量。**[R4,R13] | 不能说每次evaluate都会重派；但改一个位置或布尔值仍不等于取得任务控制权。 |
| 任务位置：`CALifeSmartTerrainTask` | 从patrol point解析game vertex、level vertex与position；它不是完整派工器。[R5] | 已有导航能力可复用，不应把此类误称自主任务生成。 |
| NPC顶层：`CStalkerPlanner::setup/add_evaluators/add_actions` | 默认目标为内部`PuzzleSolved=true`；根据Alive、Enemy、Danger、Anomaly、Items等条件选择死亡、ALife、战斗、避险、异常区子规划器或拾取动作。[R6] | 内部`PuzzleSolved`不是作者剧情完成证据。交给这个内置求解器的目标必须绑定其可解释条件，不能直接塞自由文本；不要求外部高层语义全部变为原生变量。 |
| ALife子规划器 | 区分无ALife、smart-terrain任务，以及无smart任务时的`SolveZonePuzzle`动作；后者常规实现仅设移动/姿态/武器等，本轮未核到实际解谜结算。operator效果是搜索模型声明，不是已经改变世界。[R4,R7] | **候选接入点是既有ALife/task选择边界**，保留顶层危险/战斗门控；具体原版脚本接缝尚未准入。 |
| Native任务执行：`CStalkerActionSmartTerrain::execute` | 每次重新从server实体brain取得task，再写game/level path和目标位置；不可达时可请求最近可达位置，缺task有断言。[R7] | 仅从外部调用movement setter，可能被这个仍在执行的动作后续覆盖。setter不是任务层接管。 |
| 实际结算 | 原生事件消费者及库存/移动等系统决定世界是否改变；搜索effect、发事件、到达意图都不是成功回执。[R8] | 保留原规则，不为了作者要求补虚假交付、改库存或瞬移。 |

### C. 可复用动作与真实效果：已具体核到什么

**拾取不依赖某条专用剧情，但仍有条件与对象选择限制。**`GatherItems`的符号前提为Alive且无Enemy/Anomaly/Danger并有Items，效果声明为Items=false。实际Items evaluator读取的是该NPC的`memory().item().selected()`，**不是全地图有物品就可任取**。[R4,R6]

`CStalkerActionGatherItems::execute`使用已选物品的level vertex/位置设置移动和视线；初始化里对特定ignored-touch状态会生成take event。`generate_take_event`发出`GE_OWNERSHIP_TAKE`后，`CAI_Stalker::OnEvent`还会找实际对象并检查`inventory().CanTakeItem`：通过才更新parent、`inventory().Take`及后续处理，拒绝则发ownership reject。[R8] **这是“现成选择条件→原生执行意图→原生校验/结算”的机制证据，不是某位CoP实名NPC已实测拾取。**NPC不再选中物品也不自动证明该物品已由它取得。

**原生事件接口也不是任意动作的合法授权：**本轮没有审完`CanTakeItem`内部所有条件，不能推定它重查距离、视线、所有权等全部前提。后续必须走原生选择/接近/触发路径；不能由外部随意伪发ownership事件，绕过过程后再称角色合法完成。这与“函数名叫GiveItem并不保证真的面对面交付”是同一审查原则。

可组织空间因此不是零：上层可以尝试组织已有任务位置、移动、感知支持的拾取以及原生危险/战斗反应；但下列能力本轮**未证实**：任意物品的参数化拾取、NPC间交易/交涉、任意角色代做玩家任务、不同故事方案的可达性、通用关系/承诺变化。没有为了补齐它们新增动作。

### D. 接管与交还：源码回答到哪一步

**取得live NPC planner的Lua路径确实存在**，并非只有可构造的泛接口：[R9]

`npc:motivation_action_manager()` → `script_action_planner` → 对对象进行`CAI_Stalker`类型检查 → 返回`&manager->brain()`；再经`set_goal_world_state`包装调用`set_target_state`。非Stalker对象走错误/空指针路径，不能扩大为全部游戏对象通用控制。

这只证明**进程内脚本可触及现有NPC规划器**。本轮未确认现成外部RPC、认证请求、异步回执协议或安全的目标租约。`add_action`是注册operator，`setup`会绑定/重置规划器，不是“无损获得一次目标控制权”。**随意改root目标可能改变原有战斗/危险行为选择，当前不建议直接这样接管。**也不通过删除安全前提或换成常真evaluator刷成功。

| 情况 | 固定源码能确认的行为 | 仍不能确认的部分 |
|---|---|---|
| 改目标后新解首operator不变 | 下一次update/solve后继续execute原operator，不重新initialize。[R10] | 同一operator内部如何接受新任务参数、旧进度是否有效，要看具体动作。 |
| 新解首operator变化 | finalize旧operator → 更新current id → initialize新operator → execute。[R10] | 这不是自动暂停栈；没有证据证明原巡逻进度被保存、之后会精确续跑。 |
| 交回ALife且terrain分配仍在 | `select_task`不会因再次调用就重新选terrain；原生task动作会重新向当前terrain取得task。[R7,R13] | 保留terrain ID不代表保留某个scheme/巡逻的精确进度；原task是否仍有效、由谁撤销仍受内容与生命周期影响。 |
| 无合法解 | 可见内部失败/日志与`THROW(!solution().empty())`，另有空解return分支；没有正常的typed拒绝/失败回执接口。[R10] | 具体build断言处理和游戏表现未运行验证；不能称“自动回原任务”或完整不可达证明。 |
| 切换逻辑scheme | 上游随附`xr_logic.script`会deactivate旧scheme、更新section并激活新scheme；其save/load保存section/配置与scheme自定义数据。[R11] | 保存section不等于保存任意动作精确进度；随附脚本也不等于商业原版该NPC实际配置。 |
| 切离线/再上线 | switch manager的路径涉及server对象、销毁/重建在线表示、子物件过滤与ID处理；并非同一个live planner对象一直逐帧运行。[R3] | 原任务、临时目标、观察记忆及当前动作跨切换怎样恢复，不能仅凭此manager断言。 |

还需分清：`reset_action_queue`清的是`CScriptEntity`的脚本动作队列，**不是**上表GOAP求解器的operator序列。[R12] 不把clear、reset queue或setup当作安全的“归还控制”方案。

**当前建议只是可检验接缝，不是已实现设计：**优先核实际NPC的ALife/task提供者与脚本scheme如何协调，用它组织原生动作；保留顶层紧急反应。目标失败/撤回后应重新验证原生任务是否仍合法，再由原机制继续选择，不能保证回到原路径。是否确有一个足够薄的入口仍为 `HANDOFF_NOT_ADMITTED`，暂不施工。

### E. 观察与原版数据缺口

`memory_visible_objects / memory_sound_objects / memory_hit_objects`给出了主体感知缓存入口；ALife全局registry、smart-terrain分配和对象组织元数据则是诊断世界信息。缓存本身也可能含过时对象，不能把它直接包装成已验证的角色O。对象销毁/重建后需重新解析身份，不长期保留裸指针。[R3,R12]

固定上游树**有**公开的`res/gamedata/scripts/xr_logic.script`，不能说脚本全缺；但其中调用`xr_gulag.get_npc_smart/getJob`，并依赖`xr_conditions`/`xr_effects`中的函数。固定树的scripts目录不含对应脚本，缺函数时有abort路径。这是本轮源码树的具体边界，**不是对完整商业安装包或原版游戏能力的否定**。[R11]

用户已明确无合法数据。常见Mac应用/Steam目录、appid41700 manifest、官方推荐的本地数据路径也未发现安装；该检查不是全盘搜索或所有权判断。本轮**没有确认具体原版NPC、活动地点、原始配置、可交互物件/存档**，也不以Squad名、类名或Mod示例填补。`CONTENT_INSTANCE = UNKNOWN`、`OBSERVATION_CONTROL_LOOP = NOT_RUN`，加载/推进/采样/重开/存档成本全部 `NOT_MEASURED`。

### F. 决定与停止点

本轮确实推进了源码准入：**native planner及live Lua getter有定位；原生拾取有实际校验/接受/拒绝路径；任务、movement、scheme、GOAP队列的边界被拆清。**它比“引擎有API”更具体，但不等于外部上层目标已经能安全接管或恢复。

保持 **OpenXRay为优先待准入对象，RimWorld为未启动备选**；不根据附件里未经本轮复核的排名宣称其他游戏落败。Exult旧证据保留，但不再因原版已有一条完整服务流程而优先开工。

**下一次原版验证首先缺的是合法CoP 1.6.02数据。**具备后仍须确认构建与实际接缝，只验证一个既有Stalker、一个现成动作：无外控基线 → 只读感知/状态 → 一次受限上层选择 → 原生成功或拒绝 → 解除选择后原任务重新评估，并在独立恢复/干扰运行中检查后果。先查原版实际scheme/task绑定；无法保留危险/战斗门控、只能改世界结果或必须重写原生动作，就停止该接入路线，记录原因后再决定是否转备选。当前用户仅授权源码审查，**不自动执行这项验证、不购买、不下载数据、不继续写Adapter。**

公开只提交本页增量、[来源索引](SOURCE_INDEX.md#openxray)与必要路由；原文私有归档，旧实验、C++、游戏规则与main不动。下面保留`551bc6e`的三候选历史调查，不把过去的条件性推荐伪写成从未发生。

## 历史快照：551bc6e 三候选 P0

以下为2026-10-16首轮调查，仓库基线`b326d55ba34541c1b0959eac2debfd48f4c44c81`。当时结论为PARTIAL、条件性首选Exult/备选OpenGothic；**该工程优先级已被上方当前裁决替代**，源码事实与未实跑记录保留。以下“下一阶段/P1”是当时方案，不是当前授权。

## 1. 问题、方法与边界

选的是已有内容的研究世界：角色 Planner 在无作者任务时组织自身行动；作者加入未来要求后组织既有因果过程；玩家扰动后保留真实过去、修改未来。不是选最容易接 Python 的空引擎，也不要求游戏预先拥有通用心理状态或跨轮记忆。角色记忆可以外置，但执行后果不能伪造。

只审查以下三项，不展开第四项：Black Gate + Exult、Night of the Raven（NotR）+ OpenGothic、2006 PC 原版 Oblivion。CoffeeMud / Morrowind / OpenMW 仅保留背景备选，不作本轮调查。未开发适配器、Planner、MCP、新玩法或 LLM 链路；未购买或下载商业游戏数据。三名 Luna 分查材料，父代理复核固定源码中的首选因果链、版本与覆盖风险；这不是外部独立验收。

证据等级：`NATIVE_RUN` 实际运行；`SOURCE_VERIFIED` 固定源码及生产/消费路径；`DOC_SUPPORTED` 官方/直接项目文档；`COMMUNITY_REPORT` 社区资料；`INFERENCE` 本轮判断；`UNKNOWN` 尚不能确认。**函数存在、商业原版内容采用该函数、重实现行为等同原版、实际可运行，是四个不同判断。**下文来源编号及精确位置见唯一附属 [SOURCE_INDEX](SOURCE_INDEX.md)；没有以搜索未命中证明功能不存在。

## 2. 固定候选与原生/新增能力分账

| 候选 | 本轮固定范围与来源 | 已有游戏内容 / 本轮不算已有的东西 |
|---|---|---|
| Black Gate + Exult | Exult `v1.12.1`，`cacb4f584901dab59ff288c750d3622d3378435b`；开源引擎，商业 BG 数据另需合法取得。[X1–X6](SOURCE_INDEX.md#exult) | BG 的地图、NPC、Usecode/任务与 Exult 的引擎重实现分账。固定版源码中的日程和对象交互可核查；不把 SI、Keyring Mod、master 的改进算 BG 稳定版能力。外部角色观察过滤、请求/结果协议未实现。 |
| NotR + OpenGothic | `v0.92`，tag object `e88c93dcdf0647b101061baf84203db94f0a5c67`，解引用提交 `2855fa51957bac9e7ce83f938ec127a0ab3badce`。[G1–G4](SOURCE_INDEX.md#opengothic) | 原版 Daedalus 内容与开放重实现分账；项目称实现大部分脚本接口，不等于全部 ZenGin 行为。原版脚本未取得，未下载第三方反编译包；未把 Returning、Union 或其他 Mod 算原版内容。外部通信/观察投影仍是未来适配。 |
| Oblivion（2006） | PC 原版 `1.2.0.416` 为后续核查目标，实际安装/ESM 哈希未取得；OBSE 官方 v21 支持该版本的 Steam/GOG 发行。[O1–O3](SOURCE_INDEX.md#oblivion) | 原生 AI packages、原版任务，与 OBSE 扩展和研究者另造 HTN/交易脚本分账。非 Remastered、非 Skyblivion。闭源原版数据/插件未检查；不能给出已核的具体 NPC FormID 或包记录。 |

### 行为能力：不是动作名计数

| 行为及后果 | Exult 固定源码 | OpenGothic / 原版内容证据 | Oblivion 原版 / 扩展证据 |
|---|---|---|---|
| 日程、移动、打断 | `update_schedule` 选时段日程；切换日程可终止旧 action。`SOURCE_VERIFIED` [X4] | 维护者解释 routine、waypoint、perception、遇敌转攻击后回日程；具体原版示例为 Xardas。`DOC_SUPPORTED` [G3] | packages 与重评接口有文档；包优先级/任务脚本可能覆盖请求，实际 NPC 未验证。`DOC_SUPPORTED` [O2] |
| 使用设施、取放/消费 | 服务员放食物→食客读取/移除物件，见 §3；不是仅播放动画。`SOURCE_VERIFIED` [X2] | `AI_UseMob` 等有项目文档，但不据 API 名推定所有 NPC 都具备生产/交易能力。`DOC_SUPPORTED` [G2] | 不能将玩家的交易/任务接口自动授予 NPC；原版具体物品因果链缺 ESM/运行验证。`UNKNOWN` |
| 战斗、实体影响、持续状态 | 本轮重点不是战斗；actor 序列化含生命、日程、持物，不能据此宣称每种工作进度都保存。`SOURCE_VERIFIED` [X5] | 固定源码含HP→死亡→附近尸体筛选消费者、NPC/AI队列保存；原版仪式具体脚本未核。`SOURCE_VERIFIED`（重实现）[G6] | 原版任务场景有社区记录；原版包、任务旗标及脚本之间的实际消费关系未检查。[O4] |
| 社会/任务变化 | BG 对话/Usecode 有文档与实名内容锚点，不等于自主 NPC 可自由调用全部剧情对话。[X6–X8] | 仪式已有多角色条件；是作者预写剧情，不是任意协商。部分 memory/news API 标未实现。[G2,G5] | 原版任务能串联 NPC 行动，但 Bob/Fred/Stan 交易示例属于论文扩充，不是原版经济链。[O4–O5] |

## 3. 首选的实际源码因果链与反证

**Exult 重实现机制级 `SOURCE_VERIFIED`：**

1. `Waiter_schedule::find_customer()` 查找周围 actors，只接收 `Schedule::eat_at_inn` 的食客。它确实依赖另一 NPC 的日程，不是单人循环动画。[固定源码 3420–3438](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/schedule.cc#L3420-L3438)
2. 服务员状态机进入备餐、走向客户、服务；`serve_food` 从左手取 shape 377，从 NPC 持物中移除，并 `move(spot)` 到客户可服务位置。这里产生真实地图物件状态。[3788–3914](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/schedule.cc#L3788-L3914)
3. 食客的 `Eat_at_inn_schedule::now_what()` 搜索附近 shape 377；找到时按随机分支移除食物，无食物时走另一反馈分支。服务结果由另一原生逻辑消费。[803–843](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/schedule.cc#L803-L843)

**这条链支持什么：**引擎中存在可观察的跨 NPC / 对象依赖；外部目标可尝试组织既有服务与消费，而不必先写一套吃饭规则。**不支持什么：**尚未将它对应到 BG 商业数据里的某两个实名 NPC、地点、时段；没有运行证明二者实际相遇。shape/frame 不是持久唯一物件 ID。不能假定随机分支按固定时限必定消费。

两个重要反证改变了选型判断：

- `Ready_food()` 有库存时取已有食物，**没有库存时直接创建 temporary 食物**，还清除 `okay_to_take`。因此该链不是守恒的生产/库存经济；不能据此设计“饥荒迫使厨师采购”的原生实验，也不能未经验证就假设玩家能直接拿走服务食物。[3622–3653](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/schedule.cc#L3622-L3653)
- `tend_shop` 在固定版 dispatch 中实际实例化 `Loiter_schedule`。**职业标签不等于通用自主交易**；交易是否由原版 Usecode、玩家交互或其他规则完成需单核。[actors.cc 1843–1845](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/actors.cc#L1843-L1845)

保存也不能用一句“有存档”带过：`Actor::write` 保存日程类型、位置相关字段、food_level 与持物；IREG 保存对象及 temporary 标记；这证明序列化路径存在，不证明任意工作中间态、RNG 或两个 schedule 的当前阶段可以精确续跑。[X5] `Npc_actor::paint` 还有 dormant NPC 恢复入时间队列的逻辑；至少不能假设全地图所有 NPC 始终与可见 NPC 等精度逐步模拟。[actors.cc 5321–5332](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/actors.cc#L5321-L5332)

**备选也有真实机制链，不能只列API名：**OpenGothic固定源码中，AI队列优先于routine；伤害改变HP后由`checkHealth/onNoHealth`切至死亡态并清队列；`updateNearestBody`随后筛选`isDead()`且能感知的NPC。`saveAiState/loadAiState`保存和读取state、routine与队列。[G6] 这说明另一角色的实体状态能进入感知消费路径；但不能把“看到尸体”再推成原版某NPC必然举报、复仇或改变任务，也未验证Xardas仪式现场会触发哪种后果。首选偏向非战斗活动/共享物件的证据链，而不是认为备选只有漫游。

## 4. 真实原版场景候选：每款最多两个

以下 C 是**待验证的新作者要求**，不是已经支持的任务、也不是本轮实验。未知能力不会因写进作者目标便成为原生规则。

### Exult / Black Gate

**X-S1：Britain 的 Blue Boar，Lucy + Jeanette，共享酒馆/食物服务。**实名、职业和地点来自社区内容锚点 [X8]；本轮只读到检索摘要，页面正文返回 403/406，故不升级为原版脚本核验。

- A 原本：社区记录 Lucy 经营酒馆、Jeanette 为雇员；具体每人日程、食客身份及服务窗口 **UNKNOWN**。不能把 Jeanette 自动认定为固定源码里的 waiter。
- B 已有：§3 证实的是引擎服务/消费机制，不是这两个实例的分配。原版对话/售卖与 NPC 自主服务要分别核。
- C 新作者要求候选：在现有用餐窗口内，让原版已有服务者在期限前为一位已有食客完成一次服务且被实际消费；作者只定期限/先后，不给全过程。**尚不可绑定到上述实名对象，当前不编译、不声称可达。**
- D 路径可能性：服务机制允许使用已有库存或生成临时食物；这两条是实现分支，不是已经证明的两种故事方案。只有实际 NPC/设施/日程相容时，安排到达或等待服务才可能成为规划变量。
- E 扰动候选：改变玩家自身位置/交谈时机或合法改变可移动物件位置；是否影响通路、服务点与恢复必须实际确认，不能假设食物可拿。
- F 缺口：实名 schedule 映射、日程覆盖、可拿物件及拒绝原因、离屏推进、稳定对象 ID 均未完整核实。该场景是 P1 寻找实例的线索，不作机制组合性已过关的证据。

**X-S2：Trinsic 谋杀调查，Finnigan + Iolo + Petre，共享马厩事件。**原版参考卡介绍开场人物与调查，属于 `DOC_SUPPORTED` 的原版内容锚点 [X7]。

- A 原本：预写谋杀开场，Iolo 随行、Finnigan 要求调查，Petre 与现场有关。
- B 已有：对话、队伍随行与场景线索；不是服务员/食客链，也不是这些 NPC 自主开展调查的证据。
- C 候选新要求：为既有调查交互增加次序或期限；具体可调用的交互与证据字段未核，不把“NPC 自主破案”写成已支持。
- D 当前只能确认作者预写剧情；不同因果解法 **UNKNOWN**。
- E 玩家改变访问顺序/物品状态是否影响剧情、哪些旗标会绕过过程，待合法数据核验。
- F 该场景有身份锚点但组合性较弱，不因剧情丰富而优先进入 P1。

### OpenGothic / NotR

**G-S1：Circle of the Sun 的 Eye of Innos 修复，Xardas + Vatras + Pyrokar，兼有 Bennet 的修理。**维护者直接解释 Xardas 的 routine 切换/遇敌恢复 [G3]；三人协作、Bennet 修物与条件链来自明确针对 NotR 的社区攻略 [G5]，不是已核的原版脚本。

- A 原本：Xardas 换为 `RitualInnosEyeRepair` 日程，前往仪式 waypoint；遇怪转攻击，结束后回日程。社区描述 Vatras/Pyrokar 的参与条件、Bennet 修理及后续仪式。
- B 已有：routine、waynet、感知/战斗及 MOB 使用接口有项目文档；仪式与物品变化属预写内容。不能据此认为任意 NPC 能接替任意法师或修理匠。
- C 新作者要求候选：在不跳过角色原有参与条件的情况下，令已授权角色在某期限/顺序内到达并完成既有仪式。时间要求是新增约束，不应靠直接设置剧情完成旗标满足。
- D 路途受阻后的恢复、先解决不同参与条件，可能提供排序/路线选择；**是否有多个可执行因果方案未知**，并未证明能生成新仪式。
- E 维护者描述敌人打断与恢复；玩家引发战斗后，是否失去角色、物品/仪式条件能否保持，未运行核验。
- F 高层主要由商业脚本控制；原版任务被玩家推动，不等于 NPC 拥有玩家的任务对话权限。`Npc_ExchangeRoutine` 清旧日程，不能当无损暂停。部分记忆/新闻 API 未实现；补外部记忆不等于补全游戏原本未实现的结算。[G2]

### Oblivion（2006）

**O-S1：Anvil / Benirus Manor 的 Where Spirits Have Lease，Velwyn Benirus + Lorgren Benirus，共享庄园与任务。**2006 年写作、2008 年发布的社区攻略提供原版内容锚点，非 Remastered 攻略 [O4]。

- A 原本：玩家购买庄园、经历鬼魂事件、寻找 Velwyn，促使其回庄园处理封门，后续涉及 Lorgren。是任务条件驱动的预写链。
- B 已有：原生任务、对话及角色出行；OBSE 可观察/影响 packages，但未检查原版 MS02 数据、包条件和具体 FormID。[O2,O4]
- C 新要求候选：给 Velwyn 返程/开门过程增加到达期限或前置信息要求。**尚不能证明可由 NPC 而非玩家发起对应对话/任务操作**；当前不称可执行作者约束。
- D 原有旅程/条件排序可能可调；开门与解除诅咒仍可能只有预写触发路径，不是自由组合叙事证据。
- E 改变到达时机、敌人/路径条件可能影响执行；具体拒绝、死亡/essential 与恢复行为未核，不设计新资源规则。
- F 没有商业原版源码/ESM 验证；社区任务 walkthrough 不是包源码。研究论文中的 Bob/Fred/Stan 交易链使用研究者新增脚本与 flags，**不能算原版原生经济**。[O5]

## 5. 观察与行动路径：分别查，不用存档篡改代替执行

| 候选 | 观察路径（已有 → 缺口） | 行动路径（已有 → 缺口） |
|---|---|---|
| Exult | native actor/地图物件、时间 → actor/IREG 存档和 Usecode 查询/trace。NPC number 是身份候选；物件需另核持久身份，不能用坐标当身份。**外部实时、角色合法可见 O 与诊断全知 W 分离尚未实现。** | 外部请求 → **未来薄入口** → Usecode/schedule → native actor action → 地图物件变化→消费。改 schedule 有已文档化路径，但不是已有安全 RPC。不能把编辑器直接改物件/库存当原生行动；需明确一次请求的控制所有权与到期归还。[X3–X6] |
| OpenGothic | native NPC/脚本状态、时间 → 游戏内脚本/serializer → **外部导出待核**。`Hlp_GetInstanceID` 为实例身份入口，不保证临时对象/重载身份映射。脚本访问 W 不自动等于 NPC 合法知识。 | 外部请求 → **未来脚本/薄入口** → Daedalus AI queue/routine → native actor/MOB。已有 API 不是现成外部通信；routine、queue、perception 的清空/覆盖和结果回执须验证。[G2–G3] |
| Oblivion | native references / quest state → 原版脚本 + OBSE 查询/包事件/存读档事件 → **受控导出待核**。需区分 base Form 与持久 reference、加载顺序和临时引用；本轮未核实例。 | 外部请求 → **未来插件入口** → 原生 package / AI → 真实执行/包事件。OBSE 是扩展；包结束事件不必然等于作者目标完成。其文档警告改 base package 对活跃 actor 可能无效/不可预测，重评会影响当前行为。[O2] |

三者都需要：请求 ID、指定角色/权限/目标、观察来源、原生开始/拒绝/结束及状态读回，才能形成后续实验回执。**这些是未来适配需求，不是本轮新增系统能力。**不能把全局数据库读取供给角色、直接移动物品、设 quest stage 或改 save 当作角色已经做成了事情。接口若只能修改执行结果、无法调用既有动作，则不能准入。

## 6. 版本、合法数据与实验成本

| 项目 | Exult | OpenGothic | 原版 Oblivion |
|---|---|---|---|
| 法律/资产分界 | 引擎 GPL-2.0 文本；商业 BG 数据须自备，代码许可不授权资产传播。[X1,X6] | 引擎 MIT；商业 NotR 数据/脚本不随引擎提供。[G1] | 商业原版与 OBSE 许可分开；支持版本不等于获得游戏。加密 D2D 发行被 OBSE 明确排除。[O1,O3] |
| 当前 Mac 路线 | 项目有 macOS 发行/说明，固定版实际启动未测。[X1,X6] | 官方 README 有 Metal/macOS 构建路线；不能因老游戏便假设低成本。[G1] | 手册目标 Windows；本机兼容层/另一台合法 Windows 路线未测试，不默认购买/安装。[O3] |
| 保存/恢复 | actor 与物件存在序列化；临时物件/工作状态/RNG 是否精确恢复未测。[X5] | NPC/AI状态/队列/routine有序列化及加载源码；全局时钟/RNG和实机恢复未核。[G6] | 原版 save + OBSE save/load hooks 有文档；引用、插件顺序与包重评恢复未测。[O2,O3] |
| 离屏/时间 | 源码有 dormant 恢复；时间可读/速度可设≠全世界同精度加速；跨地图具体行为未知。[X3,X4,X6] | 项目修改过 far-NPC/time-skip 处理；本轮不声称逐步连续仿真，需逐 build 检查。[G4] | OBSE 可分 process level；不能将低级处理等同高精度连续模拟。[O2] |
| 自动化/暂停 | `--nomenu`、trace、游戏暂停配置不等于 headless step API。可控步进与无窗口能力 UNKNOWN。 | `-nomenu`、`-save` 不等于 headless；真实控制/采样循环 UNKNOWN。 | console 不等于认证控制服务；脚本事件不等于外部 runner；无人值守与确定性 UNKNOWN。 |
| 成本拆分 | 游戏加载/渲染、世界模拟、导出/控制、版本/恢复维护四项均 `NOT_MEASURED`。 | 同左；README 明确现代图形接口/硬件风险，不用画质或年代估 FPS。 | 同左；另有 Windows/扩展兼容成本，不能凭平台推断具体耗时。 |

本机只做目标路径存在性检查：arm64 macOS；常见应用、用户配置/支持目录、Exult 官方 `/Library/Application Support/Exult` 以及 Steam 默认 Gothic II/Oblivion 目录未找到候选安装。**这不证明用户没有许可证，也不是全磁盘资产清查。**本轮没有下载数据、反编译商业脚本、上传第三方源码或启动游戏。

后续要恢复“相同初态”，至少固定：游戏数据/build 与扩展清单、引擎 hash、独立配置、原生存档、章节/任务/时间、玩家/NPC位置、加载区域、已装插件与随机性策略；先比对恢复状态，再请求动作。只复制 save 不保证完全重演，不能先声称 deterministic。

## 7. 底线与加权评估

先判底线，评分不能冲掉硬失败。`CONDITIONAL` 是可指出路线但接缝未验证；`UNKNOWN` 是尚不足判断；不是 NO_GO 的同义词。

| 不可妥协底线 | Exult | OpenGothic | Oblivion |
|---|---|---|---|
| 具有原版完整游戏内容，不需自建玩法 | DOC_SUPPORTED，数据未取得 | DOC_SUPPORTED，数据未取得 | DOC_SUPPORTED，数据未取得 |
| 有角色 Planner 可组织的既有行为 | CONDITIONAL：机制链明确，实名分配待核 | CONDITIONAL：routine/AI脚本明确，原版后果链待核 | CONDITIONAL：packages明确，NPC可调用范围待核 |
| 可观察真实后果 | CONDITIONAL：对象/actor持久化可定位，实时出口待做 | CONDITIONAL：脚本/对象路径可指认，读回待核 | CONDITIONAL：脚本/OBSE路径可指认，读回待核 |
| 合法且非伪造的 NPC 决策接入 | CONDITIONAL：日程请求边界，尚非可用外部API | CONDITIONAL：AI queue/routine，覆盖风险 | CONDITIONAL：package/扩展，活跃包风险 |
| 第一实验不需重写核心结算 | UNKNOWN：P1决定，禁止改规则补成功 | UNKNOWN：同左 | UNKNOWN：同左 |

**0–3 是资料适配等级，不是效果测量：**0=有证据表明当前路线不适用；1=有基础入口/单链但关键限制明显；2=已有具体机制/版本路径，可有界核验，仍有缺口；3=目标相关原版实例与端到端接缝有可复核运行支持。无法判定就填 UNKNOWN，不按零计。各项评分反映本轮证据，不评价整个游戏绝对优劣；成本维度要求实测，本轮全部 UNKNOWN。

| 维度 / 权重 | Exult | OpenGothic | Oblivion |
|---|---|---|---|
| 原生行为与可组合性 30% | 2：服务/消费源码链，原版实例缺口 [X2,X8] | 2：日程/感知/交互脚本入口，原版仪式链分级 [G2,G3,G5] | 1：包接口+预写任务，未核原版状态消费者 [O2,O4] |
| 持续世界、多角色影响 25% | 2：两NPC/物件消费与保存路径；不含全地图保证 [X2,X5] | 2：实体死亡→另一NPC感知筛选、AI状态保存；原版任务消费者未核 [G6] | 1：原版任务锚点，具体包/状态链待核 [O4] |
| 合法观察、NPC接入 20% | 1：调度接口≠可用外部闭环 [X3,X4] | 1：Daedalus接口≠外部闭环 [G2] | 1：OBSE接口≠安全闭环 [O2] |
| 运行、重开、实验成本 15% | UNKNOWN / NOT_MEASURED | UNKNOWN / NOT_MEASURED | UNKNOWN / NOT_MEASURED |
| 内容取得、版本、维护 10% | 2：引擎/版本/Mac路径明确，商业数据待取得 [X1,X6] | 2：版本/许可明确，脚本兼容风险 [G1,G2] | 1：明确旧build，闭源/扩展/Mac路径风险 [O1,O3] |

不把 UNKNOWN 重归一化为优势。按未知项取 0–3 的**可能区间**计算，满分 3：Exult **1.50–1.95**，OpenGothic **1.50–1.95**，Oblivion **0.85–1.30**；已评分权重均 85%。前两者在此粗粒度评分打平；不是统计置信区间，也不证明速度/效果排名。条件性首选 Exult 的取舍是**非战斗活动中已查到可反驳、可实测的跨NPC对象消费者链**，更直接对准日常活动组织；这是本轮适配判断，不是游戏优劣定论，更不是 API 好接就获胜。

## 8. 决定、被推翻的推断与唯一下一验证

**条件性首选 Exult。**它最接近“组织已有行为而非新增规则”的要求；先核服务/食客这一小链，不从全能 NPC 架构开始。**备选 OpenGothic。**routine/感知/恢复及实名仪式使它比仅有低层命令的引擎更有研究内容，但脚本兼容、原版状态链与现代渲染成本仍待核。**Oblivion 暂缓，不作全局 NO_GO：**内容丰富不足以抵销本轮较弱的固定原版源码证据与当前 Mac/包控制风险；尤其不能拿研究者新增交易系统证明原版已有组合经济。

本轮明确否定：老游戏一定便宜；日程/职业名意味着有真实生产；有 save 就可精确重放；有控制台就有 NPC 合法控制；有 API 就已有原版实例；所有地区都在持续同精度模拟；第三方研究示例属于原版能力。也**没有**否定外置角色记忆，或把原版缺通用心理系统当淘汰理由。

### 下一阶段唯一关键验证：Exult 原版实例上的观察—请求—结算—消费闭环

**仅为 P1 方案，当前未授权施工/未运行。**前提是用户提供合法 BG 数据或确认可用路径，固定其 hash 与 Exult `v1.12.1`；不索取账号、不购买、不下载商业资产。预算建议为一个工作包：最多一工作日、一个场景、一种既有行为；达到停止条件即停，不能因“不好接”无限造适配层。

1. **实例存在关。**加载未经新增玩法的 BG 存档，核实一名原生服务者和一名原生食客的稳定 NPC number、地点、原生日程/设施。Blue Boar 只是优先核查线索，不强制把 Lucy/Jeanette改成服务/食客。原版没有该实例就记录此机制未用于目标内容，不能靠改日程伪造“原版自主基线”。
2. **基线连续关。**无作者要求、无外部角色控制，记录一个用餐窗口的NPC日程→原生动作→食物出现→消费者实际移除；保留请求前后地图/持物与事件时间。区分消费者移除、清场删除、读档丢失，不能只看食物消失。先在加载区域内验证，不把它推广至离屏。
3. **一次合法请求关。**如果原生实例成立，只给该NPC请求一种已有服务/移动行为，允许最薄的只读观测/脚本桥；记录控制归属/期限、原生日程覆盖、实际成功或拒绝，不直接写物件、库存或任务完成字段。诊断 W 与供角色的局部 O 分开，角色不能得到引擎全局对象列表。没有可用请求入口时，本步 FAIL，不把schedule直接写值冒充行动成功。
4. **恢复/干扰关。**恢复固定初态，核对身份、时钟/日程/对象，再由玩家依法改变一个实际可移动物件/通路条件或交互时机；如原生规则不允许该扰动则换一个已允许条件，不补规则。检查原生拒绝/改道/等待及后续消费，已发生历史不回滚。保存/读回验证持物、日程及结果；另记录离开加载区域后的行为差异，不要求全地图同精度。
5. **成本与结论。**分别实测启动/载入、模拟、采样/请求、存档/重开耗时与故障，报成功和失败链。一次规则请求即可，不实现复杂 Planner。不能据接入成功宣称新算法、可信人物或作者成本下降。

**停止/转备选条件：**无法合法取得数据则记 `WAITING_FOR_LAWFUL_DATA`；原版实例不存在、必须新增人物/设施/动作才能形成链、只能直接改结果、必须大改核心结算，或一天预算内无法隔离观察/控制归属，均停止并保留原因。转备选需后续明确授权，不自动安装第二款。P1 通过也只说明载体闭环可用，不意味长期角色自主、任意作者语义、多个因果方案或研究贡献成立。

## 9. 本轮交付核对

已有：三候选固定范围、证据分级、实名场景与未知项、首选源码因果链及反证、观察/控制路径、成本/许可限制、加权区间、条件性首选/备选与唯一P1方案。未有：商业数据检查、游戏实跑、外部NPC请求、实际性能/可重放性。故 **P0 = PARTIAL**，不以文档自评 PASS 掩盖关键缺口。公开内容限本报告、来源索引和短路由更新；私有对话、商业资产、第三方完整源码和无关脏文件不提交。
