# ClubFloyd command-admission audit v0

审计对象：全量 `clubfloyd_full.replay.jsonl`（425 trajectories / 438,188 steps）。本次盲样本由固定 SHA-256 排名在四个质量层内抽取，样本文件与 manifest 可复现。

## 样本与边界

- 样本：`command_admission_audit_sample_v0.jsonl`，289 条；command-like 100、ambiguous 100、chat/commentary-like 47、meta-command 42。
- 盲审可见字段仅为 `raw_action` 与 action 前的 `pre_action_state`；样本不含 post-state、reward、future action 或 parsed 字段。
- 全量机械质量层：command-like 218,575；ambiguous 219,524；chat/commentary-like 47；meta-command 42。
- 机械质量层不是语义准入标签；尤其 ambiguous 不得自动升格为 verified command。

## 冻结评估器

`evaluate_command_v0.py` 固定输出：raw exact、normalized exact、verb exact、target exact、modifier exact、semantic match。规范化仅做 trim、casefold、连续空白折叠；不改变原始命令字段。

## 结果与准入门

当前已完成可复现的全量分层与盲样本边界检查；语义标注文件尚未形成可审计的独立 gold，因此本轮不得把机械 command-like 计数当作 `verified_command_like_v0`。

**当前 gate：NO_GO（语义准入未闭合）。**

允许的下一步是：由盲审者仅基于上述两个字段补齐语义标签，运行冻结评估器，报告 raw/normalized/verb-target-modifier/semantic 指标；在此之前不得进入 GO_TO_REPRESENTATION_BASELINE、FIX_ONE_BLOCKER 或机制训练。

## 不变边界

本审计不修改 Theory-S，不训练任何参数，不构造 W、persona、candidate set 或内部状态，不把游戏反馈重写为角色动力学状态。
