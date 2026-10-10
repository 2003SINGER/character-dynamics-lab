# 第一阶段：把 NPC / 作者控制研究拆到算法层

更新：2026-10-11（研究问题路由与方法角色映射）。**算法文档交付仍为 READY_FOR_INDEPENDENT_REVIEW；本轮未选新方法、开发导演或运行新实验。**下文的源码接缝表保留其注明的历史核对版本，不描述当前全仓能力；已有 P5 等有限实现只查各自结果 owner。本页是算法积木的唯一维护入口；逐篇计算只在三份卡片维护。后续[04 统一问题与成熟基线准入](04_统一问题与成熟基线准入.md)只将已有机制映射到 F0/F1、审查强基线与候选问题，不是并列系统总纲。

## 0. 本阶段要得到什么

用户确认的长期问题是作者部分约束下游戏世界合理、可执行未来的在线规划与控制；完整问题定义只见 [F0/F1](../../00_研究设计/CharacterDynamics_FormalProblem_v0.md)。本页仍只拆文献算法与候选接缝，旧 C++ OHXSP 不构成游戏通用 schema。LLM × 成熟规划是研究主轴候选，可覆盖语义、因果候选、grounded 绑定、层次细化和反馈修复，不要求每层都使用 LLM；层次、联合或混合候选组织未冻结。下一候选研究动作（尚未启动）是做有界最强近邻机制对照并选择一个可检验未知数；这不是新文献综述、方法或实验授权。原构想见[原始阅读判断](../../90_原始材料/2026-09-01_动态人物世界模拟探索/阅读判断.md)。

完整候选研究方向由[System Vision 长期研究版图](../../00_研究设计/Character_Dynamics_System_Vision_v0.md#长期研究版图)维护。本页拆的是技术方法和组合接缝，不等于研究对象清单，也不限缩为近期 A/B 或 Q1–Q3。

## 方法在全系统中的角色（仅按现有卡片证据）

以下是检索与对照用的角色映射，不是新算法认证或整合方案：意图/因果可解释性可对照 IPOCL 与 Sabre；层次化行动计划参照 HTN；因果链生成参照 WhatELSE；Mimesis 对照因果依赖修复，DODM 对照有限导演动作搜索与价值评估；作者时序约束监测参照 PDDL3 与本地 TypedIR；最终动作仍由游戏原生执行器结算（现有平台可看 Evennia）。具体定义、适用条件与未核验项以各方法卡为准。NCP 仅按卡03已覆盖的原件版本结论使用，不认证新出口年份或扩展版本；STORY2GAME / Dramamancer 新引文待核验。

两份新讨论分别提供九阶段路线与旧仓库 `4a44ee2` 的复核；其中的模型提案不是已实现事实。原文完整私有归档、清理可恢复，见[原始材料索引](../../90_原始材料/README.md)。本页按当前 checkout 核对接缝，不以旧 snapshot 宣布新能力。

**第一阶段验收单位不是“读过一篇”，而是能回答：输入具体是什么 → 用什么内部对象 → 哪个条件触发 → 搜索/更新的次序 → 输出具体是什么 → 无解时怎样停。**原件未披露的内部程序必须写未知；自制手算例只用于讲解，不算论文实验或运行证据。

| 算法卡 | 内容与可复算位置 |
|---|---|
| [01 叙事修复与导演](01_叙事修复与导演.md) | Mimesis 因果威胁及版本权限；DODM 的 SAS+ / TD / SASCE；玩家动作的 PDDL→PPDDL 转换 |
| [02 人物意图与约束规划](02_人物意图与约束规划.md) | IPOCL intent frames；Thespian fit / gap / belief suggestion；PDDL3 轨迹语义与 Porteous 地标规划；IDG 图扩展 / Jaccard；Sabre 辅助基线 |
| [03 内容绑定与 LLM 桥接](03_内容绑定与LLM桥接.md) | Anansi query binding / dispatch；WhatELSE 固定动作编译；Drama Llama 有序触发；DiriGent tension / enforcement；NCP 外部核验与提交 |
| [04 统一问题与成熟基线准入](04_统一问题与成熟基线准入.md) | 同一钥匙—账本实例下的能力/权限边界、最小成熟基线、可反证的研究候选；综合审查，不新增原算法卡 |

12 张主卡均使用 17 个字段：Problem、State、Author input、Character input、World model、Control authority、Planner/search、Trigger、Repair、Can change、Cannot change、Handwrite、Old cost、LLM replace、LLM must not replace、Evaluation、Failure。PDDL3 与 Porteous 在同卡中分清规格/算法；Sabre 为辅助简卡。旧报告、原件、固定源码版本和阅读覆盖保留在每卡来源栏；**17 字段填齐不等于源码都已核、全部论文都已复现。**

## 1. 到底有哪些算法可以搬到哪里

本表的“放在哪”是**候选用途**，不是选型决定或当前实现。`有基础` 只表示能提供部分输入；`缺` 表示尚无该机制。行号是可引用的机制 ID，不是功能需求编号。

| ID / 可拆算法 | 具体输入 → 运算 → 输出 | 候选用途 | 当前项目可接什么 / 还缺什么 | 必须守住的边界 / 细卡 |
|---|---|---|---|---|
| M1 因果链威胁检测 | `producer --p--> consumer` + 当前步 `a`；检查 producer 已发生、consumer 未发生、a 能在区间内执行且 `¬p∈effects(a)` → 返回被威胁 links | 玩家改变世界后，定位“未来哪一段失去了什么支撑”，不是笼统判偏剧情 | 有 typed outcome / 时间；缺通用 pre/effects 与 causal-link graph，不能从 trace 文本自动视作已建图 | 只检测，不恢复事实；[卡01](01_叙事修复与导演.md#卡-1mimesis-mediationcausal-link-threat--accommodation--intervention) |
| M2 future accommodation | 已执行 prefix + 异常动作实际后态 + 保留目标 → 重规划未执行 suffix → 新未来或无解 | 成功破坏之后找替代支持路径 | 有当前 W、历史证据；缺通用域/replanner/未来计划对象 | 执行过的动作不回滚；2003 未给内部搜索细节，不能包装成现成高效算法 |
| M3 intervention / latent-history edit | exception → 预置 failure mode；或 2013 按 knowledge model 删除确定未观察的过去步再 POCL 搜索 | **权限对照**：玩家结果否决、未见前史改写与 future repair 三者分别比较 | 当前代码无这种导演权限；不能因事件有 source 就默认允许 | 这是不同版本/权限，不默认采用，也不与保留成功结果混称 M2 |
| D1 SAS+ expectimax | 合法 DM actions 含 null；DM 节点 max，玩家节点按给定概率加权；cutoff 采样 K 条完整续篇并均值评分 → 根部 action | 作者全局偏好下的有限 lookahead 导演基线 | trace 可供 recognizer；缺 plot-point/prereq/action/refiner/player model/J | 高分针对作者函数，不等于玩家活人感；[卡01](01_叙事修复与导演.md#卡-2dodm全局-plot-history-上的优化导演sas--td--sasce) |
| D2 顺序编码 + TD value | `M[i,j]=1` 若 i 在 j 后发生；模拟故事终局 J 反向更新 value approximation；选择估值最高合法后继 | 若以后要学习“未来叙事价值”，可用顺序编码而非仅 count | 有事件时间；缺点级 encoder、训练域和经确认的 reward；旧预测训练不是这个 TD policy | 不把训练出的作者函数值写成客观心理质量 |
| D3 SASCE 玩家分布 | 下一状态估值、α 合作/对抗参数、hint β → normalized exponential 分布 → 训练采样 | 系统地生成合作/对抗未来，暴露导演短视 | 缺领域模型和 state-value；没有真人概率校准 | 仅模拟训练策略；不能称测得玩家选择概率 |
| C1 IPOCL frame / flaw refinement | partial plan + causal links + `intends(actor,g)` + frame members；补 open condition/motivation、分支纳入/排除、排除 threats → explained plan 或回溯 | 把“谁为了什么做这步、由何事产生动机”变成结构约束 | 当前 TaskCommitment 有持久状态；缺 plan frame/motivation support，二者不可直接映射 | 集中式离线构造≠自主 NPC；[卡02](02_人物意图与约束规划.md#卡-1ipocl因果计划与-intent-frame-支持链) |
| C2 Thespian prefix fit / reward fitting | 固定模型推演 `b_obs,b_alt` → `θ·(b_obs−b_alt)≥0`；违例逐坐标求 Δ、保留符号、取最小单权重变化，无解再试双权重；外层逐角色/前缀 fit → 首失败 gap | 诊断作者示例是否能由人物偏好解释，定位桥接缺口 | 缺特征奖励、期望推演和联合 fit solver；已有 policy 不等于该拟合器 | 2004 基础原式及数字手算已核；2008 完整实现未知；改 weights ≠只改环境；[卡02](02_人物意图与约束规划.md#卡-2thespian--pop2008fitgapbelief-suggestion-与作者造桥) |
| C3 islands bounded bridge search | gap 两侧锚点 + 分级动作集 + 长度上限 → 按顺序约束递归 append、complete 后 fit → bridge 或失败 | 优先复用现有域动作，失败才请求作者补内容 | 当前动作库不是通用 narrative operator 集；缺岛序、搜索状态及 fit | action-set 扩展和长度都须记账；不能把新 operator 混入原库搜索成功 |
| C4 Suggest_Pick → 作者造桥 | gap 状态 + 指定下一 action → belief-change suggestion；一层他人回应 lookahead → 他人的 suggestion | 将“应获得什么信息/动机”转成**事件候选的需求** | 有 O 的事实来源；缺反求算法、信念效应模型和多角色 lookahead | suggestion 不直接写 O/S；事件主体、知情与效果另验证 |
| P1 PDDL3 trajectory monitor | 时间戳 states + 公式；`sometime-before φ ψ` 对每次 φ 找更早 ψ，`within d φ` 找 d 内见证 → 满足/违反/偏好成本 | 分别约束世界、知识、承诺、剧情的持续轨迹 | 当前已有独立 typed reference evaluator/monitor；尚缺与生产轨迹/作者输入的生产绑定，不能声称已在生产 W/O 上监控 | 公式监测不负责让目标可达；绝对期限不可重规划时重置；逐论文未知仍按来源卡记，不以本项目 reference 倒推论文算法；[卡02](02_人物意图与约束规划.md#卡-3pddl3-轨迹约束规格--porteous-2010-地标-ff-重规划) |
| P2 地标 DAG + FF 子目标 | 当前符号 state + landmark order → 选当前适用节点，FF 求当前段；状态变后重查/重规划 → 下一步计划 | 把长程作者要求拆成当前段的强传统基线 | 有实际 W；缺符号域、节点适用/访问与 FF 接口 | “不适用”与“不可达”不能随意等同；局部求解不保证全局最小 repair |
| G1 SPG / PH → IDG | literals/action layers + goal graphs；precondition 的 possible-history 组合传播，合并角色目标 label → goal dependency exemplars | 显式说明新未来依赖哪些人物目标 | trace 不是 PH/IDG；缺 goal graphs 与构图器 | SPG 无 mutex，有潜在不可执行 exemplar；下游要验证；[卡02](02_人物意图与约束规划.md#卡-4idgaiide-17-workshop-2017spg-层扩展与-goal-set-jaccard) |
| G2 目标集合 Jaccard | 两组 `〈actor,goal〉` → `1−intersection/union` → 排序值 | 在**已合法候选**中比较改变了多少目标标签 | 当前 commitment 只跟踪有限 task；不是完整 goal set | 不衡量心理距离、时序或可达性；不能代替人物连续性评测 |
| G3 玩家选择 → PPDDL | grounded player operators → 前提交/差区域；region 启用 k 个动作则按 choice model 给 k 个 effects 概率 → 概率域/policy | 把不可控玩家选择与系统可控动作分开建模 | 有单次typed结算记录/validation；没有概率分支转移，缺声明式域、player model 与 MDP planner | 可控动作不自动保证动机；均匀分布明确只占位；[卡01](01_叙事修复与导演.md#卡-3narrative-mediation-as-probabilistic-planning2017把玩家选择转成-ppddl-outcome) |
| S1 Anansi query binding | storylet query + DB → 枚举每组合格 role binding → 可播放 instances | 同一作者内容换合法演员/地点，不逐 NPC 重写 | 有有限 O/world facts；缺 social DB/关系/Ink runtime | 通用查询绑定有作者语义成本；[卡03](03_内容绑定与LLM桥接.md#1-anansi作者编写的-storylet--社交模拟) |
| S2 weight / cooldown / dispatch | eligible instances → weighted select → Ink choice → social-event roles/preconditions/effects | 内容节奏与社会后果分离 | 缺通用社会事件执行器、repeatability/cooldown bookkeeping | 查询通过不代表 event effects 都合法；未核 rollback/fallback 不猜 |
| L1 WhatELSE 固定域 compiler | outline event + current W + 六动作 schema → action sequence → reviewer / 环境反馈 → 修订候选 | 替作者填写抽象事件之间的具体动作桥 | 有有限 typed action、W validator；缺 compiler及其事务/试执行接口 | `save` 文本不等于新增世界能力；不能让 narrator 自报成功；[卡03](03_内容绑定与LLM桥接.md#2-whatelse抽象事件固定-action-schema真实执行反馈) |
| L2 DiriGent tension / enforcement | ideal worlds + beats → tension ledger；4候选的 tension-ID 集合求和 argmax；停滞后插 required action 或 world prompt | 研究角色候选选择/引导的近邻，不当通用 world-only repair | 有 typed S/policy；不是文中 tension model，不能硬凑字段 | 原公式符号歧义保留；注入候选属于角色通道；[卡03](03_内容绑定与LLM桥接.md#4-dirigenttension-驱动角色候选与停滞-enforcement) |
| L3 Drama Llama ordered triggers | script + ordered active triggers → 逐条 YES/NO，首个 YES 消耗其下一 action，Ending 停 → stage direction | 自由文本对话中保留作者转折点 | 可以作文本层对照；缺 trigger runtime | 没有结构化 W truth；只能称文本判断，不是已结算事件；[卡03](03_内容绑定与LLM桥接.md#3-drama-llamacondition-first-的文本-storylet) |
| E1 NCP projection / commit / terminal | pending opening + reply → conflict先验；无冲突再投影facts、查trajectory、查commitment、commit → terminal | 外部一致性诊断，尤其区分待提交和已提交事实 | 现有 trace 可审计；尚未接 StorySpec/runner，也未跑 bench | 原冲突终止不能改成修复后续跑再报原 survival；[卡03](03_内容绑定与LLM桥接.md#5-ncp-bench外部-judgeterminal-协议不是-controller) |
| B1 Sabre belief / consent explanation | action 可执行；每 consenting actor 在其 belief 内把 action 当作提升 utility 的计划首步 → author utility 提升的完整 plan | 信念+意图兼顾的集中式强符号基线 | 有 stale O，但没有嵌套 belief planner/utility domain | “每步可解释”≠独立 agent 自主；[卡02辅助基线](02_人物意图与约束规划.md#辅助基线sabre集中式意图信念规划简卡) |

**不是只保留上述论文。**先前 CiF 的条件评分/社会 exchange effects、Praxish 的 activity binding 与一步 consequence utility、FAtiMA 的 appraisal/决策层、GOAP/HTN 的规划有效性与进行中动作均有[上一轮算法拆解](../算法拆解_NPC方法与生产系统_2026-10-07.md)。这些是不同模块的候选资产，不因本轮研究作者控制就删除。尚未达到同等拆解深度的模块继续保留阅读等级，不能在表里补一行“已有万能框架”。

## 2. 各种系统谁读什么、谁能改什么

这里比较**原方法权限**，不是我们批准的权限。当前项目的未来权限尚未选型。

| 系统 | 控制器实际读取 | 能改变的对象 | 角色局部信息如何处理 | 过去 / 未来边界 |
|---|---|---|---|---|
| Mimesis 2003 | 全局 plan、causal links、执行位置、用户动作 | accommodation 改剩余计划；intervention 替换玩家动作结果 | 不是完善 actor-local O 模型 | accommodation 保留已执行；intervention 在执行前截获 |
| 知识中介 2013 | POCL + possible-knowledge DB | 未观察前史和未来计划 | 保护其知识模型判定的已观察内容 | 允许受限隐史编辑；不得混入 future-only |
| DODM | plot history、可用 DM actions、player probabilities、J | cause/deny/hint/agent requests / refiner 世界操作 | 概率模拟玩家，不是完整人物私有 belief | 控制点级未来可达性；不是通用历史修复 |
| IPOCL | 符号域、initial/author goal、角色目标与 frames | 搜索中的 plan/links/orderings/motivations | 没有 actor-local belief | 离线计划构造，没有提交历史契约 |
| Thespian + POP | skeleton 与各角色 goal weights/beliefs/dynamics | fit 可改 weights；gap 可加已有 action；建议 belief effect | 有递归人物模型；作者仍补导致变化的事件 | 创作期 fitting/桥接，非任意 runtime retcon |
| PDDL3 / Porteous | 轨迹公式 / 全局符号state+landmark graph | 规格只判定；规划器改变未来路径 | 状态可含关系/视角，但非通用局部认识模型 | 当前态重规划；公式不能保证修复 |
| IDG / probabilistic mediation | goal graphs/PH / grounded choices与概率模型 | 构图/标签；或 policy 系统动作 | 前者无连续心理；后者无经校准玩家认识模型 | output 是候选或 policy，不回滚执行事实 |
| Anansi | social DB、queries、Ink变量、日程 | instance binding、社会事件 effects | query资格不等于人物知情；需作者另建模 | 内容/关系状态推进；没有通用 causal repair |
| WhatELSE | outline、角色描述、当前 world/memory | 固定 schema 内动作实现与后续具体剧情 | 拿到 current W；不自动满足我们 O-side 限制 | environment 是状态权威；trial/commit事务细节另记未知 |
| DiriGent | 完整 beats、ideals、active beliefs、tensions | world prompt 或 required-action候选；文本 beats | prompt隔离≠硬局部信息校验 | 无独立游戏世界 executor |
| Drama Llama | 全 script + setting/cast | stage-direction 文本、trigger index | 全文本上下文；无结构化信息权限 | 无真实历史 validator |
| NCP-Bench | 外部 committed/pending ledger、回复与规格 | evaluator/checkers 更新 ledger；runner终止 | 被测模型不能接管 checker | conflict 不提交本轮，不自动 repair |
| Sabre | 全局 world + 嵌套 beliefs + utilities | 唯一 planner 生成可解释完整计划 | actor consent 在其 belief 内检查 | 集中式规划，不是多NPC自治 |

不能从“都有 state / goal”推导互换：`WorldTask` 是世界任务，`TaskCommitment` 是角色持久 task 状态，IPOCL frame 是**计划解释结构**，NCP commitment 是**外部评测要求**，作者 future constraint 是**尚待定义的控制输入**。这五种对象必须先画映射，再谈复用。

## 3. 当前仓库已经提供什么，什么还没有

代码接缝核对基线为 `webgpt-sync@ed1c7a7b8e1b12c3d4cec87b977ddd129666cc5e`，依据本轮实际读取 `Demo codex-generated/Inc` 与 `Src`；未提交的 paired-harness/CMake 工作不作为本轮能力证据。以下不把设计愿景视为代码事实。

| 真实能力 / 文件 | 能支撑的接缝 | 不能推出的能力 |
|---|---|---|
| [world.h](../../Demo%20codex-generated/Inc/world.h)：WorldTask、validate_runtime_start、settle_runtime_completion、advance_runtime_by | typed任务/动作结算、世界硬校验 | 没有通用 PDDL domain、causal-link graph 或 narrative planner；有限 actions不是任意新增算子 |
| [observation.h](../../Demo%20codex-generated/Inc/observation.h)：Known/Stale/Unknown、InformationAccess、feedback、O-only rebuild | 角色不知道某真实变化仍可按 stale O 行动；反馈后修认识 | 不等于任意关系/多主体知识或 nested belief database |
| [state_types.h](../../Demo%20codex-generated/Inc/state_types.h)：固定状态字段、TaskCommitment | 持久压力/身体状态与 task intention 消费 | 没有关系矩阵 R / trust 字段；不能写 `trust_B=0.3` 当现行 API |
| [character_policy.h](../../Demo%20codex-generated/Inc/character_policy.h)：select 读 decision/O/S/P/history/running | 候选政策/模型共享执行核、信息边界可审 | 没有 Thespian 权重反求或 Sabre consent-plan search；已有接口≠方法已经训练 |
| [continuous_runtime.h](../../Demo%20codex-generated/Inc/continuous_runtime.h)：boundary、intent、pre/post outcome、trace | 记录发生的时间、选择、验证、后果；研究回放素材 | 不自动产生 future constraint / dependency graph / repair controller |
| [WorldRuntimeAdapter](../../Demo%20codex-generated/Src/world_runtime_adapter.cpp)：按 scheduler Δt 推 World | 单时钟上的实际世界变化和观察反馈 | `WorldEvent.source` 主要是来源描述；`schedule(event)` 不等于通用受校验的世界干预指令。不能只造“桥坏了”事件文本就令 W 真有桥且损坏 |
| Runtime actor history 是有限滚动历史；typed trace 可导出 | 事件/动作 provenance 的局部依据 | 内存 history 不是完整不可变审计账本；新实验仍须保留 raw traces / 配置 / 状态版本 |

因此不是“把导演类插进 execute_next_boundary 就结束”。先要定义 planning-domain adapter、事件/状态谓词绑定、可控权限和真实 execution/refiner。**本轮不改这些接口，也不重开冻结 Runtime。**若后续证据要求改接口，另行列明授权与验证；不把冻结当永久禁止研究。

## 4. 一个贯穿手推：借到钥匙后被毁，怎样保留事实并重新找路

以下是本页**自制纸面域**，不是现有房间 Demo、论文原例或新增实验。目的是让各算法的职责差别显形，不能把一张讲解轨迹拿来证明它们已可组合。

### 4.1 明确状态与有限算子

时间 0：A 已从 B 借到 `key0`，此前成功 `lend(B,A,key0)` 进入历史。作者未来要求 `holding(A,ledger) @ t≤10`。现在 t=2，玩家实际成功执行 `destroy(key0)`。世界里 B 另有备用 `key1`，A 尚不知道；B 想拿回 A 借走的工具。人物目标在本例明确给定，不是由论文猜出来。

| 操作 | 前提（本例手写） | effect / 用时（本例手写） |
|---|---|---|
| tell_spare(B,A) | colocated(A,B) ∧ knows(B,spare) | message 已送达后 `knows(A,spare)`；1 |
| return_tool(A,B) | holding(A,tool) ∧ colocated(A,B) | holding(B,tool), ¬holding(A,tool), returned(tool)；1 |
| lend_spare(B,A) | holding(B,key1) ∧ returned(tool) ∧ colocated(A,B) | holding(A,key1), ¬holding(B,key1)；1 |
| unlock(A,key1) | holding(A,key1) ∧ key1_intact | open(archive)；1 |
| take_ledger(A) | open(archive) ∧ ledger_inside | holding(A,ledger), ¬ledger_inside；1 |

当前实际 W：`¬key0_intact, ¬holding(A,key0), holding(B,key1), key1_intact, holding(A,tool), ledger_inside, ¬open(archive), colocated(A,B)`。本例 destroy 同时删除 intact 与 holding。实际认识：B 知备用钥匙，A 不知。旧 future `unlock(A,key0)` 已不可执行。这里把 `knows` 写为纸面谓词只是为展示主体区别；真实认识更新需观察机制，不允许把导演知道直接复制给 A。

### 4.2 每一步由哪个算法做什么

1. **W 先结算，不审判成功结果。**t=2 已提交 destroy(key0)；不得删 lend 或 destroy 的记录。无“原钥匙其实没毁”分支。
2. **M1 定位断链。**旧 unlock 有两条支持：`initial --key0_intact--> unlock(key0)` 与 `lend --holding(A,key0)--> unlock(key0)`；destroy 删除二者 literal，所以都失去支持。intact 由初态提供，不能误记为 lend 新建。若旧 schema 只检查 held 不检查 intact，暴露的是作者模型错误，不是 search 不够强。
3. **P1 监测与可达性分开。**t=2 尚未超过10，`within(10,holding(A,ledger))` 还可能满足；monitor不能仅因原路线坏了宣布永久失败。反过来，没超期也不代表可达。
4. **M2/FF 的全知可达性候选。**当前 W 下 `return_tool → lend_spare → unlock(key1) → take_ledger` 4分钟后达成，逻辑上 t=6≤10。这是全知条件下的可达性下界；分配给自主actor时尚未解决A为何知道备用钥匙、B为何愿借。全知计划不是自动可信角色行为。
5. **C1 / B1 检查人物解释。**A 的目标是拿 ledger，归还工具若服务借钥匙可成为支持动作；B 的目标是回收 tool，lend_spare 若事先交易约定支持这个目标才有解释。只写旁白“B 很愿意”不形成 frame/consent-plan。若本例没有给 B 交易动机，必须标解释缺口。
6. **C2/C3 暴露并补信息桥。**在固定纸面人物模型中规定 A 不知道 spare 就不选择相关借钥匙行动，则原 skeleton 首失败在此。现有域有 tell_spare；允许搜索 `tell_spare → return_tool → lend_spare → unlock → take_ledger`，拟合/检查通过才叫现有库桥接。我们没有运行 Thespian，因此这里仅展示其输入/返回应是什么。
7. **真实执行顺序。**t=3 消息送达产生 A 的 O 更新；t=4 归还工具结算；t=5 B 借出备用钥匙；t=6 开门；t=7 取 ledger。每一动作在当时状态重新校验；t=2 不能提前写 `knows(A,spare)` 或 `holding(A,key1)`。
8. **D1 做选择，不做存在性证明。**若还有“直接给另一份 ledger”的合法 DM action，才可按其效果/玩家概率与 null 比较期望；评价函数和操控注释由作者给定。不能用上面路径存在就推得 SAS+ 会选它。
9. **L1 只能实例化既有能力。**LLM可提这五步与前提；如提“钥匙自己复活”，在固定域里没有该 operator，则拒绝/报告需作者新建。Anansi 可绑定另一位真正有 spare 的 actor，但查询不会创造 spare。
10. **无解反例保留。**若真实 W 中唯一 spare 也毁了、没有 alternative ledger/入口，且 domain不许新增对象，则本例 finite domain 没有路径；只可报告无解、放松作者目标需授权、或另设干预权限。不能默默 retcon 成功历史。

**哪些能组合，哪些不能直接拼？**M1 输出 broken links；M2/P2 输出 candidate future；C1/B1 校验解释；P1 判轨迹；L1 提候选实现。这些输出类型有可能对齐。DODM 的期望分数、Thespian fitted weights、IDG Jaccard、DiriGent tension 不是同一个数，也没有统一单位，禁止直接相加成“活人感 objective”。

## 5. 真正拼接前，必须补齐的五份契约

| 接缝 | 必须精确说明 | 不说明会怎样 |
|---|---|---|
| 状态投影 | 哪个 W/O/task/关系字段对应每个 planning literal；谁观测、何时更新、Unknown如何处理 | 全知 planner 的 facts 泄漏给角色；同名 goal 误映射 |
| 动作域 | typed action → grounded operator 的 pre/effects/duration；失败/打断部分效果；新增 operator 审批 | 计划可行但游戏没有这能力；被中断进度凭空消失 |
| 时间与事件 | 实时时间/剧情序数；持续状态还是一次性事件；绝对deadline；已提交prefix | 同一 fact 多次当触发；replan 续期；“已规划”冒充“已发生” |
| 权限 | 谁提出候选、谁校验、谁执行；可改目标/策略/世界/隐藏历史分别授权 | 角色“自主”实际上导演强制；世界编辑被伪装成自然更新 |
| 评价 / 成本 | 可执行性、角色解释、作者审阅/编写/调试、推理量分开；原 benchmark协议固定 | 少写剧情却多调试；自有judge优化证明自有judge |

这些接口问题在后续用户授权的[AuthorialTrajectoryPilotV0](../../00_研究设计/AuthorialTrajectoryPilotV0.md)中具体设计；原算法与机制卡仍由本页维护。设计reference语义不等于已实现Director/关系模型，更不代表哪些接缝已有研究收益。

## 6. LLM 应替代哪段手工劳动：按产物记账

| 手工工作 | LLM 候选产物（待验证） | 后续必须检查 / 净成本 |
|---|---|---|
| 写状态谓词/事件 recognizer | 字段绑定与事件判定草案 + 正反例 | persistent vs event、信息权限、gold labels；人工复核/维护时间 |
| 写前提/效果和 domain | typed operator 草案 | 实际执行语义、失败/时长/资源、license；新增实现与测试成本 |
| 从 gap 想一个信息/动机桥 | 带 actor/pre/effects/来源的若干事件候选 | actor 是否知道、愿意、能执行；没 operator 就记录作者新增，不装自动完成 |
| high-level action 到 refiner | 固定动作序列，逐步前提缺口 | 真 validator / 试执行隔离；reviewer不能给自己提交W权限 |
| 选角色/地点 | query / binding 候选 | 查询必须返回真实符合条件的实例；LLM 叙述不创造实体 |
| 判断 coherence / explanation | 附证据的软 critique | 与执行成功、人工玩家判断分列；模型 consensus 不是独立人评 |

因此“LLM 替作者干活”只是可用手段；用户要检验的是框架是否减少**逐情境分支与维护负担**。未测 authoring+debugging+review+runtime 总成本前，不宣称低成本已经解决。

## 7. 每部分留给用户的新理解

下面全是本人待补栏；当前已有确认只有：世界中心、允许作者控制、不要逐情境补丁、先具体吃透方法再组合。模型不能把自己的接缝建议改写为“我的新理解”。逐卡也有对应留白。

### A. 世界因果 / 历史权限（M1–M3、G3）

- 我的新理解：____
- 我想保留 / 不采用的机制与理由：____
- 我认为能放在系统的哪层，缺哪个输入：____
- 一个让我改变判断的反例：____

### B. 作者偏好与人物意图（D1–D3、C1–C4、B1）

- 我的新理解：____
- 权重拟合、动机补足、世界引导三者怎么区分：____
- 哪些改动需要作者明确授权：____
- 我想追到源码的下一条：____

### C. 持续轨迹与依赖（P1–P2、G1–G2）

- 我的新理解：____
- 我想约束的具体谓词 / 时间 / 硬软边界：____
- monitor 知道什么，planner 还缺什么：____
- 我不接受的“标签距离代替人物连续性”：____

### D. 内容复用 / 生成 / 外部验收（S1–S2、L1–L3、E1）

- 我的新理解：____
- 我希望自动化的手工产物，而不是笼统说生成：____
- 由谁建立事实，失败后能否修复：____
- 我怎样算总劳动，而不只算写字数：____

## 8. 九阶段路线：本轮做到哪里

这里保留第一阶段交付时的长期路线，不是旧continuity pilot的阶段1–3。**后续状态由[AuthorialTrajectoryPilotV0](../../00_研究设计/AuthorialTrajectoryPilotV0.md)维护：用户已授权设计四份契约与独立reference，没有授权E0–E5执行。**下表的“尚未冻结”描述原阶段快照，不作为最新下一动作。

| 阶段 | 目标 / 本轮状态 |
|---|---|
| 1 方法地基 | **本轮文档交付**：17字段卡、具体机制表、权限矩阵、手推与未知项。用户复述/修改理解尚未验收 |
| 2 约束对象 | 从理解里选谓词/投影/时序语义；尚未冻结；不能与现行 appraisal X 同名混用 |
| 3 权限与接口 | 明确 future-only / world edit / character influence / author override；尚未选型 |
| 4 最小可执行世界 | 选择同域与扰动；还没授权新的微世界实现 |
| 5 简单候选机制 | 优先明确候选、有限 rollout、约束与成本；未决定训练/RL或新Director |
| 6 强近邻比较 | WhatELSE、传统规划等认真匹配域/权限/成本，而不是把近邻弱化 |
| 7 外部诊断 | NCP协议若采用须固定版本、区分原terminal与新增repair实验；未运行 |
| 8 可验证问题 | 从实在失败得具体问题；允许已有方法够用、没有新方法gap |
| 9 系统 / 研究分线 | 系统可持续扩展；每次研究只验证有界贡献；不以demo吸引力保证发表 |

**尚未收口的知识项：**Mimesis 2003 replanner 内部细节；Thespian 跨序列联合拟合/2008 完整实现与 belief-side Suggest_Pick 求解程序（2004 奖励权重不等式及单/双坐标基础已核）；Porteous planner失败时完整恢复逻辑；Anansi事务/失败fallback；WhatELSE trial/commit细节；DiriGent scoring符号；各系统总作者成本与玩家长期效度。未知项不以空泛句补齐，也不阻止已有明确算法先被理解。

**当前状态与下一动作只由[TODO](../../00_研究设计/TODO.md#active)维护。**[04](04_统一问题与成熟基线准入.md)维护有限实例的基线综合与研究准入判断；四份契约与候选 E0–E5 仍由[设计 owner](../../00_研究设计/AuthorialTrajectoryPilotV0.md#13-交付-traceability-与下一实施边界)维护。本人手推/新理解仍可在各卡补充；不自动运行 NPC 实验、开发 Director 或声明创新。
