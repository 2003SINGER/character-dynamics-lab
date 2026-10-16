# P0 来源索引

访问/核查日期：2026-10-16。它只提供证据定位，结论唯一 owner 为 [RESULTS](RESULTS.md)。源码由公开 raw 固定版本只读取得；未发布第三方文件副本。动态文档不是固定版本源码，社区材料不提升为原版实现证据。

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
