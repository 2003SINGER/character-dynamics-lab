# E0 Key Ledger Protocol v0

日期：2026-10-08。状态：**PROTOCOL_DRAFT / READY_FOR_INDEPENDENT_REVIEW**。

本文是本有限钥匙账本 E0 域的唯一执行协议 owner；它把 [04 §2 统一实例](../01_文献/算法积木/04_统一问题与成熟基线准入.md#2-统一实例域约定与判定层)具体化为可手算、可由独立有限执行器复核的协议，不重写 F0/F1 总定义，也不改 Pilot 的 Monitor/reference 语义。下列域选择、oracle、预算与 fixture 是本协议拟议选择，不是旧有实现、实验观测或论文事实。本轮只写协议，不实现、不运行实验。用户外审前不得称为已冻结、可开工或已通过。

## 1. 目标与边界

E0 只检验：此有限域中是否存在合法 joint action script；独立执行器能否逐步结算；Monitor 能否从完整追加式事件流判断 ledger_acquired(A,ledger) 是否在 t≤10 发生。另检验固定、确定性 B 答复脚本条件下的逐条正确性。

E0 不比较角色在线策略、独立策略能力、信息不对称行为效果、玩家在线扰动、GOAP/HTN/repair 效果，不做玩家概率评估。存在性脚本里的角色动作是枚举 joint controls，不表示角色会选择或自主执行。

E1/E2 若另获授权，只另行审计其与 frozen Runtime Kernel 的 adapter/replay 接缝；本协议不预写其 protocol。

不得由 E0 推出 ∃d ∀responses、作者鲁棒保证、真实 NPC/玩家概率、心理规律、玩家体验、研究缺口、新颖性、开放域可达性或方法优势。E1/E2 才讨论策略、扰动与修复；需另行授权。

## 2. Closed finite domain

### 2.1 初态与时间

- 时间为整数模拟分钟 t∈{2,…,10}。基准 fixture 中每个列出的 action 恰好 1 分钟，串行执行，单一 A/B/PLAYER 控制令牌，无并发。idle/no_control 是既有 WorldStep 的 1 分钟无操作推进，不产生 item effect；没有行动也不能冻结时钟。
- 初始检查点 t=2 前，玩家已真实结算 destroy_key(player,key0)：key0 有不可删除 tombstone，key0_intact=false。这是输入历史，不在搜索脚本中重演。
- typed entity registry 为 A、B、PLAYER、key0、key1、ledger、payment、toolB、ARCHIVE、ENTRANCE；PLAYER 只作为已提交前缀事件的来源，不是在线可控角色。ARCHIVE 是固定容器 ID，不添加房间或移动规则。A、B 初始 location=ENTRANCE；A 知入口。初始 holder：key0=none（已毁）、key1=B、ledger=ARCHIVE、payment=A、toolB=A；beneficial owner：key0=PLAYER（销毁前）、key1=B、ledger=ARCHIVE、payment=A、toolB=B。archive closed。A 的 O 知 key0 已毁、archive closed 与 ledger 在内，不知道备用 key1 存在/持有人；B 知道 key1。key0/key1/ledger 的 intact/destroyed 显式存储；基准 key0 destroyed、key1 intact、ledger not destroyed。不存在其他实体、钥匙、资源、地点、自然过程、隐式动作或在线外部输入。
- A 的唯一 E0 目标是 t≤10 前真实 settlement event ledger_acquired(actor=A,item=ledger)。这是“曾取得”事件，不是 t10 仍持有状态；后来失去 ledger 不删除 witness。
- B 的两个目标分立：取回 toolB、获得 payment。return_tool 仅满足前者，不蕴含借钥匙或 payment。E0 固定答复不由目标值计算，不声称已建模 B 的自主效用/策略。
- 交易参数固定为 1 payment、借出机会成本 1。ΔU_B=2×payment−loan_cost=+1 仅说明接受可解释，不驱动 executor、搜索 cost 或答复。B 可接受或拒绝。

### 2.2 完整 grounded operator catalogue

除 fixture 前缀中已提交的 destroy_key(PLAYER,key0)（N02 另有 key1 的 tombstone，保留 key0 原前缀）外，可枚举动作恰为表中八种（含两个独立 reply grounding 与 idle/no_control）。destroy_key 不属于搜索动作。没有 drop、lose、赠送、hint、传送、补物品或其他在线外部操作。启动拒绝本身不耗模拟时间、不部分结算；runner 同一边界不重复提交拒绝请求，而以 no_control 推进下一分钟，禁止零时间重试冻结世界。搜索只枚举合法转移。

| Action / owner | typed grounding、前提与时长 | 结算变化 |
|---|---|---|
| offer_loan(A,B,payment) / A | 同在入口，A 持 payment；只问“你是否有可借出的钥匙？若你确认并披露该钥匙，我愿支付 1 payment 借用所披露的钥匙”。报价不含 key ID、数量或对 key1 存在的预设。 | 记录唯一 offer ID、通用条款与可见性；物品不变。A 的报价是对该通用条件的预先确认。 |
| choose_accept(B,offer_id) / B | B 收到该 offer，且持有完整、未毁、可借 key1。 | 记录 B 对通用条款明确同意，并披露稳定 key1 ID；不移动物品。 |
| choose_decline(B,offer_id) / B | B 收到该 offer。 | 仅记录拒绝；不移动物品。 |
| accept_loan(B,A,key1,payment,offer_id) / B | 同一 offer 有 A 报价和 B 接受；双方可见同一条款；B 持完整未毁 key1、A 持 payment，二人在入口。 | 单一原子交换保管权：key1 的 holder 改为 A、beneficial_owner 仍为 B；payment 转归 B；追加 loan_exchanged，A 的 O 获知 key1。若校验失败，holder/付款均不变，无交换 event。 |
| return_tool(A,B,toolB) / A | A 持 toolB，二人在入口。 | 1 分钟末 toolB 转给 B，追加 tool_returned；不改变 key/payment/答复。 |
| unlock(A,key1) / A | A 已知 key1、持有完整 key1，在入口，archive closed。基准 duration=1；P02 使用显式 duration_pin=3。 | duration 末 archive=open；A 仍持有 key1。P02 期间 reservation 固定绑定同一 running_action ID、key1 与 archive。 |
| take_ledger(A,ledger) / A | A 在入口、archive open、ledger 在 archive 且无 tombstone。 | 1 分钟末 ledger 归 A，追加唯一目标 event ledger_acquired(A,ledger)。 |
| idle/no_control / WorldStep | 当前分钟不投递 actor action；clock 到下一分钟。 | 1 分钟后时间推进；没有物品/位置/门/账本 effect。 |

offer_loan 是 A 对通用借用条件的绑定报价/预先确认；B 的 choose_accept 同时确认该通用条件并披露要借出的 key1，未增加 A 的确认步骤。accept_loan 检查两条 session record，不新增第六个确认动作或分钟。B 的答复不是 offer 的 effect；不能由 A、planner 或交易请求伪造。D_joint 的两个明确 groundings 是 choose_accept(B,offer_id) 与 choose_decline(B,offer_id)；BReplyPin 固定其中一个、重复运行不调用异步策略。A 在 ACCEPT 前不能绑定/提交未知 key1，答复后只能按 B 实际披露的 key1 绑定。

有限 session 状态只有 NONE→OFFERED→ACCEPTED→SETTLED 或 NONE→OFFERED→DECLINED。每个 fixture 至多一个 offer；每个 offer 至多一次 B reply；同一 offer 不允许相反/重复答复；接受后最多一次交易结算。return_tool、unlock、take 各最多成功一次；idle 可重复至 t10。typed arguments 仅为表中固定角色/物件/offer ID，且由已列实体 ID ground；没有自由文本参数或实体生成。

operator schema 对所有 action 统一固定为 E0-KeyLedger-v0：ID/参数类型/控制者/precondition/duration pin/invariant/resource read-write/信息投影/settlement effect/failure outcome 由本节表和以下规则穷尽。action start 前 precondition 或 authority 不满足→REJECTED_BEFORE_START，零耗时、零 W effect、无成功 event；开始后中断→按实际 elapsed 推进 clock、保留已提交前缀、无本动作 settlement effect；成功则只在规定完成边界结算。reservation 仅在 running_action 存续期间占用。

信息投影固定为：初始 O_A/O_B 均知道 key0 tombstone、archive 入口、ledger 位于 closed archive；只有 B 知 key1 存在及其 ID。offer 条款同时对 A/B 可见且不披露 key ID；B 的 ACCEPT/DECLINE reply 及时间对 A/B 可见，ACCEPT 才将被披露 key1 ID 加入 A 的 O；交易完成后的持有/付款变化、return_tool、unlock、take 在同场双方可见。未列接收者不更新 O。所有世界效果由 executor 先结算后投影；O 更新不能回写 W。

成功算子只产生表列出的 effects。目标 event 仅由真实 take_ledger settlement 产生。executor 可记录 start/reject/outcome；Monitor 目标投影仅读实际 settlement event，不把 start、proposal 或预测当 witness。destroy_key 仅为初始历史，不在搜索动作集。

### 2.3 成功轨迹与 seal 顺序

主成功迹严格为五个 1 分钟 settlement：

| 时段 | action | 结算后 |
|---|---|---|
| t2→t3 | A offer_loan，无 key ID | offer/条款记录；物品未变 |
| t3→t4 | B choose_accept | B 同意并披露 key1；物品未变 |
| t4→t5 | B accept_loan | 原子交换；A 持 key1，B 持 payment |
| t5→t6 | A unlock | archive open |
| t6→t7 | A take_ledger | A 持 ledger；目标 event @t7 |

t2 玩家 destroy 是已提交前缀，不占这五步。D_joint 同时枚举 choose_accept 与 choose_decline 两个 grounding，存在性 search 可找到 ACCEPT 成功 path；D_pin 固定 DECLINE 时，穷尽后该条件域无成功 path。一次条件失败不自动说明其他 response 下不可达。idle 可将本路径推迟：t2→t5 连续 3 分钟无操作，再按五步成功链在 t10 恰好结算。

同一物理时刻的全部 settlement events 先按单调 sequence 追加，再 seal_events_through(t)；seal 后不得向 time≤t 追加。E0 Monitor 只读 settlement 流。每分钟结束边界先处理全部 outcome/event，再 seal 并 evaluate。t10 时必须先处理所有可在 t10 结算的 action/event，再 seal t10、最后评估；deadline 右端点包含，禁止先 seal 后补写 t10 事件。

## 3. State、合法性与执行结算

唯一世界状态：
W=(t, location[A,B], holder[key0,key1,ledger,payment,toolB], beneficial_owner[key0,key1,ledger,payment,toolB], intact[key0,key1], destroyed[key0,key1,ledger], archive_open, offer_session[NONE/OFFERED/ACCEPTED/DECLINED/SETTLED], action_used_bits, running_action[id,operator,start,duration,elapsed,authority,progress], reservations, action_history, event_ledger, config_pins[deadline,reply,duration])

O_A/O_B 独立保存。A 初始未知 key1；仅 ACCEPT 答复可向 A 投影 key1 ID/条款。planner 的搜索状态另含目标 monitor 摘要与 action frontier，不将其写成世界事实。物品有唯一 holder/owner；借出只转 holder，B 保持 key1 beneficial_owner。基准 action 串行；duration_pin=3 的 unlock 在执行中持有同一 reservation。D_joint 枚举 B 的 ACCEPT/DECLINE 两个 legal choices；D_pin 为对应 reply 固定的子域，只移除与 pin 不符的 reply 边，不改其他 transition。

每个 actor action 在 start 校验表内前提和控制权限；duration 由固定 domain pin 给出，基准均为 1，只有 E0-P02 的 unlock 为 3。多分钟 action start 时创建唯一 running_action ID 并一次性取得 reservation。每过一个分钟边界推进 Δt=1、elapsed+=1；若 elapsed<duration，只保存进度/继续 reservation，不产生 item effect；仅 elapsed=duration 时 settlement 一次并释放 reservation。idle 是 WorldStep 的 1 分钟推进。域无中途 partial effect。若结算前提因外部变化失效，回执 INTERRUPTED_NO_EFFECT；时间按已过时长前进、释放 reservation、无本 action settlement effect。E0 fixture 不施加在线变化，该分支仅用于 executor mismatch/注入错误检查。拒绝在 start 无 W 副作用。reservation 不因 boundary/重考虑重计数。

原子顺序：validate 当前 W → start/取得一次 reservation → 每分钟推进 clock 与 elapsed → 未完成则只保存 progress → 完成时计算唯一表内 effect并释放 reservation → 追加 outcome/event → 投影合法信息 → 同刻事件全部提交后 seal → 更新 Monitor。非法请求不得产生成功 effect；失败 trace 和已结算历史不能被后续状态回滚。

运行中的全局串行令牌容量为 1；R 尚未完成时不能启动任何新 actor action。no_control 只推进当前 R 的 elapsed，不新建或替换 R。预约在 start 取得、完成/中断时释放；边界 continuation 不重复取得。

## 4. Monitor、证据与权限

唯一 E0 硬目标是 Pilot 已定义语义中的有界事件义务：
EventCount(ledger_acquired, {actor:A,item:ledger}, min=1, maximum=None, window=[2,10])

窗口含左右端点。Monitor 输入是只追加、带 event ID/time/sequence/typed args/producer version 的 settlement ledger 和 coverage seals。它不以计划、holds snapshot、action start、loan_exchanged 或 key tombstone 代替目标 event。

maximum=None 是现有 AST 的“不设上限”，不输入浮点 Infinity。生产桥须先将 event ID/producer/内容与真实 executor settlement 回执核对；Monitor 不能单靠一个形状合法的伪造 event 自行证明其来自 W。

- 覆盖完整至 now、无 witness、now<10：PENDING。
- 发现合法目标 settlement event：SATISFIED，附真实 event ID/time/sequence；可提前判定。
- 已 seal 至 t10、覆盖完整且无 witness：VIOLATED。
- 相关过去 coverage 缺失而未有决定性 witness：INDETERMINATE。
- 假造/冲突 event、producer/schema version 不兼容或非法输入均为 contract error，不映射为 INDETERMINATE 或 VIOLATED。

planner/oracle 可读完整 W 做存在性搜索。A 的候选与答复前 binding 仅来自 O_A 和登记目录。B 答复由固定 pin 输入。Monitor 读已提交目标 event，但不能调度、补物、改 owner、授权或替角色同意。E0 无导演权限。

## 5. 唯一执行定义与独立 oracle

本协议 §2.2 的 hand-coded transition table 是此有限域唯一执行定义；后续拟实现最小独立 finite executor，现尚未实现。planner 提交 grounded proposal，每步由 executor 重新校验、结算；Monitor 只读真实 settlement。E0 不调用或修改冻结 Runtime。

X01 的 prediction check 是 executor 外的审计步骤。输入为预测记录：grounded `ActionIntent`、预测前置事实、预期 post facts、effects/events、checkpoint/frontier 标识，以及 operator/duration/deadline/reply pins；另输入独立 executor receipt（accepted/rejected、settlement outcome/ID/sequence）与实际 `ΔW`、合法投影后的 `ΔO`。operator version 定义 mandatory prediction coverage 与 effect/event 签名，须覆盖应发生与应不变/不发生项；字段缺失、coverage 不全或版本不匹配均为 `PREDICTION_CONTRACT_ERROR`，不得静默忽略。executor 只接收并校验 `ActionIntent`，不得接收预测 effects/events 作为执行指令，也不得把角色不可见的 W 提供给角色；中央审计器可读 W 核对实际 delta。预测后置事实须分别标明角色已知 O 与审计用 W，不能把后者冒充 actor input。

合法动作一旦真实 settlement，先提交实际 W/event 与合法 O 投影，再比较预测；差异记 `PREDICTION_MISMATCH` 并保留已提交事实，禁止 rollback。非法 typed binding（如通用 offer 尚未接受时就把 `key1` 写入其 ActionIntent）在 dispatch 前产出 `INVALID_BINDING` 诊断，不调用 executor，也不产生结算。另一个独立变异是合法的通用 offer ActionIntent 不含 key ID，但预测声称该 offer 会让 `O_A` 获知 `key1`：先按正常规则提交 offer settlement，再以实际 `ΔO_A`（没有 key1 披露）对账并报 `PREDICTION_MISMATCH`，保留已结算 offer，不能把预测披露写成角色实际知识。unlock 若合法启动/完成但预测声称直接产生 ledger/acquired event，也先提交 unlock 的真实结算，再以实际 `ΔW`/receipt（只开 archive，无 ledger event）对账并报 mismatch；检查不能相信或仅转发预测 effect 字段，即使 executor 忽略该字段，独立预测比较仍须检出差异。

oracle 必须独立于 planner：枚举全部 grounded choices 的有限状态遍历；其 precondition/effect 由独立手写 predicate/effect 表或逐步人工 goldens 表达，不能调用 planner 的 operator/effect 函数、共享转移代码或抽象状态更新。双方只共享本协议的常量/ID 和 fixture。只把 DFS 换 A*、仍共用 transition effect，不算独立 oracle。

oracle 去重 key 包含所有影响未来合法性/effect/目标的状态、绝对时间、O 可见性、有效 offer/reply 记录、目标相关 ledger 摘要和 Monitor 状态。只有证明对未来授权、同意、资源与 witness 无影响的历史字段才可规范化掉。Horizon 至 t10 含；仅展开能在 t≤10 完成的 action。穷尽完整有限状态空间且无 witness 才是 PROVEN_UNREACHABLE_IN_FINITE_DOMAIN。

planner 用 h=0 uniform-cost search（即按累计模拟分钟排序，不按动作个数）；独立 oracle 完整枚举可达状态并独立记录最早完成时间。对每个未变异 fixture 比对可达 verdict、最早完成时间及最短总模拟时长；动作数只作辅助报告。对 D_joint，至少有一条 ACCEPT path；对 D_pin(DECLINE)，完整穷尽后应为有限域不可达。成功路径逐步回放独立 executor，并核对真实 events 与 Monitor witness。最短性只针对本冻结域和相同 duration pins。差异记 PLANNER_EXECUTOR_MISMATCH 并停止该 case，不能改 oracle/fixture 抹差异。变异 fixture X01 单独检查 binding validation 与 prediction check，不要求 mutant planner 的搜索 verdict 与 oracle 相同。

fork contract：从同一个完整 checkpoint 建立两个独立 mutable copies。checkpoint 至少含 W、O_A/O_B、clock、running action ID/duration/elapsed/progress、reservation、offer/reply session、action/outcome history、next_action_id/next_event_id/next_sequence、ledger frontier与 seals、Monitor summary 与 domain/deadline/duration/reply pins。本域无随机流或在线模型调用。相同 checkpoint 与相同剩余输入分别恢复后，执行轨迹及 settlement ledger hash 必须相同；修改一个 fork 的 W、O、进度或 ledger 不得污染另一个 fork 或真实输入 ledger。两 fork 都不能把 proposal/预演 event 写入真实账本。

## 6. 共同预算与判定标签

拟议工程保护上限：每 case、每搜索实现最多 10,000 首次扩展状态、墙钟 2 秒；同机单线程，记录硬件、解释器/编译器与优化配置，不预定实现语言。一次 expansion 定义为某状态首次从 frontier 取出并枚举其合法 action；重复 closed-state 不重复计数，起始状态计一次。以单调时钟计时，含初始化、搜索与终止判定。9 个时钟边界本身不能证明该 cap 足以穷尽。纸面保守 boundary-prefix/history-tree 上界为 `U=2·Σ(ℓ=0..8)Σ(k=0..min(6,ℓ)) C(ℓ,k)·6!/(6−k)!=299,250`：6 类非 idle 成功动作（offer、reply、exchange、return_tool、unlock、take）各至多一次，reply 的 accept/decline 两个 grounding 由系数 2 保守计入；ℓ 选分钟位置，k 选非 idle 位置并排列动作类。目标 case pins 固定，invalid requests 不是合法边且不分支时间；因果前提、固定 reply 与长 unlock 的 forced no_control continuation 只会减少可行前缀。该数是边界前缀的粗上界，不是 exact reachable-state count；保留完整追加式 raw ledger 时，不得据此把历史折叠成未经证明的 canonical state。未来若报告 exact reachable count，须在获准实现后逐项计数并说明去重 key 保留了所有影响授权、同意、资源、未来 effect 与 witness 的字段。10,000/2秒是否足够仍未知；独立 oracle 受同一预算，耗尽预算时记 `solve_status=BUDGET`、`complete=false`、`exhausted=false` 并注明终止原因，不声称完整。planner/oracle 分别报告 expansions、墙钟、frontier/visited 和终止原因。

结果 schema 必须分开求解状态与 fixture 测试判定：`search_result` / `oracle_result` 至少含 `solve_status`、`termination_reason`、`complete`、`exhausted`、expansions 与预算；`fixture_test_result` 仅为 `PASS`/`FAIL`，并记录被检查的预期标签。C01 起点扩展后按 cap 停止，应为 oracle `solve_status=BUDGET`、`complete=false`、`exhausted=false`，planner 也报告 `BUDGET`，不是 `UNREACHABLE`；正确报告预算耗尽可使该诊断 fixture 的 test result 为 `PASS`，不表示搜索求解成功或正式正确性通过。`UNSOLVED` 是求解状态，不是 fixture failure 的同义词；正式正确性仍要求完整 oracle。

触发任一上限但未穷尽：planner 与 oracle 的 `solve_status=BUDGET`、`complete=false`、`exhausted=false`，`termination_reason` 标明 `STATE_CAP` 或 `WALL_TIMEOUT`；不是不可达。不得加预算重跑直到成功；预算改动需新协议版本与独审。除诊断 fixture 明确检查“正确报告预算耗尽”外，未穷尽搜索的 fixture test 为 FAIL / gate NOT_PASS。deadline fixture pin T 会把目标窗口改成 [2,T]，仍右闭；reply/duration/deadline pins 均进入 checkpoint 与搜索配置。成功合法路径可报告 POSSIBLE_IN_WORLD。固定 B pin 仅报告该脚本的 TRACE_SATISFIED/TRACE_VIOLATED/TRACE_INDETERMINATE。只有完整穷尽无 witness 才能报有限域不可达。结论限于本协议域。

## 7. Fixture / acceptance matrix

每例由基准初态、唯一 fixture delta、reply pin、deadline 与 expected 组成，不暗加 operator。SEARCH=独立 oracle 全域遍历；h0=planner 完整无启发式搜索；EXEC=独立 executor；MON=sealed settlement projection。

| Case | Fixture delta / reply | SEARCH / h0 | EXEC | MON witness / verdict |
|---|---|---|---|---|
| E0-P01 正例 | 基准；ACCEPT | 可达；5步 @t7，长度与 oracle 一致 | 所有 action 成功，交易原子 | t2 PENDING；真实 event @t7 SATISFIED，附 ID/sequence |
| E0-N01 拒绝 | D_pin(DECLINE) | 穷尽后该 pin 子域有限域不可达；D_joint 仍可经 ACCEPT 可达 | reply 不移动物品；不得交换 | t4 PENDING；条件 trace 完整封口 t10 无 event 才 VIOLATED |
| E0-B01 刚好够 | deadline=7；ACCEPT | 恰好 t7 可达 | 五步如 P01 | 包含 t7 event，SATISFIED |
| E0-B02 不足 | deadline=6；ACCEPT | 穷尽后该期限不可达 | 不得提前 take/缩时 | seal@6 完整无 event→该 fixture deadline VIOLATED |
| E0-B03 端点 | 固定 t5 checkpoint（由 t2→t5 三次 idle 得到）；两个合法后缀：P01 五步，或 idle/no_control 至 t10 | 成功 suffix 最短 5 actions/5 min；成功 total trace 为 8 actions/8 min，不称全域最短 | 正例先结算 take@10 event，再 seal；负例不 take、不回滚，idle 推进至 t10 | 正例 event@10 SATISFIED；负例完整 seal@10 且无 witness→VIOLATED |
| E0-H01 历史不可逆 | 保留 destroy/tombstone；尝试 key0 unlock/清除 | key0 路径不可达；无清除 action | 请求拒绝，无复活 | destroy 仍在；目标独立按 event/deadline 判 |
| E0-N02 key1 tombstone | 保留 key0 前缀，追加 key1 tombstone：holder=none、intact=false、destroyed=true；B 的初始 O 获知该自有物品失效，A 仍未知备用；B pin=DECLINE | D_joint 与 D_pin(DECLINE) 穷尽后均不可达；不存在替代钥匙 | ACCEPT 不满足“持有完整可用钥匙”的 reply precondition | 截止前 PENDING；完整 seal@10 无 witness→VIOLATED；ACCEPT pin 在此 fixture 不适用，不伪造披露 |
| E0-H02 state/event | ledger 初始 holder=A、O_A/O_B 同场合法获知该持有状态、无 acquired event；无动作可放回 ARCHIVE | 完整穷尽后不可达 event goal | 不存在合法 take settlement | t10 状态对照 AT(holds(A,ledger),10)=SATISFIED；事件目标在完整封口后 VIOLATED |
| E0-X01 mismatch | 注入 planner mutation：非法 offer ActionIntent 显式绑定 key1；或合法通用 offer 预测提前披露 key1；或 unlock 预测直接产生 ledger | binding validation 与 prediction check 分别检查；不要求 mutant search verdict 匹配 oracle | 非法 binding dispatch 前诊断；合法 offer 与 unlock 先真实结算，再比对实际 ΔO/ΔW 并报告相应 mismatch | 不出现伪造 acquire witness；逐项检出变异则 fixture test PASS |
| E0-X02 原子失败 | 由 t4、offer 已 ACCEPTED 的合法 checkpoint fork；仅在测试 fork 注入 A payment absent，再 submit exchange | 不把注入当搜索分支/玩家扰动 | 交易校验拒绝；B 保持 key1，无半交换或扣款 | 无 loan_exchanged；真实输入 checkpoint/ledger 不受污染 |
| E0-P02 长动作进度 | domain pin: unlock duration=3；t5 start，t6 boundary elapsed=1 | 扩展状态包含同一 running action 与 reservation | 同 running_id、key1/archive reservation 延续 t6→t8，elapsed 1→2→3；take t8→t9 | event@t9 SATISFIED；没有 restart/start 伪 event |
| E0-U01 unknown | 无目标 witness 的 prefix；仅在测试 evidence copy 移除相关 past coverage seal，原始真实 ledger 不变 | search 不填补证据 | 已执行事实不改 | 有未来时段但相关 past gap→INDETERMINATE；伪造 event/version mismatch→contract error |
| E0-C01 budget | 从无目标 witness 的初态，测试专用扩展 cap=1；起始状态不是 goal | 首次扩展起点后 frontier 未穷尽→oracle solve_status=BUDGET、complete=false；planner solve_status=BUDGET；两者均非不可达 | 不执行不完整 proposal | 正确报告预算耗尽使 fixture_test_result=PASS；正式搜索正确性仍 NOT_PASS，Monitor 只按真实 trace 判 |
| E0-F01 fork isolation | 从同一完整 checkpoint 还原两个独立 fork，分别续跑相同剩余输入，再只改 fork-1 的 W/O/progress/ledger | 两 fork 的未改运行应同 verdict/trace hash | 变化只在 fork-1；fork-2 与真实输入 ledger 不污染 | 两份 settled projection 独立；proposal/预演事件不得写真实 ledger |

E0-P02 保持同一闭域，仅把本 fixture 的 unlock duration pin 从基准 1 改为 3 分钟；这是显式执行参数变化，不是新 operator。t5 启动的 running_action 在 t6 boundary 后保留同 ID、reservation 与 elapsed=1，继续到 t8 完成，随后 take 在 t9 产生 witness。duration pin 属于 checkpoint/state key；不得通过重开 action 或重占资源伪造 progress。

## 8. 固定答复测试与待独审项

固定答复只有 BReplyPin∈{ACCEPT,DECLINE}。同 checkpoint/pin 重复必须得到相同答复、合法轨迹、event 顺序语义与 Monitor verdict；两个 pin 应可区分。不采样、不统计概率、不调策略参数、不声称自主性。pin 不能绕过 offer、B 的明确接受或 executor 校验。

独审选择：固定 B reply pin 是否足够明确；return_tool 是否保留在该有限动作域；10,000 expansions/2秒上限是否合适；fork 是否满足完整 checkpoint 独立性。它们分别决定允许响应/动作范围、工程保护 cap 与隔离验收边界，当前材料不足以替用户选择，故保留独审。未决时协议保持 DRAFT，不授权实现或运行。

未来获准实现时，每次运行的只读输入清单和输出记录至少包括 protocol/domain revision、代码 revision、fixture ID 与初态 hash、deadline/reply/duration pins、planner/oracle/executor 标识、共同预算及 expansions/墙钟/visited、终止标签、action/outcome trace、settlement event IDs/sequences、coverage seals、Monitor verdict/witness/reason、错误和完整日志。拟用唯一目录 runs/e0_keyledger_v0/<UTC>_<case>_<run-id>/；创建前检查不存在，禁止覆盖旧运行。此为协议要求，本轮不创建目录或运行产物。

## 9. 通过、停止与外推边界

协议独审通过只说明定义清晰，可由用户另行决定是否授权实现。获授权后的 E0 请求独立执行复核，须同时满足：各 fixture 与表列预期一致；X01 prediction check 能检出注入错误；未变异、完整求解的搜索 fixture 中 planner 与 oracle 的 verdict/最早完成时间/最短模拟时长一致；成功轨迹可重放且逐项匹配 executor events；Monitor 端点/seal/unknown 反例正确；预算标签正确；P02 保持 ID/reservation/elapsed；完整 fork isolation 通过；无未解释 mismatch。C01 的 fixture test 因正确报告未求解而 PASS，但搜索求解状态仍为 BUDGET，正式搜索正确性仍 NOT_PASS；正式搜索 fixture 若 oracle 未完整求解，仍不得通过其可达性验收。

任一 planner-oracle 差异、表外 effect、答复前 A 获知 key1、把 B 同意塞进 offer effect、非原子交易、历史/tombstone 回滚、state 冒充 event、未封口即报 VIOLATED、预算耗尽报无解、progress/reservation 重置、或 event/witness 不一致，立即停止该例并保留证据。不得改目标、加算子、放宽权限或抬预算把失败改成成功；需新版本独审。

E0 只可能提供人工有限域的 joint existential path 与固定答复条件 trace 正确性证据。没有实验结果前不得写成已通过；不得外推至独立角色策略、信息不对称行为效果、玩家扰动、GOAP/HTN/repair 比较、作者劳动、开放域或体验效用。
