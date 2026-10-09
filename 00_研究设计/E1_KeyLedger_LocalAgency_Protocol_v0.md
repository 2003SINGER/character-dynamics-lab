# E1 Key Ledger Local Agency Protocol v0

日期：2026-10-09。状态：**CONDITIONALLY_REVIEWED / CLARIFIED**。版本：`E1-KeyLedger-LocalAgency-v0.r1`（仅澄清，不改 E0 冻结内容）。

本文是 E1-0 的单一有限实验协议：把 E0 的权威世界、结算与证据边界扩展为 A/B 局部信息和 B 自己选择行动的场景。用户已授权 E1-1 最小实现及开发验证；正式实验与 E1-2 实现/运行仍未授权。E0 代码、协议、结果和冻结 Runtime 不由本文修改，也不在此宣布 E0 `CLOSED`。来源为用户授权的 2026-10-09 私有原文（SHA-256 `5157c55186976448da407c07faeb540f451a742ff974747951fde184d093fc6a`）；本次独立 WebGPT review 来源 SHA-256 `6fc133ece2205cb7133f3961f1efffc206a6a770570d61244e3629ddaff5bbfc`；此处不公开原文全文。

所有 fixture 路径、预期 verdict、效率/预算上限均为 **HAND_DERIVED**，不是运行结果、算法表现或新研究结论。

## 1. 研究对象与报告层

问题：在同一权威世界中，A 只能按自己的观察规划取得账本，B 按自己可见状态和公开策略契约决定是否借钥匙；有限期限内哪些失败来自世界、固定 B 策略、A 的信息/绑定、规划求解预算或真实执行？

唯一主目标为真实结算事件 `ledger_acquired(actor=A,item=ledger)` 在闭区间 `[2,T]` 出现。A 没有自动归还工具的义务；B 的 `tool_returned` 与 `payment_received` 分别记账，不互相替代。真实行为是否合理或玩家是否感到角色“活着”不由本协议判定。

每个主条件分别报告：

1. `O_world`：合法 joint controls 下是否存在有限世界路径及最早 witness 时间。
2. `O_fixedB(πB)`：B 遵循本协议固定策略时，是否存在合法 A controls 可达目标及最早时间。
3. 各算法自身的求解状态、完整性、扩展数、耗时和策略/动作输出。
4. 一次实际 executor trace 的回执、最终目标事件及 Monitor verdict。确定性单次 trace 不是成功率。

上述四层不合并成“可完成”。尤其 `O_world` 不表示 B 会接受；`O_fixedB` 是对固定闭环的全知评估上界，不是 A 可见的计划器输入，也不表示存在对所有不可区分隐藏 W 都成功的 observation policy。

## 2. E0 继承边界与 E1 状态

E1 保留 E0-KeyLedger-v0 的实体 registry、初始已提交 `destroy_key(PLAYER,key0)` 历史、资源与 holder/beneficial owner 语义、原有 operator 前提和结算效果、单 offer session、ledger witness、追加式事件、coverage seal、deadline 右闭和 Monitor 语义。基准物理初态仍为 A/B 同在 ENTRANCE、key1 完整且由 B 持有、ledger 在关闭的 ARCHIVE、payment 与 toolB 由 A 持有（toolB 的 beneficial owner 为 B）。

E1 搜索配置另含 `O_A,O_B,goal_A,goals_B,policy_pin_B,T`；`request_used` 是仅供 World dispatcher exactly-once 校验的世界位，不能作为 B chooser 的输入。B 的 actor-local observation 使用独立的 `O_B.request_sent` 及其来源历史：初始值为 `false`，并带明确的初始自身历史 provenance；只有成功的 `tool_return_requested` settlement/自方回执（含 event ID、时间、actor）才将其置为 `true`。意图、启动尝试、拒绝或 pre-start rejection 均不得设置该 observation 字段。状态中不得将 actor 预测写入 W/O 或事件账本。A 的目标仅为目标 witness；B 的目标分别为取回 toolB、获得 payment、保留 key1 beneficial ownership。借出只转 holder，不转 beneficial owner。

`K=known` 与 `K=unknown` 只改变 A 的合法初始 observation：

| Pin | 初始 `O_A` | 初始 `O_B` / `W` |
|---|---|---|
| K-known | 有当前可借 key1 的合法观察及稳定 ID | 不变；B 知 key1、自身工具与交易状态 |
| K-unknown | 知 key0 已毁、archive/ledger 状态，但不知道 key1 是否存在或其 ID | 不变；同一 W 中 key1 实际完整且由 B 持有 |

Known/Unknown 是权限与零效果负对照。E0 通用 offer 不要求 A 先知道 key1；B 的接受回复会披露其 ID。因此协议不强制查询，不宣称信息差异必然改变路径或性能，也不以更换 offer 语义制造信息成本。Unknown 条件在真实披露前不得让 A 输入、候选队列或 ActionIntent 含真实 `key1`；B 实际 ACCEPT 并合法披露后，`O_A` 及后续绑定/队列可含该 actual ID。

世界 registry 中存在 key1 的实体 ID，不代表 A 的 actor catalogue 可枚举该隐藏 ID。公开动作目录可以说明存在“可借钥匙”这一匿名类型；这不等于 A 知道世界里有 key1，或能直接 ground 其 ID。公开 policy parameters 通过 t2 初始实验条件中明确的公开 contract/provenance 进入 `O_A`，不是隐藏 weight，也不是新增的免费 World action；它只说明本实验采用哪套策略规则，不模拟自然对话或作者沟通成本。

## 3. 动作、类型与信息效果

除新增项外，E0 operator catalogue 原样适用，所有动作 duration=1 模拟分钟。无 reoffer、无第二个 offer、无新钥匙/地点/自然过程。`offer_loan(A,B,payment)` 始终是无 key ID 的通用报价；ACCEPT 才披露实际 key ID。交易只在 E0 `accept_loan` 的 B 持有完整 key、payment、双方同场且该 offer 已接受等前提均满足时原子结算。

| Operator | Owner / typed arguments | Preconditions | Duration 与 effect / observation |
|---|---|---|---|
| `request_tool(B,A,toolB)` | B；固定角色/物件 ID | B 的 O 确认 `beneficial_owner(toolB)=B`、当前 holder=A；同场；`O_B.request_sent=false` | 1 min。仅成功 settlement 时 World dispatcher 设置 `W.request_used=true` 并追加 `tool_return_requested(B,A,toolB)`；合法投影含 event ID、时间、actor，B 据此置 `O_B.request_sent=true`，A 仅在合法 observer 时收到回执。只投影给合法观察者，不转移工具、不改变交易状态。pre-start rejection 不写 W/O；runner 可用本地 `lastreject` 抑制同请求重试，并按 no_control 规则推进时间。 |
| `return_tool(A,B,toolB)` | A；E0 typed grounding | E0 前提：A 持 toolB，双方同场 | 1 min。仅按 E0 真实结算转 holder、追加 `tool_returned`；事件及状态只投影给合法同场角色。请求不强制此动作。 |
| `offer_loan(A,B,payment)` | A；不含 key ID | E0 前提，且本 fixture 尚无 offer | 1 min。按 E0 记录唯一通用报价；A/B 可见条款，不披露 key ID。 |
| `choose_accept/decline(B,offer_id)` | B；固定 offer ID | B 可见唯一 pending offer；E0 的物理/交易合法性前提见 E0；§4 policy 仅决定真实 B chooser 选择哪个合法 reply，不是 World precondition | 1 min。按 E0 记录 reply；ACCEPT 才披露其可借 key1 的 ID 给 A。 |
| `accept_loan(B,A,key1,payment,offer_id)` | B；B 依据自己的 `O_B` ground 当前持有的实际 key ID | 仅 E0 物理/交易前提：同一 offer 已 ACCEPTED、B 持完整 key、A 持 payment、双方同场等。策略约束只限制实际 B chooser；不属于 World operator precondition | 1 min。仅 E0 原子交换；唯一真实 payment/loan effect 在此发生。A 未来 `unlock` 的 key binding 只能在真实披露后 ground。 |
| `unlock(A,key1)` | A；E0 grounding | E0 物理前提：A 持完整 key、archive closed、双方/地点满足 E0；另需 A 已合法知道该 ID，属于 actor authority 检查 | 1 min；仅打开 archive，A 仍持 key1。 |
| `take_ledger(A,ledger)` | A；E0 grounding | E0 物理前提：A 在入口、archive open、ledger 在内且无 tombstone；actor 需合法知道 ledger/门/容器事实。不要求持有 key1 | 1 min；真实 take settlement 才生成 acquisition witness。 |
| `idle/no_control` | WorldStep | 当前 actor 无合法/选择动作 | 1 min；无物品 effect。拒绝/空槽不允许零时重试。 |

A 在 Unknown 条件下可以提出不含 ID 的 offer。GOAP 内部可用 `LoanKey(offer_id)` 表示一个延迟绑定的预测变量；它不是 entity ID、候选动作或可派发参数。只有 B 实际 ACCEPT 并披露 key1 后，`O_A`、真实 action queue 与后续 A ActionIntent 才能 ground 到 actual `key1`。B 的 `accept_loan` 则由 B 从自身 `O_B` ground 当前实际持有的 key。若预测 B 拒绝或没有可借钥匙，计划必须在真实反馈后修订，不能合成披露/交易。

信息只在真实 settlement 后依 E0 投影规则更新。独立评估器可读 W 检查泄漏，A/B policy 不得读取 W、彼此私有 O 或私有目标权重。

## 4. B 的独立确定性策略

B chooser 只读 `O_B`、自己的三个目标、公开 schemas 与公开的 policy contract。下面三组参数随运行配置公开声明，并以合法来源记录投影给 A 的 `O_A`；不允许通过隐藏 B weight 或 oracle 推断作为 actor input。它们是有限策略条件，不是心理模型或真实人物动机。

**动作优先级**（逐次 B 槽）：(1) 若 offer 已 ACCEPTED 且未 SETTLED，依物理合法性与 §4.2 policy 选择合法 exchange 或 idle；(2) 若有 pending offer，按 §4.2 选择 ACCEPT/DECLINE；(3) 若 `O_B.request_sent=false` 且 `O_B` 知 toolB 仍由 A 持有，选择一次 `request_tool`；(4) 否则选择 `idle`。World dispatcher 另以 `W.request_used` 作 exactly-once 校验。两位必须在 checkpoint、fork、restore、搜索 key 与 replay 中独立保存，replay 不得重置任一位。本优先级仅用于后续 B 槽；t2 初始无 session，故 B 自主发出一次 request（或 idle）。该顺序不读取 deadline、fixture ID 或实验分组；调度器只识别公开 session/R 状态并开放 B 槽，不替 B 选择动作。

**交易评价。**令 `I=1` 当 `O_B` 认为自身工具目标未满足，否则为 0；`c` 为借出机会成本，`p` 为 penalty。对 ACCEPT 预评估：`V=2×1 payment−c−p×I`；DECLINE 的基准值为 0。`V>0` 才 ACCEPT；`V≤0` 时 DECLINE（tie-break 固定保钥匙/拒绝）。如 O_B 不支持有完整可借钥匙或有效 1-payment 报价，B 选择 DECLINE，reason=`NO_LOANABLE_KEY`。明确意图理由分别记 `TOOL_REQUIRED`、`KEEP_KEY` 或 `NET_GAIN`。此值是预测条件条款的策略评价；接受不提前产生 payment 或 transfer。

| `policy_pin_B` | `c` | `p` | 初始工具未归还时的 reply | 理由 |
|---|---:|---:|---|---|
| PAY | 1 | 0 | ACCEPT：`V=+1` | NET_GAIN |
| TOOL | 1 | 4 | DECLINE：`V=−3` | TOOL_REQUIRED |
| KEEP | 3 | 0 | DECLINE：`V=−1` | KEEP_KEY |

初始 request 先于任何交易，是因为 t2 初始无 session 且协议显式开放 B 槽；之后 chooser 服从上述 exchange→pending reply→one-time request→idle 顺序。主 fixture 中 A 若回应并真实归还，TOOL 的 `I` 变 0，`V=2−1−0=+1`。在仍缺工具的状态下 TOOL 为 `V=2−1−4=−3`。KEEP 的 `V=2−3−0=−1`，仍拒绝。PAY 不等待工具归还，可直接报价；它不把 B 的工具目标伪称已满足。实际各 goal 的完成状态只按 settlement 事件/真实状态分别报告。

**策略与物理合法性的分层：**E0 operator 的物理、资源、session 与同意记录前提是唯一 World legality。§4 的 utility 仅决定真实固定 B chooser 如何选动作，不是 `choose_accept`/`accept_loan` 的世界合法性前提。`O_world` 可穷举物理合法 ACCEPT，即使某公开 policy 的 `V≤0`；`O_fixedB` 每个 B 槽只调用固定 chooser；真实 trace 也只能由 chooser 提交动作。这样 joint 上界不与策略条件混淆。

## 5. 串行 scheduler 与权限

时间为整数分钟，从 `t=2` 起，窗口右闭。全局只有一个控制令牌；动作不可并行。每个 action/no_control 推进 1 分钟。启动前核验类型、权限与前提；运行中的 `R` 每个 boundary 只 continue 同一 ID、duration、elapsed 与 reservation，不启动第二动作。完成时按 E0 顺序提交 outcome/event、合法 O 投影，再 seal 当前分钟、更新 Monitor。t=T 先结算所有可在 T 完成的动作，再 seal T 并判定。

调度规则：

1. `t=2` 初始先开放一次 B 槽；B 按 policy 自主选择 `request_tool` 或 `idle`，均耗 1 分钟。
2. 之后有 `R` 时只 continue R。
3. 无 R 且唯一 offer 为 ACCEPTED、未 SETTLED 时开放 B 槽；B 按 policy 选合法 exchange 或 idle。
4. 无上述情况且 offer 为 OFFERED 时开放 B 槽；B 按 policy 选 ACCEPT/DECLINE。
5. 其他情况下开放 A 槽；A planner 只在自己的 O 与合法动作目录上选择。其余无动作/不提交动作时推进一次 no_control。

完成的 offer/reply/交易改变公开 session 后，下一空槽按同一规则计算。request 只有成功 settlement 才设置 world `request_used`；pre-start rejection 不写 W。runner 可保留本地 `lastreject` 抑制无效请求重试；这不是 world bit，按共同 no_control 规则前进。忽略已成功 request 不重置该 bit，不产生反复占令牌。拒绝不能冻结时钟；同一拒绝前提不可零时重试。串行顺序不代表 B 服从 A，也不授予 A 控制 B。

A policy 权限：目标只有 acquisition witness；输入为 `O_A`、已合法披露的信息、公开 schemas、授权目录、deadline、合法历史/回执及公开 B policy contract。A 可按公开 contract 预测 B 的响应，但不得读取真实 `O_B`、B 私有目标/历史或 `W` 来做预测；任何额外假设必须逐项标记为 hypothetical assumption，不能伪装成观察事实。A 对自己动作所致物理持有者变化的预测，只能从自己的已授权动作、公开 operator effects 与自身合法反馈推演；不得用隐藏 W 或 B 私有信息校正预测。若假设与真实反馈不符，须据合法反馈修订。B 的动作不是 A 可控 operator。每个 A 动作前后读真实 feedback 并重规划；不得把预测计划写成 settled history。request_tool 不产生 A 的自动归还目标。B 自己判断是否请求工具只基于自身 O_B 和自身回执；归还动作仍由 A 自己选择。A 只有在合法观察到 request receipt 后才将其作为输入。

Checkpoint 沿用 [E0 §5 fork contract](E0_KeyLedger_Protocol_v0.md#5-唯一执行定义与独立-oracle) 的完整字段与隔离要求。E1 在其上另存 `goals_A,goals_B,policy_pin_B,W.request_used,O_B.request_sent`（含 request receipt/provenance）、scheduler queue/current actor slot、A 的 actor-budget ledger、显式 assumptions、late-binding map/action binding 状态。搜索去重 key 必须分别保留 W request bit 与 O_B request history/provenance，以及影响未来的 O、绝对时间、offer/reply/settlement 状态、reservations、holder/owner、goal witness 摘要。不得只按物理 W 合并两个不同 actor knowledge state；也不得用 W bit 覆盖/重建 O_B history。

一条实际可复算输入包含初态 hash、K observation provenance、公开 policy contract hash、T、domain/operator revision 和 scheduler revision。重复运行相同输入须得到相同 policy action、trace 与 event ID 顺序语义；如实现使用随机 tie-break，协议条件不再是本版本，须另行冻结随机源与预算。

reply、exchange、request 和 return 的 actor 来源保留在 outcome/event 中。dispatcher 校验当前控制槽、actor authority、typed arguments 和当前 W；违反任一项则 `REJECTED_BEFORE_START`，不耗时、不产生 W effect。搜索器不能把非当前 actor 的动作塞入 action proposal 以绕过 scheduler。

## 6. 12 个主条件与手算预期

主矩阵是 `K ∈ {known,unknown} × πB ∈ {PAY,TOOL,KEEP} × T ∈ {8,10}`，共 12 条件。每一对 K 条件只改 `O_A`，手算合法最短路径与 oracle verdict 相同；实际 GOAP 的首动作、轨迹和成本仍待运行，不把 oracle 路径当作算法已产生的行为。不得把可能出现的零差异误报为信息效果。

所有主条件初始 B 槽均为 `request_tool`，结算 `t=2→3`。此 event 不转工具。以下是合法世界 joint-oracle/实际对应策略路径（HAND_DERIVED）：

| K / B policy / T | 手算路径或最短 witness | `O_world` | `O_fixedB(πB)` 与期限预期 |
|---|---|---|---|
| known / PAY / 8 | B request `2→3`; A offer `3→4`; B accept `4→5`; B exchange `5→6`; A unlock `6→7`; A take `7→8` | 可达，最早 @8 | 可达，@8；trace 可 SATISFIED @8 |
| unknown / PAY / 8 | 同上一行；通用 offer 不需要 key ID，ACCEPT 后才披露 | 可达，最早 @8 | 可达，@8；trace 可 SATISFIED @8 |
| known / PAY / 10 | 同 PAY @8 路径 | 可达，最早 @8 | 可达，@8；后续不要求仍持有账本 |
| unknown / PAY / 10 | 同 PAY @8 路径 | 可达，最早 @8 | 可达，@8 |
| known / TOOL / 8 | B request `2→3`; joint A 可直接 offer `3→4`; joint B ACCEPT `4→5`; exchange `5→6`; unlock `6→7`; take `7→8`。固定 TOOL 不接受缺工具的报价；A 自己选择先 return 才存在成功路径，B 不能强迫 A 归还 | 可达，最早 @8 | fixed TOOL 最早 @9，故 T8 不可达 |
| unknown / TOOL / 8 | 同 TOOL joint 路径；A 的实际输入仍只能 generic offer | 可达，最早 @8 | 固定策略期限内不可达；不得把 key 隐藏给 A |
| known / TOOL / 10 | request `2→3`; return `3→4`; offer `4→5`; accept `5→6`; exchange `6→7`; unlock `7→8`; take `8→9` | 可达，joint 分支最早 @8 | 可达，@9；tool 与 payment 分开记录 |
| unknown / TOOL / 10 | 同 TOOL @9 路径 | 可达，joint 分支最早 @8 | 可达，@9 |
| known / KEEP / 8 | B request `2→3`; A 可 offer `3→4`; B decline `4→5`; 无成功后续 | 可达上界可枚举 B 接受分支，最早 @8 | 不可达：固定 KEEP reply 拒绝，无替代钥匙 |
| unknown / KEEP / 8 | 同 KEEP；通用 offer 可到达 B，但其 policy 拒绝 | 可达上界 @8 | 不可达 |
| known / KEEP / 10 | B request `2→3`; A offer `3→4`; B decline `4→5`; 后续只能 no_control 到 T | 可达上界 @8 | 不可达，完整穷尽后方可报 fixed-policy unreachable |
| unknown / KEEP / 10 | 同 KEEP；不可因 hidden key1 直接越权 | 可达上界 @8 | 不可达 |

**joint 上界的槽位澄清。**E1 初始 `t=2` B 槽对真实 actor 固定按 B policy 执行。`O_world` 不跳过该槽：它按相同调度器执行一个合法 B 动作（最早路径可 request `2→3`），随后 A offer、joint B ACCEPT、exchange、unlock、take，最早 @8。后续 reply 可枚举任一物理合法的 ACCEPT/DECLINE，不受 πB 的 utility 决策限制；但不得跳过 physical preconditions/session。`O_world` 不受真实 policy 限制，且不是固定 B 策略。初始 t2 的 policy parameters 是已公开实验 pin，不是免费 world action。若独立 oracle 省略初始槽并报告 @7，则违反本协议调度语义。

Known/Unknown 的零效果预期来自 E0 offer 本身能询问并在接受后披露信息。条件间若只在 O_A 上不同，而动作链相同，这是有效 negative control，不是实验失败。T=8 的 TOOL 不可达来自策略先请求、A 按公开 TOOL contract 先归还、再报价所需 7 个 E1 分钟；T=10 留有余量。KEEP 在固定 policy 下拒绝；`O_world` 可选接受，只能作为世界上界，不能写成 KEEP 实际 B 回应。

主矩阵不加入额外 query，也不改变 Offer 语义。若某算法在 K-unknown 中因为“必须先知道 key1 才能 offer”而报告无解，属错误 operator/权限建模：它忽略了合法通用 offer。若它直接把 `key1` grounding 到未知前提、或者用隐藏 W 区分 K 条件，则属信息泄漏，不是更高规划能力。

主结果采用逐格而非单一汇总分数。相同的 K 对照应并列列出 `first_action_Kknown/unknown`、`solve_status`、`earliest_witness`、`trace_verdict` 和 `Monitor_verdict`。B 的三项目标按已结算证据单独记为达成/未达成；B 的 request event 只证明提出过请求，不证明 A 已归还工具或 B 已完成其工具目标。A 在 deadline 前取得后即满足事件目标，即使随后账本 holder 改变。

## 7. 成熟比较对象与公平性

**E1-1 基线：actor-local GOAP。**算法冻结为 A 授权 operator 上的 `h=0` uniform-cost search，priority 为 `(累计实际模拟分钟, canonical sequence)`；同分序列顺序固定为 `return_tool, offer_loan, unlock, take_ledger, idle`。cost 包括预测环境中每个 B 槽/动作的实际分钟。搜索闭包可推进公开 B chooser 的预测回合，但预测 B 动作不是 A 的可执行 operator，真实 B proposal 始终只由 B chooser 产生。Unknown 的 `loanable` 明确确定化为 true，标 `UNKNOWN_LOANABLE` assumption，并仅用 `LoanKey(offer_id)` symbolic variable，不写入 `O_A` 或实际 action queue；收到真实回复后以事实更新并重规划。候选必须经 executor 校验。A 拒绝提交/无 plan 时按共同 no_control 推进到 deadline，不增加“为验证拒绝而必须 offer”的特例。冻结版本、tie-break、replanning 总预算和完整性均逐例记录。

**E1-2 独立成熟能力检查：有限 belief-state AND/OR strong-goal solver。**显式 finite belief state 保留观察等价状态；每状态 OR 选择一个当前可执行的 A 动作，后继按真实可观察 reply 分组，AND 要求所有后继均可达目标；绝对时间进入 key，因此有限且 acyclic。Unknown 的匿名 `loanable` 变量可为 true/false，非实际 ID；Known 则有当前可借 key1 的合法证据。unknown 若含无钥匙分支，可因 AND 语义无 strong policy，即使 actual W 有 key1 且 PAY trace 成功。这是 `∃policy ∀observable outcomes` 与实际单轨迹目标不同，不是强 baseline 的失败，也不与 GOAP trace 完成率排名。不得加入未声明 partial-policy/fallback 伪报 strong 解。此 solver 是 E1-2 独立能力检查，不是 E1-1 GOAP 的同目标性能基线。

上述是有限显式问题实例化；借鉴 belief-state AND/OR 强策略定义，不声称 MBP 算法/BDD 实现或复现。Bertoli et al., IJCAI-2001, pp.473–478（PDF 显示页 56–61，零基索引 55–60；文献定向核查，未声称全文精读），§2–4/Fig.2：[核对原件 PDF](https://www.ijcai.org/Proceedings/01/IJCAI-2001-e.pdf#page=56)。Orkin, GDC 2006 的 GOAP 工程参照：[原件 PDF](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)。[Sabre](https://ojs.aaai.org/index.php/AIIDE/article/view/18896) 是集中式信念/意图解释规划参照，不移植，不作为弱 baseline，也不冒充独立在线 B。

| 对象 | 量词 / 信息 | 输出与解释 |
|---|---|---|
| `O_world` | `∃ joint controls`；评估器全知 W、但遵守初始调度槽 | 世界可达上界及最早时间；不说明 actor 知道或愿意 |
| `O_fixedB(πB)` | `∃ legal A controls`，B 每槽恰按本协议固定 policy；评估器可枚举闭环 | 固定策略下的可达性上界；不把 oracle state 给 A，不是对所有 indistinguishable W 的 observation policy |
| GOAP | A-local observation/search，B 按真实 policy | A 提案、预算、反馈后重规划与实际 trace |
| Strong AND/OR | `∃ A policy ∀ observable successor`，覆盖 belief 内每个合法 outcome | strong-goal 是否存在；与实际合作轨迹分别报告 |
| Monitor | 对已提交、封口 settlement event 作判定 | `PENDING/SATISFIED/VIOLATED/INDETERMINATE` 与 witness；不能调度或证明可达 |

两 oracle 用独立手写 precondition/effect 表和独立状态遍历；不得调用 GOAP 的搜索/transition，也不得把 executor 的 transition 函数当作自身 oracle effect。共享纯 ID/schema/fixture 常量允许。用文件 hash、Unknown 首动作 invariant 及负控检查潜在隐信息泄漏。若 `O_fixedB` 与 trace 不同，先归因于 oracle 可规划的 A controls 与实际 planner/执行预算差异，不宣称单一因果机制。

`O_fixedB` 是执行评估器对固定 πB 的 complete closed-loop reachability search；它可以枚举所有合法 A controls，但每个 B 槽都调用固定 chooser。其输出需同时带 `complete/exhausted/termination_reason`。该对象可以回答“给定确定性 B policy，是否存在可完成的 A 行为”，不能回答实际 GOAP 是否找到该行为；预算耗尽时不得给 unreachable。

Strong AND/OR 的每个 belief successor 按 A 实际能区分的合法 observation 分组；隐藏 W 不得作为分组标签直接暴露。unknown `loanable` 值是 A 的 epistemic alternatives；实际 policy execution 时，B 根据自身 O_B 对真实 W 作出唯一动作。两种评估不能用一次 shared-state transition 把 B 的真实 private observation复制给 A。

## 8. 预算、指标与失败分类

每 solver/episode 的开发配置 expansion cap 为 10,000，作为跨 replans 的算法总上限；一个 case 内所有 A replan 共用同一预算 ledger，不可每轮重置。belief/状态 successor 原语生成量另计，防止一个 belief expansion 隐去大量枚举成本。2 秒只是可显式配置的候选 watchdog 值；触发时记录 `termination_reason=WALL_TIMEOUT`、`solve_status=BUDGET`、`complete=false`。无论 expansion 或 watchdog 停止，未完成的开发 case 不计正确性 PASS。runner 必须区分 `EXPECTED_VERDICT_CHECK`（预算内完成并与 hand-derived verdict 对照）与 `INCOMPLETE_BUDGET`（未完成，不能计 PASS）；禁止隐式提高 cap、失败后关闭 watchdog 或靠删改 case 掩盖停止。此配置不修改 E0 cap，也不宣称已适合正式实验。

E1 实现前置开发验证须运行固定开发配置，保留环境信息和所有结果，包括 budget miss；不得据此改写预期 verdict。正式实验前才冻结 formal budget 与 environment 一次，并记录版本/hash。已授权的前置开发验证与结果由独立实现/结果 owner 维护；本协议不选择更大预算或授权正式实验。正确性问题（权限/信息泄漏、schema 或 settlement 不一致、事件错误）始终是硬失败，与墙钟预算无关。E1-1 的校准对象是成熟方法在该有限契约下的正确性和可报告性，不是 NPC 科学瓶颈或已训练的动力学。

逐例记录 domain/protocol revision、源码 revision、condition/hash、K/policy/T、actor input O 与授权目录 hash、planner/oracle/policy 版本、扩展/生成数、耗时、终止原因、每步 ActionIntent/start/outcome/settlement、A/B O 投影、tool/payment/ledger goal 状态、event IDs/seals、Monitor verdict 与实际 witness。Known/Unknown 成对报告首动作和轨迹差异。

求解器结果结构至少分为 `solve_status`、`complete`、`exhausted`、`termination_reason` 与 fixture 对照判定。状态 cap 或 wall timeout 时标 `BUDGET`。找到并验证合法 goal 可标 `SOLVED, complete=true`（UCS 目标出队可证明最短 cost），不要求整个 frontier 穷尽；`exhausted` 独立记录。强 AND/OR 可在根 belief 的所有后继均已证明时给 complete strong verdict，也不要求搜索无关节点。只有有限域无解结论需完整穷尽或有效证明，标 `PROVEN_UNREACHABLE_IN_FINITE_DOMAIN`。实际执行 trace 单独用 `TRACE_SATISFIED/TRACE_VIOLATED/TRACE_INDETERMINATE`，不能由 search status 伪造。

失败标签可并存：`WORLD_UNREACHABLE`（穷尽 `O_world`）、`FIXED_B_UNREACHABLE`（穷尽固定策略 oracle）、`ACTOR_KNOWLEDGE_GAP`、`POLICY_DECLINE_OR_PRIORITY`、`INVALID_BINDING_OR_AUTHORITY`、`PLANNER_NO_PLAN`、`BUDGET`、`EXECUTOR_REJECTED/INTERRUPTED`、`TRACE_MISSED_DEADLINE`、`MONITOR_PENDING/VIOLATED/INDETERMINATE`。标签不自动是因果归因；例如 oracle 可达而 GOAP 未解，只有排除预算、绑定、执行/规格不一致后才可称有限域 planner miss。

## 9. 非主矩阵负控与验收病例

以下负控不计入 12 主格的成功率或均值；只用于接口正确性：

1. **key1 tombstone：**继承 E0 N02 状态，key1 holder=none、intact=false、tombstone 保留，B 的合法 O 知自有钥匙已失效。无其它替代钥匙；穷尽后两个 oracle 均无目标路径。仅有限域不可达。
2. **错误 key binding：**Unknown A 将 key1 加入 generic offer 参数或直接提交 `unlock(A,key1)`。前者违反 schema、后者违反 actor knowledge/authority；dispatch 前拒绝，0 分钟、无 W/O/event effect。generic offer 本身仍合法。
3. **强制同意/拒绝后交易与独立回复：**A 提交未经 B ACCEPT 的 `accept_loan`，或 DECLINE 后交易。拒绝在 start、无 holder/payment 部分变化、无 `loan_exchanged`。另从合法 OFFERED checkpoint 调用实际 B chooser，分别检验 PAY 接受、TOOL 缺工具拒绝/归还后接受、KEEP 拒绝及真实 reply settlement。此是 consumer-level 负控，不强迫知道公开契约的 GOAP 为演示拒绝而报价；KEEP 主轨迹可以 `no_plan→no_control`。
4. **同 O 不同隐藏 W：**构造两个 checkpoint，B 的 `O_B`、B goals、公开 contract 与候选目录相同，仅隐藏 `W.request_used` 不同；B chooser proposal 必须一致，虽然 World dispatcher 的验证结果可以不同。拒绝或 pre-start rejection 不得设置 `O_B.request_sent`。另构造 A input hash 相同但 key1 hidden truth 不同的 checkpoint；A 首个 grounded proposal 必须一致，禁止读取 W 或实际 O_B/私有目标历史来挑出 key1。此检查不要求未来轨迹相同。
5. **预算 cap=1：**诊断 runner 首次扩展后 frontier 非空必须报告 `BUDGET`，不是不可达；不用于扩大正式 cap。
6. **事件与状态区分/恢复隔离：**holder=A 不能代替 acquisition event；fork/replay、receipt、seal 与 E0 既有回归语义保持，真实 settlement 不得被预测、预演或恢复副本污染。

## 10. 实施顺序、停止与审阅门

**E1-1（最小实现与开发验证已获授权；正式实验未授权）：**只接入 E0 独立 executor/Monitor adapter、新增一次性 B request、公开 deterministic B chooser、A-local GOAP 与 `O_world/O_fixedB` 两独立 oracle；在开发配置下运行协议病例与负控，结果按 §8 标记 `EXPECTED_VERDICT_CHECK` 或 `INCOMPLETE_BUDGET`。E1-1 不含 AND/OR 实现。开发结果不能称为正式实验或独立关闭。停止门：任一泄漏、schema/settlement mismatch、未封口 verdict、预算误标或 oracle 不独立即暂停该 case 并保留证据；不得调参掩盖。

**E1-2（需另行授权）：**单独实现并评估有限 explicit belief-state AND/OR strong-goal solver；按 §7 的强策略量词报告，不与 E1-1 单轨迹完成率排名。只比较冻结同域及预算下的各自定义对象。

**HAND_DERIVED 规格审阅结论：**无须修改 E0 通用 offer 才能定义 E1；Known/Unknown 是零效果权限负控。真正的实施门是：确保 B policy contract 确实公开进入 A 的合法 O；串行 scheduler 不隐式代选 B；A 的 late-bound key 预测不泄漏 actual ID；两个 oracle 独立且量词各自正确。任何一项实现不满足就阻断该实现结论，协议本身不预判实验通过。

2026-10-09 父级完整复读及另一 Luna 的只读规格审阅已完成；随后独立 WebGPT review 提出 request visibility 与 budget semantics 的窄修正，本版据此澄清。协议修订不构成实现测试、正式实验或 E1 外部独立验收；实施状态为 E1-1 DEVELOPMENT implementation/run authorized，formal experiment 和 E1-2 未授权。不得据此将 E0 或 E1 声明为 `CLOSED`。

限制：有限手工域与三条确定性 B policy 只回答本协议条件；不估计真人/玩家概率，不证明心理规律、方法新颖性、普遍 GOAP/HTN 能力、作者成本、玩家体验或真实 NPC 生命感。13 个长期研究方向仍由其既有 owner 维护，本文不重排或删减。

## 11. 本人理解留白

以下由用户本人补写；本协议不替用户形成结论。

- 我如何理解 joint world oracle 与 fixed-B oracle 的不同问题：
- 我如何理解 Unknown 条件下 `LoanKey(offer_id)` 与真实 key ID 的边界：
- 我认为 E1-1 最值得观察的失败分类及原因：
