# OpenXRay NPC 决策接入准入 v0

审查日期：2026-10-16。项目基线：`ae63b58e3d6c89ca5d81f3b303a2209313180544`；与远端 `webgpt-sync` 一致后开展本工作包，`main` 未改。

## 裁决

**overall = BLOCKED（原版验证）**；**SOURCE_REVIEW_DELIVERED / READY_FOR_INDEPENDENT_REVIEW**；**NATIVE_RUN = NOT_RUN**。

用户已确认当前没有合法 Call of Pripyat 数据。本轮只作固定源码准入判断，不装依赖、不构建、不运行游戏、不取商业资产、不实现新接口或完整 Planner。

用户本次已条件授权最小原版验证；未实施是因为数据与实际任务接缝未具备，不是等待用户试玩或再次授权。本工作包交付后停止，不自动恢复运行。两名 Luna 分查任务接缝与原生规划器生命周期，父级独立复读关键源码、裁决并核对文档；这是内部交叉核查，不冒充外部独立验收。

固定引擎源码为 OpenXRay/xray-16 `c62d9d343981d50f6ed176412b85d94c61b578b5`，dev snapshot，非稳定发行版。旧控制链详见 [Classic RPG Carrier Selection v0](../Classic_RPG_Carrier_Selection_v0/RESULTS.md) 与 [来源索引 R1–R13](../Classic_RPG_Carrier_Selection_v0/SOURCE_INDEX.md#openxray)。旧报告是本轮源码证据的复用入口，不代表原版实例已验证。

| Gate | 裁决 | 证据边界 |
|---|---|---|
| G1：可复用行为与选择空间 | **CONDITIONAL_GO** | 源码有原生 task-location 移动、基于 NPC memory 选中物的拾取以及战斗/避险规划。不能据此证明任意作者目标都能重组为这些行为。 |
| G2：不改结算的决策接入 | **CONDITIONAL_GO（仅 Lua 触达 live planner）** | Lua 可取得 Stalker live planner 并设置 world-state target；安全交接、命名目标映射、拒绝/撤回和结果回执仍 **UNKNOWN**。不准入完整 Planner 施工。 |
| G3：实验条件 | **BLOCKED** | 无合法 CoP 数据、原版 NPC 配置/存档、构建验证或实跑。原版实例和控制闭环均未确认。 |

**技术决策：**保留 OpenXRay 为有条件的研究世界候选，尚不能接入完整角色 Planner。只选 **B（已有 Lua/task/scheme 路径）**为最低改动的待核入口；不是宣布已有安全任务 API。A/C 不开工。缺数据不是技术 NO_GO 的证据，因此本轮也没有转做 RimWorld 的依据。

## 上层目标到原生执行：已核调用链与断口

```text
server ALife: update_switch / update_scheduled
  → server brain.select_task（满足分配门控时）→ smart terrain → task
online Stalker: shedule_Update → 感知/敌人/memory 更新
  → 非 Remote 且非 ScriptControl → Think → brain.update
  → CStalkerPlanner → solve → 当前 operator 的 finalize/initialize/execute
     ├─ 原生 Combat / Danger / Anomaly
     ├─ ALife child.update → SmartTerrain action → 读取既有 task → 原生导航
     └─ GatherItems → 已选物/接近/触发 → 原生 ownership event → 库存接受或拒绝
候选外部入口（未接通）:
  npc:motivation_action_manager → root.current_action → cast_planner
  → 确认 ALife child 后 set_goal_world_state
断口: 外部角色的具体目标 → 已有 job/task/condition 的可靠映射及撤回/结果契约
```

server task 还可通过 evaluator 触发选择；上图分清两个执行侧，不表示 server 每次更新都给所有 NPC 重派任务。[R3–R10,R13,S1–S2] root 的条件驱动求解不是已证明的独立硬优先级抢占器；实际反应延迟及脚本覆盖需实机验证。

## G1：行为与选择空间

ALife update manager 周期性运行对象 online/offline switching 和 scheduled registry；它不是面向某 NPC 的剧情目标分配器。[R3]

Smart-terrain evaluator 从 ALife registry 取对应 server entity，调用 `brain().select_task()` 后读取 `m_smart_terrain_id`。这个 evaluator 会触发任务选择，不能当纯查询。[R4,R13]

继承的 `CALifeMonsterBrain::select_task()` 在 NPC 尚未分配 smart terrain、允许选任务且选择间隔满足时，遍历 enabled terrain，比较 suitability 并登记选中的 terrain；它不是接受外部“去指定目标”的 API。已有分配会直接返回。[R13]

`CALifeSmartTerrainTask` 将 patrol point 解析为 game vertex、level vertex 和位置；它是任务位置封装，不是目标选择器。[R5]

`CStalkerActionSmartTerrain::execute()` 每次执行都从 server brain 重新取当前任务，再设置 game/level path 与目标位置；不可达时尝试最近可达位置，分配标记存在却无 task 会触发异常。[R7]

拾取动作的符号条件包括存活、无敌人/异常/危险以及存在可拾取物；Items evaluator 检查的是 NPC `memory().item().selected()`，不是全地图物件清单。[R4,R6]

`GatherItems` 依据已选物设置移动目标并生成 ownership-take 事件；原生事件处理还会检查目标对象与 `CanTakeItem`，通过后才转移库存所有权，拒绝则走 reject 事件。[R8] 这是源码中的原生结算路径，不是某个 CoP NPC 实际成功拾取的记录。

Stalker 顶层 planner 将 ALife、combat、danger、anomaly 等规划器置于不同条件下。现有 combat/danger 条件是保留优先级的源码依据；新增行为若挂到不合适的顶层目标，可能改变它们的选择。[R6]

“到达某坐标”不是足够的研究目标接口。固定源码支持的是既有 task/job 产生的 patrol/graph/level 位置；本轮没有发现任意语义目标名称到可执行 task 的已证实映射。[R5,R7,R13]

**G1 判断：**原生行为可复用，但只证明了有界行为和现有选择器。任意目标组合、实名 NPC 的实际 task、人物能合法得知的目标来源都未证实。

## G2：决策接入与交接边界

固定 Lua 绑定提供 `motivation_action_manager()`，对 Stalker 返回其 root live native planner。[R9] 若当前 root operator 是 ALife 子规划器，可从 `current_action()` 经 `cast_planner()`尝试取得 child，再调用 `set_goal_world_state`；只有 operator 身份正确且 cast 非空时才成立。`action(id)`枚举、world-state构造及实际CoP脚本调用未审完，因此不提供可运行片段。

这个入口接收的是 planner world state，不是自由文本、任意 named destination 或通用任务对象。ALife child 当前 evaluator/operator 只有 ALife、SmartTerrainTask 与 PuzzleSolved 相关结构；将 SmartTerrainTask 的 symbolic effect 当作实际完成也不成立。GatherItems 在 root planner 上，不是 child goal 能按物品名参数化的行为。[R4,R6,R9]

这是 Lua 对 native planner 的既有触点，不是外部 RPC，也不表示任意游戏脚本不会再次设置目标。仅在 `CActionPlannerAction` 当前实现中，`initialize()`没有显式重设child target；这不能保证具体CoP脚本、scheme切换或读档不覆盖目标。[S2]

native GOAP 求解会对比当前 action 与新 solution 的首 operator：不同则 finalize 旧 operator、initialize 新 operator；相同则继续 execute。源码没有证明原任务会进入暂停栈或稍后精确恢复。[R10]

`CActionPlannerAction::setup()` 将 target state 设为 operator effects；`initialize()` 调用父 action 初始化，`finalize()` finalize 父 action 与子 planner，`execute()` 更新子 planner。[S2] 这说明规划器嵌套的生命周期，不证明任意 task 进度能无损保存或恢复。

`CAI_Stalker::shedule_Update()` 会更新可见性、处理敌人与 memory；随后非 Remote 对象若 `GetScriptControl()` 为真走 `ProcessScripts()`，否则才走 `Think()`。`Think()` 调 `brain().update()` 再更新 movement。[S1]

因此用 `GetScriptControl`/脚本动作队列整段替代 `Think()`，不能声称仍保留原生 root danger/combat dispatch。感知更新仍发生，不等于危险/战斗 planner 当帧仍执行。[S1,R6]

`reset_action_queue` 操作的是 `CScriptEntity` queue，不是 GOAP operator sequence；不把它当安全的暂停或交还控制。[R12]

原生 danger/combat planner 有各自 evaluator、action 和 finalize 行为；它们不是可以被上层任意置假的成功 flag。[S3,S4]

### 对象状态读取不等于角色合法观察

Stalker memory 的 visible/sound/hit object 缓存是引擎感知记录入口，可能过时；它们比 ALife registry 更接近角色观察，但本轮未验证目标NPC实际读到了哪条记录。[R12]

`level.object_by_id` 在固定绑定中标为 obsolete/deprecated，底层通过 `Level().Objects.net_Find(id)` 查当前在线 level object；它是引擎按ID查对象，不是 NPC 自己知道某人的依据。[S5]

`level.get_time_days/hours/minutes` 已绑定，函数读取 Level game time 或 ALife time manager 并拆字段；`get_time_days()` 返回 day 字段，不是经过的总天数。`game.get_game_time` 另有绑定，本轮未继续追其 `get_time_struct` 实现，不能将两个入口混为一个已验证时钟契约。[S5]

Lua 还绑定 `inventory_for_each`、`object_count` [S6]；`action/current_action/current_action_id` 则属于 planner 绑定 [R9]。这些可做诊断或引擎状态读取，不能仅凭接口存在就纳入角色 O。库存枚举不是“角色已感知物品”；current action 是规划器状态，不是角色的自述或观察内容。

在线/离线管理涉及在线 entity 表示移除、server 对象保存/重建路径与 brain movement 通知。不能只凭 switch manager 宣称 local Stalker planner 或外部目标跨切换精确续跑。[R3,R13,S1]

`CAI_Stalker::save/load` 调用 brain 的 save/load；planner save/load 会保存 evaluator/operator 与 property storage。[S1,R10] 这些入口存在，但当前片段不足以证明 live external target、当前动作精确进度或撤回租约跨存档恢复。

### A / B / C 路线比较

| 路线 | 最低机制与主要限制 | 当前判断 |
|---|---|---|
| A：扩展 native ALife high-level task/goal | 可在原生 task/evaluator/operator 处表达新目标，并将行为放在现有顶层 danger/combat 门控之下；实现可以落在 C++ 或 task 脚本，不能预先说必然要改 C++。需要目标语义到既有 job/task 的映射、清晰拒绝/撤回/结果状态，以及保存和切换生命周期验证。 | 控制模型最贴近原生决策，但扩展面和验证成本高；当前无实例映射，未准入施工。 |
| B：已有 Lua/task/scheme 路径 | 可通过现有 Lua getter 触达 live planner，或按实际 NPC 已有 scheme/task 组织原生行为。[R9,R11] 固定树含 `xr_logic.script`，但依赖的 `xr_gulag`、`xr_conditions`、`xr_effects` 及商业 CoP 配置不齐；scheme 切换会 deactivate/reset 旧 scheme，不能假设无损暂停。 | **唯一最低改动候选，尚未准入。**只有实际 CoP 脚本能承载目标且不破坏 root dispatch 时才继续；否则本轮三路都没有可用实现，不升级到 C。 |
| C：thin C++ external transport bridge | 可以新增请求传输，但传输自身不提供 NPC 语义目标、原生 task 选择、合法观察、战斗门控、失败/撤回语义或游戏内结果消费者。还需要身份解析、请求授权、状态读回与保存/切换处理。 | 没有现成 transport 被固定源码证实；桥接不是任务接入方案，成本和新接口范围更大，本轮不建。 |

上述路线都不能以“已取得某 NPC 控制权”描述。若 B 要映射进 native planner，仍须使用引擎已有 evaluator/goal 语义；若必须新增目标属性或 operator，它就跨入 A 的扩展范围。

**B 的最小改动账：**需要一个游戏进程内 Lua 调用点、实际 NPC/既有任务的映射、合法观察筛选，以及请求/真实结果/撤回记录；不拟改原生移动、拾取、战斗与库存结算。外部程序如何把一次请求送到 Lua 尚未核实，不能称为现成外部接口；若必须新增 C++ 传输或新游戏行为，本候选不自动升级施工。实现行数、工期、重编译需求与运行开销均 **NOT_MEASURED**，不以“薄”代替成本证据。

| 验收点 | A：native task/goal | B：现有 Lua/task/scheme | C：外部 transport |
|---|---|---|---|
| 指定一个真实 NPC | 必须映射到合法实例/稳定身份；当前 UNKNOWN。 | 也缺实际 CoP NPC配置；引擎对象ID不可替代实例证据。 | transport能带ID，不提供原版身份映射。 |
| 非坐标语义目标 | 需定义/映射到 native task或goal；未证实任意目标可组合。 | 只可复用已存在属性、job或scheme；named target映射未知。 | 传字符串不产生游戏内task语义。 |
| 保留 danger/combat | 若挂在 ALife child 且 root gate不改，结构上有候选；需验证。 | 对child路径须确认当前 root operator 为ALife；`GetScriptControl`会绕过Think/brain.update，不能拿脚本队列接管声称保留root dispatch。 | transport不改变原planner优先级。 |
| 拒绝与撤回 | 可设计本地结果状态，但源码现状无外部typed refusal/撤回契约。 | scheme可能reset旧行为；无请求租约或恢复栈证据。 | 可返回连接/协议错误，不能证明NPC拒绝了原生请求。 |
| 真实反馈 | 可消费原生事件/状态，但需选定具体动作和可验证结算。 | 只能读取既有scheme/action结果；没有通用回执。 | 传输成功不等于游戏行动成功。 |
| offline/save | 有 server brain 与 planner save/load路径；目标/精确进度续跑未证实。 | xr_logic保存active section及pstor，不等于动作进度恢复。 | bridge还需对象重解析与请求持久化；不能补引擎语义。 |

## G3：实验条件与未核事实

原版 CoP 数据、特定实名 NPC、其当前配置/逻辑 section、现成 job/task、存档和可复现实验场景均未取得。故本报告不写原版角色实例、不推断某 NPC 会采用 `xr_logic` 中某个接口，也不将源码类名当游戏角色证据。

固定树有 `xr_logic.script`，但其执行路径引用 `xr_gulag.get_npc_smart/getJob`，并在 condlist 处理中调用 `xr_conditions` 与 `xr_effects`；对应脚本不在固定树中。[R11] 这只证明上游公开树的依赖缺口，不代表完整商业安装包缺少这些脚本。

源码里有原生拒绝/结算实例（如拾取 ownership reject），但没有证明存在通用外部 typed refusal、撤回确认或结果回执协议。当前位置、movement intent、planner operator effect 均不能单独作为任务成功反馈。[R8,R10,R12]

角色身份也需经合法实例核对。online 对象表示销毁重建后应重新解析对象身份；源码中的 `PerformIDgen(old_id)` 不足以证明每次切换都会改变 ID。[R3]

本轮复查未发现 `/Applications/OpenXRay.app`、`/Applications/STALKER.app`、Steam `appmanifest_41700.acf`、Steam common 下两个常见 CoP 目录，或 `~/.local/share/GSC Game World/S.T.A.L.K.E.R. - Call of Pripyat`。这些是有限路径检查，结合用户无数据确认，不是全盘资产/所有权审查。当前机器为 Darwin arm64，未确认可用引擎构建，未测原版加载、FPS、离屏吞吐、加速推进或存档恢复成本。

G3 尚缺合法数据、固定 NPC/配置/存档、构建可用及明确可行的任务入口。身份、请求拒绝、撤回、真实结果、danger/combat 响应、offline/save 恢复和资源成本保持 **UNKNOWN / NOT_MEASURED**；本轮不以额外源码推断实机表现。

| 以后必须读回的证据 | 不能替代它的材料 | 本轮是否产生 |
|---|---|---|
| 同一原版 NPC 的原生目标/实际动作及受限请求前后差异 | 类名、目标 setter 返回、命令送达 | 否 |
| 拾取接受/拒绝事件与实际物品/库存变化，或所选既有任务的原生完成条件 | Items=false 符号 effect、到达意图、外部直接写 parent/持有者 | 否 |
| 危险扰动时原生响应及请求取消后合法原生活动 | guard 源码存在、清空脚本队列 | 否 |
| 同一存档恢复后的对照与离屏生命周期记录 | save/load 函数存在 | 否 |

本工作包不支持“通用任务拒绝原因已可读”的声明：GOAP 空解可能断言/返回，smart terrain 缺任务会断言，物品有特定 reject 事件，三者不可合并为已实现的统一 outcome。无解也不是完整不可达证明。

## 固定源码引用补充

旧来源定位见 [R1–R13](../Classic_RPG_Carrier_Selection_v0/SOURCE_INDEX.md#openxray)。本轮补充以下固定 commit 文件；SHA-256 对应项目被 Git 忽略的本地只读副本，仅用于字节核对，不发布副本：

| ID | 固定源码、行段与用途 | 本地副本 SHA-256 |
|---|---|---|
| S1 | [ai_stalker.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/ai/stalker/ai_stalker.cpp#L906-L985)：感知更新后 `GetScriptControl` 分流；`Think` 调 brain/movement 见 1061–1101；构造与 save/load 见 1161–1209。 | `30033a9a81d677639177fa480c8867b224b821323359dcd15ce96e2465031af4` |
| S2 | [action_planner_action_inline.h](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/action_planner_action_inline.h#L19-L50)：nested planner setup/initialize/finalize/execute。 | `ff04de0b4c51f4e0c897d6a27b03093e7f4ad21f2c17a011e3738d4ad0e7b4dd` |
| S3 | [stalker_danger_planner.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_danger_planner.cpp#L39-L108)：danger planner update/evaluators/operators。 | `b4a3618850f4fdccc96c0e1719f05250a3f61de9e2ae74aa0bdfdb5c132dae6e` |
| S4 | [stalker_combat_planner.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_combat_planner.cpp#L109-L205)：combat 初始化/结束及 evaluator。 | `c6a478144777b9556d86f60d81473a1f9e1e9c9fd615b1587276ed81612ec4fb` |
| S5 | [level_script.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/level_script.cpp#L90-L97)：`object_by_id`→`net_Find`；142–164 时间拆分；774、797–799、957 绑定。 | `cb63ccbcc9983b19d8c1172925b8b867ecddb4613e4c14735550c41dfee1c0e3` |
| S6 | [script_game_object_script2.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object_script2.cpp#L127-L133)：object_count 等；[script_game_object_script3.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object_script3.cpp#L278-L286)：inventory_for_each 等绑定。 | 复用 R12 所属固定版本缓存；没有据绑定额外推断枚举函数内部行为。 |

## 提交核验

仅报告与入口指针变更；固定 F0/F1、C++ Runtime、原生动作与旧实验产物不改。已核新/改本地链接、固定源码引用与上述五个副本哈希；仓库 health 检查完成，四项已有警告（依赖内大文件两项、TODO 体积、旧原文重复）保留，不借本工作包清理。没有代码/原生构建或游戏测试，因此不报测试 PASS 数或 NATIVE_RUN_PASS。

**停止点：**本轮交付固定源码准入结论。B 是待合法实例核验的最低改动候选，不是已选定实现；原版验证整体 BLOCKED。若真实脚本无法支持既有行为目标，不扩成 C++ transport，也不添加新玩法。
