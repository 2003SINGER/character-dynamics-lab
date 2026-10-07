# 调研子审计：稀疏作者约束、NPC 自主与叙事规划

阅读日期：2026-10-07

范围：Riedl 的 author goals/islands、Mimesis/IN-TALE experience management、IPOCL 与 Sabre。本文只补这条文献支线，不改项目索引、研究状态、代码、模型或实验。

阅读记录：下列四份原件均保存于本机 ignored 来源目录并核了 PDF 页数与 SHA-256；Luna 子代理对 Riedl 2009、Mimesis/IN-TALE 2006、IPOCL 2010、Sabre 2021 原件全文作方法级审读，核对算法、评测/限制及相关附录；父代理对关键段落作选择性复核。关键页渲染检查了 2009 作者约束、Mimesis Director 与 Sabre 搜索算法。原件和哈希见 [manifest_author_goals.json](../outputs/literature_sources/author_constraints_20261007/manifest_author_goals.json)。

## 结论先行

**强威胁：**“作者只规定稀疏的未来世界状态/plot points，把抵达它们的中间过程交给自主角色”不是新概念。更直接的先例是 Riedl & Stern 的 2006 IN-TALE：场景作者以高层 plot points 定义世界状态顺序；NPC 各自从本地自主行为（LAB，如工作、跑腿、购物）中选择并组织活动；一个 Automated Story Director 再以声明式目标指导 NPC，必要时调制、混合或覆盖 LAB。系统可离线用分级修复生成 contingency tree；玩家造成剧情因果链不可继续时，Director 在运行时切换对应预计算分支。Riedl 2009 又把中间状态约束明确形式化为 author goals / islands。这里已经同时有“稀疏剧情点 + 局部角色自主 + 中央作者目标”。

因此，本次材料**不能证明研究 gap**，也不能把“稀疏作者点”本身当作贡献。更窄、尚未查清的区别是：项目想要的更像长期运行的角色—世界模拟，作者允许对角色阶段做有 provenance 的硬变更，并优先经可在世界中成立的事件/行动推动节点；而 IN-TALE 是有界训练场景，常驻一个能看见模拟状态的导演，NPC 还需预写场景专用 NDB，来实现其 goal。这个差别有研究意义的可能，但目前只是待验证的边界描述，不是已成立的原创方法。

**对当前项目的含义：**把“谁拥有世界事实、角色知道什么、作者能用哪种手段干预、硬约束如何保留来源”写成形式化接口，可能比再抽象一遍“自主 vs 控制”更有辨识度。已有文献没有证明项目的长时程、因果来源、角色局部知识、NPC 持续自主或玩家体验效果；这些仍需与更强先例和实验对照，不能从空缺推新颖性。

## 原件和阅读范围

| 原件 | 阅读范围与身份 | 对本题的作用 |
|---|---|---|
| [Riedl, *Incorporating Authorial Intent into Generative Narrative Systems* (2009)](https://cdn.aaai.org/Symposia/Spring/2009/SS-09-06/SS09-06-015.pdf) | AAAI Spring Symposium paper, printed pp. 91–94；4 页全文 | author goal 的形式化定义、islands 关系、两项案例 |
| [Riedl & Stern, *Believable Agents and Intelligent Story Adaptation for Interactive Storytelling* (2006)](https://doi.org/10.1007/11944577_1)；[作者公开全文](https://www.cc.gatech.edu/~riedl/pubs/tidse06a.pdf) | TIDSE 2006 proceedings chapter, pp. 1–12；12 页全文。系统为 IN-TALE / Automated Story Director，沿用 Mimesis 的生成式 drama management，并结合 Façade 的 ABL/PABL agent 行为 | 最强反例：高层 world-state plot points，LAB/NDB、自主活动仲裁、导演干预与 contingency repair |
| [Riedl & Young, *Narrative Planning: Balancing Plot and Character* (2010)](https://doi.org/10.1613/JAIR.2989)；[作者公开全文](https://faculty.cc.gatech.edu/~riedl/pubs/jair.pdf) | JAIR 39, pp. 217–267；算法、实验、局限和计划/QUEST 附录全文 | IPOCL 的 formal problem、intent frame、flaw repair、评测与失败边界；区分它与 author goals |
| [Ware & Siler, *Sabre: A Narrative Planner Supporting Intention and Deep Theory of Mind* (2021)](https://doi.org/10.1609/aiide.v17i1.18896)；[AAAI 正式 PDF](https://cdn.aaai.org/ojs/18896/18896-52-22662-1-2-20211004.pdf) | AIIDE 17(1), pp. 99–106；8 页全文 | Sabre 的输入、belief/utility 语义、搜索和 benchmark/ablation |

书目、下载路径、页数、字节数和 SHA-256 仅以各原件对应的 manifest 条目为准。此处未把同目录中其他研究者保存的 PDF 记进本次 manifest。

## Riedl 2009：author goals / islands 的实际语义

**[论文证据] 输入与状态。**作者向 planning-based narrative generator 提供初始世界、动作库、结局 outcome，以及一组中间 author goals。每个 author goal 是一个或多个状态命题的描述；在 partial-order plan 中被编码为只有前置条件、没有效果的特殊 plan step。系统须让相应世界状态在故事起点和 outcome 之间至少出现一次；若有多个目标，可在初始化时指定先后关系。文中把它称作 islands 的 partial-order 版本：违反必要中间状态的 plan 分支被剪枝（printed pp. 91–92）。

```text
输入：初始世界 I，动作 schema A，最终 outcome G，按偏序排列的作者状态点 L
初始化空 partial-order plan
将每个 l ∈ L 插入为无效果、以状态谓词作条件的 plan step
加入 L 之间作者指定的 temporal links
POCL 搜索动作与因果链；不满足某个 l 的分支不能成为完整解
```

**[论文证据] 这不是一条被作者补齐的剧情轨迹。**Little Red Riding Hood 案例中，作者只在 outcome 之外规定 Little Red 与 Granny 曾经被狼吞下；planner 自行产生吞下、猎人杀狼、逃出等行动，再到结局。第二个军方训练案例里，作者点用于建立角色/语境、促成事件和最终 dilemma；原件称它们有些不直接是结局所必需，却是作者认为重要的 meta-constraint（printed pp. 92–94）。这是“中间状态点 + planner 填过程”的直接先例。

**[论文证据] 时间/可达性。**形式化提供的是目标点顺序和 POCL 因果/时间先后约束，不提供现实钟表上的 deadline、duration、宽限窗口或速率。目标 state 不可达、相互冲突时，文中语义就是不存在满足全部条件的完整计划；没有软化/降级或自动决定哪个目标可牺牲的求解层。具体互动体验管理可以递归重规划，但该短文未定义运行期保证。

**[论文证据] 评价边界。**论文展示两个使用案例和可生成的计划，没有玩家研究、作者工时、运行成本、长期自主模拟或体验质量的对照评测；它支持“这种约束能把要求写进规划输入并剪枝”，不支持“这种方法更可信/更省作者劳动”。

## Mimesis / IN-TALE：稀疏导演与真正存在的局部自主

**[论文证据] 两个 state owner / 行为层。**2006 系统不是完全自主的世界后面再附一个终局 goal，而是把 story director 和角色 agent 分层：

- 游戏引擎运行并向 Automated Story Director 提供模拟状态；Director 保存预期事件/高层情节计划。
- 每个角色的 ABL agent 用自己的 working memory 表示 subjective knowledge；LAB 由角色自行从当前条件/episodic memory 计算 bid，并以加权概率仲裁下一段活动。例子包括工作、跑腿、购物以及开店的子目标序列。
- NDB（Narrative Directive Behavior）是预先编写的场景专用行为，组织成戏剧 beat；Director 给角色下一个 declaration-level world-state goal，角色再通过目标/行为库完成。
- NDB 可以调制、混合或覆盖 LAB；作者还要写 NDB 的 beat goals、交互 handler、与 LAB 的资源需求和中断/退出解释行为。

这说明局部自主**确实存在**：角色有自己的 LAB 选择和活动顺序，用户交互能在活动之间/过程中插入；但它被有界场景里的 unseen over-mind 管理，且每个剧情特有 NDB 仍需作者预先搭建。故不能把它说成纯脚本，也不能说成不受中央剧情规划影响的持久世界自主。

**[论文证据] 节点与运行干预。**高层 plot 以“应该发生的世界状态/场景”表达，不枚举促成它的 primitive character actions；Director 将 plot points 转成 NPC 要采用的 goal。对威胁剧情 causal link 的模拟/玩家事件，系统预先分析可出现的不一致，并生成 contingency branch。生成备选计划采用分级修复：①修 threatened causal link；②删除依赖该 link 的事件并补出保持因果连贯的事件；③仍不可行时重选目标/learning situations 并重建 plan。论文明确这些重规划可离线进行以避免延迟；运行时查表进入对应 contingency，不能把它误写成每次现场从头跑完三层修复。例子用第二个肇事者/第二枚炸弹替换被玩家阻止的路径，也展示被捕角色的状态促成另一种群众冲突剧情（printed pp. 7–9）。

**[项目解释] 它允许的是重规划和 NPC goal directive，不是世界倒带。**所读原件未显示 rewind 或把既成模拟状态回滚；plan 从当前不一致处进入 contingency。论文也没有规定“Director 可直接改 NPC 的 personality/state 字段”。DIRECTOR 指令是 agent-adopted declarative goal，primitive action 由 agent repertoire 中的 NDB/LAB 实现；但是因为 NDB 可以打断、覆盖 LAB，角色自主度并非完全保留。这里的“剧情变成合理”有明确代价：场景专用行为、角色转出/转入行为及目标协调都要被作者编码。

**[未覆盖] Provenance。**论文分别提到引擎状态、Director 的预期 plan、角色主观 WMEs 与 episodic memory，但没有给出统一的事件 provenance contract、由谁写入每个状态变更、强制剧情变化与自然事件如何区分、或历史信息如何限制未来角色 knowledge。不能由此推断它不存在实现；只能说此原件未交代。

**[论文证据] 评价。**IN-TALE 是 3D 引擎上的 prototype，作者报告 contingency tree 超过 1,000 条路径，其中多数是维持叙事一致性的轻微变化（printed p. 9）。这是适应分支规模的描述性证据，不是独立玩家效度、长时程或作者成本比较；论文未报告这些实验。

## IPOCL：因果链加上“人物为什么这么做”

**[论文证据] IPOCL 的正式输入并非 author-goal island 列表。**该 2010 JAIR 论文的 fabula problem 由初始世界、终局 goal situation 与动作 schema 构成。动作 schema 带参与者/intentional actor、前置条件、效果，也可标成非意图性的 happening。IPOCL 的新增信息是 character goals 的表示与产生，不是 author 提供一串稀疏中间状态；2010 文献在 related work 中提到 Porteous & Cavazza 的 partially-ordered landmarks 是 author goals，但那不是 IPOCL 算法本身（§3; §4.1; printed pp. 225–226, 229–231）。

**[论文证据] 搜索对象。**它扩展 least-commitment POCL 的 partial plan（steps, variable bindings, ordering constraints, causal links），并跟踪 frame of commitment：角色、被追求的内部目标、该角色为目标作出的步骤、意图区间与最后一步，以及令其承诺该目标的 motivating step。搜索依次修复三类问题：

1. causal planning：为未满足的 action precondition 新建/复用 action，添 causal link，并处理 causal threat；新 action 可能开启一个意图 frame。
2. motivation planning：为每个 frame 找到 effect 产生 `intends(actor, goal)` 的 motivating step，并把它排在该 frame 的其他动作之前。
3. intent planning：对同一人物因果上先行、但是否服务于该 frame 不明的行动，分支决定纳入/不纳入 frame；不完整或相冲突则继续修复或回溯。

除标注为 happening 的外部/非意图事件外，故事动作都须属于相应角色的 intent frame。流程不是“生成剧情后补一句角色动机”，动机链本身是搜索合法性的条件（§4.2–4.3; printed pp. 229–237）。

**[论文证据] 冲突与失败。**同一人物有互相否定的 goal frame 时可通过排序串行化；更复杂的因果干扰依赖 causal threat resolution 和 backtracking。作者自己指出其识别/修复矛盾意图的机制较弱，有些案例需要额外语义/情境推理（§4.3; pp. 236–237, 243–244）。另外，IPOCL 不能生成角色目标最终失败的叙事：标准规划把不能执行到结局的 branch 剪掉。它可以生成冲突人物，但每个人物最终都成功，冲突依序解决（§6 Conclusions; printed p. 252）。不可达作者点不属于这篇算法的重点；在基础规划语义下无解会导致回溯而非运行时替代/降级。

**[论文证据] 时间与知识边界。**模型是故事 fabula 的离线 partial-order plan；允许的时间关系主要是事件排序与意图区间，未定义 clock-time deadline/window。IPOCL 2010 不建模 actor beliefs/observations，因此它的“行动可解释”不能替代项目的 `O_i` / actor-local knowledge，也不能保证角色只利用自己知道的事实。

## Sabre：作者 utility 与 character utility 同在，但“自主”仍是规划出来的

**[论文证据] 输入。**Sabre 问题包含有限角色、nominal/numeric fluents、动作 precondition/effect/consenting characters/观察条件、自动触发 trigger、初始世界与初始错误信念、作者 utility，以及每个角色自己的 utility。作者与人物 utility 都是条件式状态偏好；作者目标不是强制 ordered milestones，而是 planner 应尽量到达的状态排序/效用。动作被人物观察后按 observation 条件更新 belief；未观察时保持原信念，除非动作效果另行改变（§§3–4; pp. 99–103）。

**[论文证据] 选择过程。**搜索以特殊的 author character、初始 state 和空计划开始；若作者角色 utility 未提升，则选一个当前可执行的动作候选。每个 consenting character 都必须能在其 belief state 中解释此行动：该角色相信行动可做，且它能成为一个让自己 utility 改善的计划的首步。行动被接受后更新状态并递归扩展；完整解须可从初始状态执行、提升作者 utility，且所有角色行动都有解释。角色可持有 arbitrarily nested、错误但确定的 belief；它不建模不确定概率（Algorithm 1, §5; pp. 103–104）。

**[证据/解释] Sabre 的局部自主是 deliberative eligibility，不是运行期独立自治。**每个角色被要求有自己的 utility 与 belief，但论文明确说 narrative planner 是唯一 decision maker，planner 在全局挑选何时/如何让人物行动。它严格控制动作解释性，却没有在游戏运行里放出长期自主 NPC，再让它们按局部 policy 行动；这是 puppetmaster 的 offline centralized plan。触发器是域作者写的“条件一成立就发生”事件，并在逻辑 plan state 中立即应用，不等于独立的 authoritative world-event service。

**[论文证据] 无解处理与成本。**Sabre 可能在无解时不终止，实验中人为设置最大搜索深度；没有 soft-goal relax、节点时间窗或作者可选的 intervention policy。作者也明确承认 fluents/actions/triggers/utility functions 仍需作者定义，规划 domain 难调试；Sabre 不支持 uncertainty（§§5–7; pp. 104–105）。

**[论文证据] 评价。**Sabre 在多个 narrative planning benchmark 报告已 ground/simplify 的 domain 大小、找首解用时、访问/生成节点，并对 full / intention-only / belief-only 解空间做 ablation；作者强调因功能范围不等价，不能作公平的系统优劣横比，也不宣称 benchmark/ablation 等于玩家验证（pp. 104–105）。

## 干预权限逐项对照

| 手段 | 这些原件具体提供什么 | 与项目想法的边界 |
|---|---|---|
| 约束未来节点 | Riedl 2009：state proposition author goals，plan 全程必须曾满足并按作者顺序出现；无效果。Sabre：author utility 引导生成 plan；不是用户定义的里程碑偏序。IPOCL：outcome goal + 角色意图框架。 | “只给点、不画路径”有直接先例；硬点与软偏好不是这些系统统一的作者 schema。 |
| 影响角色 policy/goal | IN-TALE Director 给 NPC 一个声明式世界状态 goal；可编写 NDB 并影响 LAB。Sabre 的 author utility 由 planner 全局优化。 | Mimesis 对角色 autonomy 是最强 threat：目标层干预已存在，且为达到作者场景目标允许混合/覆盖其局部活动。 |
| 直接选择/执行角色 action | IPOCL/Sabre 的产物是完整的角色动作 plan；Sabre 由中央 planner 选择每个 action。IN-TALE Director 给 goal 而由 agent 选择行为，不过 NDB 事先作者化且可覆盖 LAB。 | 没有一个来源证明“纯世界干预比 goal/direct-action puppeteering 更有效”；需要做公平比较，干预权限应作为实验条件。 |
| 直接改 W 或角色持久状态 | Riedl author-goal step 无效果；Sabre action effect 是显式写在 domain 的状态更新；IN-TALE 以 agent goal/behaviors 驱动 simulation state。 | 上述论文未说明由导演直接写 W/个体 state 字段的通用 API，也未声明禁止这种实现。若项目允许作者硬改阶段状态，需单独定义不可混淆的 provenance。 |
| Rewind / 回滚 | IN-TALE 在当前矛盾点进入预生成 contingency plan；其他规划论文搜索/生成动作序列。 | 这些方法不等于回滚世界已发生事实。所读原件未见 rewind；Mimesis 是重新规划/换因果路径。 |

## 对项目需求的逐项核验

| 需求 | 已有工作覆盖到什么 | 仍需项目明确/验证 |
|---|---|---|
| 节点采用何种输入 | Riedl/Mimesis：世界状态命题/plot point。 | 是否允许 event-occurred 点（事实曾经发生）与 state-currently-true 点两种语义；角色 stage change 是否为目标状态还是直接状态赋值。 |
| 谁拥有状态/知识 | Mimesis：引擎 state、导演预期剧情、agent subjective WME/episodic memory 分层。Sabre：单一逻辑 state 中显式嵌套 belief。 | 事件来源与写入主体、时间戳、因果父节点、角色何时可得知事件；人设/状态硬改与自然演化 provenance。论文没有给可直接移植的来源 schema。 |
| 部分序/时间窗 | Author goals 支持作者指定的 milestone order；Mimesis 用情节 event order；POCL/IPOCL 有 causal/order links。 | 精确的 `before/after`, interval, absolute deadline, window tolerance 和动态时间推进都未在以上 author-goal 机制中定义；“later that day”案例叙述不构成可执行时间窗算法。 |
| 冲突/不可达 | Riedl 2009/IPOCL：在搜索中剪枝/回溯；Sabre：深度上限截断；Mimesis：换因果链、删依赖事件/补事件、最后重选目标。 | 需定义冲突报告，及 hard/soft priority、谁可降级、何时允许改写未来节点、如果 hard 点不可能是否停止/请求作者修正。不可把宽松的“最终总能到结局”当保证。 |
| 局部自主 | Mimesis 的 LAB bid + weighted probability，真实角色自己的活动序列/subjective memory 是代码可实现的局部自主；NDB 与 central goal director 会覆盖/重排。IPOCL/Sabre 只要求计划动作具人物意图解释。 | 要区分运行时局部行为选择、全局 offline 规划生成、和玩家观察到的自主感；不能把这三种 autonomy 混为一个指标。 |
| 因果合理和经验质量 | Mimesis 用因果链威胁识别和 contingency branch；IPOCL 有读者 goal-comprehension 实验。 | 没有研究证明“玩家看起来合理”或“允许硬改角色阶段仍可信”；需要独立玩家或严谨的盲评情境对照。 |

## 评价：原件有什么证据，项目若继续要测什么

**已有证据：**

- Riedl 2009（printed pp. 91–94）：计划案例展示，未作受控效果评价。
- IN-TALE（printed pp. 8–11）：原型报告 1,000+ contingency paths，并演示剧情改道；没有报告玩家实验、作者效率或长期 world-sim 指标。
- IPOCL（§5, printed pp. 245–251）：32 名北卡州立 CS 本科生随机进入 IPOCL/POCL 两组，读 Aladdin 生成故事后评 question-answer goodness；IPOCL 条件“good”问答均值 3.1976 vs POCL 2.9912（one-tailed p < 0.0585），对“poor”问答 IPOCL 1.1898 vs POCL 1.2969（p < 0.05）。论文承认 IPOCL 文本更长且 discourse planner 额外显式写出意图，两个混淆未被控制。此评测支持特定静态叙事文本的目标理解度，不能转成玩家操控 NPC、自主世界、冲突恢复或 author time 收益。
- Sabre（§6, printed pp. 104–105）：报告规划求解规模、耗时、节点数与解空间 ablation；作者明确说缺乏与功能不同系统的直接比较，且不是玩家体验结论。

**[项目解释] 若未来对这条候选做小型可证伪比较，最少应把机制拆成可观察条件：**在同一场景/角色/行为预算下比较①无作者 steer 的局部自主；②Riedl 式硬 milestones + 中央完整 planning；③Mimesis 式 NPC goal directive + LAB/NDB；④项目提出的有来源限制的 world/event intervention。记录 hard-node 满足率和时间窗错失、干预次数/类型、角色行动由何处决定、直接状态改写比例、世界/知识因果违规、被迫改路次数、作者编写/修补 NDB 与规则的时间；玩家盲评需把“情节到点”“行动有角色动机”“先前事实解释当前行为”拆开问。先用合成反例验证评测能识别无因跳变、错误知道与可解释的失败/偏离，再招募/评体验。这里只是**项目决定候选**，不是已获批实验或文献结果。

## Strong threat / Gap 状态

| 说法 | 当前判定 |
|---|---|
| “作者不必写全轨迹，只列几个中间世界状态，planner 填路径” | **明确已有先例**：Riedl 2009 author goals；Riedl & Stern 2006 high-level plot points + autonomous agents。不可宣称 novelty。 |
| “节点中间留给自主 NPC 自己生活，作者只在必要时往下发 goal” | **强近邻**：IN-TALE 的 LAB/NDB + Director 正是该组合；区别限于故事中心的 scenario director、对 NDB 的作者投入、时间尺度/状态来源尚未证明。 |
| “作者可规定某个条件后角色发生硬阶段变化” | author goals 可要求某 world state 必须出现，但不直接产生效果。Mimesis 的 Director goal 由行为库达成；论文没有展示 director 直接赋值角色状态。此机制差异还要以具体 state/provenance 合约比较，不能称“无人做过”。 |
| “主要以合法世界事件促成节点，而非直接控制角色动作” | 文献中 Mimesis 通过演员的行为目标/情节专用行为推动 state；Sabre/IPOCL 是中央规划；没有在本轮来源中找到对‘干预权限如何影响持续世界自治’的同构对照。**这只是本次小范围检索结果，不是 gap 证明。** |
| “world-centric 长时程、事件有出处、actor-local knowledge、作者强制转变可审计” | 这些特征在所读原件没有联合评测/统一数据模型。需扩大文献查新，并检索 character-based plot management、simulation-first emergent narrative、story sifting 等近邻后才可判断研究 gap。 |

## 结论边界与下一步

本轮最重要的校正是：**“稀疏轨迹约束 + 自主角色/世界 + 目标导向的剧情管理”至少在 2006 IN-TALE/Mimesis 系统脉络中已有强组合先例。**项目可继续探索，但要把问题从“是否只写几个节点”收窄为节点的状态语义、actor-local provenance、授权的干预粒度、持久世界运行、硬约束与不可达处理，以及这些设计是否能同时保持角色行为可读与减少剧情专用作者劳动。

尚未判断：

- IN-TALE 对应的大量真实 agent state 和当时 Mimesis runtime 的精确版本/性能，需查看 Mimesis 专门实现论文/系统文档；本文按 2006 原件描述，不外推成游戏生产系统。
- 新近 character-based story management（如 Shepherd）与 2005–2025 landmark-guided/event-sequence planner 是否已覆盖上述全部差异，需要独立的全文原件交叉查新；不以摘要排除威胁，也不凭摘要确认算法。
- 本项目 proposal 中允许的 author stage change、世界事件权限、角色当前动作如何中断，以及由谁决定“最小必要介入”，仍是设计决策，本文不冻结或实现它们。

**后续建议（仅一项）：**先把用户想要的硬节点/软节点/禁止状态/角色阶段变化各举一个有起因与来源的微型例子，再以它们为检索题干查 character-based plot management 和 emergent narrative 的原始算法；继续维持 `UNCERTAIN`，直到逐篇对齐 actor/state owner、授权干预、阶段偏序/窗口、无解恢复和运行时局部自主。当前不据本审计启动实验或修改系统。
