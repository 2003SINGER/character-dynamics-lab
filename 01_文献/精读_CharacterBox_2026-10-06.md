# 精读：CharacterBox — 角色扮演能力与本地 NPC 运行时接口审计

阅读/核查日期：2026-10-06

状态：主代理全文审读最终会议版 20 页（含 Appendix A–H），视觉复核 PDF pp.4/7/8/14/19；Luna 源码接口审计、主代理关键路径独立复核。不是用户本人阅读、代码运行或方法复现。

原文：[NAACL 2025 最终版](https://aclanthology.org/2025.naacl-long.323/)，印刷页 6372–6391；[本地 PDF](PDF/2025_CharacterBox.pdf)（SHA-256 `5ddb33e97f3b88423419e4ae5d3027416d93d1dfa726e62ab75b95ae048d1a7d`）。

代码：[官方作者仓库](https://github.com/Paitesanshi/CharacterBox)，审计固定 commit `5c19141ec04197bcdb2e7c7f7e235a5657952977`（2024-12-30）；下列网页代码链接均固定此 SHA。仅读 simulator/evaluation/prompt/schema 等源码，未拉取大数据或权重、未安装、未执行。

## 结论先行

**user-confirmed目标**：目标是“NPC在玩家眼中在游戏里面活起来”，不要求先证明真实人物/心理拟合。

**结论**：CharacterBox 可作为多轮文字角色行动、对话与连贯性的开发筛查参照；不能直接接入 `continuous_runtime` 并取得可比的官方分数。其角色生成是自由文本，Narrator 选择受影响角色并直接写回角色位置/状态及场景；本地 Runtime 则只允许策略在 O 已知的类型化候选动作中选择，再由 World 验证、结算。安全的适配边界是“策略建议 typed choice，Runtime 仍独占 W 写入”。

## 论文证据

- **paper evidence — 方法**：§3.2、Algorithm 1：角色以检索记忆与 self/environment belief 产生行动和即时回应；Narrator 判定互动结果并更新角色/环境。它是文本虚拟世界中的叙事回合，不是具有统一合法动作集、权威 World 转移和连续游戏时钟的引擎。
- **paper evidence — 评分**：§3.3、Appendix G：七项 1–5 分，先由 GPT-4 critique，再按维度评分；指标包括知识/行为准确、情绪、人格、沉浸、适应、行为连贯。情绪丰富、著名角色习惯语等锚点未必适用于无对白日常 NPC，不能整套照搬。
- **paper evidence — 专家核验边界**：§6.3 / Table 4（印刷页 6378）：三名熟悉原作的专家评分与 GPT-4 / CharacterRM 的 overall Pearson r 分别为 .688 / .610，是有限文本专家相关证据，不是玩家“活起来”效度。内部一致性也不等于构念效度。
- **paper evidence — 数据与比较**：§6.1–6.2：10 个作品、100 个场景、232 个角色、11,692 actions/dialogues，比较 9 个 LLM；同一模型扮演场景内所有角色。未见真实玩家盲评、BT/utility 强基线、记忆/BDI 的独立消融或长时钟天数验证。§6.5 明确排除训练的五中/五英新场景用于 **CharacterNR narrator** 测试；不能把它写成 Guided/Reflective 的人物级留出证据。
- **unknown**：本文不把论文示例成本表解释成完整端到端成本；其有限轮数示例和表中未单列的裁判开销不足以支持该说法。场景、裁判、姓名/文风偏差是待验证问题，不据此宣称已测得缺陷。

### 从想法到实际机制：它具体做了什么

| 环节 | paper evidence：读入、更新与学习信号 | 位置 |
|---|---|---|
| 记忆与信念 | 检索过去动作/观察；按提示更新 self belief 的 belief/desire/intention，以及对他人与场景的 environment belief；角色再生成动作/对白/反应。BDI 与向量记忆是具体流程，但没有因此学出心理转移定律。 | §3.2、Appendix D |
| 世界后果 | Narrator 选择一个受影响角色、解释即时互动结果、更新位置/状态/环境，写入后续记忆。可观察动作、不得编造未来情节等是提示限制，不是确定性 World 校验。 | Algorithm 1、Appendix D |
| Guided | 筛选较强模型的 2,336 条高质量教师轨迹，微调 Qwen2.5-7B；学习信号来自合成示范，不是真人动作。 | §4、§6.4 |
| Reflective | 改写自己的初始轨迹，使用 2,561 条轨迹微调 Qwen2.5-14B；不是仅在运行时加一句“反思”。 | §4、§6.4 |
| 辅助模型 | CharacterNR：Qwen2.5-7B 学 GPT-3.5 narrator 输出；CharacterRM：ChatGLM3-6B 学 GPT-4 评分。降低外部调用不等于提供独立玩家偏好标签。 | §5 |

**paper evidence — 训练细节**：Appendix E / Table 8 使用 LoRA、Adam、cosine schedule、学习率 5e-5、cutoff 8192、validation size .1；Guided 6 epochs，Reflective 3 epochs。**inference**：两者基座大小、轨迹量和 epochs 都不同；各自相对 base 的改善是论文报告，Reflective 高于 Guided 不能单独归因“反思方法更好”。

**open question**：论文未完整展开 LoRA rank/dropout、seed、token loss/masking、人物/作品分组 split 与所有可复现训练材料；本轮未审计训练器，不能替作者补成已核实的训练目标。三专家评定样本的统计单位、抽样与盲法等细节也不能由相关系数自行补齐。Appendix B / Table 7 的成本示例只有一场景三轮，列 narrator/character 而未单列 judge；本地模型的费用空项不表示零计算成本。

## 官方实现接口（固定源码版本）

- **角色输入与输出 — source**：[character.py](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/agents/character.py#L51-L107) 将场景事件/时间/地点/描述、角色资料、位置/状态、self/env belief、近期记忆和 observation 放入 prompt；[`take_action`](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/agents/character.py#L156-L195) 输出自由文本可观察物理动作，`take_reaction` 输出回应动作（L197–220），`generate_dialogue` 输出自由文本对白（L125–154）。没有 typed legal-action enum、目标绑定或动作时长。
- **每步与结算 — source**：[simulator.py](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/simulator.py#L173-L280) 先取角色动作/对白；Narrator 选一个影响目标并描述影响，目标角色再反应，Narrator叙述结果、生成位置/状态，并直接复制回角色数据对象。[`round`](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/simulator.py#L284-L329) 更新信念、轮流行动、更新场景和 plot synopsis。Narrator 的精确位置/状态与受影响角色 prompt 见 [narrator.py L98–134, L169–252](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/agents/narrator.py#L98-L252)；场景更新 prompt 见 [L254–320](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/agents/narrator.py#L254-L320)。这些文本约束不是 World 的确定性合法性校验。
- **评分器输入 — source**：[evaluate.py](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/evaluate.py#L51-L76) 用裁判 LLM 对 scene、character description、actions 写 critique；[L85–158](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/evaluate.py#L85-L158) 重建场景/角色静态信息、逐轮 observation 与 action/dialogue；[L160–235](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/evaluate.py#L160-L235) 再由裁判 LLM 评分。故 factual accuracy 是基于文字上下文的 judge 判断，并非与隐藏真值或游戏状态机比对的客观 fact check。
- **时钟/调用边界 — source**：[simulator.py L50](https://github.com/Paitesanshi/CharacterBox/blob/5c19141ec04197bcdb2e7c7f7e235a5657952977/simulator.py#L50) 初始化 `now` 为当日 08:00；在所审代码路径中轮次推进未发现显式推进该时间。一次互动含动作、对白、影响判定、反应/结果、状态更新等多个 LLM 调用，不能与本地一次 Runtime 决策时长直接等成本比较。

## 与当前接口的核验

| 项目 | 本地事实（source） | 适配判断 |
|---|---|---|
| policy 输入 | [`CharacterPolicy`](../Demo%20codex-generated/Inc/character_policy.h#L28-L41) 收到 `DecisionContext/O/S/P`，历史扩展可带 `ActorHistory/RunningAction`；O 明确与 W 分开，[`Observation`](../Demo%20codex-generated/Inc/observation.h#L92-L107)。 | 可做边界受限的文本策略 adapter；只把允许的 actor-visible O、状态/人格及合法候选传入。 |
| policy 输出 | [`CandidateAction`](../Demo%20codex-generated/Inc/decision.h#L13-L35) 与 [`ActionType`](../Demo%20codex-generated/Inc/action.h#L6-L31) 是类型化动作、对象目标、候选资格；ActionDefinition 带默认时长。 | CharacterBox 自由文本必须被 wrapper 映射为现有 `A^O` 候选；映射后是项目自定义协议，不再是原 benchmark 运行。 |
| W 结算/trace | [`ContinuousRuntime`](../Demo%20codex-generated/Src/continuous_runtime.cpp#L183-L243) 接受策略选择后仍执行 World 启动校验、替换或提交 intent。single-room 是静态 trace viewer，所谓 Player View 仍保留 O/S/π（[view toggle](../Demo%20codex-generated/demo/single_room_v0/web/view_toggle.js)）。 | 不可导入 Narrator 对位置、状态或场景的权威写入；目前的 debug 回放也不能直接作为玩家盲评呈现。 |
| 候选面 | [`request_json`](../Demo%20codex-generated/Src/local_model_policy_v0.cpp#L210-L219) 给 typed Laya 所有 hard-admissible 候选及默认时长，Rule 保留自己的 soft eligibility。 | 旧 Rule/Laya 并非只换 head；声称 state/head 收益时应匹配候选与决策机会，研究 gate 则单列干预。 |
| 现有对照 | [`RulePolicyV0`](../Demo%20codex-generated/Inc/character_policy.h#L55-L65) 直接从同一个 decision 的模型分布 `sample_action`，provenance 即 `seeded_sample_from_model_decision`。 | 它是采样封装，不是独立设计的 BT/utility 强基线；若要作比较，应另立行为规则/效用基线。 |

**inference — 可适配与不可适配**：保留 O/S/P/历史边界，将 CharacterBox 风格生成限制为“从当前类型化候选中选一个并给理由”，让现有 Runtime 完成动作启动验证、时长推进与世界结算，是可行的工程接缝；需新写 wrapper、prompt 和评测，不是官方 CharacterBox score。把完整 W、其他角色私有状态或 Narrator 的自由文本结果传给策略，会改变信息权限并可能让 narrator 偷写 W，应禁止。

**inference — 轨迹成本与候选风险**：CharacterBox 的 story-oriented 动作文本没有本地候选对象、开始/结束时刻、持续时长合同；直接比较会混淆动作空间、控制频率、上下文和预算。应匹配初始 W、信息权限、外生事件 tape、动作定义与展示，记录策略输入、候选、选择、拒绝/结算、时长及全部调用；行为改变后的 O 可以自然不同，不强迫相同未来 O。

## 没有覆盖的边界

**paper evidence**：文本轨迹分数可提示角色设定/知识/行为连贯及对白表现，不测目标游戏中的动画、走位可读性、玩家控制与 NPC 的共同互动，也未验证玩家是否感到背景 NPC 有生活感。

**project evidence**：`Demo codex-generated/demo/core_behavior_eval_v0/README.md` 明言现有工具检验同世界下 P 和积累状态/承诺是否改变行为，不是 human-validity benchmark；`demo/single_room_v0/README.md` 是 trace 静态可视化。故自动轨迹指标与玩家盲评需要分开报告。

## 项目建议（proposal，未授权执行）

**project decision**：本轮保留 Runtime 和所有模型/实验不变；不启动 benchmark、训练或招募。将 CharacterBox 的轨迹评价与裁判校准作为方法参照，不照搬七维总分，不以真人 `A*` 为玩家目标的统一前置门。一个小场景的具体机制、独立基线、玩家可见呈现与评价校准，只由[研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md#玩家目标的第一个可比较问题proposal未执行)维护；这里不另立执行协议。

## 开放问题

- 最小 player-facing “活起来”维度如何定义，怎样避免把对白丰富度当作日常行为质量？
- wrapper 给候选及动作默认时长后，如何保持候选覆盖公平，并把调用数/延迟纳入比较预算？
- 自动 fact/action 检查与盲评之间的关系、评审一致性及玩家效度，需要怎样的小规模校准？
