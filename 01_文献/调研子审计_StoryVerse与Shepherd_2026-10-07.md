# 调研子审计：稀疏作者控制与角色/世界自主

阅读日期：2026-10-07。性质：限定近邻审计，不是穷尽查新、系统综述、系统复现或实现推荐。全文主读 StoryVerse 与 Shepherd；核对 AIIDE 2025 博士提案全文以确定论文状态；外围核查 Elsewise 与作者负担研究。证据标签：**论文证据**、**从论文推论**、**项目问题**。

本轮问题不是“自主还是控制”的抽象二分，而是：作者写下少量节点/模式后，谁持有世界状态，谁提出/选择动作，谁校验行动能否发生，导演如何介入角色策略，以及偏离后系统能否继续。两篇主文都说明“编排”并未消失：它从逐个场景/反应，转成剧情模式、动作语义、角色倾向、候选权重、规划目标和验证接口。

## 结论先行

- **StoryVerse（Wang, Zhou, Ledo, FDG 2024）是“作者稀疏给抽象剧情节点、导演将其变成动作序列”的直接先例。**世界状态由 Game Environment 持有；默认 Character Simulator 产生活动，Act Director 在抽象 act 满足前置条件时接管该时步并生成整段计划。玩家改变世界状态；环境再回传。其核心不是稀疏点自动落地，而是 LLM 导演读取世界与过去行动，反复生成、环境试执行、动机审查、修订计划。作者示例展示了死角色后的适配，但没有系统性失败率、硬保证、玩家评价或作者工时证据。
- **Shepherd（Deo, Chung, McCoy, AIIDE 2024）是“世界模拟与角色策略继续运行，故事模式 sifter 对动作选择施加软偏置”的直接先例。**角色对各可行动作按自身 traits 评分，再结合 drama-manager 分数，按综合权重随机选择。模板用 Winnow 模式匹配历史事件；高进展/接近完成的模板提高相应动作分数。它没有强制动作或直接写世界状态；相较 StoryVerse 更像策略外层的可插拔导演信号。但论文没有报告确切分数公式、权重合成细节或系统评测，不能把伪代码补成确定机制。
- **2025 AIIDE 论文确为博士提案/Doctoral Consortium，而非已验证系统。**作者 Lasantha Senanayake 的 *From Emergence to Planning: A Triangle Framework for Scalable, Controllable Interactive Storytelling* 把 landmark-guided 混合机制列为 proposed approach；评估也明确写成 proposal。Landmark 定义借用经典规划的“每个有效解路径上必经命题”，不等于当前 LLM/agent 执行器已实现硬保证。一个子系统作者仍称 “currently implementing”；论文没有实验结果。
- 因而已有近邻覆盖了三种实质不同的控制方式：动作序列接管（StoryVerse）、候选效用偏置（Shepherd）、高层子目标/landmark 引导（2025 proposal）。本项目不能只凭“NPC 自主”“少量作者节点”或“世界看起来因果合理”宣称新颖；要比较谁拥有各层状态、哪些动作可被改变、如何面对不可达、以及与什么基线/指标相较。

## 主文一：StoryVerse

**书目与状态。**Yi Wang, Qian Zhou, David Ledo, *StoryVerse: Towards Co-authoring Dynamic Plot with LLM-based Character Simulation via Narrative Planning*，arXiv:2405.13042v2（2024-11-02），正式发表于 FDG 2024，DOI [10.1145/3649921.3656987](https://doi.org/10.1145/3649921.3656987)。本地全文：[StoryVerse PDF](../outputs/literature_sources/author_constraints_20261007/StoryVerse_2024.pdf)。正式全文和作者信息见[arXiv HTML](https://arxiv.org/html/2405.13042)。

**算法与所有权（论文证据：§2，印刷 pp.2–5）。**

| 层 | 论文里由谁持有/决定 | 实际接口 |
|---|---|---|
| 世界与执行 | Game Environment | 保存变量式 World State：角色位置、属性/HP、关系分数、模拟记忆等；按 action schema 执行动作并更新状态。它也是 player 改变状态的入口。论文称 proxy environment，未给通用事务/动作验证规范。 |
| 默认角色动作 | Character Simulator | 无合格作者 act 时，由 LLM 按角色预写描述、结构化行动记忆生成每角色动作。实现是 AgentVerse 式 basic simulator，每步每角色一动作；未定义每角色私有 belief、可见性掩码、独立 policy 与错信念机制。 |
| 作者结构 | Story Writer | 写 abstract acts：自然语言叙事目标；AND/OR 前置条件（当前世界状态、玩家动作、其他 act 的成功/失败）；placeholder（先前 act 产出的具体角色/对象绑定）。多个 act 可分支、非按书写顺序执行，且可分组。 |
| 导演/覆盖 | Act Director / Act Selector | 每步筛出前置条件满足的 pending act；处理 placeholder 后，为所选 act 生成整段角色动作计划。此时 Character Simulator 不作为同一动作序列的共同仲裁者：论文流程是 act 导演有 act 就产生活动，否则运行角色模拟。 |
| 计划质量检查 | LLM Plan Reviewer + Game Environment + Character Simulation Evaluation | 生成器输入目标、当前 W、Story Domain；审阅器检查剧情连贯性、通过模拟环境试执行并报告成功/失败、逐动作询问角色记忆是否支持动机；再要求生成器修订。若某动作已满足叙事目标，审阅器可截断其后计划。最大重写次数由用户设定；实验 maxStep=2。 |
| 跨 act 连续性 | Placeholder Resolution | LLM 从已执行 act 中解析角色/对象身份并存映射，后续目标能引用先前确定的 X/Y。保留的是特定剧情变量的绑定连续性；论文没有实现一般历史一致性约束或 belief provenance。 |

抽象流程可写成：`if eligible_abstract_act: instantiate_goal(W, prior_acts/placeholders); repeat generate(plan | W, domain) -> review(coherence, simulated execution, per-character motivation) -> revise up to maxStep; execute plan; resolve placeholders; else run Character Simulator; then player may update W.` 这里的 `W` 是环境维护的共享状态，不是受角色局部观察约束的世界信念。

**动作约束与接管强度。**论文说 Story Domain 有可执行的 action schemas；叙事规划目标是生成可实现序列。但并未形式化 action schema 的 precondition/effect 校验协议、拒绝类型或原子回滚。Environment Evaluation 是模型生成计划之后的试运行反馈，用于提示词修订，不等价于可证明的规划器硬守卫。act 一旦触发，导演输出的是一串动作而非给自然角色 policy 一个轻量目标偏置；作者明确把它描述为代表 writer 的 autonomous surrogate。因此它与“只在轨迹上点几个节点”相容，但系统里确实有中心导演接管阶段。

**偏离、不可达与玩家扰动。**

- **玩家修改世界：论文已展示一个手工反例适配。**作者将 Ant 设为 dead，Act Director 改用剩余角色实例化故事（§3，印刷 p.5）。它证明原型可以对不同 W 重新生成，不证明任意干扰下 act 总可满足。
- **尚未满足 prerequisite：**pending act 留待之后；Character Simulator 继续运行，例子说明角色模拟可能先运行数步等待条件出现（§3，p.5）。
- **计划动作执行失败：**环境报告成功/失败，送回 planner 修改；重复到用户指定次数或“计划可执行”。在 maxStep 到限仍失败后采取什么回退、该 act 是继续 pending/标失败/跳过，论文未说明。
- **世界变化令目标不可能：**目标可能涉及已死角色。示例说明有时会适配角色，但没有一般不可达检测、替代目标/终止条件、bounded retries 或解决冲突的规则。
- **历史连贯：**memory 参与动作动机询问；placeholders 维持 act 间的身份绑定。作者承认长期依赖与连贯性受限，提出扩大上下文、RAG、分层生成作为后续探索（§4，p.6），不是已解方案。

**实验/边界。**方法部分报告 GPT-4-0125-preview、少量手写 few-shot、最多 2 次计划修订；结果是 The Ville 与 Ant & Dove 两个场景的示例叙事。无样本总数、随机种子、规划基线、量化叙事/动作结果、消融、玩家研究或作者成本测量。作者在结论明确把系统称 proof of concept，系统性指标和 user study 列为下一步（§5，p.6）。不能说它已证明低作者负担、角色更可信、健壮性或规模扩展。

## 主文二：Shepherd

**书目与状态。**Sage Deo, Jonathan Chung, Joshua McCoy, *Shepherd: An Incremental Story Sifting-Based Drama Manager*，AIIDE 2024，20(1):256–259，DOI [10.1609/aiide.v20i1.31887](https://doi.org/10.1609/aiide.v20i1.31887)。已读正式[AAAI 全文](https://ojs.aaai.org/index.php/AIIDE/article/view/31887)；作者公开[源代码库](https://github.com/L00tkek/shepherd)。本地全文：[Shepherd PDF](../outputs/literature_sources/author_constraints_20261007/Shepherd_2024.pdf)。

**算法与状态（论文证据：Technical Description，印刷 pp.257–258）。**角色的每个 trait 拥有一个对动作的 utility function；角色 action utility 是 traits 在该动作上的分数之和。动作有 actor（单人或二元 action 另有 target）和 tags；同一角色每个时间步只能发起一个动作，可成为多个动作的 target。对全部可能动作，角色分数与 drama manager 分数合成为 overall score，再按该分数作 weighted random choice。论文只说“combined”，没有交代具体是加法、乘法、归一化、分数尺度或零/负值处理，故不能复现精确概率。

Shepherd/底层 sim 的 state owner 是共享模拟，不是每个角色的局部 W/O/belief。角色 policy 读自身 traits 与候选动作 tags；论文未描述感知、遮挡、私有事实、对象级 beliefs 或历史推理。作者称 characters “mostly autonomous”，指它们选择动作而非被导演直接指定动作；不是已建模的认知自主。模板由 Winnow 表达为事件序列 pattern，例如 `tag:cruel, actor:?c1,target:?c2` 重复三次后，同两角色反向发生 `tag:kind`；变量绑定由模式跨事件匹配维持。

**Sifting 如何进入 action choice。**Shepherd 随模拟生成同步更新可选、部分满足、已完成的 story templates。评估候选动作时检查其会不会推进模板：能推进更多模板的动作加权更高；接近完成的模板得到更高重视。模式进展使 drama manager 对各候选动作打分，进而软性改变角色 weighted-random 分布。其直观伪代码（论文未给精确数值公式）：

```text
for each time step:
  for each character c:
    candidates = possible_actions(c)
    for action a in candidates:
      character_score = sum(trait_utility(t, a) for t in c.traits)
      drama_score = score_template_progress(a, active/partial templates)
      overall_score = combine(character_score, drama_score)  # exact operator unspecified
    choose weighted-random action using overall_score
    apply chosen action; update Winnow template matches
```

重要差异：作者说 Shepherd 是 nudge 而非 demanding events（pp.256–257）。未发现论文描述导演改写 W、强制某 action 或直接变更角色状态；story pressure 通过 action distribution 间接实现。动作的 tag 同时被 trait utility 与故事 pattern 用，故作者仍需设计动作类型/tag、角色 traits/utility、Winnow 模式；模式可复用多种具体动作，但不是“只写几个点剩下自动长出来”。论文在小样例中称模板进展动作因此更可能被选中，并未给额外权重或概率。

**失败、不可达与历史。**渐进模板能记录已发生的部分序列，但论文未报告模板时间窗口、遗忘/过期、并发冲突、条件失败、不可达原因诊断、超时、重试或玩家干预协议。模板一直 tracked；作者希望未来扩展状态跟踪（例如角色关系）及 authoring tools。因而它能借事件历史追踪角色对角色实施行为的重复 pattern，但没有角色自身 memory/belief 的历史一致性证明。论文提及模板弧可能难以让玩家辨认；对动作进行模式加权不能确保玩家理解其因果关系。

**实验/边界。**正文仅给一次示例模拟/UI、trait 合乎行为的举例、一次出乎意料的 action，以及一段多时间步的故事弧。未给 N 个 run、采样量/seed、基线对照、指标、玩家或作者实验。结尾直接列“properly evaluate”作为后续；关于易 author、极可扩展、故事更连贯等结论属于论文作者的系统描述/主张，尚无量化证据。只可将 Shepherd 作为具体机制先例与算法基线候选，不可引用其“有效性”已被实验证明。

## 近邻核查：Landmark 混合博士提案（AIIDE 2025）

Lasantha Senanayake, *From Emergence to Planning: A Triangle Framework for Scalable, Controllable Interactive Storytelling*，AIIDE 2025 Doctoral Consortium，21(1):450–453，正式[AAAI 页面](https://ojs.aaai.org/index.php/AIIDE/article/view/36858)，[全文 PDF](../outputs/literature_sources/author_constraints_20261007/Senanayake_2025_DC.pdf)。这是研究提案：正文反复用 “propose / proposed / currently implementing / evaluation plan”，四页中没有最终系统结果。

**landmark 强保证要拆成定义与运行机制。**论文借定义把 planning landmark 说成“每个有效解都必须在某时刻成为真的命题”，通常构成偏序；这是经典规划理论的定义，并非它实现的运行承诺。作者提出两路混合：

1. **State trajectory constrained LLM simulation：**中心规划器先在抽象域给 landmark 因果序列；个体是有 observation、belief/intention/memory/goals 的 agent，LLM 按当前 active landmark 并结合自身观察/状态行动。此路提出了“局部状态 agent”，但未说明 landmark 如何从 agent policy 变成硬约束，LLM 偏离/幻觉/动作失败如何惩罚或强制恢复；鲁棒性是研究问题。
2. **Landmark-guided classical planner：**抽象 plan 给子目标，中心经典规划器把当前子目标展开为动作、执行、监控 effects，完成后前进。若有完备的有限域规划器、正确动作模型且子目标可达，它可能有规划层可达性保证；但提案的 low-level planner 当时 “currently implementing”，作者写了 future/after stable 才加简化意图模型。论文没有声明或验证这些实现假设，也不保证环境扰动后的子目标总可达。

进展栏只列抽象化的 landmark extraction、接口设计、参数化故事域、基线 prototypes 与 logging；论文没有呈现代码结果、成功率或数值实验。评估计划拟测剧情质量、可扩展性、landmark adherence（按预测顺序达到的 landmark 比例）、失败动作/LLM variation 偏离、不同 seeds 的最终目标数量方差，以及人物可信/剧情连贯的人工评价。样本规模仍写 multiple trials，未给 n。故提案不能当作 landmark 硬/软保证已实现、作者已证明其能扩规模，或有玩家/作者成本结果。

## 外围核查：Elsewise 与作者负担

**Elsewise**：Yi Wang et al., *Elsewise: Authoring Open-Ended Interactive Narrative with Possibility Space Visualization*, arXiv:2601.15295 v2（2026-09-09），正式[arXiv 页面](https://arxiv.org/abs/2601.15295)，全文：[本地 PDF](../outputs/literature_sources/author_constraints_20261007/Elsewise_2026.pdf)。全文核对确有 n=12 作者研究（第 7 节/附录 A.2）；不是根据题目或摘要的二手数字。研究为被试内两条件 authoring，比对 BSV 可视化与 playtesting panel，结果主要是提高对可能叙事轨迹的预期信心、探索/创造支持评分，而 NASA-TLX mental effort 两边都高。Elsewise 的系统目标是作者理解和雕塑 LLM interactive narrative 的 possibility space；story generation 仍由 LLM game master + 玩家轮替，故事空间可视化及规则编辑协助作者。它对“作者能否预见开放互动空间”相关，对世界中心 NPC 的动作所有权/局部策略、运行时自治和 W/O/belief 分层不构成直接实现先例。研究限制也明确：只有模拟玩家轨迹，未招募真实玩家；短小故事、非长期项目（§8）。

**Beyond Authorial Burden**：Joey D. Jones & David E. Millard, *Beyond Authorial Burden*, ACM Transactions on the Web 20(3), Article 34, 2026-08-13，DOI [10.1145/3757746](https://doi.org/10.1145/3757746)。正式出版社摘要记载 14 位 IDN 作者访谈，并以另外 8 位专家参与 focus groups 验证模型；作者指出工作可能在内容、动态编排、编程/工具间迁移，不一定被“消除”。本次只核出版元数据与摘要，不作全文审计：出版社 PDF 请求 HTTP 403。其对象是交互叙事作者的劳动结构，能提醒不能把劳动转移写成劳动减少；不检验 NPC 行为策略、世界连续运行或玩家可置信性。

## 补充线索：CoG 2026 Narrative Intervention（未取得全文，非方法审计）

Qianwen Lyu, David Millard, Nicholas Gibbins, *Narrative Intervention for Prospective Story Sifting*（IEEE Conference on Games 2026）。作者的[University of Southampton 主页](https://www.southampton.ac.uk/people/5wzk7h/professor-david-millard)将其列为 2026 conference publication；[CoG 2026 正式日程](https://cog2026.org/schedule)列作 regular 20 分钟论文报告；[会议 accepted-papers 页面](https://cog2026.org/acceptedpapers)确认该届录用论文，并说明 PDF 仅向参会者开放、论文集将在会后发布至 IEEE Xplore。Southampton 机构库[记录](https://eprints.soton.ac.uk/id/eprint/513351/)为 “In Press”，显示无可下载附件；目前未找到开放的 IEEE 正式全文/DOI，故**本次未取得全文，以下仅登记官方摘要线索**。

机构库摘要称：以预定义的 composable sifting patterns 引导 intervention framework，影响模拟发展、增加 generated stories 数量，并声称保持 emergent nature。这个表述使它成为值得优先拿全文核对的“故事模式主动影响模拟”的近邻，甚至比纯离线整理输出更贴近 runtime intervention；但是摘要没有给干预算子、候选筛选/动作替换方式、World/API owner、角色 autonomy 约束、失败/不可达处理、实验 baseline 或数值。因此当前不能判断它究竟是通过动作概率软偏置、强制动作、改变事件/世界状态，还是委托剧情 director；也不能把摘要结论当作具体算法或充分实验支持。索引与作者页面确认题名/作者/会议身份，不替代论文方法证据。

## 对 character-dynamics-lab 的对照与反证问题

项目现有边界见[研究问题与候选创新](../00_研究设计/前台问题与候选创新.md)、[完整机制](../00_研究设计/完整机制说明_v0.md)与[未决问题 Q04/Q05](../00_研究设计/未决问题与机制候选.md)：项目至少主张 W/O/角色状态分离、按 O/S/P 选动作、由 World 最终校验；另有世界中心 NPC 的应用方向。对照不能抹平语义层级：StoryVerse/Shepherd 解决剧情结构与故事模式偏置，项目关注可持续人物行为与动作执行真实性；但这些“关注不同”并不能自动推出方法贡献。

在项目主张任何新意前，需要能回答这些反证问题：

1. **作者的“几个点”到底是什么、由谁实例化？**是高层剧情 goal/prerequisite（StoryVerse）、带角色/事件/tag 绑定的模式（Shepherd）、偏序 landmark（提案），还是活动/目标配置？测量作者输入量时，要计入 action schema、traits/utility、故事模式、对象 affordance、约束和 prompt/修订规则，不能只数主线上点了几个节点。
2. **世界状态和 actor belief 各由谁所有？**角色只能读 O/B 还是共享全局 W？计划器、导演、memory、评分器是否会通过隐藏变量引入玩家/角色不可知信息？StoryVerse/Shepherd 都不能作为本项目“局部知识”已被覆盖或未被覆盖的单一答案，需与具体接口逐项对照。
3. **导演对 actor policy 到底做什么？**StoryVerse 是触发后整段序列接管，Shepherd 把模式分数并入 action 选择。项目的 Director 若筛候选、改效用/概率、注入行动、直接修改 W，分别与何种 baseline 比？需记录 policy 在不干预/干预时的候选与概率，证明“只改变方向/保留行动权”而非口头称自主。
4. **计划不可达、动作被拒、角色死亡、玩家破坏前提时是什么机制？**是 W 权威校验+typed rejection、重试、等待、换节点、跳过、终止，还是失败未定义？应构造 W 中确实不可达和 actor 不知情的配对情境；记录再次规划次数、到达/终止/卡死率和额外世界干预。
5. **历史一致性到底保存什么？**StoryVerse 的 placeholder 保存对象身份，memory 被 LLM 用来检查动机；Shepherd 用 Winnow 绑定已发生事件；两者都未证明角色局部知识完整、信念证据可追溯或长期一致。本项目要以相同历史下的遮蔽/误信/过时信息干预来测，不能把存在 `memory` 或 `belief` 字段当证据。
6. **效果指标与独立基线是什么？**至少比较自主 actor-only、稀疏节点直接导演、模式/landmark 偏置或一个合适已实现近邻；固定同一 W/O、角色目标/资源、seed 与节点预算。报告可解释的剧情目标达成/偏序、动作接受率与拒绝后恢复、行为分布变化、玩家对“可理解/可预期/有活感”的独立评价，并记开发/作者配置时间。自家规则模拟或模型裁判分数不能替代玩家验证。

这些是下一轮可证伪问题，不是已授权的实现规格或 novelty claim。最小比较的判据应是：在同样稀疏作者约束下，系统是否比弱/强基线更好地保留 actor-visible 因果、而且在失败与扰动后持续推进；收益是否超过导演强度、作者配置与运行成本。

## 阅读与来源边界

- 全文主读：StoryVerse（6页 arXiv v2/PDF）、Shepherd（4页 AAAI 正式论文/PDF）。两份 PDF 在 `outputs/literature_sources/author_constraints_20261007/`，该目录已被 `.gitignore` 排除；独立文件清单为同目录 `manifest_recent.json`。
- 全文状态核验：Senanayake 2025（4页 Doctoral Consortium proposal）；Elsewise（18页 arXiv v2 PDF，重点读系统、study 和 limitations）。
- 外围仅核出版社摘要：Beyond Authorial Burden（正式全文下载返回 403），样本数只报告摘要明确的 n=14 与另组 n=8，不将其升级为全文审计结论。
- 新增线索：CoG 2026 Narrative Intervention：官方作者/机构库/会议页面确认来源与访问状态；机构库无可下载文件，会议声明论文全文仅参会者可得并将进 IEEE Xplore。本次没有算法全文，故不提高它的证据等级。
- 本审计不等于复现实验、代码审计、完整系统综述或 novelty clearance。Shepherd 开源仓库本轮只核到作者论文中的项目链接及正式 README，未逐行运行/审代码。
