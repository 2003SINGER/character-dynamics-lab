# Paper-0 近邻与 LIGHT 路线审计

> 记录日期：2026-09-05。用途：冻结首轮的证据边界与外部数据准入；不是新颖性结论。外部细节若未在原论文/仓库逐项核验，保留为待核验线索。

## Paper-0 的可检验锚

在局部可观测、可回放的角色环境中，检验紧凑持久状态 `S` 是否保留对下一行为有用的历史后果，并保证未知 `W` 不越界进入角色 policy。实验拆为：信息边界、预测近似充分性、状态必要性。`W/O/X/S/P/D` 仅为仪器；E0 受控干预只能证明链路接通，不能替代独立 held-out replay。

## LIGHT：先做 T0c 轻量准入审计

[LIGHT 项目页](https://parl.ai/projects/light/) 与 [ACL 论文](https://aclanthology.org/D19-1062/) 已核对为官方来源：该环境包含地点、物体、角色与 talking/acting episode，并报告利用世界对象、affordance 与既往动作可改善 action/dialogue prediction。[LIGHT Quests](https://aclanthology.org/2021.naacl-main.64/) 官方摘要确认其动机/目标与人类演示、held-out expert evaluation 的路线。

这只说明它是**候选**，并不说明可直接形成 Paper-0 数据。T0c 只抽 30–50 条，逐条恢复 actor、turn、persona、当前世界、过往记录、真实动作与候选集；关键门槛是能否以角色为中心重建 `O`、不使用未来信息，并先检查物理 action 的实际长度。审计失败即停止，不训练、不为适配数据重写 ontology；通过后才讨论人工 replay。

## 近邻的职责边界

| 近邻 | 当前可确认的关系 | 对 Paper-0 的动作 |
|---|---|---|
| LIGHT | 世界/动作/下一步预测的外部数据候选 | 走 T0c 数据准入 |
| [PersonaForge](https://aclanthology.org/2026.findings-acl.386/) | 官方摘要称三层人格和双过程，用于长对话一致性；威胁“动态 state”泛化新颖性 | 后续逐项读实现，不能以概念名判重 |
| [ThinkPersona](https://aclanthology.org/2026.acl-long.449/) | 官方摘要称 persona graph 与角色扮演任务 | 结构化 history 应成为强基线，不能只比弱摘要 |
| [AdaMARP](https://aclanthology.org/2026.findings-acl.1563/) | 官方摘要涉及多主体管理、thought/action/environment/speech 交织 | 属未来多角色/Scene 分支，不挤进 Paper-0 |

所有条目均不得转写为“创新已被覆盖”或“数据已可用”；需按 `W/O/P/S/action/真值/评测` 的职责逐项核验。
