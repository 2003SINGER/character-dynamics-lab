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

文件名更正：独立 review 当前为 `command_admission_review_independent_v0.jsonl`；它不得解释为 human gold。

盲审文件 `command_admission_audit_semantic_v0.jsonl` 已形成 289 条标签：`valid_command` 76、`ambiguous_command` 173、`chat_or_commentary` 8、`meta_command` 32。该轮为保守的确定性 raw-action + pre-state 审查，不是人工逐条裁决；因此这些标签可作为 blocker 诊断，不应冒充高置信 gold。

另做了一次独立盲审 `command_admission_review_independent_v0.jsonl`（不读取前一轮标签）：`valid_command` 209、`ambiguous_command` 18、`chat/commentary` 23、`meta_command` 39；高置信 253/289。两轮标签一致率仅 100/289（34.60%），说明在没有人工 adjudication protocol 前，任何单轮标签都不能作为最终 precision 估计。

机械 `command-like` 100 条在旧 reviewer 体系下被分成 34/57/9，但这不是 precision 估计；两轮 reviewer 的分歧来自 admission 问题被错误地混入 world-legality/target-evidence 判断。按 corrected v1，失败或世界拒绝不应剔除 observed `A*`。

**当前 gate：FIX_ONE_BLOCKER（先修复动作质量/语义准入边界，并完成少量人工 adjudication 以校准两轮分歧）。**

已冻结 corrected `A^W / A^O / A*` 定义，并从两轮分歧中生成 60 条人工 adjudication sheet。人工 adjudication 只回答“是否代表玩家在游戏内选择/尝试行为”，不判断 `A^W` 合法性、执行成功与否或 target 是否被 pre-state 证明存在。完成后若 `IN_WORLD_CHOICE` subset 足够且边界/泄漏检查继续通过，即可进入 `GO_TO_REPRESENTATION_BASELINE`；不再进行第三轮模型全量 review。

## 不变边界

本审计不修改 Theory-S，不训练任何参数，不构造 W、persona、candidate set 或内部状态，不把游戏反馈重写为角色动力学状态。
