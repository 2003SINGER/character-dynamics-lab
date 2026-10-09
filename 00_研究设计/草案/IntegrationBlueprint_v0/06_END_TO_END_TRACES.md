# End-to-end traces｜手推集成轨迹

> 本文是蓝图的 synthetic design examples：所有状态、分钟、选择与结果均为手推示例，**不是代码运行、实验数据或心理有效性证据**。`[EXISTING]` 指当前代码已有可承担该语义的局部设施；`[PARTIAL]` 指只在受限场景或独立实现中有相似接缝；`[PROPOSED]` 指目标集成或领域能力尚未实现。标签描述代码状态，不给示例结果背书。

本蓝图的目标是一个唯一 WorldOwner、一个权威世界状态 `W`、一条精确模拟分钟时钟及追加式提交账本。下列多角色共享世界、角色个人 `O/S/Commitment`、导演 proposal、共同 Ledger 与 Monitor 的端到端应用均属 `[PROPOSED]`。C++ `ContinuousRuntime` 当前围绕单个角色、单个 `Observation/CharacterState/RunningAction` 工作；`tools/npc_system_v0` 是另一套 Python finite world 与串行 action token。两者不可拼接描述成已有的多 NPC runtime。

## 纸面执行约定

本文件的调用契约分别落在蓝图其他 owner：共享 W/clock/action settlement 见 [02_WORLD_RUNTIME](02_WORLD_RUNTIME.pseudo.md)；O/X/S/Commitment 与 Goal 的边界见 [03_ACTOR_DYNAMICS](03_ACTOR_DYNAMICS.pseudo.md)；Actor/Director planning、ActorFeasibility 与 repair 见 [04_PLANNING_BRIDGES](04_PLANNING_BRIDGES.pseudo.md)；作者权限、NOOP/机会比较、override 与 Monitor 见 [05_AUTHOR_DIRECTOR](05_AUTHOR_DIRECTOR.pseudo.md)。下文只演示这些文件间的调用顺序，不另设一套接口 owner。

- `t` 是相对 scenario start 的精确模拟分钟，采用有理数；表中整数分钟是精确值，不是现实时间或调用轮次。权威时钟只由 WorldOwner/Scheduler 推进。事件与回执按 `(physical_time, sequence)` 排序；同刻先按 Runtime contract 积分 `[t0,t)`，再处理 `t` 的外生事件/中断，再结算。见 [F0/F1 时间与执行语义](../../CharacterDynamics_FormalProblem_v0.md) 和 [Scheduler contract](../../Runtime_Scheduler_v1.md)。
- deadline 是固定绝对时间，例如 `T=12`；重规划、暂停、恢复都不移动它。一次规划调用不推进时间。被拒绝的 ActionIntent 不算真实 Settlement。
- `W` 由世界独占写入；Actor `i` 只从授权投影得到 `O_i`，X 是独立、可检查的语义解释，之后才是带版本的状态更新 `U(S_i, X, Δt)`。角色自身的 Goal/Commitment 与世界客观任务进度分开。角色 `A^O_i` 由其**已知** affordances、动作前提信息与授权动作目录形成；S/Commitment 可参与 goal 优先级、重考虑或选择评分，但不自动充当动作合法性的硬资格。World 负责权威合法性校验与结算。
- Ledger 只追加真实已提交事件/回执；rollout、预测计划、候选效果不是历史。Monitor 只读已提交证据；Repair 只替换未来 proposal，不改过去、不重置仍合法的 RunningAction。
- 本文新增的 `send_bulletin`, `open_public_meeting`, `jointly_sign`, `author_locked_line` 等均为**有限纸面领域算子，NOT IMPLEMENTED**。名称本身不赋予 executor 能力。任何将它们接入真实执行器都需要明确 schema、authority、precondition、duration、effect、失败路径、观察传播和 provenance。

### 源码事实锚点

- `[EXISTING]` C++ 单角色运行路径：[`ContinuousRuntime`](../../../Demo%20codex-generated/Inc/continuous_runtime.h)、[实现](../../../Demo%20codex-generated/Src/continuous_runtime.cpp)；它执行当前 actor 的连续推进、World 时间推进、观察刷新、appraisal/impulse/commitment 更新、decision gate、policy 选择及动作替换校验。
- `[EXISTING]` 单一 Scheduler 时间与 RunningAction elapsed：[`RuntimeScheduler`](../../../Demo%20codex-generated/Inc/runtime_scheduler.h)、[实现](../../../Demo%20codex-generated/Src/runtime_scheduler.cpp)。同刻事件与动作完成的优先顺序由该 contract 定义。
- `[EXISTING]` 当前房间世界动作合法性与结算：[`World`](../../../Demo%20codex-generated/Inc/world.h)、[实现](../../../Demo%20codex-generated/Src/world.cpp)、[`WorldRuntimeAdapter`](../../../Demo%20codex-generated/Inc/world_runtime_adapter.h)。adapter 校验 World 与 Scheduler 时间一致；World 生成 primitives 并执行结算。
- `[EXISTING]` 单角色认知与行为 seam：[`Observation`](../../../Demo%20codex-generated/Inc/observation.h)、[`CharacterDynamicsModel`](../../../Demo%20codex-generated/Inc/character_dynamics_model.h)、[`CharacterPolicy`](../../../Demo%20codex-generated/Inc/character_policy.h)、[`Action`](../../../Demo%20codex-generated/Inc/action.h)。这不是多角色高低层规划器。
- `[PARTIAL]` Python A/B 独立小世界：[`npc_system_v0` README](../../../tools/npc_system_v0/README.md)、[system](../../../tools/npc_system_v0/system.py)、[executor](../../../tools/npc_system_v0/executor.py)、[actor/model](../../../tools/npc_system_v0/model.py)、[author monitor bridge](../../../tools/npc_system_v0/author.py)。它提供有限 A/B 视图、commitment/goal 示例、串行 token、预测 rollout 与 Monitor 输入；不共享 C++ World/clock/executor，也不构成一般并发多角色系统。
- `[PARTIAL]` 作者约束独立 TypedIR reference 与局部诊断：见 [AuthorialTrajectoryPilotV0](../../AuthorialTrajectoryPilotV0.md) 及 [`trajectory_constraints_v0`](../../../tools/trajectory_constraints_v0/README.md)。它读合成 trace/evidence，不自动驱动 Runtime 或 Director。

## A｜没有 Director：独立生活、被打断、恢复或放弃

**纸面设定。**角色 Ada 在 scenario `t=0` 有一项自选的 `repair_bicycle` commitment，W 中对应 `WorldTask(task_id=repair_bicycle, effort_target=5 units, effort_done=0)`，目标截止 `t=10`；她已知工作台和工具。领域结算规则明确：可中断的首次修理动作运行到 `t=3` 后，World 依据实际检查完成量结算 `+2 units`；恢复动作运行 `t=5→8` 后再结算 `+3 units`。这些 units 是该合成 repair domain 的 W 效果，不由 elapsed 自动换算，也不是当前通用 C++ 部分结算能力。外部铃声/访客在 `t=3` 产生可见中断。Ada 暂停去回应，`t=5` 恢复同一 commitment，`started_at=0` 保持不变；另一合法分支中，若她在 `t=5` 得知工具已损坏且没有可用 affordance，可显式放弃并转向休息。`S` 中疲劳/压力数值和阈值仅为手推 fixture 输入，不是已验证心理规律。

| t / 顺序 | 数据流 | 状态与证据 |
|---|---|---|
| `0 / seq 0` | **W → O** `[PARTIAL]` | 唯一 WorldOwner 纸面初态：`workbench, tool, bicycle` 可用；World 产生 Ada 有权看到的 affordance snapshot。当前 `World/Scene/Object` 能为单 actor 构建有限房间动作，但本例物品/repair 域与共享多角色投影不存在。 |
| `0 / seq 1` | **O → X** `[EXISTING]` 单角色接缝；本例多 actor 运行 `[PROPOSED]` | Ada 只按 `O_A` 中已知工具、任务线索与访客信息解释事件；不读隐藏 `W`。真实 Runtime 有 `Observation → appraise_with_history` 调用与模型 hook；`repair_bicycle` 语义规则是合成输入。 |
| `0 / seq 2` | **X → S / Commitment** `[PARTIAL]` | 合成 updater 将 `X` 交给版本 pin 的 `U_demo_v1`；个人 commitment 变为 `ACTIVE(repair_bicycle, started_at=0)`。C++ 有可注入 dynamics 与 typed persistent intention hooks，当前 `WorldTask` 有 objective effort，但本例独立的 goal commitment 与多角色持久账本未接通。 |
| `0 / seq 3` | **Goal → Planner** `[PARTIAL]` | Goal selector 根据当前目标、S/Commitment 等排序信息选 `repair_bicycle`；这些信息影响优先级，不把心理状态变成硬 eligibility 条件。Planner 仅从由 Ada 已知 affordances、前提与授权目录得到的 `A^O_A` 提议 `repair(duration=6)`。当前 C++ `CharacterPolicy` 选择当前动作，不是 GOAP/HTN 多步规划；Python sample 有 goal/arbitration 与有限 actor planner，但在另一 executor 中。 |
| `0 / seq 4` | **ActionIntent → W validation/start** `[EXISTING]` 规则；本例动作 `[PROPOSED]` | `ActionIntent(action_id=A17, actor=Ada, target=bicycle, start=0, planned_duration=6)` 由 World 检查 affordance、权限、工具和前提。若拒绝，记录 rejection，不创建 RunningAction、不产生成功效果。C++ 每次新建/替换 action 都经 `validate_runtime_start`；repair 不是其现有动作。 |
| `0→3` | **RunningAction / W clock** `[EXISTING]` 时钟语义；共享多 actor `[PROPOSED]` | 一个 authority clock 到 `t=3`，`A17.elapsed=3/6`。动作本身不推进 clock。 |
| `3 / seq 5` | **Settlement / interruption** `[PARTIAL]` | 外部事件 `visitor_arrives` 在同刻作为 interrupt 交给世界/调度器。scheduler 保留 `A17.elapsed=3` 并标记 `Interrupted`；合成 repair executor 检查实际完成量并提交 `WorldTask.effort_done: 0→2 units`、部分物理效果及 receipt。此 `+2` 是 `[PROPOSED]` 的领域结算，不是现有 C++ scheduler 从 elapsed 自动计出的 effort；C++ 完成结算有 task effort 路径，但 interrupted 分支只记 invalidation feedback，不做本例这种部分 task settlement。 |
| `3 / seq 6` | **W → O → X → S/Commitment** `[PARTIAL]` | 若访客事件合法投影，Ada 得到 `ΔO`，X 解释其重要性，Commitment 从 `ACTIVE` 转为 `SUSPENDED(reason=visitor)`；其它 actor 只获其有权见到的部分。当前 C++ 处理单 actor observation/update；Python app 有 A/B 独立视图和显式 commitment transitions，语义限于自己的合成域。 |
| `3 / seq 7` | **Ledger → Monitor** `[PROPOSED]` | 追加 `action_interrupted(A17, elapsed=3)` 与 `visitor_arrived`，若 World 明确结算部分修理则另追加 `repair_progress_committed(amount=...)`。Monitor 只核实 deadline/任务约束，不从 `elapsed=3` 推断工作量。作者无 Director 时不存在导演分支。 |
| `3→5` | **Goal / Planner** `[PARTIAL]` | Ada 做访客回应；其短动作结算后到 `t=5`。若没有可见事件或主体 gate，无需强制全系统在每分钟重选 goal。 |
| `5 / seq 8` | **O → X → S/Commitment** `[PARTIAL]` | Ada 收到访客回应及已结算的 `repair_progress_committed(+2)` 反馈，经合法 O 投影后重新 appraisal。合成规则认为工具仍可用且目标仍值得做，commitment `SUSPENDED→ACTIVE`；`started_at` 仍是 `0`，`suspended_at=3`、`resumed_at=5` 作为独立生命周期记录。另一分支若新信息使目标不可行/不再愿意，可终态 `ABANDONED(reason=...)`。不得把 W 完成与 Ada 已知/愿意继续混为一项状态。 |
| `5 / seq 9` | **Goal/Planner → ActionIntent** `[EXISTING]` 骨架；恢复语义 `[PROPOSED]` | 她选择继续同一 commitment，提出新 action `A18(duration=3)`，目标剩余 `3 units`。`A18` 是新 action ID；不得重启或复用已中断的 `A17`。World 重新验证当前前提。 |
| `5→8` | **Settlement → W → Ledger** `[PROPOSED]` | `A18` 连续运行至 `t=8`。领域 executor 结算检查确认 `+3 units`，World 更新 `effort_done: 2→5/5`、任务 `COMPLETED`，并提交 `repair_completed` outcome/event；若实际质量不足，则不允许声称到 5。 |
| `8 / seq 10` | **Settlement feedback → O → X → S/Commitment → Monitor** `[PARTIAL]` | 完成回执经授权路径投影给 Ada；她形成 `X_A(own repair completed)`，模型更新后将同一 commitment 从 `ACTIVE→COMPLETED` 并记录完成来源，`started_at` 仍为 0。Monitor 对 W task progress 与真实完成 ledger witness 判 `SATISFIED`；deadline `T=10` 未滑动。当前 C++ 有完成 outcome/自行动作 feedback 与 intention hook，但本例持久 commitment 终态、history 与 Monitor 接线是目标集成。 |

**反例检查。**将 `A17.elapsed=3` 当成 World 任务已做一半会把运行时间误报为实际进展；每个 boundary 重建 RunningAction 会抹掉身份与进度；把世界端 `repair_complete` 直接写进 Ada 的 commitment 会违反观察/知识边界。当前 C++ 支持单角色 RunningAction 时间语义，但本例的独立承诺、repair operator、永久 Ledger 与 Monitor 接线仍是集成提案。

## B｜作者要关系变化：比较 NOOP 与合法世界机会，让 NPC 自己决定

**纸面设定。**作者约束是：在绝对截止 `T=12` 前，真实 ledger 出现一次 `joint_pledge_committed(Ada, Bo, topic=bridge)`；“关系变亲近”不是现有字段，本例只用可审计的共同承诺事件作可执行代理，不声称它等于信任或关系发展。两人各自有日常目标，只有本人能接受/拒绝承诺。导演在 `t=2` 从同一 checkpoint 比较：`NOOP`、向两人都可见的既有公告栏发布线索、开放已有社区会议时段。后两项是纸面算子 `send_bulletin`、`open_public_meeting`，**NOT IMPLEMENTED**；不得暗加道具、强制同意或写 NPC `S`。

| t / 顺序 | 数据流 | 状态与证据 |
|---|---|---|
| `0 / seq 0` | **W → O_A/O_B** `[PARTIAL]` | 共同 W 有公告栏、会议室与基础日常 affordance；Ada 知道桥梁问题，Bo 尚不知 Ada 的提议。世界对象与局部 affordance 在 C++ 有基础，双 actor 共享 World 和独立知识投影只在目标架构中。 |
| `0 / seq 1` | **各自 O → X → S/Commitment → Goal/Planner** `[PARTIAL]` | 两人各按自己的 O/P/history appraisal。Ada 可把修桥列入自己的 commitment；Bo 未获得消息，不能依据隐藏事实拒绝或接受。actor planner 的预测动作是条件化候选，不写入 W。C++ 有单 actor 语义阶段，Python 有有限 A/B view/goal/planner；关系心理模型仍未定义。 |
| `2 / seq 2` | **Author Monitor** `[PARTIAL]` | Monitor 针对 append-only ledger 检查事件约束；截至 `t=2` 无 pledge，且 deadline 未到，结果是 `PENDING`，不是违约。Pilot TypedIR 可对合成证据作独立判定，生产 ledger→monitor adapter 未有。 |
| `2 / seq 3` | **Director candidate generation** `[PROPOSED]` | 读允许使用的作者约束、授权 Director view、当前 W 和登记算子目录；产生 `{NOOP, send_bulletin, open_public_meeting}`。actor/player 未来回应只在模型 rollout 中预测。若算子缺少 authority/schema 或前提不满足，则候选被拒绝，不可由 LLM 临时发明。 |
| `2 / seq 4` | **World/Actor feasibility 与 rollout** `[PROPOSED]` | 在同一冻结 checkpoint、策略版本、绝对 `T=12`、预算与成对随机流下分别 fork。检查每个 world transition 合法；之后检查两位 actor 是否有机会观察、是否理解、是否形成动机、实际选择概率/单次轨迹。对每候选记录约束达成、选择被限制次数、Actor continuity、资源和调用成本。候选 rollout 标为 prediction-only，永不进 Ledger。 |
| `2 / seq 5` | **Director compare/select** `[PROPOSED]` | 仅在许可和 hard constraint 通过后，以预先声明的排序规则比较 NOOP 与两种机会。假设手推比较选择 `send_bulletin`，只代表本次合成 model 的候选选择；有限 rollout 不能证明人物一定接受、真人反应或对所有响应的鲁棒保证。若预算超限输出 `NO_PLAN_WITHIN_BUDGET/UNKNOWN`，不得说不可达。 |
| `2 / seq 6` | **ActionIntent → World validation/start** `[PARTIAL]` 骨架；新算子 `[PROPOSED]` | Director 提交 `send_bulletin(board=notice_board, message_ref=bridge_invitation)`，带 grant、operator version、base checkpoint hash、constraint hash 与 expiry。World 校验公告栏存在、导演权限、消息内容引用已授权、资源/时长与一次性规则；通过才执行。没有实际世界算子就阻止提交。 |
| `2→3` | **Settlement → W → O projection** `[PARTIAL]` | 若成功，World 在 `t=3` 提交公告发布事件；依据 recipient/delivery rule 分别更新 O_A、O_B，且不同步泄漏其他隐情。未投递给某人就不能令其知道。 |
| `3 / seq 7` | **Ledger → Monitor** `[PARTIAL]` | 只追加 `bulletin_published` 及实际收件回执。作者目标仍 `PENDING`，因为它要求的是两人共同承诺的真实事件；Monitor 不把导演机会等同目标完成。 |
| `3 / seq 8` | **各自 O → X → S/Commitment → Goal/Planner** `[PARTIAL]` | Bo 只有在收到公告后才把它加入 `ΔO`；其 X/S 和 goal selector 决定是否回应，自己的 planner 选择发起会面、忽略或拒绝。Ada 同样自行决定是否参加。任一拒绝都是真实分支，不能通过 Director 改写 commitment 修正。 |
| `3→7` | **ActionIntent / Settlement** `[PROPOSED]` | 手推成功分支：双方先后提交可中止的参加/同意意图；World 每次检查在场、时间、资源与双方明确同意。`jointly_sign` 只在两份独立同意都已真实结算时可提交。其他路径可空过或拒绝。 |
| `7 / seq 9` | **Ledger → Monitor** `[PROPOSED]` | 仅共同签署的 World settlement 写 `joint_pledge_committed`，包含双方 actor ID、topic、各自 consent receipt、算子版本。此后 Monitor 才能以事件 witness 判 `SATISFIED`。若没发生，保持 pending 至期限；证据缺段则 `INDETERMINATE`。 |

**反例检查。**Director 预测 Bo 愿意、A* 中包含 Bo 的 `accept`、或作者文字写“关系好转”均不是 commit。当前 Python `npc_system_v0` 中的 director rollout 和 `publish_incentive` 属于独立有限 application；不得拿它冒充本例新的 bulletin/meeting 能力或 C++共享运行。没有可登记、可验证的 World 算子时，该候选必须失败在执行准入层。

## C｜玩家破坏关键前提：保留历史、未影响活动及合法进度，只修未来

**纸面设定。**A 在 `t=0` 启动使用唯一 `key0` 的长动作 `A31(open_archive, planned_duration=6)`；玩家将在 `t=4` 破坏 key0。B 于 `t=1` 启动无关的 `B12(water_garden, planned_duration=5)`，其地点、工具、资源与作者约束不依赖 archive/key。固定 author deadline `T=10`，目标为 A 在 deadline 前取得 ledger。冻结有限 paper domain 注册一个替代路径：导演可投递既存 spare key 的位置线索（`deliver_spare_location_clue`，**NOT IMPLEMENTED**），随后 A 必须自己取得 spare、unlock、take ledger；不得把 spare 的位置预先放入 A 的 O。该 success branch 的下述算子都只是纸面定义；如果某算子未实现/未授权，不能 dispatch。

| t / 顺序 | 数据流 | 状态与证据 |
|---|---|---|
| `0 / seq 0` | **W → O_A/O_B → A^O** `[PARTIAL]` | World 提供两 actor 局部 affordances。A 的 view 包含 key0，不含隐藏 spare；B 的 view 只含 garden 状态。有限房间 C++ 有 O projection/已知 action surface；跨 actor 视图与本例领域不同。 |
| `0 / seq 1` | **O → X → S/Commitment → Goal/Planner** `[PARTIAL]` | A 承诺取得 ledger；B 保持自己的花园任务。actor planner 分别提议 open-with-key0 与 water。计划图记录 A 的 `open → take` 支持关系；B 的 action 独立，不读取 A 的计划。 |
| `0 / seq 2` | **A ActionIntent → World validate → RunningAction** `[PARTIAL]` | World 验证 A31 的权限、key0、前提、资源与时长后启动。单 actor Scheduler 的 `RunningAction` 字段能记录一项活动；目标应用需为每 actor 保存运行实例，且统一由同一个 World clock 推进。 |
| `1 / seq 3` | **B ActionIntent → World validate → RunningAction** `[PROPOSED]` | B 自己根据 O_B 选择 `water_garden`；World 检查独立地点/工具/资源后启动 `B12`。本共享并发情境还未被当前 C++ 单 `RunningAction` 或 Python serial token executor 支持。 |
| `1→4` | **W clock / progress** `[EXISTING]` clock semantics；多 actor `[PROPOSED]` | 唯一 authority clock 从 1 到 4；A31 自 t=0 起累计 elapsed `4/6`，B12 自 t=1 起累计 elapsed `3/5`。本 paper domain 的 WorldOwner 在相关世界事件或动作边界，调用 domain-specific running-action guard 检查受影响前提与 reservation；这是目标领域 contract，**不是声称 C++ 存在通用的 ongoing-validation 函数**。时钟推进不会自动提交两项动作的任务进度。 |
| `4 / seq 3` | **Player ActionIntent → Settlement** `[PARTIAL]` | `destroy_key(key0)` 由 PLAYER 权限提交，World 校验 key0 当前可破坏，结算 `key0_intact: true→false`，并清理合法持有/锁状态。玩家行为也是世界真实控制，不是 Director rollback。 |
| `4 / seq 4` | **W → Ledger → O/ΔO** `[PARTIAL]` | append `key_destroyed(key0, player, t=4)`；只把事件投影给有感知/通知路径的角色。Ledger 保留 A31 先前开始与所有过去事实。若 A 未观察到破坏，不得提前更新其 O。 |
| `4 / seq 5` | **A running action / B running action** `[PARTIAL]` | 领域 guard 在此次 `key0_destroyed` 事件边界发现 A31 前提失效，按此 paper domain 的中断规则结束 A31；elapsed=4 留在不可变 receipt，A31 永不重启，未结算效果由 domain outcome 明确记录。B12 前提仍真，原身份保留为 elapsed=3/5、原 reservation 与进度。C++ 有单 `RunningAction` 的 elapsed/interrupt/replacement 语义；双角色实例及本领域 event-triggered guard 是目标能力。 |
| `4 / seq 6` | **ΔO → X → S/Commitment** `[PARTIAL]` | 若 A 收到毁钥匙通知，appraise 形成 `X_A(key route unavailable)`；A 的 commitment 不因单一子计划失败而自动销毁，可转 `ACTIVE→SUSPENDED/REPAIR_REQUIRED`。B 不收到与其无关的事件时不强制重算其 S/goal。C++ 在强事件/gate 时能对当前 actor 重新评估；跨角色局部更新调度未实现。 |
| `4 / seq 7` | **Monitor** `[PARTIAL]` | 已提交 key destruction 是真实反例，旧计划依赖失效；ledger acquisition 事件截至目前不存在，Monitor 仍 `PENDING`（deadline=10 未到）。计划失败不能把历史中的获得事件删掉；本例历史里从未取得。 |
| `4 / seq 8` | **Repair dependency slice** `[PROPOSED]` | 根据 key0→unlock→take 的 causal support/threat，仅标记 A 的未来 suffix 与被破坏的 key dependency。先确认 B12 无依赖边、资源冲突、共享锁冲突或世界效果耦合；保留 B12 原身份和 progress。若依赖登记不完整或无法证明安全，扩大切片或保守 full replan，但也保留所有重新验证仍合法的活动/进度。 |
| `4 / seq 9` | **Actor knowledge/motivation + Planner** `[PARTIAL]` | 世界 planner 可知道 spare 在何处；ActorFeasibility 检查 A 当前 `O_A` 是否知道、是否愿意、是否能执行。此刻 A 不知道 spare，因此不能直接发 `take(spare)`。给 A 新信息需一个经授权并真实结算的观察事件；若无可行路径，返回 `knowledge_gap`/`no legal path` 区分。 |
| `4 / seq 10` | **Director / world opportunity proposal** `[PROPOSED]` | Director 比较 NOOP 与 `deliver_spare_location_clue`。仅在授权目录明确注册该算子并重新验证当前 W/grant 时，提交 `ActionIntent`；算子运行 `t=4→5`，在 `t=5` 投递已存在 spare 的位置事实。它不是生成/移动钥匙，也不直接写 O_A。若实现或许可缺失，立即返回 `REQUIRES_DOMAIN_EXTENSION`，此 success branch 不可执行。 |
| `5 / seq 11` | **W → O_A/ΔO → X_A → S/Commitment → Goal/Planner** `[PROPOSED]` | 投递 receipt 经合法 observation path 进入 O_A。A 形成 `X_A(spare-location clue is relevant and credible)`；demo updater 仅更新该 paper model 中声明的状态，不能把 hidden W 当认知。Goal selector 依自己的 commitment/S 排序，选择继续取得 ledger；ActorFeasibility 确认 spare 已在 A^O 中可知。 |
| `5→6 / seq 12` | **A ActionIntent → Settlement → W/O/Ledger** `[PROPOSED]` | A 自己选择 `take_spare`，提交新 ID `A32`；World 验证 spare 确实存在、可拿且可达后结算 holder=A。t=6 写 `spare_taken(A)`，仅按感知规则投影给 A。A31 旧中断 receipt 保留不变。 |
| `6 / seq 13` | **B12 boundary → Settlement → W/O/Ledger** `[PROPOSED]` | 同一 clock 到 t=6，B12 正常完成，保持原 action ID `B12`，elapsed `5/5`，World 结算 garden outcome 并记录 `garden_watered`。未发生玩家影响或资源冲突，因此不得重启、取消或重置 B12。 |
| `6 / seq 14` | **A O → X → S/Commitment → Goal/Planner** `[PROPOSED]` | A 收到自己取得 spare 的 settlement feedback，X/S 更新不改变其 ledger commitment；Goal/Planner 提议 `unlock(spare)`。执行前仍检查 A 的已知 affordance 与 World 当前 spare holder/lock 前提。 |
| `6→7 / seq 15` | **ActionIntent → World validate/Settlement → Ledger** `[PROPOSED]` | 新 action `A33(unlock_archive)` 经 World 校验 spare 仍由 A 持有且 archive 可开后执行；t=7 真实结算 `archive_open=true`，事件追加到 Ledger。 |
| `7 / seq 16` | **A O → X → S/Commitment → Goal/Planner** `[PROPOSED]` | A 观察到 unlock completion 后更新自己的 O/X；其 commitment 仍是取得 ledger，选择 `take_ledger`，而不是因子目标 `archive_open` 满足就关闭整项承诺。 |
| `7→8 / seq 17` | **ActionIntent → Settlement → W → Ledger → Monitor** `[PROPOSED]` | `A34(take_ledger)` 经 World 检查 archive opened、ledger 存在且 A 可达后结算。t=8 真实 `ledger_acquired(actor=A,item=ledger)` 事件提交；Monitor 用已封存的前缀 witness 在绝对 deadline `T=10` 前判 `SATISFIED`。之后 A 收到合法完成反馈才将 commitment 终态更新为 `COMPLETED`。 |
| `4→T=10` 的替代诊断 | **Monitor / planner status** `[PROPOSED]` | 若完整冻结 domain 无任何 spare 获取/线索路径，只有在 finite state/operator space 被穷尽并保存证明时，planner 才可报 `PROVEN_UNREACHABLE_IN_FINITE_DOMAIN`。若扩展数/时间预算先耗尽，结果为 `BUDGET_EXHAUSTED / NO_PLAN_WITHIN_BUDGET`，不是不可达证明。Monitor 与 planner 独立：无 acquisition witness 且 Ledger coverage 完整到 T 时判 `VIOLATED`；证据覆盖不完整则 `INDETERMINATE`。 |

**反例检查。**将 W 的 spare 直接喂入 A 的 `A^O` 是信息泄漏；修复时清空 B 的 RunningAction 是非局部破坏；以重规划为由把 deadline 从 10 改到 14 是时间语义错误；“当前预算未找到”不能报不可达。当前代码只有单 actor C++ Runtime 或单一 serial token Python executor，不能声称这里的多 actor 并发保留已经实现。

## D｜作者明确授权的覆写/亲写锁定片段；条件失效就 abort

**纸面设定。**作者显式授权 sequence `SCENE-07@v1`：前提是 Ada 与 Bo 同时在 meeting-room、原始签名信封 `env-42` 存在且未拆封；片段锁定作者亲写的两句台词和“双方把信封放到桌面”的动作顺序。grant 允许这一小段角色表现被作者控制，但不授权改写过去、伪造同意、补道具或任意写 `S`。进入检查时 `t=5` 条件成立；玩家在 `t=6`、第二句台词之前取走信封，导致后续 guard 失败。片段必须停止并记为 aborted，不能改写为角色自然说完或事后 retcon。

| t / 顺序 | 数据流 | 状态与证据 |
|---|---|---|
| `0 / seq 0` | **Author spec / permissions** `[PROPOSED]` | 编译带版本的 authored sequence：content hash、author ID/grant、角色与实体稳定 ID、锁定字段、进入 guard、逐步 guard、打断点、abort/允许分支、到期时间。TypedIR 负责约束检查，不自动成为控制授权。 |
| `5 / seq 1` | **W → guard evaluator** `[PARTIAL]` | 读取当前 W 与真实 ledger，确认两人都在场、env-42 存在/未拆，grant 未过期；每项读取带 provenance。Monitor/IR 可消费投影证据，但 guard→Runtime 的统一 adapter 尚无。 |
| `5 / seq 2` | **S/Commitment → explicit override route** `[PROPOSED]` | sequence 进入被显式记为 `AUTHOR_LOCKED` 的表现模式；不能写“Bo 自主决定说作者台词”。若内容要求改变真实心理 state，必须另有授权、模型兼容 setter、before/after 和依赖重审；本 trace 不覆盖 `S`，只锁定该段可见动作/台词。 |
| `5 / seq 3` | **Goal/Planner / ActionIntent** `[PROPOSED]` | 独立 `AUTHORED` 控制器经授权路由提交 `begin_locked_sequence(SCENE-07@v1)`，不是 actor policy 的自主选择，也不自动属于 WORLD_DIRECTOR 的机会目录。只有 grant 明确授予调度权时 Director 才可触发，来源仍是 `authored_locked`。World 校验 guard 和授权，再逐步准入 action；内部可见演出游标不等于时间推进。 |
| `5→6` | **Settlement / W** `[PROPOSED]` | 第一条作者台词与放置信封动作由 registered executor 逐项执行并结算；每步产生自己 event/receipt。sequence 不可越过正常 World 前提与世界物理校验。 |
| `6 / seq 4` | **玩家干预 → W/Settlement** `[PARTIAL]` | 玩家合法取得信封，World 将 `env-42.location=PLAYER`、ownership/holder 更新并追加事件；已经提交的第一句和放置信封历史仍在。 |
| `6 / seq 5` | **W → guard → abort** `[PROPOSED]` | 第二步进入 guard 重查失败；记录 `SCENE-07 aborted_at_step=2, reason=required_prop_missing`。不自动替换信封、不瞬移、不生成 fallback 台词；若作者先前明确写了合法 fallback branch，才重新编译/校验该分支。 |
| `6 / seq 6` | **O → X → S/Commitment** `[PARTIAL]` | 角色只从各自观察到的实际动作/玩家事件形成 X 与 S 更新。作者执行 provenance 保持单独标签，不混成自然动机。单 actor Runtime 有 self-action feedback 与 observation 更新接缝；这段多角色呈现与 author provenance 仍是 proposed。 |
| `6 / seq 7` | **Ledger → Monitor/Repair** `[PARTIAL]` | append `sequence_started`, `authored_step_committed`, `sequence_aborted` 以及玩家取走道具的真实 event；Monitor 检查“允许发生一次开始/按原条件完成或显式 abort”之类约束。Repair 只对未来允许分支重规划，不重写已说台词或隐去玩家取走道具。 |

**反例检查。**把 `AUTHOR_LOCKED` 显示成“Bo 自己决定”；玩家拿走信封后仍输出锁定台词；从 W 直接回填心理状态且不记 author setter；修改 sequence 内容却沿用旧 hash；都属于错误。这里的直接控制是合法但非自主的创作渠道，必须独立记账。

## 四条轨迹共同暴露的边界

| 接缝 | 当前证据 | 蓝图中的目标契约 |
|---|---|---|
| 一个 W / clock / executor | C++ scheduler + `WorldRuntimeAdapter` 对一个 actor 的 clock alignment；Python NPC system 有自己的单 clock/串行 token | 单一 WorldOwner 结算所有角色/玩家/导演动作，scheduler 只推进一份 clock；多 actor action 生命周期需显式扩展 |
| 每个角色独立的 O/X/S/Commitment/Goal | C++ 对单 actor 有真实 update hooks；Python A/B 有有限 local views 与 commitment 示例 | actor-local info boundary；全知 W 不能流入角色 planner；goal selector 不被 GOAP/HTN 取代 |
| ActionIntent / RunningAction / progress | C++ 有单 action gate、elapsed、validation；Python 有串行 duration action | shared-clock 多角色 running set、每角色身份、占用/共享资源锁、interrupt settlement 与 progress outcome contract |
| Director / author control | TypedIR monitor 只消费合成 trace；Python sample 有有限 prediction rollout 与一个独立 world operator | 有限且授权的目录、NOOP 对照、proposal version/hash、当前 W 重验证、预测与提交严格分离 |
| Ledger / Monitor / Repair | 各自独立 evidence/trace facilities；没有本文所述统一生产闭环 | append-only commit evidence；absolute deadline；局部 future repair；前缀保护、合法活动/进度保留、不可达与预算失败分开 |
| domain affordance | C++ 有限房间 `World/Scene/Object/Primitive`；Python NPC 有 key/ledger 小世界 | 纸面新增域算子必须逐个实现、声明来源/权限/观察与失败；不能凭 action 字符串获得能力 |

这些轨迹检查的是调用关系和权限边界是否能表达，不表示机制已经接通或行为自然。下一集成应从一个有限、真实可执行的共享领域切口开始，并复用一个 WorldOwner/clock/executor；不可把两个现有 Runtime 与独立 Monitor 直接并排跑，再称作统一系统。
