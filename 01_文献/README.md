# 本地文献库

入口更新：2026-10-08；下载盘点快照：2026-09-05
截至该盘点快照：**82 篇 PDF 已下载并以 `%PDF-` 文件头校验；4 篇已定位但待取得。** 这不是今日全库统计。下载只表示可离线阅读，不表示已精读、已认可其中论断，或已完成查新。

2026-09-05 四批新增共 54 篇，**全部尚未导入 Zotero，也未执行「检索 PDF 元数据」**：

- 心理学/appraisal 4 篇（EMA 2009、Evaluating EMA 2005、Formal Models of Appraisal 2008、Fleeson 2001），核读见 [X 维度与状态动力学](专题核读_X维度与状态动力学_2026-09-05.md)。
- 三方向近邻 6 篇（GOAP 2006、Utility Theory 2013、Behavior Trees 2022、SOTOPIA 2024、AgentVerse 2024、Social Simulacra 2022），核读见 [三方向近邻](专题核读_三方向近邻_2026-09-05.md)。其中 Behavior Trees 为 198 页**专著**（arXiv 1709.00084v6），非论文。
- 工程三空白 10 篇（HTN Ch12、SHPE、Possibility Maps、Smart Zones、ETQ、Dual-Utility、Reactivity & Deliberation、Talk of the Town、CiF、Şahin 2007 affordance），核读见 [工程三空白](专题核读_工程三空白_2026-09-05.md)。**其中 8 篇是 Game AI Pro 系列图书章节，不是学术会议/期刊论文，无任何学术索引收录**，引用时须标明性质。
- **Game AI Pro A 级 34 篇**（4 卷 146 章中按相关度筛出的 A 级 43 章，扣除本库已有的 9 章）。核读见 [Game AI Pro 全景与工程 Gap](专题核读_GameAIPro全景与工程Gap_2026-09-05.md)。**其中逐节核读仅 8 章，其余 35 章已下载并提取文本但未读**，未读状态由 TODO 的 T23b 跟踪。全部为行业书籍章节，无同行评审、无学术索引。

已完成的项目审计入口：[全量近邻精读总表（2026-09-01）](全量近邻精读总表_2026-09-01.md)。它记录了每篇的覆盖范围、对本项目的边界、可借方法和必读顺序。

当前正式文献审计入口：[全量近邻精读总表（2026-10-06）](全量近邻精读总表_2026-10-06.md)。该表明确区分 Codex/Luna 代理全文审读、委派全文审读并经主代理复核、仅筛查、以及 Cho 方法全文文本审阅；本地有 PDF 或链接可下载均不等于已读。后续近邻/算法谱系判断以该阅读等级和证据边界为准，不重复在 README 摘录全表。

LIGHT 的官方任务与本地训练输入不等价；来源映射、候选重建、信息流负控与有界时点诊断由[LIGHT 任务准入审计](精读_LIGHT与本地预测任务准入_2026-10-06.md)维护。完整 actor-visible 准入仍未过；新[SourceRankingV1 协议](../02_实验/LIGHT_SourceRankingV1/README.md)及[输入验收](../02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)只将来源记录条件排名落成开发任务，不升级为合法 O 或官方复现。

针对第一个 Replay 实验缺少独立 `A*` 的问题，见[行为真值 A* 可行性审计](专题审计_行为真值A星可行性_2026-09-05.md)。结论是：BehaviorChain 完整数据当前不可公开获取；CharacterBox 不是独立行为真值；SOTOPIA 可作为**外部合成轨迹代理**进入小切片验证，但不是人类行为数据。此限制针对旧预测问题，不否定它们用于游戏角色评测的价值。

玩家视角的评测选择见[NPC 可置信性评测定向核查](定向核查_NPC可置信性评测_2026-10-06.md)：NPC-Bench 等仍是来源/评测章节核查。CharacterBox 已提升为主代理全文审读（20 页含全部附录），方法、训练与本项目接口限制只由[唯一精读报告](精读_CharacterBox_2026-10-06.md)维护；未运行或复现该 benchmark。目标与下一阶段设计判断仅由[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)维护。

玩家研究切口的新增全文审读见[玩家可置信性问题选择](精读_玩家可置信性问题选择_2026-10-06.md)：DiGRA 2007 是作者设计/游戏分析，不是玩家实验；PLOS 2024 是短对话三条件玩家研究，不直接验证长动作中断恢复。两者的原文、覆盖、限制与第一轮反例均见该报告；Warpefelt 学位论文仅取得，2016 论文未作主代理全文审读，不提升阅读等级。

“作者定义角色/活动，而非逐情境枚举反应”的学术路线见[低编排可控 NPC 框架定向调研](专题调研_低编排可控NPC框架_2026-10-06.md)：比较 CiF、Versu/Praxish、CiF-CK、FAtiMA 作者研究、意图规划和 LLM 混合/复用机制。逐篇标注主代理/委派阅读范围、版本、玩家证据与作者成本证据；不是穷尽查新或已选定方法。共享玩家能力、商人/伐木工均仍是候选，不因本次调研启动实现。

用户确认世界中心方向后的[制作障碍与活人感外围调研](专题调研_世界中心NPC的制作障碍与活人感_2026-10-07.md)比较 Rain World、原版 STALKER、Legion、RDR2、Nemesis 与 KCD2，另全文审读一篇玩家预期实验和 Division 工具分享。明确区分开发者原件、玩家实验、官方摘要及未观看视频；不是方法选型或新实验结果。

用户要求进一步到算法层后，[NPC 方法与生产系统算法拆解](算法拆解_NPC方法与生产系统_2026-10-07.md)成为上述路线的计算机制入口：条件绑定、评分/搜索、状态更新、记忆复用、模拟层级及工具流程分别记账，含伪代码、手算与未公开缺口。FAtiMA 论文与固定源码的优先级差异明确分版；不把仍只有摘要/访谈的机制称作已吸收，不启动实现或新实验。

用户进一步提出“稀疏作者约束、节点上的角色变化、主要经世界干预让前后合理”后，新增[算法与权限综合审计](专题调研_稀疏作者约束与世界干预_2026-10-07.md)：比较 Author Goals / IN-TALE、Story Facilitator / Late Commitment、Awash、Shepherd、StoryVerse / Sabre，逐项区分状态节点、事件模式、动作接管、目标指令、策略偏置及世界设定。Awash 玩家对照、2025 博士提案、2026 CoG 摘要等证据等级分开；原件下载/哈希见[公共来源元数据](来源清单_稀疏作者约束_2026-10-07.json)。没有据此立项、运行新实验或宣称新颖性；原 PDF 仅本地保留。

用户随后授权落实 Praxish 原件核查与共同小场景：[论文/源码精读](精读_Praxish论文与原始实现_2026-10-06.md)记录正式标题、release attachment 与 tag/master 的区别、一步绝对后果 utility、共享 DB 及原脚本确定性执行证据；[原实验 owner](../02_实验/Praxish_Activity_Pilot_v0/README.md)维护前两步。2026-10-07 新增的[独立参数化 utility 比较](../02_实验/Praxish_Utility_Comparison_v0/RESULTS.md)另维护匹配、原件对象别名失败及配置账本；其开发结果不能提升为论文原有实验、作者成本优势或玩家效度证明。

继续核查的[世界引导直接近邻复核](专题调研_世界引导直接近邻复核_2026-10-07.md)拆解 DiriGent、Tension Space 和 CoDi；逐篇区分公开 prompt、符号真实执行、文本世界干预、人类故事阅读和 LLM 裁判。TSA 的主观前提/真实前提双校验已有先例；DiriGent 不是严格 world-only；其评分符号还有未解歧义。来源版本/下载状态见[元数据](来源清单_世界引导直接近邻_2026-10-07.json)，不把下载失败缓存或未运行实现算成复现，不据此确认新颖性。

## 检索原则

[多粒度剧情连接与 LLM 重组技术考古](专题调研_多粒度剧情连接与LLM重组_2026-10-07.md)及[多层状态轨迹/可执行世界续审](专题调研_多层状态轨迹约束与可执行世界_2026-10-07.md)保留前轮论据；其[叙事账本](来源清单_叙事技术考古_2026-10-07.json)与[轨迹账本](来源清单_多层状态轨迹_2026-10-07.json)分开版本、阅读范围与未核项。2026-10-08 用户要求先完成方法地基，现由[算法积木](算法积木/README.md)维护机制复用总表、系统权限与组合前提；三份卡片分别维护[修复/导演](算法积木/01_叙事修复与导演.md)、[意图/约束规划](算法积木/02_人物意图与约束规划.md)、[内容/LLM桥接](算法积木/03_内容绑定与LLM桥接.md)的17字段、逐步机制及自制手推。只公开报告，完整新原文留本地；不启动实现/实验，不把可监测推成可控制。未知内部程序明确保留，不用 introduction 填补。

2026-10-08 后续用户授权已进入[作者轨迹系统设计](../00_研究设计/AuthorialTrajectoryPilotV0.md)与独立reference语义验收；这不改变上述原算法阅读等级，不运行新NPC实验。新增[时序语义核读](语义核读_轨迹约束与在线监测_2026-10-08.md)准确区分PDDL3、2015v1 RoSI定义与项目自定义的missing/pin/coverage/editor语义。

后续[统一问题与成熟基线准入](算法积木/04_统一问题与成熟基线准入.md)把已有机制放到同一钥匙—账本实例，审查最小强基线及最多三个近期可反证问题；本轮复核对齐成功证据与反例，区分存在性路径、固定策略表现和鲁棒保证，并将“已有先例”限定为不能单独主张新颖性，不推断整个方向无缺口。A/B、Q1–Q3 不是全部研究任务，完整候选版图由[System Vision](../00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)维护。未新增文献或实验；原机制仍在三张卡、正式语义在 F0/F1、下层契约在 Pilot，不另建总纲。

中断/恢复能力的新增近邻审读见[ScriptEase 示范](精读_ScriptEase中断恢复示范_2026-10-07.md)：主代理读完 AAAI 2007 两页 demonstration 并核对图示，未运行旧游戏模块、未读 2006 完整方法。模式复用与分阶段恢复已有先例；该短文不提供受控玩家或作者成本证据，不据此宣布新 gap。

针对值域逆映射/阶段响应、低耦合更新和 Object—Scene 动作所有权的当前定向核读见：[三项 TODO 与机制修改方案](专题核读_三项TODO与机制修改方案_2026-09-05.md)。它核对 FAtiMA-PSI、Two Sides of Appraisal、Temporal Causal Network 与 Hierarchical State Space 的相关方法及证据边界；不是全库重新精读。非线性与阈值已有直接先例，具体分区作为本项目可比较假设保留。

针对 X 维度选择、状态动力学 U_k 形式、P 的落位与 Q01 的定向核读见：[X 维度与状态动力学](专题核读_X维度与状态动力学_2026-09-05.md)。该页保留原专题比较与 Q01 判定；其中 HSSA 的旧判断已按全文复核定向校正，具体证据以[HSSA 精读报告](精读_HSSA_2026-10-06.md)为唯一逐篇依据。

本库围绕完整研究链而建，不把项目缩写为泛泛的 persona 或 role-playing：

```text
客观事件 → 局部感知/遮罩 → 解释与信念 → 主观状态动力学
→ 条件行为分布（含不确定性）→ 行动 → 客观后果 → 回放/干预
```

因此包含三类材料：

1. **角色行为与评测近邻**：连续行为、动态 persona、角色逻辑、叙事一致性与漂移；
2. **局部可观测与状态表征**：ToM、belief state、Predictive State Representation；
3. **数据流与动力心理学基础**：appraisal、状态空间、时间因果网络、认知—情感动态。

`PersonaForge`、AI Town 等代码/系统线索不混入 PDF 计数；除非后续找到可核验论文原文，否则只保留为外部实现参考。

## 已下载论文

| 类别 | 本地 PDF | 官方来源 | 与项目的关系 |
|---|---|---|---|
| grounded action/dialogue | [LIGHT 正文](PDF/2019_LIGHT_Learning_to_Speak_and_Act.pdf)、[官方附录](PDF/2019_LIGHT_Appendix.pdf) | [ACL](https://aclanthology.org/D19-1062/) | 正文与附录 D / Figure 9 已核对（非全部附录精读）；[本地任务准入审计](精读_LIGHT与本地预测任务准入_2026-10-06.md)，不等于本地 `O/A^O` 已准入 |
| 角色系统 | [Generative Agents](PDF/2023_Generative_Agents_Interactive_Simulacra_of_Human_Behavior.pdf) | [arXiv](https://arxiv.org/abs/2304.03442) | 观察—记忆—反思—计划式角色 agent 的基础近邻 |
| 角色评测 | [InCharacter](PDF/2024_InCharacter.pdf) | [ACL](https://aclanthology.org/2024.acl-long.102/) | 人格 fidelity 的直接近邻 |
| 局部可观测 | [TimeToM](PDF/2024_TimeToM_Temporal_Belief_State_Chain.pdf) | [ACL](https://aclanthology.org/2024.findings-acl.685/) | 时间化角色 belief state，避免把遮罩单独误作创新 |
| 角色系统 | [CharacterBox](PDF/2025_CharacterBox.pdf) | [ACL](https://aclanthology.org/2025.naacl-long.323/) | 文本行为轨迹、裁判校准与微调近邻；[全文方法/接口审计](精读_CharacterBox_2026-10-06.md)，非复现 |
| 连续行为 | [BehaviorChain](PDF/2025_BehaviorChain.pdf) | [ACL](https://aclanthology.org/2025.findings-acl.813/) | 连续人物行为预测近邻；不是本项目可重复声称的空白 |
| 角色逻辑 | [Codifying Character Logic](PDF/2025_Codifying_Character_Logic.pdf) | [NeurIPS](https://papers.neurips.cc/paper_files/paper/2025/hash/15294ba2dcfb4521274f7aa1c26f4dd4-Abstract-Conference.html) | 可执行角色逻辑、场景决策近邻 |
| 决策评测 | [HEART-Bench](PDF/2025_HEART_Bench.pdf) | [ACL](https://aclanthology.org/2025.findings-emnlp.368/) | 人格、情景与行为决策评测近邻 |
| 动态 persona | [Dynamic Persona Coherence](PDF/2026_Dynamic_Persona_Coherence.pdf) | [ACL](https://aclanthology.org/2026.acl-long.1336/) | 多时间尺度状态、动态一致性的最直接近邻 |
| 动态 persona | [Trait Activation in Silicon](PDF/2026_Trait_Activation_in_Silicon.pdf) | [ACL](https://aclanthology.org/2026.acl-long.1792/) | trait × situation 的近邻 |
| 决策/角色值 | [RoleCDE](PDF/2026_RoleCDE.pdf) | [ACL](https://aclanthology.org/2026.findings-acl.106/) | 角色价值与具体决策倾向近邻 |
| 角色方法 | [PersonaForge](PDF/2026_PersonaForge.pdf) | [ACL](https://aclanthology.org/2026.findings-acl.386/) | 心理学驱动 persona 的近邻 |
| 评测污染 | [Identity Leakage in Role-Playing](PDF/2026_Identity_Leakage_in_Role_Playing.pdf) | [SIGDIAL](https://aclanthology.org/2026.sigdial-1.15/) | 小说人物评测的身份泄漏风险 |
| 叙事一致性 | [NCP-Bench](PDF/2026_NCP_Bench.pdf) | [arXiv](https://arxiv.org/abs/2608.08160) | 交互叙事中的长期承诺保持近邻 |
| 叙事混淆 | [The Story Shapes the Agent](PDF/2026_Story_Shapes_the_Agent.pdf) | [arXiv](https://arxiv.org/abs/2607.18566) | 叙事 framing 可能压过 persona，是干预实验的关键控制 |
| 长程漂移 | [ANCHOR](PDF/2026_ANCHOR_Long_Horizon_Persona_Drift.pdf) | [arXiv](https://arxiv.org/abs/2607.28818) | persona collapse / behavioral drift 的近邻 |
| 情绪动力学 | [CPM-MultiAgent](PDF/2026_CPM_MultiAgent_Dynamic_Emotional_Evolution.pdf) | [arXiv](https://arxiv.org/abs/2607.07824) | appraisal 驱动角色情绪演化的最新近邻 |
| 状态表征 | [Predictive State Representations](PDF/2004_Predictive_State_Representations.pdf) | [arXiv](https://arxiv.org/abs/1207.4167) | “状态为未来可观察预测”这一概念支点；不可直接迁移为人物心理理论 |
| 动力心理学 | [Two Sides of Appraisal](PDF/2004_Two_Sides_of_Appraisal_Cognitive_Architecture.pdf) | [AAAI 条目](https://m.aaai.org/Library/Symposia/Spring/2004/ss04-02-013.php) | appraisal、trait/state、行为后果的早期计算模型 |
| 动力心理学 | [Hierarchical State Space Affective Dynamics](PDF/2010_Hierarchical_State_Space_Affective_Dynamics.pdf) | [作者公开 PDF](https://www.ppw.kuleuven.be/okp/_pdf/Lodewyckx2011AHSSA.pdf) | 个体差异下的情绪潜在状态与时间动力学 |
| 动力心理学 | [Temporal Causal Network for Appraisal](PDF/2018_Temporal_Causal_Network_Appraisal_Process.pdf) | [SCITEPRESS](https://www.scitepress.org/PublishedPapers/2018/68674/pdf/index.html) | appraisal 过程的时间因果网络建模 |
| 动力心理学 | [Modeling Cognitive-Affective Processes with Appraisal and RL](PDF/2023_Cognitive_Affective_Appraisal_and_RL.pdf) | [arXiv](https://arxiv.org/abs/2309.06367) | appraisal 与目标导向学习的计算结合 |
| 动力心理学 | [EMA: A Process Model of Appraisal Dynamics](PDF/2009_EMA_Process_Model_of_Appraisal_Dynamics.pdf) | [作者公开 PDF](https://stacymarsella.org/publications/pdf/EMA_Dynamics.pdf) | 「appraisal 只读、由 coping 写状态」这一分层的直接依据；**假设过去/现在命题完全可观测，与 O 可陈旧冲突** |
| 动力心理学 | [Evaluating a Computational Model of Emotion](PDF/2005_Evaluating_a_Computational_Model_of_Emotion.pdf) | [镜像 PDF](http://deadnet.se:8080/ict.usc.edu/pubs/Evaluating%20a%20computational%20model%20of%20emotion.pdf) | EMA 的人类数据评估；**10 条定性趋势对 8 条，无统计检验、未报告样本量** |
| 动力心理学 | [Formal Models of Appraisal](PDF/2008_Formal_Models_of_Appraisal.pdf) | [作者公开 PDF](https://ii.tudelft.nl/~joostb/files/Broekens_DeGroot_Kosters_Formal%20Emotion%20Modeling%2012-Feb-2007_final.pdf) | appraisal 的形式化记号与阈值守卫；**无时间、无动作接口**，重评需 LTM 是其自述开放问题 |
| 人格动力学 | [Traits as Density Distributions of States](PDF/2001_Traits_as_Density_Distributions_of_States.pdf) | [课程镜像 PDF](http://simine.com/407/readings/Fleeson_2001.pdf) | P = 状态分布参数 (μ, σ, skew, kurtosis) 的依据；**个体内跨时间分布，不是人群横截面** —— Q01 判定见核读页 |
| 数据流/状态维护 | [SyncStream: Prototype-based Learning on Concept-drifting Data Streams](PDF/2014_SyncStream_Prototype_based_Learning_on_Concept_Drifting_Data_Streams.pdf) | [ACM DOI](https://doi.org/10.1145/2623330.2623609)；[KDD 2014 会议镜像](https://archive.gersteinlab.org/meetings/s/2014/08.28/kdd2014-i0kdd-meeting-materials/docs/p412.pdf) | 保留历史应按预测代表性而非仅按时近性；**不是**人物心理或角色模型 |
| 动态行为预测 | [DGPS: Learning evolving user’s behaviors on location-based social networks](PDF/2020_DGPS_Learning_Evolving_User_Behaviors_on_Location_Based_Social_Networks.pdf) | [Springer DOI](https://doi.org/10.1007/s10707-020-00400-3)；[作者公开 PDF](https://people.cs.vt.edu/~clu/Publication/2020/Geoinformatica-Wu-2020.pdf) | 个人偏好、社会连接与时间过程共同预测 check-in；只覆盖本项目“动态行为预测”一侧，不含主客观分离或主观状态更新 |
| 多主体心理模型 | [PsychSim](PDF/2005_PsychSim_Modeling_Theory_of_Mind_with_Decision_Theoretic_Agents.pdf) | [作者公开 PDF](https://people.ict.usc.edu/~pynadath/Papers/ijcai05.pdf) | factored ground-truth decision state、主体 belief、偏好决策与有限 mental-model revision 的直接先例；其 World 不应直接等同为对象化可执行世界层 |
| 认知—情感 NPC | [Creating Adaptive Affective Autonomous NPCs](PDF/2012_FAtiMA_Creating_Adaptive_Affective_Autonomous_NPCs.pdf) | [AAMAS DOI](https://doi.org/10.1007/s10458-010-9161-2)；[作者公开 PDF](https://www.macs.hw.ac.uk/~ruth/Papers/agents-affect/JAAMAS-final.pdf) | 感知、动机、情绪、记忆、学习、规划共同驱动 NPC 的直接先例 |
| 交互叙事 | [BDI Model for Narrative Generation](PDF/2013_BDI_Model_for_Narrative_Generation.pdf) | [AIIDE](https://ojs.aaai.org/index.php/AIIDE/article/view/12627) | 以 belief/desire/intention 建模角色动机与动作；belief 实现假定全知，不能替代局部可观测问题 |
| 动态心智评测 | [DYNToM](PDF/2025_DYNToM_Dynamic_Theory_of_Mind_Benchmark.pdf) | [ACL](https://aclanthology.org/2025.acl-long.1171/) | 连续情境中的 belief–emotion–intention–action 轨迹与转移评测；是动态状态合理性问题的直接近邻 |
| 角色模拟/评测 | [PersonaArena](PDF/2026_PersonaArena_Dynamic_Simulation_for_Evaluating_and_Enhancing.pdf) | [ACL](https://aclanthology.org/2026.findings-acl.471/) | 环境 agent 更新环境与角色状态，并评测行为连贯性；直接削弱“闭环模拟+一致性评测”作为创新 |
| NPC 动机/规划 | [Three States and a Plan: The A.I. of F.E.A.R.](PDF/2006_GOAP_Three_States_and_a_Plan_FEAR.pdf) | [GDC 2006](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf) | GOAP 原始文献：Goal Set 与 Action Set 解耦、**SmartObject**、失败知识写入 working memory 后重规划；直接对应 Q04/Q05/Q07 |
| NPC 决策/utility | [An Introduction to Utility Theory](PDF/2013_Utility_Theory_Introduction_GameAIPro.pdf) | [Game AI Pro](https://www.gameaipro.com/GameAIPro/GameAIPro_Chapter09_An_Introduction_to_Utility_Theory.pdf) | 响应曲线、**分段线性曲线**（Q01 的正确归属）、分桶/dual utility、**inertia**（承诺与迟滞的工程先例）；The Sims 系列实践 |
| 反应式控制 | [Behavior Trees in Robotics and AI](PDF/2022_Behavior_Trees_in_Robotics_and_AI_Book.pdf) | [arXiv 1709.00084v6](https://arxiv.org/abs/1709.00084) | 198 页**专著**非论文；BT 如何泛化 FSM/HFSM/subsumption/teleo-reactive/决策树。**无跨轮状态，与本项目前向动力学不同层** |
| Agent 社会/评测 | [SOTOPIA](PDF/2024_SOTOPIA_Interactive_Evaluation_Social_Intelligence.pdf) | [arXiv](https://arxiv.org/abs/2310.11667) | 90 社会场景、**私有目标导致信息不对称**、episode 末 7 维评分含 BELIEF/SECRET；**是行为真值 A\* 的候选语料来源**，但评测发生在事后而非揭晓前 |
| Agent 社会/群体 | [AgentVerse](PDF/2024_AgentVerse_MultiAgent_Collaboration.pdf) | [arXiv](https://arxiv.org/abs/2308.10848) | 四阶段循环：专家招募→协同决策→动作执行→评估→新状态；**无个体内部状态**，评测群体配置 |
| Agent 社会/原型 | [Social Simulacra](PDF/2022_Social_Simulacra_Populated_Prototypes.pdf) | [Stanford HCI](https://hci.stanford.edu/publications/2022/Park_SocialSimulacra_UIST22.pdf) | 由设计 brief 生成 agent population 供 red-team；N=16 设计者研究，**无下一行为预测评测** |
| 规划/HTN | [Exploring HTN Planners through Example](PDF/2013_HTN_Exploring_HTN_Planners_through_Example.pdf) | [Game AI Pro Ch12](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter12_Exploring_HTN_Planners_through_Example.pdf) | world state 是**角色所知的世界**而非世界本身；expected effects 只在规划期生效；**MTR** 编码计划优先级；前向分解支持部分计划（GOAP 后向搜索做不到）。与 GOAP 有同厂速度对比 |
| 规划/HTN | [SHPE: HTN Planning for Video Games](PDF/2014_SHPE_HTN_Planning_for_Video_Games.pdf) | [Springer CCIS 504](https://link.springer.com/chapter/10.1007/978-3-319-14923-3_9) | 学术侧 HTN-for-games；SimpleFPS domain 毫秒级测量；引述 Killzone 3 / Transformers 3 实测规模（**计划长度 ≤4、NPC <12、约 1 计划/秒**） |
| 未观测状态 | [Possibility Maps for Opportunistic AI](PDF/2015_Possibility_Maps_for_Opportunistic_AI.pdf) | [Game AI Pro 2 Ch7](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter07_Possibility_Maps_for_Opportunistic_AI_and_Believable_Worlds.pdf) | 对未观测状态维护 possibility/probability 分布、按传播规则演化、冲突于观测时实例化、支持 forking 推迟决策。**机制可借但方向相反**：目标是推迟提交真值（作者自述 technically cheating），不是真值/信念对照 |
| Scene 组合 | [Smart Zones to Create the Ambience of Life](PDF/2015_Smart_Zones_to_Create_the_Ambience_of_Life.pdf) | [Game AI Pro 2 Ch11](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter11_Smart_Zones_to_Create_the_Ambience_of_Life.pdf) | role → behavior → timeline → 同步点 → 触发器的 Living Scene authoring；**主角色行为结束会取消所有非主角色行为**（组合动作取消语义，对应 Q08） |
| **环境查询/主观视图** | [Asking the Environment Smart Questions (ETQ)](PDF/2013_Asking_the_Environment_Smart_Questions.pdf) | [Game AI Pro Ch33](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter33_Asking_the_Environment_Smart_Questions.pdf) | **对 Q04/Q05/Q07/Q08 最有用的一篇**：context object 定义 subjective world view；生成器按 "AI is aware of" 过滤；**同一 test 兼作 condition 与 weight**；validity test 在选择后持续校验（"oftentimes not the same thing"） |
| 决策/分桶 | [Dual-Utility Reasoning](PDF/2015_Dual_Utility_Reasoning.pdf) | [Game AI Pro 2 Ch3](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter03_Dual-Utility_Reasoning.pdf) | rank（绝对，分类别）+ weight（相对，类内加权随机）四步算法；Zoo Tycoon 2 用 **rank 抬升**实现情境性承诺（树上 rank≈5、表演 98–102、死亡 1e6） |
| 中断语义 | [Reactivity and Deliberation](PDF/2013_Reactivity_and_Deliberation_in_Decision_Making.pdf) | [Game AI Pro Ch11](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter11_Reactivity_and_Deliberation_in_Decision-Making_Systems.pdf) | "reactivity 关乎中断、deliberation 关乎维持，二者是 conceptual antipodes"；任务管理需 **starting / canceling / completing conditions** 三类；感知滞回用于**去抖**而非质变 |
| 局部可观测 | [Talk of the Town: Character Knowledge Phenomena](PDF/2017_Simulating_Character_Knowledge_Phenomena_TalkOfTheTown.pdf) | [Game AI Pro 3 Ch37](http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter37_Simulating_Character_Knowledge_Phenomena_in_Talk_of_the_Town.pdf) | **`W ≠ O` 的最强先例**：ground-truth value 与 belief facet 显式分离，facet 带 Predecessor/Parents/Evidence/Strength/**Accuracy**，11 类证据类型学，信念修正按证据强度比较。见[研究问题页 §6.1](../00_研究设计/前台问题与候选创新.md) |
| 社会模拟/角色逻辑 | [An Architecture for Character-Rich Social Simulation (CiF)](PDF/2013_Architecture_for_Character_Rich_Social_Simulation.pdf) | [Game AI Pro Ch43](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter43_An_Architecture_for_Character-Rich_Social_Simulation.pdf) | **已补上原 Comme il Faut 缺口**（Mateas & McCoy 本人撰写的架构章）：Traits（永久）/Statuses（临时带 duration）；**私有 social network vs 公开 relationship，须经 exchange 才转化**；influence rules 谓词左部→权重右部；SFKB 保留完整历史（是强 raw-history 基线） |
| affordance 正式化 | [To Afford or Not to Afford](PDF/2007_To_Afford_or_Not_to_Afford_Formalization.pdf) | [Adaptive Behavior 15(4):447–472](https://journals.sagepub.com/doi/abs/10.1177/1059712307084689) | affordance = `(effect, (entity, behavior))`，**三个分量均以 agent 感知为准、关系存放在 agent 侧**；以 effect 为索引可直接作规划算子；三个视角（agent/observer/environment）显式分离。**机器人论文，与心理/游戏 NPC 无关，只搬骨架** |

> SyncStream 文件由 KDD 2014 会议镜像获取。该镜像 TLS 证书已过期，下载时仅为取得用户指定的公开论文而绕过证书校验；随后已校验 `%PDF-` 文件头、首页标题、页码（412 起）及 SHA-256：`9E8A74135B3CDDFC1E21868D8BC6ADF21D3B5D10790658DA3AED2A5B08A3C259`。其规范书目信息以 ACM DOI 为准。

## 当前审计路由（按证据等级）

先读[2026-10-06 全量近邻精读总表](全量近邻精读总表_2026-10-06.md)确定文献覆盖、方法和迁移边界。HSSA 已由 Codex/Luna 代理全文审读并经主代理复核，详见[唯一精读报告](精读_HSSA_2026-10-06.md)；这不表示用户本人阅读、学者确认或方法复现。Cho 全文方法已由主代理核验，但本地无 PDF，引用以正式 ACL/全文入口为准。2009 EMA 本地 PDF 已存在并纳入本轮代理全文审读，替代早前“附件待取得”的路由状态。下载、书目核验、摘要浏览均不可自动记作精读；项目实时阶段见[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)，PredictionBaselineV1 的具体边界见其[开发协议](../02_实验/PredictionBaselineV1/README.md)。

另有两份**工程对照清单**，做 T18 查新或任何"机制新颖"表述前，先过一遍：

- [Paper-0 近邻与 LIGHT 路线审计](专题审计_Paper0近邻与LIGHT路线_2026-09-05.md)：冻结首篇的三项可失败检验，并把 LIGHT 定为 **30–50 条准入审计候选**，不是已可用数据源；PersonaForge、ThinkPersona、AdaMARP 仅按职责登记为待复核近邻。
- [公开轨迹与玩家日志数据资产登记](数据资产登记_玩家日志与公开轨迹_2026-09-06.md)：登记 LIGHT、OPeRA、ClubFloyd、PowerWash、AGAIN、FarmQuest、HEART-BENCH、PersonaX 等候选的可核验规模、用途和访问边界；不等于已准入。

- [三方向近邻核读 §2](专题核读_三方向近邻_2026-09-05.md)：项目当前的 π(A)、承诺惯性、目标优先级、对象动作、前置条件校验 与 2005–2013 年 utility-AI / GOAP 实践的逐条对应物。
- [工程三空白核读 §5](专题核读_工程三空白_2026-09-05.md)：**`W ≠ O` 的先例清单**。Talk of the Town 已实现 ground-truth 与 belief facet 的显式分离、错误信念、证据来源追踪与 Accuracy 对照；HTN 的 world state 与 ETQ 的 context object 是另外两条佐证。**这一条比上一轮清单更硬，直接覆盖原本认为最站得住的那条差异。**
- [Game AI Pro 全景与工程 Gap §1](专题核读_GameAIPro全景与工程Gap_2026-09-05.md)：**为什么有技术却没有游戏这么做**。六条 gap，逐条带原文引句。最硬的一条是 V3 C01 §1.3.6 正面否定"模拟内部状态"路线（"weird obsession… misguided"）；另一条是 V3 C34 记录的主动放弃——planner 性能超预期仍被弃用，理由是"wrong level of abstraction"和"too many of them… to care about them in detail"。**§2 给出"LLM 打破了哪几条、没打破哪几条"的对照表，直接决定项目定位。**
- [工程可复用资产](专题核读_工程可复用资产_2026-09-05.md)：代码包、下载与接口建议以该历史核读为准。其 V3 C04 的玩家辨别结果提示评分可能不敏感，**不支持普遍用 held-out NLL 取代玩家评价**：动作预测与玩家可置信性是不同目标，应分别验证测量方法。二阶知识的零命中严格限于当时检索的 Game AI Pro 146 章，不是“学术界没人做”；TimeToM、DYNToM 与 PsychSim 的近邻边界另见[全量近邻精读总表](全量近邻精读总表_2026-09-01.md)。

每篇统一填写：`W 如何表示 / O 如何受限 / P 如何进入 / S 如何更新 / affordance 如何产生 / action 如何选 / 真实行为如何用于修正或评价`。不能因为论文含有 world、state、belief、action 任一名词就判定与本项目同构。

## 已定位、PDF 待取得

| 文献 | 已确认信息 | 与项目的严格关系 | 当前阻碍 |
|---|---|---|---|
| PSI: *Learning Individual Moving Preference and Social Interaction for Location Prediction* (Wu, Luo, Yang, Shao; IEEE Access 2018; DOI 10.1109/ACCESS.2018.2805831) | 建模 individual moving preference 与 group-level exterior social interaction，并以 pair-wise ridge regression 预测下一地点。 | 仅可比较 `internal preference + external influence → next behavior` 的局部结构；没有可见信息遮罩、世界状态或主观状态转移。 | [学校公开 PDF](https://dm.uestc.edu.cn/wp-content/uploads/paper/Learning%20Individual%20Moving%20Preference%20and%20Social%20Interaction%20for%20Location%20Prediction.pdf) 当前连接超时；IEEE 自动下载端返回 418。 |
| EMA: *A Domain-Independent Framework for Modeling Emotion* (Gratch & Marsella; Cognitive Systems Research 2004; DOI 10.1016/j.cogsys.2004.02.002) | appraisal/coping 将感知、规划、对话管理等连入虚拟人物情绪与行为生成。 | 是主观状态更新机制的基础近邻，不是当前 LLM 角色系统评测。 | 作者旧公开 PDF 链接现返回 404；已导入 Zotero 规范元数据和 DOI，待取得可验证附件。**部分缓解**：2026-09-05 已取得同作者 2009 年 *EMA: A Process Model of Appraisal Dynamics*（自述为 EMA 的 updated description），其 appraisal 维度清单含 2004 版没有的 `expectedness`；2004 原篇仅用于核对版本差异。 |
| ~~*Comme il Faut: A System for Authoring Playable Social Models* (McCoy, Treanor, Samuel, Wardrip-Fruin, Mateas; AIIDE 2011)~~ | **2026-09-05 已关闭**：取得 Mateas & McCoy 本人撰写的 CiF 架构章节（Game AI Pro 卷一 Ch43），覆盖架构全部要素。 | 同上，且已提取 trait/status、私有 network vs 公开 relationship、influence rules、SFKB 四条可用结论。 | ~~galley 链接全部 404~~ 不再需要。若日后要核对 AIIDE 2011 六页短文与图书章节的**版本差异**，再走 Semantic Scholar / OA.mg 全文入口。 |
| *CreatureSmarts: The Art and Architecture of a Virtual Brain* (Burke, Isla, Downie, Ivanov, Blumberg; GDC 2001, pp.147–166) | MIT Media Lab Synthetic Characters 组的 C4 架构，GOAP 底层 agent 架构的直接来源。 | 虚拟角色认知架构的祖先；可用来判断项目架构在多大程度上重走了既有路径。 | 尚未检索公开全文；GDC 2001 论文集多数未公开线上。 |
| *Social Activities: Implementing Wittgenstein* (Evans, Barnet; GDC 2002) | 把维特根斯坦语言游戏式的社会活动实现为游戏 AI 结构。 | Versu 一脉的早期工作；与 Comme il Faut 同为「社会规则可计算」的代表。 | 尚未检索；GDC 2002 论文集公开性未知。 |

## 尚待补齐/核验

- **落地游戏工程三块空白已于 2026-09-05 补齐**（HTN、affordance 正式化、中断/部分失败语义），核读见 [工程三空白](专题核读_工程三空白_2026-09-05.md)。
- **Game AI Pro 覆盖问题已解决**：全 4 卷 146 章（官网宣称 149，目录实列 146）已建完整分级清单，A 级 43 章全部下载到位。见 [Game AI Pro 全景与工程 Gap](专题核读_GameAIPro全景与工程Gap_2026-09-05.md) §5 附录。
- **当前最大的未读量**：A 级 43 章中**逐节核读仅 8 章**，其余 35 章已下载并提取文本但未读。B 级 30 章未下载、未读。C 级 73 章（寻路/转向/人群/赛车/摄像机/动画/MCTS 等）判定为与机制链无对应，不读，但该排除须在 T18 查新报告中显式声明理由。跟踪见 TODO 的 T23b。
- 原始对话中提到的心理学书章、用户建模、AI Town、PersonaForge GitHub 等，需要作为“实现或理论线索”另行登记；它们不能替代论文阅读。
- 每篇论文需先完成：题目/版本/作者核对、任务与数据、状态定义、信息可见性、评测、可比与不可比边界；之后才可写入近邻地图或研究问题。
