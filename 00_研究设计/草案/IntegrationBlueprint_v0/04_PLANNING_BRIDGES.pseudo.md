# 04｜高低层规划、角色可行性与未来修复

调用方是 [03 自主角色](03_ACTOR_DYNAMICS.pseudo.md)或 [05 作者/Director](05_AUTHOR_DIRECTOR.pseudo.md)，执行方始终是 [02 权威 Runtime](02_WORLD_RUNTIME.pseudo.md)。以下拟议桥不替 F0/F1 定义，不把所有规划算法混成一个数值目标。

## 当前可复用的接口

EXISTING：Python [E1 `uniform_cost_search(view,...)`](../../../tools/e1_keyledger_v0/planner.py)只读 A-local disclosed view，输出 solve_status/path/selected_action、假设和 budget；B 的预计同意不执行 B。E0 全知 UCS/oracle属于有限世界可达性参照，不直接喂给角色。PARTIAL：Python [npc planner adapter](../../../tools/npc_system_v0/planners.py)复用 E1 GOAP/UCS，另一条件实际调用 GTPyhop HTN；仅有限领域，不支持一般跨场景 narrative planning。

EXISTING：C++ `CharacterPolicy::select_with_history`可作为“当前首动作”接入口，但没有多步 plan store、高层任务图和 general GOAP/HTN runtime adapter。本轮不改接口。成熟规划组件“有代码”不等于已适配我们的 state/permission/time model。

## 输入视图、绑定与高层输出

```text
PlanningRequest = {
    role: ACTOR(i) | DIRECTOR,
    goal_origin: own selected goal | confirmed author requirement | derived subgoal,
    goal_id/version, exact deadline anchor, authorized read view/frontier,
    registered domain/operators + stable entity bindings,
    current Run/progress constraints, assumptions, budget,
    domain/model/permission/registry versions
}
actor request reads only local O/S/P/H/commitment/A^O;
director request may read its authorized W/actor evaluator view,
    but actor simulation receives only each actor's legal view.

high_level_propose(request):
    use optional LLM/narrative/search backend to propose alternative abstract routes
    output typed steps with preconditions, dependencies, binding variables,
           own vs other-agent roles, operator requirements, source/model/prompt pins
    mark any unknown domain capability or meaning as gap, never make it executable
    return CandidateFuture(PREDICTION_ONLY), not accepted control or committed evidence

bind_and_refine(candidate):
    lookup exact registered operators/entities; validate role/read authority
    distinguish author hard goals from retractable planner-derived tasks
    if missing skill/operator/recognizer: DOMAIN_GAP / SEMANTIC_BINDING_REQUIRED
    lower each selected abstract task with GOAP OR HTN backend
    keep conditional other-agent response as assumption, not achieved effect
    return plan + next dispatchable own intent + dependency graph + uncertainty
```

LLM可作语义解释前端、候选计划前端或受限动作 policy，三种配置/输出分开，不因“LLM”一个标签合并。结构化输出不是任意 W/S 写权限。symbolic `LoanKey(offer_id)`在计划里有用，但未获 disclosure 和稳定实体绑定不能派发实际 unlock。deadline沿原 author/actor事件锚，不从每次调用时间重新起算。

## 一个共同低层计划结果

```text
plan_actor(goal_choice, local_view, A^O, budget):
    request = actor PlanningRequest(goal_choice, local_view, A^O, budget, pinned versions)
    candidate = bind selected goal to existing registered low-level operators
    if abstract decomposition genuinely needed:
        candidate = high_level_propose(request)     # 可选；日常动作不强制调用 LLM
    return bind_and_refine(candidate) with request budget/authority checks

PlanResult = SOLVED_MODEL | NO_PLAN_WITHIN_BUDGET | EXHAUSTED_DECLARED_DOMAIN |
             KNOWLEDGE_GAP | MOTIVATION_GAP | DOMAIN_GAP | STALE_INPUT
    carries proposed steps, selected current intent, unresolved bindings,
            causal/time/resource dependencies, model assumptions,
            search visits/expansions, elapsed wall time, complete/exhausted flags
```

这些是蓝图诊断类别，不要求改现有码字符串。GOAP action graph 与 HTN method decomposition的搜索量不相同，不能按 expansions直接评速度胜负；换 planner必须共用域、信息、执行器、失败协议和预算报告，支持不了的语义明示不能公平比较。规划找到全局路径只说明声明模型内 `∃ path`，并不证明 fixed actors会选或 Director有 `∃ policy∀responses`保证。

## ActorFeasibility：五个不合并的检查

```text
check_actor_feasibility(candidate, authorized_world, actor-local views, model):
    world_path = world_reachability(candidate, finite registered domain, absolute deadline)
    knowledge = for every proposed actor step:
                    find its legal known facts or an actual future observation bridge
    motivation = rollout own GoalSelector/commitment/Policy for that actor
                    # B can refuse; no director goal setter unless explicit authored mode
    executable = check registered request/time/resource/control ownership constraints
    author_feasibility = evaluate candidate forecast against confirmed bundle using forecast evidence
    return separate verdicts + first gap + missing bindings + assumptions
```

`actual execution` 不是这组预测检查的 true flag：只在 02 获真实回执之后另行报告。缺actor响应模型时只能unknown或做显式情景集合，不能造“B愿意概率0.8”；单条 rollout不是校准概率也不是鲁棒保证。actor knowledge与W真值不同，已知错误也可能促成尝试；不能用factively true过滤所有角色候选。

## 缓存、异步候选与调用成本

```text
cache key = request/read-set hashes + observed frontier + bindings + domain/model pins
            + goal/author version + permissions + deadline anchor
if relevant ref changed or opaque dependency set: invalidate affected cached futures
if high-level call pending:
    existing legitimate Run continues, other actors/world processes continue
    no LLM call is a world tick; no pause/rewind to response's old snapshot
on response:
    compare relevant dependencies to current frontier; rebind/revalidate or mark STALE_INPUT
    cost ledger records tokens/calls/cache/retry/wall latency + human review/debug work
```

这是未来协调接口，现有 C++同步本地模型调用不自动变成 async服务。低成本来自可验证门控、缓存、稀疏语义与便宜日常策略，效果/成本仍待比较，不能只写“避免每tick调用”就宣布省钱。

## 玩家/世界变化后的局部修复

```text
repair_future(actual_delta, L.frontier, active Runs, pending plan graph):
    assert committed prefix is immutable
    changed = typed refs + entity tombstones + resource/known-fact updates
    if dependency graph incomplete/LLM opaque:
        affected = all dependent future proposals, conservatively recheck
    else:
        affected = transitive consumers of changed supports/guards/permissions
    preserve unrelated future nodes whose dependencies still hold
    preserve each legal active Run identity, elapsed, reservations
        # plan invalidation ≠ physical cancellation; validate ongoing action separately
    for affected unexecuted tail:
        update from actual current state and each actor's actual current knowledge
        keep original requirements, absolute anchors and already-spent resources
        propose repair with existing operators; high-level bridge only if genuine gap
    if future impossible in fully searched frozen domain:
        return bounded DOMAIN_UNREACHABLE diagnostic/proof scope
    if budget exhausted: return NO_PLAN_WITHIN_BUDGET with frontier/usage
    if required author change/permission expansion:
        return NEEDS_AUTHOR_DECISION, do not silently soften constraint
    return replacement future version + retained-prefix hash + changed dependency explanation
```

角色不知道变化时，Director可以全知诊断，角色只在合法新观察/失败反馈后重考虑；不能为了 repair“通知”人物它没听到的消息。修复不能制造被毁物品、把世界完成当人物确认或从头开始所有任务。没有可用替代资源时失败是有效诊断；自然世界/NPC无关日常仍运行。

## 成熟方法用在哪、不能借什么权限

| 层 | 成熟近邻（本地已核卡） | 装配时保留的边界 |
|---|---|---|
| 具体行动路线 | [04 GOAP/HTN](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md) | 角色目标和权限由外部给定；expected effects不是执行 |
| 因果断链切片 | [01 Mimesis](../../../01_文献/算法积木/01_叙事修复与导演.md) | accommodation future-only；不引入2013潜史编辑或事后玩家拦截 |
| 动机/认识gap参照 | [02 IPOCL/Thespian/Sabre](../../../01_文献/算法积木/02_人物意图与约束规划.md) | frame/fit/central consent解释不等实时自治，weight fit也不免费授权改P |
| 高层内容/固定域绑定 | [03 Anansi/WhatELSE](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md) | binding不创造物品；候选 compiler不执行World，不继承未知rollback能力 |
| 约束规格/分段目标 | [02 PDDL3/Porteous](../../../01_文献/算法积木/02_人物意图与约束规划.md) | 检查规格不是规划保证，本地TypedIR也非完整PDDL3/STL |

本草案不合并 Thespian weights、DODM utility、IDG goal-set距离和玩家活人感。下游 [05 Director](05_AUTHOR_DIRECTOR.pseudo.md)只在已声明可行/权限范围内比较作者偏好，[06](06_END_TO_END_TRACES.md)逐步检查预测与实际的分界。
