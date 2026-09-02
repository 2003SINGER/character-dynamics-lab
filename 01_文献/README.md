# 本地文献库

更新时间：2026-09-02  
状态：**28 篇 PDF 已下载并以 `%PDF-` 文件头校验；2 篇已定位但待取得。** 下载只表示可离线阅读，不表示已精读、已认可其中论断，或已完成查新。

已完成的项目审计入口：[全量近邻精读总表（2026-09-01）](全量近邻精读总表_2026-09-01.md)。它记录了每篇的覆盖范围、对本项目的边界、可借方法和必读顺序。

## 检索原则

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
| 角色系统 | [Generative Agents](PDF/2023_Generative_Agents_Interactive_Simulacra_of_Human_Behavior.pdf) | [arXiv](https://arxiv.org/abs/2304.03442) | 观察—记忆—反思—计划式角色 agent 的基础近邻 |
| 角色评测 | [InCharacter](PDF/2024_InCharacter.pdf) | [ACL](https://aclanthology.org/2024.acl-long.102/) | 人格 fidelity 的直接近邻 |
| 局部可观测 | [TimeToM](PDF/2024_TimeToM_Temporal_Belief_State_Chain.pdf) | [ACL](https://aclanthology.org/2024.findings-acl.685/) | 时间化角色 belief state，避免把遮罩单独误作创新 |
| 角色系统 | [CharacterBox](PDF/2025_CharacterBox.pdf) | [ACL](https://aclanthology.org/2025.naacl-long.323/) | 文本虚拟世界与行为轨迹近邻 |
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
| 数据流/状态维护 | [SyncStream: Prototype-based Learning on Concept-drifting Data Streams](PDF/2014_SyncStream_Prototype_based_Learning_on_Concept_Drifting_Data_Streams.pdf) | [ACM DOI](https://doi.org/10.1145/2623330.2623609)；[KDD 2014 会议镜像](https://archive.gersteinlab.org/meetings/s/2014/08.28/kdd2014-i0kdd-meeting-materials/docs/p412.pdf) | 保留历史应按预测代表性而非仅按时近性；**不是**人物心理或角色模型 |
| 动态行为预测 | [DGPS: Learning evolving user’s behaviors on location-based social networks](PDF/2020_DGPS_Learning_Evolving_User_Behaviors_on_Location_Based_Social_Networks.pdf) | [Springer DOI](https://doi.org/10.1007/s10707-020-00400-3)；[作者公开 PDF](https://people.cs.vt.edu/~clu/Publication/2020/Geoinformatica-Wu-2020.pdf) | 个人偏好、社会连接与时间过程共同预测 check-in；只覆盖本项目“动态行为预测”一侧，不含主客观分离或主观状态更新 |
| 多主体心理模型 | [PsychSim](PDF/2005_PsychSim_Modeling_Theory_of_Mind_with_Decision_Theoretic_Agents.pdf) | [作者公开 PDF](https://people.ict.usc.edu/~pynadath/Papers/ijcai05.pdf) | factored ground-truth decision state、主体 belief、偏好决策与有限 mental-model revision 的直接先例；其 World 不应直接等同为对象化可执行世界层 |
| 认知—情感 NPC | [Creating Adaptive Affective Autonomous NPCs](PDF/2012_FAtiMA_Creating_Adaptive_Affective_Autonomous_NPCs.pdf) | [AAMAS DOI](https://doi.org/10.1007/s10458-010-9161-2)；[作者公开 PDF](https://www.macs.hw.ac.uk/~ruth/Papers/agents-affect/JAAMAS-final.pdf) | 感知、动机、情绪、记忆、学习、规划共同驱动 NPC 的直接先例 |
| 交互叙事 | [BDI Model for Narrative Generation](PDF/2013_BDI_Model_for_Narrative_Generation.pdf) | [AIIDE](https://ojs.aaai.org/index.php/AIIDE/article/view/12627) | 以 belief/desire/intention 建模角色动机与动作；belief 实现假定全知，不能替代局部可观测问题 |
| 动态心智评测 | [DYNToM](PDF/2025_DYNToM_Dynamic_Theory_of_Mind_Benchmark.pdf) | [ACL](https://aclanthology.org/2025.acl-long.1171/) | 连续情境中的 belief–emotion–intention–action 轨迹与转移评测；是动态状态合理性问题的直接近邻 |
| 角色模拟/评测 | [PersonaArena](PDF/2026_PersonaArena_Dynamic_Simulation_for_Evaluating_and_Enhancing.pdf) | [ACL](https://aclanthology.org/2026.findings-acl.471/) | 环境 agent 更新环境与角色状态，并评测行为连贯性；直接削弱“闭环模拟+一致性评测”作为创新 |

> SyncStream 文件由 KDD 2014 会议镜像获取。该镜像 TLS 证书已过期，下载时仅为取得用户指定的公开论文而绕过证书校验；随后已校验 `%PDF-` 文件头、首页标题、页码（412 起）及 SHA-256：`9E8A74135B3CDDFC1E21868D8BC6ADF21D3B5D10790658DA3AED2A5B08A3C259`。其规范书目信息以 ACM DOI 为准。

## 当前阅读入口（按计算职责，不按大词相似）

先读以下五篇，而不是顺着库逐篇读：

1. [Generative Agents](PDF/2023_Generative_Agents_Interactive_Simulacra_of_Human_Behavior.pdf)：核验对象世界、局部观察、记忆和行为之间到底怎样接口；它是 `W → O` 的强工程近邻。
2. [PsychSim](PDF/2005_PsychSim_Modeling_Theory_of_Mind_with_Decision_Theoretic_Agents.pdf)：核验 factored ground-truth decision state、belief/preference 决策与有限 inverse revision；它的 `World` 不应直接等同为本项目对象化可执行 `W`。
3. [Dynamic Persona Coherence](PDF/2026_Dynamic_Persona_Coherence.pdf)：核验稳定 identity、动态状态和长中短期更新具体怎样实现。
4. [BehaviorChain](PDF/2025_BehaviorChain.pdf)：核验 raw history/context 如何直接得到下一行为；它可提供预测任务，却不替代内部状态动力学。
5. [FAtiMA](PDF/2012_FAtiMA_Creating_Adaptive_Affective_Autonomous_NPCs.pdf)（EMA 附件待取得）：核验事件怎样进入 belief/memory/appraisal/affect 并影响行为。

每篇统一填写：`W 如何表示 / O 如何受限 / P 如何进入 / S 如何更新 / affordance 如何产生 / action 如何选 / 真实行为如何用于修正或评价`。不能因为论文含有 world、state、belief、action 任一名词就判定与本项目同构。

## 已定位、PDF 待取得

| 文献 | 已确认信息 | 与项目的严格关系 | 当前阻碍 |
|---|---|---|---|
| PSI: *Learning Individual Moving Preference and Social Interaction for Location Prediction* (Wu, Luo, Yang, Shao; IEEE Access 2018; DOI 10.1109/ACCESS.2018.2805831) | 建模 individual moving preference 与 group-level exterior social interaction，并以 pair-wise ridge regression 预测下一地点。 | 仅可比较 `internal preference + external influence → next behavior` 的局部结构；没有可见信息遮罩、世界状态或主观状态转移。 | [学校公开 PDF](https://dm.uestc.edu.cn/wp-content/uploads/paper/Learning%20Individual%20Moving%20Preference%20and%20Social%20Interaction%20for%20Location%20Prediction.pdf) 当前连接超时；IEEE 自动下载端返回 418。 |
| EMA: *A Domain-Independent Framework for Modeling Emotion* (Gratch & Marsella; Cognitive Systems Research 2004; DOI 10.1016/j.cogsys.2004.02.002) | appraisal/coping 将感知、规划、对话管理等连入虚拟人物情绪与行为生成。 | 是主观状态更新机制的基础近邻，不是当前 LLM 角色系统评测。 | 作者旧公开 PDF 链接现返回 404；已导入 Zotero 规范元数据和 DOI，待取得可验证附件。 |

## 尚待补齐/核验

- 原始对话中提到的心理学书章、用户建模、AI Town、PersonaForge GitHub 等，需要作为“实现或理论线索”另行登记；它们不能替代论文阅读。
- 每篇论文需先完成：题目/版本/作者核对、任务与数据、状态定义、信息可见性、评测、可比与不可比边界；之后才可写入近邻地图或研究问题。
