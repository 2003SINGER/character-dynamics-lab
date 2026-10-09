# AuthorialTrajectoryPilotV0｜作者控制候选 F2 与预实验协议

日期：2026-10-08。状态：**系统设计与独立参考契约交付；READY_FOR_INDEPENDENT_REVIEW，不是 Pilot 已运行、方法有效或 milestone CLOSED。**

阶段说明：下文 E0–E5 是整体候选计划，不能据此推断整套阶段已获授权。E0 的实际有界验收只查[结果 owner](../02_实验/E0_KeyLedger_v0/RESULTS.md)。用户已授权[E1-0 有限协议](E1_KeyLedger_LocalAgency_Protocol_v0.md)下的 E1-1 最小实现与开发验证，独立开发包已交付；实际状态与证据只查唯一结果 owner：[RESULTS](../02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)。正式实验、E1-2 与 Director 开发未授权。E1 代码入口见[runner](../tools/e1_keyledger_v0/runner.py)。文中的“E0 待审/待编码”保留为历史阶段描述，不再代表当前事实。

本页是作者轨迹分支的设计 owner；[算法积木](../01_文献/算法积木/README.md)维护原算法及来源，不在这里重写论文。输入为本地私有完整讨论两部分：持续人物与作者控制的接口，以及 Typed Trajectory Constraint IR 四份契约。原文 SHA256 为 `65d9142d1b09526fb3d678fd335837d40f04cc923beda5f5c03767d6cea20c94`。自然语言例子不是自动获得执行资格的世界能力。

**职责边界补充：**全系统算法无关的 F0/F1 语义定义由唯一 owner [CharacterDynamics_FormalProblem_v0](CharacterDynamics_FormalProblem_v0.md) 维护；该 owner 当前为 DRAFT、未实现。本页只维护作者控制方向的候选 F2、Typed Trajectory Constraint IR 与预实验设计，不能作为完整 Character Dynamics 系统定义。作者意图如何绑定角色/命题、由何 recognizer 或具体事件证据支撑、再映射为可执行约束，属于 F0/F1 的上层语义链；本 Pilot 的 typed IR 只是候选下游接口，不预设作者直接填写底层变量。

## 0. 要交付什么，不能声称什么

作者想控制的是**持续世界中允许的未来区域及少数必需事件**，不是一条 NPC 必须照演的完整录像。玩家、NPC、世界过程都能改变条件；已经发生的历史不能被重写。人物日常行为仍由其自己的模型产生。

| 等级 | 本轮处理 | 验收对象 |
|---|---|---|
| 用户要求 | 世界中心、多轨迹、稀疏作者控制、可锁定片段、可显式覆写 | 设计不能把其中任何一项删成“导演改 W 就够了” |
| 算法候选 | 规划域绑定、时序 monitor、依赖修复、人物可行性、有限 rollout、语义补桥 | 有输入、计算、输出、前提及拒绝分支；可替换 |
| 研究假设 | 信息机会是否更好、局部修复是否保护生活、不可达诊断是否有用 | E0–E5 才产生实验结果；本轮没有结果 |

本轮实现范围仅为 `tools/trajectory_constraints_v0/` 的独立 reference evaluator：人造状态/事件/区间证据 → 类型检查 → 确定判定。它不是新 NPC、Director、城市经济模型、信任模型或游戏 fork。不改 C++ Runtime、Dynamics、参数、S/P/action schema，不覆盖旧实验。

PlotPoint、Arc、锁定片段等是作者表达的候选形式，不是要求作者必须填入的 IR 类别；底层约束也不得强迫作者提供粮食、心情等浮点曲线。Node/Maze/递归图只可作为规划器内部候选，尚未冻结为架构。LLM、HTN、搜索及其他规划器是可替换实现候选，不由本页预定。规范的未来、对未来的预测、当前控制提案与已提交历史必须分开；预测/rollout 不能作为已发生证据。任何方法产出的作者约束若要声称已落实，必须有真实构造、授权、校验与执行/提交 provenance；method label 本身不构成证据。长程 Monte Carlo 仅是讨论中的候选门控例子，不是已实现部件。

### 0.1 既有系统必须保留，不能冒充现成的新模块

代码基线为 `webgpt-sync@28dfa77`，核查对象包括 `Inc/world.h`、`observation.h`、`state_types.h`、`actor_history.h` 及相关实现。

| 现有设施 | 可以利用 | 明确缺口 |
|---|---|---|
| ContinuousRuntime / scheduler | 时间边界、RunningAction、验证/结算、O 投影、gate、trace | 不是多 NPC RPG；不得再造一套与之竞争的时钟 |
| CharacterDynamicsModel / CharacterPolicy | 人物模型与策略可替换 | 不是已训练通用行为 law；不保证规划里的 NPC action 被选择 |
| W / O | 真值与 Known/Stale/Unknown、来源、失败经验分离 | `Known` 不等于与 W 一致；没有万能 factive knowledge API |
| WorldTask / TaskCommitment | 当前任务进展、运行中 Active/Suspended、暂停恢复 | TaskCommitment 不是 IPOCL 的未来动机 frame |
| ActorHistory / replay | 角色可见的滚动历史、已有配对恢复设施 | 滚动历史不是永久故事账本；部分 RNG 恢复不是完整世界 checkpoint |
| Evaluator / Optimizer | 多维诊断、运行产物及开发/验证隔离纪律 | 当前 no-selection 流程不是 Director 优化器 |
| ActionType / WorldPrimitive | 有限房间域中的实际执行能力 | 没有 `lend_spare/reveal_secret/damage_bridge`；字符串声明不产生能力 |

已有实验的否定和限制以[研究重建审计](研究重建审计_2026-10-06.md)和各 RESULTS 为准；设计不把加入 LLM 当成既定收益。便宜人物模型负责日常生活；LLM 只在已识别缺口时提候选，这是待比较的分工，不是新方法有效的事实。

## 1. 总体闭环：由谁读、由谁改、何时运行

```text
作者编辑 → 类型化约束 bundle（经作者确认）
                        ↓
真实 Runtime 边界 → committed ledger / W / 各角色 O、S
                        ↓              ↓
                 ConstraintMonitor   人物正常继续生活
                        ↓（相关变化/风险，不是每 tick）
            依赖切片 → 世界可达性 → 人物 gap
                        ↓（必要时）
                 LLM bridge proposal
                        ↓
          null / 合法机会 / 已授权作者操作 的有限比较
                        ↓
               再验证 → 真实执行接口 → 新历史
```

Director 能全知读 W 作规划，不代表 NPC 能读 W。把世界事实喂入 ActorFeasibility 的候选集构造或 policy 输入属于信息泄漏。预测的未来与已提交历史分两层保存；rollout 失败不会回滚真实 ledger。

### 1.1 四条控制通道，不因“写进 W”而混同

| 通道 | 可执行权 | 禁止的捷径 | 必须记账 |
|---|---|---|---|
| WorldOpportunitySteering | 仅注册过、作者授权的世界操作：递送线索、提供资源/机会等 | 以 `source=director` 伪装新增执行权限；秘密改 NPC 选择 | 操作、合法性、可见传播、机会收缩/资源成本 |
| NPC autonomous | 由自己的 O/S/P/history/eligible A^O 决策 | 把 A* 的动作直接塞给 NPC 就称自主 | 预测分布与实际选择、持续活动、gap |
| Player | 真实玩家操作不可被 Director 保证 | 不经授权屏蔽毁物/离场等自由 | 玩家实际干预、限制及允许分支 |
| AuthoredOverride / locked sequence | 显式许可的作者 setter 或手写段落 | 假装覆写来自自然 O→X→S；绕过 W 硬合法性 | override ID、条件、setter/model 版本、内容 hash、偏离 |

自然引导不是天然温和：只剩一个机会也可能实质夺走选择。比较中必须同时报告机会数量、被强行限制的行动、覆写次数与作者目标命中，不能只报后者。

## 2. 契约一：Observable Registry

### 2.1 注册量不只是字段名

每个定义使用 `(observable_id, semantic_version)` 唯一键，定义不可原位修改。引用携带稳定实体 ID 与精确版本，不依显示名匹配。Registry 定义至少包括：

| 字段 | 具体契约 |
|---|---|
| owner | WORLD / ACTOR_O / ACTOR_S / LEDGER；禁止调用者把世界量改标 O |
| arguments | 参数名、实体类型、稳定 ID；关系必须保留方向 observer→target |
| value type | BOOL、闭合 ENUM、REAL、类型化 SET、EVENT；不存在万能 float |
| unit / domain | 数值单位与合法范围、枚举合法值、集合元素类型；单位转换显式登记 |
| evaluator ID | 指向白名单中的纯函数；禁止 eval 字符串、动态 Python 或 LLM 判真 |
| reads | W 字段、角色 O/S、事件及其他 observable 依赖；派生量求传递闭包 |
| model pin | ACTOR_S 必须绑定 model ID/版本；关系量还要说明更新规则及 policy consumer |
| time semantics | POINT_ONLY / PIECEWISE_CONSTANT / CERTIFIED_POLYNOMIAL / INTERVAL_BOUNDS / EVENT |
| missing / deletion | 默认 INDETERMINATE；仅显式 exists 谓词可将权威 tombstone 判 false |
| provenance | producer、版本、ledger frontier、合法接收路径、certification 与完整性范围 |

注册函数本身必须通过：正常输入、缺字段、域外值、删除对象、错误 owner、错误单位、版本变化测试。自称“reads 已完整”不能代替代码审计；opaque/LLM 派生量用 `dependencies_complete=false`，触发全范围复查，不承诺局部安全。

### 2.2 四个有具体语义的最小 projector

1. `world.task.progress_fraction(task)`：读取 `effort_done/effort_target`。仅在 target>0、0≤done≤target 且两者可取得时返回 done/target。当前 World 结算有 target clamp；不能在 projector 再悄悄 clamp 非法轨迹。target=0、缺任务、域外输入返回缺证据/拒绝非法记录，不填 0。
2. `world.inventory.holds(actor,item)`：在**拟议 Pilot inventory** 的权威 ownership 中判稳定物品 ID；不是当前房间 World 的通用 inventory API。物品删除与“没有持有”分别由注册 missing policy 确认，不能查同名新物品。
3. `actor.believes(observer, proposition)`：只读取 observer 的 O，保留值、Known/Stale/Unknown 与来源。错误信念可以成立为 believes；Unknown 不自动 false。
4. `evaluator.factive_knows(observer, proposition)`：全知**评估器**联合检查 actor belief、对应 W 真值、合法 delivered-observation/initial-authorized-evidence provenance。一项不成立就不能声称知道；缺来源返回 unknown。它在四owner系统中注册为WORLD-owned的评估谓词（依赖中仍列observer的O与证据），不能标成ACTOR_O并喂给actor policy；也不声称建立完整认识论。

`anxiety` 可注册为模型内部控制量，但要明确是哪个 model 的状态、更新和消费位置；不能改名为人类焦虑量表。当前没有 trust 或 relationship_phase，因此作者选择这些量时编译失败。E3 要先给关系模型定义，不能因 IR 支持 ENUM 就宣称关系动力学已经实现。

### 2.3 证据的时间含义

所有时间统一为精确有理数模拟分钟（整数或十进制字符串输入）；bool、浮点时间、NaN、Infinity 拒绝。显示 Day/hour 不参与求值。实体与事件 ID 不因显示名改动而变化。

- 离散状态：结算后的值在 `[t_i,t_(i+1))` 保持；只有生产者声明并完整记录所有变化，这种 hold 才合法。不能把任意采样列当阶梯真值。
- 连续状态：给出区间内的真实模型解或带假设/误差界的证书。本 reference 接受低阶精确多项式（局部时间 u=t-start）及保守数值界；它**不从两个端点发明 dynamics**。这些是合成测试中受信的输入假设：类型、域、覆盖及数学计算可验，不代表 reference 已独立证明生产者的系数符合真实 World/Dynamics。生产接入必须另验 oracle/commit 路径；当前 C++ 没有自动获得多项式证书。
- 区间界 `[l,u]`：只是可能值包络，u>阈值不证明越界、l≤阈值不证明曾满足。整个界在安全区才能认证；跨界但没有实际见证时 unknown。
- 事件：只按 ledger 真正提交的离散实例计数，连续 state=true 不自动生成事件。重复 event ID+同 payload 去重；同 ID+异 payload/order 视损坏输入拒绝。
- 时间相同：ledger 用 `(time,sequence)` 明确排序。物理严格先后 `t1<t2` 与提交顺序 `(t1,s1)<(t2,s2)` 是两个操作，作者必须选择。

已删除实体保留 tombstone。已提交事实不靠新建同名实体恢复；关系引用保留原两个稳定 ID。模型与 registry 换版会使旧证据不兼容，而不是自动重新解释旧剧情。

## 3. 契约二：Temporal Constraint AST

### 3.1 V0 的闭合节点集合

序列化格式只是载体，语义是以下 typed AST。未知 tag、任意 expression、未注册 ref 均编译失败。编译后的 bundle pin 注册表、domain/operator、model、编辑器/compiler 与 monitor 语义版本。

| AST | 含义与边界 |
|---|---|
| CompareValue(ref, EQ/LE/GE/IN, typed value) | BOOL 仅 EQ(bool)；ENUM EQ/IN合法值；REAL 比较带单位常量；没有字符串隐式转数字 |
| Not / And / Or | **同一时刻**的三值谓词组合；不是先对每个孩子跑完整时窗再组合 |
| AT(formula, time) | 该时刻状态，time window 为单点；不表示新事件 |
| EVENTUALLY(formula, window) | 窗内至少一次为真；过去已有见证可提前成功 |
| ALWAYS(formula, window) | 整窗每一时刻真；反例可提前失败，终点与 coverage 完整后才能成功 |
| EventCount(type, filters, window, min/max) | 权威事件存在/次数；动作启动、完成、失败分别不同 type |
| EventOrder(first, second, order) | 选定匹配实例的先后，实例范围/选择必须显式；不以类型名替代同类型多事件身份 |
| EnumTransitionSequence(ref, states, exact/subsequence, window) | 压缩重复保持后检查真实顺序；exact 不允许未列转换，subsequence 允许插入其他阶段 |
| NumericBand(ref, L/U, window) | 整个指定窗口处于包络；是否连续由证据模式决定 |
| TimeWeightedMeanDifference(ref, earlier/later, min_difference, unit) | `(∫earlier z/Δearlier)-(∫later z/Δlater)≥d`；不是样本平均 |
| Trigger(event, filter, FIRST/EACH, relative requirement) | 真事件启动一次或多次独立义务，锚冻结；不把持续信念当每轮新触发 |

V0 不冒称完整 PDDL3 或 STL：没有任意嵌套 Until、量词、开放算术和任意连续 Boolean 求根。不能可靠认证的组合必须编译拒绝或 INDETERMINATE，不降格成端点测试。扩语法需要新 semantic version 和反例集。

唯一grammar为 `P := CompareValue | Not(P) | And(P+) | Or(P+)`；TemporalConstraint只允许AT/F/G直接包P。TemporalConstraint不能成为P的孩子。其他EventCount/EventOrder/band/mean/enum各自为顶层constraint；bundle是约束集合，不是把temporal节点塞入普通And。连续Boolean组合未有可靠联合证书算法的V0拒绝编译。

EventOrder V0限定为有界窗口中的 `EXISTS_DISTINCT_PAIR`：before/after各为event type+typed args filter，可附精确event ID；枚举真实匹配实例笛卡尔积，要求a.id≠b.id并满足显式order。任一合法pair可作见证；没有pair时按未来/缺证据/闭窗规则判定。不支持ALL配对、按名称猜pair或自动最近配对。DAG节点使用指定实例selector，重复类型不合并；至少一次要求用EventCount，不能把一条order edge自动当发生证据。未指定window或selector范围的order不能作为完成的bounded目标。

### 3.2 窗口、锚与“点”的三个选择

每个 window 存 start/end 与 left_closed/right_closed。所有比较遵从开闭边界；单点 `[t,t]` 非空，`[t,t)` 空并拒绝作为作者目标。零时长 mean 未定义。锚只有 scenario_start、固定绝对时刻、指定真实事件实例；绝对时刻不能同时当偏移再加一次。

账本例子的三种编辑动作应产生三个不同约束：

```text
状态点：AT(holds(A,ledger), absolute=180)
截止目标：F_[0,180](holds(A,ledger)), anchor=scenario_start
发生事件：EventCount(ledger_acquired, actor=A,item=ledger,min=1,window=[0,180])
```

A 起初有账本：前两个可能成功，第三个不能凭空成功。A 拿到后又丢失：acquired 仍然发生过，后来的 AT 可以失败。编辑器预览必须提供这两个反例，而不只给 JSON。

`F(p AND q)` 要求某同一时刻二者成立；p在0分钟真、q在10分钟真但从不同时真时该式失败，而 `Fp AND Fq` 可以成功。这是 pointwise 执行语义的准入反例。

### 3.3 条件启动与真空满足

FIRST 选择匹配事件的最早 ledger key，记录 activation_id、真实 origin 与固定 deadline；EACH 给每个去重事件实例一个独立 obligation。以完整同一前缀重评不能更新锚或延期。多个 EACH 实例分别返回判定，不把一个成功覆盖另一个超时失败。

触发前是 NOT_ACTIVATED，不是 SATISFIED。若作者还要求触发必须出现，需要独立 EventCount/F 约束。不存在“没触发所以剧情目标完成”的快捷方式。丢失可能包含触发的 ledger 段时不能确定从未触发，要给 INDETERMINATE。

ledger completeness必须由producer给出coverage seal：完整提交到哪个 `(time,sequence)` frontier、覆盖哪个时间段及producer版本。FIRST只有从scenario start到匹配实例的事件前缀完整时才可认定最早；否则unknown。锚选择用ledger key，deadline仅加到该event的**physical time**，sequence不转换成分钟。无seal的空event list不是“什么也没发生”。

例如 `belief_revision(B,p,accepted)` → 24h 内 relationship_phase(B,A)∈{SUSPICIOUS,ESTRANGED}，必须先注册事件生产规则及关系模型；现在仅为后续类型化设计，不被假装成现行 C++ 能力。

### 3.4 四类“线”各有表示，不万能 float

- 数值：窗口 band、time-weighted mean、显式包络。粮食 [Day0,2]∈[800,1200] kg，[Day5,7]∈[300,650] kg，早均值−晚均值≥200kg。Day2～5没写的部分自由，不暗补直线；数值只是作者的示例输入，不是经济 law。
- 状态：Active→Suspended→Active→None，区别 exact 与 ordered subsequence；给事件证据与时间范围，不伪造当前值。
- 事件：发现证据→对质→揭露的 DAG，节点是事件选择器/实例，不是三个模糊名称；检测环与同timestamp排序。
- 知识/关系：方向化命题/信念集合、来源修订与合法状态转换，不合成 knowledge_progress/trust_float。SET 可注册；V0 不支持的集合运算必须拒绝，不能隐式当数值。

## 4. 契约三：reference monitor

### 4.1 输入与输出

输入为 `(compiled bundle, registry pins, immutable trace prefix, now)`。Trace 包含 point、segment、event、tombstone、证据覆盖范围。段不得互相矛盾或越过实际 prefix 偷读未来；仅当前 now 以前的证据可用。对每个约束实例返回：

```text
constraint_id / activation_id
verdict / reason_code
witness（时间、值、事件ID或覆盖/反例区间）
dependencies（含版本/稳定ID/时间或事件读取）
margin（若定义，附原物理单位；不做混量纲总分）
semantic_version / evidence_frontier
```

输入非法与真实 VIOLATED 分开：未知 AST、模型错版、冲突重复事件等不产生一个貌似已监测的 false。

### 4.2 五个判定不混合规划状态

| verdict | 正式条件 |
|---|---|
| NOT_ACTIVATED | 已知完整触发流中没有匹配实例，义务未启动 |
| PENDING | 在已观测区域未有决定性见证/反例，仍有未知的**未来**时间可改变结果 |
| SATISFIED | 当前证据已足以保证该有限窗口性质成立；F可以提前，G需整窗完整 |
| VIOLATED | 决定性已发生反例，或截止已过且完整覆盖证明无见证 |
| INDETERMINATE | 相关已过去数据缺失、模型不兼容、证书不够、身份失效，不能可靠判真/假 |

先找决定性证据：F已有真见证时其他位置缺失不妨碍成功；G已有假反例时别处unknown不妨碍失败。没有决定性证据时，相关 past unknown 优先说明证据缺口，不被“还有未来”伪装成纯 PENDING。对同一版本和同一完整 prefix，结果必须确定且可复算。

点谓词采用Kleene三值：NOT(T)=F、NOT(F)=T、NOT(U)=U；AND含F即F，全T为T，其余U；OR含T即T，全F为F，其余U。U记录缺证据原因，不当作一个state值。temporal lifting顺序为：决定性见证/反例→相关已到时段unknown→未来剩余PENDING→完整闭窗最终判定。AT在未来PENDING，在已到时刻U为INDETERMINATE。空窗口与不支持formula先编译拒绝，不走vacuous PASS。

### 4.3 算法：离散分片与连续证书

离散 state 谓词：收集所有被读取 signal 的变化时刻、window 边界、tombstone 时刻，构成公共分片；在每个有效 piece 求同一时刻三值 formula。变化记录完整的 step signal 在 piece 内保持。参考实现用 `seal_values_through(ref,time)` 显式声明该 ref 的变化流完整到该时刻；精确时间点可单独作事实，未 seal 的稀疏点不能证明中间保持或整窗无反例。多个 ref 必须**各自**有 coverage，不能用一个 ref 的段覆盖另一个缺失 ref。seal 是生产者输入承诺，不是 monitor 自动发现的物理事实。

连续 REAL 原子/band：

1. 切到 window∩segment∩prefix；每段检查 owner/version/ref 与闭开边界。
2. 精确局部多项式 `z(u)=a+bu+cu²` 的极值候选为两端点及区间内 `u=-b/(2c)`；c=0只看端点。计算真实最值及见证，而不是匀速猜测。
3. band violation：exact minimum<L 或 exact maximum>U（考虑开端点是否实际达成）；保守 bounds 只有整段必然在允许域外时才证明违背。bounds与允许域重叠但超出时 unknown。
4. 安全认证要求全窗完整覆盖；端点值全安全但没有内段证据仍 INDETERMINATE。
5. 积分用 `(a u + b u²/2 + c u³/3)|u0^u1`，每段分配一次，除以真实时长。重叠冲突/缺段不重复积分或取平均替代。

准入反例：`z(t)=4t(1−t), t∈[0,1]`，端点皆0，内部t=1/2为1；G(z≤4/5)必须 VIOLATED。只有保守界[0,1]而无真实轨迹时必须 INDETERMINATE，不能捏造t=1/2见证。

开端点只用于sup/inf计算，不能作为实际witness返回。对非严格LE/GE连续多项式，若不包含的端点值严格越界，连续性保证附近内部也越界，应寻找一个内部有理点作为真实见证；端点恰等于允许边界不构成越界。EQ的F不能仅凭一个排除的边界根成功；必须在窗口内有真正根或常值满足。V0做不到精确认证时返回unknown/拒绝，不借端点跨过开闭契约。

reference 的精确二次证书不是要求所有 NPC dynamics 改成二次函数。真实 continuous model 可后续提供自己的可靠界/证书 adapter；做不到就不允许 hard连续约束假 PASS。不会用 `sample_every_60_minutes` 冒充正确性。

### 4.4 hard/soft、冲突、版本与删除

hard 与 soft 使用同一真值语义；soft 不把unknown抹成低罚分。每个具体量只报告可解释 deficit：band max越界量及持续时间、mean差不足值、目标迟到分钟、事件少几个。不同单位不直接求和；后续 Director 的 author weight/lexicographic priority 必须另冻结，缺失数据不可优化成0成本。

静态冲突检测只输出有证明的局部矛盾，例如同锚同实体的重叠 universal窗口 x≤1 与x≥2，或同一 AT bool要求相反。必须计算开闭交集；F(x≤1)与F(x≥2)不是这种矛盾，因为可以不同时发生。不同事件锚不能按相同相对窗口断言冲突。

检测不到矛盾不等于整束可满足，默认 COMPATIBILITY_UNKNOWN。HARD_CONFLICT_PROVEN 给出两个constraint ID、同ref/版本、交集及互斥值证明；不降权其中一项来“解决”。硬软冲突交由作者取舍，不能自动升级/降级。

registry公式/模型/插值变化产生新版本；旧constraint仍读旧版本。迁移需旧→新ref映射、语义差异、golden replay对照及作者批准记录。旧版本不可用返回不可判定/加载失败，不用新版本静默替代。删除通过稳定ID/tombstone传播；只有注册了 exists语义才有明确定义的false。

## 5. 契约四：作者编辑语义

| 操作 | 生成的语义 | 必须选择/检查 |
|---|---|---|
| 画状态点 | AT | 时刻、合法ref/value、单位、pin；不是event |
| 画截止节点 | EVENTUALLY | 起止及开闭、状态谓词；不是“到点前每帧都真” |
| 画事件节点 | EventCount / EventOrder | 事件存在或先后、actor/item选择器、同刻顺序 |
| 画数值允许带 | NumericBand / envelope | 显式 LINEAR、HOLD或POINT_ONLY，不默认插值 |
| 画离散阶段 | EnumTransitionSequence | closed enum、exact/subsequence、发生窗口 |
| 连事件箭头 | DAG→order constraints | 节点匹配/实例、strict物理或ledger order、无环 |
| 写一句话 | annotation + 待确认candidate AST | 未绑定语义不能保存成可执行硬约束 |

包络控制点为 `(t,L,U)`，要求L≤U且时间严格增。LINEAR：在作者明确连线的相邻点间分别插值L/U；HOLD：采用左值直到下一点，半开区间，最后一点只是结束标记，不额外约束该时刻；若要约束末点应另加 AT。LINEAR/HOLD至少两个点，单点拒绝而不是静默无约束；POINT_ONLY：只约束点，无间隔限制。未明确连接的两段窗口之间自由；不拿“没有指定”推导成0或直线。样条不在V0，选择它返回unsupported而不是换linear。

预览保存前显示**最终 AST、单位、模型pin、三个正反例、空白区域、override权限**。作者确认后hash bundle；编辑产生新bundle，不修改正在执行的历史判定。撤销约束只撤销未来义务，不删除已有 violation/provenance。

“城市越来越混乱”不自动变chaos:0.2→0.8；应列可注册维度、缺定义处及候选 AST。作者可选择粮食、服务中断、治安事件等多个量，也可保留氛围为未校准展示评价。LLM不决定刻度或充当Monitor。

## 6. 规划域 / WorldOperatorAdapter：先有真实操作才搜索

### 6.1 Frozen OperatorSpec

每个算子具备：ID/version、typed arguments、control_owner、preconditions、持续时间、invariants、effect/settlement、resource reads/writes、information delivery、实际executor绑定、失败outcome及测试。控制权不是actor字段推导；NPC操作的 actor是B也不能由 Director调度。

最小钥匙域另立应用，不塞进当前 C++房间variant。以下是**拟实现**的操作定义，不是现行API：

| 算子 | pre / effect | owner / time / 信息 |
|---|---|---|
| destroy_key(player,key) | 存在且可接触；提交destroyed tombstone，不毁备用钥匙 | PLAYER；结算即事件；只向现场/合法通道传播 |
| inspect(actor,site) | 可达并到场；产生观察，不凭空改变物品持有 | NPC；定义时长；接收者自己的O更新 |
| return_tool(A,B) | A持有B的tool且双方同场；真实转移ownership | NPC；双方接收自有反馈；不会自动使B答应借key |
| request_spare(A,B) | 同场、A可选择请求；提交request事件 | NPC；B是否同意非该操作effect |
| lend_spare(B,A) | B持有备用、合法交易条件；物品转移 | NPC；需B真实policy选择；失败保留原owner |
| deliver_hint(channel,A,prop) | 作者许可、已有合法来源/媒介、channel可达 | DIRECTOR_WORLD；提交delivery，非知道/相信必然为真 |
| open_archive(A,key) | key真实可用、门匹配、A到场；门状态改变 | NPC；有duration/invariant；玩家可中途改变条件 |
| acquire_ledger(A,item) | 物品真实存在且可接触；转移ownership、产生acquired | NPC；settlement；不要以task努力proxy代替 |

duration必须由domain定义，不让LLM拍分钟数；executor以真实precondition复核，效果只在真实settlement提交。开始合法但期间关键资源消失产生typed失败/中断，不能照未来plan继续写effect。

### 6.2 搜索基线与输出

E0先在有限离散域做全量均匀代价/A*搜索。状态key包括所有影响pre/effect的变量、资源、时间/约束monitor摘要；不能只hash几条“剧情事实”。启发式先用h=0作为正确参考，再比较经验证admissible relaxation；不是LLM距离。

展开：枚举grounded合法算子→计算持续/资源→模型转移→更新时序约束状态→丢弃真实hard violation→队列。每个节点存parent/op及causal support。显式记录最大expansions、walltime、domain版本、closed-set与搜索算法；预算耗尽只报NO_PLAN_WITHIN_BUDGET。

最短world plan仅证明假定所有动作执行时可达；输出NPC actions为**预测/建议条件**，不是可直接执行的Director commands。planner model与real executor不一致时停止并记录domain gap，而不是补一段文本继续。

## 7. 永久账本、checkpoint/fork与因果依赖

### 7.1 CommittedWorldLedger

append-only记录 `(event_id,time,sequence,type,typed args,producer/version,action/outcome IDs,causal parents,observability,delivery receipts)`。真实物品、任务、承诺来源用stable ID；顺序单调。已提交对话/玩家destroy不能删除、更改顺序或“修复”到另一条过去。

ActorHistory是ledger经权限投影和压缩后的滚动view，不是权威历史。压缩/遗忘可影响NPC知情，不影响作者审计过往事实。未发生proposal与committed event不同存储，不能把plan写进ledger当历史。

### 7.2 完整 checkpoint/fork 验收清单（后续应用实现）

checkpoint必须含：W与entity/tombstone表、resource状态、clock、scheduler队列与sequence、running actions及progress/invariants、每个NPC O/S/P/model/policy pins/commitment/历史、每个随机流状态、ledger frontier、activated monitor obligations/依赖图、domain/constraint/compiler版本、外部model request/cassette引用及response确定性策略。

restore后第一步需hash对照；对同checkpoint同输入同RNG/cassette运行必须同trace。两个fork不得共享可变W、queue、ledger、monitor。sandbox模拟结果不得append真实ledger。联网生成器不允许在fork里“自然一样”，必须冻结responses/cassette或明确非确定性。

本轮monitor-only trace copy/replay测试不满足以上世界checkpoint contract；禁止据它宣称多NPC沙盒已完成。

### 7.3 CausalDependencyGraph 与局部未来修复

有向边包括：world predicates/resources→operator precondition/invariant→running task/action→actor合法观察/commitment→未来constraints；每条边带生产/消费ID、版本、时间范围和authority。经典 causal link `(producer,predicate,consumer)` 的 threat为介于二者之间可能否定predicate的操作；order/resource冲突单独边，不靠自然语言因果猜测。

玩家毁key后的算法：

1. committed destroy写tombstone；diff生成changed refs。
2. union registry transitive reads、plan causal links、running invariant/resource dependents与monitor dependencies，找可达future slice。
3. 不修改过去；freeze未受影响future steps与仍合法的running progress/commitment；保留的不是文本，而是具体实例/资源预约。
4. 在剩余子问题搜索repair；新support重新检查全局共享资源、时间冲突、actor information及全部hardconstraints。
5. 若依赖不全、共享冲突传播出slice或验证失败，扩大slice/全量重规划并记录原因；不得宣称局部最优/安全。
6. repair失败保留真实当前W/历史，返回诊断与作者允许分支；不是重跑过去让key没被毁。

保留比例分“未受影响仍合法活动”和“原未来计划节点”两类；高保留率不能掩盖保留了invalid动作。修复只决定可控操作/条件，不冻结NPC必然执行未来行动。

## 8. ActorFeasibility / MotivationGap

输入world plan、每个actor自己的 O/S/P/history/commitment/policy、合法观察传播，以及operator actor/requirements。输出每个NPC建议动作的三层证据：world legal / actor-known eligible / conditional policy support，另列知识/动机/资源gap。

- World legal：W precondition真实成立。
- actor-known eligible：候选来自actor-local A^O，不把全知可用备用key直接塞给A。
- policy support：在pin模型的当前可见输入下给出probability/utility及条件；没有训练/校准的数值不解释成人类概率。
- future motivation frame：参考IPOCL，把自有goal、支持steps、引发goal的事件、causal links存为未来解释对象；不覆盖当前TaskCommitment。
- gap：A不知备用→information gap；B自有repair任务且借出损失→motivation/resource gap；某action不存在→domain gap；不是一个泛化“不够合理”分数。

任务commitment仍由真实运行反馈维护。给ActorFeasibility加frame不会把NPC变成必服从计划的人。E1必须允许B选择不借；如果只测一条成功借钥匙录像，无法检验自主执行差距。

## 9. LLM bridge、rollout与不可保证的诊断

### 9.1 LLM proposal 契约

只在明确gap时调用。请求含gap、合法operator catalogue/pins、proposal可读信息及控制权限、作者constraints，NPC语义请求不可越过其O。返回有限typed候选：调用哪个已实现算子、绑定哪些stable IDs、满足哪些preconditions、预计怎样消除gap、读取哪些dependencies、权限和未验证假设。

schema→类型/权限→W合法性→反例/rollout依次验证。未实现能力只能输出`requires_domain_extension`交作者/开发者，不在运行中注册新operator。LLM的“对话说服了B”不能直接设置B信任/承诺；只有明确授权override通道可以，并必须留下记账。

### 9.2 有限反事实机会选择

候选集必须包含null（不干预）、合法world opportunity、明确允许的作者operation；NPC/player动作作为模型随机变量而不是控制变量。候选在同完整checkpoint、同成对seed/cassette、同horizon和相同调用预算进行rollout。

每次估计记录 author约束达成次数/总数及区间、actual policy failure、需要覆写/剥夺选择次数、actor连续性破坏、runtime/LLM成本、世界资源消耗。先排除真实hard权限/合法性违背，再使用作者事先冻结的lexicographic priorities或同单位代价，不拍一个混合总分。

`Pr(C_author | do(u_D))`在此仅是**给定模拟模型的单次候选干预 `u_D` 达成率**；不是从观察数据识别的真实因果效应，也不是玩家自由下的保证。候选评分/选择及其rollout本身不证明闭环Director策略存在 `∃d ∀responses` 的鲁棒保证。选择出的 `u_D` 提交前必须在当前W重新validate，过期候选不执行。

本节估计属于“固定策略下的成功概率”对象：策略、随机模型、初态和绝对 deadline 必须固定；单次确定性 trace 是单次 verdict，有限 rollout 只能在明确采样假设下给估计/置信区间，不能给无条件或确定性下界。汇总得分不能代替合法路径见证；经逐步验证的成功 rollout 可以给出同一冻结模型中的存在性见证，但不证明真实世界已完成，也不证明作者策略对所有允许响应都有保证。后者需要显式冻结响应策略类并完成有限博弈/模型检查证明，不能由全成功样本替代。Director 策略只读其授权历史，不能控制 B 的自主选择。

### 9.3 六个标签是正交证据，不是一种万能status

| 标签 | 足够证据 | 不能替代 |
|---|---|---|
| SATISFIED | 真实trace的Monitor已满足 | 不从rollout预期写成已经发生 |
| POSSIBLE_IN_WORLD | 冻结模型中存在合法joint control与executor转移，可达目标witness | 不保证NPC/玩家实际选择；不等于固定策略成功概率或作者鲁棒保证 |
| PLAUSIBLE_UNDER_ACTOR_POLICIES | 给定固定策略π、响应/随机模型M、deadline及样本预算的rollout估计 | 单trace不是概率；有限样本只在明确采样假设下给估计/置信区间，不能给无条件或确定性下界或全响应鲁棒保证，亦非心理有效性 |
| NO_PLAN_WITHIN_BUDGET | 有完整预算/timeout日志但无解 | 不证明不可达 |
| PROVEN_UNREACHABLE_IN_FINITE_DOMAIN | 已穷尽完整有限domain或有效形式证明 | 不升级成开放游戏绝对不可能 |
| CONFLICTS_WITH_AUTHOR_CONSTRAINT | 两约束冲突proof或可验证unsat core | 不自动降低hard权重 |

例如deadline未到且唯一key被毁：Monitor可以PENDING，planner在确证无spare/domain完整时可PROVEN_UNREACHABLE；两者同时成立。不存在“搜索失败所以过去时序已违反”。

上述标签不新增“鲁棒成功”万能status。鲁棒保证作为单独的策略量词问题记录：需给出合法Director策略、授权历史边界、完整允许响应集合与有限博弈证明。一次B拒绝只说明当前交易分支未成；任务trace仍可包含之后的合法机会，最终由截止时刻及以前的真实witness判定。若固定B策略在整个窗口始终拒绝，且已证明所有合法Director策略均无替代路径或许可干预，则该条件下失败；若此拒绝策略属于允许响应集合，它也构成该冻结域鲁棒保证的反例。这不证明W中任意角色选择下都无路径，也不外推到其他响应集合或授权版本。

作者修订接口只提供：放弃目标、选择已许可分支、补真实operator/资源、显式限制玩家行动、请求override；保留原goal/失败证据及修改版本。不能LLM造未登记的备用key逃避冲突。

## 10. GuardedAuthoredSequence：锁的是内容，不是物理世界

spec含sequence ID、内容hash、进入guard、角色/道具/位置前提、核心动作与对白顺序、锁定范围、可被打断点、abort/branch条件及作者明确允许的fallback。

进入前真实W验证actors在场/存活、ledger存在与信息权限；每个核心动作仍走executor。guard不成立等待/拒绝，不瞬移道具或补知识。玩家中途毁账本/离场按预写abort或允许branch记录；没有fallback就暂停并请求作者，而不让LLM改锁定台词/关键动作。

覆写可以是一项授权setter，但须有model-compatible解释与后续一致性检查（旧关系/承诺依赖失效、决策重新考虑），且显式记录非自然转变。不能拿作者锁定通道为自主行为质量加分。

## 11. 三个研究假设与强对照

| 假设 | 实验操作 | 反证或无增益分支 |
|---|---|---|
| H1 信息/机会比直接命令更能保留人物连续性 | 同world目标比较null、等资源世界机会、明确命令/override；policy/model固定 | 机会命中不稳定、代价更高或实质选择同样被剥夺，则不宣称更好 |
| H2 跨层依赖修复是否能降低未来 suffix 修复成本并保留合法持续活动 | 同玩家perturbation与资源预算，比较 causal-only / 跨层 repair 与进度保持的 full replan；核对依赖合法性、资源重新获取/活动切换、计算量及 repair 总维护成本 | 依赖漏建、非法保留，或总修复与维护成本未改善即失败；不把 full replan 的 reset 当收益 |
| H3 不可达/权限诊断帮助作者处理自由与控制冲突 | 可达、预算不足、有限域不可达、constraint conflict四类已知case | 把timeout当不可达、偷偷补资源、伪装覆写即失败 |

传统基线必须有相同域、信息/任务、资源和预算能力。所有基线（包括 full replan）都必须保留仍合法的 `RunningAction`、reservation 与 progress；需要 adapter 时单列其成本，并报告基线原生行为。E0用正确的、进度保持的 full replanning；人物侧采用同场景的认真utility/GOAP，而不是把RulePolicy采样器叫独立GOAP；LLM基线共享operator权限与grounding，不故意让其全知/空壳。禁止用明显弱baseline为复杂设计制造优势。

## 12. E0–E5 预实验准入、操作和停止条件

本轮不执行新NPC实验。下表是实施顺序，不能一口气实现完整心理/城市world。每一步冻结input/domain/model/operator/constraint/seeds、专用非覆盖run目录、raw trace、错误与null结果；development发现后再冻结新的验证集，不用同案例自证。

共同小世界仍是：玩家毁primary key；A仍想取得ledger；B有spare但A不知道。每个case有真实初始W、actor初始O、各自goal、权限、duration、扰动时间与作者约束；不把一句剧情描述当snapshot。

| 阶段 | 只新增 | 对照与具体产物 | 必须失败/拒绝的case及下一准入 |
|---|---|---|---|
| E0 | 有限inventory/location/key域、真实executor、完整fork、账本截止节点、monitor与fullplanner | reachable path/执行trace；对照exhaustive/h=0与拟用A* | 唯一key不可用且无备用；同时间窗冲突；planner/real effect不一致。未有正确强基线不得进E1 |
| E1 | A/B独立O、B自身任务与自主policy、ActorFeasibility | world path vs eligible/policy/真实行为；故意knowledge/motivation/resource gap分类 | planner知道spare但A不可知；B可拒绝借出；非法O泄漏停止。不得把成功命令录像当自主 |
| E2 | ledger causal links、player destroy perturbation、局部未来repair | 同prefix配对进度保持的full replan/causal-only/cross-layer；比较合法活动与reservation保留、suffix重算、资源重新获取、活动切换、validity及repair总成本 | 任一基线reset仍合法动作、回滚过去或漏掉shared resource冲突即不公平/失败；依赖漏建必须保守扩大 |
| E3 | 有行为语义的关系模型及相对事件窗软轨迹 | 在model specification审计后比较opportunity/override；关系真实transition、policy consumer与差异 | trust未注册拒绝；无触发NOT_ACTIVATED；LLM仅嘴上说信任下降无state effect。未定义关系机制不运行 |
| E4 | 亲写账本揭露片段与guards/abort规则 | 内容hash保持、合法进入/不能进入/中途干扰三类trace；null代价 | 人不在/道具毁坏不偷补；无abort规则请求作者；不得自动改锁台词 |
| E5 | 不相关NPC持续任务、shared resources及第二条world线 | 严格同扰动paired run；未受影响合法生活保留、资源/时间一致、作者劳动分项 | 保留非法计划不能算收益；预算增加/特殊分支劳动必须计入 |

### 12.1 指标的计算口径

- 作者目标：每constraint实例真实判定计数，NOT_ACTIVATED/PENDING/INDETERMINATE单列，不归成功率；hard/soft分开。
- 可达与执行差距：world有path的cases中，actual NPC成功、拒绝、knowledge gap、motivation gap、玩家破坏分别计数；不把world计划成功率当人物成功率。
- 连续性：合法未受影响action ID及elapsed保留、commitment持续/暂停/恢复来源，policy重选次数；真实起止/settlement计数，不能按每boundary重复计行为。
- 修复：changed refs、slice大小、保留/重建因果edges、full validation失败、expansions/time/fork次数及fallback。
- 作者劳动：定义operator/角色/约束、写分支、调试、审核、修改次数和耗时分别记；重用不自动算降低总劳动。
- 运行成本：engine时间、rollout数、LLM调用/token/latency分列；null也用相同horizon。
- 因果可读性/可信体验：先保留可见证据链供人工审阅；没有玩家研究不报告“活人感提升”。机械一致性不等于心理或体验有效。

### 12.2 预算与停止

钥匙—账本 E0 的有限状态、算子、预算与逐 case 预期统一维护于[E0 有限实验协议](E0_KeyLedger_Protocol_v0.md)，其结果由 E0 结果 owner 维护。本页保留较高层阶段契约，不另维护 E0/E1 执行实例。当前 E1-1 授权边界、开发预算和停止条件以[E1 协议 v0.r1](E1_KeyLedger_LocalAgency_Protocol_v0.md)为准；正式实验和 E1-2 尚未授权。

编码E0前必须把有限domain规模、search expansion/walltime、候选上限、rollout N/H和误差/置信报告规则填入独立execution protocol；不能边看结果边加预算。本文不发明一组未经成本测定的实验参数。首次最小cost probe只能确定计算预算，不用于H1/H2效果结论。

停止条件：W/O泄漏、非法effects、账本回滚、fork共享、参考语义不一致立即STOP；预算不足只改变diagnosis，不能修改作者目标凑成功。behavior collapse先审真实trace，不因统计“完成”扩大运行。每阶段结束留待独立复核，不自行闭关制造总PASS。

## 13. 交付 traceability 与下一实施边界

### 13.1 应用实现必须遵从的接口对象（设计，不是当前C++ API）

| 对象 / 调用 | 输入与返回 | 失败不可被抹掉的字段 |
|---|---|---|
| `project(snapshot, ref, frontier) → EvidenceValue` | ref pin+typed entity IDs；返回value或missing、owner/provenance、适用时间及domain校验 | unknown原因、旧model version、tombstone、非法来源 |
| `compile(author_edit, registry, pins) → CompiledBundle` | 闭合AST、typed refs、explicit windows、dependency closure、bundle hash | unknown量/单位、unsupported grammar、hard conflict proof |
| `monitor(bundle, committed_prefix, now) → ObligationResult[]` | 每constraint+activation独立verdict、见证、时间、依赖、单位margin | past缺证据 vs future未到；没有隐式LLM裁判 |
| `checkpoint(world_owner) → ImmutableWorldCheckpoint` | §7.2全部字段+hash；fork返回独立可变副本 | 不完整checkpoint、模型/cassette不匹配必须拒绝 |
| `plan(world_checkpoint, domain, constraints, budget) → PlanEvidence` | steps、pre/effects/资源、causal links、权限、时间、search诊断 | timeout与proof分别记录；NPC steps标predicted |
| `actor_check(plan, actor_views, model_pins) → ActorGap[]` | 每step的W合法、A^O可知、policy支持、goal/frame来源 | knowledge/motivation/domain/resource各分项，不返回泛化可信分 |
| `repair(committed_diff, future_plan, graph, budget) → RepairProposal` | affected slice、preserved instances/progress、替代支持、全量validation | 依赖不完整、共享资源冲突、全量fallback、未授权修改 |
| `bridge(gap, allowed_catalogue) → TypedProposal[]` | 有限已登记operator绑定或requires_domain_extension | 未实现能力/缺动机不写成effect；不commit |
| `compare(checkpoint, proposals_with_null, paired_seeds, budget) → RolloutEvidence[]` | 次数/达成率区间、权限/生活破坏、成本、多维诊断 | 每个fork error、opaque模型与不确定性，不排除失败样本 |
| `submit(proposal, current_world) → ExecutionOutcome` | 当前W重新validate后交唯一executor；真实settlement写ledger | stale proposal、precondition failure、interruption、override provenance |

`Proposal`包含proposal_id、base_checkpoint_hash/frontier、constraint_bundle_hash、operator/model pins、typed binding、control channel、authority grant、assumptions和expiry boundary。基础frontier已变时需重新validate而非盲执行；hash不一致的缓存rollout不能给新W使用。`PlanEvidence`与`ExecutionOutcome`使用不同类型，禁止强制cast把计划效果当真实效果。

这些契约采用一个WorldOwner提交账本，不由Monitor/Planner/LLM分别维护一份真W。将来adapter接scheduler-native runtime时，只有WorldOwner能推进时钟/结算；author应用不反向给frozen人物模块增加“导演专用状态”。

### 13.2 钥匙场景的完整失败/修复推导（不是新模拟）

该实例的纸面来源见[统一问题与成熟基线准入 §2](../01_文献/算法积木/04_统一问题与成熟基线准入.md#2-统一实例域约定与判定层)，具体 E0 执行定义由[E0 有限实验协议](E0_KeyLedger_Protocol_v0.md)维护；本节只对齐原推导：t=2时玩家已提交destroy key0；作者要求不晚于t=10出现真实 `ledger_acquired(actor=A,item=ledger)` 事件。B取回自己的tool与获得payment是分立目标；`return_tool(A,B)`只满足前者，不构成借钥匙动机。教学成功正例是 `offer_loan → B独立选择接受 → 双方确认后的原子交易 → unlock → take_ledger`；只有真实结算的take事件满足目标。此t2→t7手推轨迹用于说明语义，不是benchmark或实验结果。

1. Monitor检查已提交事件账本：截至t=2，coverage完整且尚无 `ledger_acquired(actor=A,item=ledger)` 事件；deadline未到，所以仍是PENDING，不是VIOLATED。初始持有状态本身不能替代本例要求的取得事件。
2. committed destroy使 `key0_intact` false，旧unlock(key0)的support失效；primary-key引用不能改绑spare。
3. 在04 §2冻结的纸面域中，假设B选择接受且各动作合法结算，t2→t7存在取得witness的路径：POSSIBLE_IN_WORLD；这一步不保证B实际接受。`acquired_by_10` 是该事件在时间约束下的witness/派生记号，不是holds状态或另一种事件类型。
4. ActorCheck指出A不知key1；在合法询问前不把key1喂给A。B是否接受由B自己的policy决定；B取回tool本身不能替代独立payment目标或借出决定。
5. Director候选包括null、已授权合法hint delivery、明确许可override；若domain没有delivery算子则requires_domain_extension，不补一个“说句话即可”的effect。
6. sandbox中按固定policy与模型运行，B可能拒绝；记录单次trace或有限样本估计，不改写其TaskCommitment来增加成功率。真实执行只有当前precondition通过的可控候选；一条拒绝trace本身不构成世界不可达证明。
7. 若t=4玩家又毁key1且有限域确无别的途径：planner可给有限域不可达proof；Monitor在t4仍PENDING。作者选择放弃目标/允许branch/授权新真实资源，不能生成“其实还有key2”消除失败。
8. deadline10到达后，若覆盖至deadline且含端点的完整事件账本内没有真实 `ledger_acquired(actor=A,item=ledger)` witness，则VIOLATED；若coverage缺段则INDETERMINATE，不能用planner说无解替代事件证据检查。

同样的trace可以同时支持不同层的结论；这种分离正是现有持续人物设施与新作者控制接口的价值。无需现在发明信任系数或训练policy来让这个机制推导成立。

| 原文要求 | 设计位置 | 本轮 executable / 后续实现 |
|---|---|---|
| 四份语义契约 | §2–5 | 独立Python reference与admission反例；不接NPC |
| 既有持续人物与信息/时间边界 | §0–1、8 | live代码事实核读；C++不改 |
| 可执行世界与规划绑定 | §6 | contract与算子表；E0后续实现 |
| 永久ledger、完整fork | §7 | contract；monitor重放不冒充world fork |
| 六机制 | §3–4 / §7.3 / §8 / §9 / §10 / §1.1 | monitor可执行；其余设计与分阶段准入 |
| 三假设、强基线、E0–E5 | §11–12 | 预实验协议，不伪造新实验数据 |
| unknown/连续内部越界/版本/硬冲突/删除 | §2–4 | 黄金反例与边界测试 |
| 作者本人新理解 | 本节下方 | 留空由本人写；不以模型解释替代 |

本段保留的是该 Pilot 设计当时的实施边界；当前 E1-1 最小实现与开发验证已另获授权，具体范围见 E1 协议及其结果 owner。已有 Runtime 不是空壳，但也不是现成多角色规划游戏。设计准入与方法有效分两次验收。

### 本人新的理解（本人编辑区）

- 我怎样区分状态点、截止节点与真实事件：
- 哪些“线”是允许区域，哪些是我确实想锁定的过程：
- 我接受的作者覆写/玩家自由边界：
- 我认为这份机制还偷用了什么未经定义的东西：

| 部分 | 本人新的理解 / 反例（留白，不由模型代写） |
|---|---|
| Registry：什么量真正有定义 | |
| AST：状态、事件、时窗、触发 | |
| Monitor：证据、unknown、连续区间 | |
| 作者编辑：包络与自由区间 | |
| 世界算子：真的能执行什么 | |
| Ledger / fork：过去与未来怎么分 | |
| 因果修复：哪些生活应该保留 | |
| 人物可行性：知道、愿意、能做的区别 | |
| LLM / rollout：只提候选、怎样验 | |
| 作者覆写 / 锁定内容：我希望怎样控制 | |
| E0–E5：我希望先看到哪个失败或收益 | |

## 14. 算法来源与项目自定义语义

PDDL3 提供 state trajectory constraints及preferences语义；Mimesis的causal support/threat用于未来修复；IPOCL的未来意图解释与当前TaskCommitment分开；DODM启发候选比较而不把world可达当actor保证。具体原算法输入/内部对象/更新/失败见[算法卡](../01_文献/算法积木/README.md)，这里不是宣布原创这些算法。

本项目的typed registry、五个工程verdict、missing/provenance/deletion、模型pin、作者编辑包络、timeweighted差值、权限分道和跨层活动保护均是明确的**设计选择/候选扩展**，不能整套归于某篇论文。时序来源的版本、定义与关键差异见[语义核读](../01_文献/语义核读_轨迹约束与在线监测_2026-10-08.md)。
