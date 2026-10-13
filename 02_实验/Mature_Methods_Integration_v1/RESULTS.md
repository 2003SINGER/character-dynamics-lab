# Mature-Methods Integration v1 — bounded native evidence

当前状态：**DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**（2026-10-13；未 CLOSED）。本页新增的 Ongoing Station 结果见下方“2026-10-13 Ongoing Station”章节；此前 2026-10-12 的成熟装配结果仍按历史状态保存。原 S1–S4 与 S2 权限编辑拒绝均为历史结果，不因本次增量而改写。本次结果不构成完整系统通过、性能优势、研究新颖性或机制有效性证据；不自动进入新阶段。

> **历史分隔：** 原 S1–S4 内容及 2026-10-12 成熟装配章节维持其原始结果和边界，不应用作本次 Ongoing Station 增量的当前状态。本次新增证据唯一见本文末尾“2026-10-13 Ongoing Station”。

## 范围与可复核证据

固定套件 SHA-256：`952ddb923d12b106628dca7b0cb13829659daf0aae25040b6ad630ce0df5554b`；基线提交 `47d3ce7e445747c153c9ab4c5d3f34e2ebc12495`。四个 case 共八个唯一原生场景，均运行 24 分钟，配对使用同一 seed/preset/horizon 及原生 P5 Director 对照；没有额外 `observe_actor` 采样。每场景均有独立数据库读回。逐文件索引、哈希与保留失败尝试的原始证据包见[索引](public_evidence/index.json)、[证据摘要](public_evidence/summary.md)及[完整证据包](public_evidence/mature-methods-s1-s4-evidence.tar.gz)。原始成员位于压缩包内的 `02_实验/Mature_Methods_Integration_v1/runs/<run-id>/...`；仓库忽略的本地 `runs/` 不作为公开链接。r2 证据包包含 1,701 个索引文件、压缩前 579,810,974 字节；包含同一 Evennia DB/端口重载的原始 stop/start 日志。归档 SHA-256 为 `a63a01aa56752cba61cfd485d8353eb7af4edc29dc2dbd488f8a60072178f7ea`；1701 个成员均按索引核验，不公开私有对话或数据集。

| Case | 原生结果 | GTP 高层根调用（方法臂） | P5 快照规划调用（方法臂） | 结论边界 |
|---|---|---:|---:|---|
| S1 结果目标 / 拒绝分支 | 最低正例；四项硬约束 SAT | 5 次有效调用；另有 1 次因 runner 解释器导入失败而未完成的尝试 | 26 次有效调用；另有 1 次失败尝试 | 闭环和同场景续跑有证据；两臂墙钟不可比较 |
| S2 编辑 / 重选 | 两臂均完成，四项硬约束 SAT | 5 | 25 | 原生权限编辑不支持；重选未测试 |
| S3 玩家取放 / 恢复 / 拒绝 | 两臂均完成，四项硬约束 SAT | 7 | 25 | 观察到原生可用性变化与独立执行 |
| S4 无权限机会 | 两臂均完成，四项硬约束 VIOLATED | 2 | 25 | 安全负例；不证明世界不可达 |

上表只计外部协调器调用，不是全系统规划次数或性能排名；原生 P5 每个 arm 另有 24 次 Director 规划记录，即使关闭其干预执行，也仍会调用纯规划函数。NPC 局部规划费用未汇总进此表。成本文件将 GTP 根规划、P5 纯快照规划、sealed advance 分开记录；分段墙钟仅作本次描述性观测。S1 旧基线使用系统 Python，而方法臂最终续跑使用项目 venv，且方法臂有 runner 失败/恢复，因此不作跨臂或总体性能比较。套件和各 arm 的源身份、调用成本及逐分钟记录均在证据索引/压缩包内。

## 实际数据流与观察

实际调用顺序是：`get_trace` 的封存原生事实与 AuthorBundle → `snapshot_from_native` 验证身份/前沿并调用原 P5 `planning.plan()` 排序机会 → `plan_high_level` 在独立 GTPyhop 域中分解所选支持方法和真实事件等待义务 → runner 验证 `candidate_guard`，通过原 `step_world` 提交授权操作 → 原 NPC callback 的局部 GTPyhop/Ensemble 与 Evennia 原生结算 → TypedIR 的真实 witness → `advance_from_sealed` 判断哪些未完成依赖需要重新考虑。不是 GTPyhop 先独立优化路线，再让 P5 确认。普通移动只更新执行遥测；高层根调用不是每分钟重造剧情。

高层方法域与 NPC 自身既有 GTP/Ensemble/Evennia 执行链分开。高层只读授权 planning view；角色通过原有 callback 获得自己的 O。P5 是有限机会规划器，不是完整 DODM；NPC helper 是原生 P5 服务中的只读规划视图。高层方法及元数据/控制原语使用了 8 个注册方法、4 个元数据/控制 primitive；实际机会排序仍由原 P5 规划器完成，不能据此称为独立于 P5 的通用路线优化。

- **S1：真实闭环正例。** 旧 Director 臂在第 24 分钟完成；第 1 分钟侧路支持结算，A/B 于第 16 分钟交付，第 17 分钟原生拒绝回应，四项硬约束均满足。方法臂最初因 runner 误用未安装 GTPyhop 的解释器失败；随后同一未推进初态在既有项目 venv 下运行，并在第 17 分钟拒绝后从同一场景/检查点续至第 24 分钟。首次故障、runner 源码和哈希、续跑身份均保留；未重置场景或在 continuation 中创建新场景。S1 方法臂计 5 次有效 GTP 根规划（第 0、1、16、17、24 分钟）及 26 次有效 P5 快照调用（前段 18、续段 8）；另计一次失败导入尝试，不混入成功调用数。旧控制臂系统 Python 与方法臂续跑 venv 不同，墙钟性能不可比。
- **S2：原生能力边界。** 第 1 分钟拟进行的 CAS 作者编辑被现有 `BundleStore` 以 `PERMISSION_ESCALATION` 拒绝，因为运行时不允许任何权限差异。Bundle 仍为 v1，side 仍合法；没有执行 v2、旧候选失效守卫或 main-route 重选。尽管两臂场景最终都完成且硬约束 SAT，本场景对编辑后重选目标的状态是 `NATIVE_PERMISSION_EDIT_UNSUPPORTED / RESELECTION_NOT_EXERCISED`，不是该目标的 PASS。未改权限规则，也未用替代离线模拟冒充原生验证。
- **S3：原生物资反馈。** 玩家在第 2 分钟 get、第 6 分钟 drop，读回显示 A 的可用性等待后恢复；B 的既有义务保持独立。两臂 A/B 在第 16 分钟交付，第 17 分钟发生拒绝回应；四项硬约束均满足。方法臂在第 0、1、2、6、16、17、24 分钟计 7 个高层根调用。场景使用真实原生操作与回执，没有由等待直接制造完成结果。
- **S4：安全负例。** 无合法机会且无现有通路；两臂 24 分钟内均无机会尝试，四项硬约束均为 VIOLATED。方法臂只在第 0 与 24 分钟调用高层根规划，共 2 次。原生现场终态曾将关闭机会误分类为 `existing_path`/null；随后只用保存的 S4 证据离线重评 terminal projection 并新增回归检查，未重跑原生场景。报告将原始 LIVE 观察与修正后的 OFFLINE 重评分开；这不改变现场轨迹，也不证明更广泛的不可达性。

## 解释、实现边界与剩余工作

两条 S1 runner 故障与同场景续跑均保留：第一次是解释器依赖缺失；第二次是第 17 分钟把合法 `existing_path / NO_OP / candidate=null` 错当成 malformed blocked。修补运行器分类后，只续完第 18–24 分钟，没有重做前缀。S4 terminal 分类修正依据已封存证据离线完成；原始 live 输出仍可审阅。独立数据库读回覆盖八场景。最终 P5 专项测试记录为 58 PASS；此处不据此宣称全 CI 通过，最终 CI 状态未在本结果中核实。旧 E0-H02 预算失败仍属已知旧问题，不通过改预算或断言处理。

新增维护量（含注释/空行，不是算法复杂度）：高层应用包 857 行 Python，runner/审计/发布/校验工具 1,283 行，测试 650 行；原生 `service.py` 仅抽取同源只读状态构造并公开视图（54 行新增、12 行删除）。高层知识工程是 8 个注册 task methods（其中 4 个支持方法）与 4 个仅写控制记录的 primitive；不是新增 4 种游戏能力。原 P3/P4、P5 世界/机会规划/BundleStore、Sabre/GTPyhop 库、C++ 和 E0 均未改。实验运行源哈希与后续离线 terminal-label 修补源哈希分开保存，不把后者冒充现场版本。

本机复核：P5 58 项、runner/证据校验 13 项、P3 53 项、旧 Sabre 输出解析 5 项及 System Baseline 25 项通过；公开归档 1,701 个成员及本地原件逐一核验为 VERIFIED。仓库健康检查仅有既有本地依赖体积/历史重复材料告警，无失败；这些检查不代表语义编辑或科研主张通过。

本证据只支持有限原生工作流中的方法装配和反馈行为。它不证明完整在线规划系统、通用并行/异步调度、心理机制、文学/人类可信度、训练收益、研究新颖性或相较基线的性能提升。S2 权限编辑与编辑后重选仍是明确缺口；高层原语仍限于本 P5 方法域。不得据本轮自动扩展到 LLM、DODM、Mimesis、新搜索器或新框架。完成授权场景后停止，待独立审阅与用户决定。

## 2026-10-12 定向外部审阅已收到

审阅认可有界装配与真实反馈，不通过全部能力验收，也未证明高层独立方法选择或相对原 P5 的增益；本页的 PARTIAL 和 S2 未测试结论保持不变。审阅后的能力缺口与下一候选只维护于[未决页](../../00_研究设计/未决问题与机制候选.md#2026-10-12-成熟装配复核与下一能力入口)，执行指针见 [TODO](../../00_研究设计/TODO.md)。此次仅核对源码和沉淀讨论，未重跑旧场景、改写数据或新增方法结果；原文私有保存。

## 2026-10-12 Story-process 增量：真实便条回应后归档

### 范围与结论

本次在同一 P5 世界实现并验收一个限定目标：原生 A→B 便条取得真实回应后，同一实体便条须在绝对期限内进入注册档案地点。规划器提出角色可接受或拒绝的任务请求；角色、物理世界和现有时钟仍是任务接受、移动、交接与归档的事实来源。方法搜索与事件驱动对照共享游戏内容、可见状态、动作权限、反馈、任务授权和 24 分钟物理期限。事件驱动策略也完成了相同目标；结果不支持 GTPyhop 优于该对照。

最终固定审计包括 **14 个代表性条件**（13 个实际原生场景加 1 个 reset 前权限拒绝条件），其中正例目标均满足，四个负控产生预期拒绝或不满足结果。发布归档包含 **16 个唯一实际 scene ID**：上述 13 个代表场景之外，还保留两个 task-refusal 失败 scene 和一个早期 future-edit 成功但遥测缺失的 scene。scene 数、代表性条件数和运行尝试数不是同一个分母；不据此声称所有尝试通过或报告总体成功率。

### 关键运行事实与失败保留

- 接受与拒绝回应的 GTPyhop / event-driven 配对均满足目标。rejected 配对中的拒绝是便条回应内容；该分支的实例内容规则预先规定 B 不愿承担归档任务，因此 `file_by_B` 不适用，实际由 A 路线完成。B 的交接任务在该路线中被接受。它不是一次归档任务拒绝事件；方法提案也不作为接收或完成的证据。
- 另两个 `task-refusal` 条件使用本实例 `LOCAL_CHOICE` 角色内容规则：GTPyhop 和 event-driven 均观察到 B 在第 18 分钟实际拒绝归档任务，并转向 A 路线。此前两次 GTPyhop 失败 scene 未能完成真实交接/会合并以 VIOLATED 结束；第三个独立同输入修复 scene 在显式建模同一注册交接地点的会合支持和真实 give 前置后满足目标。失败现场保留。修补是执行器/会合接线，不是改变角色规则或方法搜索。
- accepted 正例和 locked-fragment 正例的续跑均保留。accepted 场景曾在第 18 分钟封存后触发 planner 异常；锁定片段场景曾在第 17 分钟触发 `UnboundLocalError`，当时尚未产生 controller decision。修复后均从原场景继续，封存前缀逐行不变并完成；这些故障不是抹除的重跑。
- future file-actor 编辑的早期 SAT 运行缺少持久遥测。另一个独立同输入运行补足 trace 与 DB 核验：v1 请求失效、v2 选择 A 路线，旧请求未派发，目标满足。无权限条件则在 reset 阶段按预期拒绝，scene 未创建、目标未评估；locked-refusal 负控保留原锁定核心并中止。资源仍由玩家持有的条件下，未绑定新便条且归档目标未满足；期限负例在第 24 分钟为 VIOLATED。

### 证据、成本与边界

逐条件事实和尝试/续跑账本见最终发布副本中的[固定 case table](public_evidence/story-process-v1-20261012T152500Z/case-table.md)（SHA-256：`b2e45cc024beb8d59b361d1ade37c1fb9706d754d2bbe43ee585ce5da2863090`）；机器可核验的[manifest](public_evidence/story-process-v1-20261012T152500Z/audit-manifest.json) SHA-256：`8692a459f478b88dafad91acc3221ed5838b41cef653bda0cd87514d56c7b1e2`。发布证据为[story-process-v1.tar.gz](public_evidence/story-process-v1-20261012T152500Z/story-process-v1.tar.gz)：30 个明确 allowlist 目录、1,354 个归档成员、192,660,283 原始字节；归档 SHA-256：`4d29a96891564921c079db0ab9aa19c6cd011ab79ff0b08de51f711a16be53c4`。仅此最终发布包作为本次引用；较早包是旧表版本。

本次工程内容/代码账如下；行数是所列当前文件的 `wc -l` 规模（含空行/注释），不是新增行差、作者工时或成本下降的估计：

| 维度 | 实际新增/维护内容 | 可核验规模或边界 |
|---|---|---|
| 游戏内容 | `handover_note`、`archive_note` 两种授权任务；接受/拒绝回应后的角色 disposition 规则，含 `LOCAL_CHOICE` | 本实例内容规则；不等于普遍角色心理法则 |
| 方法/策略知识 | 两个独立 GTPyhop 替代方法、等待回应方法；event-driven 的对应候选规则 | 方法各自检查前提并分解；不是新动作能力，也不预设哪一臂占优 |
| 适配与运行工具 | `story_process` model/planning/actor/native 与单条件 runner | 2,615 行当前文件规模；不是纯新增 LOC 或耗时 |
| 契约与回归测试 | 新增 story-process、native adapter 与 case contract tests | 1,076 行当前文件规模；总计上述目标文件 3,691 行 |
| 调试修补类别 | 持久化/TypedIR 边界；模式分支变量初始化；recipient 路由；会合地点与真实交接前置；嵌套 parser 审计 | 修复及离线审计均保留；不能转写为作者劳动减少 |

运行成本账本另分记 controller decisions、原 GTPyhop 实际 method callbacks、仅诊断用途的替代 guard 检查、原生 P4 ledger/角色回执及 sealed minute；墙钟记录排除 service lifecycle，只作描述。源代码在修复和续跑期间发生变化，且对照同样成功，因此不做算法性能排序或总成功率包装。专项复核记录：P5 为 85 项中 84 PASS、1 skip；成熟方法集成 34 项；P3 为 53 项通过。它们是开发验收，不等于整个系统 CLOSED。

此增量仅支持该有限实例的原生行为和失败反馈证据，不证明通用调度、方法优势、研究新颖性、玩家可信度或系统完整性。原 S1–S4 / S2 权限编辑拒绝仍按历史边界解释；当前成熟方法集成总体仍为 **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**，未 CLOSED。

## 2026-10-13 Ongoing Station：原生自主承诺、作者约束与事件基线

### 状态与范围

状态：**DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**，不标为 CLOSED。下述只引用本次 9 个明确 allowlist 目录（8 个原生 scene 运行 + 1 个同 DB service lifecycle 记录）；不改写旧 S1–S4、权限规则或旧 E0 预算。用户已明确授权公开本次限定证据，原始对话/private attachment 未收入发布包。能力结论来自本轮实际运行；远端版本与 CI 以 `webgpt-sync` 和 GitHub Actions 的实际读回为准，不预先宣称全仓 CI 通过。

固定 case suite SHA-256 为 `105377a780e719cd4c8655ddc954bbb96c5c7ffbd47092f787f3f6ec65c929c6`；作者包 SHA-256 为 `b008047ca1fcd956f69f0d95ef491c0303cb3035d87e0296c771b7458f491e50`。固定物理期限 24 分钟，配对场景使用相同 initial preset、seed、资源和动作权限；GT 与 event-driven 唯一实验控制差异是 planner strategy。最终代表条件是 T1 无作者、T2/T5/T7 同场混合约束的 GT/event 配对、T4 有真实角色承诺的作者 offer 与 future edit、T6 玩家持有真实物资的负例。另保留一条更早 T1 probe 和两条作者 native adapter 修复前失败 scene；它们不是额外通过条件。

### T1–T8 覆盖与实际轨迹

| 项 | 固定要求与本次可验结果 | 场景/证据状态 |
|---|---|---|
| T1 | `author:null` 时 A、B 均从自己的本地 P3 view 选择 self-goal；每角色 23 个 station decisions，11 个 self commitments，其中 10 个由独立 DB native receipt settle，之后又选择并 dispatch/pending 一个不同 self-goal。这里的 10 是已结算承诺数，不是 10 条物理 receipt。 | 最终 T1 PASS，scene `20261013032814-4ee796`；`runs/story-ongoing-station-t1-no-author-autonomy-20261013T032814Z-9059b4/`。更早 probe scene `20261013022923-d8fca2` 保留但不计代表条件。 |
| T2 | 作者只约束同一真实 note 的按期归档结果，不指定 NPC 必须接受。通过 sealed request/response 绑定精确 note；结果方法与锁定片段分开绑定，后续 edit 只改未来 filer。 | 修复后 GT scene `20261013033249-9c2415`，offline audit v3 PASS；event scene `20261013033640-1dcd15`，PASS。run dirs 分别为 `story-ongoing-station-t2-t7-author-gtpyhop-20261013T033249Z-2f5e13`、`story-ongoing-station-t2-t7-author-event-driven-20261013T033640Z-195726`。 |
| T3 | 给/交接实际接受 P3/Evennia 可见性校验与物理反馈。GT 场景中 B 在 m7 尝试 locked handover 时 A 尚不可见，故出现真实 `WORLD_VALIDATION_REJECTED` settlement 记录；不是成功 receipt，也没有让 A 停止自己的 route。A 完成路线后 B 于 m8 成功 give，A 于 m9 archive；真实 note/locked 目标均 SAT。 | 与 T2/T5/T7 共用 GT scene `20261013033249-9c2415`，Event scene `20261013033640-1dcd15` 也按同一玩法得到 SAT。准确失败尝试可从两场的 `final-trace.json`、分钟增量和 scoped DB 回放；不可把失败尝试删成“直接成功”。 |
| T4 | 作者 offer 到达时，B 的真实 `routine_route` 承诺仍在进行；m6 `AUTHOR_OFFER_DEFERRED` 引用其 live commitment 和路线 receipt `p3:7525:0:13`。m7 handover 有实际失败执行记录 `p3:7525:0:19`，`settled=false`、`dispatch_succeeded=false`、`WORLD_VALIDATION_REJECTED`（A 不可见），所以结论是“无成功物理 give”，不是“没有 receipt”。m8 合法 CAS 将 filer A 改 B，edit response 的 `invalidated_offer_ids` 指向旧请求；旧未执行 handover suffix 记为 `CANCELLED_STALE`。此前 SELF 路线前缀留存；B 于 m10 以 `p3:7525:0:28` 归档。没有脚本化拒绝，也没有声称打断已在执行中的世界动作。 | 原始 `summary.json` 是 NOT_CERTIFIED（客户端旧断言错误要求 m7 movement、并读取空的汇总 stale ID）；用保存的 native response/history/receipt 与同一 DB 离线重审为 v3 PASS，15/15 条件。scene `20261013033716-ea2579`；`story-ongoing-station-t4-live-actor-deferral-20261013T033716Z-806402/`。summary 与 v2 审计原样保留。 |
| T5 | 同一个作者 envelope 同时含结果 constraint 与独立 locked core：v1 结果约束 filer=B，使 `file_by_B` 可行，但锁片 B handover→A archive 要求 `return_then_file_by_A`，二者不兼容，因此 controller 记录冲突且不发布 actor task；m6 CAS 只把 filer 改 A，deadline=24、grant、locked sequence/hash 不变。v2 结果搜索与 lock intersection 兼容，真实交接和归档 receipts 依次通过。 | 同 T2 配对两 scene。GT final audit v3 16/16 PASS；Event 16/16 PASS。T5 的 v1 “冲突 projection superseded”不夸大成取消已发布/已运行的 NPC task；当时没有这种 offer。 |
| T6 | 玩家在 m1 通过注册 `get courier_supply` 真正拿走物资并持有至 m24。A 的 delivery target 仍配置但没有被假称已接受/中断的 commitment；A 明确因 item 不可用未执行目标。B 仍用原生 receipt 完成独立 delivery 和两段 route。此为 NPC callback 前发生的初始资源持有负例，不是中途扰动。 | PASS，scene `20261013033010-0b39f5`；`story-ongoing-station-t6-player-holds-courier-supply-20261013T033010Z-af18a2/`。player command receipt 与最终 item holder 由 scoped DB 核验。 |
| T7 | “认真 event”对照共用同一 profile、result/lock guards、授权与真实反馈；只改 strategy。两对 `case-input.json` 去掉 strategy 后 reset inputs 与 interventions 相同，按角色/minute/operator/status 规范化后的全部 native execution 序列 diff=0。 | GT 与 Event 都达到同一目标；本次未发现行为增量，不支持 GT 优于 event-driven。两臂 native code controller/actor 相同，但完整 source-set hash 因离线 audit/test 文件变化而不同，故也不包装成字节级同源码对照。 |
| T8 | 每场保留完整 final trace、每分钟增量、scene identity、独立 scoped DB JSON、源码快照和可读回放。可读回放是叙事索引，不替代 ledger/DB；对不同证据流不伪造跨流总序。 | 最终发布目录邻接的 `readable_replays/` 有 7 个 byte-identical Markdown 副本及 hash index；早期 T1 probe 的同名文件实际是 JSON-encoded malformed Markdown，原件仍在包内但不伪装成可读回放，index 明确记录排除原因。 |

两个修复前 matched-arm scene 都实际运行了 SOCIAL_REQUEST/SOCIAL_RESPONSE；它们的失败原因不是“没有世界便条”，而是 adapter 用不存在的 receipt `item_id` 绑定 note，加上 `_author_verdicts` 的局部 `service` import NameError，致 controller/TypedIR 读回错误。scene `20261013032840-334a92`（GT）与 `20261013032922-1ed505`（Event）和原 `NOT_CERTIFIED` summaries 均保留，不以成功重跑覆盖。T1/T6 与最终 episode 的原 `summary.json` 不改写；GT/T4 的审计纠正写在新的 v2/v3 offline audit sidecar。

### 原生与规划成本边界

配对 trace 各有 **40 次 controller evaluation**：20 次 `result_only`、20 次 `locked_fragment`。只有 GT arm 的 20 次 result-only evaluation 调用高层 GTPyhop；其 `attempted_methods` 记录 60 个候选尝试，search trace 共 81 行。Event arm 的 20 次 result-only 是 event policy evaluation；锁定分支不调用高层 GTPyhop，全场高层 search trace 为 0。81/0 是搜索 trace 行数，不是访问过的独立状态数或运行时间。两场共同有 46 次 actor-local P3 GTPyhop planner 调用、合计 186 次 `method_action_visits`；这些执行辅助开销两臂相同。每场 ledger 另有 24 个 P5 director decisions、48 个 NPC callbacks 和 24 个时间推进事件；它们是共享游戏运行成本，不应混作高层搜索调用。墙钟配对时间未采集/不作比较。

独立 actor DB 的两臂各有 45 条 settled native P3 primitive receipts：39 `move`、3 `drop`、2 `get`、1 成功 `give`。这是输出动作回执数，不是规划节点或总动作尝试数；例如失败的 m7 give 单独保留在 execution-settlement log，未计入成功 receipts。

| 层 | 本次新写 / 本次复用 | 成本或限制 |
|---|---|---|
| 游戏内容 | 新 author bundle bindings、结果目标、锁片序列、A/B 本地 self-goals 与路线/资源约束；没有预置首次拒绝规则或脚本化 NPC 动作。 | 证据只覆盖固定内容、seed 与 24 分钟期限。 |
| 高层方法知识 | 新 `file_by_B`、`return_then_file_by_A` 与等待真实回应的方法候选；新 locked/result intersection 与 controller offer mapping。 | GT 搜索与 event candidate policy 最终选择一致；未观测到方法优势。 |
| Actor 任务适配 | 新 station-specific `deliver_supply`、`routine_route`、`archive_note`、`handover_note` commitments 与本地 arbitration/history。 | 复用 P3 GTPyhop 2.0.2、`observe_actor`、known-exit route helper、move/get/drop dispatcher；`give` 仍受 native recipient visibility 验证。 |
| Evidence/audit | 新 actor/callback/TypedIR receipt binding、未来 edit CAS、五份 offline audit v3 与 replay 索引。 | 两个旧 adapter failure 保留；原 GT/T4 `NOT_CERTIFIED` 原文保留并由 hash-bound offline audit 复核，不伪装成当时runner summary PASS。 |

### 适配债、成本全账与研究边界

本实现的内容和方法边界仍然很窄：固定的 author goal、`file_by_B` / `return_then_file_by_A` 两种归档方法，以及基于本地 commitment/history 的优先级，都是本项目为该 profile 新写的领域内容；它们不是通用目标生成器，也不是完整 BDI 架构。跨约束锁片适配器只验证已注册的 constraint、grant、hash、sequence index、真实前缀 receipt 与当前可行 suffix；它不是通用 HTN/STN 或任意过程组合器。交接 rendezvous 按 sealed view 中的实际位置绑定；当前没有通用资源规划器、通用时间约束网络或跨场景路径协商。

运行中的 station/commitment 状态由现有持久对象和可读回历史承载，但本实验没有验证进程崩溃后的恢复、重复投递幂等性或跨版本迁移，不能称作 crash recovery。玩家资源命令与 Evennia 校验是真实物理边界；高层/角色方法仍只提出一个 primitive，不能越过 dispatcher 或替代世界校验。T4 的 m7 give 是有 settlement 记录的失败尝试，而不是成功 receipt；T5 v1 也只是 projection conflict，没有已发布的 actor task 可供取消。

成本应拆成运行成本、实现内容和人类劳动，不能相互换算。上文的 controller evaluation、GTP callback/search trace、actor-local P3 calls/visits、native settled receipts、NPC callbacks、时间推进和墙钟缺测，分别是本次运行可计量项；它们不是开发工时。README 中的模块行数只是当前文件 footprint，不等于新增 LOC、建模时间或效率收益。内容建模、方法设计、适配、调试、证据整理及作者劳动的小时数没有可靠记录，故记为**未知**，不从代码行数推断节省或总成本。实际修复/诊断类别包括 note producer 字段与局部 import、edit projection reconcile、locked-prefix suffix continuation、audit 对真实嵌套 trace shape 的解析；这些是开发期间的代码/审计问题，不应都计作原生场景失败。两条 pre-fix author scenes 是真实保留的失败运行；测试夹具修正和离线 parser 回归不是 live failure。

后续仅保留研究候选，不启动新阶段：其一，既有目标历史与 commitment 如何影响新目标选择；其二，多个过程并存、作者只给部分约束时如何协调，以及对作者创作劳动有什么影响。LLM 可能的两个插入点仍是作者文本到受限 binding、以及角色本地观察/历史到候选目标解释；两者都需要单独设计与评估，当前没有自动接入或运行。

数据流如下；controller 只规划/发布可拒绝的 future offer，最终完成来自本地角色回调、原 dispatcher 和物理 receipt：

```text
AuthorBundle + registered bindings
  -> sealed-note/request binding + controller method/lock evaluation
  -> eligible future offer / future-version CAS edit
  -> actor-local P3 observe_actor + commitment arbitration + shared HTN intent
  -> existing pending-action dispatcher + Evennia validation
  -> settled native receipt -> actor history / TypedIR verdict / next sealed decision

author:null -> SELF offers -> actor-local commitment/history -> same dispatcher/receipt path
```

### 源身份、审计与发布

每场存自己的 working-tree byte-set SHA，不能把所有实验简化成一个 Git HEAD：最终 T1、T6 和两条 adapter-fix 前失败场的 file-set hash 为 `43941d01c13d43c70c4aeaddbb1504235dc3a3895eb165613555d99dc6561b23`；修复后的 GT scene 为 `6275afc73cd642bd834c8efb7dc0abd7378e34f21aa89d8d6323e6053028d3da`；Event 与 T4 为 `85fb9d752350a62c774900521614c19aaf1bd7d31602afd9d26cd421e07aee84`。GT→Event source-set 差异仅 `ongoing_station/audit.py` 与对应 runner test；runtime controller/actor hash相同。所有改过的文件 bytes 都在每场 `source-snapshot/` 中。

最终统一复核使用 `audit.py` SHA-256 `9fe219389efa210929312ee5d8ccd926eb7b1812274eb6c40a361b05ce04b480`（40,612 bytes），完整字节载于 GT run 的 `audit-source-v3.py`。5 个 `offline-audit-recheck-v3.json` 分别绑定实际 trace SHA、原始 DB readback SHA、case input SHA、scene identity SHA、source file-set SHA；v3 sidecar 自身哈希为：T1 `c5ac3d8f1338b1ce0ef42baa8e150e44f034abfb1222c8a23ec0ab38c7b22e73`，GT `335a70605dec1dfd97248f6e5d1f9ab6f55273b1c4f18e24a0886f7ed37ac4a0`，Event `a84e577e9e79eeb447654950b3a6445a88060660351095b818906e92ecb4ecef`，T4 `c15b0906823bd48a0fc283363d010b0dcf2c723f5af95819885ea354f6fe964d`，T6 `bdaa7e1997f011231c197ca60f229bb21446d32a3408081a99a7b5711103fee3`。修复前故障和先前 v2 sidecar 不覆盖。

最终包目录为 `public_evidence/story-process-v1-20261013T040000Z/`；其中 `story-process-v1.tar.gz` 有 568 个逐成员校验文件、压缩前 141,997,708 bytes、压缩后 6,175,869 bytes，归档 SHA-256 `69246b239667199cf89b206a528862dbcde9fa3eb241e8d4ad04cafd00e17fba`。既有 publisher 专项安全测试 5/5 通过，最终 tar 按 index 对 568 个原件逐项校验为 VERIFIED。目录的 `index.json` 是逐文件 hash 成员索引，`publication-scope.md` 特别澄清其 8 个原始 DB payload 是用户许可且敏感扫描通过的**scene-scoped simulated JSON**，不含全账户/unscoped DB、数据库 binary、凭证或 private 原文；其存在不应与 publisher 的通用 “raw DB exports” exclusion label 混读。相邻 `readable_replays/` 有 7 个最终/诊断 Markdown 原文逐字节副本，其来源与 SHA 见 `readable_replay_index.json`（SHA-256 `b78e0533cb3d4c81f8c1033e4f7383077c1606a8494c7364f9aea73822fbe868`）。此前 03:45 本机包缺 v3 source carrier，仅作被 supersede 的历史本地包，不作最终链接。

审阅入口：[完整原始证据包](public_evidence/story-process-v1-20261013T040000Z/story-process-v1.tar.gz) · [逐文件索引](public_evidence/story-process-v1-20261013T040000Z/index.json) · [回放索引](public_evidence/story-process-v1-20261013T040000Z/readable_replay_index.json) · [直接阅读 T4 过程](public_evidence/story-process-v1-20261013T040000Z/readable_replays/story-ongoing-station-t4-live-actor-deferral-20261013T033716Z-806402.md)。

Parent 最终复核：实际 trace 与独立 DB 中的 SELF 任务/后续活动、m6 延后、m8 旧承诺撤销、m10 原生归档，以及混合片段 m8 交接/m9 归档均已定向读回；匹配输入和归一执行序列逐项相同。独立重新验证 568 个归档成员、8 份 DB、5 份 v3 审计/源码与 7 份回放副本。最终本机 P5 unittest 运行 139 项：138 PASS、1 skip；P3 53 项与成熟方法工具 34 项通过，不把这些数量相加称为独立语义实验。仓库健康检查退出成功，保留 11 个既有本地依赖体积/历史重复材料告警；旧 E0-H02 预算失败没有调预算或重跑刷绿。

下一步仍只列候选而不自动开新阶段：优先围绕“历史/commitment 怎样影响新目标”和“多个部分作者约束过程如何协调及影响创作劳动”提出可证伪问题；若独立审阅要求，再预注册多 seed、受控可见性/路径变化的同能力复验与墙钟/搜索状态计数。LLM 作者 binding 与 actor-policy 是未来入口而非当前结果。不从这一组固定轨迹推断心理真实性、长期自主性或普遍策略优劣，也不自动扩大权限。
