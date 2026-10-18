# Veloren Native NPC Decision Integration v1

2026-10-18；起点 `webgpt-sync@c4c47f8`（Talk A 代码/有限结果起点 `4026af0`）。

最新检查点：**Loaded Msg 最小修复：ROUTING / HIRE / FOLLOW 有限 PASS，READY_FOR_INDEPENDENT_REVIEW，已停止**。唯一一对真实 OFF/ON 已完成：ON只提交1请求，原生442受雇于476，并在原生跟随任务中水平移动11.82m；详见文末和[本轮原始证据](evidence/loaded_msg_repair_v1/)。不等于完整角色规划、方法优势或跨存档恢复。以下 `ab6dad9` 的 **DEVELOPMENT / PARTIAL** 与原始失败证据保持不变，不自行 CLOSED。

## 原生链准入与唯一选择

固定官方源码 `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。定位以下函数时以该 commit 加已冻结 A 观测补丁为阅读视图；新增接口只写独立 build copy，不改冻结 A 源码视图、Talk patch、harness 或旧证据。

| 候选 | 真实原生因果链 | 准入边界 |
|---|---|---|
| Job / Hire / Escort | `npc_ai::pirate` 由头目选成员，靠近后发送 `RequestHire`；受方 `check_inbox` 延迟后设置持久 `Job::Hired`；`humanoid` / `hired` 按该 Job 原生跟随；原生返家流程可发送 `EndHire`。`quest_request` / `escorted` 则有 deposit、期限与奖励结算 | **只选原生海盗招募—受雇状态链。**Escort 的现有接受入口依赖玩家对话，NPC 作 escorter 是 TODO；不补写它。海盗 raid 阶段当前是 `villager` 占位，不称袭击、战利品或 Quest 成功 |
| 原生事件 / sentiments / reports | `ReportEvents::on_death` → 合法收方 `check_inbox` → `known_reports` / sentiment → `check_for_enemies` → 原生攻击；`OnHelped` 也会更新获救者的 sentiment | 机制存在但本轮不接，不制造死亡、伤害或倒地来刷状态；没有本轮运行证据，不推广为通用关系规划 |
| 交易 / 物品 | Agent 可回应交易邀请，`commit_trade` 才结算真实库存 | 没找到 NPC Agent 主动相互邀请交易的原生路径；不补新交易规则，不作为本轮链 |

`humanoid()` 的既有 Job / 职业任务选择与 `Action::choose` 是高层接缝；不是向 resettable Controller 写一次活动，也不是替换导航或整个 Brain。外层原生收件、危险与 Agent 反应保持优先。原生任务资格和局部可见条件由引擎复核，计划只预测，不写世界完成事实。

只读解析原始 `rtsim/data.dat`，确认 UID476、480 为原生 Pirate leader；其各自 home/faction 下分别有8、17名未受雇成员。该存档无 Quest；共有23名序列化的原生 Hired 成员，其中2名归 UID476，12名归 UID477，9名归 UID478。序列化 Job 不是当前运行中的可见受雇人数；本次两个运行中 leader476 的局部观测均为0。它们是**实验输入审计**，不是角色知识或执行成果，不能把全存档对象直接喂给 Planner。运行只选 UID476，不因失败换人、种子或世界刷成功。跨加载 Job 持久性本轮没有验证通过。

## 本轮实施与验收范围

复用本地 `gtpyhop-core==2.0.2` 与已有 P3 的 HTN 搜索调用方式；Evennia 的具体任务域不能直接冒充 Veloren。新适配只处理原生招募聚合任务（接近并请求），目标为组建至少4名原生受雇成员；这个数对应现有准备队伍的最低人数，不定义袭击成功。

Planner 仅接收自身角色/Job/地点及局部合法候选；全局原生资格最多提供守卫布尔值，不透露远处对象和 Job。多个合法候选才构成实际选择。`message_sent` 只代表请求，必须在原生视野实际读到收方 `Job::Hired(leader)` 才记录接受；每次反馈后重新计划。历史接受不等于永久有效，目标达成需当前原生观察支持。结束外部任务不直接清理成员 Job 或发送伪造 `EndHire`。

## 固定版本、接口与执行路径

正式运行前冻结输入；[协议](../../tools/veloren_native_decision_v1/PROTOCOL.md)保留启动前措辞，不回写成事后协议。实际输入、限制与逐文件哈希见 [evidence](evidence/) 中的 freeze / manifests / SHA 索引。

| 项目 | 实际冻结值 |
|---|---|
| 官方源码 | `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248` |
| 冻结 A 观测补丁 SHA-256 | `4174287ddd467804e7efbfe7bb6868736475597f0225067c2030aaa17c709610` |
| 本轮五文件增量补丁 SHA-256 | `458c590d701561a0aee011348ed6823da943d4af0e203588fd2a7e8433fb5b7f` |
| Cargo.lock SHA-256（未改） | `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f` |
| 实际服务器 SHA-256 | `2369b3c1712e90156361bda4293da910399b274ebd1710171b6d48090245c318` |
| 世界与选择 | 原版已存在的 seed130626853 世界；同源独立副本；只允许头目 UID476 |
| 预算 | OFF/ON 各一次、各360秒单调时钟保护；请求最多8个、单个 TTL60游戏秒；磁盘底线6GiB |
| 观测 | 同等只读 native observer/persister；没有客户端、玩家输入、Talk 请求或出生/传送 NPC |

新补丁相对**已打 A 补丁的源码**，不是直接相对官方源码。保留原 A patch/harness/结果，构建副本应用新增接口。`PROTOCOL.md`、Python 适配/监督代码、binary 和 userdata manifests 都在启动前固定；两次均由同一 supervisor 顺序启动，没有失败后补跑。

资产复现边界：两组使用同一官方安装的 `install_v0_18_0/assets` 路径；本次 freeze/runner 只检查目录存在，**未包含完整 assets 内容哈希**。协议中“assets hashes”的要求没有完整落实，不能把路径检查称作全资产完整性验证；不事后补一个哈希冒充启动前冻结。

实际调用链：

1. `server::rtsim::native_recruit` 从当前原生角色及局部候选生成 ActorView，复核身份、职业、home/faction、距离、Job、时间与原生准备队伍资格。
2. Python `adapter.py` 复用 GTPyhop 2.0.2，按距离/UID的确定顺序细化 **下一项招募进展子任务**。它不是求完四成员的完整计划，受方是否接受也未被建模；`SOLVED_NEXT_SUBTASK` 不等于总体目标成功。
3. JSONL `RecruitMember` 进入指定 NPC 的原生 `humanoid` / `pirate` 高层任务选择，复用原生接近与 `send_msg(RequestHire)`；没有直接写收方 Job、移动坐标或结算状态。
4. 原生 `SimulateNpcs` / Loaded Agent 继续执行。收方原生 `check_inbox`、Job 更新和 `hired` 跟随才可能产生后续效果；本次**在到达收方这一段出现断点**，见下节。
5. 来源字段 `character-dynamics-htn-v1` 只标记外部任务来源；无请求时为 NATIVE，收方结算始终归原游戏。旧 Talk telemetry 的 `external_lease_active=false` 仅描述 Talk lease，不能证明本轮招募未受控制。

## 实际运行：唯一固定 OFF/ON 对

运行 ID：`pair-20261018-v1`。两组 server 都在后台真实运行并以 exit0结束，均由固定时间保护停止。两组 RNG 未受控，相同世界输入不等于逐帧同轨，不作效率或算法优势比较。

OFF 使用同一个带观测/接入补丁的二进制、只是不提交外部任务，属于 instrumented native baseline，不是官方发行二进制的逐帧等价证明。原生分支保留任务前缀、守卫和随机调用顺序，但本轮没有进行跨二进制确定性复现。

| 原始记录 | OFF 原生选择 | ON HTN 选择 |
|---|---:|---:|
| 服务器启动次数 | 1 | 1 |
| 监督器单调计时（含关闭宽限） | 361.266s | 361.399s |
| ActorView | 344 | 344 |
| 原生基线 telemetry | 3317 | 3319 |
| 外部招募请求 | 0 | 6 |
| native accepted / started / message_sent | 0 / 0 / 0 | 6 / 6 / 6 |
| 原生 Hired 观测 | 0 | 0 |
| TTL terminal `expired_after_message` | 0 | 5 |
| 终点尚未到 TTL 的请求 | 0 | 1 |
| 当前局部受雇成员 / 目标4 | 0 / 4 | 0 / 4 |

本地日期时间原样保留于 manifest；保护预算使用单调计时，不能直接以日志本地时间相减替代（ON 本地时钟区间与单调计时不一致）。原始 stdout 保留已有 optional-plugin NotFound 报错；stderr 为空不代表 stdout 无错误。运行末磁盘约15.66/15.57GB，未触发6GiB底线。

ON 启动后先确认 Loaded、alive、有限 ECS 位置的原生前缀：t2.103/3.126/4.141，跨度2.089单调秒，leader476 与至少两名合法候选；不以 SPEAK 或截图准入。之后只有当前合法 Loaded 候选可被提出，最多一项在途，不重复同一目标。

这里的“局部”具体是原生招募角色/阵营/Job资格加24m距离过滤，不声称已实现遮挡射线、人的视觉或通用知识模型；远处成员身份不进入 HTN。原生准备队伍人数及可用 raid-site 只以布尔资格输入，不泄漏远处坐标或名单。

| 请求 | 目标 UID | native started t | Controller 消息入队 t | 实际结果 |
|---|---:|---:|---:|---|
| on-recruit-01 | 442 | 4.285 | 6.230 | t64.286 到期；未见 Hired |
| on-recruit-02 | 469 | 65.397 | 67.521 | t125.418 到期；未见 Hired |
| on-recruit-03 | 433 | 126.502 | 129.646 | t186.515 到期；未见 Hired |
| on-recruit-04 | 450 | 187.553 | 190.348 | t247.589 到期；未见 Hired |
| on-recruit-05 | 459 | 247.742 | 251.157 | t307.753 到期；未见 Hired |
| on-recruit-06 | 452 | 308.753 | 311.640 | 实验终点 t351.556 尚未到 TTL368.753；**右删失/未完成，不改写成拒绝或到期** |

`native_recruit_message_sent` 的实际含义是 Controller 入队，不是收方收到消息。五次到期反馈后，HTN依据新观察换选未尝试候选；曾出现候选不足而等待。这证明反馈影响后续**选择**，不证明雇佣效果。目标442并非固定 persister UID，但原生自动 catalog 对它有 Loaded 基线；实际请求时的合法 ActorView 才是候选来源。

**协议/实现偏差：**冻结协议 Pair design §6 写“未尝试候选少于2名即提前停止”，实际冻结运行器没有在 `INSUFFICIENT_CHOICES` 时结束服务器，而是在360秒总上限内等待后续合法观察。原始 ON 记录确有一次此状态后继续。因此本次不是逐条符合协议的正式配对实验；保留协议与代码原样并披露偏差，不事后改协议、删去后续请求或重跑。该偏差不放宽候选资格、重复目标或总时限，也不能用于宣称成功率与方法优势。

OFF 中头目自行进入 `preparing for raid`、`inviting raid participant` 与原生 Following 活动。它们是原游戏已有的决策链，不是 Character Dynamics 成果，也不证明实际袭击发生。ON 的任务来源、请求对应的 Brain 活动与原生消息入队一起支持“高层选择确已生效”，而非仅收到接口文本。

## 失败定位：Loaded 原生消息传递接缝

固定官方源码已存在下列顺序，新接口没有新增收方规则或修补此路径：

1. `rtsim/src/lib.rs::start_default_rules` 先注册 `SimulateNpcs`、后注册 `NpcAi`；`bind` 以 Vec 追加，`emit` 顺序执行。
2. `SimulateNpcs::on_tick` 先从 Controller 队列提取已有 `NpcAction::Msg`，转入收方 inbox。
3. 随后的 `NpcAi` 才运行 Brain，将本轮 `RequestHire` 加入该队列。
4. `server/src/rtsim/tick.rs` 在 `state.tick` 返回后，把 Loaded NPC 剩余 actions 通过 `mem::take` 交给 Agent。
5. `server/src/sys/agent/behavior_tree/mod.rs::handle_rtsim_actions` 对 `NpcAction::Msg { .. } => {}` 不执行投递；下一轮 RTSim 已没有这条消息。

这是**源码可追踪的 Loaded 路径缺口**，与六条消息均无 Hired 的运行事实一致；不是 HTN 搜索已经被证明无解或收方明确拒绝。当前运行没有逐条 instrument Agent dequeue / inbox，因而不冒充逐条接收端审计，也不排除另外的运行因素。原生离屏模式另有机会在下一 tick 路由残留消息，不能把 Loaded 断点推广成所有 Veloren NPC 都不支持 Hire。

另一个仅登记的持久性风险：`SimulateNpcs` 会写 `npc.job = npc.controller.job.clone()`，而恢复后 Controller/AI 首轮次序可能影响序列化 Job。原始存档中已有 Hired 在运行局部视野未出现；本轮未隔离复现这一原因，**不宣布 Job 持久性 bug 已实测，也不宣称跨读档恢复通过**。

本轮不在有效运行中改消息投递、强塞收方 inbox、直接设置 Job 或改离屏模式来补出成功。精简官方源码片段、版本和独立诊断见 [source_audit](evidence/source_audit/)；独立原始读回见 [independent_audit.md](evidence/independent_audit.md)。

## 构建、测试与已知缺口

- Rust 首次构建因新 action 的返回类型不匹配失败；只补 `.map(|_, _| ())`，保留001失败日志及失败补丁。第二次固定版本构建成功，没有改依赖/lock、裁剪原生世界或跳过插件。
- 同一构建环境的聚焦 Rust 测试 **7/7 PASS**（2项招募守卫 + 5项原 A 守卫）。
- 最终 Python 新接口/运行器测试 **35/35 PASS**，原 A 离线回归 **25/25 PASS**；开发中测试夹具/沙箱写权限失败与最终重测分别保留。不是再跑旧 Talk 实验。
- 同源独立输入、code/patch/binary hashes、逐组启动/信号/退出/请求/原始状态均保留。公开证据不包含游戏资产、存档数据库二进制、可执行文件或私人对话全文。
- 新专项 CI 仅运行离线契约测试，不会下载游戏或冒充原生运行。exact-head CI 以实际 GitHub run 为准；历史 E0-H02 的 BUDGET/UNREACHABLE 问题不因本轮修改而被调预算或刷绿。

## 有限裁决与停止

| 本轮验收 | 裁决 |
|---|---|
| 原生候选能力 / 高层接缝 / 权限识别 | 有源码依据；Hire 在 Loaded 执行处存在原生断点，不能仅凭接口列表准入全链 |
| OFF 保留原生决策；ON 从合法观察选择任务并进入 Brain | **有限 PASS** |
| 原生动作尝试、到期反馈与后续重选 | **有限 PASS**；仅 Controller 入队，不是收方结算 |
| Hired 世界效果、受雇跟随及完成后原生续行 | **未证实 / NOT_PASS**；没有效果，不能拿普通 Following 或旧 A 续行替代 |
| 整体原生长链 / 完整 Character Dynamics | **PARTIAL**；不是方法有效性、统计对比或科研创新 |

`ab6dad9` 工作包按两次启动/固定时限停止，交付 `READY_FOR_INDEPENDENT_REVIEW`，不自行 CLOSED。当时待授权的最小消息修复已由下节新审查授权接续；这不改变原实验结论。旧 A、P0/P5、冻结 C++、F0/F1、main 与已有失败记录未改。

## 2026-10-18 新授权：Loaded Msg 最小修复与最后一次纵向验收

状态：**有限接口 PASS / READY_FOR_INDEPENDENT_REVIEW，唯一 OFF/ON 已结束，不再追加运行或第二套机制修复**。新审查原文已完整私有归档并核对 SHA-256 `054d471c1ede602519d60ab6d9fc5d1ee04f39cf732c2aa9bc4026ca2feda7ba`；原文不公开，不建立另一个 RESULTS owner。

本轮只将 Loaded handoff 中的 `NpcAction::Msg` 留给下一轮原生 `SimulateNpcs`；其余动作仍交原 Agent，Say 关联保留原始 action index。`Controller.reset` 不清空 actions，规则顺序不变。新诊断只观测同条消息的保留、原生 inbox 投递、实际消费、Job 变化及受雇者跟随，不直接设置状态，也不把消息发送当成功。

先完成混合 Say/Msg/Say、一次投递、Simulated语义和无效收方测试，再冻结新补丁/二进制/完整 assets 清单/代码/独立输入。旧 A 与上一轮 adapter/runner/protocol/数据不覆盖；OFF/ON 都用相同修复二进制，沿用 UID476、原世界和合法候选，各最多360秒，ON最多6请求。`INSUFFICIENT_CHOICES` 严格停止；首个可信 Hired 后不再招募，只观察同一受雇者最多30秒或到总时限。

最后分别判 ROUTING_PASS / HIRE_PASS / FOLLOW_PASS、PARTIAL 或 FAIL。原生未支持的深层机制不补写，不为了追成功修改第二套机制；无论结果如何本轮结束，不扩 Planner、作者层、游戏技能、LLM或新选材。

### 实际改动与验证

新增的[修复补丁](../../tools/veloren_native_decision_v1/veloren-native-loaded-msg-repair.patch) SHA-256 为 `4883c461895833d493b130143df5f0dd3245b31d00a8324e8b87e90d6ea84ee1`，顺序应用于官方 `1d12f35e` + 原 A + 原 Decision。9个Rust文件、527行新增/68行删除，主要包含只读因果诊断与inbox元数据封装；真正的路由改变是Loaded handoff保留Msg。`NpcInput/NpcMsg`原载荷、原生响应条件、原 `set_newly_hired`、Job序列化、hired/follow、全局规则顺序及RNG调用不改。Say仍按**原始action index**交接；Controller reset不清空actions。新增运行器与协议独立于已冻结旧版本。

最终服务器二进制 SHA-256 `93473c17e11556d9ed7080b6ed9007a879b0614a77c7e9341a6a6b557ebc3aeb`；Cargo.lock仍为 `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`。完整官方资产清单含10419文件、429597400字节，逐文件核验；最终POSIX路径排序树哈希 `e117799caf8d61686fca7c8f7d6e0024384f0fa429959922b922eb2dbc0e6ebf`。初始清单排序预检失败也保留，未改变资产来准入。

原生聚焦Rust测试 **8/8 RTSim + 7/7 server PASS**；父级独立Python决策测试 **54/54 PASS**，旧Talk离线回归 **25/25 PASS**。首次构建的两处类型错误、首次Rust测试的CharacterId夹具错误及其补丁/日志均保留；修正后最终构建成功。详见[尝试记录](evidence/loaded_msg_repair_v1/TEST_AND_PREFLIGHT_ATTEMPTS.md)。没有再跑旧Talk实验，没有缩减依赖、插件feature、世界或预算。

### 唯一一次 OFF/ON 原生运行

本地 run ID：`pair-loaded-msg-20261018-v1`；同一修复二进制、原世界独立副本、seed130626853、leader476、同一组10名observer/persister，view distance仍为2 chunks。没有GUI、传送、强写Job、注入受雇结果或运行中改代码。31项父级哈希核对全部一致，含原世界6文件、冻结源码/工具/二进制和原始JSONL，见[父级读回](evidence/loaded_msg_repair_v1/parent-readback.json)。

公开归档的[最终逐文件哈希清单](evidence/loaded_msg_repair_v1/public-evidence-index.json)覆盖47个证据文件（清单自身除外），保留预审导出索引与最终独立审计；不包含游戏资产本体、存档数据库、可执行文件或私人原文。

| 实际运行 | OFF | ON |
|---|---:|---:|
| 服务器启动次数 / 退出码 | 1 / 0 | 1 / 0 |
| 实验停止请求单调秒数 | 360.069866 | 21.235659 |
| 关闭宽限 / 总监督秒数 | 1.245483 / 361.316354 | 1.238025 / 22.474353 |
| 外部请求 / 上限 | 0 / 0 | 1 / 6 |
| 原生基线行 / recruitment事件行 | 3494 / 344 | 132 / 22 |
| 该窗口局部Hired成员最大数 | 0 | 1 |
| 同请求保留 / inbox投递 / 消费 / setter / Job | 0（无外部请求） | 各1 |
| provenance violation / 未闭合JSONL尾部 | 0 / 0 | 0 / 0 |
| 停止原因 | 固定墙钟上限 | 受雇者原生跟随证据已出现 |

OFF的360秒保护在0.1秒轮询中有**0.069866秒检测超调**；随后1.245秒正常SIGUSR1关闭宽限。不能把总361.316秒写成“进程360秒内完全退出”。本地启动/信号/退出时刻、PID、字节数和哈希均在原始manifest，未重跑来美化时间。OFF/ON四路JSONL总字节各3152783/118995，未触发10000行、16MiB或6GiB磁盘下限。stdout均保留原有optional-plugin目录NotFound错误，两组exit0不等于日志无错误。

ON的准入证据在原始controller行：leader476与候选433/442，Loaded/alive/有限ECS位置的三个游戏时刻 **1.069303 / 2.108912 / 3.115697**，跨度 **2.084008单调秒**；之后才有唯一planner调用和实际请求。没有使用SPEAK门槛；没有出现INSUFFICIENT_CHOICES。该停止分支由离线测试验证，本次未触发，不能宣称本次实跑覆盖了它。

### 同一条真实因果链

唯一请求为 `loaded-msg-on-recruit-01`，目标442，原生接受时距离5.3816m。真实映射是 **476 → NpcId(477v1)**、**442 → NpcId(443v1)**，由实际NPC表与基线核对，非由UID加一猜测。

直接读回：[唯一请求](evidence/loaded_msg_repair_v1/raw_pair/on/recruit-requests.jsonl)、[原生消息与Job事件](evidence/loaded_msg_repair_v1/raw_pair/on/recruit-events.jsonl)、[受雇者原生基线](evidence/loaded_msg_repair_v1/raw_pair/on/native-events.jsonl)、[controller与准入](evidence/loaded_msg_repair_v1/raw_pair/on/controller.jsonl)、[OFF/ON完整manifest](evidence/loaded_msg_repair_v1/raw_pair/pair-manifest.json)。[独立原始读回](evidence/loaded_msg_repair_v1/raw-audit.md)另核17个原始文件、3293523字节及逐项哈希，不以manifest结论替代事件链。

| 游戏时刻 | 实际证据 |
|---|---|
| 3.288135 | 原生accepted、started、RequestHire入队，随后Msg保留在RTSim；均同一request ID |
| 3.322262 | 下一轮原生路由进入442 inbox，442实际消费同一RequestHire；各一次 |
| 5.288342 | 原生接收响应执行原 `set_newly_hired` 后产生只读effect receipt，expiry为原生infinity |
| 5.325925 | 回读442真实 `Job::Hired(476, infinity)`，与同请求的消费/效果回执一致，随后请求终结 |
| 6.150382–12.290614 | 442本人Brain持续出现 `hired by Npc(NpcId(477v1))` 与 `Following actor Npc(NpcId(477v1))` |
| 10.247930–12.290614 | 三个post-hire Loaded快照有原生Goto；真实ECS水平位移 **11.820530m**，三维11.988533m，不用落体Z位移代替跟随 |

首个可信Job后**没有第二次规划或提交**，仅观察该受雇者；跟随证据满足即提前关闭，未用满额30秒。四人队伍目标仍有3人残留，**未完成**；本轮按授权只验证第一条招募链，不冒充整队组织、完整角色Planner或袭击成功。

### 原始数据的两处展示限制

1. 运行器manifest的 `loaded_prefix` 后来被重复check覆盖为null；准入已在controller原始 `loaded_native_prefix_satisfied` 行和逐NPC基线保留。不能把manifest的null当作未准入，也不事后修改冻结JSON或重跑。
2. controller末行 `unattributed_terminal_released_controller_pending / trusted_hire:false` 描述的是**被刻意绕过Job匹配的旧adapter**释放pending，不是新完整因果链的裁决。此前已有 `first_trusted_hire_locked_submissions`，原生投递/消费/效果/Job逐项俱在，manifest新链记录1个可信Job。保留这个命名不佳的兼容日志并说明，不拿它隐藏真实Job，也不靠manifest单独证明成功。任何实际provenance重复或错配仍必须判FAIL。

### 裁决与两个问题的回答

| 本轮关卡 | 有界裁决 |
|---|---|
| ROUTING_PASS | **PASS**：同一Loaded Msg保留、原生投递、接收消费各一次，未进入Agent空分支 |
| HIRE_PASS | **PASS**：原生接收处理与真实Job变更的同请求链闭合，非预测/发消息/外部写状态 |
| FOLLOW_PASS | **PASS**：同一442在受雇后进入原生hired/follow + Goto，并有11.82m实际水平执行 |
| 严格零超调的360秒执行预算 | **未完全符合**：OFF轮询检测超调0.069866秒，另列正常关闭宽限；保留偏差，不改写预算或重跑 |
| 完整Character Dynamics / 方法有效性 | **未验证**；本轮只是修复后游戏的一个有限接口实例 |

**问题1：能否改变原生NPC高层选择，并由游戏结算长期状态？** 在这条限定Pirate链上可以：HTN从既有ActorView选442，476进入原生招募前缀，442经原生消息响应变为Hired，并自行执行跟随。长期状态指游戏原生Hired/expiry机制，不是瞬时展示标志；本轮没有做跨存档重载、长期存活、战斗打断或一般职业验证。

**问题2：为后续重组提供了什么？** 已有可提交的招募子任务、共享的实际雇佣关系、对方后续原生跟随和可核验的事件反馈，可作为未来“先招募、后协同行动”计划的一条真实因果边；上层不必重写这些原生执行。仍缺经过验证的多角色依赖规划、原任务竞争/保留、拒绝及协商、作者节点绑定与约束监测、在线扰动修复和跨读档语义。没有验证的新能力不能从故事想象补齐。

修复本身恢复既有游戏消息机制，OFF也使用同样修复；n=1、native RNG未受控，**不以OFF的0与ON的1宣称方法优势、成功率提升或科研创新**。源码静态审查见[独立记录](evidence/loaded_msg_repair_v1/independent-static-audit.md)，原始运行另作独立读回。旧A、旧Decision/PARTIAL、原世界、冻结C++、F0/F1和main保持不变。本工作包到此停止，等待用户独立验收，不自行CLOSED，不续补Job/Follow/Quest/交易或新作者层。
