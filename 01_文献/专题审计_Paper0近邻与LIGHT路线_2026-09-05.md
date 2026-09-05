# Paper-0 近邻与 LIGHT 路线审计

> 记录日期：2026-09-05。用途：冻结首轮的证据边界与外部数据准入；不是新颖性结论。外部细节若未在原论文/仓库逐项核验，保留为待核验线索。

## Paper-0 的可检验锚

在局部可观测、可回放的角色环境中，检验紧凑持久状态 `S` 是否保留对下一行为有用的历史后果，并保证未知 `W` 不越界进入角色 policy。实验拆为：信息边界、预测近似充分性、状态必要性。`W/O/X/S/P/D` 仅为仪器；E0 受控干预只能证明链路接通，不能替代独立 held-out replay。

## LIGHT：先做 T0c 轻量准入审计

[LIGHT 项目页](https://parl.ai/projects/light/) 与 [ACL 论文](https://aclanthology.org/D19-1062/) 已核对为官方来源：该环境包含地点、物体、角色与 talking/acting episode，并报告利用世界对象、affordance 与既往动作可改善 action/dialogue prediction。[LIGHT Quests](https://aclanthology.org/2021.naacl-main.64/) 官方摘要确认其动机/目标与人类演示、held-out expert evaluation 的路线。

这只说明它是**候选**，并不说明可直接形成 Paper-0 数据。T0c 只抽 30–50 条，逐条恢复 actor、turn、persona、当前世界、过往记录、真实动作与候选集；关键门槛是能否以角色为中心重建 `O`、不使用未来信息，并先检查物理 action 的实际长度。审计失败即停止，不训练、不为适配数据重写 ontology；通过后才讨论人工 replay。

## OPeRA：优先于 LIGHT 的 T0d 准入审计

[OPeRA ACL 2026 官方页面](https://aclanthology.org/2026.acl-long.2033/)报告其从人类 persona、history 与 observation 预测下一行动；页面摘要中的规模数字（51 users、692 sessions、28,904 observation–action pairs、604 rationales，以及过滤后的 527 sessions/5,856 pairs）在本项目中先作为**官方但待独立逐项复核**的线索。它是候选人类轨迹来源，但不能据此宣称持久 `S` 的充分性/必要性已被先例覆盖。

T0d 只抽 30–50 个 session，逐项审计 session 长度、动作 ontology/click subtype、user grouping、observation 完整性、rationale 时间位置、split 与未来泄漏，并确认 finite candidate/ranking/NLL 可计算。动作不是独立样本，后续统计须按 session/user 聚类；未通过则保留负结果，不训练、不重写 ontology。

## 近邻的职责边界

| 近邻 | 当前可确认的关系 | 对 Paper-0 的动作 |
|---|---|---|
| OPeRA | 人类 persona/history/observation→next action 候选 | **先走 T0d 数据准入**；不等于验证 `S` |
| LIGHT | 世界/动作/下一步预测的外部数据候选 | 走 T0c 数据准入，优先级低于 OPeRA |
| [PersonaX](https://aclanthology.org/2025.findings-acl.300/) | 官方论文涉及动态 persona 与行为/对话一致性；需逐项核对其 state、更新源与评测是否等价 | 作为高风险近邻，后续按 13 维审计，不作裸判重 |
| [PersonaForge](https://aclanthology.org/2026.findings-acl.386/) | 官方摘要称三层人格和双过程，用于长对话一致性；威胁“动态 state”泛化新颖性 | 后续逐项读实现，不能以概念名判重 |
| [ThinkPersona](https://aclanthology.org/2026.acl-long.449/) | 官方摘要称 persona graph 与角色扮演任务 | 结构化 history 应成为强基线，不能只比弱摘要 |
| [AdaMARP](https://aclanthology.org/2026.findings-acl.1563/) | 官方摘要涉及多主体管理、thought/action/environment/speech 交织 | 属未来多角色/Scene 分支，不挤进 Paper-0 |

所有条目均不得转写为“创新已被覆盖”或“数据已可用”；需按 `W/O/P/S/action/真值/评测` 的职责逐项核验。
