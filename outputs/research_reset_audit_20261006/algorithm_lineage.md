# Character Dynamics 算法谱系与论文证据审计

审计日期：2026-10-06  
工作树：`webgpt-sync`，起始状态 `6d488f8`，审计开始时 clean  
范围：只读核验论文、研究问题与候选协议；本报告不构成实现、模型、实验或分支决策。

## 结论先行

- **[论文证据]** SyncStream 是监督式数据流分类器：它在持续到达且随后可获得类别标签的数据上，在线挑选、压缩并维护有预测价值的带标签样例，最后以最近邻预测类别。它研究的是 `P(Y|X)` 的数据分布/目标概念随数据流变化，不是角色的心理状态 `S_t` 随时间变化。
- **[从论文推断]** 如果把“概念漂移”直接类比成“角色心理漂移”，属于对象层级错误。角色心理变化必须有可解释的观测、appraisal、状态写入和动作后果；SyncStream 的 `Rep` 是分类正确性驱动的训练样例代表性分数，没有心理含义、效价或因果状态语义。
- **[论文证据]** 2009 EMA、2012 FAtiMA-PSI 和 PsychSim 分别提供 appraisal/coping 流程、驱动—预期成功—目标选择机制、信念/偏好—有限前瞻动作选择的可计算先例；但其自身数据或评测均不能证明当前 `ResearchDynamicsV1` 的四个字段、固定速率或角色动作预测有效。
- **[项目决定]** 当前协议里 `fatigue/task_pressure/boredom/satisfaction` 的定义和常数仍是工程候选。借用某论文的术语或公式，不等于继承其构念验证。若要继承，必须把源论文的计算对象、输入、更新、可观察证据和验证指标逐项映射到本项目，并保留有标签的独立行为真值与对照。
- **[开放问题]** Paper-0 所需的独立 `A*`、角色级合法历史、冻结的 `A^O` 和无泄漏 held-out NLL 仍是先决条件；此次阅读没有替这些准入问题解锁实验。

## SyncStream：模块、来源和逐段验证链

规范文献：Junming Shao, Zahra Ahmadi, Stefan Kramer, “Prototype-based learning on concept-drifting data streams,” *Proceedings of the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD ’14)*, 2014, pp. 412–421, DOI [10.1145/2623330.2623609](https://doi.org/10.1145/2623330.2623609)。本地原文：[2014 SyncStream PDF](../../01_文献/PDF/2014_SyncStream_Prototype_based_Learning_on_Concept_Drifting_Data_Streams.pdf)。全文共 10 个 PDF 页面；以下页码同时注明论文印刷页。官方来源链接和首页 DOI 与本地 PDF 相符。

| 模块 | 原文位置与算法实义 | 来源/来源性质 | 原文中的检查链与可迁移边界 |
|---|---|---|---|
| 输入、在线预测 | §3.1、§3.5，PDF p.2、p.6（印刷 pp.413、417）；新样例 `x` 到来时，在 P-Tree 中找最近 prototype `y`，用 `y.label` 预测 `x` 的类别。 | 最近邻/实例学习；论文把它用作整体预测器。 | 每个新样例形成一次类别预测。输入必须是有标签训练流中的样例特征，不是无监督心理“状态”。 |
| 监督误差驱动的代表性 `Rep` | §3.4.1、Algorithm 1，PDF pp.5–6（印刷 pp.416–417）；`Rep(y) := Rep(y) + Sign(predicted_label, true_label)`，初值 1，预测正确加 1、错误减 1。后续由 `Rep` 决定删除、保留或归并样例。 | 本文提出的在线维护规则，不是心理测量；其监督信号是样例真实类别。 | 每个预测后取得该条样例的真标签，再把误差反馈至被最近邻命中的 prototype。若本项目没有独立 `A*`，不得把模型自选动作回灌为等价监督信号；即使有 `A*`，得到的也是动作预测记忆的价值，不是 `S` 的心理意义。 |
| Synchronization-inspired、类别约束聚类 | §3.2，PDF pp.3–4（印刷 pp.414–415）；特征向量各维被视作相位振子，与 ε 邻域内同类样例按 `x_i(t+1)=x_i(t)+(1/|Nε(x)|)Σ_y sin(y_i(t)-x_i(t))` 互动；异类对施加 cannot-link，不互动。局部 order parameter `R_c` 收敛后，同相样例成为 prototype。 | 核心谱系为 Böhm, Plant, Shao & Yang, “Clustering by Synchronization,” KDD 2010, DOI [10.1145/1835804.1835879](https://doi.org/10.1145/1835804.1835879)。SyncStream 是将同步聚类适配到有标签、在线数据流摘要。 | 论文用合成数据可视化相位聚合，并报告 prototype 保持样例的局部结构与类别分布。振子方程表示特征空间中的聚类过程；它不是人体情绪振荡模型，也不说明相似心理事件会自然“同步”。 |
| 突变概念检测（PCA） | §3.3.1、Algorithm 1，PDF pp.4、6（印刷 pp.415、417）；按类分别比较连续两块数据的协方差主特征向量，取最大夹角 `Angle(D_t,D_{t+1}) = max_l acos(v_{t,l}·v_{t+1,l})`；实验阈值为 60°。 | 经典 PCA 被本文用作概念变化启发式。 | 在作者生成的 gradual/sudden moving-hyperplane 流上，对比两个检测方式：渐变时角度小于 10°；突变时超阈值识别。只验证流中类条件几何变化，不验证人物状态改变。 |
| 突变概念检测（秩统计） | §3.3.2、Algorithm 1，PDF pp.4–6（印刷 pp.415–417）；按类比较相邻数据块，按每个特征维度的 pooled rank 形成统计量，扩展 Brunner–Munzel 广义 Wilcoxon 检验，最小 p 值作为漂移强度；实验阈值 `p≤0.01`。 | 基础统计源：Brunner & Münzel (2000), “The Nonparametric Behrens-Fisher Problem: Asymptotic Theory and a Small-Sample Approximation,” *Biometrical Journal* 42(1):17–25, DOI [10.1002/(SICI)1521-4036(200001)42:1%3C17::AID-BIMJ17%3E3.0.CO;2-U](https://doi.org/10.1002/%28SICI%291521-4036%28200001%2942%3A1%3C17%3A%3AAID-BIMJ17%3E3.0.CO%3B2-U)；SyncStream 另引 Brunner, Munzel & Puri 2002 多元版本。 | 仍然检测带标签类别在特征分布上的统计差异。统计显著性不等于心理显著性；项目不能把某字段突然改变或超阈值自动解释成角色“情绪转变”。 |
| P-Tree 分层记忆和容量维护 | §3.4.2、Algorithm 1，PDF pp.5–6（印刷 pp.416–417）；第一层保存当前变化中的 prototypes，第二层存储检测/定期汇总出的历史 concepts。容量 `maxP` 满时删低 `Rep` 项，保留高 `Rep` 项，将 `Rep` 未变项重新聚类；`maxC` 满时删最旧 concept。检测到明显突变时，把当前 prototypes 聚类归档并清空当前层；仅周期性摘要时不清空。 | 本文提出的数据结构和操作规则。 | `maxP/maxC/chunkSize/T` 是内存与检测边界；§4.4 只改变 `maxP` 与 chunk size 检查敏感性。若项目需要“重复情境检索”，可把这类受容量约束的原型记忆作为单独预测 baseline；不能把它当成每个角色的持续心理 `S`。 |
| 整体预测和实验比较 | §3.5、§4，PDF pp.6–10（印刷 pp.417–421）；P-Tree prototypes 以最近邻分类。对比 Adaptive Hoeffding Tree、IBLStreams、Weighted Ensemble、OzaBagAdwin、PASC；指标为 Accuracy/Precision/Recall/F1 和处理耗时。 | 数据流分类实验。 | 数据含两条各 100 万样例 moving-hyperplane 合成流，及 Spam 9,324、Electricity 45,312、Covtype 581,012、Sensor 2,219,803 条真实样例；报告不同处理量下曲线及完整集性能。实验报告主要是逐数据流汇总值，无 actor/session held-out、无人物独立 `A*`、无消融单独拆掉 `Rep`/聚类/P-Tree 的因果比较。 |

**证据强度与限制**

- **[论文证据]** 它在监督数据流分类任务中，用多个真实数据集和合成渐变/突变流演示整体系统表现，并将 SyncStream 与五类流分类器比较。对照覆盖了不少常见方法；§4.4 也检查 `maxP`、chunk size 对性能/时间/检测概念数的敏感性。
- **[论文证据]** 这是在线监督设定：Algorithm 1 在当前样例被预测后使用其 `x.label` 更新 `Rep`。其核心增量不是“只保存有代表性的历史”这一抽象，而是“类别预测误差更新 prototype 分数 + 同类约束同步压缩 + 概念级分层归档/漂移启发式”。
- **[论文证据]** 局限：论文没有把每个模块逐一移除的消融；没有用户/个体拆分或未来时间段独立 held-out；没有展示对真实人类行为动作的预测；检测阈值和容量部分靠人工设定；绝对性能与耗时是特定 Java / 3GHz CPU / 32GB RAM 环境和数据流的报告值。
- **[从论文推断]** 可以借鉴的是一条可检验的“历史片段—下一动作”预测记忆 baseline：用过去的可见观察/上下文作 prototype，按独立 `A*` 预测误差累计代表性，按记忆预算压缩，再在独立 actor/session split 上与 raw history、summary、no-S 等比较。那是**预测记忆/压缩基线**，不是把 SyncStream 改名成 `ResearchDynamicsV1`，也不证明字段级状态更新必要。

## 另外三篇深读论文和一篇筛查论文

### 1. EMA：把情绪动力学放在“解释—appraisal—coping”流程中

规范文献：Stacy C. Marsella & Jonathan Gratch, “EMA: A Process Model of Appraisal Dynamics,” *Cognitive Systems Research* 10(1), 2009, pp.70–90, DOI [10.1016/j.cogsys.2008.03.005](https://doi.org/10.1016/j.cogsys.2008.03.005)。官方出版商记录：[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1389041708000314)。本地原文：[2009 EMA PDF](../../01_文献/PDF/2009_EMA_Process_Model_of_Appraisal_Dynamics.pdf)，PDF 21 页（文章分页 70–90）。

- **[论文证据｜§2.3.1–2.3.3，PDF pp.8–10，文章 pp.78–80]** EMA 的核心状态表示是 causal interpretation：由过去事件、当前世界命题、可能未来结果/计划构成，动作有前置条件与效果，因果链接表达结果如何建立/破坏其他动作条件。命题带 belief/utility/概率等标注。Appraisal 不负责写入这个表示，而是对其命题运行快速、并行的 appraisal feature detectors；心理过程通过感知、推理、规划和行动改变表示，再导致 appraisal 变化。
- **[论文证据｜§2.3.3，文章 pp.80–82]** appraisal 涉及 relevance、valence/intensity、likelihood、expectedness、causal attribution、goal conduciveness、urgency、control/power、normative significance 等维度。一个事件的多个结果可并行 appraisal；不同 appraisals 形成 emotion frames，当前被注意的 frame 受 mood-adjusted intensity 影响。
- **[论文证据｜§2.3.5，文章 pp.82–83]** coping 是对 belief、desire、intention、plan、attention 等结构的控制信号；策略包含寻求信息、压制监测、改变因果归因、wishful thinking、降低目标重要性、重规划、回避、拖延、放弃等。策略由 control/changeability 等条件择取，作用会改变后续表示并形成 re-appraisal 闭环。
- **[论文证据｜§3–4，文章 pp.83–89]** 论文以一段意外鸽子飞入实验室、演员 2.6 秒反应的视频作自然情境示例，编码一个可解释的状态/计划/事件序列，并展示模型怎样产生惊讶、恐惧、防御、对鸟关切等变化。作者明确说该示例是解释性建模，不是对演员真实心理过程的确认，也不是严格实验验证；需更约束的实验来区分模型假设。
- **[论文证据｜§2.3.1 注3，文章 p.79；§4，pp.87–89]** 关键边界：当时 EMA 对过去/当前命题假设完全可观察，只有未来结果和他人意图有概率不确定性。这与 Paper-0 的 stale/unknown 局部观察有直接冲突；作者也承认自然示例的领域编码存在建模者主观性，且物理/心理过程时程设定很浅、部分延迟参数自由。
- **[从论文推断]** 项目真正可继承的是“输入观察变化 → 形成带时间/因果/视角的解释 → 独立 appraisal → 以策略修改解释/目标/意图 → 新行动与重新评价”这一机制分层和可干预性。若把 EMA 变量压成四个静态标量，只保留 emotion 名称而删除因果解释和 coping，就没有继承其方法。
- **[项目决定]** 当前协议可以把 EMA 当作候选机制参照，但必须自行解决观测不完整、旧信念、信源/时间、状态变量操作定义与独立动作评估；不要声称 EMA 为 `boredom`、`fatigue` 或 `[0,1]` 固定恢复率提供了验证。

### 2. FAtiMA-PSI：NPC 中把 appraisal、驱动、学习与规划接起来

规范文献：Mei Yii Lim, João Dias, Ruth Aylett & Ana Paiva, “Creating Adaptive Affective Autonomous NPCs,” *Autonomous Agents and Multi-Agent Systems* 24(2), 2012, pp.287–311, DOI [10.1007/s10458-010-9161-2](https://doi.org/10.1007/s10458-010-9161-2)。官方机构出版记录：[Heriot-Watt Research Portal](https://researchportal.hw.ac.uk/en/publications/creating-adaptive-affective-autonomous-npcs/)。本地原文：[2012 FAtiMA PDF](../../01_文献/PDF/2012_FAtiMA_Creating_Adaptive_Affective_Autonomous_NPCs.pdf)，PDF 31 页。

- **[论文证据｜§4.1，PDF pp.7–14]** 原有 FAtiMA 有两层 appraisal/决策：预置规则对外部事件作快速 OCC appraisal；deliberative 层根据 intention 的成败与预期成功率 appraisal，再做 BDI 风格计划。作者指出原 FAtiMA 需手写大量事件 desirability、目标、动作倾向、阈值和 decay，规则与参数交互难以调校，也不从经验自适应。论文将 PSI 的 homeostatic drives、经验学习组件并入架构，形成 FAtiMA-PSI。
- **[论文证据｜§4.2，PDF pp.15–24，尤其 pp.19–22]** 情景中的 energy、integrity、affiliation 等需求值受行动和外部反馈影响；certainty 根据期望与实际结果的误差，以 `Uncertainty_t(g)=α·ObservedError_t(g)+(1−α)·Uncertainty_{t−1}(g)` EMA 更新；competence 按成功概率与失败概率之差变化（`k·P(g)−k·(1−P(g))`）。目标 utility 汇总其对多个驱动的作用，再与 expected competence、urgency 相乘；一个 selection threshold 控制新目标替换当前 intention 的机会，避免行为来回切换。目标成功/失败概率来自该角色在具体目标上的试做记录。
- **[论文证据｜§5，PDF pp.24–27]** 角色在 meal、recycling、gardening 三个 ORIENT 情景运行；图示展示一段短交互前后的 drives、Evui 违规—被教育—道歉—被原谅序列中的状态变化。这些是系统运行案例。
- **[论文证据｜§5，PDF p.27]** 作者明确承认：没有评估新架构相对 FAtiMA 或 PSI 在技术上的改进（例如 authoring 成本或角色行为），且无法孤立比较。ORIENT 的用户研究是 UK/Germany 各 4 组、每组 3 名青少年、约 2 小时的游戏体验/跨文化意识与沉浸评估；参与者觉得 Sprytes 有趣可信，但也认为个体人格差异仍不足。这不是状态机制对独立下一动作的预测检验或 ablation。
- **[从论文推断]** 可迁移的具体方法是：由可测的 action outcome 更新“特定目标成功概率/不确定性”，让驱动与当前情境的缺口共同影响 goal utility，随后用显式 commitment/threshold 选择意图。要借用就应先有可复现的目标、动作结果、试验次数、预测概率和误差记录，并将这套目标层算法与 static persona、raw history、naive EMA 等基线比较；不能只拿 EMA 公式套给 `satisfaction` 就宣称相同理论。
- **[项目决定]** 该文是强 NPC 架构先例，同时也是“机制做出来 + 体验反馈不错”仍不足以证明内部状态算法优越的反例。当前四个 ResearchDynamicsV1 字段与此处的 homeostatic drives 不同，阈值/速率也不是从本文估计得来。

### 3. PsychSim：显式世界转移、主体信念、偏好和决策的因果连接

规范文献：David V. Pynadath & Stacy C. Marsella, “PsychSim: Modeling Theory of Mind with Decision-Theoretic Agents,” *Proceedings of IJCAI-05*, 2005, pp.1181–1186。官方原文：[IJCAI Proceedings PDF](https://www.ijcai.org/Proceedings/05/Papers/1559.pdf)。本地原文：[2005 PsychSim PDF](../../01_文献/PDF/2005_PsychSim_Modeling_Theory_of_Mind_with_Decision_Theoretic_Agents.pdf)，PDF 6 页。

- **[论文证据｜§2.1–2.3，PDF pp.2–3]** agent 有客观 state vector、由动作驱动的概率转移、可各自不同的主观 belief、目标偏好 reward 权重。部分客观事实对主体隐藏；主体按照 belief 对候选动作做有限前瞻，通过转移和其他 agent 的政策推演后续状态并最大化预期 reward。作者明确把有限前瞻、信念错误视为 bounded rationality，而不是完美理性。
- **[论文证据｜§2.3–2.4，PDF pp.3–5]** belief 含关于世界和其他主体信念/偏好/政策的递归模型；示例使用两层 ToM，深层用 stereotype policy 控制计算复杂度。主体观察到他人行为或收到信息后，可按 prior history 的一致性、自身利益、说话方利益、trust 与 support 等因素评估信念变化；信任/支持随历史接受信息与行为反馈更新。
- **[论文证据｜§3.1–3.2，PDF pp.4–5；Table 1 PDF p.6]** school-bullying 场景对 dominance-seeking、sadistic、attention-seeking 三种人工设定的 bully、教师干预、同学反应及主体 mental models 进行组合模拟，汇报下次是否再次攻击受害者。目标是条件分析/what-if 解释，不是与真实行为 held-out 数据比预测准确率；作者结尾仍把扩大场景与应用评估列为后续目标。
- **[从论文推断]** 对 Paper-0 最可继承的结构是把 `W` 转移、每个角色的 `O/belief`、目标/偏好、`π(A)` 拆开，并将“同一可见证据因主体信念/偏好不同而导致不同动作”变成可干预的对照。它能启发动作条件分析和敏感性报告，但不能给本项目的四个心理字段、学习规则或人格解释背书。
- **[项目决定]** PsychSim 是 `W≠O`、偏好加权动作与反事实决策的强工程/方法先例；若纳入实验，必须把人工场景结果和外部真实 `A*` 预测分别报告，不能把可解释的模拟行为等同心理验证。

### 未列入四篇深读：Hierarchical State Space Affective Dynamics

文献信息核验：Tom Lodewyckx, Francis Tuerlinckx, Peter Kuppens, Nicholas B. Allen & Lisa Sheeber, “A hierarchical state space approach to affective dynamics,” *Journal of Mathematical Psychology* 55 (2011), pp.68–83, DOI [10.1016/j.jmp.2010.08.004](https://doi.org/10.1016/j.jmp.2010.08.004)。本地文件名带 `2010_`，但 2010 是在线发表时间/投稿年份，卷期出版年为 2011。

- **[论文证据｜摘要、§2–3、§4]** 该文比前三篇更直接地展示了如何以线性状态空间模型估计个体内动力学及群体间参数差异：层级 Bayesian random effects + latent physiological states；样本是 66 名正常与 67 名抑郁青少年，在亲子冲突任务中采集每秒 HR、BP 与亲代愤怒行为编码；报告状态持续、交叉滞后、反应性及组间差异。
- **[论文证据]** 作者明确讨论线性、高斯噪声和连续观测等假设限制；其输出变量是生理测量，不是角色离散动作，其输入为编码的亲代行为，不是以状态充分性为估计对象的 `S`。
- **[筛选理由]** 这篇是值得后续深入的个体差异动力学估计方法，但此次按任务限制选它之外的四篇作为深读：SyncStream、EMA、FAtiMA-PSI、PsychSim 覆盖了状态压缩、心理过程、NPC 集成和动作决策四类不同谱系。HSSA 已作摘要/适配度筛查，不将其写成完整精读结论。

## 项目中“真正继承方法”的最低要求

| 若要继承 | 必须继承的对象和计算 | 不足以称为继承的做法 | 必须补上的验证 |
|---|---|---|---|
| SyncStream | 可见历史片段成为带 `A*` 标签的预测样例；用预测错误更新样例代表性；限定记忆预算；在线或分块检测分布变化；独立评估压缩对预测的影响。 | 把 `Rep` 叫心理重要性；把类别分布变了叫人物心理漂移；拿 prototype 替代可解释 `S`。 | 对 actor/session 留出；`A*` 独立于模型；无泄漏；与 raw history、summary、no-S、capacity-matched permutation 对比；每模块消融。 |
| EMA | 显式 causal interpretation；事件/命题/计划与观测可信度；appraisal 与表示更新分离；coping 策略修改 belief/goal/intention 并产生后续重评。 | 把四个命名字段和固定速率直接说成 EMA 或 appraisal theory。 | 缺失/陈旧观测处理、字段操作化依据、被解释的状态变化与独立动作结果、相对更简单状态模型的 held-out 检验。 |
| FAtiMA-PSI | 需求状态由行动及后果改变；根据真实成功/失败误差维护目标级概率/不确定性；多个目标的预期满足程度进入 utility；意图 commitment 与切换阈值显式定义。 | 只复制 `αx_t+(1−α)x_{t−1}`，却没有目标成功概率、真实 outcome 与 utility 决策链。 | 相对原始 FAtiMA/PSI 或簡单 EMA baseline 的作者也承认未完成；本项目需独立做消融/行为预测，不以可运行的情景图代替机制比较。 |
| PsychSim | 明确分离真世界转移和主体 belief；动作分布由有限前瞻、主体 reward/偏好与观测模型生成；对不同 beliefs/preferences 做配对干预。 | 将全局世界 state 暴露给角色，或把人工模拟输出叫真实人类真值。 | 固定合法观察权限和 `A^O`；比较同信息、同容量的不同状态条件；配对 seed/session；用外部 `A*` 评价预测，而不是只看世界内部目标是否成功。 |

## 对当前协议的约束性读法

- **[项目文件证据]** `00_研究设计/Paper-0问题卡.md` 将问题限定为：在局部可观测、可回放单角色 Forward 环境中，检验持久 `S` 对下一动作预测的近似充分性及必要性；主指标是 held-out action NLL；独立真值 `A*` 不可由 E0 自生成动作替代。这个问题与 SyncStream 的流分类任务不是同一 estimand。
- **[项目文件证据]** `00_研究设计/Research_Dynamics_V1_Protocol.md` 明确把 `ResearchDynamicsV1` 标为候选、未冻结，常数为 transparent development constants、阈值为 engineering controls，而非拟合值/人格阈值；字段可观测证据暂定来自 action duration、deadline delta、visible event/action family、typed outcome。
- **[从论文推断]** 就现有原文而言，四字段与 EMA/FAtiMA/PsychSim 都只能做“候选机制映射”，没有被这些论文以当前字段、当前单位和当前更新常数进行过校准。若研究目标保持 Paper-0，应先锁定独立行为真值/动作候选空间及数据准入，然后再决定是否比较理论驱动状态 `S`；不要先把手调状态方程包装成心理学模型。
- **[开放问题]** 如果用户目标改为让 NPC 出现更有生活感、但暂不主张科学有效性，那么 FAtiMA/PSI 的驱动—目标实践可作为工程先例；这与 Paper-0 的科研证据路线须分开记账。

## 来源、版本及文件核验

- 项目边界文件已核读：`AGENTS.md`、`README.md`、`00_研究设计/README.md`、`01_文献/README.md`、`00_研究设计/Paper-0问题卡.md`、`00_研究设计/Research_Dynamics_V1_Protocol.md`、`00_研究设计/当前实现进度.md`、`90_原始材料/2026-09-01_动态人物世界模拟探索/阅读判断.md`。
- SyncStream 本地原文 10 PDF pages，首页标题/作者/DOI与 ACM DOI 一致；算法核心页 PDF pp.3–6、实验 pp.6–10 已文本抽取并视觉检查 PDF p.3。
- EMA 本地原文 21 PDF pages，与 ScienceDirect 题名/作者/卷期/年份/页码/DOI一致；causal interpretation 与限制页已视觉检查 PDF p.9。
- FAtiMA 本地原文 31 PDF pages，与 Heriot-Watt 官方机构记录给出的作者、期刊、2012 年、卷期、页码和 DOI 一致；算法公式与结论/评估局限页已核文本，评估页 PDF p.18 已视觉检查。
- PsychSim 本地原文 6 PDF pages，与 IJCAI 官方 proceedings PDF 首页题名/作者一致；来源显示 IJCAI-05，pp.1181–1186。状态/ToM 页和结果表已抽取，模型因素页 PDF p.4 已视觉检查。
- HSSA 本地原文首页显示 2011 卷期、pp.68–83，online availability 20 Oct 2010，DOI `10.1016/j.jmp.2010.08.004`；因此本地文件名 `2010_...` 不应当作正式发表年。
- 所有 PDF 保持原样；文本与页面图像提取只用于本地临时核查，存于 `tmp/pdfs/algorithm-lineage/`，不构成研究结果或正式实验产物。
