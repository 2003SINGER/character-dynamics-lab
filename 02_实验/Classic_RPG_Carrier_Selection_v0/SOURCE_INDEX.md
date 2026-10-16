# P0 来源索引

访问/核查日期：2026-10-16。它只提供证据定位，结论唯一 owner 为 [RESULTS](RESULTS.md)。源码由公开 raw 固定版本只读取得；未发布第三方文件副本。动态文档不是固定版本源码，社区材料不提升为原版实现证据。

## OpenXRay

本节对应后续授权的控制交接源码审查，不把下面历史三候选调查改为实跑。固定上游 `c62d9d343981d50f6ed176412b85d94c61b578b5`（`dev` snapshot，非release）。以下源码均属这个上游版本，**不证明CoP商业原版内容中的任意实名NPC实例已执行**。

| ID / 等级 | 具体路径、函数与能支持的判断 |
|---|---|
| R1 / SOURCE_VERIFIED（许可文字）+ DOC_SUPPORTED | [固定README](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/README.md)列CoP 1.6.02、平台与dev风险；[License.txt](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/License.txt)区分原引擎衍生与OpenXRay修改/新增代码MIT，并指回GSC EULA/内容指南。不是商业资产授权，也不是本轮法律结论。 |
| R2 / DOC_SUPPORTED（动态文档） | [官方安装](https://github.com/OpenXRay/xray-16/wiki/%5BEN%5D-How-to-install-and-play)、[Linux/Mac构建与Game resources](https://github.com/OpenXRay/xray-16/wiki/%5BEN%5D-How-to-build-and-setup-on-Linux-and-MacOS)：需合法原版资源，有Mac依赖/构建说明。仅核文档，没有安装、购买或运行；不以全平台声明证明当前ARM Mac可用。 |
| R3 / SOURCE_VERIFIED | [alife_update_manager.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/alife_update_manager.cpp#L78-L101) `update_switch/update_scheduled/update`；[alife_switch_manager.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/alife_switch_manager.cpp#L48-L129) `add_online/remove_online/switch_*`，167–255 `try_switch_*`。更新/切换管理不等于任务分配；online对象重建、子物件过滤、ID处理不等于精确逐步恢复。 |
| R4 / SOURCE_VERIFIED | [stalker_property_evaluators.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_property_evaluators.cpp#L318-L330) `SmartTerrainTask::evaluate`调server entity `brain().select_task()`，75行Items读memory selected；[stalker_alife_planner.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_alife_planner.cpp#L23-L61)注册evaluator/operator。副作用与符号effect分开，不把property false声明当真实任务完成。 |
| R5 / SOURCE_VERIFIED | [alife_smart_terrain_task.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/alife_smart_terrain_task.cpp#L72-L126) `setup_patrol_point/game_vertex_id/level_vertex_id/position`：任务定位封装，不是目标规划器。 |
| R6 / SOURCE_VERIFIED | [stalker_planner.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_planner.cpp#L48-L185)：setup默认目标、121–130七个evaluator、133–184六个顶层operator。常量PuzzleSolved用于规划机制，不是游戏剧情真实进展。 |
| R7 / SOURCE_VERIFIED | [stalker_alife_task_actions.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_alife_task_actions.cpp#L194-L267) `CStalkerActionSmartTerrain::initialize/finalize/execute`：234–267每次拉原任务、写game/level path和dest/nearest accessible，缺task抛断言；这是movement覆盖风险的具体生产者。 |
| R8 / SOURCE_VERIFIED | [stalker_alife_actions.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/stalker_alife_actions.cpp#L118-L181) `GatherItems`；[ai/stalker/ai_stalker_events.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/ai/stalker/ai_stalker_events.cpp#L24-L68) `OnEvent`查物件/CanTakeItem/parent+Take或reject，112–117 `generate_take_event`。两名代理分别核事件片段；本轮未审完CanTakeItem所有内部条件，不推定其验证全部空间/所有权前提。 |
| R9 / SOURCE_VERIFIED | [script_game_object_script2.cpp:201](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object_script2.cpp#L201) `motivation_action_manager`→[script_game_object_use.cpp:112–128](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object_use.cpp#L112-L128) `CAI_Stalker`→`&brain()`；[action_planner_script.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/action_planner_script.cpp#L15-L57)包装目标与注册API。确实触及live NPC planner，不是外部RPC或通用自然语言目标接口。 |
| R10 / SOURCE_VERIFIED | [action_planner_inline.h](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/action_planner_inline.h#L50-L130) `update/solve`后按首operator切换/execute，90–93空解断言/return；305–342 save/load evaluator/operator与property storage。没有据这些片段证明自动任务resume或完整重演。 |
| R11 / SOURCE_VERIFIED | [res/gamedata/scripts/xr_logic.script](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/res/gamedata/scripts/xr_logic.script)：120–202 configure、347–418 activate、685–713 switch、586–593 conditions/648–657 effects依赖、1350–1508 save/load。脚本正文含旧编码注释，本轮机制判断据可读函数体；不靠猜译注释判语义。固定Git tree有此脚本但不含对应xr_conditions/xr_effects/xr_gulag，未取得完整原版配置；不能把上游随附文件当某NPC的原版运行。 |
| R12 / SOURCE_VERIFIED | [script_game_object3.cpp](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object3.cpp#L90-L123) visible/sound/hit memory；484–533 movement dest setters；[script_game_object.cpp:111–138](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object.cpp#L111-L138) reset/add是CScriptEntity队列，非GOAP序列；[callback枚举](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrGame/script_game_object_script.cpp#L56-L115)不等于已有外部结果协议。 |
| R13 / SOURCE_VERIFIED | `CALifeHumanBrain`在[src/xrServerEntities/alife_human_brain.h](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrServerEntities/alife_human_brain.h)继承`CALifeMonsterBrain`；任务选择实际在[alife_monster_brain.cpp:86–122](https://github.com/OpenXRay/xray-16/blob/c62d9d343981d50f6ed176412b85d94c61b578b5/src/xrServerEntities/alife_monster_brain.cpp#L86-L122)：已有terrain立即return、can_choose/间隔门控、enabled/suitable遍历、register_npc；78–84处理任务位置、124–150 update/online/offline移动通知。父级已读。初次误找xrGame下同名实现得到404，随后据固定tree纠正路径；不以找不到函数推断没有恢复能力。 |

父级独立读取的本地副本SHA-256：`stalker_planner.cpp`=`76ab7007d20b06e8b584418372574f66ab6597388d6f744841e776c2c00f021a`；`action_planner_inline.h`=`b9a58ac6f193d3156e0dfe10185a81b85de4b3c9e35ad624d3d4f433891611e1`；`script_game_object_use.cpp`=`d92c830f4be4a2dc7d6e00b66ca58998315fab300ce13ee48bf6dc472fb0135d`；`stalker_alife_task_actions.cpp`=`3a0e31ecfa49b1f55af13a2d39f327b39948142e0e5c3392eed64ce22e7646b6`。这些是源码审查校验，不是游戏执行记录。

以下保留首轮三候选来源；原有版本和事实不变，其推荐优先级按RESULTS当前裁决理解。

## Exult

| ID / 等级 | 实际核查来源、位置与证据边界 |
|---|---|
| X1 / DOC_SUPPORTED + SOURCE_VERIFIED（许可文本） | [v1.12.1 release](https://github.com/exult/exult/releases/tag/v1.12.1)；Git tag `cacb4f584901dab59ff288c750d3622d3378435b` 只读核验；[COPYING](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/COPYING) 是 GPL v2 文本。覆盖引擎，不覆盖 BG 商业数据。 |
| X2 / SOURCE_VERIFIED | [schedule.cc 固定提交](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/schedule.cc)：`Waiter_schedule::find_customer` 3420–3438；`Ready_food` 3622–3653；服务状态机 3705–3914；`Eat_at_inn_schedule::now_what` 803–843、`ending` 847–861。分别证明跨NPC筛选、可生成临时食物、搬移地图物件、随机读取/消费；不证明任何实名 BG NPC 采用这些日程。 |
| X3 / DOC_SUPPORTED（动态API文档） | [Usecode intrinsics](https://exult.info/seventowers/code.php?DATAFILE=exult_intrinsics.dat)：schedule 分类，`UI_set_schedule_type`、`UI_modify_schedule`、`UI_set_new_schedules`，以及 day/hour/minute 查询。日程持久更改有文档，不是实时外部API或角色合法信息投影。 |
| X4 / SOURCE_VERIFIED | [actors.cc 固定提交](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/actors.cc)：`Actor::set_schedule_type` 1800起会结束旧日程/清动作；1843–1845 `tend_shop`→`Loiter_schedule`；`Npc_actor::update_schedule` 5292–5314 按时段选日程；`paint` 5321–5332 唤醒 dormant NPC。不能据此声称无损暂停或离屏逐步推进。 |
| X5 / SOURCE_VERIFIED | [actorio.cc](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/actorio.cc)：读 schedule_type 252、schedule_loc 331–332、next_schedule 358；`Actor::write` 565起，日程701、旧目标位置738–739、next_schedule747、food_level790、持物806；`write_contents` 838–862。另 [objs/iregobjs.cc](https://github.com/exult/exult/blob/cacb4f584901dab59ff288c750d3622d3378435b/objs/iregobjs.cc) `write_ireg`159–181 保存对象/temporary标记。没有证明工作栈/RNG全保存。 |
| X6 / DOC_SUPPORTED（snapshot，非release承诺） | [官方 docs](https://exult.info/docs.html) §1.1声明适用于 snapshot；§1.2–1.3 原版数据/Usecode；§2 Mac路径/CLI；§3.7暂停等选项；§11 speed/trace/config；§12合法原版安装说明。[官网](https://exult.info/)将稳定版和开发树更新分列，不把 SDL3/开发树日程改进归稳定版。Mac路线未本机实测。 |
| X7 / DOC_SUPPORTED（原版手册的第三方托管扫描） | [Black Gate reference card PDF](https://www.mogelpower.de/manuals/ultima7/BLACKGAT-e.PDF) p1 开场指导：Iolo、Petre、Finnigan/Trinsic马厩调查。身份/固定剧情证据，不是源码、自由NPC任务规划或自主行为记录。 |
| X8 / COMMUNITY_REPORT（检索摘要，正文受限） | [Lucy / Ultima Codex](https://wiki.ultimacodex.com/wiki/Lucy)、[Black Gate Britain / StrategyWiki](https://strategywiki.org/wiki/Ultima_VII:_The_Black_Gate/Britain)：Lucy、Jeanette、Blue Boar 身份/地点。正文分别406/403；只能记录检索摘要线索，不能作为其schedule分配或实际食物链的验证。不取未明授权的反编译对话/脚本副本。 |

## OpenGothic

| ID / 等级 | 实际核查来源、位置与证据边界 |
|---|---|
| G1 / DOC_SUPPORTED | [固定 v0.92 README](https://github.com/Try/OpenGothic/tree/2855fa51957bac9e7ce83f938ec127a0ab3badce)、[LICENSE](https://github.com/Try/OpenGothic/blob/2855fa51957bac9e7ce83f938ec127a0ab3badce/LICENSE)：MIT 引擎；原版 NotR assets/scripts 另需自备；macOS Metal/构建与现代图形要求。`git ls-remote`核验v0.92 annotated tag及解引用提交；未构建/运行。 |
| G2 / DOC_SUPPORTED（动态wiki） | [项目 Daedalus scripts wiki](https://github.com/Try/OpenGothic/wiki/Daedalus-scripts)：`Hlp_GetInstanceID`、`Npc_ExchangeRoutine`、`AI_UseMob`、`AI_GotoWP/FP/Npc`；以及未实现的 `Npc_MemoryEntry/HasNews/Witness*`、`Npc_IsInRoutine`。按实际条目区分，不把“most implemented”扩为全部实现。 |
| G3 / DOC_SUPPORTED（维护者直接解释，不是商业脚本源码审计） | [discussion #505](https://github.com/Try/OpenGothic/discussions/505)，Try 于2023-08-11回答：state/start-loop-end、timetable与perception；Xardas `Npc_ExchangeRoutine(...RitualInnosEyeRepair)`，waypoint→遇敌→战后恢复。只使用公开回答片段，没有沿其第三方反编译包链接下载原脚本。 |
| G4 / DOC_SUPPORTED | [v0.92 release](https://github.com/Try/OpenGothic/releases/tag/v0.92)：版本/变更材料；far NPC 与 time-skip 变化提示需固定 build，不等同原版连续离屏仿真。当前README、wiki与较老说明各自有版本边界。 |
| G5 / COMMUNITY_REPORT | [NotR Eye of Innos](https://colony-guide.com/gothic-2-notr/quests/the-eye-of-innos/) “Restoring the Eye”及 involved NPCs：Xardas/Vatras/Pyrokar、Bennet、原版地点与条件。证明有可定位内容线索，不证明OpenGothic该build执行正确、任意NPC可替代，或任务是自由生成。 |
| G6 / SOURCE_VERIFIED | 固定提交 [npc.cpp](https://github.com/Try/OpenGothic/blob/2855fa51957bac9e7ce83f938ec127a0ab3badce/game/world/objects/npc.cpp)：`save/load`208–320、`saveAiState/loadAiState`335–375；`checkHealth/onNoHealth`555–617；`implAiTick`1877–1886队列优先；`takeDamage`2051–2127；`updateNearestBody`2185–2202按`isDead`/感知筛选；`tickRoutine`2997–3039、时段3236–3275；`excRoutine`4356–4359清旧routine。[gamescript.cpp](https://github.com/Try/OpenGothic/blob/2855fa51957bac9e7ce83f938ec127a0ab3badce/game/game/gamescript.cpp) `npc_exchangeroutine`2051–2061、`npc_isdead`1297–1299；[aiqueue.cpp](https://github.com/Try/OpenGothic/blob/2855fa51957bac9e7ce83f938ec127a0ab3badce/game/world/aiqueue.cpp)9–31队列参数序列化。Luna读取，父级复核NPC保存、队列优先、死亡及尸体消费者、routine清空片段；证明重实现机制，不冒充商业原脚本/实机证据。 |

## Oblivion

| ID / 等级 | 实际核查来源、位置与证据边界 |
|---|---|
| O1 / DOC_SUPPORTED | [OBSE官方主页](https://obse.silverlock.org/)：v21支持原版1.2.0.416 Steam/GOG；旧build/加密D2D排除。不是 Remastered；xOBSE社区更新与官方旧版另列，未擅自确定组合版本。 |
| O2 / DOC_SUPPORTED（OBSE v0020文档） | [OBSE command docs](https://obse.silverlock.org/obse_command_doc.html)：搜索 `GetActorProcessLevel`、package data、`SetPackage*`、`SetEventHandler`/package与save/load事件。package部分明确区分 base package 与活跃actor，警告 live NPC 数据更改/重评风险。官方主页v21与文档页v20不能混成同一固定源码版本；本文只据有文档的接口提出待核路线。 |
| O3 / DOC_SUPPORTED | [Bethesda PC GOTY manual PDF](https://assets.ctfassets.net/rporu91m20dc/35hpuLKJ2wsgsaWgKmsqaW/1ba5c2c99d147348094c06d0c8649b79/manual_oblivion-goty_pc_en-us.pdf)，PC安装/数据文件/保存章节。原版平台与商业资产分界；不证明Mac兼容或已持有安装。 |
| O4 / COMMUNITY_REPORT（原版年代资料） | [TES Alliance Side Quests Guide](https://tesalliance.org/forums/index.php?/topic/823-side-quests-guide/)，WhoGuru，原文v.80标2006-05-27、论坛发布2008-09-22，§4.3 Where Spirits Have Lease：Velwyn/Lorgren与庄园剧情。未检查MS02原版ESM或live包，不能升为SOURCE_VERIFIED。CS/UESP相关页面读取受限，未使用搜索片段伪造脚本行号。 |
| O5 / 原研究报告，反证用途 | [AIIDE 2008原论文PDF](https://www.cs.ucf.edu/~gitars/cap6671-2009/Papers/AIIDE08-010.pdf) pp1–3：Oblivion包能力与研究者新增HTN/脚本的区分，Bob/Fred/Stan与交易flags/pelt示例。它只用于排除“论文新造交易链=原版自带”这一误读，不是本轮论文全面审计/新增复现。 |

## 可复查与缺失材料

三个候选均无商业数据 hash、实际 save、游戏内 NPC/物件读回、实时控制结果、性能记录。它们不是省略上传，而是本轮没有产生。公开原始材料仅有上游来源链接；本轮终端只读检索/源码检查不是游戏执行日志。下一步不得将这些空项补写为PASS。
