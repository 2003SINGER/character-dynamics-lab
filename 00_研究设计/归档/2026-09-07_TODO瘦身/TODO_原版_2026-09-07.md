# TODO

> 2026-09-06 代码结构审计后的实验化边界：`prepare_decision` 已与 `settle_action` 分开，运行轨迹记录统一命名为 `StepRecord`；`FactKey` 与 `known_int/known_bool` 已提供最小 typed 读取。World/Decision/State 暂不做大拆分；verify/E0 的物理 tests/experiments 目录迁移留到真实 replay 需要时再做，不阻塞 T0d。

更新时间：2026-09-07（Theory-S 结果边界复核后）

这是唯一行动清单，不保存整篇设计论证。“待决策”不等于授权实现；以下次序是依赖建议，没有新增用户 deadline。代码项仅在其边界、验收和实际状态可复核时更新。

## 2026-09-07 主线纠偏：先验收机制表达力，再做正式实验

来源原件：[Theory-S 与机制纠偏对话](../90_原始材料/2026-09-07_用户对话_Theory-S与机制纠偏/README.md)。

- [x] **M0 mechanism sandbox（工程 sanity 完成）**：固定 Scene/O/P/generated `A^O`，在 5 个 LIGHT development fixtures 上做 `do(S=s_1)` / `do(S=s_2)`；结果显示 π 改变且 support 不变。结果不是现实数据机制证据，见[Mechanism Sanity v1](../02_实验/Mechanism_Sanity_v1/README.md)。
- [~] **M1 Theory-S trainable dynamics candidate**：已把每字段 relaxation、T14/T20 readout 与多步 candidate-NLL gradient smoke 合并为可训练参数化；X/S semantic contract、真实参数拟合与外部预测有效性仍未冻结/验证。见 [Theory-S v2](../02_实验/Theory_S_v2/README.md)。
- [~] **M2 minimal candidate compiler**：从 canonical SceneSnapshot 的 objects/agents/possessions/facts 独立生成带 provenance 的 affordance 与 `A^O`；生成后才做 source `available_actions` support hit/miss。当前 ontology、实例绑定和前置条件仍是最小 development slice。
- [~] **M3 dataset→capability matrix（路由版）**：已按 owner audit 登记 LIGHT、OPeRA、ClubFloyd、FarmQuest、PowerWash、AGAIN、SOTOPIA 的字段能力与阻塞项；不是准入或识别结论，仍需各自 semantic audit，见 [capability matrix](../02_实验/Theory_S_v2/capability_matrix.md)。不得把 source `available_actions` 当作 `A^O`。
- [ ] **M4 formal experiment gate**：M0–M3 未完成前，Run1–4 仅保留为 development identifiability diagnostics，不启动正式 test 或把结果写成 Theory-S 结论。
- [x] **M5 Mechanism Sanity v1.2 trajectory sanity（受控工程检查）**：4 条固定 `A^O` 的 effort/progress/obstruction/recovery trajectory 均通过状态惯性、累积/恢复与 `π` 传导检查；`ΔO→X→U→S` 的真实数据语义审核仍未开始，不能视为 Gate 1 或正式实验。

## 本轮 development diagnostic 封口

- [x] T14/T20 development chain：Run 1 full-refit、Run 1b frozen-model intervention、Run 2 frozen-`theta_0` incremental、Run 3 trajectory bootstrap、Run 3b permutation-assignment robustness、Run 4 Theory failure decomposition 均已完成并推送。该链只支持当前 LIGHT development cohort 下的结构诊断，不等于独立行为真值上的 formal result。
- [x] Run 4 后停止继续围绕 v1/v1.2 Theory-S 加诊断、调 `eta`、扩 coverage 或修改 representation；本轮只冻结 v2 trainable contract，不启动正式训练。
- [ ] 下一阶段回到 Paper-0 的 Experiment B：独立 `A*` 准入后，比较 `S` 与 raw legal history / structured history / strong summary，并报告 `S + history` residual gain。

## 本轮完成

- [x] 13 份原工作稿完整快照并核对 SHA-256；保留推理历史，见[归档映射](归档/README.md)。
- [x] 已确认机制、研究候选、未决问题、实际进度和行动分开维护；移除前台重复版本。
- [x] 修正“尚无代码”、commitment gate 含义和旧 batch 数据的版本边界。

## A. 先冻结一个最小改造切片

| ID | 状态 | 下一动作 | 完成判据/依赖 |
|---|---|---|---|
| T01 | 待决策 | 明确暂停承诺恢复是软偏好还是硬守卫；明确 started_at 与可知反馈语义；**补上 canceling conditions**（Côté 2013 §11.4.3 明列的 starting/canceling/completing 三类条件之一，当前缺） | 写下接受/拒绝、暂停/恢复、不可见完成的预期；并评估把承诺实现从 weight 调制改为 **rank 调制**是否更贴合语义，见 Q07 |
| T02 | 待设计 | 选一个 X 意义维度与一个 U_k，分开解释和实际 delta | 同一 action 两个情境有独立 X→S 记录；保留旧映射对照，见 Q02/Q03 |
| T03 | **部分完成** | 保留“稳定 affordance + O 已知前置条件”两层：角色已知的灯/窗帘/闹钟/任务/钱包/对象可用性可筛 `A^O`，未知条件只能由 W 结算；采用最小 predicate 表，不引入 DSL | T42 已接通这些已知条件与未知条件的区分；对象错误 belief、遮挡、实例绑定和一般化反馈策略仍见 Q04/Q05 |
| T04 | 待设计 | 给一个自然场景组合写最小 recipe 和对象实例绑定 | Object 基础能力→Scene 组合→W 结算；两同类物品可区别。**affordance 关系**建议按 `(effect, (entity, behavior))` 三元形式化，三分量以角色感知为准、关系存放于角色侧的 `O`，同时兼作规划算子；它不是多角色人际关系，见 Q05。选择条件与保持条件分开声明且放同一处 |

T01–T04 是不同边界，逐项处理和验收；不要一次实现整套插件架构。涉及接口变动时先保留已知基线，再做最小代码切片。[问题详情](未决问题与机制候选.md)是各 Q 编号的唯一说明。

## B. 用户提出的阶段响应实验

- [ ] T05：按用户近似分界冻结一份分段配置，选定一个状态或 P 的消费位置；不要改变原数值加减。完整原意和两套边界见[Q01](未决问题与机制候选.md#q01-分段逆映射与量变质变)。
- [ ] T06：对比线性、分段响应及必要的 gate；固定其余输入与随机源，测边界响应、抖动、饱和、恢复和 Δπ。若加滞回，单列阶段记忆消融。
- [ ] T07：若进入研究结论，增加独立行为/干预评价；规则自己产生预设差异仅算接口验收。

## C. 机制精读与单任务干预

| ID | 状态 | 下一动作 | 判定条件 |
|---|---|---|---|
| T08 | 待继续 | 围绕 X/U/P/承诺缺口精读，不再泛列相似 Agent | 每篇给输入、状态、更新、P、动作、验证及可迁移边界；接文献库，不另抄全文 |
| T09 | **已完成：E0 paired fixtures 回归验收** | E0-1/2/3 已实际运行并归档；E0-1 现在硬断言完整 O/X/S/support 相等，E0-3 硬断言 `task_completed` 经过 X→S 且方向正确 | 当前三组均固定 world seed/personality/state，未采样动作；结果只验证信息边界控制链，不作为行为预测证据；completion 的 `O→X→S` 已在 fixture 中直接输出；下一步转 T13 |
| T10 | 待决策 | 判断单 session 质量是否为首个实验所需 | 如需才设计显式 ActionQuality；不能让 W 暗读 S，见 Q06 |
| T11 | 待实验设计 | 检验 task_pressure 与残留紧张是否需要拆开 | 完成后是否有数据要求不同恢复；不要仅因可拆就加字段 |
| T12 | 待实验设计 | 单因素改变 deadline、疲劳、中断或一个 P 维度 | 相同其余条件/seed，保留负结果；不以更多随机人格替代控制 |

## D. 先确定独立行为真值，再做第一个可判定研究实验

| ID | 状态 | 下一动作 | 完成判据/依赖 |
|---|---|---|---|
| **T0** | **已完成审计；路线 B 待 pilot** | 审计独立 `A*` 来源；不要用本项目规则采样的动作自评 | [审计记录](../01_文献/专题审计_行为真值A星可行性_2026-09-05.md)：BehaviorChain 完整数据因版权暂不可得；CharacterBox 不构成独立 `A*`；SOTOPIA 可进入 30 episode 外部合成轨迹 pilot。**未通过 pilot 前不得启动正式 baseline 比较。** |
| **T0b** | **已完成：结构通过，研究准入未过** | 从 SOTOPIA-π 公开 dump 导出 30 个 episode 的开发切片，核验 action、turn order、private/public information、provenance 与 episode-level split | 30/30 保留自身 goal 与对方 `Unknown`，但 provenance 在 dump 内未知，且动作表面高度坍缩为 `said/did nothing/left`，无法冻结不丢语义的有限动作 ontology。见 [T0b 结果](../01_文献/专题审计_行为真值A星可行性_2026-09-05.md#t0b-实测结果2026-09-05)。**不得据此启动 T14–T17。** |
| **D02** | **已完成全量准入审计：暂缓 pilot** | [OPeRA 全量审计结果](../02_实验/T0d_OPeRA/2026-09-06_准入审计结果.md)：527 条 filtered session；真人 `A*`、O/action 时间序与有限粗标签可用，但官方 split 有 12 user overlap，exact target 无枚举候选集，rationale 时间位置未证实 | **先明确 OPeRA estimand 及能检验 persistent state 的标签层级；暂不训练、不把它写成当前 `A^O` 等价。** |
| **D01** | **进行中：LIGHT 全量无损抽取已完成** | 已审计前 50 episode；全量扫描 10,268 episode，导出 7,258 条 trajectory / 25,001 physical-action steps，并生成聚合 QA 与分层 review slice。下一步人工核 actor/turn/persona/world/history/action 对齐、O 可见边界和候选集语义 | 当前仅为 restricted dev；不训练、不重写动作 ontology、不把 `available_actions` 自动当 `A^O`。详见 [LIGHT](../02_实验/T0c_LIGHT/README.md)。 |
| **T0c-SC** | **已完成最小 bridge：外部 Replay 的 Scene Projection** | 已新增 Python source-preserving snapshot 编译器，并将 snapshot 投影接入 scene-aware candidate semantics；C++ `SceneSnapshot`/RoomDemo projection 与 dataset-neutral `CandidateSemantics` 已通过 smoke。后续转为人工 semantic audit，并为对象 affordance 增加可审计的 source/inferred 区分 | 仍不把 setting/objects 提升为 W，不把 source candidates 提升为 `A^O`；scene-aware v1 结果与 neutral scorer 工件见 [LIGHT](../02_实验/T0c_LIGHT/README.md) |
| **T0c-TR** | **进行中：Scene transition → appraisal → theory-S** | 已在 41 trajectories / 140 steps 跑通 transition audit、固定 `eta=0.35` 的 three-condition smoke，并加入 T1–T6 最小边界测试；下一步独立审查 expected-effect 覆盖与 transition trace，再决定是否扩展 | 当前 `AppraisalTraceStateV0` 是历史结构化摘要，不是心理变量；不调参、不扩大 LIGHT、不把结果写成机制成立 |
| **T0e** | **进行中：跨数据集接口草案** | 用十来个字段定义 `ReplayRecord v0`，先支持 schema 校验、缺失字段和 provenance；不冻结大框架 | [接口草案](../02_实验/跨数据集Replay接口_v0.md) 与 [JSON Schema](../02_实验/Replay/replay_record_v0.schema.json)；完成前不写大型 adapter 继承体系 |
| **D03** | **进行中：ClubFloyd 全量无损抽取已完成** | 425 条 trajectory / 438,188 steps；375 条 quality-stratified review fixture。PowerWash 已下载并外挂到 `E:\library\科研\PowerWash`，待增量导出；AGAIN 受官方条款表单阻塞 | [数据资产登记](../01_文献/数据资产登记_玩家日志与公开轨迹_2026-09-06.md)；[ClubFloyd adapter](../02_实验/Replay/ClubFloyd/README.md)；semantic audit 仍未完成 |
| **D04** | **进行中：FarmQuest 全量 event projection 已完成** | 42 participants / 29,328 telemetry lines / 122 sessions / 10,844 action-proxy steps；已生成 raw+parsed+transformed review fixture。timestamp 不用于排序，`source_O` 保持 null | [FarmQuest](../02_实验/T0f_FarmQuest/README.md)；semantic audit 仍未完成，不进入 mechanism loop |
| **T0g** | **已完成边界设计；待具体实验 protocol** | Phase I（多数据集 dev + LLM-assisted semantics + 显式动力学迭代）、Phase II（冻结 `S/X/U/utility/timing`）、Phase III（新数据上的 fixed-semantics/live-LLM/direct-LLM 对照）已写入架构与 Replay 边界；不在本行启动真实 LLM 调用 | [Replay 接口语义边界](../02_实验/跨数据集Replay接口_v0.md#semantic-frontend-boundary)；test 不得反向改机制 |
| **T0h** | **待启动：compiled semantics 小切片** | 第一个真实 adapter 先由人工/离线 AI 建立版本化固定语义规则表；运行时关闭 LLM，按 `X → U → S` 跑 dev；记录规则修改、失败原因与未来 LLM prompt 约束线索 | 规则不可按单条 `A*`/未来打补丁；待 ClubFloyd 小切片后再决定规则表字段与 protocol |
| **T0i** | **待启动：首个 adapter 语义审核（结构切片已准备）** | 对 ClubFloyd 的 375 条 quality-stratified review fixture 逐条审 W/O/X/S 归属、动作语义、字段损失和 provenance；审核后冻结 semantic annotation 文件 | schema validator 已通过，但 semantic audit 尚未完成；未完成前不扩大批量、不进入 mechanism loop |
| **T0j** | **待启动：首个反事实 replay smoke test** | 第一个真实 adapter 完成语义审核并接通 canonical replay 后，只实现一个单事件 `remove` 或 `replace`，输出 `ΔO/ΔX/ΔS/Δπ` 与 trace 元数据 | 同一 mechanism/semantic-rule/初始状态/随机种子，仅改变一个历史输入；不实现通用 engine，不进入新心理机制 |

- [x] T13：**已冻结 Paper-0 问题卡**：[一页问题卡](Paper-0问题卡.md)。局部可观测、可回放的单角色 Forward；`P` 固定、`D` 导出；分别定义信息边界、预测近似充分性、状态必要性三条主张、外部 `A*`、baseline、split、NLL 口径与 no-go。E0 只验证控制链。
- [ ] T14：建立 persona only、raw history、**结构化 history**、强 summary、`no-S`、rank-matched 1D `Activity-S`/`ActionSupport-S`/`Theory-S`、state 与置换-S基线；相同信息权限和模型条件；区分开发/测试，并报告 `S + history` 的残余收益。v0 为设计历史；v1 raw-feature/probe 候选协议与一键 dev runner 见 [T14/T20 v1](../02_实验/T14_T20_rank_matched_probe_v1.md)，正式训练待独立行为真值准入。
- [ ] T15：真实下一行为揭晓前输出概率/排名，做 Replay；控制身份泄漏、叙事 framing 和动作支持集。**2026-09-05 新增依据（迄今对"用 held-out NLL 而非人类评分"最强的一条支持）**：Game AI Pro V3 C04 是全套 146 章里**唯一的真人受试实验**——22 个 AI 对手、同日完成、顺序随机化、五点量表 + 开放式短答。结果：**「83% of players were unable to recognize an AI that was literally nothing more than a random number generator」**；享受度与实际/感知难度、智力、真实感**均不相关**，一个纯随机 AI 在"最好玩"上并列第二；且**「players invent stories for the nonplayer-controlled characters… They see cheating, bias, motivations, and desires where none exist」**。**人类评分测的是叙事可读性，不是机制保真度**，故只能作次要指标。同一来源还给出反向警告：**「In game AI, words sometimes speak louder than actions」**——这与 AI Town 的爆火互相印证（见资产页 §3.4）。
- [ ] T16：做小消融再收缩机制；若 state 不优且无效率/可控性收益，接受更简单表示。
- [ ] T17：接入有成本推断后，预先冻结质量容差，测总维护+决策 token/调用/延迟/成本，不只比较 prompt 长度。
- [ ] T18：围绕最终窄问题做可复现职责级查新，记录数据库、检索式、时间、全文访问限制、引文追溯与等价先例。**起手先过一遍[研究问题页 §6.1](前台问题与候选创新.md) 的重合表**。⚠️ **2026-09-05 晚间修正**：原写「状态→分数→采样、承诺惯性、目标分桶、SmartObject、前置条件校验这五项…**不得再作为新颖性主张**」，**该约束力现已暂停**。理由：这些判定是在概念标签层做的比对，属用户批评过的错误方法（见[方法复核 §0](审核_文献比较方法与阶段缺口_2026-09-05.md)）。**T35 完成重审前，该五项只作提示，不作新颖性约束。**查新范围须显式纳入 GDC / Game AI Pro 等非学术来源（不在任何学术索引内，本次仅取到 2 篇，覆盖严重不足）。
- [ ] T19：多 horizon 曲线。在约 20 / 100 / 500 决策点分别比较 raw history、强 summary 与 S 的 held-out NLL 或排名，找交叉点；不存在交叉点也原样记为结论。
- [ ] T20：等容量对照消融。当前先做 rank-matched 1D `Activity-S`、`ActionSupport-S` 与 `Theory-S`，三者使用同一 EMA 与同一 raw-feature conditional linear probe；待 appraisal 经验维度真正超过一维后，再升级 3D structural/hashed naive-S。结论限定为当前数据、容量与 baseline 条件下的证据，不表述为心理机制已成立。v0 为设计历史，v1 候选协议见 [T14/T20 rank-matched probe v1](../02_实验/T14_T20_rank_matched_probe_v1.md)。
- [ ] T21：噪声填充消融。在 trace 中注入与行为无关的填充事件，观察 S 相对 raw history 的优势是否增大，检验正则化假设。
- [ ] T22：把"引入心理学"落成可证伪链：选定 N 个 appraisal 维度 → 固定函数形式 → 等维度非理论对照 → 预先写定 ΔNLL 判定阈值。四步完成前，不把心理学贡献写进任何结论，见[Q09](未决问题与机制候选.md#q09-字段和理论怎么选收益怎么判)。
- [x] T23a：**T18 的前置**——Game AI Pro 覆盖。已从 10 篇扩到 **A 级 43 章全部下载完毕**（4 卷共 146 章，官网免费 PDF，**不在任何学术索引内**）。已按相关度分级：A 级 43（定向核读）/ B 级 30（按需回查）/ C 级 73（不读，寻路·转向·人群·赛车·摄像机·动画·MCTS 等，与机制链无对应）。完整清单见[Game AI Pro 全景与工程 Gap](../01_文献/专题核读_GameAIPro全景与工程Gap_2026-09-05.md) §5 附录。
- [ ] T23b：完成 A 级 43 章的定向核读。**43 章文本已全部提取**（`tmp/gameaipro/txt2/`）；逐节核读仍仅 8 章，其余 35 章待读。C 级不读须在 T18 查新报告里显式声明为"已排除并说明理由"。
- [~] T24：**不再阻塞 Paper-0**（2026-09-05）。首篇以局部可观测、可回放的状态预测识别为锚；“更 believable NPC”与“降低 authoring 成本”的对外价值叙事留到有 held-out 证据后再选择。原有比较保留作论文写作期背景，不替代 T13 的可检验问题卡。
**2026-09-05 追加（用户提出 AI Town 例证后的核对）**：Generative Agents（2023）的小镇，其**调度底座**（地点 + 日程 + 动作槽 + 移动）与 Game AI Pro V1 C36（2013）的 `BackgroundAI` 小镇模拟器**是同一套东西**，十年间被替换的只是表面文本层。其 NPC 状态仅有位置/速度/朝向/目的地/归属/当前动作/当前日程/条目结束时间**八项，全部是物理与日程量，无任何内部状态**。→ **AI Town 的爆火验证的是"在既有调度底座上接 LLM 文本层"的吸引力，不是"内部状态建模"的吸引力。** 这对 (a) 是**双刃**：位置确实存在且人们想要（正面），但若以人类观感评测则很可能测不出 S 的贡献（负面）。**`(a)` 与 `(b)` 不是互斥的**：可取「(b) 的评测协议 + (a) 的价值叙事」，但前提是**评测只认 held-out NLL**。 保留约束：对外表述中 `P` 必须显式区别于业界"projected personality shell"用法（V3 C01 §1.5："covering up any inconsistencies"）。

## E2. 调研方向（用户 2026-09-05 指定登记，不是当前任务）

- [ ] R1：「**LLM 打破的是成本与带宽，没有打破需求与取舍**」这条判定的成立范围。当前是基于 8 章核读的 `[项目推测]`，**语料全部成文于 2013–2021，早于 LLM 角色模拟兴起，文中无任何 LLM 讨论**。需要独立论证：Gap 1/2/4 究竟是设计选择（不随技术变）还是技术约束下的妥协（会随技术变）。**本条不作为当前执行项。**
- [x] R2a：**学术 ToM 调研**——⚠️ **2026-09-05 晚间修正：本不需要新做，本地库已覆盖。** 原写"新增学术 ToM 调研"属**重复劳动**，我开任务前没查自己库，已撤回。
  - **已覆盖**（[全量近邻精读总表](../01_文献/全量近邻精读总表_2026-09-01.md) §逐篇审计，2026-09-01 已完成）：**TimeToM** 已为每个角色构造 Temporal Belief State Chain，并**区分 self-world 与 social-world belief 来回答不同阶 ToM**；**DYNToM** 评测连续情境中的 belief–emotion–intention–action 轨迹与转移；**PsychSim** 是决策论 agent 的 ToM 建模先例。
  - ⚠️ **术语澄清**：此前"二阶知识全库零命中"指的是 **Game AI Pro 那套工业书**（146 章），**不是说学术界没做**。引用时禁止简化为"二阶知识无人做过"。
- [x] R2b：✅ **已拍板（2026-09-05 晚）：二阶知识取二阶，不做三阶。**
  - 用户决定。**三阶明确不做**，与心理学证据一致（人类实际很少使用三阶嵌套信念）。
  - 仍待补的差额（**不是"要不要做"，是"怎么做"**）：
    1. 表示形式未定。候选：②-a 每个他者一条 belief 槽；②-b 只存"我关于他者心智的摘要字段"，不存完整嵌套。倾向 ②-b——与我们"有限角色动力学变量"的整体取向一致，且不给 State 加无界结构。
    2. TimeToM 的 belief chain 是**为 ToM 问答**设计的，**它如何影响行为分布这一层它没做**——这正是我们的位置（见[机制说明 §3.1.2](完整机制说明_v0.md)）。
    3. 与 §3.1.1 的整合——关系事实 `E^W` 及**可追溯的二阶知识归属索引**由 `W` 维护；私有态度 `R_i[j]` 仍归 `S_i`，且索引必须先进入相应 `O_i` 才能影响行为。
    4. ⚠️ **二阶知识不得登记为创新点**（学术界 ToM 做得很多）。我们的位置是"把二阶知识接到行为分布上"，这是接口/整合层的工作，按 13 维模板（维 8 因果链位置、维 13 实验里验证什么）与 TimeToM 区分。

## F. 工程资产与整合复核（2026-09-05 新增）

起因：用户批评「这些文章你都是在说和我的有啥重叠有啥支持、反对，但是**工程上完全没说？他们的实验和代码呢？能不能为我们所用？**」，以及「我们弄得是一个**整合系统**，曾经在有其他部分短板的情况下做的判断可能不成立」。

成果页：[工程可复用资产](../01_文献/专题核读_工程可复用资产_2026-09-05.md) ｜ [整合复核](审核_整合系统视角复核_2026-09-05.md)

| ID | 下一动作 | 依据 | 优先级 |
|---|---|---|---|
| ~~**T25**~~ | ✅ **已实现于 `807359b`，历史口径**：轨迹 CSV 落盘每个实际 `ActionType` 的 `p_<action>` | 65,536 行 smoke 仍是记录仪，但其 `A^O` 来自旧的 `W.available_actions()` 语义；当前分支已改为 visible-object affordance，**旧统计对当前模型候选集无效**，不得当作当前分布或实验结果 | 已办（需重标） |
| ~~**T25b**~~ | ✅ **已实现于 `807359b`，历史口径**：落盘 `known_action_count = |A^O|` 及 NLL 报告规则 | `ln|A^O|` 规则仍保留；旧 9/10/11/13/14 分布只属于历史候选定义。E0 前重跑几十/几百步 smoke 后再记录当前分布 | 已办（需重标） |
| ~~**T25c**~~ | ✅ **已实现并验证于 `6be808a`，历史口径**：每步落 `known_<action>` support mask | mask 机制可复用，但旧 65,536 行验收不能证明当前 `A^O`；待 T03 的 O-known predicate 落地后重新验收 | 已办（需重标） |
| **T26** | 接 `ngram_lib`（V1 C48，1762 行 header-only）跑 N=1..5 留一 NLL 作**基线地板** | 其 `Probability_Next_Is(event)` 正好给出完整下一跳分布 | 高 |
| **T27** | **预注册分层 ΔNLL 判据**：报告按 session/user 聚类的 paired ΔNLL（并转 Δbits），另设 `S≈H` 的非劣效/等价界 ε 与置换-S 的优越性检验；不把 OPeRA action 当独立样本 | `ln|A^O|` 仅是逐步随机基线；候选集变化时同时报告分层原始 NLL 与按预注册分母归一化值 | 高 |
| **T28** | 增设**置换 S 对照**：保持 X 与 π 不变，随机置换 S（或换成他人 S），看 NLL 是否显著变差 | 整合后 LLM 先验会从 X 一路传导到 π 并被包装成"角色决策"。此对照**成本极低、杀伤力最大** | 高 |
| **T29** | 增设**等记忆对照**：给基线足够大的 N（或 LSTM/SSM）使其记忆容量不落下风 | 否则 S 取胜可能只证明"状态压缩有效"，不证明"理论结构有效" | 中 |
| **T30** | 增设**分层诊断指标**（X 抽取一致性 / S 轨迹平滑性 / π 重现性） | 串联系统失败时**不可定位**是哪一环错 | 中 |
| **T31** | 评估 `BackgroundAI`（V1 C36，10,758 行小镇模拟器）可否作世界底座，或至少抄其 `ActionDefinition`/`ActionInstance` 切法与三类日程组合子 | 见资产页 §3.3 | 中 |
| **T32** | 主评测场景**主动削弱日程周期性** | 日常作息强周期，N-gram 会是硬基线；若 S 打平可能只说明"场景太容易" | 中 |
| ~~**T33**~~ | ✅ **已实现于 `807359b`**：`StudyAtDesk` 拆为 `StudyFocused` / `StudyHalfhearted`，实际动作数 **15→16** | 后者消费 boredom 与 suspended 决策点，前者消费 satisfaction；π(A) 形式与 softmax 未改。系数只是规则占位，拆分不自动证明 Q01，见 [Q01 拍板块](未决问题与机制候选.md#q01-分段逆映射与量变质变) | 已办 |
| ~~**T33b**~~ | ✅ **已实现并复核于 `807359b`**：`decision.cpp:86–90` 已将 `StudyFocused`、`StudyHalfhearted`、`StudyAtComputer` 全部计为 `advances_committed_task` | commitment bonus 不会因动作拆分而静默失效；本次复核同时更正此前过期的待办状态 | 已办 |
| **T34** | 抓下剩余 8 个 demo 包存档 | companion 站点在腐烂，C09（Utility Theory 导论）链接**已实测 404** | 低（有时效） |

| ~~**T42**~~ | ✅ **已完成于 `da70afa` 后续修订** | 已实现最小 `InformationAccess` trajectory 配置、完整 O-known/W-authoritative 前置条件、stale 解析修复与研究不变量；`--e0` 三组 paired fixture 已运行并有 raw stdout | T42 只负责 information-boundary 仪器；E0 fixture、元数据与研究协议归 T09，不再倒灌；**不表示 E0 或研究假设已验证** |

状态同步约束：凡 TODO 宣称“已实现”或“待修复”的代码项，必须同列提交号、代码位置和可复核验收；实现改动与该行状态变更须在同一提交中完成。若是事后审计发现偏差，明确记录为“复核更正”，不把旧状态继续当作事实。

## G. 文献比较方法与阶段缺口（2026-09-05 新增）

起因：用户自己的调研笔记（已归档为[`2026-09-05_ChatGPT_人物动力学Demo设计.md`](../90_原始材料/2026-09-05_ChatGPT_人物动力学Demo设计.md)，1962 行）里两次批评 AI，都直接适用于我：

> 「tmd每次让你找你都会说，唉，我查了一圈叉叉叉不是你的创新点啊…我把我的研究问题不断缩窄，加修饰语，就越来越小，越来越小」
> 「你总是混淆一些概念…你去别的人的论文那里找到一个客观世界就说重合呢。**具体机制完全不是这样的**」

成果页：[审核_文献比较方法与阶段缺口_2026-09-05.md](审核_文献比较方法与阶段缺口_2026-09-05.md)

| ID | 下一动作 | 依据 | 优先级 |
|---|---|---|---|
| **T35** | **后置：只审 8 个高风险近邻**（OPeRA、BehaviorChain、PersonaX、Dynamic Persona Coherence、PersonaForge、ThinkPersona、LIGHT、PsychSim），按 13 维补矩阵；不重审全库 | 研究准入与 Paper-0 问题卡优先；任何近邻结论仍须逐项核验，不作裸判重 | 中（T13/T0d 之后） |
| **T36** | **补文献检索记录**：数据库、检索式、时间范围、全文访问限制、引文追溯 | 当前 82 篇**不可复现**，T18 的查新无法成立 | 高 |
| **T37** | 建**跨论文机制对比矩阵**（参照 `WenyuChiou/ai-research-skills` 的 `literature-triage-matrix`），按 13 维逐项填，替代现有标签级重合表 | 现有[重合表](前台问题与候选创新.md#61-重合表格)是标签级的，正是用户批评的形态 | 高 |
| **T38** | ✅ **已完成**（2026-09-05）：自研两个 skill。① **用户级** `mechanism-level-lit-compare`（13 维模板 + 错误模式 + 自检清单 + 母问题冻结规则）；② **项目级** `cd-orient`（新会话免重扫，含机制链、读文档顺序、三个数字、五个已踩过的坑、用户协作偏好） | WorkBuddy 市场**零科研 skill**（3 次检索确认）；GitHub 上的也不是中文流程 | 中（已办） |

**新增硬性规则（已写入成果页 §1，对所有后续文献比较生效）**：
任何"与 X 重叠/已被做过"的判定，必须走完 13 维（表示什么／谁拥有／从哪来／谁能改／何时更新／输入／输出／**因果链位置**／是否跨时间保存／是否参与动作选择／是否参与世界结算／能否被错误认知／**在实验里验证什么**），并以下列之一收尾：

- 「**机制等价**：同一位置、同一职责、同一更新源 → 才允许说已被做过」
- 「**概念重叠，但机制位置和职责不等价** → 只作提示，不构成新颖性约束」（默认形态）

禁止输出裸结论「X 已被做过」。

## H. 对外表述与英文论文（2026-09-05 晚新增）

用户明确：**最终要写英文论文**。因此对外表述不是"宣传文案"，是**论文的 abstract/intro 的原料**，现在就该按可写进论文的标准来定，而不是临到写的时候再想。

| ID | 下一动作 | 依据 | 优先级 |
|---|---|---|---|
| **T39** | **暂缓 abstract wording；仅冻结 scientific anchor**：Paper-0 的持久状态充分性/必要性与 `W→O` 前提已固定；待 T0d 后再定外部数据与结果措辞 | `对外表述.md` 仍保留过宽的领域概括与未完成数据路线，不能整页冻结 | 低（T0d 后） |
| **T40** | 把 `WenyuChiou/ai-research-skills` 的 **Stage 6–8** 技能登记为后期写作阶段的参考：`academic-writing-skills`、`paper-memory-builder`、`paper-review` | 我们 Stage 5–7 全空（见[方法复核 §5](审核_文献比较方法与阶段缺口_2026-09-05.md)），这几个正好补位。市场无现成中文科研 skill，需按我们的流程改造 | 低（后期） |
| **T41** | 现在写文档时即按论文结构组织：每份设计文档对应 Methods 的一节，每份审核文档对应 Threats to Validity / Limitations | 避免"设计文档 ↔ 论文"二次翻译。英文论文是终点，倒推组织现在的内容 | 中（贯穿） |

**定位（T24）用户表态**：「两个都不太好，硬要的话，第一个是科研，第二个是工程，不冲突吧？」——见[对外表述](对外表述.md) §3 的处理：**拆成「可行性前提 (b) + 价值主张 (a)」的链条，并补第三个 framing (c)**。

### D.1 S 相对 raw history 的三条信息优势（建议，待检验，不是结论）

若 S 是当前 trace 的确定性函数，则 S 信息上不多于 raw history，只能赢计算量（token/延迟/上下文），不能赢准确率。要在准确率上占优，只可能来自：

| 假设来源 | 内容 | 对应检验 |
|---|---|---|
| 理论推断 | X 产出 trace 里没写下的东西：appraisal 维度、弱信号聚合、隐变量 | T20 |
| 正则化 | 有损压缩丢掉噪声，避免 LLM 被无关事件误导 | T21 |
| 长程可用性 | 上下文装不下时 O(1) 状态才可用 | T19 |

### D.2 归因陷阱与判据

X 若由 LLM 做 appraisal，S 胜过 raw history 可能来自 LLM 的世界知识先验，而不是机制本身。只有 T20 的等维度对照能拆开三者：

| 结果 | 允许的结论 |
|---|---|
| theory-S 明显优于 naive-S | 在当前数据、容量与 baseline 条件下，理论选定维度带来增量预测收益；不单独等同于心理机制已成立 |
| theory-S ≈ naive-S | 收益来自有损压缩本身，与理论选择无关 |
| naive-S 不优于 summary | 压缩在该任务上无价值，S 只剩成本收益 |
| 换成弱模型后优势消失 | 观察到 representation × model-capacity interaction；模型先验是候选解释之一，也可能是弱模型未能读懂该 representation，不能单独归因 |

## E. 扩展触发条件，不作为当前待完成量

- 第二同类对象/复杂组合前：完成 T04 的具体实例绑定。
- 多 Task 前：task_id 贯穿 action、outcome、O、commitment 与日志；不依赖第一个 active task。
- 替换多个 updater 时：验收只读输入、唯一写入、依赖/patch 合并及消融旁路，见 Q03。
- 更复杂中断/调度前：冻结实际 Δt、事件跨越、部分失败和 task 子结算日志，见 Q08。
- 对外公开演示前：无 API key 的可复现示例、清楚 README、配置/日志、符合宣称范围的检查；若宣称研究评测还需 fixture、基线与结果。

Inverse、P 可塑性、多角色、叙事自动抽取、专门模型、UI/异步留在[研究分支](前台问题与候选创新.md#7-保留但不挤进首版的分支)，不自动转为本期承诺。

## 每次改代码的通用验收

局部边界测试 + 主链 smoke；同 seed 可复现；新增模块可替换/禁用且无信息旁路；日志区分 requested/applied、计划/实际、pre/outcome/post；运行目录不覆盖；更新[实现进度](当前实现进度.md)。验证后本地提交，只有用户本轮明确要求才推送。
