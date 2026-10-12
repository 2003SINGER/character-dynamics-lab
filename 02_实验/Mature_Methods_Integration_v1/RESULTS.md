# Mature-Methods Integration v1 — bounded native evidence

状态：**DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**（2026-10-12；未 CLOSED）。原 S1–S4 与 S2 权限编辑拒绝仍是历史结果；同阶段新增的“真实便条回应后归档”有界增量已完成开发运行，现待独立审阅。该增量不改变旧结果，也不构成完整系统通过、性能优势、研究新颖性或机制有效性证据；不自动进入新阶段。

> **历史分隔：** 下方原 S1–S4 内容维持其原始结果和边界，不应用作本次 story-process 增量的当前状态。新增增量的唯一结果见本文末尾“2026-10-12 Story-process 增量”。

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
