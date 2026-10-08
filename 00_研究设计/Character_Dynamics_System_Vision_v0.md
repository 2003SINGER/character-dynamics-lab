# Character Dynamics：系统主线与研究支线 v0

更新时间：2026-10-08（作者控制需求；冻结执行边界不重开）

## 系统定位

Character Dynamics 的主产品是一个可持续运行的 NPC 角色动力学框架，而不是某一篇 Paper-0 的实验脚本集合。

目标包含：

1. NPC 在可结算世界中表现出更连贯、可响应、可恢复、彼此有差异的长期行为；
2. 常规决策不必每一步重新调用大模型，从而降低模型调用次数、token、延迟和运行成本。
3. 世界中心的作者控制：作者可混用稀疏世界/人物节点、趋势包络、锁定段落与允许分支，不逐情境枚举全部反应；NPC仍有自身任务和信息，玩家成功改变条件后只调整未提交未来。

这是创作/体验需求，不是已证实低成本或活人感的算法成果。自然世界机会、显式作者覆写与锁定内容分三条权限通道；作者覆写如获授权必须留下authored_override，不假装人物自然得出。点/线引用有定义的typed量，不能自动造trust/chaos浮点。具体规格由[AuthorialTrajectoryPilotV0](AuthorialTrajectoryPilotV0.md)维护，本文不复制契约或实验状态。

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

LLM 不是整个 NPC。它最多在开放语义确实需要解释时充当受限的语义编译器；状态更新、承诺、候选动作、策略和世界结算必须保持可审计、可替换、可低成本运行。

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

Paper-0 persistent representation、外部 Replay、Theory-S 和未来数据实验都是从系统中抽出的证据支线。它们为系统提供证据，不再拥有整个项目的叙事权。

LIGHT 当前封口为 generic actor-local history development diagnostic；它不承担完整 Theory-S 训练准入。`COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE` 是该支线的边界，不是整个系统的成败判定。
