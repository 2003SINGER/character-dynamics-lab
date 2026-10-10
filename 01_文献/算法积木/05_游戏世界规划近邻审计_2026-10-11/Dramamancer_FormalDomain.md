# 精读：Dramamancer 与形式域抽取混合叙事规划

日期：2026-10-11

状态：定界近邻审计；不是研究结论或方案决策

范围：Dramamancer 的 UIST Adjunct 2025 demo、arXiv v1 extended abstract 与指定公开仓库；以及一篇混合神经符号叙事规划论文。Luna全文与限定源码审读，主代理复核原文；源码未由主代理独立重取。未运行代码、未安装依赖、未改项目实现。

## 结论先行

两套系统、三份论文材料回答的是不同层次的问题；Dramamancer 两种出版物分别记证据。

- [论文证据] Dramamancer 的设计分工是：作者提供风格、人物/场景与事件（storylets）；解释器 LLM 根据玩家输入和已生成文本判定事件条件；生成器 LLM 续写非玩家角色/叙述者文本并把事件结果编织进去。作者与玩家评价指标在这份短文中是拟议方向，不是已报告的 benchmark 或玩家研究结果。
- [源码事实] 固定到 Dramamancer 仓库 `main` 的读取快照后，触发判断仍是 LLM 对文本记录的解释，不是读取独立、权威的游戏状态 `W`；事件 outcome 主要作为文本指令交给下一次生成。能确认有应用持久化的叙事行/元数据/场景等，但在本次追踪的生成与触发路径中没有发现独立的游戏世界执行器，不能据此断言整个仓库绝无其它执行机制。
- [论文证据] Kelly 等人的 AIIDE 2023 系统给出更清晰的混合分工：LLM 将故事草稿转成 PDDL 域/问题，Glaive 对角色目标和作者目标进行符号规划，再由 LLM 把计划写成故事；作者可以修订形式域。它报告的是形式域编译/规划可行性和小规模文本分析，不是外部游戏引擎执行、作者劳动成本或玩家 agency 的验证。
- [项目解释/推论] 两者提供的是“可考虑的组件接口”，不是已经证明能完成从空白到全编排、且尊重游戏原生 `G/state/events/permissions` 的方案。可迁移的问题是让作者约束成为可检查、可编辑的中间表示，并把软文本生成与硬状态变更分开；不可迁移为“LLM 判定文本已发生=游戏事件真实发生”或“PDDL 计划=运行时合法动作”。

## 来源、版本与原件

### Dramamancer

- [论文事实] Tiffany Wang 等，*Design Techniques for LLM-Powered Interactive Storytelling: A Case Study of the Dramamancer System*, [arXiv:2601.18785](https://arxiv.org/abs/2601.18785)，版本 v1，PDF 首页标注 2026-01-26。原件共 3 个 PDF 页面，正文 2 页加参考文献；属于 extended abstract / case-study outline，方法与评测细节有限，无附录。本文只把它作为设计描述，不当作强 benchmark。它与下文 UIST Adjunct ’25 正式 5 页 demo 是不同出版物/版本，不把一者的细节或证据倒灌进另一者。
- [源码事实] 公开仓库 `dramamakers/dramamancer` 的 `main` 读取时固定为 commit `1db056dd33390ef88029a08492d577b65cdc48ad`（只读 `ls-remote` 确认；未 clone、运行或安装）。[README](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/README.md) 描述实验性交互故事应用；[LICENSE](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/LICENSE) 为 MIT。以下源码判断只属于该 commit 的实际读取文件，不能自动视为论文系统版本或 2025 论文实现。
- [本地原件] `../../../90_原始材料/_private/2026-10-11_规划近邻原件/Dramamancer/arXiv_2601.18785v1.pdf` 与同名 `.txt`。PDF SHA-256：`e3a8b2219c9909b6f815676cb7a9b4726352c134d1276ac8ab6ce4b93a9771a0`；TXT SHA-256：`5b15a3f380eb50ef22b949774ef0da716263b8fb498467fcf7adb2886e164d55`。

### Dramamancer UIST Adjunct ’25 Demo（单独版本）

- [论文事实] Tiffany Wang 等，*Dramamancer: Interactive Narratives with LLM-powered Storylets*, UIST Adjunct ’25, DOI [10.1145/3746058.3758995](https://doi.org/10.1145/3746058.3758995)，公开 PDF：[原文](https://johnr0.github.io/assets/publications/UIST25-dramamancer-demo.pdf)。原件为 5 页 demo paper，完整阅读；不是 arXiv 2601.18785 的同一版本。它对界面与 storylet 交互的说明比 2026 extended abstract 更具体，但没有提供受控 benchmark。
- [论文事实] §1，印刷页 1–2：作者报告其内部部署已收集 15 个互动故事，由 8 位不同作者创作，其中一些故事是供后续作者修改的模板。这是使用/内容库规模的自述，不等于 8 位作者参加了受控任务研究，也没有对照组、耗时测量、独立质量评分或玩家实验结果。
- [论文事实] §2.1，印刷页 2–3：作者可编辑 style、characters、scenes、events；角色自然语言描述包含人格、背景、关系；scene 有 cast、setting、opening line；事件是自然语言 precondition/content，并选择转移场景或结束游戏的 effect。支持 action-based events 和按回合数触发的 time-based events；界面还提供 LLM 生成事件 precondition 的建议。§2.2，印刷页 3：玩家以自然语言输入自己角色的动作/对白，系统生成旁白与 NPC 对话；可由 narrator 提示可能行动；触发事件可显示作者预设图片并转场/结束。
- [论文事实] §1 对 storylet 的概念定义说 precondition 触发，content 呈现，effects “potentially” 更新 game state；但本文实际展示的 effect 控件主要是 “Then go to” 场景跳转或结束，而不是一般游戏世界变量的类型化 effect。故不能仅凭 storylet 概念定义推断系统具有通用状态更新器。
- [视觉核查] 本地渲染 PDF 第 3 页（印刷页 3，Figures 3–4）已核看：图中是人物编辑表单及场景/事件编辑器，包含自然语言 condition/content 与 “Then go to” 下拉选择。这支持“作者界面确实暴露这些字段”的图示证据；不支持其语义会被外部规则引擎校验。
- [未知/测量边界] 5 页 demo 没有交代模型/提示全文、解释器的内部实现、检测准确率、effect 执行事务、行为合法性或失败率；也没有测 15 个故事的完成/质量、作者负担减少幅度或 agency。文中“降低作者负担”“平衡作者控制和玩家 agency”是目标/主张，不是该文测得的效果。
- [源码事实] 本文展示的原生界面与公开 repo 固定快照并非同一证据：论文明确描述可视化风格编辑、事件图片/弹窗、时间事件和提示按钮；已查 repo 的触发/生成路由只能证明对应 commit 的代码路径，不可凭 README 或图把两者视为完全同版实现。
- [本地原件] `../../../90_原始材料/_private/2026-10-11_规划近邻原件/Dramamancer/UIST25_Dramamancer_demo.pdf` 与同名 `.txt`。PDF SHA-256：`d27c63892f91468b5d5e9450f89a30011f1759e27d446bfec43e958cc6aafdb2`；PDF 元数据确认 5 页；TXT 为 pdfplumber 提取文本，197 行。

### 混合规划近邻

- [论文事实] Robert Kelly 等，*There and Back Again: Extracting Formal Domains for Controllable Neurosymbolic Story Authoring*, AIIDE 2023, 19(1), 64–74, [DOI 10.1609/aiide.v19i1.27502](https://doi.org/10.1609/aiide.v19i1.27502)。11 页全文已读，无附录；讨论及测量可按下文定位。
- [本地原件] `../../../90_原始材料/_private/2026-10-11_规划近邻原件/FormalDomain/Kelly2023_AIIDE_ThereAndBackAgain.pdf` 与同名 `.txt`。PDF SHA-256：`449fb93bad5002c4b12f0300fa1c78d72352312c773907e1e27a99b536abc49e`；TXT SHA-256：`076c374dfed73a4dfe049b5168c24217f2e7a94c4d331bb4f07608c93360c40a`。

## Dramamancer：论文主张与证据

### 数据流与职责

- [论文事实] §2，印刷页 1–2：故事 schema 含 style、characters、scenes；scene 包含角色、setting、开场句与 events。event/storylet 由自然语言 condition 与 outcome 构成；condition 可为空（按生成行数触发），outcome 可以结束场景或转场。玩家以自然语言逐行输入。
- [论文事实] §3，印刷页 2：每个回合有两次 LLM 交互。解释器在每次玩家输入后判断当前 playthrough 是否满足 event condition，并返回触发项。生成器依据之前文本、风格、角色/场景信息生成下一行；它决定旁白或 NPC 发言者，且被要求不要代写玩家角色的动作或对白。触发 outcomes 会传给生成器，要求自然地纳入后续叙述。
- [论文事实] §1–3，印刷页 1–2：论文把作者、玩家、LLM 各自应控制什么作为设计问题，并描述作者编写 schema、玩家输入、模型解释和续写的分工；没有定义一个游戏原生 action API 或形式化执行器。
- [源码事实] 固定 repo `1db056d`：`app/api/gen/story/check/prompt.ts` 给出触发条件核验指令；`app/api/gen/story/check/response.ts` 将历史行转成消息，附候选条件，再调用 Anthropic，解析 `TRIGGERS:` 索引并映射到 trigger UUID。无有效结果时可返回空触发。判定依据是文本上下文与模型输出，不是权威状态读取。
- [源码事实] 同一快照的 `app/api/gen/story/step/prompt.ts` 输入玩家角色名、作者 scene prompt、地点描述、NPC 描述、风格、触发事件叙述及玩家当轮输入；要求模型响应玩家动作、控制 narrator/NPC，不写玩家角色动作。还允许改变叙述中的情势/环境/角色。`app/api/gen/story/step/response.ts` 把历史行中的 `PLAN/LINE/PAUSE` 与触发叙述纳入提示，生成并解析一行文本及元数据。
- [项目解释/推论] 源码里的 `PLAN` 是短自然语言连续性备注（提示限制长度，供后续生成参考），不是有类型、有前置条件/效果、可由 planner 搜索或由游戏执行器执行的动作计划。Prompt 中“事件必须发生”表达生成目标，不构成真实状态变更的事务保证。

### 真值、执行与修改

- [源码事实] `app/api/gen/story/check/response.ts` 的触发证据来自已累计的故事/玩家文本。Prompt 的“仅匹配已完成动作，不匹配计划/假设”等要求是模型指令，不是独立校验器或真实性证明；因此模型可能误判，也可能漏判。本文没有运行代码验证实际错误率。
- [源码事实] `utils/playthrough.ts` 将已玩文本行、行元数据、当前场景及项目内容快照等用于 playthrough；提供作者编辑后检查已生成内容、触发和已遇角色/地点是否过期的逻辑。此为“旧文本是否需视为过期”的维护路径，不等同于逆转或重放权威游戏状态。`utils/validate.ts` 校验数据类型、引用/ID 等结构，不验证叙事条件的客观真值、物理可达性或人物因果合理性。
- [未知] 本次只沿触发/生成/快照与校验路径读代码，没有审计全仓库所有 API、数据库迁移与 UI；因此不宣称“系统完全没有引擎”。就已检查路径而言，未见独立 `W`、具权威性的游戏事件账本、动作权限检查或 effects 执行器；repo README 所述 SQLite 持久化也不能单独证明世界状态语义。
- [源码事实] 可核查入口：[`check/prompt.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/app/api/gen/story/check/prompt.ts)、[`check/response.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/app/api/gen/story/check/response.ts)、[`step/prompt.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/app/api/gen/story/step/prompt.ts)、[`step/response.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/app/api/gen/story/step/response.ts)、[`utils/playthrough.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/utils/playthrough.ts)、[`utils/validate.ts`](https://github.com/dramamakers/dramamancer/blob/1db056dd33390ef88029a08492d577b65cdc48ad/utils/validate.ts)。源码是固定快照链接；未执行，因此是静态证据。

### 人物、天气、作者劳动与玩家 agency

- [论文事实] 人物通过角色设定/描述提供给生成器，scene 和 style 提供上下文；论文关注角色区分、风格遵循与响应性等设计目标。没有形式化 beliefs/goals/permissions/action causality 的人物模型证据。
- [源码事实] repo 的地点描述及场景设定是自然语言字段；本次查阅的 schema/触发/生成文件没有发现具类型的天气状态、天气事件或从外部观测更新的接口。天气可以作为文本设定写入，但其当前真值和因果效果未被这些路径锚定。[未知] 未审全仓库，不据此断言没有其它天气字段。
- [论文事实] §4，印刷页 2：作者侧列出风格遵循、人物独特性、场景感知、事件检测准确率、outcome 实现；玩家侧列响应性、时机、反思/有意义选择、投入度。这些是拟议的评价维度，不是该 extended abstract 已完成的用户研究数据。
- [版本区分] UIST Adjunct ’25 demo 在 §1 报告内部内容库“15 stories / 8 authors”，并在 §2 给出作者与玩家界面操作。这里有更具体的系统展示和内部部署规模，但仍没有受控人评、作者劳动测量或玩家 agency 评价。2026 extended abstract 的维度列表不能被反向当成 2025 demo 已完成的测量；同样，2025 demo 的字段/界面不能自动补全 2026 文本的实现细节。
- [项目解释/推论] 该文有降低作者负担的设计动机，但没有作者耗时、编辑轮次、设定成本、返工量或与基线作者流程比较。事件表、人物描述、场景/地点文本和风格仍需作者输入。允许玩家自由文本行动、且不替玩家角色行动，是一种交互边界设计；不能替代对玩家 agency 的实证测量。

## Formal-domain 近邻：方法与测量

### 混合流水线

- [论文事实] §Formal Story Specification，印刷页 66–67；Fig. 1，印刷页 65：故事形式表示使用 PDDL domain/problem。谓词表示世界事实，action schema 由参数、preconditions、effects 组成；action 带 agents 集合。Glaive 作为 partial-order causal-link planner 搜索作者目标，并用角色目标/意图组织角色行动。图 1 明示人类作者在 LLM 分解与规划环节之间可检查/编辑形式模型，并修改故事世界再重跑。
- [论文事实] §LLM Prompting，印刷页 66–67；Fig. 2，印刷页 67：Decompose 用一次 GPT-4 调用从故事草稿生成 PDDL 域和问题；system prompt 解释任务、PDDL/Glaive 与格式，并含一个手工示例。规划失败时可把失败的 domain/problem 和 Glaive 错误交回模型重试；若可编译但超时无解，则追加人工编写的常见问题提示。实验中只做一次重试。Compose 将计划、域/问题交给 LLM 生成叙事；另设无计划版本作对照。它不是让 LLM 执行游戏动作。
- [论文事实] §Recompose，印刷页 67–68：原型把“写约半页故事→生成形式域/问题→作者修订域/问题→Glaive 规划→LLM 改写故事”组合成作者可控工作流。人工修订是显式纠错点；作者自行校正并不等于论文已定义机器可验证的语义正确性 oracle。
- [项目解释/推论] Glaive 的 action 是虚构故事模型内部的符号动作。论文未报告这些动作被映射到真实游戏动作 API、经由游戏权限校验或提交给独立执行器。因此“计划可解/符合形式域”最多证明模型内部一致，不能直接证明游戏中可执行或当前状态下合法。

### 评估与限制

- [论文事实] §Quantitative Evaluation / Results，印刷页 68–70，Tables 1–2：数据来自 TinyStories 与 r/WritingPrompts。论文报告 GPT-4 未自动调试时约 57% 可编译、21% 可规划；自动调试后约 77% 可编译、34% 可规划；GPT-3.5 为 0%/0%。生成域平均约 4–6 个谓词/动作（原文按其表格报告），较手工 Glaive 域简单。指标是格式/编译和能否找到计划，不是形式事实是否忠实于原故事，更非游戏执行正确率。
- [论文事实] §Thematic Analysis，印刷页 69–72：定性样本包括 4 个手工例故事及其多个组合；端到端生成 100 个样本后，从成功样本随机选 12 个细读。带计划文本通常更贴近计划但可能叙事空洞、直接暴露模型术语；无计划文本可能遗漏作者目标。论文也观察到域可能过拟合单篇故事（如把过程步骤写成目标事实），降低可表达的故事范围。
- [论文事实] §Limitations / Discussion，印刷页 72–73：作者承认系统仍在开发、prompt/模型/planner 选择带任意性；读者/用户研究是未来工作。没有报告玩家 agency、参与度或作者劳动量的对照测量，也没有人类标注域正确性的独立 gold standard。
- [项目解释/推论] 成功率是“生成的形式表示能否让规划器运行”的工程可行性证据，不是“LLM 能准确抽取作者意图”的充分证据。人工修订是重要的人类控制接口，但其耗时、负担和一致性尚未测量。

## 与当前项目的核验表

当前锚点是项目的游戏无关 F0/F1 边界：[`CharacterDynamics_FormalProblem_v0.md`](../../../00_研究设计/CharacterDynamics_FormalProblem_v0.md) 与 [`算法积木 README`](../README.md)。本表只给近邻对照，不改 F0 或积木索引。

| 问题 | Dramamancer | There and Back Again | 对本项目的边界含义 |
|---|---|---|---|
| 作者从何处约束 | 2025 demo 展示 style、人物/场景、自然语言 storylet 及场景转移；2026 摘要概述 schema | 初稿故事生成 PDDL，作者可检查/修改域与问题 | 可研究约束接口的可编辑性；15故事/8作者是内部部署规模，不是作者劳动成本评测 |
| 谁判断“发生了” | LLM 对玩家/故事文本判定 trigger | Glaive 在 PDDL 状态与动作模型中求解 | LLM 文本自报不能写入权威事件账本；形式域自身也需与游戏世界核对 |
| 谁决定后续 | LLM 续写；短 `PLAN` 是文本备注 | Glaive 生成内部符号计划，LLM prose realization | planner 与语言生成职责可分，但 planner 输出不自动具备运行时权限 |
| 效果写入 | 事件 outcome 主要成为叙述指令 | PDDL action effects 更新模型内符号状态 | `W` 的权威写入者仍应由游戏执行/规则层定义，非生成器 |
| 合法性 | 未发现本路径中的行动权限/物理规则执行 | plan 对域内前置条件一致；无外部游戏执行证明 | 域内可解不等于游戏当前合法；需分别检查权限、状态前置条件与 executor |
| 人物因果 | 自然语言人物描述 + LLM 生成 | 角色目标/意图引导符号行动 | 可作人物因果显式化近邻；不证明人物表现真实或玩家认为合理 |
| 反馈来源 | 解释器再次读文本（模型自解释风险） | planner 返回可编译、可解/失败与错误 | 应区分文本反馈、模型内部反馈、真实游戏事件反馈 |
| 天气等世界变量 | 可写入场景/地点文字；未见类型化天气事实路径 | 谓词/属性可在符号域表达；不等于接入真实天气 | `weather` 是否属于 `G`、`W`、事件或观测要先定所有权和更新源 |
| 评价 | 2026 extended abstract 仅列 author/player 维度；2025 demo 自报15故事/8作者，无受控人评 | 编译/规划率 + 小规模文本质性分析；无玩家/作者研究 | 作者意图、玩家 agency、故事质量、执行合法性需分别操作化 |

## 没有覆盖的边界

- [未知] Dramamancer 2026 extended abstract 与 2025 demo 均没有足够信息确定模型/提示全文、触发准确率结果、错误分析、持久化一致性或真实游戏引擎接口；2025 demo 的 15 stories / 8 authors 是内部部署计数，不补成受控的人类评价。公开仓库静态读取也不能补上论文未报告的实验。
- [未知] Dramamancer 本轮只读取触发、生成、playthrough 快照/编辑过期检查和结构校验等关键路径，没有全仓库穷尽审计；无运行测试、无外部服务调用。因而不能给出部署效果、实际异常率或“整个应用绝无执行器”的断言。
- [未知] Formal-domain 论文没有人类标注的语义正确性基准、作者工时/返工统计、真实游戏 action grounding、运行时权限检查或玩家实测；已报告 compile/plan 指标不能替代这些缺口。
- [证据边界] 三份材料没有报告对这组原生边界的联合验证：从实际 `G/state/events/permissions` 中抽取或维护形式模型、对真实 executor 的前置条件做核验、将成功/失败事件作为独立反馈，并衡量作者控制与玩家 agency 的权衡。未报告不等于方法原则上不能扩展，也不能据此单独宣称研究空白。

## 项目决定

1. 只把这三份材料保留为“叙事作者约束与混合规划”近邻证据，不据此新增 planner、runtime、代码或实验。
2. Dramamancer 可用于提出一个待验证的界面问题：作者如何定义自然语言事件条件、触发结果如何回到生成器；其当前可见实现不能作为“LLM 准确认知游戏状态”或“事件真实落地”的证据。
3. Formal-domain 可用于提出另一个待验证接口：LLM 提议形式域/目标，作者纠错，planner 提供可解计划，文本生成器负责表述；但必须另设游戏原生校验/执行边界，且先验证作者控制成本与收益。
4. 对后续 AUTHOR-PLANNING-NEIGHBOR-CHECK，保持问题拆分：合法性（权限与游戏规则）、约束满足（作者意图）、人物因果、作者劳动、玩家 agency 各自定义证据和指标；不得用单一“故事连贯/满意度”代替。

## 用户新理解

留白：由用户补充，不以本报告的 AI 判断代写用户观点。
