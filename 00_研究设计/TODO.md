# TODO｜active research queue

更新时间：2026-10-22。此页只保留 ID、状态、下一动作、验收条件和链接；历史论证与已完成批次见[TODO 原版快照](归档/2026-09-07_TODO瘦身/TODO_原版_2026-09-07.md)。总体失败证据和证据边界以[研究重建审计](研究重建审计_2026-10-06.md)为准。

当前统一目标是让角色在持续游戏世界中依据自身目标行动，同时接受作者在线未来要求与修改，由协调过程组织成熟方法、调用原生行为、读取真实反馈并继续更新计划；开发与科学验证是同一过程。问题定义仍由唯一 [F0/F1](CharacterDynamics_FormalProblem_v0.md) 维护，本次不改定义。成熟方法能解是复用基础，不构成停止开发条件；多条合法路径只是特定算法对照条件，不是普遍开发门。旧 C1/C2 `NO_GO` 保留其候选级历史含义，不再作为当前停点。**当前工作包：Character Dynamics Online Integration v0，DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**；本轮跨角色协调结果与 Judge 摘要以[唯一 owner](../02_实验/Character_Dynamics_Online_Integration_v0/CROSS_ACTOR_COORDINATION.md)为准；此前多角色结果、旧在线 playtest 与先前三组运行均按各自历史 owner 保留，不回写。多角色、作者剧情协调与明确版本化 G1 属同一系统开发主线。

**实现检查点：系统集成首轮在 `bf30d4c` 交付 DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW，未 CLOSED**。限定原生内容与四条件开发运行的能力、失败、历史对照未成立及无方法收益证据只见[既有 RESULTS](../02_实验/Mature_Methods_Integration_v1/RESULTS.md)，不换条件刷 PASS。2026-10-14 的 `872292c` / `8ca0a45` 仅设计修订；同日后续实施授权见下段。B0传统基线已完成；随后授权的LLM-Admission见下方独立owner。正式B1/B2模型对照仍暂缓，不会因准入调用而自动扩大比较。M1–M5 / E1–E4 的历史 PARTIAL 不改写。新对话原文仅私有归档；公开限本轮代码、报告、文本回放与测试证据，不包括私有对话、第三方完整源码/资产/二进制。C++、E0、main 不动，不自行 CLOSED。

**2026-10-14 新实施授权：**上方“只更新设计”描述 `872292c` / `8ca0a45` 检查点，不再限制本轮获授权的局部代码债清理与首个外部完整游戏接入。只用 Open Adventure 1.22，先保持上游原规则通过测试与回放，再审查原生 NPC/历史状态；最多三个短场景。不移植 P5 人物策略，不改外部规则，不增加新游戏或调用 LLM。旧 System Integration 的 PARTIAL 与失败不重写。

角色动力学的[阶段与过关证据](研究重建审计_2026-10-06.md)与各原生平台历史阶段分别保留；System Baseline v0、Planner Adapter Integration v1、P0/P5 历史检查点与失败结果不被抹除。文档更新不算原生运行通过。

## SYSTEM / APPLICATION TRACK

2026-10-22 跨角色作者目标协调迭代已停止，状态 **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**。已执行真实跨角色报告交付与作者目标动作排序，但最终会合失败；OFF 监督停更导致完整对照未成立。当前摘要与 Judge 口径以[唯一协调 owner](../02_实验/Character_Dynamics_Online_Integration_v0/CROSS_ACTOR_COORDINATION.md)为准。本轮停止供独立审阅，不自动修复或扩展；后续优先诊断监督 readiness 连续性及接近后会合停滞。旧 ONLINE_PLAYTEST、多角色结果、旧 Judge 和三组运行均保留，不回写。

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| CHARACTER-DYNAMICS-ONLINE-INTEGRATION-V0 | **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW；跨角色协调轮停止** | 停止供独立审阅；后续优先诊断 readiness 连续性与接近后会合停滞，不自动修复或扩展 | [唯一协调 owner 与 Judge 摘要](../02_实验/Character_Dynamics_Online_Integration_v0/CROSS_ACTOR_COORDINATION.md)；真实协调已执行但最终会合失败，OFF 监督停更使完整对照未成立；旧 ONLINE_PLAYTEST 与历史保持原结论 |
| VELOREN-CAUSAL-RESEARCH-ADMISSION-V0 | **历史裁决：两候选 NO_GO / READY_FOR_INDEPENDENT_REVIEW** | 保留原裁决与因果证据，不把双方案条件扩成系统开发门槛；当前集成见上行 | [唯一裁决](../02_实验/Veloren_Causal_Research_Admission_v0/ADMISSION.md)；[机制证据 owner](../02_实验/Veloren_Causal_Research_Admission_v0/CAUSAL_NETWORK.md)。原文档与历史 RESULTS 不改；不据此宣称 Veloren 全局不可能 |
| VELOREN-NATIVE-DECISION-INTEGRATION-V1 | **ROUTING/HIRE/FOLLOW 有限 PASS；READY_FOR_INDEPENDENT_REVIEW；已停** | 独立审阅唯一新OFF/ON：1请求→原生Hired→本人跟随；核预算/日志限制，不自动追加机制或运行 | [唯一 RESULTS](../02_实验/Veloren_Native_Decision_Integration_v1/RESULTS.md#2026-10-18-新授权loaded-msg-最小修复与最后一次纵向验收)；旧PARTIAL/A/C++/main不改，不自行CLOSED |
| VELOREN-VERTICAL-SLICE-V0 | **READY_FOR_INDEPENDENT_REVIEW；A=PASS_BY_NATIVE_TRACE；A_FROZEN** | 有限接口与旧失败保留，不再补跑 Talk；新授权高层接入归上行，不以旧 B 未授权声明阻挡本轮 | [唯一 RESULTS](../02_实验/Veloren_Vertical_Slice_v0/RESULTS.md#最终接口验证实际结果与停止)；Brain→Say→Agent 及有限续行已见原始证据，不推论收方接受、长期自治或完整系统 CLOSED |
| OPENXRAY-NPC-DECISION-ADMISSION-V0 | **接入探索 DEFERRED_BY_USER；原源码交付保留** | 用户决定先试 Veloren；不恢复 CoP 数据/接口调查、不自动开发 C++ 桥或 RimWorld | [原 RESULTS](../02_实验/OpenXRay_NPC_Decision_Admission_v0/RESULTS.md)；OpenXRay 自身历史准入状态仍由该 RESULTS 维护，与当前 Veloren 环境状态分开 |
| CLASSIC-RPG-CARRIER-SELECTION-V0 | **此前检查点：源码补审 PARTIAL / READY_FOR_INDEPENDENT_REVIEW；无实跑** | 选材与前轮源码证据保留；本次决策接入裁决及后续条件转由上行工作包维护，不继续泛化选材 | [选材 RESULTS](../02_实验/Classic_RPG_Carrier_Selection_v0/RESULTS.md)；Exult旧优先级已撤回，源码事实/旧评分保留历史；不自行 CLOSED |
| DOCS-PLANNER-SEMANTICS | **文档修订 / READY_FOR_INDEPENDENT_REVIEW；非新实现** | 定义修订检查点保留；后续已授权的三候选材料选型见上行，不因该文档检查点自动安装或开发 | [F0/F1](CharacterDynamics_FormalProblem_v0.md)定义角色/作者规划与语义边界；[System Vision](Character_Dynamics_System_Vision_v0.md)说明应用路线；[待核候选](未决问题与机制候选.md#2026-10-16角色规划与载体选择的待决问题)保留问题及原生/新增分账；历史运行证据不改、不自行 CLOSED |
| NATIVE-NPC-GAME-ADMISSION-V0 | **P0 DOCUMENTARY_ADMISSION / READY_FOR_INDEPENDENT_REVIEW；无 P1 游戏准入** | 独立审阅三候选来源、状态链及 P1 stop criteria；本轮停止，不启动 P1/P2/P3+，不改历史成果 | [唯一 RESULTS](../02_实验/Native_NPC_Game_Admission_v0/RESULTS.md)；RimWorld 是优先调查候选而非选定版本；CDDA 是 LIMITED_SOURCE_FIT/暂不选择，不作全局 NO-GO；本机未确认 Sims/DLC |
| AUTHOR-OBLIGATION-PLANNING-V0 | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；未 CLOSED；限定证据已公开** | 已推 webgpt-sync 并核验对应 CI，失败与局限见唯一 owner；本轮停止，供独立审阅，不自动新增游戏、正式 B1/B2 或通用 Director | [唯一 RESULTS](../02_实验/Author_Obligation_Planning_v0/RESULTS.md)；[固定协议](../02_实验/Author_Obligation_Planning_v0/PROTOCOL.md)；[代码入口](../tools/author_obligation_planning_v0/README.md) |

2026-10-14 Open Adventure B0 已按[固定协议](../02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md)完成并停止，本检查点为 `DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW`。D clean、最终反馈修复与 E 冻结目标通过预设判据；G 按协议返回 `UNSUPPORTED_SEMANTICS`。首次反馈负控的 `MODEL_MISMATCH` 原始失败保留，修正运行不覆盖它。运行细节、成本与测试数字只见[唯一 RESULTS](../02_实验/OpenAdventure_Planning_B0_v0/RESULTS.md)。三方法比较整体仍为 `PARTIAL`；B1/B2 `DEFERRED_BY_USER`，不自动调用模型或启动新游戏。P1 保留独立有限检查点，不升级为全系统 CLOSED。

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| AUTHOR-CONSTRAINT-DIAGNOSTIC-V0 | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止** | 独立审阅原候选四原子经因果规划/原版完成作者时间语义的证据，及AUTHOR/PLANNER撤销/历史界限；不扩实验或恢复模型比较 | [唯一 RESULTS](../02_实验/Author_Constraint_Diagnostic_v0/RESULTS.md)；[冻结诊断协议](../02_实验/Author_Constraint_Diagnostic_v0/PROTOCOL.md)。旧Admission FAIL不改，零模型调用，不自行 CLOSED |
| LLM-ADMISSION-V0 | **DEVELOPMENT / AGENT_CONFOUNDED / READY_FOR_INDEPENDENT_REVIEW；本轮停止** | 独立审阅真实调用、E的时间语义/残留义务分歧及G缺口分析；不重试、不补答案、不运行拒绝候选，不恢复正式B1/B2 | [唯一 RESULTS](../02_实验/LLM_Admission_v0/RESULTS.md)；[固定协议](../02_实验/LLM_Admission_v0/PROTOCOL.md)。1 probe + E/G各1次；原样输出及运行时证据保留，不自行 CLOSED |
| OPEN-ADVENTURE-PLANNING-B0 | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止** | B0 传统基线交付；独立复核[唯一 RESULTS](../02_实验/OpenAdventure_Planning_B0_v0/RESULTS.md)。三方法整体比较仍为 `PARTIAL`；B1/B2 `DEFERRED_BY_USER`，不自动启动 | [PROTOCOL](../02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md)；结果、失败、预算和成本仅由 RESULTS owner 维护；无 LLM 调用；P1 为独立有限检查点，旧 C++/E0/main 不动，不自行 CLOSED |
| OPEN-ADVENTURE-ONLINE-P1 | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；独立有限检查点已接受** | 保留同进程逐次输入、反馈分支和精确回放结果；P1 继续作为有限接口检查点，不宣称全系统 CLOSED。主要实现和结果证据仅见[唯一 RESULTS](../02_实验/OpenAdventure_Online_P1_v0/RESULTS.md) | 最终程序18次输入/12次非启动、seed 或退出回答的游戏输入；初始观察及18段原始输出精确匹配；16/16离线测试。P1 不代表规划能力或全系统完成 |
| EXTERNAL-GAME-NATIVE | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止** | 原版 Open Adventure 构建、功能测试与三个短回放已交付；独立清理只移除被覆盖定义。固定规则传统准入由上方 B0 项推进；原生社会机制审查可另行讨论，不自动追加第二游戏、模型或扩规则 | [独立维护记录](../02_实验/Mature_Methods_Integration_v1/MAINTENANCE_20261014.md)及回归；原版源码/玩法不变、真实输入/输出与版本/哈希、可见性/缺项可审查。旧 PARTIAL、C++、E0、历史 RESULTS、main 不动，不自行 CLOSED |
| CD-SYSTEM-INTEGRATION | **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW；未 CLOSED** | 保留首轮实现供独立复核，该检查点施工已停止；未来可先比较受限游戏中的语义/因果候选，再检验真实执行与空白泛化，LLM 职责按实际缺口选择，也可不调用。未来 A/B/C 不是三个立即执行的任务 | [既有 RESULTS](../02_实验/Mature_Methods_Integration_v1/RESULTS.md)为唯一运行/失败 owner；[F0/F1](CharacterDynamics_FormalProblem_v0.md)定候选接口语义，[未决问题](未决问题与机制候选.md)定比较/泛化准入。先区分可绑定、可组合、需扩展，不让模型首轮编完整 Bundle；新目标、新场景、新游戏分别报告，来源未核的外部环境不作为正式 benchmark |
| MATURE-METHODS-INTEGRATION-V1 | **M1–M5 / E1–E4 已交付；外部复核确认 PARTIAL；未 CLOSED** | 保留 `b039c87`；停止本包实施，不追加规则刷 PASS；下一切口不以便条或某个 Planner 命名 | [唯一 RESULTS](../02_实验/Mature_Methods_Integration_v1/RESULTS.md)；[现行代码契约](../tools/native_platform_v0/p5/ongoing_station/README.md)。E3/E4 有界证据保留，严格 E1/E2 未证实；限定证据已公开，私有原文、旧 C++、E0 预算、main 不动 |
| PLANNER-ADAPTER-INTEGRATION-V1 | **PARTIAL / READY_FOR_INDEPENDENT_REVIEW；本轮停止** | 审阅实际候选缺失、同域对照和反馈边界；后续仅提出 domain/heuristic 一致性诊断，不自动实施、扩预算、进入 P6 或接 LLM | [唯一 RESULTS](../02_实验/Planner_Adapter_Integration_v1/RESULTS.md)；A1/A2/A4 未证明，不自行 CLOSED；不改历史结果或 F0/F1 |
| SYSTEM-BASELINE-V0 | **PARTIAL；M1 READY_FOR_INDEPENDENT_REVIEW；M2 INVALID；本阶段停止** | 等待 M1 独立审阅；无 native LLM candidate execution，不进入 P6。任何继续实施或新阶段须另行授权 | [唯一 RESULTS](../02_实验/System_Baseline_v0/RESULTS.md)；[M2 证据包](../02_实验/System_Baseline_v0/public_evidence/llm-binding-20261012.tar.gz)及[manifest](../02_实验/System_Baseline_v0/public_evidence/llm-binding-20261012.manifest.json) |
| PLANNER-P0-ORIGINAL | **A/B 有界 DEVELOPMENT 检查点保留；LLM/embedding/Qwen 与 A/B/C 比较 PAUSED** | 保留 A 原生 Sabre/Evennia 证据与 B 五轮历史缓存 replay；不再启动模型/embedding 资源准入，不补做新 LLM 搜索，不比较跨 Sabre 版本节点数。历史重放不称 live，B 实时未准入；不改 frozen C++，不自行 CLOSED | [原始 P0 RESULTS](../02_实验/Planner_P0_v0/RESULTS.md)；[LLM 机制与历史 replay 记录](../01_文献/算法积木/06_P0原始规划路线_2026-10-11/LLM_Sabre_Search.md) |
| P0-INTEGRATION | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；未 CLOSED** | 独立审阅有限运行、失败与边界；CI 仅覆盖离线契约，exact-head 状态以 Actions 为准 | [唯一 RESULTS](../02_实验/Planner_P0_Integration_v0/RESULTS.md)；不等于完整传统系统或独立 NPC agency |
| P0-BASELINE-GATE | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；未 CLOSED** | 三个固定 direct 场景已各做一对运行；停止扩场景、调参或自动修复，等待独立审阅/后续讨论 | [唯一 RESULTS](../02_实验/Planner_P0_Baseline_Gate_v0/RESULTS.md)；[协议](../02_实验/Planner_P0_Baseline_Gate_v0/README.md)；P0-Integration 原 READY 检查点独立保留 |
| P0-AUTHOR-BINDING | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW（固定域离线原型）；未 CLOSED，当前局部扩张暂停** | 保留离线原型和审阅边界；仅在 System Baseline v0 接线需要时复用，不另开 P0-vNext 或 live gate | [唯一 RESULTS](../02_实验/Planner_P0_Author_Binding_v0/RESULTS.md)；[讨论决策与差异记录](2026-10-11_P0_Author_Binding_Discussion.md)；问题语义见 [F0/F1](CharacterDynamics_FormalProblem_v0.md)，TypedIR owner 见 [Pilot](AuthorialTrajectoryPilotV0.md) |
| AUTHOR-PLANNING-NEIGHBOR-CHECK | **MECHANISM_AUDIT_DELIVERED / READY_FOR_INDEPENDENT_REVIEW** | 审阅[强近邻总表及比较候选](../01_文献/算法积木/05_游戏世界规划近邻审计_2026-10-11/全量近邻精读总表_2026-10-11.md)：同一固定G/权限/扰动，成熟符号重规划 vs LLM候选+独立检查，反馈粒度作为受控变量；先核共同语义与强实现准入 | 原件、方法/源码定位、交换接口、世界过程纸面诊断与评价分层已交付；这不是冻结实验协议。改G、固定G规划、文本storylet分账。**未复现软件、未运行新比较，无新机制/组合增益/玩家可信度证据；不自行CLOSED，不自动实验/P6。**定义仍见[F0/F1](CharacterDynamics_FormalProblem_v0.md) |
| BOUNDARY-V1 | **CLOSED / FROZEN** | Kernel / Dynamics / Demo ownership 与依赖边界已完成复核 | [架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md) |
| RUNTIME | **Shared Runtime Kernel v1：CLOSED / FROZEN** | 不因 Demo naturalness 重开；仅处理 execution invariant | [Closure Matrix](Runtime_Closure_Acceptance_Matrix.md) |
| DEMO-LIVING | **ACTIVE / DEMO ONLY** | 保留历史批次为实现诊断。Laya v4.3 一日工程 gate 通过、行为 scale gate 未通过：no-history 单 seed 睡眠 1,149 分钟且历史输入使首请求分布大幅变化；停止扩成 64 actors / 7 days | [core behavior eval](../Demo%20codex-generated/demo/core_behavior_eval_v0/README.md)；[Laya typed policy](../Demo%20codex-generated/demo/laya_typed_policy_v0/README.md)；[v4.3 audit](../outputs/laya_runs/laya_v43_66ebfe7_20260925/RESULTS.md) |
| RESEARCH-DYNAMICS | **TOY_NOT_ADMITTED / 未训练** | 不把四字段手写 law、相对分数 policy 或当前不足的干预测试称作机制通过；不运行会覆盖 artifacts 的生成器 | [研究重建审计](研究重建审计_2026-10-06.md)；[ResearchDynamicsV1 source](../02_实验/ResearchDynamicsV1/README.md) |
| NPC-SYSTEM-INTEGRATION-V0 | **DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW** | 首个 vertical slice 已交付，保留独立审阅实际链与未实现项；后续动作不自动设为 C++ 桥或独立 Python CLI | [唯一结果/需求映射](../02_实验/NPC_System_Integration_v0/RESULTS.md)；[可运行入口](../tools/npc_system_v0/README.md)。不等于正式 E1-2、LLM 接入或完整系统 |
| TRADITIONAL-CHAIN-BASELINE | **P5 Author Bundle：READY_FOR_INDEPENDENT_REVIEW** | 12 场、11/12结构审计及18-world旧回归已复核；保留1项shared-supply真实失败，不改预期、不自动修复。等待独立审阅；不标CLOSED、不自动进入后续阶段 | [当前 P5 README](../02_实验/Native_Platform_P5_v0/README.md) / [唯一 RESULTS 与公开证据索引](../02_实验/Native_Platform_P5_v0/RESULTS.md)；[核心 API](../tools/native_platform_v0/p5/README.md)；历史阶段仍见 [P4-0](../02_实验/Native_Platform_P4_0_v0/README.md) |
| MC-EXECUTION-ROUTE | **DEFERRED_CANDIDATE** | 暂不启动。保留 Minecraft/Mineflayer/煤炭任务作为后续执行载体候选；它不是传统全链原生复现的前置条件 | [历史候选与边界](草案/IntegrationBlueprint_v0/07_INTEGRATION_GAPS.md#历史延期候选minecraft-执行) |
| DIRECTOR-BUDGET-QUESTION | **待源码复现** | 若重新处理，先按来源审计/复现预算疑点；该恢复摘要不构成本轮新确认 | [NPC System Integration v0 结果](../02_实验/NPC_System_Integration_v0/RESULTS.md) |

## ACTIVE

| ID | 状态 | 下一动作 | 验收 / owner |
|---|---|---|---|
| PRAXISH-ACTIVITY-PILOT | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW** | 前两步执行证据与原件保持不变；后续比较另立输入和 outputs，不覆盖旧结果 | [原件运行与验收 owner](../02_实验/Praxish_Activity_Pilot_v0/README.md)；[原文/源码证据](../01_文献/精读_Praxish论文与原始实现_2026-10-06.md) |
| PRAXISH-UTILITY-COMPARISON | **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；有界立项 NO_GO** | 原执行目标已产出否定分支：不以活动组织本身改善该共同场景行为立项。作者成本/玩家偏好仍未知；下一问题待准入，不自动扩方法/训练/招募 | [唯一结果与研究判断](../02_实验/Praxish_Utility_Comparison_v0/RESULTS.md)；[公共 viewer](../02_实验/Praxish_Utility_Comparison_v0/presentation/README.md)；[逐项完成审计](../02_实验/Praxish_Utility_Comparison_v0/PARENT_REVIEW.md#原-thread-goal-逐项完成审计) |
| NPC-CONTINUITY-PILOT | **阶段1—3 DEVELOPMENT / READY_FOR_DISCUSSION，保留** | 三案例×两policy短轨迹与匿名回放已交付，未进入阶段4；本轮不扩展，也不把未提交paired源码混入提交 | [唯一检查点](../Demo%20codex-generated/applications/npc_continuity_v0/STAGE3_CHECKPOINT.md)；[原问题与限制](研究重建审计_2026-10-06.md#玩家目标的第一个可比较问题)。无玩家评价 |
| WORLD-NPC-PERIPHERAL | **算法级首轮已交付；部分原算法未公开/待核** | 保留现有知识缺项；仅在具体有限协议或研究问题需要时核对相应原算法，不主动扩成新一轮大综述、不跑新批次或改 Runtime | [算法、版本与当前边界](../01_文献/算法拆解_NPC方法与生产系统_2026-10-07.md)；长期方向见[系统愿景研究版图](Character_Dynamics_System_Vision_v0.md#长期研究版图) |
| AUTHOR-CONSTRAINT-AUDIT | **E0 有界单次验收 PASS / 外部审阅已收到；CI 成功与预算失败均保留** | 停止非阻断 E0 改进，完整成功/失败证据和固定预算保留，正式 CLOSED 仍待用户明确确认。后续 CI 的具体结果只由结果 owner 维护，不重跑刷绿、不暗改预算；E1-1 是另行授权的开发工作，不改 E0 | [唯一 E0 结果](../02_实验/E0_KeyLedger_v0/RESULTS.md)；[实验入口与审阅边界](../02_实验/E0_KeyLedger_v0/README.md)；[冻结协议](E0_KeyLedger_Protocol_v0.md) |
| E1-LOCAL-AGENCY | **E1-1 DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW；外部定向审阅已收到，无开发阻断** | 停止扩修，等待下一研究问题及明确授权；不自动启动 E1-2 或正式实验，不自行 CLOSED | [唯一结果与审阅边界](../02_实验/E1_KeyLedger_LocalAgency_v0/RESULTS.md)；[协议 v0.r1](E1_KeyLedger_LocalAgency_Protocol_v0.md)；[代码](../tools/e1_keyledger_v0/README.md)。成熟 GOAP 可解公开 deterministic B 有限域；Known/Unknown 零差异仅为负控，不证明一般认知能力 |
| PREDICTION-BASELINE-V1 | **DEVELOPMENT_TRAINED_REPRODUCIBLE / READY_FOR_INDEPENDENT_REVIEW** | 保留旧 fits 与冻结协议，不将旧 physical-history view 冒称完整观察；新比较另由 SOURCE-RANKING-V1 维护 | [唯一旧数值结果](../02_实验/PredictionBaselineV1/RESULTS.md)；[LIGHT 来源准入审计](../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)。完整 actor-visible contract / 人工准入未过，已暴露数据不是 untouched formal test |
| SOURCE-RANKING-V1 | **DEVELOPMENT_TRAINED / PARENT_ARTIFACT_AUDIT_PASS / READY_FOR_INDEPENDENT_REVIEW** | 复核固定比较并确定下一可识别问题；不调参挽救假设，不替代 Paper-0 | [冻结任务/通道规格](../02_实验/LIGHT_SourceRankingV1/README.md)；[唯一结果与下一动作](../02_实验/LIGHT_SourceRankingV1/INPUT_REVIEW.md)，执行准入与 actor-visible 准入分开 |
| SYSTEM | **Shared Runtime Kernel v1：CLOSED / FROZEN** | Continuous Runtime ownership、threshold/W validation、typed rejection、fixtures、trace、case-isolated CTest、explicit DynamicsModel injection 与 isolation guard 已闭环。此状态只关闭执行 Kernel，不代表任何行为模型、Evaluator、Objective、Optimizer 或 Paper-0 完成。 | [Runtime Scheduler v1](Runtime_Scheduler_v1.md)、[Closure 验收矩阵](Runtime_Closure_Acceptance_Matrix.md)、[架构边界](Architecture_Boundary_Runtime_Dynamics_Demo_v1.md) |
| M1 | **历史 proxy 已审计；不作为新研究模型** | 保留旧 Theory-S 结果为 `ExpectedEffectEMAProxyV0` diagnostic，不延伸其心理解释 | [研究重建审计](研究重建审计_2026-10-06.md)；[Pre-V1 validity audit（2026-09阶段边界）](PRE_V1_EXPERIMENT_VALIDITY_AUDIT.md) |
| M2 | **Paper-0 formal blocker；不是全部开发的前置门** | 为正式 Paper-0 补齐 SceneSnapshot → affordance → generated actor-local `A^O` 的最小 ontology 与实例绑定 | 生成不得读 source `A*`；source support 仅 post-hoc 诊断；[Mechanism Sanity v1](../02_实验/Mechanism_Sanity_v1/README.md) |
| M3 | **已完成（owner audit v0）** | 保留审计边界；若要重开 D01，先完成 actor-local observation audit、跨 actor gap 编码和 X 字段准入 | [capability matrix](../02_实验/Theory_S_v2/capability_matrix.md)、[D01 LIGHT](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)、[OPeRA candidate reconstruction](../02_实验/T0d_OPeRA/candidate_reconstruction_feasibility_v0.md)；proxy/telemetry 不升级为 A* |
| POOL | **已完成（routing v1；2026-09-09 superseded）** | 按 routing update 转入 LIGHT actor-local history eligibility gate；ClubFloyd Stage 0c paused，AGAIN 仍仅是 external proxy | [routing v1 + superseding update](Existing_Dataset_Pool_Routing_v1_2026-09-08.md)；不得把旧 ClubFloyd #1 排名当作当前主线 |
| CLUBFLOYD | **Stage 0c non-duplicate view completed；当前 estimand 无正向增量** | 暂停 ClubFloyd persistent-compression / Theory-S bridge；保留 lossless source 与 analysis view；不得继续调参追分 | [Stage 0c protocol](../02_实验/Replay/ClubFloyd/stage0c_nonduplicate_protocol.md)；1,964-row view / 194 test rows |
| LIGHT-H0 | **历史探索性结果；episode-independent signal 未证** | 不再按旧 actor-unit CI 声称泛化；旧数值/artifact 保留。审计发现 H0b/compression train/test 共享 279 episode，三组 pairwise overlap 合计 912 | [split audit](../outputs/research_reset_audit_20261006/split_audit_v3.json)、[H0b report](../02_实验/T0c_LIGHT/LIGHT_H0b_transition_probe_v0.md)、[compression report](../02_实验/T0c_LIGHT/LIGHT_compression_benchmark_v0.md) |
| AGAIN-DYN | **completed development audit；不升级** | 保留 proxy persistence 结果；不训练 Theory-S 参数，不继续设计新 event/tau | [AGAIN audit result](../02_实验/T0h_AGAIN/dynamics_audit_v0_result.md)；event-driven relaxation 不稳定，arousal 仅 external proxy |
| T0d | **LIMITED-GO（v1 single-target failed; set route unresolved）** | routing v1 已完成；不再把该旧待办当 blocker。仅在 LIGHT actor-local gate 为 NO-GO 后，按 OPeRA protocol 重新冻结 set route | v1 每 step 恰好 1 candidate，10/30（33.3%）是 target selection accuracy；canonical 13D readout 仍不兼容；[OPeRA protocol](../02_实验/T0d_OPeRA/OPeRA_pilot_protocol_v0.md)、[v1 correction](../02_实验/T0d_OPeRA/terra_candidate_spike_v1_result.md) |
| D01 | **NO-GO（完整六维训练）** | 保留 actor-local / temporal boundary 失败边界；重开前完成 observation audit、predecessor/gap 编码与 X 字段协议 | [D01 semantic/temporal admission](../02_实验/T0c_LIGHT/D01_semantic_temporal_admission_v0.md)；LIGHT 不作为第一次完整 Theory-S gradient training 主数据 |
| T0c-TR | PAUSED | 等待 M2 candidate-set admission；不单独推进外部 pilot | `ΔO → X → S` 语义与时间边界可追溯；不调参冒充结果 |
| M4 | 未开始 | 独立 `A*` 准入后，冻结 data/split/feature/state protocol，再做 formal gate | 未满足前不启动 Experiment B、正式 test 或论文结果 |

## 研究重建顺序与范围护栏

- **新授权覆盖范围（2026-10-09）**：用户明确“现在不只是外围维护了，可以改了！按照目标文本贴出的txt来”。本次允许 E1 之上的应用整合、有限 Director 与应用版本的 response/commitment；此前下文“Director 未授权”仅描述 E1-1 交付时的状态，已被本条覆盖。E1-2 formal、心理训练、参数优化与冻结 C++ Kernel 仍不重开。新应用数据保持 DEVELOPMENT。

- **E1-1 交付时的检查点（新授权覆盖范围见上方）**：完整研究方向由[系统愿景版图](Character_Dynamics_System_Vision_v0.md#长期研究版图)维护；F0/F1 定系统语义，Pilot 定候选 F2 / TypedIR，04 定原方法综合。A/B 与 Q1–Q3 都不是完整研究目录。E0 已达到有界验收停止条件且收到外部收口建议，数值/成功/失败仅由[结果 owner](../02_实验/E0_KeyLedger_v0/RESULTS.md)维护；不继续完善 E0。2026-10-09 用户明确授权[E1-1 最小实现与开发验证](E1_KeyLedger_LocalAgency_Protocol_v0.md)，完成后停止；正式实验、E1-2、Director、训练或全面方法比较未授权，正式 milestone CLOSED 仍需用户明确确认。非阻断存储/稳定性增强进入 backlog；外围待核算法不扩成综述。Praxish 否定分支与 SourceRanking 开发结果仍由各自 owner 维护，不追分救假设、不否定整个 NPC 方向。Runtime 继续 frozen。
- **Paper-0 formal gates**：persistent `S`、legal actor-local `O`、independent `A*`、可复核有限 `A^O`、episode/user-disjoint split 和预注册指标；M2 是 candidate-set formal admission 工作，不阻塞开发方法基座。
- **PAUSED**：Objective readiness、Evaluator ranking、Optimizer、旧 proxy training、外部数据集扩展；ResearchDynamicsV1 不作为已训练模型，仅记录为尚未准入的 toy/fixture。
- **DEFERRED SYSTEM/RESEARCH BRANCH**：ToM、multi-agent、Inverse、P drift、Q01 advanced response curves、Scene Manager 与 live LLM semantics。
- 所有开发结果标为 DEVELOPMENT；任何已暴露数据都不是 untouched formal test。独立行为标签、actor-local O、可重建 `A^O` 与 episode/user split 是旧 Paper-0 预测主张的缺口，不自动成为玩家可置信性目标的前置门；后者也不能以模型裁判得分冒称玩家认可。不靠 dataset tourism 或重开 Runtime 绕过对应证据要求。

## COMPLETED CHECKPOINTS

- **M0**：Mechanism Sanity v1；固定 `W/O/P/generated A^O` 的 S intervention 通过，见 [README](../02_实验/Mechanism_Sanity_v1/README.md)。
- **M5**：Mechanism Sanity v1.2 trajectory sanity；effort/progress/obstruction/recovery 工程回归通过，见 [README](../02_实验/Mechanism_Sanity_v1_2/README.md)。
- **T14/T20 development chain**：Run 1、1b、2、3、3b、4 已封口；均为 development-only，不是 formal test。
- **LIGHT H0b / compression**：结果 artifact 保留；2026-10-06 split audit 发现 episode 跨 actor 分入不同 split，原有泛化与 actor-unit CI 结论降级为开发切片探索。
- **T0b**：SOTOPIA 30-episode 外部合成 pilot 结构审计完成，但 provenance/action surface 限制使其不能作为真人 A*。
- **T0c-SC**：Replay → SceneSnapshot bridge 已接通；`source available_actions` 不等于 `A^O`。

## BLOCKED / NO-GO

- 候选集不能冻结、角色 O 无法重建、split 有未来/身份泄漏、或外部 A* 不独立：停止 formal baseline。
- 对冻结 Runtime、旧心理/Paper-0 分支仍不新增 S/X schema、改变 P、做 P drift、启动 ToM 或重构 `simulation.cpp`；本次有限应用有自己版本化的状态/语义，与这些冻结 owner 隔离。
- `ResearchDynamicsV1` 是 `TOY_NOT_ADMITTED` 的手写 fixture；`Theory_S_v2` 是 `ExpectedEffectEMAProxyV0` 历史 proxy；Replay 是 canonical feature layer；PredictionBaselineV1 是已拟合并复现、待独立外审的 DEVELOPMENT 预测方法基座，不代表已学到心理 `S` 或 Runtime policy；dataset adapter 只做 raw → ReplayRecord/SceneSnapshot/X-compatible input，不复制 proxy。

## DEFERRED

- Paper-0 正式比较：`history / summary / no-S / theory-S / naive-S / trajectory-permuted-S`，使用同一 candidate-set NLL 和冻结 protocol。
- T20 attribution：generic/naive-S、理论语义与压缩收益的区分；不是当前机制主线。
- 更复杂 commitment、multi-task、inverse、叙事抽取、UI/异步，等首轮 external trajectory protocol 冻结后再评估。`LayaTypedPolicyV0` 是受限的本机 Demo policy adapter，不属于此研究 protocol。

## SOURCE OF TRUTH

- 研究历史失败、当前科学证据与方法重建顺序：[研究重建审计](研究重建审计_2026-10-06.md)
- 当前事实：[当前实现进度](当前实现进度.md)
- 当前入口：[项目现状速览](项目现状速览_通俗版.md)
- 冻结研究问题：[Paper-0问题卡](Paper-0问题卡.md)
- 实验索引：[实验 README](../02_实验/README.md)
- 架构边界：[ARCHITECTURE_RULES](../ARCHITECTURE_RULES.md)
