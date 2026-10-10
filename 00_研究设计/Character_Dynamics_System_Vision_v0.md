# Character Dynamics：系统主线与研究支线 v0

更新时间：2026-10-11（作者控制谱系、规划层次与游戏原生机制边界）

**正式问题语义 owner：**全系统算法无关的 F0/F1 定义唯一维护于 [CharacterDynamics_FormalProblem_v0](CharacterDynamics_FormalProblem_v0.md)（当前 DRAFT，未实现）。本页只维护架构/运行时层级视图；作者控制的候选 F2、Typed Trajectory IR 与预实验由 [AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md) 维护。若本页的高层描述与 F0/F1 定义冲突，以 F0/F1 owner 为准。

## 系统定位

系统目标是：在游戏原生状态、事件、角色机制与权威执行之上，针对作者给出的部分约束规划一条合理、可执行的未来路径，并随真实反馈调整尚未发生的部分。作者可自由决定控制范围与密度：零约束、点、线、多条线协同，直至完全编排；同一作品可以混合这些方式。系统在作者留白处继续补全。角色规划器为角色生成、经游戏真实执行的合理行为，可以呈现角色自主；自主性不是不允许上层规划，也不是对作者控制的硬性限制。

系统依赖目标游戏定义自己的状态、事件、动作、角色属性与演化规则，不要求每个游戏都实现 `O/H/X/S/P`。这些符号可描述既有 C++ Runtime 或某个 reference instance，不是跨游戏的必需内部模型。接入层绑定游戏语义、控制权限与真实结算；不得把计划当事实，也不得改写已经结算的玩家/世界历史。天气、资源变化等自然过程可与人物行为一起进入规划和反馈问题，但系统不要求建立通用的天气或物理模型。

目标架构的核心组织思路是从上到下的多层规划：作者意图/约束先绑定到游戏语义，高层规划确定世界、角色与剧情未来，中间层把它细化为持续的过程、轨迹或任务控制，底层适配器再将动作请求交给游戏核验合法性并执行。此图景是目标职责，不是当前代码已实现的端到端链路。实际采用分层、联合、混合规划及具体算法仍待选择和比较；这不是已经冻结的新算法。LLM 是本研究的重要技术机会之一，覆盖语义理解、因果候选生成、跨层细化与反馈修复等环节；不要求每层都用 LLM，也不预设其优于成熟规划器，需设置成熟规划及规划+LLM 强基线。

2026-10-09 用户授权形成的 [NPC System Integration v0](../tools/npc_system_v0/README.md)仍只是有限应用接缝实例；实际证据和缺项见其 [RESULTS](../02_实验/NPC_System_Integration_v0/RESULTS.md)。其控制范围和已实现能力不定义完整系统边界，不改冻结 C++ Kernel。

Character Dynamics 的主线是一个能协调游戏原生机制、角色与世界行为、作者意图及真实执行的规划系统，而不是统一心理状态模型或某一篇 Paper-0 的实验脚本集合。人物动力学可以由游戏自身提供，也可按需作为可替换机制接入。

目标包含：

1. 在可结算的持续世界里，规划出的角色与世界过程连贯、响应实际变化，并能形成玩家可理解的合理表现；
2. 支持作者从完全留白到完全编排的任意控制粒度，并能在受约束与自由生成的区域之间协调；
3. 让高层目标经过中间持续规划细化为游戏可执行的合法动作，并依据执行结果修订未来；效率、调用成本和玩家体验是需要测量的结果，不预先承诺。

这是系统目标，不是已证实的低成本、合理性或玩家体验成果。间接世界引导、直接角色/世界编排与锁定内容都可由作者选择；系统须标记来源和权限，不把明确编排伪装为角色自然选择。作者目标要绑定游戏已定义或明确新增的语义；若当前规则、权限、资源或预算下不可行，规划器应给出冲突/不可行及证据。点、线、多线不强制对应一种几何数据结构，也不要求作者填写通用心理数值曲线。具体 TypedIR / Pilot 规格由[AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md)维护，本文不复制其协议或实验状态。

现有 Continuous Runtime v1 的工程计算范式是：**an event-driven incremental
stateful dataflow runtime over one authoritative simulation timeline**。这描述冻结 C++ Kernel 的内部语义，不规定接入的每个游戏都采用同一世界/人物对象模型。该实现保留 W/O/S/P 与 RunningAction 等节点，并传播 Delta-t、WorldEvent、ActionOutcome、观察投影、StateDelta 与 DecisionGateReason；它是可复用的执行实例，不是通用规划系统的强制架构。Reference v0 保留 action-step 语义作对照。

该旧 C++ Kernel 的三条 runtime flow 为：时间流 `Delta-t → W/S/action progress`；事件流
`WorldEvent/Outcome → legal O projection → Delta-O → X → S impulse`；决策流
`DecisionGate → A^O → π → ActionIntent`。普通事件不自动运行 policy。它们是该实现的真实内部语义，不规定其他游戏必须实现同名 `O/X/S`。

三条流共享以下持久节点：

```text
Persistent in this old C++ runtime: W ── O ── S ── P ── RunningAction
TIME:       Δt → W/S/action progress
EVENT: WorldEvent/Outcome → legal O projection → ΔO → X → S impulse
DECISION: DecisionGate → A^O → π → ActionIntent → W validation
```

上面的运行时图只记录冻结 C++ 分支。系统目标中的作者意图到动作的多层规划链属于更高层架构，不能据此推断已接入该 Kernel 或任意游戏。

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

LLM 不是整个 NPC，也不拥有权威世界或执行权限；但 LLM 与多层规划的结合是本研究主线的重要候选技术问题，不应降为只在末端生成对白的插件。它可参与作者语义理解、绑定候选、因果路径构造、层次细化或反馈修复；每个角色的输入/输出契约、信息权限和可执行性须明确。LLM 不能创造已结算世界事实或取代 executor。具体哪些层采用 LLM、是否带来质量/成本收益，须与成熟规划及成熟规划+LLM 基线实证比较。

## 五个系统模块

核心多层规划链是目标系统的组织主线；以下先说明这条规划链，再保留旧 C++ 分支的五模块分工。其 Dynamics、状态参数 Evaluator/Optimizer 等不是所有游戏接入的前置要求；新规划方案的评价与优化须按相应比较协议定义。

### 多层规划（目标架构）

将作者与世界约束绑定到具体游戏语义，再规划角色/世界的高层未来，向中间层持续过程控制细化，最后交由游戏动作接口检查并结算。中间层须承接目标与具体动作之间的持续控制职责；层次/联合/混合算法及各层是否使用 LLM 均为待比较选择。当前 NPC System Integration、P5 和冻结 C++ Runtime 都只是有限实例，不代表这条完整通用链已经实现。

### Runtime Kernel

冻结 C++ 分支中的共享执行骨架，负责 authoritative clock、RunningAction、runtime boundary、World event 调度、合法的 O 投影、typed settlement、DecisionGate、trace 和 provenance。它不拥有某一套 state law、appraisal law 或 policy；这些字段与 flow 是该分支实现，不是跨游戏接入的共同要求。

### Dynamics Model

旧 C++ Runtime 中由调用方显式注入的角色行为模型，可提供 continuous state dynamics、appraisal/impulse、persistent intention 更新与 policy。`ReferenceRuleDynamicsV0` 冻结 `5d3c164` 的规则语义，仅作可复现实验基线；`DemoLivingDynamicsV0` 是 living sandbox 的应用模型，不是心理学真理。其他游戏可以直接采用自己的属性和行为机制；是否额外接入角色动力学是实例选择。

### Evaluator

负责从完整 trajectory 产生多维 score vector，而不是压成一个不可审计的“自然度分数”。第一版维度包括 WorldValidity、InformationIntegrity、CausalResponsiveness、Persistence、Recovery、Commitment、Adaptivity、CharacterDifferentiation、BehavioralDiversity、Believability、Efficiency。

内部 evaluator 可以用于开发和优化；它不能单独证明自然性、心理机制或 Theory-S 有效。

### Optimizer

在冻结 evaluator 和开发/外部场景分离后，才搜索 state update 参数、decision weights、threshold、decay/recovery constants 等。第一阶段只允许 random search / grid / CMA-ES 一类黑箱搜索；禁止看到外部评测后反复改分数定义。

### Applications

现有 Room Demo、free-run 与可视化消费旧 C++ Runtime trace 和显式模型输出。在该旧 Kernel 的应用边界内，adapter 提交的操作仍须服从游戏合法性，且不能直接改 Kernel 时钟或真实历史；缓存的 NPC 未来计划本身不代表已经授权或已提交执行。目标系统允许作者明确编排并授权角色/世界未来，待语义、能力、权限及资源检查通过后可执行，不能用旧 Kernel 的计划缓存规则限制完整系统。应用可以选择 Demo 模型，但不得把 Demo 行为或视觉表现写回 Reference、Evaluator 或研究结论。

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
| 作者控制与留白处的规划补全 | 作者如何在零约束、点线、多线与完整编排之间选择控制密度，并让系统规划可行的未指定过程？ | 04 已比较相关成熟方法与权限边界；通用端到端能力、控制粒度转换及作者劳动/体验效果未证。[统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 剧情生成与内容衔接 | 如何在权威世界状态、角色认知、作者片段与玩家行为之间连接可执行的内容过程？ | 算法积木整理了内容绑定、固定域编译和剧情引导近邻；项目尚无贯通内容与真实执行的通用链。[算法积木](../01_文献/算法积木/README.md) · [统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) |
| 运行效率与扩展性 | 如何让更多 NPC 长时运行，同时控制推理、存储、延迟和模型调用成本？ | 单时钟 Runtime 是工程底座；大规模角色负载、端到端成本与质量权衡未测。[Runtime Closure Matrix](Runtime_Closure_Acceptance_Matrix.md) · [实现进度](当前实现进度.md) |
| 作者创作工具与总成本 | 作者需要多少编写、补例、审核、调试和维护劳动；系统是否降低总制作成本？ | 已有候选指标与成熟系统参照；没有同等功能条件下的受控总工时比较。[统一基线综合](../01_文献/算法积木/04_统一问题与成熟基线准入.md) · [候选 Pilot](AuthorialTrajectoryPilotV0.md) |
| 玩家可感知的生命感 | 哪些可观察行为让目标玩家感到 NPC 有持续生活、连贯经历、情境响应与差异？ | 评测外围调研及 development 轨迹可复用；尚无目标游戏中的独立玩家效度结果。[玩家评测核查](../01_文献/定向核查_NPC可置信性评测_2026-10-06.md) · [研究重建审计](研究重建审计_2026-10-06.md) |

这些方向部分交叉、彼此关联，但不与各系统模块一一对应。要区分：**Research Program → Research Area → Research Question**。长期版图保留完整方向；A（规划/执行）与 B（作者控制和留白补全）是近期为选择基线而抽取的研究组合；04 中的 Q1–Q3 是有限实例下的条件化候选问题，不是全项目问题总表。任何方向是否形成可研究的具体问题、是否有 gap、是否产生贡献，均须由对应证据决定。

Paper-0 关于“历史如何进入未来行为”的表示/预测问题保持为独立方向。LIGHT 的既有负结果限制的是已测协议与数据条件，不能据此判定该方向已结束；它也不是所有 NPC 研究必须先通过的统一门槛。

不同研究方向可以复用成熟方法，但研究对象不能和技术模块混层：世界、角色、关系、作者要求及玩家体验是研究对象；Kernel、Dynamics、Evaluator、Optimizer 与 Applications 是系统模块。多种成熟组件的组合若经同条件证据显示在规模、成本、控制或体验上解决了既有方法未能同时满足的要求，可能形成系统贡献；“把方法接起来”本身不构成贡献。

Paper-0 persistent representation、外部 Replay、Theory-S 和未来数据实验是研究计划中的证据支线，不拥有整个项目的叙事权。各自的结果与准入仍由其 owner 维护。

LIGHT 当前封口为 generic actor-local history development diagnostic；它不承担完整 Theory-S 训练准入。`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE` 是该支线的边界，不是整个系统的成败判定。
