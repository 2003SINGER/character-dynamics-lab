# ClubFloyd dev slice｜初步语义审计 v0

审计对象：全量 `clubfloyd_full.replay.jsonl`（425 条 trajectory / 438,188 steps）及 300 条 review fixture。这里是 adapter 的逐字段审计记录，不是机制实验结果。

## 结论

**结构上可进入人工语义复核；当前准入状态：source-labeled only，未冻结 semantic annotation。**

| 检查 | 结果 | 说明 |
|---|---|---|
| trajectory 切分 | 通过 | 一个源 HTML 文件对应一条 transcript；按文件名稳定生成 `trajectory_id`，不跨文件拼接 |
| `source_O` | 通过（格式层） | 每个字段取 `[STATE]` marker 中、对应 `[ACTION]` 前的文本；没有把下一 state 拼入当前 state |
| `source_action_A_star` | 通过（来源层） | 原样复制 `[ACTION]` 文本；不压缩到本项目 16 类动作 |
| 系统文本/命令/反馈边界 | 通过（格式层） | 游戏反馈进入 `source_O`，玩家命令进入 `source_action_A_star`；原始 pair 在 `source_step_context` 再保留一份 |
| `W` / persona / state | 保持 unknown | transcript 不提供可证明的角色内部状态、人格或完整客观世界 |
| candidate sets | 保持 unknown | CALM transcript 没有可复核的当步合法候选集 |
| provenance | 通过 | `source_O` 与 `source_action_A_star` 均标为 `observed`，无 LLM 推断 |
| future leakage | 格式检查通过，语义复核待人工 | parser 只读 action 前的 state；仍需人工抽查 HTML 异常和 transcript 边界 |
| source action quality | 已完成机械分层 | command-like 218,575；ambiguous 219,524；chat/commentary-like 47；meta-command 42；不得直接等同 `verified_action_A_star` |

## 不应过度解释

ClubFloyd 的 `source_O` 是文字游戏反馈，不等同于本项目定义的完整角色 `O`；`source_action_A_star` 是外部回放中的命令，不证明当前角色动力学已经能解释它。该切片只能用于 adapter/字段边界开发，不能直接进入 mechanism loop。

## 下一步

对 `ClubFloyd_review_v0.jsonl` 的 375 条分层夹具进行人工抽查：覆盖全部 47 条 chat/commentary-like、42 条 meta-command，以及 command-like/ambiguous 分层样本；确认异常 marker、重复 transcript、跨 episode 拼接、动作是否确为玩家命令。通过后再生成冻结的 semantic annotation 文件。未完成前不进入 mechanism loop。
