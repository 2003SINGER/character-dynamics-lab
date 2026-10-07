# LIGHT before-turn 信息来源核查（v1）

日期：2026-10-06。范围仅为 2019 LIGHT 原始任务/处理链与本地 `light-dialog-processed-small7.pkl` 的 before-turn 通道来源。事实分为：**直接源代码/论文证据**、**本地结构或逐字段核对**、**尚未证实**。本文件是准入证据草稿，不改变模型、训练结果或 Paper-0 决策。

## 结论

2019-03-21 ParlAI LIGHT worker world 的确实现了轮前环境与候选动作准备、由 worker 将自由文本和所选 action 作为一次 act 提交、再更新世界并把结果展示给另一 worker。官方附件 Figure 9 也显示 worker UI 有自己的 Persona/Setting、对话/动作结果 feed、动作下拉菜单和自由文本框。

但是，针对本地官方处理文件 `light-dialog-processed-small7.pkl`，没有找到从 MTurk collection log 到 pickle 字段的 exact serializer/exporter。故不能将 March world 的流程直接断言为 `context[i]`、`available_actions[i]` 在 small7 中的精确生成/记录时点，也不能据此认证所有同索引字段的角色可见性。**`context[i]` 与 `available_actions[i]` 相对当前 action 的 small7 时序仍 UNKNOWN；记录候选不等于 `A^O`。**

## 证据锚点

### 1. 正式论文与附录

- Urbanek et al., “Learning to Speak and Act in a Fantasy Text Adventure Game,” EMNLP-IJCNLP 2019, pp. 673–683；[ACL 书目及官方 PDF/Attachment 入口](https://aclanthology.org/D19-1062/)。本地正文 PDF：`01_文献/PDF/2019_LIGHT_Learning_to_Speak_and_Act.pdf`，11 页，SHA-256 `18226b3a54122cd0c5e9629cf0addf4cb015ab7d28b64c51ba131d0e5547b350`。
- 正文 §3（PDF pp. 675–676）说明两名人类扮演幻想角色，每轮可说话并做物理动作或 emote，角色有 persona/环境信息；§4 和 §5.4 说明预测任务使用 dialogue、persona、环境、自身/伙伴动作等不同通道。它不定义 `small7` 的每数组写入时点，也未给出 speech 与 action 在原始 pickle 内的先后序列化约定。
- 官方 ACL attachment：[直接下载 ZIP](https://aclanthology.org/attachments/D19-1062.Attachment.zip)，本地临时副本 `/private/tmp/light-acl-attachment-JKziCl/D19-1062.Attachment.zip`，ZIP SHA-256 `315201aee5044008be48e4b1d464abd264d2ed117f4a6ada972b2b848ec67af5`。提取的 23 页 PDF 暂存于 `/private/tmp/light-acl-attachment-JKziCl/LIGHT-Appendix.pdf`，SHA-256 `d686e280b1a8425f8f3f0c8f97cb008766ef2379ff46ea04b14d9aacea3f3d18`。Appendix D（附件 PDF pp. 4–5）描述 Task 6 的双人角色互动与 onboarding；Figure 9（附件 PDF p. 13）截图可见 worker 自己的 Persona 与 Setting、伙伴消息/动作 feed、动作下拉框（截图当前显示 “Speak only”）及自由文本 speech 输入框。该图是论文的 worker UI 证据，但未能证明 small7 pickle 由该 exact 页面版本或 exact logger 生成。

### 2. 精确到提交的历史官方 ParlAI 源码

本节采用 GitHub 官方仓库提交 [`d4e3b1c76360bcf72cbae541834f8cd38f5449ee`](https://github.com/facebookresearch/ParlAI/commit/d4e3b1c76360bcf72cbae541834f8cd38f5449ee)，提交日期 2019-03-21，主题为 “MTurk tasks for LIGHT #1551”。固定源码链接：

- [`light_chats/worlds.py`](https://github.com/facebookresearch/ParlAI/blob/d4e3b1c76360bcf72cbae541834f8cd38f5449ee/parlai/mturk/tasks/light/light_chats/worlds.py)；Git blob `5c3e813e8d25a8d1016314f9120a53176082861d`。
- [`light_chats/frontend/components/custom.jsx`](https://github.com/facebookresearch/ParlAI/blob/d4e3b1c76360bcf72cbae541834f8cd38f5449ee/parlai/mturk/tasks/light/light_chats/frontend/components/custom.jsx)；Git blob `bd3ba21881a15e464ba0219f49cd67fd2797ea14`。

直接源码观察（行号指上述固定提交版本）：

- `worlds.py:146–156`：`get_context_actions_for` 对当前 actor 执行 `look`、`inv`，从图状态产生当前 `context` 和 `graph.get_possible_actions(...)`。
- `worlds.py:158–195`：启动每个 worker 时传入该角色的 persona、setting/context 和 actions；任务指示 worker 了解 partner persona，但该 task-data 片段直接传的是当前 worker 角色的 persona。
- `worlds.py:197–250`：每位 worker 的一次 act 同时包含文本 `a['text']` 和 `task_data['action']`；物理 action 经 `graph.parse_exec` 执行，世界状态更新后 actor 收到刷新的 context/actions；随后 partner 收到该轮 speech，以及更新后的 setting/context/actions。物理动作给 partner 的 `task_data.action` 是 `graph.get_text(other_agent_name)` 产生的结果描述，而非直接转发源物理命令字符串；gesture 则作为 gesture 字符串转发。因此，**raw physical `action[t]` 与 partner 当时看到的动作表述之间有 representation gap**。不能把源命令直接当作 partner-visible observation。
- `worlds.py:284–293`：`get_custom_task_data` 提供 `acts`、`room`、`characters`、`graph_copy` 等任务日志相关对象。这证明该 world 有哪些可供记录的对象，不证明这些对象如何被转换为 small7 的 per-turn arrays。
- `custom.jsx:24–29, 41–53, 77–111, 132–142, 181–217, 221–256`：前端将给定 `task_data.actions` 显示为 action selector；action 和文本一并提交；worker 有 free-text 输入；对话区显示伙伴消息及 task-data action；右侧显示传入的 persona 和 setting。

### 3. exact producer 链查找结果

检查了该 March commit 的**官方 ParlAI 完整递归 tree**，包括 `parlai/mturk/tasks/light/light_chats/`、`parlai/tasks/light_dialog/` 及其 builder/build/worlds 文件。查到下游 `light_dialog` builder/build，可加载 processed pickle 并建立模型 teacher examples；**未找到** MTurk `acts`/`graph_copy` collection log 写成 `light-dialog-processed-small7.pkl` 的 exact converter、exporter 或 serializer。因此 UNKNOWN 应精确限定为：

> March worker-world 记录对象 → 论文所用 processed `small7` pickle 中 `context/action/available_actions/speech/emote/agents` 等字段的映射、时序与版本对应关系。

这不是“2019 LIGHT worker 接口完全未知”：官方 March world 与论文附录界面可核实部分交互机制；缺口是其与当前本地处理文件的 exact producer/array mapping。

### 4. 本地原始文件与 adapter 的核验边界

- 本地 source：`outputs/external_assets_2026-09-06/LIGHT/light_data.pkl`，SHA-256 `7c83cf49818586db9999ea67a4a6ad087afbd91c26ed629a9f00e21d0b84058f`。下载来源及同 hash 记录于 `02_实验/T0c_LIGHT/light_dialog_build.py`。
- 本地 [adapter `export_replay.py`](../../02_实验/T0c_LIGHT/export_replay.py) 在物理动作非空时，将同 raw index 的 `context/action/available_actions` 复制到一步记录，并把同一 raw index 的 speech/emote 放在 `source_step_context`；它是复制实现，不是原始 collector 的时间契约。
- [来源 join audit](source_join_v2.json) 使用物理动作非空项建立 physical-index → raw-turn 映射后核验：13,463 targets 的 `source_O`、gold action、candidate list 与规范化 actor 均与对应 raw entry 相同；13,456 条同一 raw turn 有非空 speech；13,152 条 physical index 与 raw-turn index 不相等。该证明的是 adapter 字段对应与 speech 同步存储，**不是**其相对 action 的可见/可预测权限。
- 全量 raw 结构核验（主代理独立复核）：13,463 个 target 均可匹配 self persona，且每条都有严格先前 partner speech；9,397 条有严格先前 partner physical action。此处不主张每条都有严格先前 self speech。它证明对应 history 通道在 source 中存在，不证明所有动作以原字符串形式对对方可见。raw `agents[]` 的角色/persona 关联是来源元数据；不能把两角色 persona 同时喂给当前 actor。`all_descriptions` 是 episode 级环境描述集合，而非已证明的 actor 当前可见集合。

## 通道判定与最小重建边界

| 通道 | 可核实事实 | `small7` 当前准入判定 |
|---|---|---|
| 当前 `context[i]` | March world 在 worker 做动作前计算当前 actor 的 look/inventory context；动作后又会刷新并发送新 context。 | **时点 UNKNOWN**：无 exact log→small7 converter，不能认定每个存储的 `context[i]` 是 action 前还是后。若做候选重建须保留 source O 原值和 raw-turn provenance，并显式标 temporal status unknown；不能靠字段名/与论文概念对齐填补。 |
| `available_actions[i]` | March world 从图状态产生合法动作并送入 action dropdown；动作后更新候选。前端显示 dropdown 与 Speak only。 | **记录 support only**：small7 候选对应的是动作前列表还是更新后列表未闭合；不宣称 `A^O`、worker 每轮确实看全列表或最终选项无 UI/过滤差异。 |
| 当前 speech 与 physical action | 论文称每轮可说话和做动作/emote；March UI 将自由文本及所选 action 在一次 `onMessageSend` 中提交。 | 视作来源中同一 actor event 的 co-recorded 字段；精确 `small7` serialization 时序 UNKNOWN。不能无条件把同轮 speech 加入预测当前 action 的输入。 |
| 先前 self/partner speech、action、emote | raw pickle 中各 per-turn arrays 保留；source code 的轮流处理使先前 event 发生在后续 worker action 前。Partner 收到物理动作的图文结果，gesture 是字符串。 | **候选 history 可先限定严格过去并保留角色与原始表示**；但 raw physical command 不是已证实的 partner observation 内容，不能直接称为完整 `H^obs` 或证明充分状态。候选仅是 recorded-history reconstruction，准入仍待审。 |
| persona | March world 把当前角色 persona 传给该 worker；附录 UI 截图显示 worker 的 persona 面板；任务文字鼓励了解 partner persona。 | `agents[]` 可作 provenance 与 self-persona 对照；不得因 records 同时保存两角色 persona 就将 partner persona 当作 actor-visible 输入。未证实的 partner persona 访问继续排除。 |
| `all_descriptions` / room objects | March task-data 直接暴露当前 actor 的 setting/context/actions；`get_custom_task_data` 另含 world/log 对象。论文建模使用环境/物体 grounding。 | episode 全描述集合不是已证明的 worker 可见通道；不得直接扩展成 `O`。优先只从经确认的 actor context 提取；source 级全描述保留作环境/来源元数据，待逐项验证。

**最小可重建 candidate（不等同正式准入）：**对目标 actor，在当前 target 之前严格按 raw turn 排序的两角色记录 speech、emote、physical action，以及角色身份与 self-persona 关联；每个字段保留原文、raw turn index 和 source provenance。partner physical action 必须标 `recorded command; partner-visible realization unverified`，不能伪装成 UI 显示文本。当前 O、candidate support、当前同轮 speech/action 的 before/after 边界均记 UNKNOWN/PENDING；不加入未来事件、未证实 partner persona 或全局 `all_descriptions`。若协议要求合法 actor-visible `O`/`A^O`，这份候选本身仍不足以过 Paper-0 formal admission。

## 不可据此推出

1. 不能由 March UI/source 推出 local `small7` 每条 context 或 candidate 精确在 action 前记录。
2. 不能由 source arrays 同索引或全量 join 通过推出人类确实看到完整 `available_actions`、伙伴动作原始字符串、两角色 persona 或 episode 全部 descriptions。
3. 不能把当前物理动作子序列称为完整角色观察历史，亦不能由 prior speech 存在就断言其对所有 target 有预测增益。
4. 不能由本次來源链核验推出心理状态、心理因果、新颖性或 Paper-0 形式准入。

## 当前执行边界

本审计未修改原始 pickle 或其来源文件；本地 join 核验仅读取数据，没有运行训练/实验。证据还包括已锁定来源 hash、现有 join audit、官方论文/附件与固定历史源码。`PredictionBaselineV1` 的 development 实现与 formal Paper-0 的 NO-GO 是不同状态：本来源审计不维护实时 implementation/training 状态，按当前开发协议和研究重建审计路由。
