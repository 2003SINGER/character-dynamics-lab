# 配对短轨迹开发协议 v1

本轮属于阶段 2—3 的 **DEVELOPMENT exploration**，不是预注册玩家实验、正式效应估计或新机制验证。先前单独 utility / LLM trace 已用于开发，均保留，不与本轮配对结果混算。

## 要回答的问题

在同一个房间中，已有目标正在执行，发生可见干扰后，两种简单基线实际怎样响应、继续或切换？若行为不同，差异能否从真实动作和可见事件理解，还是必须依靠调试状态、理由或人为剧情解释？

utility 的评分/惯性和历史 LLM 的 v1 prompt 在本轮不调参。允许修输入、执行与统计契约缺陷，但必须保留失败记录并说明影响；不能看结果后给某个案例补答案。我们不预设“必须立刻关闹钟”“必须学习到完成”是玩家认可的唯一正确行为。

## 固定案例与配对条件

| 开发案例 | 初始时间 / World setup | 用途，不是正确答案 |
|---|---|---|
| `alarm_active` | Day 1 08:45；自然 coursework effort 0 / target 8；StudyFocused 35 min | 自己的事进行中，09:00 真 World alarm 可知；观察响应、保留或切换与其成本。 |
| `quiet_active` | Day 1 09:05；effort 0 / target 8；StudyFocused 35 min | 当前短窗无新的 alarm；09:30 真 study message 是弱事件。检查正常继续是否被无故解释成“不响应”。 |
| `near_completion_alarm` | Day 1 08:45；effort 7.7 / target 8、Active；StudyFocused 35 min | 同样干扰但目标接近完成；检查简单惯性/低剩余效用是否妨碍推进，以及真实完成后不继续的合理反例。 |

每个案例是**新建 World 的明确初始状态**，不是将 Day 1 08:00 起的事件自动重放到起点；`quiet_active` 的起点不意味着此前角色听过闹钟。修改 effort 只在构造阶段，不制造 action feedback。所有初始动作由 scenario setup 给出并接受 W validation，不称为自主目标选择结果。

每案例两条条件共用 World seed 0、policy seed 17、同一初始 W/O、InformationAccess、Reference X/S law、application gate、硬候选与 nominal action duration。只换 `UtilityPolicyV0` / `HistoryLlmPolicyV0` head。后续行动不同导致 O/history/决策时刻自然分岔；不强迫后续输入相同。候选、gate 与初始实际决策机会必须审计，而不是凭类名假定相同。

每条计划运行精确 **90 simulated minutes**；每条最多 32 次真实 policy 选择、1000 boundaries，无自动 retry/fallback。call limit、error、boundary limit 独立报告，不能冒充全窗完成。6 条短轨迹只是排错与探索，不计算组间显著性、置信区间或群体发生率。

## 执行、展示与读数

- interval `[from, at)` 归给 `running_before`；`selected_action` 是 at 后的选择，不占已过去时间。动作启动、成功结算、被打断和同 intent 保留进度分别记。
- task completion 只能来自真实 typed completion outcome / 对应可见 O；不从 effort >= 1 或动作次数推断。rejection 只数 performed validation 且拒绝，不把默认 false 算拒绝。
- 原始 debug trace 保存完整时间、O、actor history、候选、typed outcome、W debug、policy provenance 和错误。请求使用 actor-visible O/history/RunningAction，不发送 W、S/P 或 utility score 给 LLM。
- 玩家回放另导出白名单 payload；网页不读取原始 trace 后再隐藏。只画真实动作、可见事件和公开任务信息，不显示 method identity、内部状态、分数、理由或人为剧情 note。同一 typed 行为不因模型身份或修辞不同而得到不同展示。
- 回放可播放/暂停/定位，但**不可玩、没有玩家 World 输入**。不伪造点击产生的 O event；真正交互场景的输入 seam 留待明确接口决策。
- 成本报告实际 HTTP calls、API token 与 HTTP wall time；utility 的“没有 HTTP 调用”不等于 CPU 成本为零。context truncation、解析失败和被 cap 截停均属于读数的一部分。

父 agent 逐条读完六条 trace 与实际请求，并查看匿名回放。自动 audit 只作契约/账本检查，不输出“生命感”或心理病态分数。合理不响应、同动作继续、完成后不再学习均保留为反例；若所谓差异只能靠 debug 理由辨识，应先改场景/呈现，而不是扩大批次或加 S 字段。

## 本轮停止点

交付逐案成功/失败/不确定性、可观看回放和成本账本后，停在阶段 3 检查点与用户讨论。最多得出这些案例中明确的 baseline / candidate / gate / execution / presentation 瓶颈，不能推出持久记忆、情绪或人格必要。未验证的玩家感知、强模型对比与真正交互仍列为缺口；不自动进入阶段 4。
