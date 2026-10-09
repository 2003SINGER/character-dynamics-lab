# IntegrationBlueprint v0 — Idea Ledger

> 草案：按 `webgpt-sync@19e5b373303b1504b7fa46f6e01af4563947171a` 的可见源码与 owner 文档核对。这里追踪思想，不冻结算法，也不把工程通过写成心理或玩家效度。状态只回答“这条思想在来源中的地位”，不是实现成熟度。

## 判读与证据边界

- `USER_CONFIRMED`：能在用户直接原话或当前 owner 的明确用户决定中找到依据；仅确认原意，不代表公式、科学效度或每项实现方案均已决定。
- `DOCUMENTED_CANDIDATE`：owner 文档维护的待选机制、候选形式或研究方向；还需决定、比较或验证。
- `ASSISTANT_PROPOSAL`：模型提出的结构、公式或选项，未见用户明确采纳。它可以是有用接缝，但不能升级成用户决定。
- `LEGACY_ASSUMPTION`：旧摘要、代码形状或过时状态曾被当成事实；本版标明证据不足、后来变更或与现 HEAD 不符。

出处优先指向公开 owner 章节。2026-10-09 的完整用户—模型讨论保存在本机私有源，SHA-256 `12ef1420e1db6b580e69c149601357cc4d20a17c50e5103933add12f690b783f`；公开索引说明其归档和阅读边界：[原始材料索引](../../../90_原始材料/README.md)。本文件仅引用该 hash、用户发言时点与被公开 owner 吸收的语义，不复述私有原文。较早来源及阅读判断见[2026-09-01 原始探索](../../../90_原始材料/2026-09-01_动态人物世界模拟探索/阅读判断.md)。

“成熟近邻”仅转引仓库已有的职责级方法卡和已审计 owner；这些是可比较的方法，不是新查新结果、等价证明或本项目原创性证据。相关卡片：[01 叙事修复与导演](../../../01_文献/算法积木/01_叙事修复与导演.md)、[02 人物意图与约束规划](../../../01_文献/算法积木/02_人物意图与约束规划.md)、[03 内容绑定与 LLM 桥接](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)、[04 统一问题与成熟基线准入](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md)。

## 思想条目

### 1. 客观世界、角色认知与错误/过时信念分离

- **状态：** `USER_CONFIRMED`。
- **原意：** `W` 是唯一客观真值；`O_i` 只含角色合法获得的信息，可为 unknown、stale 或错误。角色依据自己的 `O_i` 形成候选，不可从隐藏 `W` 获得正确答案；现实合法性仍由世界检查。
- **出处：** [完整机制 §2–4](../../完整机制说明_v0.md)；[Q04](../../未决问题与机制候选.md#q04-主观动作候选与隐藏条件)；[F0/F1 §2、§4](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** C++ [observation.h](../../../Demo%20codex-generated/Inc/observation.h) 有 Known/Stale/Unknown、`InformationAccess`、局部 feedback 与 `A^O`；[world.h](../../../Demo%20codex-generated/Inc/world.h) 独立校验。Python E0/E1 checkpoint 分开 W/O；npc_system_v0 的 `actor_view` 提供有限视图。对象级错误 belief、遮挡、多实体感知仍有限。
- **成熟近邻：** [工程三空白核读 §5.1–5.3](../../../01_文献/专题核读_工程三空白_2026-09-05.md) 对 W≠O 先例的边界；[三方向近邻核读 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md) 对 GOAP/Utility 默认状态权限的比较。
- **接缝：** perception projection → actor-local affordance/plan view；W validation → typed rejection/合法反馈 → O 更新。
- **未决：** stale 何时失效、错误信念怎样修订、注意/遮挡/传闻如何建模，以及局部候选如何绑定稳定对象 ID。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)；[03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)。

### 2. 二阶知识与他人认知

- **状态：** `USER_CONFIRMED`（保留问题重要性；具体表示未定）。
- **原意：** 不只表示“A 知道什么”，还要能表达“A 认为 B 知道/不知道什么”；这是多人互动与信息差的语义要求，不能把全局 O 复制给每个人。
- **出处：** [完整机制 §3.1.2](../../完整机制说明_v0.md#312-二阶知识用户-2026-09-05-确认为必需从后续分支升为-v0-设计要求)：明确记载用户 2026-09-05 确认“二阶知识肯定需要”，并规定角色信息边界；[F0/F1 §2](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** E1/npc_system_v0 有 A/B 分离 O、B 自主接受/拒绝，但没有嵌套 belief/ToM 状态；C++ `Observation` 是单角色视图，不是 belief-of-belief 模型。
- **成熟近邻：** [完整机制 §3.1.2](../../完整机制说明_v0.md#312-二阶知识用户-2026-09-05-确认为必需从后续分支升为-v0-设计要求)指出学术 ToM 已有工作、工业/游戏接缝仍需另查；本轮不把任何近邻等同所需表示。
- **接缝：** actor-local belief store + 可追溯的“我认为对方知道”更新；只能通过观察、交流或已建机制更新。
- **未决：** 是否需要递归到几阶、信念置信/来源表示、错误 ToM 更新成本，以及哪些场景确实需要它。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)。

### 3. `O/ΔO → X → S` 的语义中间层

- **状态：** `USER_CONFIRMED`。
- **原意：** 经历对角色“意味着什么”(`X`) 不等于直接增加/扣减情绪数值；先解释合法观察，再让动力学消费可检查的语义结果。
- **出处：** [完整机制 §2、§3](../../完整机制说明_v0.md)；[ARCHITECTURE_RULES §18–27](../../../ARCHITECTURE_RULES.md)；[Q02](../../未决问题与机制候选.md#q02-x-与字段动力学如何真正分开)。
- **现码 / 缺口：** C++ `CharacterDynamicsModel::appraise/apply_impulse` 与 `Appraisal` 已有接口；Demo 有规则及 opt-in typed appraisal。npc_system_v0 `model.py` 以 `appraise(view,new_events)` 形成 X。没有被验证的通用心理语义 schema。
- **成熟近邻：** [X 维度与状态动力学核读 §2–4](../../../01_文献/专题核读_X维度与状态动力学_2026-09-05.md) 对照 X 候选、FAtiMA/EMA 更新边界及 re-appraisal；[全量近邻精读总表 2026-10-06 §2](../../../01_文献/全量近邻精读总表_2026-10-06.md)记录 EMA 过程模型及阅读证据等级。
- **接缝：** `ObservationDelta + prior O/S/P + history → typed X (+ provenance) → U_k`；语义层不能直接写 S。
- **未决：** 最小 X 维度、目标/预期/控制感等评价量如何定义，X 是否可由规则/LLM/hybrid 产生，以及其错误如何与 updater 错误区分。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)。

### 4. 重评价与新证据修正旧解释

- **状态：** `DOCUMENTED_CANDIDATE`。
- **原意：** 新信息可改变对先前事件的解释；不应把第一次 appraisal 永远累加成不可修正的状态。
- **出处：** [未决问题 Q02](../../未决问题与机制候选.md)；[完整机制 §3](../../完整机制说明_v0.md)。
- **现码 / 缺口：** O 支持 known/stale 与更新事件；X/impulse 主要消费当前变化，未见一般的“旧事件重评估并校正既有状态”契约。
- **成熟近邻：** [X 维度与状态动力学核读 §4](../../../01_文献/专题核读_X维度与状态动力学_2026-09-05.md#4-re-appraisal-的可计算形式)列出 re-appraisal 的可计算近邻与前提；不是项目已定更新器。
- **接缝：** 新证据 → 指向既有 episode/claim 的 appraisal revision → 带依据的状态 patch 或 belief 修订。
- **未决：** 重评影响哪些字段、是否回写旧状态、时间衰减与证据冲突怎样处理；必须避免改写已提交世界历史。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)。

### 5. 每个状态字段拥有自己的 `U_k`

- **状态：** `USER_CONFIRMED`（独立、可替换的字段更新思想）；统一注册/patch 合并方式仍是候选。
- **原意：** 疲劳、压力、意图等字段有各自触发、积累、恢复和耦合；模块可分别替换，但并非彼此独立或互不作用。
- **出处：** [完整机制 §8](../../完整机制说明_v0.md)；[未决问题 Q02–Q03](../../未决问题与机制候选.md)；[架构规则 §18–27、§36](../../../ARCHITECTURE_RULES.md)。
- **现码 / 缺口：** `CharacterDynamicsModel` 可替换整个 dynamics model，C++ state 更新由选定模型消费；npc_system_v0 `ContextDriveV0`/`MonotoneAvoidanceV0` 可替换响应实现。尚无通用逐字段 U_k 注册、版本、冲突合并机制。
- **成熟近邻：** [X 维度与状态动力学核读 §3](../../../01_文献/专题核读_X维度与状态动力学_2026-09-05.md#3-u_k-更新形式候选本页核心产出-b)明确指出“逐字段独立 U_k”未见于所核 12 篇；FAtiMA/TCN 只提供更新形式近邻，不能为项目自定义 U_k 背书。
- **接缝：** 只读一致快照 → 各 updater 返回有版本/provenance 的 patch → 唯一状态 owner 检查冲突并提交。
- **未决：** 多 patch 优先级、旧值/新值依赖、Δt 口径、裁剪所有者与哪些跨字段耦合必须显式保留。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：独立字段更新、P 调制与阶段响应](03_ACTOR_DYNAMICS.pseudo.md)。

### 6. 非线性、阶段性状态消费：Q01 逆映射候选

- **状态：** `DOCUMENTED_CANDIDATE`；用户明确提出“逆映射/正常—独特—极端分区”的原意，但具体切点和消费函数未拍板。
- **原意：** 状态数值仍连续更新；消费函数可在阶段间改变响应，不只是给数值换标签。文档分开近似分区与 `Φ⁻¹(u)` 精确标准正态分区；它不是要求状态服从正态，也非人群校准。
- **出处：** [未决问题 Q01](../../未决问题与机制候选.md)（含原意、正态逆映射、近似/精确边界与 utility 文献判定）；[当前实现进度 §3](../../当前实现进度.md)。
- **现码 / 缺口：** C++ 规则系数和 npc_system_v0 的非线性/overload 皆是开发实现，不等于 Q01 逆映射已落地；未实现基于逆映射的阶段化通用 consumer，也未识别心理收益。
- **成熟近邻：** [三方向近邻核读 §2–3](../../../01_文献/专题核读_三方向近邻_2026-09-05.md)记录 Utility 2013 §9.5.4 响应曲线、§9.6 分桶与 §9.7 inertia；[X 维度核读 §6](../../../01_文献/专题核读_X维度与状态动力学_2026-09-05.md#6-对-q01-的判定重要结论为否定)明确 Fleeson 不支持正态折点。
- **接缝：** 选定变量与消费点 → 单独版本化分段/连续曲线/gate → 输出可观察的目标或行动差异。
- **未决：** 使用近似边界、精确逆 CDF 还是纯人工切点；低端/高端语义、连续性、滞回及最小可辨行为指标。**不与下条压力非单调候选合并。**
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：独立字段更新、P 调制与阶段响应](03_ACTOR_DYNAMICS.pseudo.md)。

### 7. 压力的非单调行为效应

- **状态：** `USER_CONFIRMED`（不接受“压力越高必然越回避”的单调化；具体响应曲线仍需检验）。
- **原意：** 用户指出较低/适中压力可能督促投入，过载时才可能抑制、回避或恢复；压力可以影响启动、坚持、目标切换等不同环节，不能凭一个“压力影响权重”声称实现了原机制。
- **出处：** [完整机制 §3、§8](../../完整机制说明_v0.md)；[Q06](../../未决问题与机制候选.md#q06-行动质量与任务关联压力)；2026-10-09 私有来源 hash（仅作为方向补充，不引用模型归纳为逐字原话）。
- **现码 / 缺口：** npc_system_v0 `ContextDriveV0.drive()` 给有限开发场景非单调 drive，`MonotoneAvoidanceV0` 是反例模型；[RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)只证实现可改变开发行为，不是普遍倒 U 心理规律。C++ 冻结 schema 不等于该候选已科学验证。
- **成熟近邻：** [三方向近邻核读 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md)有一般 utility 响应曲线与目标分桶近邻，但不支持“压力必为倒 U”或本项目的压力心理效应；没有直接验证近邻。
- **接缝：** Stress updater/response → 明确 Goal Selector、Commitment 或 action-quality consumer → 同场景配对观察。
- **未决：** 压力评价语义、任务难度/个体调节、到底影响启动还是执行/坚持、指标和公平对照。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：独立字段更新、P 调制与阶段响应](03_ACTOR_DYNAMICS.pseudo.md)；[03：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)。

### 8. 稳定人物差异 `P` 是反应调制，不是角色小传

- **状态：** `USER_CONFIRMED`（稳定差异参与同一情境的不同反应）；P 的字段与人格规律未验证。
- **原意：** 同一事件可因角色差异产生不同解释、状态更新和行动倾向；P 在运行内相对稳定，不应靠静态描述覆盖动态因果链。
- **出处：** [完整机制 §3](../../完整机制说明_v0.md)；[原始阅读判断](../../../90_原始材料/2026-09-01_动态人物世界模拟探索/阅读判断.md)。私有讨论仅以归档 hash 作背景，不用未复核时点定位原话。
- **现码 / 缺口：** C++ `Personality` 进入所选 `CharacterDynamicsModel` / policy；demo 有具名 profile；npc_system_v0 model/goal arbitration 提供有限参数。并非拟合的人格或已证明的个体差异模型。
- **成熟近邻：** [研究重建审计](../../研究重建审计_2026-10-06.md)没有证明某种 P 字段或人格因果律；Thespian 的 reward fitting 只是目标选择/个体化比较，不是人格测量证据。项目专属 P 维度仍待专题核读。
- **接缝：** 版本化 P → appraisal/updater/goal utility 的明示读取点，并保留零化/替换消融。
- **未决：** P 的哪些维度有独立行为消费者、个体化依据、与 S 的可辨识关系及是否需运行中变化。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：独立字段更新、P 调制与阶段响应](03_ACTOR_DYNAMICS.pseudo.md)；[03：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)。

### 9. 状态之外的历史、记忆与压缩

- **状态：** `DOCUMENTED_CANDIDATE`。
- **原意：** 人物过去发生的帮助、承诺、失败与中断应参与未来；不是每轮把整段剧本重读，也不等于把所有知识/关系都压成 S 的浮点数。
- **出处：** [完整机制 §2–3](../../完整机制说明_v0.md)；[F0/F1 §2](../../CharacterDynamics_FormalProblem_v0.md)；[研究重建审计 §想法到可执行机制](../../研究重建审计_2026-10-06.md)。
- **现码 / 缺口：** C++ `ActorHistory` 有限滚动历史和 trace；npc_system_v0 checkpoint 含事件、收据及角色可见历史。通用长期记忆选择、压缩/遗忘、原型检索策略未实现/识别。
- **成熟近邻：** [全量近邻精读总表 2026-10-06 §5、§8](../../../01_文献/全量近邻精读总表_2026-10-06.md)分别记录 Generative Agents memory loop 与 BehaviorChain 的证据等级；[研究重建审计 §想法到可执行机制](../../研究重建审计_2026-10-06.md)提醒“保留有用历史”仍需定义成操作。
- **接缝：** 事件证据 → actor-local episodic/semantic memory → appraisal/goal query；严格保存来源与可见范围。
- **未决：** 保存/遗忘触发、检索输入与输出、同预算 recency/summary 基线、跨回合因果和 token/延迟成本。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)；[04_PLANNING_BRIDGES.pseudo.md：缓存、异步候选与调用成本](04_PLANNING_BRIDGES.pseudo.md)。

### 10. `WorldTask → TaskCommitment → Action` 三层对象

- **状态：** `USER_CONFIRMED`。
- **原意：** 客观任务、角色对任务的持久承诺、当前一次行动互不等同；目标选择和 planner 不可把它们揉成一个 task/goal。
- **出处：** [完整机制 §5.3](../../完整机制说明_v0.md#53-taskcommitment-与单步-action)；[F0/F1 §2、§4](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** C++ `WorldTask`、`TaskCommitment` 和 `RunningAction` 分离；npc_system_v0 checkpoint 分别维护 world progress / actor commitment / running action；E0/E1 也区分 world progress 与 action receipt。通用多任务目标层未实现。
- **成熟近邻：** [02 IPOCL 卡](../../../01_文献/算法积木/02_人物意图与约束规划.md)明确 intent frame 不等于运行时 TaskCommitment；[04 §2](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md)。
- **接缝：** 角色先选/维护 goal 与 commitment，再把具体目标交 planner；executor 只提交一次 action 并回传结算。
- **未决：** 多任务竞争、目标产生与绑定、任务取消/失败/到期，以及 commitment 如何解释成 planner goal。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)；[03_ACTOR_DYNAMICS.pseudo.md：三种持久对象与承诺生命周期](03_ACTOR_DYNAMICS.pseudo.md)。

### 11. 承诺的暂停、恢复、放弃与知识门控

- **状态：** `USER_CONFIRMED`（暂停/恢复不等于重置；完成需角色获得证据）。放弃机制的完整语义尚属缺口。
- **原意：** 中断时任务进度和 started_at 不因暂停而清零；新信息可导致恢复或放弃。若 W 已完成但角色不知道，不应自动把其承诺标完成。
- **出处：** [完整机制 §5.3](../../完整机制说明_v0.md#53-taskcommitment-与单步-action)；[未决问题 Q07](../../未决问题与机制候选.md#q07-commitment-的信息入口和生命周期)；[当前实现进度 §3](../../当前实现进度.md)。
- **现码 / 缺口：** C++ `CommitmentStatus::{None,Active,Suspended}`、typed self-feedback；npc_system_v0 保留开始时间，只有合法完成认知才关闭。本应用已有暂停/恢复状态，但一般放弃/重承诺原因模型有限。
- **成熟近邻：** [工程三空白核读 §4.1、§4.4](../../../01_文献/专题核读_工程三空白_2026-09-05.md)记录 Côté 的 starting/canceling/completing conditions 与 Dill rank 近邻；[Q07](../../未决问题与机制候选.md#q07-commitment-的信息入口和生命周期)维护项目的未决语义。
- **接缝：** receipt/合法观察 → appraisal → commitment transition(reason, source, time)；world task completion 不可直接写 actor commitment。
- **未决：** 何种目标竞争、压力/关系或证据触发暂停、恢复、放弃；何时允许重新开启已完成任务。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：三种持久对象与承诺生命周期](03_ACTOR_DYNAMICS.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：执行反馈与失败传播](02_WORLD_RUNTIME.pseudo.md)。

### 12. 反应性响应与深思熟虑规划并存

- **状态：** `DOCUMENTED_CANDIDATE`（反应性与深思熟虑分开仲裁是工程近邻；将其纳入本系统仍是候选）。
- **原意：** 并非所有角色行为都应等待 GOAP/HTN 路径最优；火灾等突发事件可能引发即时反应，与长期承诺/规划竞争。
- **出处：** [未决问题 Q07 文献补充](../../未决问题与机制候选.md#q07-commitment-的信息入口和生命周期)；[工程三空白核读 §4.1](../../../01_文献/专题核读_工程三空白_2026-09-05.md#41-côté-2013game-ai-pro-ch11的核心划分)。
- **现码 / 缺口：** C++ scheduler 有 DecisionGate、事件/中断/重考虑入口与 policy hooks；未见通用 reactive-vs-deliberative arbitration 契约。npc_system_v0 每次边界作有限目标/规划决策，非通用紧急行为仲裁。
- **成熟近邻：** [工程三空白核读 §4.1](../../../01_文献/专题核读_工程三空白_2026-09-05.md#41-côté-2013game-ai-pro-ch11的核心划分)记录独立 decision/concept models 与 Action Selector 仲裁；[未决 Q07](../../未决问题与机制候选.md#q07-commitment-的信息入口和生命周期)明确此为待对齐候选。
- **接缝：** 事件优先级/安全反应 → 是否中断当前 `RunningAction` → commitment 保留 → planner 再考虑。
- **未决：** 哪些刺激可抢占、可中断点、不同反应源冲突规则及其对进度的影响。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：唯一时间边界的装配](02_WORLD_RUNTIME.pseudo.md)。

### 13. 行动方式、投入程度与行动质量

- **状态：** `USER_CONFIRMED`（行为不能仅有动作类型；“怎么做”有意义）；统一机制仍是 `DOCUMENTED_CANDIDATE`。
- **原意：** Focused/Halfhearted 表明同名任务的方式不同；还可能区分投入、持续时间、资源消耗和执行质量。人物选择的投入要与世界执行效率、随机噪声分开。
- **出处：** [完整机制 §5.3](../../完整机制说明_v0.md#53-taskcommitment-与单步-action)；[未决问题 Q01](../../未决问题与机制候选.md#q01-分段逆映射与量变质变)、[Q06](../../未决问题与机制候选.md#q06-行动质量与任务关联压力)。
- **现码 / 缺口：** C++ 已有 `StudyFocused`/`StudyHalfhearted` 两个枚举与各自规则占位；Q06 提出 `S/O/Commitment → ActionQuality/Engagement → Payload → W Settlement`。一般 ActionQuality/Payload 尚无通用实现。
- **成熟近邻：** [三方向近邻核读 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md)的 Utility response curve / inertia 可作行动选择侧比较；[工程三空白核读 §4.3](../../../01_文献/专题核读_工程三空白_2026-09-05.md)列长动作与后台执行模式。二者都不等于项目的 ActionQuality 机制。
- **接缝：** Policy 选择 action mode/engagement → typed payload → W executor 按物理规则结算 → 分离记录 intended quality 与 realized outcome。
- **未决：** quality 的可观察单位、S/P/commitment 的作用、效率/噪声归因与动作空间膨胀成本。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：行动方式与世界结果分开](03_ACTOR_DYNAMICS.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)。

### 14. Object / Scene affordance 到人物可行动作

- **状态：** `USER_CONFIRMED`。
- **原意：** Object 提供基础交互，Scene 将它们组合成有生活意义的动作；人物从自己的观察形成可考虑动作；世界最终验证与结算。动作不是简单从 World/Object 继承。
- **出处：** [完整机制 §4](../../完整机制说明_v0.md)；[未决问题 Q04–Q05](../../未决问题与机制候选.md)；[当前实现进度 §3](../../当前实现进度.md)。
- **现码 / 缺口：** C++ `Object`、`Room/Scene`、`KnownObjectAffordance`、`ActionTargetBinding` 与 W start validation 已有基础。scene recipe/多对象组合及通用持续效用/维持条件仍缺；npc_system_v0 KeyLedger 的 operator 集为有限域，不是通用 affordance 库。
- **成熟近邻：** [工程三空白核读 §3.1–3.2](../../../01_文献/专题核读_工程三空白_2026-09-05.md)核读 Şahin affordance 与 ETQ validity；[三方向近邻核读 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md#2-核心发现-a项目的无心理学框架大量重合于-20052013-年的-utility-ai-实践)是 SmartObject/GOAP 的具体近邻。
- **接缝：** Object capability + Scene recipe → 带实体 ID 的 actor proposal；O-known 前提参与 `A^O`，W 真条件由 executor 判。
- **未决：** recipe 与执行器各自所有权、实例绑定、选择/保持条件、target_task_id 如何贯穿 trace。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)。

### 15. 人物局部权限与动作候选 `A^O`

- **状态：** `USER_CONFIRMED`。
- **原意：** Actor 只能规划其已知对象、前提和技能；不等于世界真可执行集合 `A^W`。未知余额/故障可以形成尝试，随后被 W typed rejection。
- **出处：** [完整机制 §4](../../完整机制说明_v0.md)；[未决问题 Q04](../../未决问题与机制候选.md)；[ARCHITECTURE_RULES §21](../../../ARCHITECTURE_RULES.md)。
- **现码 / 缺口：** C++ `rebuild_known_actions_from_observation` 与 `World::validate_runtime_start` 有区分；E1 `actor_view` 和 npc_system_v0 有独立 actor view。一般 skill/effect 信息权限仍是有限实例。
- **成熟近邻：** [工程三空白核读 §3.2、§5.2](../../../01_文献/专题核读_工程三空白_2026-09-05.md)记录 ETQ context object / awareness filtering；[三方向近邻核读 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md)记录 GOAP working-memory 的失败知识边界。
- **接缝：** `A^O` 规划输入、typed ActionIntent → 权威 W 预检、拒绝反馈；预测路径和真实 receipt 分型。
- **未决：** 角色已知前置条件注册、错误 belief 如何改变 candidate、能力/资源/意愿的 actor feasibility 分类。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)；[04_PLANNING_BRIDGES.pseudo.md：ActorFeasibility：五个不合并的检查](04_PLANNING_BRIDGES.pseudo.md)。

### 16. 单一权威时钟、长期动作进度与中断

- **状态：** `USER_CONFIRMED`（持续运行及不中断进度的工程原则已有规范）。
- **原意：** 世界时间不能由 action 私自推进；动作具有持久 progress；事件或重新考虑不应每轮重置已合法动作与进度。
- **出处：** [完整机制 §2、§7](../../完整机制说明_v0.md)；[Runtime Scheduler v1](../../Runtime_Scheduler_v1.md)；[AGENTS §Scheduler-native runtime](../../../AGENTS.md)。
- **现码 / 缺口：** C++ `ContinuousRuntime::execute_next_boundary`、`RuntimeScheduler`、`RunningAction`、`WorldRuntimeAdapter` 是冻结工程设施；E0/E1/npc_system_v0 有独立单分钟有限 executor/action checkpoint。两套执行实现尚未统一，不应重开/重写冻结 Kernel。
- **成熟近邻：** [04 §2](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md)定义共同实例时间与执行语义；这里以本地冻结 Runtime 契约为准。
- **接缝：** 从时钟 owner 取得 `Δt` → 持续 action 进度/自然事件 → completion/interruption receipt → O/X/S/gate；intent start 必经 W 校验。
- **未决：** 应用 Python executor 与 C++ runtime 的 future bridge、并发互斥、资源预约与不同时间粒度的转换。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：唯一时间边界的装配](02_WORLD_RUNTIME.pseudo.md)；[02：执行反馈与失败传播](02_WORLD_RUNTIME.pseudo.md)。

### 17. 多角色各自生活，不以玩家/导演为唯一驱动

- **状态：** `USER_CONFIRMED`。
- **原意：** NPC 在玩家不在场或作者引导关闭时也有自己的目标和日常活动；多角色可自行请求、拒绝、合作或离开，不是单一任务代理。
- **出处：** [完整机制 §1–3、§7](../../完整机制说明_v0.md)；[System Vision 长期研究版图](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)；[2026-09-01 原始阅读判断](../../../90_原始材料/2026-09-01_动态人物世界模拟探索/阅读判断.md)。私有讨论仅按索引 hash 作为补充，不依赖无法精确核对的发言时点。
- **现码 / 缺口：** npc_system_v0 有 A/B，director-off 条件下角色 work/rest/request；[RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)仅验证 8 分钟 KeyLedger 开发域。未有开放多人并发或长时程生活证据。
- **成熟近邻：** [03 Anansi 卡](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)有社交模拟/内容绑定近邻；[04](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md)区分 actor strategy 与 world plan。
- **接缝：** 每个 Actor 拥有 O/S/P/H/commitment/policy；scheduler 只发合法控制机会，共享资源由同一 W 仲裁。
- **未决：** 多角色公平调度、冲突与资源抢占、通信、死锁及规模下成本。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：唯一时间边界的装配](02_WORLD_RUNTIME.pseudo.md)。

### 18. 关系事实、角色可知投影与私有有向态度分属三种所有权

- **状态：** `USER_CONFIRMED`（W/O/S 三种关系所有权）；关系 updater、关系维度与消费者仍未选择。
- **原意：** `W` 保存客观关系事实 `E^W`；每个角色的 `O_i` 只投影其可知、可能过时的关系事实；`S_i` 保存自己对他人的私有有向态度 `R_i[j]`。三者不可互相替代；已确认的是所有权区分，不是任何关系心理学或更新公式。
- **出处：** [完整机制 §3.1.1](../../完整机制说明_v0.md) 对 W 关系事实、O 可知投影、S 私有有向态度作出明确区分；[完整机制 §3.8](../../完整机制说明_v0.md) 重述三所有权并将关系更新器留作未定；[F0/F1 §2、§7](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** E1/npc_system_v0 有 B 对公开交易的 utility/accept/reject，但无通用关系矩阵/关系更新器；当前 C++ state types 也未实现该三层结构。缺实现不削弱已确认的数据所有权。
- **成熟近邻：** [专题核读_三方向近邻 §2](../../../01_文献/专题核读_三方向近邻_2026-09-05.md)中的 SmartObject 与 utility 是交互/选择近邻；[全量近邻精读总表 2026-10-06](../../../01_文献/全量近邻精读总表_2026-10-06.md)中的社会记忆近邻不替本项目选定关系 updater。
- **接缝：** W 事件/关系事实 → 按角色权限生成 O 投影；个人经历/评价由关系 updater 更新 `S_i.R_i[j]`；policy 只读取明示输入。更新器单独可替换，不得跨写 W/O/S。
- **未决：** 哪些关系事实对何人可知、态度的维度/方向/衰减、事件如何改变态度、ToM 如何表达，以及何种 consumer 与验证标签适用。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：主观世界、二阶知识、重评价与记忆](03_ACTOR_DYNAMICS.pseudo.md)；[03：独立字段更新、P 调制与阶段响应](03_ACTOR_DYNAMICS.pseudo.md)。

### 19. 世界自然演化与角色行动并行

- **状态：** `USER_CONFIRMED`。
- **原意：** 时间、资源、日程和既有规律可在没有角色或导演命令时继续变化；自然演化、actor action、玩家 action 和 director action 需要可区分来源。
- **出处：** [完整机制 §2、§7](../../完整机制说明_v0.md)；[System Vision 长期研究版图](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)；[F0/F1 §1、§6](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** C++ `World::advance_runtime_by` 与 scheduler adapter 驱动事件；npc_system_v0 有固定时钟、deadline、动作推进，未含城市生态或长时程生产经济。
- **成熟近邻：** [01 Mimesis/DODM 卡](../../../01_文献/算法积木/01_叙事修复与导演.md)和[03 Anansi 卡](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)提供不同的世界演化/控制近邻。
- **接缝：** 单一 clock boundary 产生自然 WorldEvent；与提交动作结算合并到一份有 provenance 的 ledger，再投影合法观察。
- **未决：** 世界更新频率、自然事件随机性、与 running action 的同刻顺序及预测模型如何覆盖自然过程。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：唯一时间边界的装配](02_WORLD_RUNTIME.pseudo.md)；[05_AUTHOR_DIRECTOR.pseudo.md：World Director 是独立规划参与者](05_AUTHOR_DIRECTOR.pseudo.md)。

### 20. 作者稀疏的多层「点」

- **状态：** `USER_CONFIRMED`（关键发展点可作为作者输入；语法/粒度未冻结）。
- **原意：** 作者只指定重要的人物、关系、事件或世界状态结果，不逐动作写完整情节；点跨抽象层级，不能退化成 planner 任务清单。
- **出处：** [F0/F1 §5](../../CharacterDynamics_FormalProblem_v0.md)；[AuthorialTrajectoryPilot §5](../../AuthorialTrajectoryPilotV0.md)；[完整机制 §7](../../完整机制说明_v0.md)。私有来源仅作 hash 级背景，不据不确定时点定位原话。
- **现码 / 缺口：** TypedIR AST/monitor 和 `npc_system_v0/author.py` 支持有限作者约束 bundle；当前应用支持 global/scene/beat 层 JSON，但非完整可视化创作系统或通用剧情语法。
- **成熟近邻：** [02 PDDL3/Porteous 卡](../../../01_文献/算法积木/02_人物意图与约束规划.md)与[03 DiriGent/WhatELSE 卡](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)分别提供时序规格与高层事件实例化近邻。
- **接缝：** 高层 author node → typed registry/semantic binding → 可监测作者约束；高层生成的子目标另有 owner/id，不能覆盖原节点。
- **未决：** 多层级如何继承/覆盖、作者如何设硬/软/允许分支、抽象要求怎样绑定到具体实体/量。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：意图、绑定、异质点线与版本](05_AUTHOR_DIRECTOR.pseudo.md)。

### 21. 异质「线」：因果、顺序、趋势、状态轨迹与允许区域

- **状态：** `USER_CONFIRMED`（线的语义不可互相压平）；各线的形式化表示有候选并行。
- **原意：** 事件先后、因果支撑、数值趋势、承诺/关系状态变化、禁区/允许区不是同一类边；“点到点连线”不必是线性插值或行动序列。
- **出处：** [AuthorialTrajectoryPilot §3](../../AuthorialTrajectoryPilotV0.md)；[F0/F1 §5](../../CharacterDynamics_FormalProblem_v0.md)；[完整机制 §7、§9](../../完整机制说明_v0.md)。
- **现码 / 缺口：** TypedIR reference 支持有限 AST、时间窗、事件、状态与连续证书；npc_system_v0 运行监测真实 snapshots/receipts 的有限点、顺序与资源线。不存在通用多线高层规划器。
- **成熟近邻：** [02 PDDL3/Porteous](../../../01_文献/算法积木/02_人物意图与约束规划.md)、[01 Mimesis causal links](../../../01_文献/算法积木/01_叙事修复与导演.md)。
- **接缝：** 每条线编译到有类型的 constraint/dependency；Monitor 对真实 ledger 给 verdict；planner 只读这些义务并提出未来候选。
- **未决：** 状态线、数值段与事件线覆盖语义、连续时间证据、未知值、hard conflict 与跨层修订。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：意图、绑定、异质点线与版本](05_AUTHOR_DIRECTOR.pseudo.md)；[05：实际 Monitor 与修复触发](05_AUTHOR_DIRECTOR.pseudo.md)。

### 22. 作者亲写片段与条件锁定

- **状态：** `USER_CONFIRMED`（亲写内容保留为一条控制通道）；Guarded sequence 的具体契约是 `DOCUMENTED_CANDIDATE`。
- **原意：** 作者可亲自写一段关键内容，满足条件后按作者写定的关键内容呈现；它与自由生成的未来不同，但不能假装由角色自然生成。
- **出处：** [AuthorialTrajectoryPilot §10](../../AuthorialTrajectoryPilotV0.md)；[完整机制 §7、§9](../../完整机制说明_v0.md)。任务附件是本轮范围与校核要求，不充当用户原话；私有源仅以索引 hash 标识。
- **现码 / 缺口：** TypedIR 有约束和 seal/provenance；npc_system_v0 当前没有完整 authored segment、guard/abort/fallback runner。
- **成熟近邻：** [03 Drama Llama / Anansi 卡](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)有有序内容/条件触发近邻；文本触发不等价于执行事实。
- **接缝：** guard 对真实 W/O/身份/物件校验 → 作者片段进入受控执行通道 → 每个动作真实结算；失败走预写 abort/branch 或暂停请求作者。
- **未决：** 锁定对白还是关键事件/顺序、可中断点、玩家破坏前提后可否走分支、素材 hash 与执行 provenance。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：作者亲写锁定片段](05_AUTHOR_DIRECTOR.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：执行反馈与失败传播](02_WORLD_RUNTIME.pseudo.md)。

### 23. 显式作者覆写，与自然因果的区别

- **状态：** `USER_CONFIRMED`（存在明确覆写通道并需承认作者来源）；授权颗粒度/后果处理未定。
- **原意：** 作者有权在获授权模式直接规定角色/状态转变；覆写不可伪装成角色自行根据心理决定。作者创作权与“默认自主、优先通过世界机会引导”并存。
- **出处：** [AuthorialTrajectoryPilot §1.1、§10](../../AuthorialTrajectoryPilotV0.md)；[完整机制 §7、§9](../../完整机制说明_v0.md)。任务附件只作为范围/检查清单，不单独证明思想已由用户确认。
- **现码 / 缺口：** npc_system_v0 仅有 `publish_incentive` 世界机会，没有角色状态 setter / override 通道；typed ledger 可记录来源但不是通用授权系统。
- **成熟近邻：** [01 DODM](../../../01_文献/算法积木/01_叙事修复与导演.md)比较不同世界/作者控制操作；本地卡强调权限差异，不宣称已有相同 setter。
- **接缝：** 权限 grant + 目标实体/字段/条件 + override intent → validator → 有 `author_override` provenance 的真实 transition → 冲突/承诺后果重新考虑。
- **未决：** 哪些字段可覆写、谁授权、是否可覆盖关系/知识/承诺、需要何种解释一致性检查与回滚禁止。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：四种控制模式和执行入口](05_AUTHOR_DIRECTOR.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)。

### 24. 经授权的世界机会引导

- **状态：** `USER_CONFIRMED`（优先保留合法机会途径）；操作目录是领域特定且有限。
- **原意：** 可安排线索、资源、任务机会或既有信息，让角色在自身动机下决定回应；这不同于直接设定人物状态或强迫行动。
- **出处：** [完整机制 §7](../../完整机制说明_v0.md)；[F0/F1 §6](../../CharacterDynamics_FormalProblem_v0.md)；当前有限实现见[npc_system_v0 README](../../../tools/npc_system_v0/README.md)。
- **现码 / 缺口：** npc_system_v0 实际实现一种有预算、一次性、公开传播的 `publish_incentive`，由 W 校验后 B 自行回应；不是所有设想中的留言/事件/环境操作。
- **成熟近邻：** [01 DODM 与 Mimesis](../../../01_文献/算法积木/01_叙事修复与导演.md)、[03 WhatELSE](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)。
- **接缝：** Director 只可从授权、注册的 `WorldOperator` 目录绑定 typed action；重验真实 W 后交同一 executor；可见性按 actor 投影。
- **未决：** 哪些机会预先存在/可安排、资源与因果成本、目标冲突、有效窗口、玩家可否阻止与机会失败后的重规划。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：World Director 是独立规划参与者](05_AUTHOR_DIRECTOR.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：世界能力、主观动作与请求](02_WORLD_RUNTIME.pseudo.md)。

### 25. 世界作为规划参与者，同时区分 W、自然规律与 Director

- **状态：** `USER_CONFIRMED`。
- **原意：** 世界不是只能被动承受 NPC 动作；可把拥有自身合法 action space 的 world/director actor 纳入高层规划，主动塑造条件。但世界真值、自然演化规则、世界控制者不是同一对象，不能给 Director 任意 `set_world_state()`。
- **出处：** [F0/F1 §1、§6](../../CharacterDynamics_FormalProblem_v0.md)；[完整机制 §7、§9](../../完整机制说明_v0.md)；[System Vision 长期研究版图](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)。
- **现码 / 缺口：** npc_system_v0 `System.world_proposal` 预测比较 NO_OP 与一个已授权 incentive 并真实提交；当前仅一个 WorldOperator、一种有限策略，不是开放 Director。
- **成熟近邻：** [01 DODM / Mimesis](../../../01_文献/算法积木/01_叙事修复与导演.md)；[04 §1–3](../../../01_文献/算法积木/04_统一问题与成熟基线准入.md) 对世界可达、actor 可行和保证作区分。
- **接缝：** 联合未来模型可含 NPC/玩家/自然世界状态；执行时每一方只能交自己的 ActionIntent，Director proposal 隔离预测后回到当前 W 再校验。
- **未决：** Director 是否有独立目标/预算、同时干预上限、预测策略和玩家响应空间、成本如何定义与是否需鲁棒保证。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：World Director 是独立规划参与者](05_AUTHOR_DIRECTOR.pseudo.md)；[05：实际 Monitor 与修复触发](05_AUTHOR_DIRECTOR.pseudo.md)。

### 26. 高层规划与低层 GOAP/HTN 的桥接

- **状态：** `USER_CONFIRMED`（允许/希望高层下接低层 planner；不冻结 LLM 或具体分解法）。
- **原意：** 高层在稀疏点/线间提出路径/子目标，低层 planner 将角色接受的局部目标变成可执行动作；是目标协调、绑定、失败回传，不是万能 Adapter 或单向 LLM 管线。
- **出处：** [F0/F1 §6](../../CharacterDynamics_FormalProblem_v0.md)；[完整机制 §7、§9](../../完整机制说明_v0.md)；当前有限实现见[npc_system_v0 README](../../../tools/npc_system_v0/README.md)。
- **现码 / 缺口：** npc_system_v0 `System`/`actor_decision` 贯通 GOAP(UCS) 与真实 GTPyhop HTN，同一 executor，且每次只执行首项；高层 LLM 未接入。GOAP/HTN 的完成任务并不产生角色目标本身。
- **成熟近邻：** [02 IPOCL / Porteous](../../../01_文献/算法积木/02_人物意图与约束规划.md)、[03 WhatELSE / DiriGent](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)。
- **接缝：** 高层子目标必须绑定已注册谓词/实体/约束 → actor goal arbitration → planner-specific proposal → 通用 ActionIntent → 真实反馈/失败理由回高层。
- **未决：** 子目标 owner、撤销/替换生命周期、分层期限/资源传递、未来条件分支与 planner 公平替换接口。
- **蓝图落点：** [04_PLANNING_BRIDGES.pseudo.md：输入视图、绑定与高层输出](04_PLANNING_BRIDGES.pseudo.md)；[04：一个共同低层计划结果](04_PLANNING_BRIDGES.pseudo.md)；[03_ACTOR_DYNAMICS.pseudo.md：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)。

### 27. Goal Selector 与 planner 分工

- **状态：** `USER_CONFIRMED`（角色如何形成/选择目标不同于如何规划路径）；具体算法未定。
- **原意：** X/S/P/D、既有承诺和新事件决定“现在想做/坚持什么”；GOAP/HTN 只负责将已采用目标编成步骤，不发明人格、关系或承诺。
- **出处：** [完整机制 §3、§5.3](../../完整机制说明_v0.md)；[Q07](../../未决问题与机制候选.md#q07-commitment-的信息入口和生命周期)。
- **现码 / 缺口：** C++ `CharacterDynamicsModel::build_policy` 和 `update_persistent_intention_typed` 把部分状态/意图接至 policy；npc_system_v0 `goal_choice` 与 commitment transition 位于 model/planner 之间。一般多目标 arbitration 与 GoalSelector 协议未统一。
- **成熟近邻：** [02 Thespian/IPOCL/Sabre](../../../01_文献/算法积木/02_人物意图与约束规划.md)分别提供 utility、intent frame、belief-consent 近邻，不能互相替代。
- **接缝：** state/history → scored goal candidates + reasons → commitment transition → planner；Planner 失败不直接清除角色目标。
- **未决：** competing goals、效用/优先级、反应性抢占、目标形成与持久承诺如何分工及校准。
- **蓝图落点：** [03_ACTOR_DYNAMICS.pseudo.md：Goal Selector、Planner、Policy 与反应仲裁](03_ACTOR_DYNAMICS.pseudo.md)。

### 28. 玩家扰动后的未来局部修复

- **状态：** `USER_CONFIRMED`（玩家改变真实未来后必须承认；只改未来的修复方向已记录）。
- **原意：** 不撤销已经发生的世界/玩家事实；破坏支撑后只重规划相关未来，保护仍合法的活动、reservation 与 RunningAction progress；必要时承认目标失败。
- **出处：** [完整机制 §7–9](../../完整机制说明_v0.md)；[AuthorialTrajectoryPilot §7、§9](../../AuthorialTrajectoryPilotV0.md)；当前有限场景见[npc_system_v0 README](../../../tools/npc_system_v0/README.md)及其结果记录。
- **现码 / 缺口：** npc_system_v0 在玩家 t=3 毁钥匙后保留真实收据/绝对 deadline 并重新 forecast；有限场景直接重算未来，没有通用 causal dependency graph/局部 suffix repair。C++ RunningAction 有执行层进度保持，不是 Director repair。
- **成熟近邻：** [01 Mimesis causal threat/accommodation](../../../01_文献/算法积木/01_叙事修复与导演.md)；[02 Porteous landmark replan](../../../01_文献/算法积木/02_人物意图与约束规划.md)。
- **接缝：** committed diff → 威胁受影响因果依赖 → 选择修复 slice → 保留合法前缀/活动 → 全量 validate → 提案或明确无解/预算状态。
- **未决：** 何种图足以定位影响、何时扩大到 full replan、替代资源搜索、进行中动作冲突与复杂度/维护成本比较。
- **蓝图落点：** [04_PLANNING_BRIDGES.pseudo.md：玩家/世界变化后的局部修复](04_PLANNING_BRIDGES.pseudo.md)；[05_AUTHOR_DIRECTOR.pseudo.md：实际 Monitor 与修复触发](05_AUTHOR_DIRECTOR.pseudo.md)。

### 29. 预测未来、作者判定与已提交历史不得混写

- **状态：** `USER_CONFIRMED`。
- **原意：** rollout/LLM/planner 预测是 proposal；只有 W executor 真实结算的 event/receipt 才是历史。Monitor 对已提交轨迹给证据判断；预测成功不等于角色实际完成或鲁棒保证。
- **出处：** [ARCHITECTURE_RULES §18–27](../../../ARCHITECTURE_RULES.md)；[AuthorialTrajectoryPilot §4、§7、§9](../../AuthorialTrajectoryPilotV0.md)；[F0/F1 §6–7](../../CharacterDynamics_FormalProblem_v0.md)。
- **现码 / 缺口：** TypedIR 监测真实 snapshots/receipt；npc_system_v0 将 forecast proposals 和 committed receipts 分表，world revalidates；状态标签仍受有限 synthetic domain 限制。
- **成熟近邻：** [01 DODM rollout](../../../01_文献/算法积木/01_叙事修复与导演.md)、[03 NCP-Bench ledger](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)提供预测/提交分界相关近邻。
- **接缝：** strong types `PlanEvidence` / `ExecutionReceipt` / `MonitorResult`；proposal hash、model pins、source provenance 与当前 checkpoint 复核。
- **未决：** rollout 的不确定度/样本口径、过期提案、未知 evidence 与系统级鲁棒保证如何报告。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：实际 Monitor 与修复触发](05_AUTHOR_DIRECTOR.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：真实证据和 provenance 桥](02_WORLD_RUNTIME.pseudo.md)。

### 30. 低 LLM/运行成本与合适的抽象粒度

- **状态：** `USER_CONFIRMED`（低成本/投入产出比是目标）；“高层 LLM 按需调用”是候选而非已验证方案。
- **原意：** 不需要后台高保真模拟每秒心理过程；角色被玩家接触时，表现要与已提交历史相容。希望减少无必要 LLM 调用、作者填表和长期成本。
- **出处：** [完整机制 §1](../../完整机制说明_v0.md)；[System Vision 长期研究版图](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)。任务附件仅界定本轮范围，不作为原话或独立证据。
- **现码 / 缺口：** C++ policy 可用规则/typed local endpoint，npc_system_v0 当前不启动 LLM；没有公开的整体调用/玩家接触成本评测。
- **成熟近邻：** [03 WhatELSE / Anansi](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)与[算法积木 README](../../../01_文献/算法积木/README.md)列出不同调用职责；不是成本收益的本项目证据。
- **接缝：** 事件驱动边界、低成本 actor loop、高层按 gap/作者约束触发；对外呈现只投影与实际 ledger 一致的行为和结果。
- **未决：** 何时调用 LLM、摘要/缓存、后台时间粒度、相同体验下 token/延迟/内存/人工成本如何量化。
- **蓝图落点：** [04_PLANNING_BRIDGES.pseudo.md：缓存、异步候选与调用成本](04_PLANNING_BRIDGES.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：模拟层与表现层](02_WORLD_RUNTIME.pseudo.md)。

### 31. 玩家可感知的持续角色生活

- **状态：** `USER_CONFIRMED`（系统愿景与应用目标）；“活人感提升”尚无玩家证据。
- **原意：** 最终价值是玩家看到角色有自己的生活、经历能持续影响行动、对打断和互动作出可追溯反应，而非单纯多变量或通过内部一致性测试。
- **出处：** [System Vision 长期研究版图](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)；[研究重建审计 §玩家目标](../../研究重建审计_2026-10-06.md)。
- **现码 / 缺口：** C++ 单房间 trace viewer 能展示局部轨迹；npc_system_v0 仅有限 synthetic KeyLedger vertical slice。无开放游玩、长时程体验比较或独立玩家评估。
- **成熟近邻：** [03 Anansi/Drama Llama/WhatELSE](../../../01_文献/算法积木/03_内容绑定与LLM桥接.md)是不同叙事系统比较入口；不将论文工具研究当本项目玩家效度。
- **接缝：** 真实 receipt/actor history → presentation narrative 与 UI；呈现层不写回 W/S，不编造未发生事件。
- **未决：** 玩家可感知连续性的操作化、玩家研究设计、哪些可见迹象有价值、表达层如何适配不同时间粒度。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：模拟层与表现层](02_WORLD_RUNTIME.pseudo.md)；[06_END_TO_END_TRACES.md](06_END_TO_END_TRACES.md) 用于后续端到端可追溯例，不等同玩家效度。

### 32. 研究目标是有价值的系统集成，不要求每个模块原创

- **状态：** `USER_CONFIRMED`（用户明确要求追求有研究价值的集成系统）；贡献与效果仍待比较。
- **原意：** 成熟算法可以替换系统模块，也可以嵌在模块之间协调；系统研究要测真实组合能力、兼容性、行为效果、作者劳动与运行成本，不把“接通很多算法”直接叫原创贡献。
- **出处：** [System Vision](../../Character_Dynamics_System_Vision_v0.md)；本轮任务附件对“跨模块契约/集成骨架”的范围说明；私有原件仅按原始材料索引 hash 保持证据，不将模型补充视为用户决定。
- **现码 / 缺口：** npc_system_v0 已替换 `ContextDriveV0`/`MonotoneAvoidanceV0` 与 GOAP/GTPyhop HTN，共用有限 executor；[RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)为 DEVELOPMENT、无独立玩家/科学验证。不是“通用插件平台已完成”。
- **成熟近邻：** [01–04 算法积木](../../../01_文献/算法积木/README.md)维护算法能力和公平基线；[研究重建审计](../../研究重建审计_2026-10-06.md)维护证据成熟度。
- **接缝：** 按职责划分 Dynamics / Goal Selector / actor planner / high-level planner / Director / Monitor / executor；Adapter 做表示转换，Coordinator 做跨层时机、权限、失败传播。
- **未决：** 系统主指标与强基线、何处需新协调机制、集成工时归集、模块替换是否不改其他业务逻辑、何时可称研究贡献。
- **蓝图落点：** [04_PLANNING_BRIDGES.pseudo.md：当前可复用的接口](04_PLANNING_BRIDGES.pseudo.md)；[04：输入视图、绑定与高层输出](04_PLANNING_BRIDGES.pseudo.md)；[02_WORLD_RUNTIME.pseudo.md：真实入口与不能假装已有的部分](02_WORLD_RUNTIME.pseudo.md)。

### 33. 用加权总成本选择“最自然”的干预

- **状态：** `ASSISTANT_PROPOSAL`。
- **原意：** 旧模型回复提出把世界干预成本、角色自主性损害和作者成本写成加权目标函数；这是可讨论的形式化方向，不是用户确认的效用定义。
- **出处：** 私有来源 hash `12ef1420e1db6b580e69c149601357cc4d20a17c50e5103933add12f690b783f`，仅标识模型提案来源，不以不确定发言时点定位；[AuthorialTrajectoryPilot §9.2](../../AuthorialTrajectoryPilotV0.md)要求权限先过滤、比较规则预先冻结，不能反向证明用户采纳了该权重。
- **现码 / 缺口：** npc_system_v0 有限应用用硬约束过滤并以有限 lexicographic score 比较；没有经用户或实验确认的多目标权重。
- **成熟近邻：** [01 DODM](../../../01_文献/算法积木/01_叙事修复与导演.md)维护导演评分/目标函数近邻；不能从其存在推出本项目权重正确。
- **接缝：** 先做 authority/precondition 硬过滤，再让独立、版本化 evaluator 比较剩余 forecast；保留分项成本与 null 候选。
- **未决：** 是否需要标量化、字典序或帕累托选择；权重从何而来、如何避免“自主性”成本被目标达成抵消。
- **蓝图落点：** [05_AUTHOR_DIRECTOR.pseudo.md：World Director 是独立规划参与者](05_AUTHOR_DIRECTOR.pseudo.md)；[04_PLANNING_BRIDGES.pseudo.md：成熟方法用在哪、不能借什么权限](04_PLANNING_BRIDGES.pseudo.md)。

### 34. “Director 尚未实现”的旧 checkpoint 状态

- **状态：** `LEGACY_ASSUMPTION`。
- **原意：** 较早 `8f4fb7b` checkpoint 的“Director 未实现”是历史状态，不能覆盖当前基线 `19e5b37`：有限 Director/forecast 已在 Python app 中运行。任务 TXT 本身并未把系统缺口简化为单个格式 `Adapter`：它区分格式转换与承担跨模块时机、权限、失败传播的 `Coordinator`，并要求系统集成骨架/模块契约；此处只把旧 checkpoint 的 Director 状态标为过时，不把任务原意列作错误假设。
- **出处：** 任务附件 `pasted-text-1.txt` 中明确记录的历史 checkpoint `8f4fb7b` 与 Adapter/Coordinator 区分；当前事实以 [npc_system_v0 README](../../../tools/npc_system_v0/README.md)、[唯一 RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md) 与当前 HEAD `19e5b373303b1504b7fa46f6e01af4563947171a` 为准。
- **现码 / 缺口：** `System.world_proposal`、受限 `publish_incentive`、NO_OP 对照、真实 executor 与监测确实存在；仍缺通用多角色/开放世界 Director、高层 LLM、长时程生活和生产性 C++ 接线。
- **成熟近邻：** [01 叙事修复与导演](../../../01_文献/算法积木/01_叙事修复与导演.md)提供方法比较入口；本地算法卡不是现有实现。
- **接缝：** 保留 Python 开发纵向切片作为事实锚；把 Adapter 的数据表示转换职责与 Coordinator 的跨模块生命周期/权限/失败传播职责分开描述，通用契约仍需逐项补齐；不要把有限实现误报为通用 Director。
- **未决：** 哪些 Python 接口只属有限应用、是否将来桥接 C++ Kernel、通用世界行动目录及可审计 rollout 何时需要扩展。
- **蓝图落点：** [02_WORLD_RUNTIME.pseudo.md：真实入口与不能假装已有的部分](02_WORLD_RUNTIME.pseudo.md)；[04_PLANNING_BRIDGES.pseudo.md：当前可复用的接口](04_PLANNING_BRIDGES.pseudo.md)；[04：输入视图、绑定与高层输出](04_PLANNING_BRIDGES.pseudo.md)。

## 来源索引与当前实现核对

### 公开语义 owners

- [完整机制说明 v0](../../完整机制说明_v0.md)：W/O/X/S/P/D、动作、任务、承诺、场景和时间语义。
- [未决问题与机制候选](../../未决问题与机制候选.md)：Q01 非线性阶段消费与逆映射；Q02 X/U；Q03 替换与低耦合；Q04 `A^O`；Q05 affordance；Q06 action quality；Q10 作者约束与世界干预。**Q01 的逆映射候选与第 7 条压力非单调效应是两个不同问题。**
- [Character Dynamics System Vision](../../Character_Dynamics_System_Vision_v0.md#长期研究版图)：长期研究方向与 Kernel/Dynamics/Application 边界。
- [CharacterDynamics FormalProblem v0](../../CharacterDynamics_FormalProblem_v0.md)：F0/F1 唯一算法无关问题与执行语义 owner。
- [AuthorialTrajectoryPilotV0](../../AuthorialTrajectoryPilotV0.md)：候选 F2、TypedIR/reference 与作者轨迹预实验语义。
- [前台问题与候选创新](../../前台问题与候选创新.md)：旧 Paper-0 行为预测分支的独立 owner；不是本系统愿景的总纲。
- [当前实现进度](../../当前实现进度.md)：代码能力 owner；历史版本按记录日期读。
- [研究重建审计 2026-10-06](../../研究重建审计_2026-10-06.md)：科学证据成熟度及负结果 owner。
- [项目规则](../../../AGENTS.md) 与 [Architecture Rules](../../../ARCHITECTURE_RULES.md)：信息边界、时间、provenance、冻结 Runtime 与开发/验证纪律。

### 真实实现入口（HEAD `19e5b373303b1504b7fa46f6e01af4563947171a`）

- C++ Kernel：[`continuous_runtime.h`](../../../Demo%20codex-generated/Inc/continuous_runtime.h)、[`character_dynamics_model.h`](../../../Demo%20codex-generated/Inc/character_dynamics_model.h)、[`character_policy.h`](../../../Demo%20codex-generated/Inc/character_policy.h)、[`world.h`](../../../Demo%20codex-generated/Inc/world.h)、[`scene.h`](../../../Demo%20codex-generated/Inc/scene.h)、[`object.h`](../../../Demo%20codex-generated/Inc/object.h)、[`observation.h`](../../../Demo%20codex-generated/Inc/observation.h)、[`state_types.h`](../../../Demo%20codex-generated/Inc/state_types.h)、[`world_runtime_adapter.h`](../../../Demo%20codex-generated/Inc/world_runtime_adapter.h)。Kernel 当前 `CLOSED / FROZEN`；这些接口不是完整多角色游戏系统。
- Python 有界系统：[`tools/npc_system_v0`](../../../tools/npc_system_v0/README.md) 的 `model.py`（局部视图、X/S、目标/承诺）、`planners.py`（GOAP/UCS 与 GTPyhop HTN）、`system.py`（导演提案/forecast/actor loop）、`executor.py`（W 权限、时钟、RunningAction/receipt）、`author.py`（TypedIR monitor）；唯一结果见[NPC System Integration v0 RESULTS](../../../02_实验/NPC_System_Integration_v0/RESULTS.md)。
- 既有独立基础：[`tools/e0_keyledger_v0`](../../../tools/e0_keyledger_v0/README.md)、[`tools/e1_keyledger_v0`](../../../tools/e1_keyledger_v0/README.md)、[`tools/trajectory_constraints_v0`](../../../tools/trajectory_constraints_v0/README.md)。不能将三个原独立工具的旧描述直接当作当前总系统能力；npc_system_v0 是其上的有限新集成。

### 来源原件与状态冲突说明

- 2026-10-09 目标讨论公开索引：[原始材料 README](../../../90_原始材料/README.md)，私有原件 hash `12ef1420e1db6b580e69c149601357cc4d20a17c50e5103933add12f690b783f`。只按用户直接发言确认方向；模型在同一导出中的架构、命名、公式与文献陈述均不自动算用户决定。
- 2026-10-07 稀疏作者约束用户/模型原始讨论 hash `d5bf60647c08dc517ad737cb1d132d03dcef946f57f0c80be331f9ee641371f8`，角色区分见[公开来源说明](../../../90_原始材料/2026-10-07_WebGPT_稀疏作者约束与世界干预/README.md)；用户确认“关键节点可要求角色变化、主要经世界干预促成其合理过程”，但模型另提术语不得混入该确认。
- 当前源码事实与以上旧材料冲突时，以本 HEAD 的源码及对应结果 owner 为准。比如任务附件开头引用 `8f4fb7b`、称 Director 未实现，是较早 checkpoint 结论；当前 `19e5b37` 已有有限 `npc_system_v0` Director。反过来，README 的有限执行结果也不能外推成通用 Director、C++ 集成或长时程生活。
