# ClubFloyd command-admission audit v0

审计对象：全量 `clubfloyd_full.replay.jsonl`（425 trajectories / 438,188 steps）。本次盲样本由固定 SHA-256 排名在四个质量层内抽取，样本文件与 manifest 可复现。

## 样本与边界

- 样本：`command_admission_audit_sample_v0.jsonl`，289 条；command-like 100、ambiguous 100、chat/commentary-like 47、meta-command 42。
- 盲审可见字段仅为 `raw_action` 与 action 前的 `pre_action_state`；样本不含 post-state、reward、future action 或 parsed 字段。
- 全量机械质量层：command-like 218,575；ambiguous 219,524；chat/commentary-like 47；meta-command 42。
- 机械质量层不是语义准入标签；尤其 ambiguous 不得自动升格为 verified command。

## 冻结评估器

`evaluate_command_v0.py`（schema `command_evaluation_v1`）固定输出：raw exact、normalized exact、verb exact、target exact、modifier exact、semantic match。semantic match 使用固定 token signature、有限别名（如 `i→inventory`、`x→examine`、`get→take`）与冠词移除；不读取 post-state，不接受 prediction 自报的 semantic_match，也不把 review classification label 当作命令等价性。

## 结果与准入门

盲审文件 `command_admission_audit_semantic_v0.jsonl` 已形成 289 条标签：`valid_command` 76、`ambiguous_command` 173、`chat_or_commentary` 8、`meta_command` 32。该轮为保守的确定性 raw-action + pre-state 审查，不是人工逐条裁决；因此这些标签可作为 blocker 诊断，不应冒充高置信 gold。

机械 `command-like` 100 条中仅 34 条被判为 `valid_command`，57 条仍 ambiguous，9 条被判 meta；这说明现有 quality heuristic 明显过宽，不能直接产出 `verified_command_like_v0`。

**当前 gate：FIX_ONE_BLOCKER（先修复动作质量/语义准入边界）。**

允许的下一步是：收紧 quality/admission 规则并补做独立人工 gold，再运行冻结评估器报告 raw/normalized/verb-target-modifier/semantic 指标；在此之前不得进入 GO_TO_REPRESENTATION_BASELINE 或机制训练。

## 不变边界

本审计不修改 Theory-S，不训练任何参数，不构造 W、persona、candidate set 或内部状态，不把游戏反馈重写为角色动力学状态。
