# 05｜作者意图、World Director、监测与显式创作控制

本文件装配 [F0/F1 §5–6](../../CharacterDynamics_FormalProblem_v0.md)、[Pilot 四控制通道/TypedIR](../../AuthorialTrajectoryPilotV0.md)，不重写 grammar、window、certificate 或未来修复的完整规范。调用 [04 规划/预测](04_PLANNING_BRIDGES.pseudo.md)，执行走 [02](02_WORLD_RUNTIME.pseudo.md)，人物正常生活走 [03](03_ACTOR_DYNAMICS.pseudo.md)。

EXISTING：独立 Python [Registry/AST/compiler/MonitorSession](../../../tools/trajectory_constraints_v0/README.md)检查 typed证据；[有限应用 `System.world_proposal`](../../../tools/npc_system_v0/system.py)已比较 NO_OP和一次有成本公开激励，通过隔离 Python world执行 actor chain和 Monitor。PARTIAL：只一个机会、短时两角色串行域；不是通用关系Director、多层语义识别器、Cpp生产桥或四控制通道均实现。

## 意图、绑定、异质点线与版本

```text
author_edit(intent, existing domain, allowed controls):
    bind role/place/object references to stable IDs; ask on ambiguity
    separate global invariants / scene goals / beat or locked content
    bind each requirement to registered state/event/process semantics
        # "B发现A欺骗"需要B合法观察和已确认recognizer，不能只检查W deception=true
    classify point: AT state | by-deadline state | occurrence | event guard -> change
    classify line: order | allowed paths/phases | registered feature envelope/mean
    declare axis: exact physical time | event/arc index (index cannot advance clock)
    pin registry/model/domain/recognizer/compiler + permission/control mode
    show positive/negative examples to author before confirmed compilation
    compile via existing TypedIR if representable
        otherwise SEMANTIC_GAP / UNSUPPORTED_CONSTRAINT, not guessed numeric float
    return confirmed AuthorBundle(version, anchors, hard/soft, permissions, source)
```

“关系改善”可以先用可观测的合作/拒绝/承诺履行事件作被作者确认的代理，也可以等待真实关系模型；两者不能混称测得 trust。ACTOR_S量必须model pin，不注册无updater/consumer的trust/chaos来让剧情看起来有线。高层意图由作者表达，TypedIR是检查后端，不要求作者填写所有心理/经济曲线。不同层约束冲突需检测/解释，不将beat自动压过global safety。

作者新编辑是新 bundle。过去真实证据不变；旧约束判定保留原版本。必要迁移按既有compiler gate核对，不把“改了语义所以旧故事自动满足”当事实。事件trigger锚定实际instance；保持状态不是每tick新触发，绝对deadline不因修复顺延。

## 四种控制模式和执行入口

| 模式 | 允许提案 | 谁验证/写入 | provenance 与限制 |
|---|---|---|---|
| 默认自主/自然涌现 | 无作者命令，人物自己的 goals/intents | 03模型与02 World | 不把正常生活计作Director收益 |
| 世界机会引导 | 已注册线索/资源/环境/授权事件安排 | 02领域权限/start/结算 | world_opportunity，记录成本与O传播，不能强迫同意 |
| 角色/策略引导 | 作者授权的goal bias/choice constraint等 | 03明确许可控制入口与model边界 | authored_guidance，披露范围/时效，非自然动机产生 |
| 显式覆写/亲写锁定 | 指定状态转变、固定内容/行动段 | 03授权state setter或02实际动作准入 | authored_override/locked，记录ID/guard/hash/版本，不伪称自主 |

后两行是拟议通用接口，不是现有Kernel可用 setter。Actor/Player/World目录分别限权，作者也不能通过任意 set_world_state绕过领域硬规则。作者明确改S/P可以允许，但仍需要具体setter/值域/授权/模型换版后果；默认autonomy不等于作者永远不可改人物。

```text
ControlGrant = scope/fields/operators, conditions, duration, model/domain versions,
               author approval ID, override disclosure, cost, conflict policy
authorize_and_route(proposal):
    require exact grant covers controller, effect, target and current guard
    if world action: submit only registered typed Intent to 02
    if goal/policy bias: submit bounded authored-guidance message to 03
    if state override: actor state owner validates and records requested/applied change
        bypass natural X/U only via visibly distinct authored_override receipt
        run affected model reconsideration/plan invalidation at canonical boundary
    if direct P change allowed: issue new config pin, do not rewrite old model evidence
    never grant LLM commit authority; model supplies candidate, author approves grant
```

state override可以产生真实新状态，但不能补造“人物先观察到某事”、删旧X/失败经历或把setter结果称自然O→X→S。覆盖目标与角色承诺冲突时报告、按已批准模式处理，不静默清空所有承诺。无批准scope，返回 NEEDS_AUTHOR_DECISION，而不是为了deadline擅自升控制强度。

## World Director 是独立规划参与者

```text
director_on_relevant_risk(actual_monitor_results, relevant W change, author edit):
    candidates = [NO_OP] + registered permitted world opportunities at current frontier
        # 如 deliver_existing_message / expose_existing_opportunity / schedule_authorized_event
        # 示例目录：不表示KeyLedger或Cpp现在已实现这些能力
    for candidate in candidates:
        check actual authority/preconditions/resources; discard invalid proposal with reason
        if full isolated checkpoint/forecast model unavailable: report FORECAST_UNAVAILABLE
        else:
            fork = isolated forecast of chosen host, model/actor/player assumptions pinned
            apply candidate only inside fork via same modelled execution boundary
            let each actor run own 03/04 loop; let world/player model continue independently
            evaluate forecast requirements separately from actual Monitor
            04 returns world-path/knowledge/motivation/execution-model/author-feasibility gaps
    hard unresolved/unknown futures do not become zero-loss or feasible candidates
    choose within declared feasible set by confirmed preference/control/cost policy
        # if no certified feasible candidate: retain diagnostic/no-op, or ask author
        # authorized best-effort tradeoff is a separate explicitly approved mode
    revalidate selected current intent at latest frontier; only then submit to 02
    discard/revise speculative suffix on actual feedback; never force all forecast actors
```

NO_OP必须保留。Director控制自己的世界操作，不取得NPC/PLAYER未来行动写权。若作者允许策略引导或覆写，可作为另一明确mode比较，不把它混入世界机会实验。自然事件不需要Director；高层规划暂停也不能让W停止。

同一作者目标要分 world reachability、actor knowledge、motivation、真实 execution、author feasibility。路径存在不保证人物愿意；rollout假设B一定接受时必须报告；single trajectory不提供成功概率或鲁棒保证。全世界fork不是MonitorSession checkpoint：后者只保存监测激活账本。当前Python有限域有独立checkpoint/fork，不能宣称Cpp全World/事件队列/RNG/模型可独立fork。

评估向量保留 constraint verdict/unknown、干预/覆写、机会收缩、资源/时间、author review/debug成本、模型调用。DODM等作者效用可作替代selector参考，不能自动与Thespian weights、剧情tension或玩家体验加成单个“自然度”。

## 实际 Monitor 与修复触发

```text
monitor_actual(evidence from 02):
    verify producer/domain/model/registry pins, receipts, exact time, ordering and coverage
    append admitted actual points/events/segments to Trace
    evaluate confirmed bundle via existing evaluate/MonitorSession
    report SATISFIED / VIOLATED / PENDING / INDETERMINATE / NOT_ACTIVATED
        with actual witness/counterexample/frontier and missing-evidence explanation
    notify 04 repair of relevant changed dependencies/constraints
    notify Director only on relevant risk/new info/version edit
```

PENDING是窗口未闭而还没见证；INDETERMINATE是证据不足；NOT_ACTIVATED是trigger未发生，不冒充完成。ALWAYS需覆盖整窗，无真实continuous证书不从端点补曲线；事件count只认实际实例和receipt，不认LLM“已完成”文本。World真实不可达诊断与Monitor未来PENDING可以同时存在。

玩家扰动先提交，04只改未发生未来并保护合法progress。不应“作者目标是硬，所以玩家成功毁坏不算数”。若前提坏了、缺能力或已过deadline，返回分层诊断，放宽目标/新算子/更强权限需用户批准。

## 作者亲写锁定片段

```text
LockedSegment = content hash/version, entry guard, participant/object bindings,
                permitted control scope, per-step validity, exit/abort,
                explicitly authorized fallback (optional)
try_enter_locked(segment, actual frontier):
    if unresolved guard/absent actor/invalid resource: LOCK_NOT_ENTERED
    else record actual LockEntered event; retain origin=authored_locked
each authored step:
    at existing boundary recheck guard and World admissibility
    if invalidated by player/world: record LockAborted with evidence; call04 future repair
    else execute through02 (or03 approved state setter), record true outcome
    render exactly authored content only when supported by current facts/control mode
on completion: emit LockCompleted only from actual completed steps
```

锁定是创作控制，不是历史回滚或无条件现实override。亲写台词如果声明新信息，需真实通信效果与收件权限；如果演员离场或道具毁坏，不在画面里偷换同名物品。fallback可以是另写片段、明确作者编辑或允许失败，选择仍未定。无批准fallback就abort/请求决策，不能自动强制NPC归位。

四种模式在 [06 A–D](06_END_TO_END_TRACES.md)分别走完整链；真实源码缺口和下一有限接线提案见 [07](07_INTEGRATION_GAPS.md)。
