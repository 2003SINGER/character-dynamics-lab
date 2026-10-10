# STORY2GAME：从故事生成可执行文字游戏的强近邻审计

阅读日期：2026-10-11

状态：Luna 委派全文审读（arXiv v1 全文 8 页，含 Appendix A）；主代理复核方法、动态扩域与评测条件

角色：作者约束下游戏世界规划的强邻近系统；更准确说，是故事生成、引擎搭建与动态动作扩域，而非本项目所说的在线作者约束规划器。

原文：[本地 PDF（私有原件）](../../../90_原始材料/_private/2026-10-11_规划近邻原件/STORY2GAME/STORY2GAME_2505.03547v1.pdf)；[arXiv:2505.03547v1](https://arxiv.org/abs/2505.03547v1)；[PDF](https://arxiv.org/pdf/2505.03547v1)。版本：v1，2025-05-06。SHA-256：`e7fae3debb79dfb88b085cbe81cefbec19a9f2db5690cb5fcdbae454a147bde0`。arXiv 页面显示 CC BY 4.0；论文/代码分开处理，未找到作者发布的软件仓库或可读源码。本文可见的 Appendix A 是论文中的 prompt 与 JSON 样例，不是软件源代码。

## 结论先行

**[paper evidence]** STORY2GAME 已经越过“LLM 只生成对白/旁白”的范围：它从故事句子抽取动作前提与效果，把这些语义编译成实际检查和变更游戏状态图的 Python 游戏动作；当玩家提出未预建动作时，还能增加必需对象、属性和前置事件，并检查新属性是否影响既有动作（§III–IV、Fig. 1–2、Appendix A）。所以“LLM × 规划/游戏机制还没有触及可执行状态”会被这篇直接反驳。

**[inference from paper]** 它与本项目 `I=(G,s,H,C,U,E,B)` 的交集主要在 `G` 的建模/生成及动作语义进入执行接口：STORY2GAME 从零构造一个有限文本游戏实例，并让玩家动作真正改动该实例状态。但它没有展示一个根据作者当前约束持续搜索、生成并修订多层未来计划的在线 planner。主故事由输入的主线事件引导生成；后续“扩域”由玩家提出的单个动作触发，不是对开放作者约束的统一求解。

**[project decision]** 将它纳入“生成式 IF 引擎与动作编译”最强近邻，限定比较对象为：故事→pre/effects→世界对象与状态→可执行动作代码，以及玩家临时动作导致的 schema/action 修订。它不能替代 GOAP/HTN、作者轨迹规划、世界过程模拟或反馈修复的同域强基线；也不支持新颖性结论。它使“不是纯对白”成为项目表述必须承认的既有能力，并把更窄的未知收束为：在同样具有真实执行状态的游戏中，是否能从稀疏、可混合密度的作者约束规划合理可执行的未来，覆盖非玩家角色与世界过程，同时把新增状态、动作和修订控制在作者可审阅且预算可接受的范围内。

## 论文实际主张

**[paper evidence] 任务与状态。** 目标是从头生成文字互动小说：LLM 先生成故事，然后按故事创建地图、对象和人物，再生成玩家可调用的动作代码；游戏维持 ground-truth world state，玩家可用自然语言式输入探索故事外动作（§I、§III）。默认世界是有限 Python 图：节点为 Player、Character、Item、Room、Container；玩家和容器有 inventory；房间能包含节点；非房间节点可挂属性。默认动作仅 `look`、打开背包、去房间（§III）。论文承认 world generation 相对简单且不是贡献重点（§I、§III-B）。

**[paper evidence] 生成次序与因果表示。** 输入故事标题、2–6 个主事件、目标/设定描述；GPT-4o-mini 生成 5–18 个事件，句子主要描述玩家要做的动作。其后再让 LLM 为每句标注三类 preconditions：基础的地点/库存条件、附加属性条件、要求此前动作完成的 preceding events。effects 被归入移动、设置属性、创建对象、删除对象四类。关键区别是论文先写故事、再注释 pre/effects；这不是 planner 先在形式域中搜索出故事（§III-A，pp. 2–3；Fig. 1）。作者指出，故事生成器本身简单且不是贡献；只要替代生成器能产出 pre/effects，其他生成器也可接入（§III-A）。

**[paper evidence] 从符号绑定到真实动作代码。** 世界阶段把故事里的房间放到格图上；从第一个房间开始，后续房间随机放在前后左右，未指明房间的动作归到最近提及的房间，参与动作的对象和人物放入对应房间（§III-B）。动作阶段严格按故事顺序逐个建立：preconditions 被翻译为地点检查、库存检查、节点属性检查；preceding events 用已有句子的先后要求表示。effects 变为移动节点、设属性、向房间加节点或从状态图删除节点的操作（§III-C、Table II）。这意味着输入的谓词并不是任意通用 PDDL 域：状态和操作受该引擎的节点类别及上述操作集合约束。

**[paper evidence] 变量绑定。** 故事句子中的地点、人物、物品需要解析并对应到图中的节点；生成出来的 action form 通过诸如 `{characters[0]}`、`{rooms[0]}` 的槽位绑定现有对象，并在执行前检查具体节点的位置、库存或属性（Appendix A、Fig. 6）。这是面向单人玩家动作的 grounding，不是对多个 actor 的 joint plan，也没有角色各自可见状态或 belief 绑定机制。

**[paper evidence] 临时动作、动态扩域和旧动作修订。** 玩家发出引擎尚无的动作时，系统用 LLM 生成 action 的涉及人物/房间/物品、preceding events、基础与附加前提、effects 和显示文本（§IV、Appendix A）。新动作必须操作至少一个现有物品/对象，以保证有所 grounding；但执行所需的对象可以新造，名称和位置由系统给出，位置随机（§IV-A）。新属性槽位可以补入既有对象，默认值由 LLM 选定；属性限定为布尔或 0–10 整数（§IV-B）。若新增属性可能改变旧动作语义，遍历涉及同一对象的动作并让 LLM 判断相关性，相关时把属性追加为旧动作前提（§IV-D）。preceding event 缺失时递归建动作，但深度最多 1（§IV-C）。

**[inference from paper] 这不是固定域内重规划。** 新动作生成会新增对象、状态属性和 operator，并回写旧 operator 的可执行前提；因此 `G` 本身可能变化，不能归类成只在固定动作域中重新搜索。另一方面，论文没有给出对 schema/action revision 的版本化、作者批准、撤销、冲突仲裁或计划一致性求解器；也没有证明这种扩域对所有现存未来目标都安全。作者明确说新动作可能破坏游戏完整性，让故事无法完成（§IV）。

**[paper evidence] LLM 与代码执行边界。** LLM 产出结构化 action 信息并生成 Python 代码；该代码在游戏中检查条件并修改实际基础数据结构，因此这是行为执行层，不只对白生成（§III-C）。论文没有描述独立静态类型/安全验证器、代码沙箱边界、候选试运行与 rollback、运行错误后的错误信息反馈循环或“失败后重写旧动作”的算法。论文中“compile success”是作者对生成动作能否成功建入引擎、且其前提可由状态进展满足的度量；不是报告使用编译器错误反馈驱动迭代修复（§V）。初始化动作失败的叙述性应对是玩家可以用动态动作探索替代路径，不是系统自动 repair 原计划（§V-A）。

**[paper evidence] 非玩家人物与世界过程。** 状态图里有 Character/NPC 类节点，可通过动作改属性；本文例子包括让 guard distracted（Table II、Appendix A）。但叙述动作被视为玩家将执行的动作，未描述 NPC 自己选择目标、可拒绝/承诺的角色策略或多角色协作规划。也未见天气、资源再生、生态、经济、定时事件或持续世界过程的 autonomous transition；房间和对象位置主要是静态初始放置，状态变化由玩家动作代码触发。这里的“没有描述/未评测”不等于证明系统绝对无法扩展。

**[paper evidence] 作者控制表达。** 作者提供故事标题、主事件、目标与设定；这属于一条预先引导的主线输入。论文没有形式化约束对象、硬软约束、作者可锁定的对象/片段、按对象混合控制粒度、允许覆写的权限，或在线跟踪部分实现要求的协议。故其主线输入可视为作者/提示给定故事骨架，不能直接等同 F0 的稀疏作者约束规划接口。

## 关键证据

- **[paper evidence]** §III-A：故事先产生；之后标注 preconditions/effects。基础前提包含位置/库存，附加前提可用自定义属性，preceding events 负责顺序条件。动作 effects 有四类。story generator 被作者定位为简单且可替换，不是本文主要贡献。
- **[paper evidence]** §III-B–C、Fig. 1、Table II：世界 graph 节点类型、随机房间布局及按故事顺序转 Python 检查/状态写入的流程；Table II 示例 `distract guard` 只要求双方在 dungeon，效果为设置 `guard.distracted=True`。
- **[paper evidence]** §IV、Fig. 2、Appendix A：玩家新动作采用一套有字段约束的 JSON 中间表示；可添必需 item/character 与新属性，且可以让 preceding events 变成前置动作；新增属性会触发对旧动作前提的检查与追加。Appendix prompt 限制新增要求 1–3 个，并把“基本存在/同地点”等交给系统基础规则。
- **[paper evidence]** §IV、pp. 3–5：新增前置事件深度限制为 1；作者承认自由动作没有保证不妨碍原故事完整性，且提及 intervention/accommodation 是兼容的相关路线，却未在本系统中实现相应冲突分析。
- **[paper evidence]** §V-A、Table III：4 个故事长度组，每组 8 个故事。动作句编译成功率分别为 0.972、0.937、0.928、0.942；整篇故事全部成功的比例分别为 0.875、0.75、0.625、0.75。常见失败是指称/形容词差异导致对象错认（如 Key 与 Metallic Key）。评估时若对象/玩家不在动作地点，直接强制搬到所需地点后再检查和应用效果（§V-A）。所以这些成功率不等价于玩家自由探索时端到端通关率。
- **[paper evidence]** §V-B、Fig. 4–5：对 5 个故事中的 15 个物品和 15 个角色，各取 3 个新动词，合计 90 个动作。动态动作 code compilation 约 80%；人工目视代码的 semantic success 总体约 60%。语义判断为作者主观逐段看代码，没有盲法标注者、一致性统计或玩家研究。失败例“用手电照亮森林”暴露架构缺口：room 无属性，且无法把房间层的 illumination 传播到隐藏物品可见性（§V-B）。
- **[paper evidence]** §VI：未来工作才考虑更复杂地分析新动作何时干扰、补充或应被禁止；作者把本文限制在文字 IF，以便省略图形与空间资产。
- **[paper evidence]** Appendix A：prompt 输出的完整字段/JSON 例能证明 action representation 的形状；不提供自主角色规划器、通用的层间 plan representation 或错误修复器。
- **[paper evidence]** arXiv 页面记录 v1（2025-05-06），提供 PDF/HTML/TeX Source 与 CC BY 4.0 论文授权；arXiv 页面和可见关联链接未给作者软件仓库。**[unknown]** 未能确认作者私有或未公开仓库是否存在；本轮未运行、安装或复现软件。

## 没有覆盖的边界

- **[paper evidence]** 没有作者约束 `C` 的通用表示/语义解析与 grounding；没有部分控制密度或多类授权边界 `U`；没有将预算 `B` 纳入算法比较。
- **[paper evidence]** 没有持续在线 world/plot/NPC 多层计划求解。故事动作按已有序列顺序编码；玩家输入新动作则追加能力与前提，而非报告对当前 `C` 的 plan search。
- **[paper evidence]** 没有 NPC autonomous policy、其他角色拒绝、玩家/NPC 多策略 response、共享资源竞争或角色局部信息权限测试。NPC 是可由玩家 action 操作的世界对象。
- **[paper evidence]** 没有可观察气候、自然资源演化或其他不由玩家 action 触发的持续世界过程。该对象与项目的世界中心目标存在差异。
- **[paper evidence]** 没有 domain growth 的作者批准、revision provenance、回滚语义、既有动作冲突全局检查，或自动保证原目标依旧可达；正文直接承认它可能破坏故事可完成性。
- **[paper evidence]** 编译/效果检查不等于强运行时验证、执行回执与反馈修复；论文没有给出失败后给 LLM 的 validator diagnostics 或 repair attempts 记录。
- **[paper evidence]** 没有传统规划、规划+LLM、人工动作编写、固定动作域、或相同世界/作者预算条件的 baseline/ablation。没有比较完整作者劳动成本（写作、对象建模、审核、调试、API/运行开销）。
- **[inference from paper]** 它可以证伪“LLM 生成的互动故事天然只是空洞文字”这种宽泛命题，却不能证伪/证明此项目 F0 所述在线作者约束规划是否已有足够成熟方法；两者问题层次不同。

## 与当前项目的核验表

| 项目 | 论文覆盖 | 项目仍需验证 |
|---|---|---|
| 主体/状态 | [paper evidence] 有限 IF 图状态：玩家、Character/NPC、Item、Room、Container、库存与对象属性；动作能真实改图。 | [project decision] 保持游戏原生 `G,s,H`，不要把论文的节点图或 OHXSP 固化成通用模式；测试目标若涉及 NPC/world processes，应有真实执行与持续过程。 |
| 作用/写入 | [paper evidence] pre/effects→代码，代码检查地点/库存/属性并执行状态操作；动态动作能扩对象/属性并修订旧动作前提。 | [open question] 对 revision 的授权、可追溯版本、冲突检查、试执行/回滚、错误反馈和已生成未来计划的协调如何定义。不要把其属性相关性 LLM 判断称作完整验证器。 |
| 失败/反事实 | [paper evidence] 报告对象错认、动作编译失败和语义不合理；新动作可能使故事无法完成。 | [open question] 在同一世界输入下，真实阻断/失败、部分效果、对手行为、拒绝和世界扰动如何反馈并重规划；本项目仍需区分作者改域、合法控制与玩家实际行动。 |
| 评测 | [paper evidence] 32 条生成故事按长度测试动作链；动态动作 90 条，约 80% 编译、约 60% 主观语义通过；初始化测试会强制移动对象。 | [project decision] 可作“从故事构造可执行 IF 动作”的外部近邻结果；不能当同域 planner baseline 或作者成本/玩家体验证据。若比较，统一 domain、执行器、作者输入与失败条件并明确成本。 |

## 项目决定

**[project decision]** 本卡纳入05总表，入口与任务状态按本轮综合审计更新；F0/F1、planner、代码、实验与Runtime未因这篇论文改动。该文献抬高了项目“领域已有能力”边界：完整 state-grounded action code generation 和运行中动作/对象/属性扩展并非空白；但对项目在线解 `I=(G,s,H,C,U,E,B)` 的直接替代性有限。后续如用户授权比较，应优先把 STORY2GAME 放在“生成式游戏初始化与开放玩家 action/schema 扩展”侧，用来反证对白-only baseline 和暴露动态改域的安全/一致性边界，而不是假装它是传统 planner 的弱版。

**[open question]** 是否应纳入同一 benchmark，取决于目标任务能否适配文本 IF 的 player-action 交互形式；如目标是 NPC 持续自主、自然世界演化或作者在过程中的局部硬约束，直接同分数比较会混淆任务对象。

## 来源与读取记录

- 私有原件：`90_原始材料/_private/2026-10-11_规划近邻原件/STORY2GAME/STORY2GAME_2505.03547v1.pdf`（本地 ignored/archive；保持原文件不变）。PDF SHA-256 如上。公开版本与授权见 arXiv v1 页面。
- PDF 共 8 页。已提取全文文本用于检索，并渲染检查 pp. 3–6 的 Fig. 1–2、Tables II–III、Figs. 3–5 及正文排版；tmp 中的临时文本/PNG 在审计完成后应删除。
- 软件源码：论文和 arXiv article links 可见 TeX Source；它是论文排版源。未发现作者软件源码链接，因此没有 clone、运行或声称源码审计。

用户新理解（留白，不以 AI 判断代填）：
