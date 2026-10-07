# Character Dynamics 最近邻论文核验（bounded comparison）

核验日期：2026-10-06  
范围：只核对 Paper-0 问题卡与六篇指定近邻；本地 PDF 全文用于定位证据，文末链接为正式书目/出版入口。此文件位于 Git 忽略的 `outputs/`，不修改研究决策、代码或实验数据。

## 结论先行

**目前能排除“动态角色状态”“长历史预测下一行为”“状态随情境演化”“角色状态/局部知识边界”“预测充分状态”这些单项作为新颖性主张。** 近邻论文分别已覆盖：生成式角色的观察—记忆—反思—规划闭环（Generative Agents）；从 persona、history、prior behavior、context 预测小说/传记行为的连续链基准（BehaviorChain）；角色在虚拟世界中的 belief、memory、state 更新和轨迹评测（CharacterBox）；belief/emotion/intention/action 随连续场景变化的测评（DYNToM）；stable identity + cumulative adaptive state + 轨迹纠偏（Dynamic Persona Coherence）；以及一般受控动力系统中的 predictive state / history sufficiency（PSR）。

它们**没有共同完成** Paper-0 所设想的具体可失败检验：在冻结的角色可见信息 `O` 和有限候选集 `A^O` 下，以独立于待测系统的下一行为 `A*` 为标签，比较 `S`、raw/structured history、强 summary 与容量匹配的置换/朴素状态；按角色或 session 留出，并报告 NLL/成本。这个组合仍只是一个**待验证的实验问题**，不是已查证的新颖性；本轮不能推出“没人做过”，也不能推出心理机制成立。

## 六篇的可比边界

| 文献与角色 | 任务、状态与可训练对象 | 标签/基线/切分/指标 | 直接覆盖与未覆盖 |
|---|---|---|---|
| [Generative Agents（UIST 2023）](https://doi.org/10.1145/3586183.3606763)；[本地 PDF](../../01_文献/PDF/2023_Generative_Agents_Interactive_Simulacra_of_Human_Behavior.pdf) | 25 个角色在小镇沙盒中行动；agent 将观察写入自然语言 memory，检索、反思并计划。论文评估的是一套可运行的 LLM agent architecture，不是训练一个可识别的心理状态转移模型。见 §4–5、PDF pp. 5–12。 | controlled study 以人类受试者对单角色行为做排序，另有两日端到端模拟的人类评价；组件消融 memory/observation、planning、reflection。受试者排名按组做非参数检验。没有独立真实人物下一动作标签、held-out user/session split、候选动作 NLL 或稳定 cost/accuracy 曲线；作者称两日模拟成本达数千美元。见 §6.1–6.3、PDF pp. 13–15、§8.2 p.17。 | **覆盖**受观察约束的记忆—反思—规划角色闭环、组件消融和角色行为可置信度评测。**不覆盖**独立人类行为预测真值或 `S` 对完整合法历史的增量/非劣效检验。其随机消融支持架构组件影响人类评分，不是心理因果证据。 |
| [BehaviorChain（Findings ACL 2025）](https://aclanthology.org/2025.findings-acl.813/)；[本地 PDF](../../01_文献/PDF/2025_BehaviorChain.pdf) | 输入为 persona profile、历史叙述、此前 context–behavior 节点与当前 context；任务是从真行为+3 个 distractor 中选行为，或生成行为。数据来自 1,001 个小说/传记人物、15,846 个行为节点；构造链条和摘要大量使用 GPT-3.5，源文本为文学/传记。见 §3.1–3.3、PDF pp. 3–5。 | 10 个闭源/开源 LLM；选择任务报告 node-wise AvgScore、连续正确长度 CumScore，并给随机/半数选择基线；生成由 GPT-4o 判定一致性/适切性。来源 monograph 去重，但论文没有训练/验证/测试 split 或按 persona/session 留出报告。人类标注验证行为条目，不是对模型整条行为预测作独立盲评分。见 §4.1–4.3、表1–2，PDF pp. 5–9；标注见附录 A.2、p.14。 | **直接覆盖**从完整 history + persona + context 推断连续下一行为，以及历史消融/错误累积。对“有序行为链预测是空白”构成直接反例。**不等同**角色局部可观测 `O` 下的有限动作概率，也未比较显式 `S` 与容量匹配 summary；其行为 gold 是文学/传记文本中的叙述行为代理，不能外推为无中介的现实人类心理或行为真值。 |
| [CharacterBox（NAACL 2025）](https://aclanthology.org/2025.naacl-long.323/)；[本地 PDF](../../01_文献/PDF/2025_CharacterBox.pdf) | 叙述者作为 world model 更新环境与角色状态；角色用 vector memory、self/environment beliefs、BDI，并在每轮计划/行动后更新 belief。角色数据和情境来自十部小说/剧本；系统产生角色交互轨迹。论文也以轨迹微调小模型（guided/reflective）及 narrator/reward model。见 §3.1–3.2、§4、PDF pp. 3–5。 | 100 个中英场景（每部作品 5 个摘取+5 个新生成），9 个模型；GPT-4 评分 7 个 1–5 维度；用专家评分比较自动评价器相关性。训练 CharacterNR/RM 后在明确排除于微调集的新场景上评估；这是组件场景泛化，不是角色/session 行为预测留出。报告每三轮 API 成本（GPT-3.5 narrator+GPT-4 judge 为 $0.0785/场景）。见 §6、表1–5，PDF pp. 6–9；成本表7，pp.12–13。 | **覆盖**文本虚拟世界、动态角色轨迹、角色 belief/memory 更新、行为评分和轨迹微调；故“闭环角色世界 + 行为一致性评价”本身已不是空白。**不提供**独立的下一动作真值：很多行为由 LLM 在其 sandbox 中生成，评价目标主要是评分者对 fidelity/coherence 的判断；不是可与真实 `A*` 对照的动作分布，也没有隔离显式 state 的必要性。 |
| [Towards Dynamic Theory of Mind / DYNToM（ACL 2025）](https://aclanthology.org/2025.acl-long.1171/)；[本地 PDF](../../01_文献/PDF/2025_DYNToM_Dynamic_Theory_of_Mind_Benchmark.pdf) | 1,100 个 social context、5,500 个连贯场景、78,100 道题；跟踪角色 belief、emotion、intention、action，并测静态理解、相邻转移、转移原因和长程演化。场景和心理轨迹由生成流程构造。见 §3.1–3.3、PDF pp. 3–5，附录生成 prompts p.13。 | 10 个 LLM、vanilla 与 CoT；问答 accuracy。10 名人类标注者建立参考表现，随机抽 30%（330 stages/23,430 questions）做人类评估。未训练状态模型，也没有 held-out 角色/情境的预测模型 split。人类标注验证情境真实性/质量，不能将程序化心理轨迹等同于测得的人类内在心理因果链。见 §4、表3–5、PDF pp. 5–9。 | **覆盖**连续场景中的多状态转移、状态间影响与轨迹追踪评测，直接否定“动态心理状态序列评测尚不存在”。**不覆盖**真实独立行为预测、有限 `A^O` 分布或状态压缩相对 raw history 的 sufficiency/necessity。它是 benchmark，不是角色动力学更新算法。 |
| [Beyond Static Persona Consistency / Dynamic Persona Coherence（ACL 2026）](https://aclanthology.org/2026.acl-long.1336/)；[本地 PDF](../../01_文献/PDF/2026_Dynamic_Persona_Coherence.pdf) | 明确拆分恒定 identity 与 history-dependent adaptive state；L/M/S 分别表示身份锚、累积 meaning/strain、短期 affect。GPT-4o 评估事件冲击并生成 Δstate，后续响应按状态生成；PCC 评分、PCR 存 exemplar，PDS 对低分响应重写并反馈。见 §3–4.4、PDF pp. 3–6。 | 5 个手工 persona、情绪挑战事件序列（约 100–150 turns/persona、5 seeds）、3 个闭源模型。主基线是中性固定状态 persona；另做仅状态更新与加 PDS 的消融；GPT-4o PCC 为主指标，附多 judge 稳健性。报告平均 PCC 从 .7254 到 .9195；没有真实人类轨迹 gold，也未报告 train/test persona split；同一设计序列/配置跑 seeds。见 §5、表1–7、PDF pp. 6–8、14–15。 | **直接覆盖**多时间尺度状态演化、persona 稳定性约束、事件状态累积、状态消融及输出纠偏；所以此类架构与抽象主张已被覆盖。**未证明**这些数值状态是真实心理变量或转移符合人类因果机制；其证据是合成 persona/event + LLM critic 的约束一致性结果。 |
| [Predictive State Representations: A New Theory for Modeling Dynamical Systems（UAI 2004）](https://web.eecs.umich.edu/~baveja/Papers/uai2004psr.pdf)；[作者的 UAI 书目信息](https://web.eecs.umich.edu/~baveja/PSRmainpage.html)；[本地 PDF](../../01_文献/PDF/2004_Predictive_State_Representations.pdf) | PSR 把受控离散系统的状态表示为给定动作序列后、未来可观察测试结果的预测；状态更新依赖 action–observation history。论文从 system-dynamics matrix 推导表示并比较 Markov/HMM/POMDP。见 §2–4、PDF pp. 2–5。 | 理论论文，以形式化构造/定理为主，无角色数据集、行为训练/测试 split、人类心理证据或心理因果实验。 | **覆盖**“紧凑状态应对未来可观察结果保留预测信息”这一一般概念。**不覆盖**角色心理解释、人格因果，也不替 Paper-0 解决怎样选择可预测的角色行为 tests、如何取得独立 `A*`。不能把 PSR 直接当作本项目的新机制，也不能因其存在就判项目的具体实验无效。 |

## 论文库路由核验

- 六篇的年份、题名和 ACL 链接与 ACL Anthology 书目页相符；BehaviorChain、CharacterBox、DYNToM、Dynamic Persona Coherence 的本地 PDF 与出版版本标记一致，论文页码分别为 15738–15763、6372–6391、24036–24057、28942–28956。
- PSR 的“2004”是 UAI 会议年份，作者页列为 *UAI 2004*, pp. 512–519；本地 8 页 PDF 正文和引用也吻合。文献 README 当前链接指向 `arXiv:1207.4167`，是 2012 年登记的全文副本，不是发表年份；建议将作者列出的 UAI 书目信息作为规范元数据，并把作者 PDF 作为全文入口。没有发现把 PSR 误标成 2012 的证据。
- BehaviorChain 入口旁写“不是本项目可重复声称的空白”，与本轮全文核验一致。DYNToM 的“动态状态合理性”描述需要收窄：它实证的是对生成故事中明示 mental-state trajectory 的 QA 能力，不是观察人类心理因果过程。
- Generative Agents 入口已列 arXiv 预印本；建议同时附 UIST DOI 作为正式版本。其核心观察—记忆—反思—规划证据应引用论文正文，而非项目网页或系统演示。

## 对 Paper-0 的决策含义（证据 / 推断 / 仍待验证）

**论文证据：** 上表直接排除若干宽泛方向作为独立新颖性：状态随经历演化、静态 persona 对照、history/context 到下一行为、连续角色轨迹、受限/虚拟世界里的角色 belief 与动态评价、低维状态用于预测未来可观察输出。这些都已有近邻。

**由论文对比得出的推断：** Paper-0 最有边界感、也最容易失败的版本，是不声称心理理论，而检验一个预测表示主张：给定同一合法 `O`、`P`、候选动作支持集和模型容量，显式跨轮 `S` 是否在按 session/user/角色留出的独立行为标签上，相对 `H^obs`、strong summary、naive/rank-matched state 有可重复的 NLL/成本收益；同时置换 `S` 是否消掉收益。即便结果成立，首先支持的也只是这个明确数据域中的表示/预测价值，不能直接支持“人类心理机制已被发现”。

**仍待验证：** (1) `A*` 必须独立于待测系统，且不是其自生成 policy 输出；文学/传记、LLM 生成轨迹、专家一致性分数和心理 QA gold 都要标记为各自代理，不能互换。(2) 问题卡指定的 `O` 遮罩、有限 `A^O`、无未来泄漏和身份/叙事 framing 控制能否在一个具体数据源上实现。(3) 是否有足够样本按 session/user 聚类并留出。(4) 除以上六篇外的系统查新仍未完成。本报告只界定已核论文的覆盖范围，不宣称新颖性，也不建议现在改代码或启动实验。

## 证据边界

所有事实依据为上述本地全文 PDF 中所列章节、表格与页码；摘要只用于定位，未作为精确方法或效果结论的证据。外部书目链接用于核对正式题名、作者、年份和版本。模型或自动评价分数被报告为论文自身的评测结果，不等同于独立人类行为真值。
