# Mature-Methods Integration v1 — bounded native evidence

当前工作包：**M1–M5 / E1–E4 有界实施与原生运行已交付；DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**（2026-10-13，未 CLOSED）。新结果只见本文末尾“历史依赖、跨过程方法与未来剧情点”。严格 E1 历史对照未匹配，E2 未观察到工作条件驱动的方法切换；E3 新剧情点与 E4 失败负控有原生证据。完成本包后停止，不追加规则追求全 PASS。此前装配与早期站点结果保留历史状态，不充当新增条件通过的证据。

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

## 2026-10-13 历史依赖、跨过程方法与未来剧情点（M1–M5 / E1–E4）

### 交付与停止点

基线为 `796510ab3b3c0115cca7e71404194dbbcd8ac467`。本包在同一 opt-in 站点增加真实自身活动、作者约束派生输入、局部工作下界及反例审计；没有新引擎、规划器、LLM、心理状态或并行平台。**8 个代表性场景全部封存至第 24 分钟；另保留 1 个第 9 分钟发布失败的实际场景。** 封存完成不等于作者目标全部成功，也不等于四项能力全部通过。每场在同一个权威 Evennia 世界中运行；不同条件各建独立场景，而不是八个条件共用可污染的世界。

| 验收项 | 实际证据 | 判定与限制 |
|---|---|---|
| M1 自身活动 | 两名角色自主配送后，以同任务真实 get/drop 记录生成 `return_stock`，再执行巡路 | 有限 reverse logistics 已运行；不是通用生活、仓储或人格机制 |
| E1 历史对照 | 同作者 offer 下，H1 的 B 在 m10 接受；H2 的 B 以真实未完成 route 延后 | **PARTIAL**：物品、持有者、道路、作者输入对齐，但 NPC 位置与感官未对齐，不能作纯历史因果结论 |
| E2 工作/位置/期限下的方法取舍 | 编辑前 m5–7，两方法合法；工作下界改变预计成本，但 GT 与 event 都持续选择 B 归档 | **PARTIAL**：未观察到由这些条件单独驱动的合法集合或选择变化；新增交接要求导致的方法变化属于 E3，不挪作 E2 成功 |
| E3 真正新增未来剧情点 | m8 CAS 新增同便条 B→A occurrence 与 strict-before-archive；m11 give、m13 archive，三条约束 SAT | **限定通过**：原约束和绝对期限 24 保留；m7 前缀不变，旧未派发 offer 撤销；没有已接受 v1 AUTHOR commitment，不能宣称取消了这样的承诺 |
| E4 失败负控 | 要求交接及交接先于归档的事件对均在 m8 前成立；两臂实际违约，无伪造 give；期限后 SELF 活动继续 | **负控证据已核验，作者目标 VIOLATED**；不是成功剧情，也不是全域不可达证明 |
| M5 等能力对照 | 同输入、角色策略、方法前提、权限、执行接口；仅高层 selector 为原 GTPyhop 或 event-driven | 所有配对的实际结果一致；没有组合优势或速度优势证据 |

### 八场输入与原生事实

固定 seed `20261013`、horizon `24`、`hero_intelligence_30_v0`、Director 关闭、两份独立配送物品。套件入口是 `tools/native_platform_v0/p5/ongoing_station/cases/m5-e1-e4-v1.json`。开发中调整的输入与源码逐场快照，不宣称预注册或单一 Git HEAD 覆盖全部现场字节。

| 条件 | GT 场景 / run 时间后缀 | Event 场景 / run 时间后缀 | 实际结果 |
|---|---|---|---|
| E1 H1 自然配送—回库历史 | `20261013092722-b9b548` / `092722Z-4bed47` | `20261013092948-b5925d` / `092948Z-197ef5` | B m10 接受作者目标，m11 归档；单臂审计仍为 PARTIAL |
| E1 H2 玩家搬运历史 | `20261013092810-ba8c71` / `092810Z-049525` | `20261013093022-c8eb17` / `093022Z-f58514` | B m10 继续自身路线并延期，m11 接受、m12 归档；不是严格匹配对照 |
| E2/E3 归档结果→交接+归档 | `20261013093047-bd940f` / `093047Z-f4bac8` | `20261013093328-9ed286` / `093328Z-2501cf` | m8 v2 UPDATED；B give m11，A archive m13，三项 SAT；E2 未通过强判据 |
| E4 期限 8 交接/order 负控 | `20261013093732-eccd53` / `093732Z-753111` | `20261013094129-825e3b` / `094129Z-ecb7bc` | 交接/order 与归档均 VIOLATED；两角色各有 16 条 m8 后真实 SELF move |

H2 的历史来自现有 P3 `inject_action`，不是 NPC 命令或数据库修改：8 条玩家 move/get/drop 在首次 NPC 回调前把物品移到 Destination；另 6 条在 m6 后将两物品送回 Pickup，**14/14 均有真实 settled command receipt**。它们发生在模拟分钟回调之间、不消耗 NPC 模拟分钟，是本开发场景的外部干预模型，不是人类玩家操作耗时模型。回放与 sidecar 保留其真实 P3 来源；不伪造不存在的 P5 ledger event。

H1 的 m9 封存时，两条巡路已有同 commitment 的完整有序移动收据；存储的 `IN_PROGRESS` 缓存尚未更新，m10 callback 以收据 refresh 后才判 SETTLED。H2 的 m2 巡路因当时局部已知路径不足而暂停，m8 恢复旧路线，m9 又启动新路线。到 m10 行动前，H1 两角色在 Pickup，H2 在 Destination；H1 能看见两个物品，H2 看不见。因此虽同一作者请求下有真实接受/延后差异，**位置与当前感官混杂仍未排除**。过去完整 O、收据数量和记忆时间戳也不被人为删成相同。

E3 GT 的 give 为 `p3:8018:0:31`、archive 为 `p3:8017:0:37`，同一便条 `8027`；event 的对应回执为 `p3:8040:0:31` / `p3:8039:0:37`，同一便条 `8049`。两场绝对 ID 不同，场内实体相同与 `11 < 13` 分别核验；事件 witness 指回对应场景 DB 中的原生收据，不以方法预测作证。编辑保留 archive 起点 5、截止 24，仅新增起点 8、截止 24 的交接 occurrence/order；事后已归档再要求交接的编辑由历史守卫拒绝。

### 实际责任与反馈路径

| Owner | 输入与职责 | 不得替代的事实 |
|---|---|---|
| AuthorBundle / BundleStore | 唯一约束源、版本与未来 CAS；保留期限、权限和已提交历史 | 派生支持目标不是新增作者硬约束 |
| station model/controller | 将注册 occurrence/order 映射成 `required_story_events`，记录源 hash/cid；只读局部工作 primitive 下界 | 下界和 causal support 不保证路线可行或目标发生；未知工作返回 unknown，不暗作零工作 |
| 原 GTPyhop / event selector | 相同方法前提与能力下，分别搜索/按固定顺序选择；diagnostic guard 不参与预选 | GTP 不被 controller 预先喂唯一答案，也不被包装成全局最优或 STN 求解器 |
| NPC callback / 原 P3 HTN | 自己合法观察、历史 refresh、保留/接受/延期、细化一个真实 primitive | controller 不额外调用 `observe_actor` 改写感知；角色接受不是世界完成 |
| Evennia / dispatcher / ledger | 实际移动、取放、交接与验证；append-only 结算 | 预测、任务提案、等待不能写成成功事件 |
| TypedIR / audit | 实际事件窗口、count/order、receipt/DB 对账 | 区分目标 VIOLATED、证据完整性和测试通过；不把 WAIT/预算不足叫不可达 |

### 成本、公平性与已知失败

| 条件（GT / event） | 高层决策行（两臂各） | GT method callbacks / event candidate evaluations | GT trace 事件 | actor HTN 调用 / visits（两臂各） | settled actor receipts（两臂各） |
|---|---:|---:|---:|---:|---:|
| E1 H1 | 16 | 32 / 32 | 64 | 46 / 200 | 46 |
| E1 H2 | 16 | 32 / 32 | 64 | 44 / 172 | 44 |
| E2/E3 | 20 | 40 / 40 | 82 | 46 / 196 | 45 |
| E4 | 20 | 40 / 40 | 80 | 46 / 200 | 46 |

GT callback 与 event candidate check **不是同一计量单位**。GT trace 长度不是搜索节点总数；后者没有暴露，记为未知。Actor 计数只计含实际 `planner.implementation` 的决策；社交消费 callback 与 H2 的 14 条玩家命令另列，不混入 actor HTN 或 actor settled receipt 分母。尚无统一可靠的分段规划墙钟、作者建模/修改/调试工时，均记为未知，不从 LOC 推断节省。配对 runtime 核心逐文件相同；E2/E3 全量快照差异为 audit 与 runner test，E4 另有 runner 字节差异（负控审计接线），不是角色/方法行为变化，不能宣称所有 full manifests identical。

保留失败 `20261013090427-19e3d7`：m9 两名角色已真实执行并封存，随后 archive-only author requirements 中 `required_handover=None` 被 `_task_request` 错误解引用。run 保存 8 条已返回 minute 输出及封存至 9 的失败 trace/DB/服务 traceback；未重做第 9 步，未假称续完。修复 None 分支及真实 compile→derive→planner→offer 接缝回归后，新建上述场景；旧失败字节仍存。

现场 GT E3 初始审计误要求不存在的 v1 AUTHOR commitment 被取消；GT E4 初始审计混淆正例目标与负控证据完整性。**原 summary/audit/回放不覆盖**，保存 hash-bound 离线复核与对应审计源码 carrier；离线修正不改变世界轨迹，也不增加成功场景数。新增适配工作包括 reverse-logistics 任务、注册事件需求/窗口传播、同源投影、真实工作下界、历史编辑守卫、运行/审计工具与正反例测试；两种故事方法和底层算法已存在，不能算成本轮原创。未重开冻结 C++、E0 预算、Sabre 原算法或 Ensemble 规则。

当前结论停在 **PARTIAL**：新增未来剧情点已有完整原生链，但严格历史匹配和由工作/位置/剩余时间驱动的非平凡方法取舍仍未证实。其外部复核已收到，见下节；旧工作包停止，不通过追加规则或重跑补考刷 PASS。下一施工入口另由设计 owner/TODO 维护，不改写本批轨迹。

### 本包验证与公开入口

最终本机 P5 suite 共 161 项：**160 PASS、1 原环境 skip**；P3 53/53，既有成熟装配/发布测试 34/34。这些是回归测试，不等于八套独立科研实验。仓库健康检查退出成功，11 个既有依赖体积/历史原文重复告警保留，未清理无关文件。原 E0-H02 墙钟波动与历史 CI 失败不通过改预算、断言或重跑刷绿处理。

按用户明确批准的本轮范围，发布 8 场代表、1 场真实失败、1 个重载日志 wrapper：共 682 个归档成员、161,561,009 原始字节、7,747,548 压缩字节。归档 SHA-256 `5339a33612fc731fc18641b1dda566656bdadea447e15c8b69a3f52d7f96f245`，逐成员与本地原件核验为 VERIFIED。包括九份 scene-scoped simulated DB JSON、所有原始输入/轨迹/失败/source snapshots、最终离线审计与源码载体；不含私有原文、凭证、数据库 binary 或其他项目。九份 Markdown 回放亦逐字节核验；原始错误标签不覆盖。

入口：[完整本轮证据包](public_evidence/story-process-v1-20261013T094903Z/story-process-v1.tar.gz) · [682 文件索引](public_evidence/story-process-v1-20261013T094903Z/index.json) · [公开范围与最终审计版本](public_evidence/story-process-v1-20261013T094903Z/publication-scope.md) · [直接阅读回放](public_evidence/story-process-v1-20261013T094903Z/readable_replay_index.md)。历史包仍在原位置，只有本链接属于新的 M1–M5 / E1–E4 工作包。

## 2026-10-13 `b039c87` 外部复核与后续入口

用户提供的外部复核认可 E3 的注册剧情点进入方法选择、原生执行和 TypedIR 的有界链，以及 E4 不伪造成功的失败负控；不认可 E1 的独立历史因果效应或 E2 的工作条件驱动取舍。PARTIAL 保持，未 CLOSED，不将复核改写为三项目标全部完成。

复核提出 `return_stock` 内容风险。独立源码核查确认它由自己的 get/drop 回执派生，未找到“配送物送达后应回收”的作者内容契约；过去送达事件不等于持续物资占有。保留旧实现和全部结果，后续若复用须先明确游戏内容，不能把逆向搬运直接称为自然生活。

接下来的候选转向 Character Dynamics System Integration：先补真实活动/共享资源机制，再按实际冲突选择成熟方法，不继续精修同张便条。设计、算法级准入和首条施工候选只见[未决问题末节](../../00_研究设计/未决问题与机制候选.md)，下一动作只见 [TODO](../../00_研究设计/TODO.md)。本次只读核查与文档修改没有新增原生能力、场景或实验结果；新原文私有归档，不沿用上轮限定证据授权公开。

## 2026-10-14 系统工作 episode：最终固定输入复核

本节记录 `system-work-suite.json` 的最终四场，以及此前同一有界开发回合的全部 11 个失败/部分尝试。只包含 scene-scoped simulated DB JSON 与来源快照；服务仍为同一 loopback Evennia/同一数据库。源快照按每场 `identity.json` 记录，不将不同现场快照合并成一个虚构 HEAD。

### 最终四场

| 条件 | Scene / run | 事实结果 | 独立 DB 与回放 |
|---|---|---|---|
| 主场 GT | `20261013163433-17a730` / [GT run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T163433Z-0e5719/) | m1 A 开始 inspection，m3 `p5_station_supply_inspected`；m2 激活 v1，m3 CAS 更新 v2；m6 玩家真实 get tool、m8 drop，B 的 repair 之后才在 m8 开始、m11 以 SELF receipt 完成；m11 发布 A 的 literal locked store offer，m12 因 A 的既有 route commitment 被延期，保留的同一 offer 在 m13 被接受，m15 同一 AUTHOR commitment 的 store receipt 完成。两个 bundle constraints SAT。没有 work-abort receipt；这是工具在工作开始前被拿走并归还，不是运行中断言或部分进度。 | `db-readback.json` SHA-256 `1b160f50df7859f65b610ddab061171afea7ad3a008e08188ca6bcaf4149a84e`；[逐分钟回放](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-main-gtpyhop-20261013T163433Z-0e5719.md) |
| 同输入 event-driven | `20261013163557-71197e` / [event run](runs/story-ongoing-station-system-work-main-event-driven-20261013T163557Z-d96adb/) | 相同活动/干预顺序；m3 inspection、m11 SELF repair、m13 AUTHOR locked store 接受、m15 storage receipt；两项约束及物理审计通过。与 GT 的归一化 role/task/time 序列相同，没有观察到行为增量或优势。 | `db-readback.json` SHA-256 `836614b70659454b2bc102e0762a0a7a001894dd43bef896dadd374eb1823dd8`；[逐分钟回放](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-main-event-driven-20261013T163557Z-d96adb.md) |
| history first-request due=3 | `20261013163646-86190d` / [early-due run](runs/story-ongoing-station-system-work-history-early-due-20261013T163646Z-1eb2f4/) | m1 玩家请求有 settled native receipt；A 的 lend 候选 eligible/provisional，但按既有候选排序选了 inspection。之后没有 loan/return 物理 receipt 或 witnessed return event，因此未形成 history treatment。工作链仍真实完成。 | `db-readback.json` SHA-256 `48a254b8cfcc3be8b4de232c2ddc76b9e2996bcbb0e8d9e09db2ab55ebe215ae`；[回放](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-history-early-due-20261013T163646Z-1eb2f4.md) |
| history first-request due=2 | `20261013163728-594202` / [tight-due run](runs/story-ongoing-station-system-work-history-tight-due-20261013T163728Z-3655a0/) | m1 玩家请求也有 settled receipt；同样由 inspection 候选先行，没有实际 loan/return，故无准时/迟还的历史因果比较。工作链真实完成。 | `db-readback.json` SHA-256 `9791b58f73b42b516f4fdd89c9ae45211dda00baca48d0f83c3eac9fa2c4888f`；[回放](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-history-tight-due-20261013T163728Z-3655a0.md) |

GT literal-store commitment 在 scene 内具有独立 source id、`repair-before-storage` constraint、grant `system-work-v1:repair-before-storage:fixed-native-grant`、projection `system-work-v1:2:47b66b7b5ce3`、sequence index 0 与锁片 hash `7dff5c671c5f9d18277788bbf650e81571836bcc085c9e5ee09c52fcf5cb9bd1`；其 m15 settled receipt 为 `station-store:20261013163433-17a730:8806:8808:15:1`，与 commitment 精确 join。inspect 与 repair 仍是 SELF commitments，不将其倒写成作者锁任务。event-driven 同样完成；两种 selector 选得同一 `inspect_then_repair` 方法并得到相同物理序列，本组有限证据不支持任何一方更优。

History 两场的入口不是未实现或未触发：请求真实结算、local request 被角色看见、lend 候选 eligible；实际排序选择 inspection，两个 due 条件均没生成借还事件。故历史准入/处理变量没有形成，二者只能作为无处理对照，不能声称历史规则通过或失败。

### 保留的同回合失败与部分场景

以下尝试均保留原始目录、minute/最终 trace、输入、source snapshot 和 scoped DB（若当时已成功导出）；最终四场不覆盖它们。

| 结果 | Scene / run | 原因或边界 |
|---|---|---|
| Incomplete | `20261013144618-f9fda6` / [run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T144618Z-5f4bd9/) | P3 planning 未初始化 `item_room` 导致异常；实际封存到 m2。之后修复并加 concrete regression；没有重放故障 minute。 |
| PARTIAL，世界运行至 24m | `20261013145645-67fa5d` / [run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T145645Z-4a215b/) | 场景实际运行到 24 分钟；raw `INCOMPLETE` 来自审计器对 `task_kind=None` 的解析异常。旧 draft 修改既有 control mode，CAS 正常拒绝 immutable/mode conflict；不能作为新控制模式通过证据。 |
| Incomplete | `20261013154128-8691c0` / [run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T154127Z-2db5fd/) | locked-order prerequisite 被错误按 literal lock 处理，adapter 拒绝任务；后加 producer→adapter 组合测试。 |
| PASS，但无作者 locked store | `20261013152025-ae10cd` / [run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T152025Z-138e71/) | 物理/TypedIR 终态有效，但高层长时间 WAIT、没有 AUTHOR commitment；不得用其终态冒充跨层协调成功。 |
| PASS，但 deferred offer 丢失 | `20261013162100-c6cb25` / [run](runs/story-ongoing-station-system-work-main-gtpyhop-20261013T162100Z-3325fe/) | 场景物理目标完成，但 m12 deferred literal offer 未留到 m13 空闲边界，SELF storage 接手；催生本节有界 adapter 修复与最终复核。 |
| PASS，同早期 source | `20261013152353-88d84a` / [run](runs/story-ongoing-station-system-work-main-event-driven-20261013T152353Z-5fcc69/) | event-driven 配对前期版本；仅作开发证据。 |
| PASS，同早期 source | `20261013162302-db99e2` / [run](runs/story-ongoing-station-system-work-main-event-driven-20261013T162302Z-c5752b/) | 配对终态通过，但在 deferred-offer adapter 修复前，不作最终四场替代。 |
| PARTIAL | `20261013152443-dec19e` / [run](runs/story-ongoing-station-system-work-history-early-due-20261013T152443Z-3fc1ac/) | 初次 history 入口问题，未形成合格 history treatment。 |
| PARTIAL | `20261013162347-bf658d` / [run](runs/story-ongoing-station-system-work-history-early-due-20261013T162346Z-4d6277/) | 请求已修复并真实结算；但实际候选排序未触发借还，未形成 history treatment。 |
| PARTIAL | `20261013152516-ac1f7d` / [run](runs/story-ongoing-station-system-work-history-tight-due-20261013T152516Z-16e079/) | 初次 tight-due history 尝试，未形成合格 history treatment。 |
| PARTIAL | `20261013162438-a43f1f` / [run](runs/story-ongoing-station-system-work-history-tight-due-20261013T162438Z-39ea9a/) | 请求已修复并真实结算；但实际候选排序未触发借还，未形成 history treatment。 |

另外，v2 双任务 locked draft `system-work-v2.json` 与更早的 store-lock draft `system-work-v2-store-lock.json` 均非最终输入；最终条件只使用 `system-work-v2-order-store-lock.json`。未把旧失败输入改名成正例。

### 成本、复现与范围

本轮确认存在两种高层实现路径，但在最终 GT/event 配对中，方法选择、角色活动与物理收据序列一致；因此没有收益或速度优势主张。每个最终主场有 23 个唯一高层 controller evaluation 分钟（按分钟去重；不是原始约束行数）。GT 实际调用 13 次 GTPyhop search、记录 40 行 search trace；event-driven 调用 0 次 GTPyhop search，在 13 个选择阶段记录 26 条方法候选（每阶段两条）。这些记录不计内部重复前提评估。两臂各有 43 条带 actor planner 的局部决策（A=22、B=21），P3 `method_action_visits` 合计各 108。Trace 行数不是独立状态访问数；event candidate evaluation 与 GT search 不是同一种成本单位。墙钟耗时未采集，记为 unknown。

actor-local P3 HTN、单步 dispatcher、Evennia 物理状态与 P4 clock 都是共用基线；增量仅是注册 station 工作内容、两个有限序列方法、当前 AuthorBundle 投影/offer 接缝、局部工作/receipt witness 与审计器。方法并不构成一般生活目标生成、任意任务协调或完整 BDI。工作下界是基于可认证 primitive/receipt 的条件估计，不是保证完成时间；缺路线/失败模型时不伪造 ETA。当前世界不持久化一般 crash-recovery workflow。此次 episode 没有原生 active-work abort，也没有部分工作进度语义；中途合法拿走工具发生在 B repair 开始前，且场景无 work-abort ledger event。历史 pair 因实际排序未触发借还而维持 PARTIAL。

作者建模、实现、runtime 调试和实验运营分别投入工时未知，不以 LOC 替代人时。可复现 suite 路径：`tools/native_platform_v0/p5/ongoing_station/cases/system-work-suite.json`；使用项目 pinned Evennia venv 与 `PYTHONPATH=.:tools:tools/native_platform_v0/bridge`。最终 quartet 同一 controller source hash `1f1328b19cbb5e17afd1f8149ad47c8cf4e923cdd6aa2c4bf72056db75e2ec75`；P5 regression 共 228 项，227 pass、1 configured-Django skip。三次同实例重载的可用 stop/start 日志只读复制入 [完整 lifecycle carrier](runs/story-ongoing-station-lifecycle-all-reloads-20261013T1652Z/)；无 standalone 权限误判或 source-freeze transcript，说明见载体。发布快照之后，`commands.py` 与 `work.py` 仅做 EOF 空白清理，AST 与最终 run 的源码快照一致；逐场快照仍是对应场景的 source authority，未用当前 HEAD 替换。

本节最终公开包索引、归档 SHA 与成员校验见下方新发布入口；允许目录严格为上述 15 个 `story-ongoing-station-system-work-*` 尝试加 lifecycle carrier。排除私有原文、凭证、DB binary 和其他项目。八个更早的 M5/E1–E4 runs 及 S1–S4/E0 均不属于此次新 package allowlist。

本次发布：[归档 `story-process-v1.tar.gz`](public_evidence/story-process-v1-20261013T165500Z/story-process-v1.tar.gz)（SHA-256 `8c6adce4e53061b0ceaef990ac505ec522763e17fadb1e86b2ab4099c33ff5a3`，11,793,391 压缩字节）；[成员索引](public_evidence/story-process-v1-20261013T165500Z/index.json)（16 个 run directories，1,261 个成员，220,680,317 原始字节，逐成员 VERIFIED）；[发布范围补充](public_evidence/story-process-v1-20261013T165500Z/publication-scope.md)。四份最终回放在包外可直接阅读：[GT](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-main-gtpyhop-20261013T163433Z-0e5719.md)、[event-driven](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-main-event-driven-20261013T163557Z-d96adb.md)、[history due=3](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-history-early-due-20261013T163646Z-1eb2f4.md)、[history due=2](public_evidence/story-process-v1-20261013T165500Z/readable_replays/story-ongoing-station-system-work-history-tight-due-20261013T163728Z-3655a0.md)。回放副本与 run 内原件逐字节相同，SHA 列于 [回放索引](public_evidence/story-process-v1-20261013T165500Z/readable_replay_index.json)。旧 `164200Z` 包保持不变。
