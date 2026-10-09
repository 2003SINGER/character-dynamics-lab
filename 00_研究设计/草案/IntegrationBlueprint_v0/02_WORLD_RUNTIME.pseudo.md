# 02｜World、Runtime、执行与表现

本文件使用 [README 共同符号](README.md#证据等级和共同符号)，语义遵循 [Runtime Scheduler](../../Runtime_Scheduler_v1.md)、[F0/F1 §3–4](../../CharacterDynamics_FormalProblem_v0.md)及 [完整机制 §3–5](../../完整机制说明_v0.md)。下面是装配伪代码，不另定义 Kernel。

## 真实入口与不能假装已有的部分

EXISTING：`ContinuousRuntime::execute_next_boundary(CharacterState&, const Personality&)` 调 `RuntimeScheduler::advance_to_next_boundary()`、model 连续更新、WorldRuntimeAdapter 世界推进、合法 O 投影、X/impulse/intention、gate/Policy/W validation。[实际调用顺序](../../../Demo%20codex-generated/Src/continuous_runtime.cpp)不是由下方伪代码取代。

EXISTING：`submit_action_intent(ActionType, target_object_id, duration_minutes, interruptible)` 先世界验证，再 start；完成用 `settle_runtime_completion(..., actual elapsed)`。Scheduler 不读 W；action 不推进时间。旧 `World::settle` 整动作推进路径是 Reference v0，对持续 Runtime 不可混用。

PARTIAL：C++ World 有 Scene→Room→Object、有限动作、WorldTask；Observation 有实例 target binding 和有限 stale/失败知识。C++ 当前 Scheduler 一个 `RunningAction`，没有 `map<actor,Run>` 的通用多 NPC 资源仲裁。Python 有独立有限 Executor 和覆盖 seals，不是 C++ 同时运行的第二世界。PROPOSED：本文件的通用控制信封、共同多主体生命周期、事件证据桥与表现只读接口。

## 世界能力、主观动作与请求

```text
WorldDomain.lookup(object_id) -> Object state + registered basic interactions
SceneRecipeCatalogue.bind(scene_id, objects, exits) -> world-side interaction recipes
ActorAffordanceView.resolve(O_i, own learned skills, known preconditions) -> A^O_i
    # 03 使用这一份；未知隐藏故障不提前过滤；错误认识可以提出实际非法动作

Intent = {
    intent_id, controller: NPC(i) | PLAYER | WORLD_DIRECTOR | AUTHORED,
    operator_id/version, stable bindings: object_id/task_id/target_actor,
    chosen duration/engagement if domain supports them,
    observation_frontier or authorized_world_frontier,
    provenance, permission_token if non-autonomous
}
admit(Intent, W, K.now):
    reject unknown schema/operator/version, unresolved symbolic IDs, wrong authority
    World.validate_current_start(preconditions, resources, local reach, permissions)
    if rejected:
        emit typed StartRejected(receipt, limited observable reason)
        # 不新建/替换 Run；不因拒绝冻结自然过程；角色只收到它有资格知道的原因
    else:
        reserve resources using domain's actual reservation rules
        create Run identity and start receipt using authoritative K.now
        schedule next relevant boundary using canonical Runtime path
```

Object 是世界互动能力来源；理论上的 agent-perceived affordance 存在 O 侧，不把 Object 上的真实 usability 直接复制给 planner。Scene recipe 的选择条件与保持条件分开；recipe 声明不授予任意 primitive 写入权。当前 Scene 无通用 recipe 库，实例绑定也不是全域完成。`task_id/engagement` 通用 payload 是待设计，现行 C++签名没有这些参数，不靠“适配”静默塞入。

NPC 的学/睡/交易、玩家的毁坏/离场、Director 的递送/排程各自目录。写 `source=director` 不新增合法算子；自然事件由世界已有规则产生。W 结算不能暗读 S/P/私有承诺；状态影响质量只能通过公开声明且受范围校验的行动 payload，见 [03](03_ACTOR_DYNAMICS.pseudo.md#行动方式与世界结果分开)。

## 唯一时间边界的装配

```text
drive_current_single_actor_host():
    actual = ContinuousRuntime.execute_next_boundary(state, personality)
        # EXISTING：一次调用已推进 Scheduler/W、更新 O/X/S/commitment，
        # 必要时选择/校验动作；外围绝不再调用 K.next 或 World.settle
        # 03 的模型/策略职责在这个 canonical 调用内部由显式 hooks 承担
    b = actual.runtime.boundary
    readonly_record = capture(actual, authorized_post_state, run_model_pins)
        # 只保存事实与版本，不重新投影 O、不重新积分或再次调用03更新
    committed_evidence = evidence_bridge(readonly_record)
    append_actual_evidence(L, committed_evidence)     # 拟议生产接线：只写证据 sink
    05.monitor_actual(committed_evidence)
    actual_changed_refs, committed_frontier = derive_recorded_changes(readonly_record)
        # 无完整变更目录则标为 opaque；不推测隐藏变化或完整 dependency coverage
    04.invalidate_future_dependencies(actual_changed_refs, committed_frontier)
        # 只更新 future proposals，当前已提交 RunningAction 不重建
    expose_readonly_presentation_snapshot(L.frontier, actor-visible views)
```

目标多主体装配也必须保持**同一宿主的一次世界推进**，不能循环创建每actor一个会推进W的 ContinuousRuntime。内部因果次序是：共享边界的实际 Δt→受影响人物 due字段连续更新→一次W自然推进/结算→分别合法ΔO→各自03 X/impulse/承诺→开放gate的自己的03/04决策→02世界准入。多主体 running set、公平调度、共享资源和模型hook编排目前缺失，需后续授权单独实现，以上当前宿主伪码不假装承担了它们。

在当前或未来canonical执行内部，CONTINUE保持原动作身份/start/elapsed/reservation；换动作先验证replacement，合法后才处理原动作实际中断并创建新动作，拒绝不先销毁旧动作。上述职责只能运行一次，不在证据/表现adapter再执行。真实实现还有内部可观察clock cue、阈值/soft gate、拒绝下一边界处理；适配需尊重现码而非重写简化循环。

同刻的 sequence 只表示 ledger order；严格物理先后要求 `t1<t2`。Δt、模拟分钟、wall runtime、规划调用数、叙事进度分别记录。心理字段在自己 due 时积分未消费区间，不重复累计；已运行动作不能因为一条弱消息或 planner 重算换 ID/elapsed。

## 执行反馈与失败传播

| 事实 | 写入/传播 | 不允许推出 |
|---|---|---|
| 启动拒绝 | WorldOutcome→受限 self O→03 X/行动约束→04 reconsider | 把隐藏余额/备用钥匙详情直接暴露；已运行动作被自动取消 |
| 接受但尚未完成 | 真实 Run 与 reservation；Monitor 只能看到 start | 已成功、已 acquired、已完成承诺 |
| 执行中阻塞/部分效果 | 实际时长、消耗、产出、typed reason→可知反馈 | “失败所以没发生”或恢复已消耗资源 |
| W 完成、无确认反馈 | WorldTask 完成、真实事件可给评估器；actor O unchanged | actor commitment 自动关闭或压力解除 |
| 获得完成确认 | O receipt/source→X completion→updater/承诺 | 完成后所有疲劳/残留压力归零 |
| 玩家成功改变前提 | 先实际提交，再依赖切片 repair | 为保故事抹去玩家结果；悄悄延长 deadline |

所有回执保留 requested intent、accepted start、actual execution、terminal outcome 的区别。Planner 返回 BUDGET 不是执行拒绝，Monitor 缺历史 coverage 不是 actor 失败。

## 真实证据和 provenance 桥

```text
evidence_bridge(readonly_record):
    actual, authorized_post_state, producer_manifest = readonly_record.components
        # capture 固定本次 RuntimeExecutionResult、可授权读取的后状态与 producer/model pins
    point = exact time + typed registered observable + value + source frontier
    event = actual settlement-backed instance + stable args + time/sequence + receipt ref
    if producer can prove all changes for a piecewise-constant observable:
        append change points and seal values through this actual boundary
    else: point-only evidence; do not certify intervals
    if exact model solution/bounds certificate is genuinely available and verified:
        emit pinned certified segment with assumptions
    else: no synthetic polynomial inferred from two endpoints
    return typed evidence package; missing fields remain unknown
```

这个桥需要新设计/验证；当前 C++ `RuntimeExecutionResult`/viewer trace 不是 E0 receipt/seal schema。不能补伪造 ID、覆盖或证书以让 Monitor 绿。真实 start/completion 的转换规则、producer 的覆盖声明及其生成端验收见 [07 最小切口](07_INTEGRATION_GAPS.md)。原始 trace 不覆盖，转换后的每字段 provenance 可回查；验证无效则拒绝该证据，不“修正”结果数据。

## 模拟层与表现层

```text
PresentationReadView(frontier, player_access):
    read committed visible outcomes, actual activity/progress, authorized dialogue facts
    request animation/utterance proposal tied to event IDs and content version
    render proposed words only if claims agree with committed history and speaker knowledge
    if unsupported: omit, use uncertainty, or request author-authored marked content
    # UI frame / narration / LLM presentation never writes W, O, S, clock or completed events
```

EXISTING 的 [single-room viewer](../../../Demo%20codex-generated/demo/single_room_v0/README.md)消费导出的实际 trace。拟议通用演出允许后台稀疏更新、远处活动较粗粒度；但改变时间粒度需声明哪种世界规律/资源和边界仍成立，不以画面补出未发生的承诺履行。表现文本若真通过对话行动告诉 NPC 新信息，应作为新的世界通信 intent 经正常结算/观察，而非读视图旁路。

下一调用：[03 Actor](03_ACTOR_DYNAMICS.pseudo.md)；规划失败/扰动：[04 Repair](04_PLANNING_BRIDGES.pseudo.md)；证据：[05 Monitor](05_AUTHOR_DIRECTOR.pseudo.md)。
