# Character Dynamics：系统主线与研究支线 v0

更新时间：2026-10-08（作者控制需求；冻结执行边界不重开）

**正式问题语义 owner：**全系统算法无关的 F0/F1 定义唯一维护于 [CharacterDynamics_FormalProblem_v0](CharacterDynamics_FormalProblem_v0.md)（当前 DRAFT，未实现）。本页只维护架构/运行时层级视图；作者控制的候选 F2、Typed Trajectory IR 与预实验由 [AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md) 维护。若本页的高层描述与 F0/F1 定义冲突，以 F0/F1 owner 为准。

## 系统定位

Character Dynamics 的主产品是一个可持续运行的 NPC 角色动力学框架，而不是某一篇 Paper-0 的实验脚本集合。

目标包含：

1. NPC 在可结算世界中表现出更连贯、可响应、可恢复、彼此有差异的长期行为；
2. 常规决策不必每一步重新调用大模型，从而降低模型调用次数、token、延迟和运行成本。
3. 世界中心的作者控制：作者可混用稀疏世界/人物节点、趋势包络、锁定段落与允许分支，不逐情境枚举全部反应；NPC仍有自身任务和信息，玩家成功改变条件后只调整未提交未来。

这是创作/体验需求，不是已证实低成本或活人感的算法成果。自然世界机会、显式作者覆写与锁定内容分三条权限通道；作者覆写如获授权必须留下authored_override，不假装人物自然得出。点/线引用有定义的typed量，不能自动造trust/chaos浮点。具体候选规格由[AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md)维护，本文不复制契约或实验状态。

Continuous Runtime v1 的正式计算范式是：**an event-driven incremental
stateful dataflow runtime over one authoritative simulation timeline**。W/O/S/P
与 RunningAction 是持久节点；正常运行传播的是 Delta-t、WorldEvent、
ActionOutcome、Delta-O、X、StateDelta 与 DecisionGateReason，而不是每轮重算
完整世界。Reference v0 保留其 action-step 语义作对照。

三条 runtime flow 为：时间流 `Delta-t → W/S/action progress`；事件流
`WorldEvent/Outcome → legal O projection → Delta-O → X → S impulse`；决策流
`DecisionGate → A^O → pi → ActionIntent`。普通事件不自动运行 policy。

三条流共享以下持久节点：

```text
Persistent: W ── O ── S ── P ── RunningAction
                 │     │       │
TIME:       Δt → W dynamics / S continuous / action progress
EVENT: WorldEvent/Outcome → legal ΔO → X → S impulse
DECISION: DecisionGate → A^O → π → ActionIntent → W validate
```

其中下列链只表示角色因果语义子路径，不再是完整 runtime mental model：

```text
W authoritative world
  → O actor-local observation
  → ΔO / X structured appraisal (optional sparse semantic model call)
  → S persistent state
  → D / π(A) cheap policy
  → typed world settlement
  → W'
```

LLM 不是整个 NPC，也不是必选组件。按具体任务，它可以作为受限的语义前端、策略前端或规划前端；各角色的输入与输出契约须明确。LLM 不能自行扩张角色可见信息、创造世界状态或历史、授予执行权限，也不能代替权威 executor 校验并结算动作。是否采用及由它承担哪种职责，属于待比较的研究/应用选择，不是架构前提。

## 五个系统模块

### Runtime Kernel

共享的执行骨架，负责 authoritative clock、RunningAction、runtime boundary、World event 调度、合法的 O 投影、typed settlement、DecisionGate、trace 和 provenance。Kernel 不拥有某一套 state law、appraisal law 或 policy。

### Dynamics Model

由调用方显式注入的行为假设，提供 continuous state dynamics、appraisal/impulse、persistent intention 更新与 policy。`ReferenceRuleDynamicsV0` 冻结 `5d3c164` 的规则语义，仅作可复现实验基线；`DemoLivingDynamicsV0` 是 living sandbox 的应用模型，不是心理学真理。两者共享 Kernel，但不可互相替代或隐式回退。

### Evaluator

负责从完整 trajectory 产生多维 score vector，而不是压成一个不可审计的“自然度分数”。第一版维度包括 WorldValidity、InformationIntegrity、CausalResponsiveness、Persistence、Recovery、Commitment、Adaptivity、CharacterDifferentiation、BehavioralDiversity、Believability、Efficiency。

内部 evaluator 可以用于开发和优化；它不能单独证明自然性、心理机制或 Theory-S 有效。

### Optimizer

在冻结 evaluator 和开发/外部场景分离后，才搜索 state update 参数、decision weights、threshold、decay/recovery constants 等。第一阶段只允许 random search / grid / CMA-ES 一类黑箱搜索；禁止看到外部评测后反复改分数定义。

### Applications

现有Room Demo、free-run与可视化消费Runtime trace和显式模型输出。未来作者控制应用通过注册执行adapter提出合法世界操作或明确授权的创作操作，不能直接改Kernel时钟/真实历史，也不能把NPC未来计划当必执行命令。应用可以选择Demo模型，但不得把Demo行为或视觉表现写回Reference、Evaluator或研究结论。

## 评价边界

- Internal Development Score：允许使用合成世界、规则指标和模型 judge，用于发现明显坏行为和优化运行时。
- External Evaluation：必须使用 frozen unseen scenarios、盲评 judge 或人类 pairwise，并与优化数据隔离。
- 当前 Self-Evaluation v0 只覆盖现有 RoomDemo batch 的自动诊断；其中 InformationIntegrity 与 Believability 明确标为未评分，CausalResponsiveness 仅是事件后动作变化诊断，不是因果估计。

## Research Tracks

### 长期研究版图

Character Dynamics 是一个长期研究计划，不等于当前一项实验或一篇论文。以下是从用户长期目标、原始讨论和现有项目材料整理出的**候选研究方向地图**，用于保留问题空间，不是 13 项承诺、已确认的学术 gap、创新点或统一共享底座。当前证据只说明已有何种工程/文献基础及其边界；未验证仍保持未知。

| 研究方向 | 真正研究的对象 / 问题 | 当前基础与待证边界（详情 owner） |
|---|---|---|
| 世界动力学与行为能力 | 世界规则、物体 affordance、资源与时间如何共同支持灵活且可结算的行动？ | 房间级 Runtime 已冻结；通用世界域、动作覆盖和跨场景能力未建立。[实现进度](当前实现进度.md) · [Runtime 契约](Runtime_Scheduler_v1.md) |
| 多主体共享世界 | 多角色如何在共享资源、并发活动与相互影响下持续行动并产生一致后果？ | F0/F1 有职责草案，尚无通用多 NPC 执行闭环。[F0/F1](CharacterDynamics_FormalProblem_v0.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 认知与信息传播 | 角色如何形成、保持、传播并修正不完整或错误的世界认识？ | W/O 权限边界及局部反馈已有工程基础；一般信念、跨角色信息传播及其行为效果仍待验证。[Runtime 语义边界](Runtime_Semantic_Audit_Matrix.md) · [F0/F1](CharacterDynamics_FormalProblem_v0.md) |
| 记忆与状态动力学 | 过去如何被压缩成影响未来行为的持久状态；状态如何渐变、突变、恢复并产生个体差异？ | Paper-0、历史数据诊断与手写模型提供了材料和有限负证据；LIGHT 的负结果仅限已测协议/数据条件，不关闭“历史如何进入未来行为”这一方向，也未验证心理状态规律。[Paper-0 问题卡](Paper-0问题卡.md) · [研究重建审计](研究重建审计_2026-10-06.md) |
| 目标与承诺动力学 | 角色如何形成、竞争、维持、暂停、放弃和恢复目标，并在变化后调整承诺？ | TaskCommitment 有工程基础；复杂目标形成、竞争与长期恢复尚未得到机制或外部行为验证。[F0/F1](CharacterDynamics_FormalProblem_v0.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 规划、执行与修复 | 角色如何实现长期目标，并在真实执行、拒绝、失败或世界变化后调整未完成的未来？ | Runtime 提供执行核，文献综合给出成熟近邻和候选基线；完整规划—反馈—修复闭环尚未实现/验证。[统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) · [F0/F1](CharacterDynamics_FormalProblem_v0.md) |
| 社会关系与角色互动 | 关系、信任、利益与知识差异如何由互动积累并改变后续行为？ | 文献和历史讨论提供候选机制；项目尚未选定关系状态/更新机制，也没有相关效果验证。[算法积木](../01_文献/算法积木/README.md) · [F0/F1](CharacterDynamics_FormalProblem_v0.md) |
| 作者意图的形式化 | 如何把稀疏、抽象的创作要求绑定到可检查的世界条件、角色变化和证据？ | Typed Registry/Monitor 与独立合成 reference 已有设计/工程证据；真实作者语言到游戏语义的绑定仍待实例化。[F0/F1](CharacterDynamics_FormalProblem_v0.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 自主性与作者控制 | 作者如何以合法、有限的机会或干预引导过程，同时保留角色与玩家选择及失败的空间？ | 04 已比较相关成熟方法与权限边界；Director 未实现，低劳动/自主性组合效果未测。[统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 剧情生成与内容衔接 | 如何在权威世界状态、角色认知、作者片段与玩家行为之间连接可执行的内容过程？ | 算法积木整理了内容绑定、固定域编译和剧情引导近邻；项目尚无贯通内容与真实执行的通用链。[算法积木](../01_文献/算法积木/README.md) · [统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) |
| 运行效率与扩展性 | 如何让更多 NPC 长时运行，同时控制推理、存储、延迟和模型调用成本？ | 单时钟 Runtime 是工程底座；大规模角色负载、端到端成本与质量权衡未测。[Runtime Closure Matrix](Runtime_Closure_Acceptance_Matrix.md) · [实现进度](当前实现进度.md) |
| 作者创作工具与总成本 | 作者需要多少编写、补例、审核、调试和维护劳动；系统是否降低总制作成本？ | 已有候选指标与成熟系统参照；没有同等功能条件下的受控总工时比较。[统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 玩家可感知的生命感 | 哪些可观察行为让目标玩家感到 NPC 有持续生活、连贯经历、情境响应与差异？ | 评测外围调研及 development 轨迹可复用；尚无目标游戏中的独立玩家效度结果。[玩家评测核查](../01_文献/定向核查_NPC可置信性评测_2026-10-06.md) · [研究重建审计](研究重建审计_2026-10-06.md) |

这些方向部分交叉、彼此关联，但不与五个系统技术模块一一对应。要区分：**Research Program → Research Area → Research Question**。长期版图保留完整方向；A（规划/执行）与 B（稀疏作者控制）是近期为选择基线而抽取的研究组合；04 中的 Q1–Q3 是有限实例下的条件化候选问题，不是全项目问题总表。任何方向是否形成可研究的具体问题、是否有 gap、是否产生贡献，均须由对应证据决定。

Paper-0 关于“历史如何进入未来行为”的表示/预测问题保持为独立方向。LIGHT 的既有负结果限制的是已测协议与数据条件，不能据此判定该方向已结束；它也不是所有 NPC 研究必须先通过的统一门槛。

不同研究方向可以复用成熟方法，但研究对象不能和技术模块混层：世界、角色、关系、作者要求及玩家体验是研究对象；Kernel、Dynamics、Evaluator、Optimizer 与 Applications 是系统模块。多种成熟组件的组合若经同条件证据显示在规模、成本、控制或体验上解决了既有方法未能同时满足的要求，可能形成系统贡献；“把方法接起来”本身不构成贡献。

Paper-0 persistent representation、外部 Replay、Theory-S 和未来数据实验是研究计划中的证据支线，不拥有整个项目的叙事权。各自的结果与准入仍由其 owner 维护。

LIGHT 当前封口为 generic actor-local history development diagnostic；它不承担完整 Theory-S 训练准入。`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE` 是该支线的边界，不是整个系统的成败判定。
