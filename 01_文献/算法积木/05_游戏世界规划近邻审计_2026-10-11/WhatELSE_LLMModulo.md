# 机制对照：WhatELSE 与 LLM-Modulo

阅读日期：2026-10-11

状态：已精读（WhatELSE CHI ’25 全文 18 页；LLM-Modulo arXiv v3 全文 13 页，限于本文所需框架接口）

原文：私有归档 `../../../90_原始材料/_private/2026-10-11_规划近邻原件/WhatELSE与LLMModulo/`；[WhatELSE 作者 PDF](https://www.research.autodesk.com/app/uploads/2025/02/WhatELSE.pdf)（arXiv:2502.18641v1，CHI ’25）；[LLM-Modulo arXiv v3](https://arxiv.org/pdf/2402.01817v3)。PDF SHA-256分别为 `9c4533816cdac0c2ca25f989ab9c3ce4e24fe863d5acb7a3d6de9adcc32b1ada` / `8f79507f1fb1f1d6b4e086be2c2401df6775f091ae158efdc291116cfe6b720c`；完整清单见私有归档 `SHA256SUMS.txt`。Luna委派全文审读，主代理定向核对方法/执行/评测与§3接口；未运行软件。

## 结论先行

**论文证据：**WhatELSE 是与“作者部分约束下的游戏世界高层规划”直接相关的强近邻：作者用示例故事、可调抽象层级的 outline 和 variants 塑形叙事空间；运行时由 LLM 把 outline event 编成角色动作序列，既读既有 game state，也经模拟环境执行、收到成功/失败结果后迭代。它证明这一交互式“抽象目标—固定动作域—真实游戏状态反馈”管线可落地，并做了用户与技术评价。

**边界：**它不是符号规划器，也未证明一般完备性。游戏环境实现函数确实执行 schema 动作并更新 W；但论文没有给出对任意世界的形式化 soundness 证明、独立 PDDL/SMT solver、规划完备性、候选事务回滚契约或通用的非角色世界操作接口。Coherence 与角色动机评估是 LLM critique，不能算 hard validator。将其概括为“LLM-Modulo 风格的执行反馈循环”准确；称为“符号规划器验证了 LLM 计划”则超出证据。

**对本项目的定位（推断）：**优先用作 F0/F1 中作者抽象目标转成 grounded game action、依据当下世界重编译的系统基线。它对本轮“AUTHOR-PLANNING-NEIGHBOR-CHECK”构成正面近邻压力；是否覆盖本项目要检验的作者成本、世界操作权限、跨回合持续约束仍待同域对照，不能从本论文直接推出 gap 或新颖性。

## 论文实际机制

| 接口 | WhatELSE 论文证据 | 对照边界 |
|---|---|---|
| 作者约束 | §4.1，pp.3–5：pivot 可由样例故事起步；生成 outline；beat/scene/sequence/act/story 五级 abstraction ladder；词句级 abstraction tooltip；可编辑 pivot/outline，移除或恢复 variants，并从 variants 更新 outline。 | 支持作者从实例到可调叙事空间的混合主动塑形。没有给出任意可执行谓词、作者动作模型或可检验硬/软约束语言；抽象自然语言目标仍有模糊性。 |
| 域与状态 | §4.2.2，p.5：Game Environment 持有 Story Domain 与 World State；W 含角色属性（如生命值）、地点、关系分数及模拟记忆。Domain 有角色、地点、action schema；每个动作是改变 W 变量的可执行函数调用，例 `kill(X)` 使 X dead。 | 事实由游戏函数执行后建立，不是仅由模型叙述。其可验证范围受该游戏状态模型和已编码动作限制。 |
| 高层候选 | §4.2.2，p.5：逐个 outline event，LLM Plot Generator 输入角色及描述、action schema、当前 W（含记忆），生成角色动作序列。Narrative goal 可是模糊 outcome，也能约束转移过程；论文举“everyone likes Bob”“someone careless and got into an accident”。 | 是候选生成和事件细化，不是搜索完备的状态空间 planner。相同 outline event 可随当前 W 细化为不同 action sequence。 |
| Reviewer 与执行反馈 | §4.2.2，p.5：Plot Reviewer 的整体 coherence 评估、逐动作角色扮演/motivation 检查均通过 LLM prompting；之后 simulated Game Environment 执行候选，并报告执行 success/failure；合并反馈进下一轮生成 prompt。 | Reviewer 的连贯性/动机意见是软语义 critique。环境执行反馈是对已实现动作效果/前提的外部检查；论文未证明该模拟器相对于任何更完整游戏规则无遗漏或形式化 sound。两者不可混称符号 solver。 |
| 动作域实例 | §5.2，p.7：Fairytale Forest 有 6 角色、5 地点、6 schema 动作：move to、speak to、kill、attack、think、save。 | 这是角色动作域实例。正文没有展示 weather/world actor、雨、云等非角色 world action；能否表达须查具体 schema，当前证据为 unknown。 |
| 反馈与提交 | §4.2.2，pp.5–6、Fig.3：Game Environment 执行序列并更新 W；玩家（真实或 proxy）可随后改变 W；更新 W 与 outline 返回 compiler 处理下一事件。示例若 dove 已死，则可改用 ant 落水等替代序列（脚注）。 | 说明事件间 state-aware replanning / 后续事件重编译。没有明确写出隔离试跑、逐动作提交、失败 rollback/原子事务语义；不能把执行前的候选过程假定成可撤销 transaction。 |
| 回合级互动 | §4.2.2，pp.5–6：outline event 被实例化执行；事件之间玩家或 NPC 有 free actions；每轮玩家行动后执行动作更新 W，再展开下一个 outline event。§4.3.2，p.7–8 给出玩家自行完成抽象事件、或由 witch 等 NPC 履行的示例。 | 玩家行动可履行作者事件；否则后续由角色满足事件，显示有限的作者目标维持策略。没有给出广义冲突优先级、强制世界改写、可达性或终止保证。 |
| 信息与权限 | §4.2.2，p.5：角色 prompt 含当前 W（包括该角色记忆），但文本没有系统刻画字段可见性/角色 belief 与导演全局状态的权限矩阵。 | 不推断 LLM 自动遵守角色视角；也不推断导演可随意改变事实。作者编辑叙事空间、玩家改变 W、游戏函数执行动作，是论文明确展示的不同接口。 |

### 方法顺序（据 §4.2.2 pp.5–6 / Fig.3）

1. 作者的 outline event 进入 Interactive Narrative Compiler。
2. Plot Generator 根据 schema、角色资料、当前世界与记忆生成一串 grounded character actions。
3. Plot Reviewer 产出整体 coherence 与逐动作角色动机意见。
4. Game Environment 对候选动作执行模拟并反馈 success/failure；各类反馈加入下一轮 prompt，重复生成/审阅。
5. 产生最终序列后由环境执行并更新 W；玩家或 NPC 在 outline events 之间行动，也改变 W。
6. 后续 outline event 读取更新 W 继续编译，直至 outline 用完。

**未公开 / 不应补造：**最大迭代次数或无可接受候选时的 fallback；试执行是否写入临时副本；候选提交与失败回滚；环境对复杂动作、非角色事件、隐藏信息和并发事件的覆盖保证。论文把执行可行性称为 causal soundness，但无法据此声称一个通用的、已证明 sound 的规划器。

## 与 LLM-Modulo 的接口核对

| 项 | LLM-Modulo 原文主张 | WhatELSE 中实际对应物 |
|---|---|---|
| 框架形式 | §3，pp.5–6：Generate-Test-Critique；LLM 生成 candidate；critic bank 检查 hard correctness 与 soft quality；失败可回传粗到细反馈，也可有 constructive suggestion。 | Plot Generator → LLM Reviewer + simulated Game Environment → critique 进入下一轮生成，形式上符合 generate/test/critique 的核心循环。 |
| soundness | LLM-Modulo §3.1，p.6：总体 soundness 继承自 external hard correctness critics 的 soundness；hard critic 可是 model-based checker 或 simulator；LLM 可作 soft/style critic，但不能给出 soundness guarantee。 | WhatELSE 的环境确实执行 schema 函数、检查其状态效果和成功/失败。它只对实现内的游戏语义提供操作性反馈；没有论文级形式证明或独立符号求解器。LLM coherence / motivation feedback 不增加硬正确性保证。 |
| completeness | LLM-Modulo §3，p.5：完整性依赖 LLM 是否能生成所有相关候选；框架本身不提供完备搜索。 | WhatELSE 没有声称 outline-to-action 搜索完备。未找到候选不能解释为目标不可达。 |
| 是否本文实现 | WhatELSE §4.2.2，p.5 明确称“following the LLM-Modulo framework [33]”；LLM-Modulo 参考条目是 Kambhampati et al. 的框架/position paper。 | 属于直接引用并按该结构实例化，不表示把 LLM-Modulo 的全套规划条件、hard critic 契约或 soundness 证明完整实现。 |

**判读句：**WhatELSE = 作者可编辑叙事空间 + LLM grounded action proposal + LLM soft critique + 本地游戏模拟器执行反馈。LLM-Modulo 是解释这类“候选—外部检查—反馈”组合的一般框架；若 hard critic 的规则模型不 sound，系统就没有框架所说的 soundness guarantee。本文所展示的环境比纯 LLM self-judge 强，但不等于与同状态输入的符号/规划 solver 对照。

## 评测证据与量的分离

- **用户研究**：§5，pp.7–11，N=12（同校招募；参与者均至少中等生成式 AI 经验，9/12 没有 interactive narrative 创作经验），比较 WhatELSE 与 baseline workflow。问卷、观察、访谈评估作者控制/表达/负荷，以及参与者对生成剧情/游戏体验的感知；不是大规模真实玩家长期体验试验。作者报告生成后进一步编辑剧情的主观工作量更低（中位数 4.5 vs 3.0，p=.027，§5.6）。
- **抽象能力**：§6.1，p.11：Fairytale dataset 的 100 个故事，在 scene/sequence/act 三层生成 outline；用词典 concreteness 与 imageability 测量措辞抽象度差异。支持词面抽象层级分离，不直接证明约束满足或世界规划质量。
- **plot diversity**：§6.2，pp.11–12：12 份人类 outline 与 50 份 LLM outline；每份 outline、每种方法生成 20 个 plots；WhatELSE 与 prompt-based compiler 比较 ROUGE 距离。衡量文本差异/多样性，不等于语义合理性或人评质量。
- **player impact**：§6.2，p.12：固定 Fairytale Forest、两幕 outline、玩家为 dove；对比攻击/杀害角色与帮助受困角色的两类动作，各条件生成 20 个后续 plots；指标包括后续 plot ROUGE 差异、被杀角色之后是否重现、帮助后玩家角色参与频率。它测模拟动作对后续生成的影响，不等于玩家主观体验。
- **基线与消融**：主文比较对象是 prompt-based IN Compiler / baseline workflow；正文未报告 ablation study。没有“同一状态交给符号 planner”的对照，因此不能用结果证明 LLM planner 优于成熟规划器，也不能量化各 reviewer/环境组件独立贡献。
- **限制**：§8，p.14：研究使用简单 story domain/template、样本小且参与者背景有限；没有与传统 IN authoring tools 直接比较；玩家体验仍需真实主观 engagement/enjoyment 研究。§7.1，p.13 还指出长期依赖/coherence 是 LLM narrative generation 的限制。

## 与当前项目的核验表

| 项目 | 论文覆盖 | 项目仍需验证 |
|---|---|---|
| 主体 / 状态 | 作者 outline、角色/地点、W 属性/位置/关系/记忆、玩家输入；更新 W 回传下一事件。 | F0/F1 的作者部分约束具体映射为何种 predicate / goal；角色可见状态、共享世界态与导演态怎样区分。 |
| 作用 / 写入 | LLM 产已有 schema 的角色 action candidate；执行函数改变 W。 | 需要非角色世界动作时，是否纳入固定可执行域，权限如何授予；天气案例需具体 domain operator 才能判断。 |
| 失败 / 反事实 | 模拟器反馈 action success/failure，后续可按更新态换序列；有已死 dove 时转 ant 情境的例子。 | trial/commit、部分效果/中断、rollback、无解/fallback、最大迭代及真实 engine 与模拟器一致性。 |
| 评测 | N=12 作者工具研究；Fairytale 技术比较，文本距离/模拟状态代理指标。 | 同域与成熟规划/作者工具比较；玩家体验、作者总工时、硬约束违例和长程轨迹质量独立评测。 |

## 项目决定与开放问题

**项目决定（边界修正）：**把 WhatELSE 作为“自然语言抽象 outline → 现有角色动作 schema → 执行反馈重编译”的强基线纳入本轮候选比较。它让“LLM + 环境反馈处理作者抽象目标”不再是可主张的新机制；本审计不决定其与本项目的同域性能，也不据此宣告 research gap。

**开放问题：**对本项目真正新增的要求，是否需要环境候选之外的非角色世界动作？作者权限是只约束可接受轨迹，还是允许世界干预补足可达性？将生成事件改成显式 hard/soft contracts，是否能以可审计收益超过已有 schema+environment loop？现阶段均未回答。

## 证据来源定位

- WhatELSE §4.1 pp.3–5（pivot、outline、abstraction ladder、variants）；§4.2.2 pp.5–6 / Fig.3（state/action schema/compiler/reviewer/execution loop）；§4.3.2 pp.7–8 / Fig.4（交互例）；§5.2 p.7（domain/action schema）；§5 pp.7–11（N=12 study）；§6 pp.11–12 / Tables 1–3（技术评测）；§7.1 p.13 与 §8 p.14（长期一致性及限制）。
- LLM-Modulo §3 pp.5–6（generate/test/critique、soundness 与 completeness 边界）；§3.1 p.6（hard/soft critics、soundness 来自 hard critic）。本文只用此框架接口，不以其两个 case studies 为 WhatELSE 结果。
- 原文版本与 SHA-256：见 ignored 私有目录 `90_原始材料/_private/2026-10-11_规划近邻原件/WhatELSE与LLMModulo/SHA256SUMS.txt`。

用户新理解（留白，不以 AI 判断代填）：
