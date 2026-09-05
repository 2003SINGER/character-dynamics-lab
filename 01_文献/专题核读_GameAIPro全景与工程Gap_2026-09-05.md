# 专题核读：Game AI Pro 全景与"为什么没有游戏这么做"

核读日期：2026-09-05
核读人：WorkBuddy（定向核读，非全文精读）
驱动问题：用户问「既然 2005–2013 年就有这些技术，为什么没有一个游戏有这么厉害的 NPC？肯定有 gap。」

**本页的立场**：gap 确实存在，但**不是"没人想到"或"做不到"**。已核读的证据显示，业界**知道怎么做、做过、并且在多数情况下主动放弃了**，而且把放弃的理由写下来了。这个语料库的价值主要不是"可搬的机制"，而是**一份 149 章的、带理由的负面结果库**。

---

## 0. 可复现性与语料规模

| 项 | 值 |
|---|---|
| 来源 | `https://www.gameaipro.com/`（官网免费 PDF，全系列） |
| 抓取时间 | 2026-09-05 |
| 卷册 | Game AI Pro（2013，V1）47 章 / Vol 2（2015）40 章 / Vol 3（2017）42 章 / Online Edition 2021（OE21）17 章 |
| 总章数 | **146 章**（官网宣称 149，目录实列 146） |
| 学术索引状态 | **不在任何学术索引内**。Web of Science / Scopus / DBLP / arXiv 均不收录，Google Scholar 基本检索不到 |
| 本次已下载 | 34 章（8 章 gap 关键 + 26 章 A 级），全部 `%PDF-` 校验通过 |
| 文本提取 | `pdftotext -enc UTF-8 -layout`，缓存于 `tmp/gameaipro/txt/` |
| 完整分级清单 | 见 §5 附录（146 章全列，A/B/C） |

### 分级标准

| 级 | 判据 | 数量 | 处理方式 |
|---|---|---|---|
| **A** | 直接涉及角色知识/信念、主观视图、效用决策架构、心理学、承诺与规划、可相信性评价 | 43 | 定向核读（提取与项目机制直接对应的段落，不逐页精读） |
| **B** | 通用架构、可调试性、规模优化，可能含可搬模式 | 30 | 暂缓，仅在 A 级出现缺口时回查 |
| **C** | 寻路、转向、人群、赛车、摄像机、GPGPU、动画驱动、MCTS/极小极大、载具 | 73 | **不读**。与 W→O→X→S→D→π(A)→W′ 无对应关系 |

**回答用户的问题"你能全部精读吗"**：技术上能，但全精读是错的策略。73 章讲寻路和赛车 AI，读了不产生任何东西。正确做法是 A 级定向核读 + B 级按需回查 + C 级不读。**A 级 43 章已下载 34 章，剩 9 章为本次已核读过的旧下载（Utility Ch09、Reactivity Ch11、HTN Ch12、ETQ Ch33、CiF Ch43、Dual-Utility V2C03、Possibility Maps V2C07、Smart Zones V2C11、Talk of the Town V3C37）计 9 章，合计 43 章全部到位。**

---

## 1. 六个 gap：为什么技术存在、游戏没有

### Gap 1（最硬的一条）：优化目标是玩家感知，不是内部保真度

**这不是"做不到"，是"做出来没用"。**

Rabin, *The Illusion of Intelligence*（V3 C01）§1.1：

> "Game AI is seldom about any deep intelligence but rather about the **illusion of intelligence**. Often we are trying to create believable human behavior, but the actual intelligence that we are able to program is fairly constrained and painfully brittle."
>
> "if expectations are not properly managed, then **even truly human-level intelligent behavior might be perceived as incompetent** and decidedly nonhuman."

§1.3.6 是**对项目核心前提最直接的一次冲撞**，必须逐字记录：

> "Some programmers have this **weird obsession** with trying to get game AI to **simulate emotions**. This seems to stem from the belief that if an AI was truly sad, angry, or happy, then maybe it might finally convince players that some deep kind of intelligence was actually there. ... **Without simulating everything that makes up human-level intelligence, this approach for the purposes of games appears misguided.**"
>
> "**Players can only see an AI's behavior, not what is being simulated.** If you want to make an AI appear emotional, then directly show that specific emotion in the correct situations."

**判定**：对本项目而言，这一条是**双向的**。

- 若项目的价值主张是"内部状态 S 让 NPC 更 believable" —— **被业界明确否定**。原文用的词是 weird obsession / misguided，且理由不是技术不可行，是"完整的类人智能缺了任何一块，模拟出来的情绪都不会渗透出来"。
- 若项目的价值主张是"内部状态让行为**可预测、可干预、可评测**" —— 不与本条冲突，因为那是另一条评价线。

§1.3.5 还给出一条必须警惕的术语冲突，见 §3。

### Gap 2：评价标准是 fairness 与 fun，不是 fidelity

Zielinski / Innes, *Knowledge is Power*（OE21 C04）§5.3 先用一句话承认了深度的价值：

> "The more entity specific data knowledge we track, the more complex and believable we can make our agents behavior."

紧接着给出相反的指导原则：

> "The key is to have access to the **minimum amount of information** to allow the agents to make decisions according to their design in the game."

这不是自相矛盾，是**成本收益判断**。同一章给出的取舍理由是**玩家公平性**而非真实性——L 形走廊警报的例子：

> "From the player's point of view, it would be **unfair** for the hidden agent to activate the alarm based on secondhand information. It would be better for the first agent, who can actually see the player first hand, to run for the alarm."

**判定**：业界主动限制了 `O` 的深度，理由是"信息更全会让玩家觉得不公平"。**真实性与公平性冲突时，公平性赢。** 本项目若在 `O` 上追求保真度，不能默认"更真 = 更好"。

同一章 §5.1.1 给出了业界标准的 `O` 究竟有多薄：

```c
struct TargetInfo
{
     targetEntity
     isTargetVisible
     lastKnownPosition
}
```

并直言 "Action games typically do not require a lot of target knowledge."

**这是 gap 最刺眼的量化对照**：Talk of the Town 的 belief facet 有 `Predecessor / Parents / Evidence / Strength / Accuracy` 五元组加 11 类证据类型学；而 2021 年 shipped game 的标准答案是 **3 个字段**。两者相差 8 年，且后者引用了前者的同一批作者（本章引 Mateas 13）。**不是不知道，是不采用。**

### Gap 3：内容与"词汇"瓶颈——内部状态再好也表达不出来

Rabin V3 C01 §1.3.2 提出 **vocabulary of the AI** 概念：

> "Let us call this the **vocabulary of the AI**. The vocabulary consists of every dialog clip, every grunt, every animation, every movement, and every interaction. Imagine that an AI character had only two sound clips (an attack grunt and a death cry) and had only four animations (idle, walk, attack, and die). ... **There is virtually no way you can convey a deeply intelligent AI with such a limited vocabulary.**"

§1.3.2 还记录了 F.E.A.R. 战斗对话的真相（与 GOAP 2006 互相印证）：

> "The surprising thing was that this was all **smoke and mirrors**. An AI module simply monitored what was happening and called for these dialog moments as they fit the moment (Orkin 2015)."

**判定**：这是**表达带宽**的硬约束，且它解释了本轮调研中一个原本困惑的现象——**为什么"厉害的 NPC"最先出现在文字/对话场景（AI Dungeon、CharacterBox、SOTOPIA）而不是 3A 动作游戏。** 自然语言是近乎无限的词汇表，动作游戏受制于动画与配音资产。

`[项目推测]` 这一条对本项目是**有利的**：项目的动作空间是文本/结构化动作，天然不受 vocabulary 约束。但这也意味着，**项目不能拿 3A 游戏的 NPC 作为"基线很弱"的论据**——那不是它们 AI 差，是它们表达不了。

### Gap 4：规模与深度互斥，且业界在冲突时主动选规模

Zubek, *1000 NPCs at 60 FPS*（V3 C34）是本次最有价值的一篇，因为它记录了**一次主动放弃**，并写明理由。

先排除性能解释——**planner 的性能是超预期的**：

> "Once implemented, **the planner's performance exceeded expectations**."
>
> "We ended up switching away from planning for a **reason unrelated to performance**."

真正的理由（§34.2.2）：

> "we realized that **by employing planning, we were working on the wrong level of abstraction**. We were authoring individual planning steps and trying to figure out how to turn them turn into the right behaviors at runtime—but what we actually wanted to do, was to author peoples' entire daily routines at a high level, so that we could have **strong authorial control** over when things happened and how they varied."

以及规模理由（同一节）：

> "We realized that we wanted to have our NPCs live very stereotyped, routinized lives—they should be **pretty predictable, because there were too many of them in the building for the player to care about them in detail**."

还有一条对 GOAP/HTN 类规划的冷峻观察（§34.2.1）：

> "with the relatively small number of NPC types living fairly stereotyped lives, **only a handful of distinct plans actually got created and then cached**, so the planner only had to run that many times during the course of the game."

**判定**：这是**对"通用机制"路线的一次实证反驳**。规划器跑得动、也够快，但因为 NPC 生活刻板，实际只生成了"少数几个不同的计划"。**通用机制的复杂度，在刻板场景下是纯浪费。**

配套的规模数据（SHPE 2014 §1，上一轮已记，此处合并）：计划长度 ≤4、NPC <12、约 1 计划/秒。

`[项目推测]` **本项目应主动把自己放在"NPC 数量少（1–10）+ 玩家真的在乎细节"的区间。** 那个区间里，Gap 4 不成立，深度建模才有需求。这也和上一轮"S 该赢的区间是长程、多角色、干预反事实"的判断一致，但需要补一条：**必须是少角色**。多角色 + 刻板生活 = 不需要深度。

### Gap 5：Authoring 成本与可调试性——维度与参数全靠人工，且人工方法不可复现

Dill, *Choosing Effective Utility-Based Considerations*（V3 C13）§13.5：

> "Selecting a response curve can be difficult. ... **the vast majority of the response curves used in the game are chosen from a small palette of preset curves.** Permitting arbitrary curves is immensely powerful but has the substantial drawback of being **intimidating and possibly even unintuitive**."

§13.5.1 给出**维度选择的方法**——请注意它是纯人工的：

> "Although the options may seem overwhelming at first, it helps to do a little bit of **applied role-play**. ... **Put yourself in the character's shoes**, so to speak, and think about why you would (or would not!) want to decide to do a particular action. **Distill these reasons into concrete metrics.**"

与上一轮的两条合并看：
- Utility 2013 §9.5.4：折点位置 = "hand-tune a bunch of 2D points"，即**手工调参、任意设定**。
- C13 §13.5：任意曲线"intimidating and unintuitive"，实际只用一个**小的预设曲线调色板**。

**判定**：`X` 的维度选择与 `U_k` 的参数设定，在工业实践里是**设计师代入角色想象出来的（applied role-play），不可复现、不可扩展、无对照**。

这一条对本项目**既是威胁也是机会**：

- **威胁**：Q01 若坚持正态 ±1σ/±2σ 折点，其性质与"hand-tune 2D points"完全相同，只是换了个参数来源——而业界已经承认这种做法 arbitrary。
- **机会**：**LLM 做 appraisal 的最强定位，是"替代设计师的 applied role-play"**，把维度选择从人工代入变成可复现、可扩展、可对照的过程。这比"LLM 让 NPC 更聪明"扎实得多，而且**T20 的等维度对照消融正是在测这件事**：theory-S vs naive-S，测的就是"理论维度是否优于随手选的等维度"。

### Gap 6：没有评价协议——业界从没测过"下一行为预测准确率"

Carlisle, *Psychologically Plausible Methods for Character Behavior Design*（V2 C38）是标题最像本项目的、内容最不像的一章。它讲的全是**玩家心理学**——如何用心理学操纵玩家对 NPC 的解读，而不是建模 NPC 的内部状态：

> "The aim of this chapter is to encourage you to think about this aspect of your behavior design and to ground you in a sample of the **psychological aspects that come into play from the player's perspective**."

且作者自己给了免责声明：

> "As psychology is a very complex field, it is recommended that these studies **not be taken at face value**"

（本章引用的实证研究均为 Bolton 大学本科生的未发表课程作业。）

§38.5 给出一个对本项目有直接杀伤的观察：

> "most players chose characters **not based on their narrative delivery method, but instead on a measure of perceived usefulness in the game**. In essence, they had **ignored the 'character' of the choice** and had instead chosen based on the **utility value**."

**判定**：两个后果。

1. **玩家自己把 NPC 当机制而非角色**。这与 Gap 1 呼应，但更狠：不是开发者偷懒，是**玩家不在乎**。
2. **"心理学"在 Game AI Pro 里的默认含义是玩家心理学，不是角色心理学**。本项目的文献引用必须显式区分这两者，否则会被误读为同类工作。

关于评价协议：已核读的 34 章中，**没有任何一章以"下一行为预测准确率"为指标**。验收方式是 playtest、QA、fun、以及 C38 说的"adding methods of evaluation"（评价玩家感知，不是评价 NPC 模型）。

---

## 2. LLM 打破了哪几条，没打破哪几条

这是本页对项目定位最直接的推论。

| Gap | 内容 | LLM 是否打破 | 依据 |
|---|---|---|---|
| 1 | 目标是玩家感知，不是内部保真 | **未打破** | 玩家依然只看得到行为；C01 §1.3.6 的论证不依赖技术能力 |
| 2 | 公平性优先于保真度 | **未打破** | 这是设计选择，不是能力限制 |
| 3 | 表达词汇瓶颈 | **已打破** | 自然语言/结构化动作近乎无限词汇；3A 的动画配音瓶颈不存在 |
| 4 | 规模与深度互斥 | **部分打破** | 降低了单角色 authoring 成本，但"上千 NPC 时没人在乎细节"仍然成立 |
| 5 | Authoring 成本与可调试性 | **已打破（最显著）** | 维度选择与参数不必 hand-tune；但可调试性可能**变差**，见下 |
| 6 | 无评价协议 | **无关** | 这是本项目自己要建的东西，不是被打破的对象 |

**关键推论**：LLM 打破的是**成本与带宽**（Gap 3、5），**没有打破的是需求与取舍**（Gap 1、2、4）。

因此，本项目的价值主张如果写成"用 LLM 做出更 believable 的 NPC"，会同时撞上 Gap 1（业界明确否定）和 Gap 4（规模下无需求）。如果写成"**把 authoring 成本降一个量级，从而第一次能系统评测这些内部表示的预测质量**"，则：

- 不与 Gap 1 冲突（走的是可预测/可评测线，不是 believability 线）
- 直接填补 Gap 6（评价协议确实没人做）
- 对 Gap 5 给出可检验的替代（LLM 的维度选择 vs 设计师的 applied role-play，可对照）

`[待用户确认]` 这是**定位建议，不代决**。但它影响 T13（问题卡）怎么写，建议尽快拍。

---

## 3. 一个必须处理的术语冲突：personality

Rabin V3 C01 §1.3.5：

> "Because personality has such power and influence, a carefully crafted personality can convincingly convey **there is something beneath the surface of your characters, whether there is or not**. Personality can be used as a **shell** around your character to imply humanistic qualities that are simply an illusion."
>
> "In addition, a strong personality goes a long way to **covering up any inconsistencies in the behavior or logic of a character**. Strong personalities can be irrational and unpredictable, allowing incredible leeway in how players might critique their actions."

**这是同一个词的两种截然相反的用法**：

| | 业界用法（C01 §1.3.5） | 本项目用法（P） |
|---|---|---|
| 作用 | 掩盖机制的不一致 | 驱动机制 |
| 是否可推理 | 不需要，是外壳 | 必须是参数，可被 U_k 消费 |
| 与行为的关系 | 为不一致提供豁免 | 应产生一致的行为倾向 |
| 验证方式 | playtest | held-out 预测、干预 |

**判定**：项目的任何对外表述里，`P` 必须显式与"projected personality shell"区分。否则审稿人或读者会按业界默认含义理解，认定本项目做的就是"用个性掩盖不一致"——**与本意正好相反**。

同一节还有一条与 Q07 相关的观察：业界认为"strong personalities can be irrational and unpredictable, allowing incredible leeway in how players might critique their actions"。**这与项目要的"P 固定、行为可预测"是相反的设计哲学**，需要显式声明立场。

---

## 4. 对现有 Q / T 的影响

| 对象 | 影响 | 出处 |
|---|---|---|
| R01（预测充分性） | **得到一条支持性旁证**：业界从没测过预测准确率，说明该协议确实空白；但也说明**没有现成的失败案例可引** | Gap 6 |
| Q01 分段响应 | **又一条反面证据**：任意响应曲线被业界评为 "intimidating and possibly even unintuitive"，实际只用预设调色板。正态折点属于 arbitrary 参数来源 | C13 §13.5 |
| Q09 维度选择 | **拿到对照物**：业界的维度选择方法是 applied role-play（设计师代入角色想）。**T20 测的本质是"理论维度 vs applied role-play 等维度"** | C13 §13.5.1 |
| Q07 Commitment | 业界用 personality 掩盖不一致，与"P 固定、行为可预测"相反；需显式声明立场 | C01 §1.3.5 |
| Q05 / Q06 | 无新增 | — |
| T13 问题卡 | **需先定位**：NPC 数量必须少（1–10），场景必须是玩家在乎细节的；否则 Gap 4 成立，深度建模无需求 | C34 §34.2.2 |
| T18 查新 | 分级清单（§5）可作为查新的覆盖证据；73 章 C 级不读须在查新报告里显式声明为"已排除并说明理由" | §0 |
| T23 | 已完成 A 级 43 章下载；T23 应改写为"A 级定向核读"而非"扩覆盖" | §0 |

---

## 5. 证据边界（必须随引用一起保留）

1. **非同行评审**。全部 146 章为行业书籍章节，无同行评审流程，无统计检验要求。
2. **C38 的实证基础是本科课程作业**。作者本人明言 "not be taken at face value"，且研究未发表。**不得作为心理学证据引用**，只能作为"业界如何使用心理学"的证据。
3. **C34 是单一团队的单项目经验**（SomaSim, Project Highrise，2D 精灵、管理模拟类）。其"放弃规划"的结论对 3A 动作游戏未必成立。
4. **C01 是主编的立场章**，代表的是 Game AI Pro 系列的整体倾向，不代表所有从业者。
5. **本次 A 级 43 章中仅 8 章做了逐节核读**（C01、C13、C34、C38 V2、C35、C36 V1、OE21 C04，加部分 C13）。其余 35 章已下载、已提取文本，**尚未核读**。本页所有结论仅基于已核读部分。
6. **§2 的"LLM 打破了哪几条"是推论，不是文献结论**。语料库全部成文于 2013–2021，早于 LLM 角色模拟的兴起，文中没有任何关于 LLM 的讨论。该节所有判断均为 `[项目推测]`。
7. **B 级 30 章、C 级 73 章未读**。C 级不读的理由已在 §0 声明；B 级未读是本次的资源取舍，不是判定为无关。

---

## 附录：146 章分级清单

A = 定向核读（43）｜B = 按需回查（30）｜C = 不读（73，寻路/转向/人群/赛车/摄像机/动画/MCTS 等）
| 章节 | 级 | 标题 |
|---|---|---|
| V1 C01 | C | What is Game AI |
| V1 C02 | B | Informing Game AI Through the Study of Neurology |
| V1 C03 | C | Advanced Randomness Techniques for Game AI |
| V1 C04 | A | Behavior Selection Algorithms |
| V1 C05 | C | Structural Architecture Common Tricks of the Trade |
| V1 C06 | C | The Behavior Tree Starter Kit |
| V1 C07 | C | Real-World Behavior Trees in Script |
| V1 C08 | C | Simulating Behavior Trees |
| V1 C09 | A | An Introduction to Utility Theory |
| V1 C10 | A | Building Utility Decisions into Your Existing Behavior Tree |
| V1 C11 | A | Reactivity and Deliberation in Decision-Making Systems |
| V1 C12 | A | Exploring HTN Planners through Example |
| V1 C13 | B | Hierarchical Plan-Space Planning for Multi-unit Combat Maneuvers |
| V1 C14 | B | Phenomenal AI Level-of-Detail Control with the LOD Trader |
| V1 C15 | C | Runtime Compiled C++ for Rapid AI Development |
| V1 C16 | C | Plumbing the Forbidden Depths Scripting and AI |
| V1 C17 | C | Pathfinding Architecture Optimizations |
| V1 C18 | C | Choosing a Search Space Representation |
| V1 C19 | C | Creating High-Order Navigation Meshes through Iterative Wavefront Edge Expansions |
| V1 C20 | C | Precomputed Pathfinding for Large and Detailed Worlds on MMO Servers |
| V1 C21 | C | Techniques for Formation Movement Using Steering Circles |
| V1 C22 | C | Collision Avoidance for Preplanned Locomotion |
| V1 C23 | C | Crowd Pathfinding and Steering Using Flow Field Tiles |
| V1 C24 | C | Efficient Crowd Simulation for Mobile Games |
| V1 C25 | C | Animation-Driven Locomotion with Locomotion Planning |
| V1 C26 | C | Tactical Position Selection |
| V1 C27 | C | Tactical Pathfinding on a NavMesh |
| V1 C28 | C | Beyond the Kung-Fu Circle A Flexible System for Managing NPC Attacks |
| V1 C29 | C | Hierarchical AI for Multiplayer Bots in Killzone 3 |
| V1 C30 | B | Using Neural Networks to Control Agent Threat Response |
| V1 C32 | A | How to Catch a Ninja NPC Awareness in a 2D Stealth Platformer |
| V1 C33 | A | Asking the Environment Smart Questions |
| V1 C34 | A | A Simple and Robust Knowledge Representation System |
| V1 C35 | A | A Simple and Practical Social Dynamics System |
| V1 C36 | A | Breathing Life into Your Background Characters |
| V1 C37 | A | Alibi Generation Fooling All the Players All the Time |
| V1 C38 | C | An Architecture Overview for AI in Racing Games |
| V1 C39 | C | Representing and Driving a Race Track for AI Controlled Vehicles |
| V1 C40 | C | Racing Vehicle Control Systems using PID Controllers |
| V1 C41 | C | The Heat Vision System for Racing AI |
| V1 C42 | C | A Rubber-Banding System for Gameplay and Race Management |
| V1 C43 | A | An Architecture for Character-Rich Social Simulation |
| V1 C44 | A | A Control-Based Architecture for Animal Behavior |
| V1 C45 | C | Introduction to GPGPU for AI |
| V1 C46 | B | Creating Dynamic Soundscapes Using an Artificial Sound Designer |
| V1 C47 | C | Tips and Tricks for a Robust Third-Person Camera System |
| V1 C48 | A | Implementing N-Grams for Player Prediction Proceedural Generation and Stylized AI |
| V2 C01 | C | Game AI Appreciation Revisited |
| V2 C02 | A | Combat Dialogue in FEAR The Illusion of Communication |
| V2 C03 | A | Dual-Utility Reasoning |
| V2 C04 | A | Vision Zones and Object Identification Certainty |
| V2 C05 | A | Agent Reaction Time How Fast Should An AI React |
| V2 C06 | C | Preventing Animation Twinning Using a Simple Blackboard |
| V2 C07 | A | Possibility Maps for Opportunistic AI and Believable Worlds |
| V2 C08 | A | Production Rules Implementation in 1849 |
| V2 C09 | A | Production Systems New Techniques in AAA Games |
| V2 C10 | B | Building a Risk-Free Environment to Enhance Prototyping |
| V2 C11 | A | Smart Zones to Create the Ambience of Life |
| V2 C12 | C | Separation of Concerns Architecture for AI and Animation |
| V2 C13 | B | Optimizing Practical Planning for Game AI |
| V2 C14 | C | JPS Plus An Extreme A Star Speed Optimization for Static Uniform Cost Grids |
| V2 C15 | C | Subgoal Graphs for Fast Optimal Pathfinding |
| V2 C16 | C | Theta Star for Any-Angle Pathfinding |
| V2 C17 | C | Advanced Techniques for Robust Efficient Crowds |
| V2 C18 | C | Context Steering Behavior-Driven Steering at the Macro Scale |
| V2 C19 | C | Guide to Anticipatory Collision Avoidance |
| V2 C20 | C | Hierarchical Architecture for Group Navigation Behaviors |
| V2 C21 | C | Dynamic Obstacle Navigation in Fuse |
| V2 C22 | C | Introduction to Search for Games |
| V2 C23 | C | Personality Reinforced Search for Mobile Strategy Games |
| V2 C24 | C | Interest Search A Faster Minimax |
| V2 C25 | C | Monte Carlo Tree Search and Related Algorithms for Games |
| V2 C26 | B | Rolling Your Own Finite-Domain Constraint Solver |
| V2 C27 | A | Looking for Trouble Making NPCs Search Realistically |
| V2 C29 | C | Escaping the Grid Infinite-Resolution Influence Mapping |
| V2 C30 | C | Modular Tactical Influence Maps |
| V2 C31 | B | Spatial Reasoning for Strategic Decision Making |
| V2 C32 | C | Extending the Spatial Coverage of a Voxel-Based Navigation Mesh |
| V2 C33 | A | Infected AI in The Last of Us |
| V2 C34 | A | Human Enemy AI in The Last of Us |
| V2 C35 | A | Ellie Buddy AI in The Last of Us |
| V2 C36 | A | Realizing NPCs Animation and Behavior Control for Believable Characters |
| V2 C38 | A | Psychologically Plausible Methods for Character Behavior Design |
| V2 C39 | B | Analytics-Based AI Techniques for a Better Gaming Experience |
| V2 C40 | B | Procedural Content Generation An Overview |
| V2 C41 | A | Simulation Principles from Dwarf Fortress |
| V2 C42 | A | Techniques for AI-Driven Experience Management in Interactive Narratives |
| V3 C01 | A | The Illusion of Intelligence |
| V3 C02 | B | Creating the Past Present and Future with Random Walks |
| V3 C03 | B | Logging Visualization in FINAL FANTASY XV |
| V3 C04 | A | Player Perception of AI Opponents |
| V3 C05 | C | Six Factory System Tricks for Extensibility and Library Reuse |
| V3 C06 | C | Debugging AI with Instant In-Game Scrubbing |
| V3 C07 | B | How to Build Robust AI for Your Game |
| V3 C08 | B | Modular AI |
| V3 C09 | B | Overcoming Pitfalls in Behavior Tree Design |
| V3 C10 | C | A Reactive AI Architecture for Networked First-Person Shooter Games |
| V3 C11 | B | A Character Decision-Making System for FINAL FANTASY XV by Combining Behavior Trees and State Machines |
| V3 C12 | B | A Reusable Light-Weight Finite-State Machine |
| V3 C13 | A | Choosing Effective Utility-Based Considerations |
| V3 C14 | B | Combining Scripted Behavior with Game Tree Search for Stronger More Robust Game AI |
| V3 C15 | C | Steering against Complex Vehicles in Assassin’s Creed Syndicate |
| V3 C16 | C | Predictive Animation Control Using Simulations and Fitted Models |
| V3 C17 | C | The AI of Driver San Francisco |
| V3 C18 | C | A Unified Theory of Locomotion |
| V3 C19 | C | RVO and ORCA How They Really Work |
| V3 C20 | C | Optimization for Smooth Paths |
| V3 C21 | C | 3D Flight Navigation Using Sparse Voxel Octrees |
| V3 C22 | C | Faster A Star with Goal Bounding |
| V3 C23 | C | Faster Dijkstra Search on Uniform Cost Grids |
| V3 C24 | C | Being Where It Counts Telling Paragon Bots Where to Go |
| V3 C25 | C | Combat Outcome Prediction for Real-Time Strategy Games |
| V3 C26 | B | Guide to Effective Auto-Generated Spatial Queries |
| V3 C27 | A | The Role of Time in Spatio-Temporal Reasoning |
| V3 C28 | C | Pitfalls and Solutions When Using Monte Carlo Tree Search for Strategy and Tactical Games |
| V3 C29 | B | Petri Nets and AI Arbitration |
| V3 C30 | C | Hierarchical Portfolio Search in Prismata |
| V3 C31 | A | Behavior Decision System Dragon Age Inquisition’s Utility Scoring Architecture |
| V3 C32 | B | Paragon Bots A Bag of Tricks |
| V3 C33 | C | Using Your Combat AI Accuracy to Balance Difficulty |
| V3 C34 | A | 1000 NPCs at 60 FPS |
| V3 C35 | A | Ambient Interactions Improving Believability by Leveraging Rule-Based AI |
| V3 C36 | A | Stochastic Grammars Not Just for Words |
| V3 C37 | A | Simulating Character Knowledge Phenomena in Talk of the Town |
| V3 C38 | A | Procedural Level and Story Generation Using Tag-Based Content Selection |
| V3 C39 | B | Recommendation Systems in Games |
| V3 C40 | C | Vintage Random Number Generators |
| V3 C41 | C | Leveraging Plausibility Orderings to Achieve Extremely Efficient Data Compression |
| V3 C42 | C | Building Custom Static Checkers Using Declarative Programming |
| OE21 C01 | B | Automated AI Testing Simple tests will save you time |
| OE21 C02 | A | Efficient Event Based Simulations |
| OE21 C03 | C | Gearing the Tactics Genre Simultaneous AI Actions in Gears Tactics |
| OE21 C04 | A | Knowledge is Power an Overview of AI Knowledge Representation in Games |
| OE21 C05 | B | Taming Spatial Queries Tips for Natural Position Selection |
| OE21 C06 | C | Flooding the Influence Map for Chase in Dishonored 2 |
| OE21 C07 | C | Managing Pacing in Procedural Levels in Warframe |
| OE21 C08 | C | Cinematic Gameplay in Watchdogs 2 Pose Matching and AI Coordination |
| OE21 C09 | C | Obstacle avoidance for robots of multiple sizes and forms in Horizon Zero Dawn |
| OE21 C10 | B | AI-Driven Autoplay Agents for Prelaunch Game Tuning |
| OE21 C11 | A | You had me at AAAAHHH On the importance of reactions in game AI |
| OE21 C12 | B | Squad Coordination in Days Gone |
| OE21 C13 | B | Template Tricks for Data-Driven Behavior Trees |
| OE21 C14 | C | Planning Movement on Player-Modifiable Maps |
| OE21 C15 | C | Should STL containers be used in game engines |
| OE21 C16 | B | Open-world Enemy AI in Mafia III |
| OE21 C17 | B | Game Balancing using Genetic Algorithms to Generate Player Agents |
