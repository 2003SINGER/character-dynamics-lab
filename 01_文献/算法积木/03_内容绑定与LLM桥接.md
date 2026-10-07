# 内容绑定与 LLM 桥接：算法积木底稿

日期：2026-10-08。用途：把已发表系统拆成可单独搬用的机制原子；不是选型、gap 判断、Director 设计或新方法主张。以下“自制手推”只演示输入怎样改变下一步，不代表原系统复现。

## 阅读边界与来源

- WhatELSE：CHI 2025 作者 PDF，方法/环境/审阅/实验定向核读；此前委派阅读及父代理关键段复核，非所有附录逐项精读。固定动作接口与外部 Game Environment 已确认；源码细节/运行未知。[论文](https://www.research.autodesk.com/app/uploads/2025/02/WhatELSE.pdf)；[前审计](../专题调研_多粒度剧情连接与LLM重组_2026-10-07.md#51-三种桥接不是一个东西)。
- Anansi：ICIDS 2024 / proceedings 2025 系统论文，定向读系统、storylet/query/事件和讨论段；[官方论文](https://doi.org/10.1007/978-3-031-78450-7_9)；[开放全文](https://escholarship.org/content/qt21r7h0fq/qt21r7h0fq_noSplash_551994d2dca07b890d023a629e3e27c8.pdf)。GitHub v0.5.1 pinned SHA `1f69f67fc5ac93c69c9eb64cf19612053e9e775c` 只核元信息/版本，源码机制未完整核验；rollback、无候选 fallback 未知；未复现。[前审计](../专题调研_多层状态轨迹约束与可执行世界_2026-10-07.md#5-真游戏与ai-小说看谁建立事实不看有没有文字界面)。
- Drama Llama：arXiv v1 (2025-01-15)，正文 pp.1–6 与 Appendix A trigger 示例定向读；非同行评审结论。[原文](https://arxiv.org/pdf/2501.09099v1)；[前审计](../专题调研_多粒度剧情连接与LLM重组_2026-10-07.md#51-三种桥接不是一个东西)。
- DiriGent：AIIDE 2025 正文 11 页全文及公开五类 prompt / README 核读；附件固定 `1aaa1855f1963c9f191eb575a5d8c8083b4b7480`，是 prompts/materials，非完整可运行实现；未复现。[论文](https://ojs.aaai.org/index.php/AIIDE/article/view/36841)；[固定附件](https://gitlab.inf.ethz.ch/prj-cgl/cgl-ai-character/dirigent/-/tree/1aaa1855f1963c9f191eb575a5d8c8083b4b7480)；[精读](../精读_DiriGent_算法与世界引导边界_2026-10-07.md)。
- NCP-Bench：ICML 2026 正式论文；正文 pp.1–9、相关 prompt pp.19–20；源码按固定 SHA `780aeb559ce216a57cbd934b5a20bfd35018c4f6` 核对 runner、schema、Baseline/HiAgent 关键路径，未运行 benchmark。[论文](https://proceedings.mlr.press/v306/ma26ap.html)；[固定代码](https://github.com/NLP2CT/NCP-Bench/tree/780aeb559ce216a57cbd934b5a20bfd35018c4f6)；[协议卡](../精读_NCPBench_协议与接入边界_2026-10-07.md)。

## 1. Anansi：作者编写的 storylet × 社交模拟

| 字段 | 机制底稿 |
|---|---|
| Problem | 把可复用对话/场景嵌入有社会关系、地点、日程与事件的视觉小说，同时保留作者叙事控制。 |
| State | 角色 ID/位置/日程；有向关系图及 traits/stats；日期时间；共享 logic DB；Ink storylet 当前实例/变量。 |
| Author input | Ink knots + tags、自然语言对白/选项、`@query`、角色/位置/关系数据、Storylet weight/tag/repeatability/cooldown；social event 另定义 roles、preconditions、effects。 |
| Character input | 查询结果绑定到 Ink role 参数；对话依据角色身份与作者写的条件分支，不是自主 LLM agent。 |
| World model | Unity 离散 ticks 更新时间、日程位置、timed modifiers、eligible social events；DB 与关系模拟双向同步。 |
| Authority | logic DB query 决定角色是否符合绑定条件；Ink 运行时决定故事控制流；DISPATCH_EVENT 调用关系模拟执行作者声明的 effect。 |
| Search | 对含变量的 query 为每组有效 binding 创建 storylet instance；全部 eligible instances 进入选择空间；论文称 weighted random selection，没给通用伪码/边界细节。 |
| Trigger | 故事流 queue 到下一个 storylet 或当前位置/玩家动作触发；实例化时重跑查询与 precondition。 |
| Repair | 论文未给失败后自动修补故事/回滚流程；不存在实例时的 fallback/rollback 细节未核，留空不猜。 |
| Can change | 角色绑定组合、对话与 Ink 变量；执行 social event 可改变关系分值，并可级联影响被背叛者朋友对 betrayer 的态度。 |
| Cannot change | query 不会凭空创造合格人物；storylet 不是自由动作生成器；已生效的社会 effect 由模拟写入，不等于更改历史角色绑定。 |
| Handwrite | 角色、地点、关系标签/规则、Ink storylets、查询、权重/标签、社会事件 role/precondition/effect 和各分支对白。 |
| old cost | 作者仍需设计可组合内容与状态逻辑；论文明确存在 learning curve、状态追踪和组合复杂度，作者可能退回传统分支写法。 |
| LLM replace | 本论文不使用 LLM 替作者生成 storylet / action / effect；可借用的是查询绑定和运行时选择接口，不要给它补生成能力。 |
| must not replace | 可执行社会模拟及作者提供的关系规则/effects；角色符合条件的事实绑定；真实 player choice 的 dispatch 边界。 |
| Eval | 系统/工具介绍与 RCR 游戏示例；玩家学习/更广用户体验测试列作 future work，不可写成已证玩家效度。 |
| Failure | 角色可替换导致对白不合身份/关系；角色绑定组合爆炸；DB 与 Ink 两份变量需要同步；作者难以追踪多路径状态。 |

算法顺序（论文 §5，6–10 步）：

1. 当前 state：玩家在提供食物的地点，角色集合和 directed relationships 存入 logic DB。
2. 加载 Ink 文件，runtime 扫描带 storylet header 的 knots，取出 tags/weight/repeatability/cooldown/query。
3. 需要新内容时，对每个 active storylet 的 `@query` 查询 DB；query 不成立则不生成实例。
4. 含变量 query 对每种合法 binding 生成独立 instance；例如两位合格朋友→两份 `lunch_with_friend(speaker=...)`。
5. 将 eligible instances 汇入 selection space；按其权重做加权随机选择（具体采样细节未公开重建）。
6. 把所选 instance bindings 写入 story state，记作 current/on-deck；Ink 跳转进入 knot。
7. 执行 Ink 内容；作者写的 choice 可调用 `DISPATCH_EVENT(event, role bindings)`。
8. social event 再核绑定角色及额外 preconditions；符合则按作者 effect 更新关系/角色数据并同步 DB。
9. AdvanceTime/tick 可推进日程及自动触发符合条件的 social event；之后重新查询可用 storylets。

手推例（自制查询演示，不是论文新算法）：

论文 Listing 1.4 的 query 形态是：

```ink
# @query
? speaker.relationships.player.traits.friend
player.location.traits.serves_food
# @end
```

自制可算输入：Cafe 满足 `serves_food`，Nia 和 Omar 的关系记录都满足 `speaker.relationships.player.traits.friend`，因此 binding 集合为 `{speaker=Nia, speaker=Omar}`。设两份 instance 的作者 metadata weight 分别为 2 与 1；用讲解用抽样式 `P(i)=w_i/Σw_i` 得 `P(Nia)=2/3, P(Omar)=1/3`，假设本次抽中 Nia。这个式子/数字只是解释 weighted selection 的通用例，不声称论文给出该精确归一化代码。玩家选“告诉导师”后，Ink 按论文 Listing 1.2 形态调用 `DISPATCH_EVENT("betrayal", "player, {labmate}")`，本次即绑定 `betrayer=player, victim=Nia`。论文 Listing 1.3 的事件可先应用 victim→betrayer Friendship −10；仅当 DB 查到 Nia 的 friend 且该 friend≠betrayer，才再应用 friend→betrayer Friendship −5。这里展示的是论文示例事件的角色参数/precondition/effect；没有假设事务、原子提交或 rollback 实现。

## 用户的新理解（本人待补）

<!-- 仅由用户本人补写；模型不代填。 -->

## 2. WhatELSE：抽象事件→固定 action schema→真实执行反馈

| 字段 | 机制底稿 |
|---|---|
| Problem | 作者在不同抽象粒度写 narrative space；LLM 将高层 outline 变成随世界状态变化的具体可玩剧情。 |
| State | story domain 的 characters/locations；Game Environment 的角色属性、位置、关系分数、memory；outline 与历史实例。 |
| Author input | narrative examples/outline、domain/entities、抽象层级约束；作者指定可执行 action schema，故事实例可归纳为不同 abstraction ladder。 |
| Character input | plot generator 收当前角色描述、固定 action schema、当前 W（含 memory）；另有 NPC free actions 与 player/proxy actions。 |
| World model | 游戏模拟环境执行 actions 并更新 W；文中 action schema 六种：move to、speak to、kill、attack、think、save。 |
| Authority | LLM 生成 action 序列；Game Environment 执行/更新状态并反馈成功失败；coherence 与角色动机 reviewer 是 LLM 评审，不是硬 truth。 |
| Search | 对 outline event 提案具体 action sequence；plot reviewer 合并整体一致性与逐行动机反馈、环境执行结果，追加到 prompt 重生成。 |
| Trigger | outline 当前 event 到达 compiler；执行一段后玩家可改变 W，compiler 读更新后的 state 再实例化后续事件。NPC 间也可在节点间自由行动。 |
| Repair | 失败或状态变化引发重新生成；例：dove 已死，不能照原序列救鸽子，可改成 ant 落水等替代 action sequence。 |
| Can change | 从抽象事件到具体 action 的实现、角色行动顺序、结局表现；玩家 action 改 world state 后可改变后续序列。 |
| Cannot change | 不能任意发明 schema 外 executable operator；环境的六类 action/角色/对象与实现是固定 domain，不等于语言可以新定义 effect。 |
| Handwrite | domain/world/action implementations、角色描述、outline及抽象度要求；失败 feedback 的可接受叙事和安全边界仍需作者/系统定。 |
| old cost | 传统预写具体 branching 内容限制适配空间；此法把成本移到领域建模、动作定义、审阅/多轮生成，未给总作者工时测量。 |
| LLM replace | 高层 outline 抽象/变体提案；event→六动作实例化；软 coherence/motivation critique。 |
| must not replace | fixed action executable functions 与 world-state authority；校验每个动作是否可执行；不能让文本审核取代真正 engine execution。 |
| Eval | 12 位参与者、作者 3 位；抽象控制/创作与玩家 proxy 变体任务。自报编辑偏好不等于实际总工时；不是“12作者”。 |
| Failure | action schema 覆盖有限；LLM judge 不保证动机真；proxy 不是真玩家；作者成本/长期内容维护未量化；执行有效不保证 narrative quality。候选序列因果试执行后，论文未说明试执行状态是否隔离、克隆、重置/回滚或直接变更后续 W；不能推断会污染 committed W，也不能擅自声称试跑安全隔离。 |

算法顺序（CHI 2025 §4，具体主循环）：

1. 给定 Story Domain（characters/locations）和其固定六动作执行函数，以及当前 World State/character memory。
2. 从高层 outline 取一个 event，送 Interactive Narrative Compiler。
3. LLM plot generator 读 event、角色描述、固定 action schema、current W，提一个具体 action sequence。
4. Plot reviewer 读整段 sequence，给 overall coherence 建议；再逐 action 以被行动角色视角检查动机依据。
5. 把候选序列交给 Game Environment 作执行/因果可行性检查，取得 success/failure observations；试执行后的状态隔离、克隆、重置或 rollback 语义原文未披露（unknown）。
6. 合并 soft reviewer 和执行反馈，作为下轮生成 prompt 的 critique；再提案/审阅。
7. 序列通过后，论文描述再由环境执行最终 action sequence，并更新 attributes/location/relationships/memory；不可把第5步试执行与这里的正式执行合并成“只执行一次”，也不可据文未述推断试跑如何恢复状态。
8. 玩家或 Player Proxy 可改 W；NPC 也可能执行 free actions。
9. 更新后的 W 与 outline 回到 compiler，处理下一个抽象事件，直至 outline 耗尽。

手推例（根据论文示例抽象，执行反馈链为机制；细节是自制）：

输入 outline event=`援助到场、阻止动物受伤`，current W=`dove dead`，固定 action schema 如上。第一提案若含 `save(dove)`，环境状态检查/执行反馈指出受援角色已 dead，后续审阅不能把 `save` 写成复活；反馈回传 compiler。可重生成为 `ant MoveTo(water) → character Save(ant)` 这类同抽象功能的序列；若候选需要 schema 没有的操作，则判当前 domain 不支持，不可声称“新增一个 save operator”。通过的合法动作才更新 W，再处理下一 outline event。

## 用户的新理解（本人待补）

<!-- 仅由用户本人补写；模型不代填。 -->

## 3. Drama Llama：condition-first 的文本 storylet

| 字段 | 机制底稿 |
|---|---|
| Problem | 在开放式 LLM 对话中，让作者能在典型剧情转折处注入可响应的 stage-direction，而非锁定每句对白。 |
| State | 自然语言 setting/cast；累计 script text；每个 trigger 的 condition、action 文本序列、type、当前下一个未用 action/active 状态。 |
| Author input | 写 world setting、角色 prompt、trigger 的自然语言 condition、若干 action stage-direction、Basic/Ending 类型。 |
| Character input | 角色 LLM 读 setting/cast 和完整至今的 script，提议下一句；玩家角色由玩家输入。 |
| World model | 叙述 script 是唯一运行状态；未见结构化实体/可执行 action/effect truth engine。 |
| Authority | LLM trigger checker 回 YES/NO 决定条件满足；runtime 依顺序找第一个满足者；stage direction 文本加进 script。 |
| Search | 没有全局搜索；每条 active trigger 单独做 condition classification，按作者顺序短路；一回合最多触发一条。 |
| Trigger | 每条消息后检查全部 active triggers；最高优先级（即列表最前）匹配触发，注入下一条 action text。 |
| Repair | 不做语义/动作后果 repair；触发列表顺序、condition/action 文本由作者迭代编辑；可 reset/修改故事试跑。 |
| Can change | 文本可注入对话/行为方向；action index 消耗；Ending trigger 停止模拟。 |
| Cannot change | 不会硬写游戏状态或执行 operator；条件 TRUE 是 LLM 对文本判断，不是事实谓词 validator。 |
| Handwrite | Setting、角色行为 prompt、触发条件、序列化 stage directions、触发优先顺序，需反复试玩调整。 |
| old cost | 用自然语言条件替代程序式规则可能较易上手，但作者仍承担 trigger timing/consistency 调试；论文未测节省工时。 |
| LLM replace | 角色下一句文本生成、单 trigger YES/NO 检测。 |
| must not replace | trigger 的作者优先次序/已消耗 action index/文本叙述与游戏事实的区分；LLM 不可当外部 world executor。 |
| Eval | 6 位有互动叙事经验作者的小规模远程 authoring study；自评与 trigger accuracy 标注，无大规模玩家效度。 |
| Failure | trigger timing stochastic/inaccurate；列表前项压后项；action 序列耗尽后失活；无 idle fallback、cooldown/repeatable 机制（future work）。 |

算法顺序（论文 pp.2、Appendix A–C）：

1. 作者输入 trigger 列表 `[(condition_i, [action_i1…], type_i)]`，保持既定列表顺序。
2. 角色模型用 setting、cast、到当前的 script 生成/接收一行剧本；玩家角色由玩家提交行。
3. 每新增一条消息后，依列表次序扫描 active triggers。
4. 对每条 active condition，独立 LLM checker 获得剧本上下文 + condition，只输出 `YES` 或 `NO`。
5. 首个 YES 即停止本轮 trigger scan；其后 trigger 本轮不判断/不触发。
6. 从命中 trigger 的 action 数组取下一个未用文本，追加到可见 story。
7. action 文本这次算 consumed/inactive；若动作数组耗尽，整个 trigger 变 inactive。
8. type=`Ending` 时命中即停止模拟；Basic 则回到角色/玩家生成回路。
9. 如果无 trigger 匹配，继续普通角色/玩家回合；论文当前实现无 K 轮 idle fallback。

手推例（基于 Appendix A，顺序及 index 展示）：

两个 active triggers：A=`Has Sepideh noticed Byron withdrawing?`, actions `[raises voice to ask if okay, angrily suggests rest]`; B=`Byron left the dining room`, actions `[Sepideh takes plate to sink]`。本轮 script 新增 Byron 回答变短。按列表先查 A，checker YES，追加 A[0]，index→1，停止 scan，所以即使 B 也匹配也不会本轮执行。后续再命中 A 则追加 A[1]，A 序列耗尽即 inactive；如果将 B 移到 A 前，输出可能改变。这是顺序控制/文本注入，不是对 Byron 的真实状态或是否已离开餐厅做验证。

## 用户的新理解（本人待补）

<!-- 仅由用户本人补写；模型不代填。 -->

## 4. DiriGent：tension 驱动角色候选与停滞 enforcement

| 字段 | 机制底稿 |
|---|---|
| Problem | 作者有高层 sequence/故事目标，但角色应基于 beliefs 与自身理想行动；在故事停滞时施加引导。 |
| State | 累积 story beats `S`；角色 `⟨Wr,wT,B⟩`：role-grouped ideal worlds、tension scores、beliefs；sequence beat count。 |
| Author input | 初始 story prompt、角色理想世界/relationship、belief seeds、sequence 目标与导演/World/Protagonist prompts。 |
| Character input | `S` 与 active beliefs；不直接接当前 sequence 或 director guidance；另有按候选识别 addressed tension 的公开 prompt。 |
| World model | 以 story beats 表示环境变化；无对象资源层的权威状态执行器，事件/知识判定由 LLM 读故事。 |
| Authority | LLM 识别 challenge/satisfy、强度、belief 支持；LLM 产生候选与 addressed tension ids；程序汇总论文给定分数并 argmax。 |
| Search | 每回合角色 brainstorm 4 个候选动作；通过现有 tension 指向候选，算法选分数最大的候选。 |
| Trigger | sequence 计 beat；平均每 sequence 目标 N=6，超过 N−1 后启动 enforcement（不是独立可达性证明）。 |
| Repair | Director 推断下个 sequence 必需动作/对应 tension；若下一侧是角色则把 required action 加入候选；若世界侧则提示 World 放大 tension；未走所需事件继续 enforcement。 |
| Can change | 新 world beats/tension、角色动作候选与叙事推进；enforcement 可提高特定张力/注入候选。 |
| Cannot change | 作者事实/角色认识并未有硬执行校验；角色候选注入不证明角色真的会执行；无一般不可达检测/有限终止保证。 |
| Handwrite | 高层 sequence、角色 Wr/B、prompt、优先级/张力初始条件；人物/世界文本生成边界仍靠 prompt。 |
| old cost | 有初始角色初始化与提示/故事调整；不是纯自动规划；缺完整可运行源码，实际作者总成本未知。 |
| LLM replace | 从故事文本推理张力/信念、提候选、挑 addressed tension、生成 beat 与 enforcement 方向。 |
| must not replace | 玩家/角色经验真实性、不可见信息过滤、世界成功后果执行；不得把 prompt 禁令当硬 validator。 |
| Eval | 5 prompts、4 配置×3 输出=60；Gemini judge pairwise；人评仅 18 对故事、213 有效答卷；非交互玩家世界执行评估。 |
| Failure | score/decay 公式正负号有歧义；prompt 看完整 beats 与角色可见信息可能不一致；story-length guidance 可混淆成有效世界 steering。 |

算法顺序（论文印刷 pp.379–381 与固定公开 prompts）：

1. Director 用起始 story prompt 生成 sequence 目标；角色初始化 Wr/B，张力从 0 起，形成累计 beats S。
2. 角色张力检查器读 S 与 Wr，为各理想标 challenge/satisfy 及 severity；更新相应 tension ledger。
3. 角色候选生成器读 S、active B，产 4 条候选动作和 belief rationale。
4. 候选筛选 prompt 将候选、张力描述交 LLM，让它返回每条 action 对应的 tension IDs；prompt 不给其权重数值。
5. 程序对每个候选 `a` 依论文正文计算 `score(a)=Σ_{t∈T_a}s_t`，选最高分。Tension 初始化/更新的原文是：challenge severity 取 2/6/10 并带负号、satisfy 取正号；再乘所属 ideal 的权重 0.2/0.6/1.0（正文另称比例 1:2:5，与列值 1:3:5 不一致）。
6. 对处理过的 tensions，论文给出重置值 `s_t=2`，随后描述衰减 `r_t=0.5·exp(−s_t/10)` 与 `s'_t=s_t·(1−r_t)`；没有明说“只衰减未处理项”，重置项是否参与同轮衰减未由实现核实。保留 signed `s_t` 会使负值时 `r_t>0.5`，例如 `s_t=−10 → r≈1.36, s'≈+3.59`；文本没有解释负分是否先取绝对值/翻号/截断。不得自行补充。belief evidence accumulation 是另一路账本，合并/过期及阈值值未充分公开。
7. 角色生成所选动作的 beat，追加到 S；director 交替调度 world/protagonist beat。
8. sequence 平均 beats 超过 N−1 (N=6) 时进入 enforcement：director 找下一 sequence 的 required action/associated tension。
9. 若 next actor=World，则以 prompt 放大对应 tension；若 Protagonist，则把 required action 加入 4 个 brainstorm 候选；未选中则继续引导。

手推例（输入/决策流程可计算，分数来自假设台账，不代表作者程序）：

假设台账里有已存 `T1=-2`、`T2=+6`（这是给定输入，不声称由上述严重度×权重推出），四个候选为 `a=道歉`、`b=追问`、`c=沉默`、`d=离开`；筛选 prompt 假设返回 `a→{T1}`, `b→{T2}`, `c→{}`, `d→{T1,T2}`。按论文 score 直读，四分为 `−2,+6,0,+4`，因此选 `b`。之后被处理的 T2 重置到 2；若它参与同轮衰减，则约为 `2·(1−0.5·exp(−0.2))=1.181`，不参与则仍为 2，排除它的实现依据未核到。T1 直读衰减得 `r≈0.61`, `s'≈−0.78`；输入 `−10` 却得到正数 `+3.59`。这正是 sign/decay 歧义，演算不代表作者程序。若 enforcement 后把另一个 required action 加进四项候选，也只是文本候选注入，不等于经 W 成功执行。

## 用户的新理解（本人待补）

<!-- 仅由用户本人补写；模型不代填。 -->

## 5. NCP-Bench：外部 judge/terminal 协议，不是 controller

| 字段 | 机制底稿 |
|---|---|
| Problem | 压测自由玩家输入下的长程事实、trajectory milestones 与 narrative commitments 一致性。 |
| State | Initial facts（active/negated）、commitments(type/description/satisfaction/violation)、ordered trajectory nodes、history、checker ledger；episode session。 |
| Author input | 电影规格、初始事实、achievement/invariant/ordering commitments、trajectory trigger/key_delta、玩家输入条件。 |
| Character input | Baseline/HiAgent narrator 接自身 prompt 范围内的规格/事实/history/当前输入；统一由 runner 提供 API request。 |
| World model | 叙事文本事实抽取/ledger + trajectory/commitment checker；不是通用游戏 object/action executor。 |
| Authority | 官方 evaluator 判 conflict；若冲突 runner 终止本 turn/episode；否则依次 projection、trajectory checker、commitment checker，再提交状态。 |
| Search | Bench 本身无 plan search；Baseline 按 node/commitment/事实出文本，HiAgent memory/core 是外部 method reference，不改变 judge 的 ownership。 |
| Trigger | 每个 player input 后 narrator.respond→固定 evaluator；opening 有独立 evaluator pending facts；terminal 由 conflict/all achievements/max turns 决定。 |
| Repair | 原协议冲突后不允许改文本再继续冒称官方流程；格式错误的有界重试≠语义冲突后修复。 |
| Can change | narrator 生成回复和方法私有记忆；成功且无 conflict 时 evaluator facts/progress/commitment ledger 更新。 |
| Cannot change | narrator 不能自判无冲突、覆写 benchmark ledger、改原 commitment/trajectory；发生 conflict 不得 external repair 后以原 benchmark survival 计。 |
| Handwrite | StorySpec facts/commitments/trajectory、criteria/prompt，以及方法实现；checker backbone/prompt 也是实验条件。 |
| old cost | 作者需写自然语言电影情境及多类约束；HiAgent 还付检索、子目标、summarization 与模型交互成本；论文 interaction 数不等于人类作者工时。 |
| LLM replace | narrator 可以是 LLM；fixed evaluator/checker 是 benchmark 外部协议组件，研究方法可研究其可靠性但不可让被测者接管自己的 pass/fail。 |
| must not replace | conflict/terminal logic、提交顺序、ledger ownership、原题面的 constraints；不能以改 evaluator 允许 repair 继续却报原得分。 |
| Eval | report conflict categories、survival/terminal 与真实 achievement completion、trajectory progress；同一固定 evaluator 配置下比较，非玩家活人感测量。 |
| Failure | evaluator 是语义模型非逻辑真理；source/prompt/backbone 变动会变协议；survival 不等于完成所有 achievement；不可把 conflict修复与原结果合并。 |

算法顺序（固定源码 runner；不是新 controller）：

1. `start_episode`：narrator.start_episode → 初始化 state → narrator.open。
2. opening evaluator 提出 pending fact updates；opening 文本进 history(turn −1)，updates 暂未提交。
3. 每轮从 committed state 组 NarratorRequest：active facts、commitments、trajectory/current node、history、pending opening、玩家输入。
4. 把 pending opening updates 投影到本轮 audit ledger；调用 `narrator.respond` 得文本。
5. 固定 evaluator 先判 narrator 回复有无 conflict；有则返回原 session，不提交本轮 facts/progress，不调用后两 checker，episode 终止 `CONFLICT`。
6. 无 conflict：投影 response fact updates；trajectory checker 读投影 facts + 加入本轮后的 history，给 milestone assessment。
7. 投影 trajectory assessments；commitment checker 再读更新后 facts/history 与 trajectory，输出 satisfaction/violation assessments。
8. 按次序 commit opening updates → response updates → trajectory/commitment assessments → history。
9. terminal：conflict 则 `CONFLICT`；全部 achievement 满足则 `ALL_RESOLVED`；否则至 100 turns 得 `MAX_TURNS`；随后 close narrator。

手推例（自制小 ledger，顺序按官方 runner）：

固定 evaluator 的首个 TurnEvaluator 检查 narrator response 与 active fact ledger 的事实冲突/玩家输入冲突；ordering/invariant commitment violation 留给后续 CommitmentChecker，不混作这个首检。例：已提交 active fact=`the bridge was destroyed and remains impassable`；trajectory 节点尚未发生、也没有后来修复桥梁的已存事实。narrator 却写“众人沿着原桥完整无损地走了过去，没有修桥或绕行”。该回应与已有 active fact 直接冲突，TurnEvaluator 返回 conflict。runner 不提交本轮抽取出的 added/negated facts，不运行 TrajectoryChecker/CommitmentChecker，session 原样返回并终止 `CONFLICT`。这是外部校验触发原协议 terminal，不是 commitment repair。

ordering 另例：已存事实并不互相矛盾，但 commitment 要求先取得证据再公开身份；response 把两事件顺序写反。这属于 commitment/ordering 检查，不应拿来说明首个 active-fact conflict evaluator。对应检查之后才会有 trajectory/commitment 分析与成功路径提交。

## 用户的新理解（本人待补）

<!-- 仅由用户本人补写；模型不代填。 -->

## 候选组合接口（纯可组合清单，未做选型）

- 条件触发与作者文本：Anansi query-bound reusable instance，或 Drama Llama transcript-condition＋逐条消耗 action；二者状态权威不同，不要混为一种。
- 高层 event 到执行世界：WhatELSE fixed-domain compiler→external execution→critique；可和 Anansi 的作者内容绑定接口并列比较，但该拼接尚未实现/评测。
- 角色状态与引导：DiriGent 的 ideal/tension/belief 候选提议/enforcement 可作为角色侧策略材料；需另配 W/O权限及因果执行，原算法符号未解歧义不补公式。
- 对外判分：NCP runner 作为独立 judge/terminal contract；不把它放在任一候选 controller 内部，不改 conflict 后续流程仍报原 benchmark。
- 任一组合都要逐个标明：提案者、状态读者、W 写入者、独立验证者、失败后权限；这里只留接口，不选最终架构或 research gap。

## 用户的新理解（待补，不由模型代写）

<!-- 留白：由用户本人补充其新理解；模型不代写。 -->
