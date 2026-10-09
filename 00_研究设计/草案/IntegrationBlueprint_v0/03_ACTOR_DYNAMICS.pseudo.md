# 03｜人物动力、目标、承诺与行动选择

承接 [02 合法观察](02_WORLD_RUNTIME.pseudo.md)，向 [04 Planner](04_PLANNING_BRIDGES.pseudo.md)提出自己的目标，最终只向 02 提交一个当前请求。语义引用 [完整机制 §3–8](../../完整机制说明_v0.md)、[Q01–Q09](../../未决问题与机制候选.md)，不是新心理学模型。

EXISTING：注入的 [CharacterDynamicsModel](../../../Demo%20codex-generated/Inc/character_dynamics_model.h)有 `advance_continuous/appraise[_with_history]/apply_impulse/update_persistent_intention[_typed_with_history]/build_policy/reconsider_running_action`；[CharacterPolicy](../../../Demo%20codex-generated/Inc/character_policy.h)可读自己的 O/S/P/history/RunningAction。它们不是本文件全部拟议函数的现成 API。PARTIAL：现行 C++固定九个状态字段/单承诺，Python有限应用两个状态字段、自己的 X 与任务承诺；一般二阶知识、关系、更新器冲突规则和多任务生命周期缺失。

## 主观世界、二阶知识、重评价与记忆

```text
ActorLocal = O_i + S_i + fixed P_i + H_i + own Run_i
BeliefEntry = proposition/value, Known|Stale|Unknown, source IDs, observed_at, confidence?
NestedBelief = "i believes j knows/believes f", source path, scope, uncertainty
    # 拟议：i 目击 j 收到 f 或 j 自述，能支持相应归属判断；不免费查询 j.O
    # W 可保存实际 delivery 索引用于审计，不自动向 i 暴露；未送达不代表 j 不知道

receive(deltaO, self_feedback, time):
    validate delivery/access/source; merge only authorized fields into O_i
    preserve stale/error beliefs until declared revision evidence arrives
    append own observable history H_i, never global L as free policy input
    X_new = AppraisalModel.interpret(deltaO, O_i, old S_i, P_i, explicit retrieved H_i)
    for earlier appraisal affected by newly known evidence:
        X_revision = reappraise(event_id, old interpretation, new known evidence)
        preserve original X and revision provenance
        send versioned revision signal to state updater (not replay full old impulse)
    advance_due_fields(old local snapshot, Run_i, unconsumed intervals,
                       X_new + collected X_revisions, time)
    update_commitments(own known feedback, S_i, time)
```

二阶知识是用户必需的设计要求；表示、深度、负知识和置信规则仍待定，不实现无限递归 mental models。`i believes j believes f` 与评估器 `factive_knows(j,f)` 不可混同；KnowledgeStatus::Known 是角色认识状态，不是真值证明。别人的姿态/话语/已见行动作为 O 中的对象证据，不读取对方 S/P/私有关系态度。

Reappraisal 修订“此事对我意味着什么”，不撤销事件本身。要选补偿 patch、重算带版本的统计量或别的更新机制需设计/比较，不能把旧影响先加一次、新解释再加全量而无重复消费记录。过去对状态的作用若无法准确分解，应输出候选不确定修订而非编造精确逆操作。

`H_i` 的检索模块须明确来源、时间窗、读权限和 token 成本；压缩成 S、摘要或结构化记忆各是候选，不能认定 S 充分或 summary 较弱。日志 L 保护证据，人物 H_i 可以遗忘；遗忘不删除 L。当前 C++ ActorHistory 是角色可见滚动窗口，现有 history hooks 不等于通用长期记忆库。

## 独立字段更新、P 调制与阶段响应

```text
FieldSpec(k) = domain, initial, due triggers, read-set, coupling policy,
               updater_id/version, P parameter binding, consumer-set, ablation
advance_due_fields(old O/S/P, Run_i, unconsumed intervals, due X signals, time):
    snapshot = immutable local input at declared frontier
    for k due by event, own elapsed interval or recovery boundary:
        patch[k] = U_k(snapshot.declared_inputs(k), X due for k, unconsumed Δt_k)
        patch records requested/applied/source/version + consumed IDs/interval
    if patches conflict on same field or dependency order unspecified:
        report CONFIG_CONFLICT; keep last accepted state; no arbitrary call-order winner
    actor_state_store.commit(validated patches, pinned model)
```

所有 updater 同一快照读旧值是本草案一个明确候选；若要即时级联耦合，应显式声明拓扑和一次更新的语义，不默认为先执行谁谁获胜。合并/裁剪 owner、恢复积分、event exactly-once、重评价补偿尚需冻结；本轮不造 registry/plugin loader。

P 在 O→X 的解释、X→S 的响应时间/幅度、S→D/π 的表达分别可生效；同一 run 默认固定，不因一次失败改人格。作者获准换 P 要另记 authored_override 和新 model/config pin，见 05，不伪称自然学习。

Q01 原意不能被“压力越高越逃避”或普通线性权重替换：状态数值可连续更新，消费函数可跨阶段改变行为模式。正态逆映射/近似分区、精确分区、平滑曲线、硬 gate/滞回是不同候选，尤其低端/高端语义分开；正态折点不是已证心理依据。

```text
response = ResponseModel.evaluate(state, P, context, phase memory if explicitly selected)
examples_for_design_only:
    moderate pressure may promote task engagement
    overload may suppress engagement / favor recovery
    fatigue very low may mean recovered, not "abnormal"
GoalSelector consumes response, not raw S as universally monotone coefficients
```

当前 Python `ContextDriveV0` 已给非单调 synthetic 示例和 overload guard；这不实现 Q01 的 Φ⁻¹分区，也不验证压力心理曲线。模型替换不应改世界结算。新增状态字段必须说明输入/更新/消费者/消融和证据需要，不因名字好听添加。

## 三种持久对象与承诺生命周期

| 对象 | 属于谁 | 更新凭什么 |
|---|---|---|
| WorldTask | W | 实际 effort/resources/action settlement；可已有完成而无人知道 |
| TaskCommitment | actor S | 自己收到的任务/反馈、需求、取消/恢复条件 |
| RunningAction | Runtime/W执行 | 世界准入后的实际动作、时长/进度/中断 |

拟议完整生命周期保留 `CANDIDATE → ACTIVE ↔ SUSPENDED → COMPLETED/ABANDONED/FAILED`。`BLOCKED` 可是独立状态或带理由的 SUSPENDED，仍未选；不能因为蓝图列出就说当前 C++支持这些枚举。C++当前仅 None/Active/Suspended；有限 Python样机更多状态也非全域支持。

```text
update_commitments(own feedback, S_i, t):
    if own known completion receipt for task:
        close that commitment, preserve first_started_at and transition log
    elif own known obstruction:
        suspend/reconsider with reason; do not equate one failed action with abandoned task
    elif reactive need temporarily wins:
        suspend; keep task_id, completed work and resume conditions
    elif cancellation condition chosen by actor model is satisfied:
        abandon/fail with own rationale and evidence; never reset W progress
    elif own resume guard/preference allows and goal reselected:
        active; resumed_at distinct from first_started_at
    else: maintain existing commitment, including unknown world completion
```

恢复硬 guard vs soft preference、承诺 rank vs weight、何时放弃、多人约定义务和失败态由 owner/user/实验选择，不由蓝图代决。恢复不会重新承诺而覆盖 first_started_at；行动换成吃饭/休息不自动放弃。同任务完成可能仍有疲劳/残余 stress，updater分别消费。

## Goal Selector、Planner、Policy 与反应仲裁

```text
decide(actor, gate, Run_i):
    if !gate.open: return CONTINUE
    D = derive_current_context(O_i, S_i, P_i, commitment, H_i)
    reactive_candidates = ReactiveController.propose(own known urgent evidence, A^O)
    goal_candidates = GoalSelector.activate(own needs, concerns, known tasks, commitments, D)
    goal_choice = GoalSelector.maintain_or_select(goal_candidates, own model policy)
    deliberative_proposal = 04.plan_actor(goal_choice, local view, A^O, budget)
    chosen = ActionSelector.arbitrate(reactive_candidates,
                deliberative_proposal.next_intent, existing Run_i, D, explicit priority policy)
    if chosen == current intent: return CONTINUE
        # 02 独立校验实际维持条件；actor 不免费读 W 来判隐藏的物理合法性
    if chosen unresolved/invalid/timeout:
        return authorized safe-local fallback or CONTINUE, with typed diagnosis
    return ActionIntent + action-choice provenance     # 02 revalidates before replacement
```

GOAP/HTN只解决“怎样完成自己决定推进的事”，不替 Goal Selector 选择人生目标；Policy/Action Selector最终也可以选择非计划动作。火灾示例：目击/听到危险后可选撤离或救人并暂停工作；具体优先级/救人条件是领域与人物模型，不预定每个 NPC总选逃跑。世界物理危险可使动作无法继续，这是 W 强制停止，不伪装角色主观知道火灾。

当前 `build_policy` 与 `select_with_history` 是有限候选评分/选择，不是现成通用 ReactiveController 或 persistent planner。04返回的预测不能给另一角色发命令。当前 Python B 的独立 chooser 在自己控制槽运行，只给有限交易自治，不证明一般角色生活模型。

## 行动方式与世界结果分开

```text
ActionQualityProposal = choose_engagement(O_i,S_i,P_i,commitment,D)
    -> supported intent payload (effort/attention/method/duration), typed and bounded
02 validates domain supports payload; record chosen vs accepted quality
World settlement:
    actual yield = registered world efficiency × actual execution duration
                   × validated engagement contribution × interruption factor × named RNG noise
    record each factor; World does not pull hidden fatigue/P from actor store
```

这是一般质量桥候选；当前 `StudyFocused/StudyHalfhearted` 标签拆分已真实存在，但自由质量 payload 不存在。角色投入、世界效率和随机噪声不合成一个“认真程度”，不以学习产量推断人物意图。质量未被域支持时应报 unsupported 或只使用现有动作标签，不添加虚构字段。

社会关系保留三个量：W 可验证关系事实；O_i 可知的关系/互动；`R_i[j]` 私有有向态度属于 S_i。对话、借物、拒绝的真实结算→各自可知反馈→各自 X/U，A信任B不意味着B信任A。关系字段/阶段还没模型，不注册空 trust 指标以让作者关系弧线通过。

交付 trace 要记录 deltaO/X/U requested/applied、D/goal/commitment transition、planner assumptions、reactive vs deliberate 仲裁、quality、世界实际效果；下游 [05](05_AUTHOR_DIRECTOR.pseudo.md)只按已注册 model-pinned 量监测，[02 表现](02_WORLD_RUNTIME.pseudo.md#模拟层与表现层)呈现可见因果，不宣称心理真实。
