# 阶段 1—3 开发检查点（2026-10-06）

**状态：DEVELOPMENT / READY_FOR_DISCUSSION。到这里停，未进入阶段 4。** 问题选择、两种可执行基线、同条件短轨迹与统一回放已形成第一轮开发闭环；玩家可置信性、强基线充分性和新机制收益均未证明。这里不是整个研究目标的 CLOSED。

## 实际完成了什么

按[固定开发协议](DEVELOPMENT_PROTOCOL_V1.md)运行三案例 × 两 policy，各精确 90 分钟。所有初始动作经过 W validation，后续走同一 ContinuousRuntime；没有脚本化替 policy 选择答案。父 agent 核读六条 trace 和全部 11 次真实本机 LLM 请求，并独立重算请求 hash、候选映射、时间归属与成本。

三组的初始 setup/O/RunningAction，以及首次真实决策的 O/clock/history/硬候选逐项相同。后续行动自然分岔，未强行同步后续输入。六条均正常到 horizon，无 retry/fallback、解析失败或 cap 截停。原 Runtime、World、Reference/Demo law、系数及 schema 未改。

| 开发案例 | Utility v0 的实际行为 | Qwen3-4B 历史 LLM 的实际行为 | 当前能说什么 |
|---|---|---|---|
| 学习中遇到闹钟 | 09:00 关闹钟，09:01 回到电脑学习 | 09:00 换为 StudyHalfhearted，09:35 换为电脑学习；闹钟未关闭 | 两者仍推进任务；“没关闹钟”本身不是病态判据。替换均丢弃原动作已执行 15 分钟的未结算 task effort，这是冻结执行语义的成本。 |
| 没有新闹钟的学习窗 | 弱消息到来不打断，完成一段后继续学习 | 与 utility 的动作、可见事实、进度和时间完全相同 | 当前小窗没有观察到新增历史 LLM 的行为收益；不是证明历史一般无用。 |
| 接近完成时遇到闹钟 | 09:36 真 `task_completed=true`，随后 Idle | 09:35 effort 达 7.962369/8，O 仍为 `active`；学习候选仍在，随后 Idle 40 分钟，任务未完成 | 值得核查的任务状态/决策差异，不能直接命名“忘记目标”或心理崩坏。 |

最后一例不是候选被过滤、时钟 stale 或没有提供历史：全部实际请求均含已知 active 状态、真实进度/target、学习硬候选和供给的完整 actor ledger。**“输入提供了事实”和“模型按我们预期使用事实”是两回事。** 可疑原因包括近完成数值解释、选择优先级、prompt、模型能力和候选顺序；本轮没有做能区分这些解释的干预，也没有生成事后心理理由。

## 可观看证据与成本

本机非覆盖 run：`outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/`。其中保留六条 raw JSONL、三份 HTTP journals、模型日志、执行源码/二进制 SHA、manifest 与 audit；`player/index.html` 是可双击打开的六片段匿名回放，浏览器不加载 debug trace。

呈现仅使用真实 RunningAction 和白名单已知 O：实际房间对象、公开任务进度、闹钟/消息 cue。按模拟分钟比例播放，区间归 `running_before`，边界后才换新动作；相同 quiet 轨迹导出的 frames 完全相同。active 的 99.5296% 显示 99.5% 且仍标“进行中”，不因 rounding 冒充完成。父 agent 实际浏览器验证了播放终点、两种完成状态及匿名选择器，无页面错误。CSS 小人只是展示占位，页面没有玩家 World 输入，不冒充可玩游戏或正式盲评。

本轮历史 LLM 共 **11 次调用、18,643 API tokens、累计 HTTP wall time 63.692 秒**；三案例分别 3/2/6 次。Utility 选择次数为 4/2/6，无 HTTP 调用，CPU 延迟未测，不写成零成本。请求串行，latency 含本机 prompt-cache 等因素，不是公平硬件速度 benchmark；窗口终点若恰好完成动作，也可能作出一个尚未执行的新 intent，该调用仍计成本，但不分配已过去时长。

模型为既有 Qwen3-4B Q4_K_M，SHA `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`；llama-server build10809/`5266f24da`、ctx 16384、temperature 0、thinking off，无 context shift。模型服务已关闭。源码当时尚未提交，实际字节由 run 内 hash 标识，不能把 compiled revision 冒充干净的提交后执行。

## 这一轮的瓶颈判断

1. **没有证据支持立刻开发新持久 S / 情绪 / 记忆机制。** 简单 utility 已能在这个单目标 fixture 中处理中断、继续和真实完成后停止。LLM 的可疑例同时有完整供给历史，不能归因为缺一个记忆池。
2. **先确认这个差异是否真是玩家在乎的差异。** 统一回放已能呈现“任务真完成后停”和“任务还 active 时停”，但尚无人类评价；休息或不回应某个干扰也可能合理。任务完成率不是“活起来”的代用品。
3. **若玩家在乎，先排除弱基线/简单替代解释。** 本轮 utility 是有固定 alarm/task 偏好的透明手写实现，LLM 是小模型；不是成熟产品 NPC 或经过验证的强 LLM 对照。不能据此宣布 utility 类方法优于 LLM，更不能用它证明我们的新机制必要。

其他边界：初始 Study 为 scenario setup，不是自主立目标；身体需求与多目标日常策略不在 utility 的覆盖内。Kernel 的 actor ledger 在首次 boundary 才捕获 setup 中 pending 的初始 O facts，该时间不能解释为它们首次进入世界/角色认知的时间；本轮不据此研究记忆时效。展示 cue 因此按已知可见状态的真实变化生成，不把重投递的初始 facts 演成新事件。没有隐藏干扰的完整 Runtime 对照，也没有独立 test 条件、玩家样本、效应估计或正式评价量表。

## 下一项决策：先讨论，不自动写机制

建议用户/GPT 先看匿名回放与这份证据：是否能辨认并在乎这些行为差异？如果不能，先改场景/展示；如果在乎，决定先补较强基线或简单任务状态约束对照，还是已有足够具体的失败机制值得研究。只有讨论后才决定是否进入阶段 4。本次不再追加长批次、训练或 Runtime 工作。
