# 07｜源码映射与真正的集成缺口

状态：DRAFT / READY_FOR_INDEPENDENT_REVIEW。本文只提出接线与决策，不修改 Runtime、Python owners、实验或运行产物。

## 核对基线与判断边界

本次实读 checkout 为 `D:\desk\科研\character-dynamics`：HEAD `19e5b37`，其前一实现提交 `e5eeedd` 已包含有限 `npc_system_v0`；HEAD 只更新开发验证/CI 记录。结论来自当前文件与字段，不把历史草案的“没有 Director”当成现状。全局协作规则记载的 Mac canonical root 与本次 Windows source checkout 不同；此文不推断另一 checkout 的状态。

工程目标与候选心理机制、作者语义、科学证据分属不同 owner。这里核对“代码现在能做什么”，不改写 [F0/F1](../../CharacterDynamics_FormalProblem_v0.md)、[Pilot](../../AuthorialTrajectoryPilotV0.md)、[完整机制](../../完整机制说明_v0.md) 或 [研究重建审计](../../研究重建审计_2026-10-06.md)，也不把有限开发验证升级成机制有效性。

## 现有模块：源码能承担什么

| 模块 | 实读源码与现有职责 | 具体边界 |
|---|---|---|
| C++ 权威连续执行 | [ContinuousRuntime header](../../../Demo%20codex-generated/Inc/continuous_runtime.h)、[实现](../../../Demo%20codex-generated/Src/continuous_runtime.cpp)。`execute_next_boundary` 编排 Scheduler、World adapter、O、显式 Dynamics Model、gate、Policy 与 W validation。`RuntimeExecutionResult` 返 boundary、前后 `RunningAction`、continuous/impulse state、appraisal、decision、pre/post `WorldOutcome`、选择/目标、替换验证、O deltas、policy identity/selection provenance 与概率；model 身份/版本须由注入端 manifest 另行固定，不是结果内现成字段。 | 一个 Runtime/World 时间与动作执行路径；执行结果是结构化的内存对象，不等于永久 ledger 或通用 receipt API。每个新 `ActionIntent` 仍要经 W start validation。不得在外围再推进时钟或自行结算动作。 |
| C++ 世界边界 | [WorldRuntimeAdapter](../../../Demo%20codex-generated/Inc/world_runtime_adapter.h) 只按 Scheduler 推进 W、安排 W 边界并校验 start；[World/Event/Outcome](../../../Demo%20codex-generated/Inc/world.h) 给当前房间世界与实际结算字段。`WorldEvent` 有 `id/description/source/occurred_at_total_minutes`；`WorldOutcome` 有 accepted/action/target/failure、耗时、task effort/completion、effects、primitives、events 与 provenance。 | `WorldEvent` 没有通用 `event_type + typed_args + sequence + producer_version` 契约；`WorldOutcome` 没有 `receipt_id` 或 ledger sequence。`source`/description 字符串不能代替 typed semantics。 |
| C++ 主观观察与模型 | [Observation](../../../Demo%20codex-generated/Inc/observation.h)/[实现](../../../Demo%20codex-generated/Src/observation.cpp) 保存有限 `Known/Stale/Unknown`、事实来源/观测时刻、self feedback、对象 affordance、target binding、`A^O` 与约束 belief；[Dynamics Model](../../../Demo%20codex-generated/Inc/character_dynamics_model.h) 有 continuous/appraise/impulse/intention/policy construction/reconsider hooks。 | 已有局部错误/过时认识、typed action feedback 和 history hook，不等于一般多角色认知、二阶知识、关系模型、通用记忆压缩或已验证心理 law。 |
| C++ Policy | [CharacterPolicy](../../../Demo%20codex-generated/Inc/character_policy.h) 从模型生成的合法候选中选当前动作，可接 history/RunningAction hook；Policy 可用 Runtime 传入的 RNG 抽样并返回已选动作，Runtime 编排、复核候选、记录并经 W validation 启动/替换，不再抽样一次。 | 是单步 action selector，不是多步 GOAP/HTN Planner，也不承担持久 Goal Selector、世界导演或作者约束求解。 |
| Python TypedIR Monitor | [Trace](../../../tools/trajectory_constraints_v0/trace.py)、[reference README](../../../tools/trajectory_constraints_v0/README.md)、[Pilot](../../AuthorialTrajectoryPilotV0.md)。Monitor 使用有类型的 `Point(ref,time,value,source)`、`Event(event_id,type,time,sequence,args,version,provenance)`、可选 certified segments、event/value coverage seals；无证据覆盖时按约返回 `PENDING`/`INDETERMINATE`。 | 它是独立的证据解释/监测 reference，不会推进 C++ W、创建执行收据、恢复未来计划或实现 Director。 |
| Python E0/E1 与有限 NPC 应用 | [E0](../../../tools/e0_keyledger_v0/README.md)、[E1](../../../tools/e1_keyledger_v0/README.md) 各有独立 Python 有限执行器/协议；[npc_system_v0](../../../tools/npc_system_v0/README.md) 的 `system.py`、`executor.py`、`author.py`、`model.py`、`planners.py` 在该 Python 世界内贯通作者约束、有限 Director proposal、W 校验/结算、O、X/S/承诺、GOAP 或 GTPyhop HTN、receipt/seal 与现有 TypedIR。其唯一结果 owner 为 [NPC System Integration v0 RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)。 | 这是已开发验证的**有限 Python 应用纵切**，不是 C++ Kernel 集成、通用多 NPC 世界、高层 LLM 或心理有效性证据。Director 已有 `NO_OP / publish_incentive` 有限候选，玩家有 `destroy_key1`；不得再写成“全无 Director”。 |

## Trace 导出核查：可审阅材料不等于完整封存账本

这次实际打开了仓库内三个 C++ single-room JSON 导出 `phone.json`、`deadline.json`、`commitment.json`，以及两个连续 Runtime 的 C++ 导出器 `npc_continuity_harness.cpp`、`npc_history_llm_harness.cpp` 和 `runtime_trace_smoke.cpp`。不能只因这些产物叫 trace 就推断具有 immutable-ledger 语义。

- single-room JSON 每 boundary 含 `scenario/timestamp/elapsed_minutes/policy_seed`、有限 `world/observation/state`、动作前后进度、decision/candidates、`world_events`、O deltas、continuous/impulse state delta、pre/post outcome、selected action、validation 与 note。示例里的 `world_events` 项只含 `id/description`；单条 JSON 没有 ledger `sequence`、typed event args、producer/version pins、receipt ID 或 `sealed_through`/coverage record。
- `npc_continuity_harness.cpp` 的 JSONL header 给场景、seeds、model/policy、compiled git revision、trace protocol 与 scope；step 行给 minute、event count、alarm/O 状态、gate reason、running before/after、selection、task effort、interruption 摘要、candidate signature 与 O delta 的 key/value。它只打印 `event_count`，不输出完整 typed event/receipt ledger 或 coverage seal。`runtime_trace_smoke.cpp` 仅向 console 打印若干 boundary/outcome 汇总，不是可回放 typed ledger。
- [npc_history_llm_harness.cpp](../../../Demo%20codex-generated/applications/npc_continuity_v0/npc_history_llm_harness.cpp) 另输出 `world_event_ids`、replacement validation、简化 pre/post outcomes、动作 start/elapsed 和 selection/provenance；不能把两个 exporter 说成同一字段集。它仍不输出通用 typed event payload/sequence/native receipt/coverage seal。
- Python TypedIR `Trace` 明确要求可排序的 event identity/time/sequence/type/args/version/provenance；`seal_events_through(t)` 才声明从场景起点到 t 的事件 ledger 完整，值信号另用 `seal_values_through(ref,t)`。seal 是供 reference validator 判断证据覆盖的声明/契约，不是密码学签名。稀疏 endpoint 不能证明中间连续覆盖；窗口未覆盖会保留 unknown。
- Python `npc_system_v0` 的 checkpoint 另有 Python executor receipts、event payloads、producer versions 与 `seals`，`validate_evidence` 检 receipt/event 对应和封存前缀；这属于那条独立 Python 执行路径。它不能替现有 C++ trace 补出相同证据，也不应与 C++ 世界状态拼成两个“共享”时钟。

结论：C++ Runtime 有足够丰富的 `RuntimeExecutionResult` 供小型投影器读取，但当前导出不满足 TypedIR 的生产证据输入契约；Python Monitor 能读严格证据，但并不负责证明 C++ 导出没有丢步。缺 seal 时不得回填推定覆盖，也不得把 Monitor 的 UNKNOWN 解释成约束满足或世界失败。

## 六类缺口

### 1. 现有接线 / Adapter

当前最明确的空接缝是：**C++ canonical Runtime 的实际 boundary/outcome → 严格的证据 envelope → 已有 Python TypedIR Monitor**。这是异构模块尚未生产接通，不是缺一个重新写的 Python world。C++ 的 `RuntimeExecutionResult` 是内存返回值；现有 viewer/CLI exporter 是面向可读回放的摘要，不含足够 identity、typed event、producer pins 与 coverage frontier。Python `npc_system_v0` 则已在自身 Python executor 内实现 receipts、seal 与 monitor adapter。

接线要保留原始字段，逐字段注明来源；只将已发生 settlement 变为 committed event。必须把 event sequence、event type/args/version、boundary 归属与执行 receipt 的映射约束为可验证契约；输入缺字段、record 丢失或 action 起止无法对应时拒绝 seal，并让 monitor 保持 `INDETERMINATE`。对值轨迹只在 producer 能证明指定量的完整覆盖/持有语义时推进该 `ValueRef` 的 seal；不能从两端采样拟合连续曲线。

### 2. 语义 Coordinator

不同执行栈尚未由一个生产协调边界连接：C++ 有冻结的单 actor canonical Runtime；Python `npc_system_v0` 有局部双 actor/Director/goal arbitration/planner/monitor 的有限应用。它们各自承担协调职责，但**没有同一 W、同一 K、同一 RunningAction 与同一提交账本**。下一步若仅接 Python Monitor，Python 只读 C++ 已提交 evidence，不可执行 Python Executor 再造世界。

更大的多角色 Coordinator 还须解决 actor schedule/行动权限/各自 O 视图、世界事件合法投影、planner 过期提案、目标与承诺生命周期、author intervention 权限和局部 repair invalidation。它应协调既有 owner，不暗中成为万能 Simulator/Executor。C++ `CharacterPolicy` 与 Python goal selection、GOAP/HTN 的职责也不可压成一个“planner adapter”。

### 3. 缺少的领域算子 / 世界能力

领域覆盖仍有限，但应以 owner 为界分别评估：C++ `World` 是单房间 `Scene→Room→Object`、有限 affordance/任务/资源和 W 结算；通用 Scene recipe、普遍多实体绑定、共享世界中的任意社交/交易/事件调度并未由当前 C++ API 提供。Python `npc_system_v0` 则有它自己明确登记的 key-ledger 小域：Director 一种付费 incentive、玩家一种毁钥匙动作、角色 work/rest 与既有借还/解锁/拿物动作。它证明有限算子可通过共同的 Python executor 被治理，不证明开放 World 能力已齐备。

每个新增 world operator 都要有明确 authority、绑定、前提、实际效果、启动/终结 receipt、可观测投影与失败理由；不能仅加一个 `source=director` 或文本事件来改变 W。Scene recipe/互动目录是否需要泛化，需以要做的具体玩家场景驱动，不从长期蓝图直接扩张。

### 4. 缺少的角色动力机制

有接口与有限实现，缺的是一般机制而非“没有动力学”：C++ Model hook 可替换连续更新、appraisal、impulse、持久 intention 与策略候选；Observation 有 stale/unknown/self-feedback；Commitment 与 ActorHistory 有当前有限状态。Python 应用另有 `ContextDriveV0` / `MonotoneAvoidanceV0`、goal arbitration、暂停/恢复与自有 receipt 反馈。它们是版本化有限规则/人造候选，不是心理定律。

未形成的部分包括一般化的二阶知识更新、跨角色关系/信任表征、历史压缩和可验证来源、多个并存任务的承诺 lifecycle、反应性与深思熟虑行动竞争、通用 Action Quality/engagement 到 W 的受控映射，以及跨时间人格差异的可审计 owner。C++ 当前执行 kernel 的一个 RunningAction/单 actor API 与研究目标中的多角色长期生活也有范围差距。逐项含义和准入边界仍由 [01_IDEA_LEDGER](01_IDEA_LEDGER.md) 及既有机制 owner 维护。

### 5. 需要科学比较才能决定的算法

“有算法”与“这个项目该采用”是两件事。GOAP/UCS 与真正 GTPyhop HTN 已在有限 Python app 接通同一个执行器；不应再把它们列为全无实现。`ContextDriveV0` 与 `MonotoneAvoidanceV0` 的对照证明候选 rule 可改变有限行为，不证明非线性压力规律。C++ policy/model 插槽也只证明 replaceability，不证明规划质量。

尚待具体问题与评估协议来比较的候选包括：反应性/深思熟虑 action arbitration；goal selection 与 commitment；不同压力响应候选；高层叙事规划与低层 GOAP/HTN 的分工；作者约束下的 rollout / classical trajectory-planning / bounded director 候选；以及玩家干扰后的依赖定位与 future-only repair。可借鉴方法及其限制见 [算法积木综合准入](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md) 与卡片 01–03；接入成熟算法本身不构成创新，未解决的研究 gap 也不能先验宣称。

### 6. 用户必须拍板的创作与控制选择

这些选择会改变作者权力、角色自主边界和作品体验，代码或 Codex 不能从技术接口推断：

1. 哪些情境使用自然涌现、合法世界机会、角色/策略引导、显式作者覆写；覆写能写哪些对象、何时生效、冲突怎样拒绝/显示，如何标注为作者行为而非人物自主决定。
2. 多层点/线中什么是硬约束、软偏好、时间窗、前置条件、允许分支；约束冲突或不可实现时由谁改、何时停、是否允许 Director 继续提出新机会。
3. Director 的允许动作目录、资源成本、信息权限与可见性；是否只允许环境条件/机会安排，是否允许条件化触及人物目标或状态，哪些干预需要作者逐次许可。
4. 关系/二阶知识所需的最小语义：谁能表示“我认为 B 知道什么”、错误信念如何纠正、哪些记忆/关系状态需要持续多久；不能把理论愿景直接变成字段清单。
5. 玩家可干预的对象与局部修复承诺：需保留的过去/动作进度、绝对期限、哪些未来可改写、无解/未知/预算不足对创作界面的不同呈现。
6. 最终主运行选择与体验目标：未来若要求 NPC、Director 和 Monitor 在同一场景真实运行，谁是唯一 W/K/Executor owner；验收看何种玩家可感知的连续性证据，而不是只看任务成功率。

本轮的最小证据桥不要求现在拍板以上完整产品控制方案；它只要求接受一个有界前提：先由现有 C++ canonical Runtime 执行，Python TypedIR 只读实际提交证据。若要把 Python Director/GOAP/HTN 放进同一运行，再另行决定唯一执行 owner 和迁移边界。

## 建议的最小纵向接线切口（仅提案）

**C++ `RuntimeExecutionResult` → 严格 execution-evidence envelope → 现有 Python TypedIR `Trace` / Monitor。**选择这一切口，是因为两端都真实存在、责任独立，且中间缺的是可验证的证据生产桥；不用重写 Python world，也不用新增时钟、Scheduler 或 Executor。

“只读桥”指对模拟 W/Runtime/O/S/clock 只读；它会向 adapter evidence 与 Python Monitor Trace 追加记录/覆盖前沿。原始运行记录保持不动，转换和监测输出另存。

1. 运行端仍只调用现有 `ContinuousRuntime::submit_action_intent` 与 `execute_next_boundary`；一次完整边界结果作为 source record 同步交给只读 adapter。按源对象原样留存 `RuntimeBoundary`、`WorldEvent`、pre/post `WorldOutcome`、`RunningAction`、`ObservationFact` delta 及 model/policy/run pins。adapter 不再次调用 World，不从文字描述猜 effect。
2. 给本桥定义窄而显式的 run-local envelope：run/source revision、producer/model/registry version、boundary ordinal、精确 `from/to/elapsed`、事件顺序、actual event identity/type/args、动作 start 与 terminal outcome 的对应、源字段 provenance。C++ 目前无 native `receipt_id`/sequence/seal；桥产生的 identity 必须标为 **adapter receipt/projection**，逐字段连回真实 `RuntimeExecutionResult`，不能伪装成内核原生收据或加密不可篡改保证。
3. 先限一个确定性 C++ case、一个角色、一类可从实际 `WorldOutcome` 严格投影的终态事实（例如完成状态的实际 RunningAction 对应成功 completion outcome，并有 `task_completed + task_id`），仅让已有 TypedIR 对这一条 event constraint 监测。Event ID、typed args、event time、producer version 必须来自实际 settlement/受注册的确定性 projector；初始已完成状态不凭空产生 completion event，拒绝或 plan-invalidated outcome 不作完成见证。任何不匹配、缺记录或多义 action correlation 都失败关闭，不产生虚构 witness。
4. 只有 adapter 从 scenario start 连续收到并验证每个 canonical boundary、没有跳过结果且完整覆盖注册事件目录的实际来源时，才能推进 `Trace.seal_events_through(t)`；中断时前沿停在最后一条被证明完整的 boundary。契约要声明 `runtime.world_events` 与 `pre_policy_outcome.events` 等载体的规范 producer/投影规则和稳定去重键，同一实际事件不从两处变成两个 witness；无法确认对应关系就拒绝覆盖声明。覆盖仅对本切口注册的事件语义成立，不宣称全世界叙事无遗漏。当前 C++ state samples 不自动支持区间值证书；此切片先不 seal 数值区间、不输出 polynomial/NumericBand，不从样本稀疏性补值。
5. 将投影 trace 送入已有 Python TypedIR compiler/monitor，比较的是其对**同一真实 C++ committed prefix**的 verdict；预测、Python rollout、导演候选与 player-safe presentation payload 均不进入这条 committed evidence stream。遇到遗漏/未知就接受 `INDETERMINATE`，由结果报告说明 source contract 缺口。

进入实现前仍要把 adapter receipt 与 seal 的字段和拒绝情形写成小契约，并选定具体 C++ fixture/作者约束；本文件不授权实现。若实际数据源不能提供完整 event delta 或可追溯的 completion outcome，切口应收缩到现有可严格证明的观察/终态，不可改用 Python 仿真替它补证。

## 交叉链接

- 目标/语义 owner：[完整机制](../../完整机制说明_v0.md)、[F0/F1](../../CharacterDynamics_FormalProblem_v0.md)、[Pilot/TypedIR](../../AuthorialTrajectoryPilotV0.md)。
- C++ 执行契约：[Runtime Scheduler v1](../../Runtime_Scheduler_v1.md)、[Runtime/Dynamics/Demo 边界](../../Architecture_Boundary_Runtime_Dynamics_Demo_v1.md)、[当前实现进度](../../当前实现进度.md)。
- 独立 Python 执行与结果：[E0](../../../tools/e0_keyledger_v0/README.md)、[E1](../../../tools/e1_keyledger_v0/README.md)、[npc_system_v0](../../../tools/npc_system_v0/README.md)、[开发结果](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)。
- 成熟算法比较：[算法积木](../../../01_文献/算法积木/README.md)；问题定义与选择不在本页裁决。
- 同目录装配图：[README](README.md)、[02 World Runtime](02_WORLD_RUNTIME.pseudo.md)。
