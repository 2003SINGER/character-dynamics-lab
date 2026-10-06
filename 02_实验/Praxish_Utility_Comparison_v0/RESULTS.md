# 结果与研究判断｜Praxish / parameterized utility v0

日期：2026-10-07。**DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW**，不是方法胜出、玩家验证或正式 closure。父代理审查与命令见 [PARENT_REVIEW](PARENT_REVIEW.md)。原件机制依据见[论文/源码审读](../../01_文献/精读_Praxish论文与原始实现_2026-10-06.md)。

## 观察结果

父代理 fresh run `parent-final-comparison-20261007-01` 位于项目内 `outputs/praxish_utility_comparison_v0/runs/`。它记录源码 pin、七项输入/依赖哈希、执行 Git HEAD 和 worktree 标记；不把未提交执行冒充 exact-head 执行。后续最终运行以 PARENT_REVIEW 的精确 run ID 为准，不使用“最新目录”定位。

| 条件 | 实际行为 / 失败 | 匹配结果 |
|---|---|---|
| 无请求 | worker 在 turn 0 开始、turn 2 完成 | 候选、角色、分数、事件、前后状态一致 |
| 普通请求 | turn 1 请求进入，turn 2 响应，turn 4 完成原工作 | 一致；请求没有脚本化指定响应 |
| 低优先级请求 | turn 2 先完成工作，turn 4 响应 | 一致；只降低作者配置的请求目标权重 |
| 第二对 worker / visitor | 两对分别服务、完成自己的工作；12 turns | 一致；动作模板复用，目标仍指向各自 worker |
| 同 worker 两个请求 | 两个请求都服务，再完成工作；12 turns | 一致；两个 served 匹配贡献 20，总分另含工作状态 |
| 工作区关闭，未适配 | 两边都在 turn 2 违规完成 | **parity 不等于正确**；两侧失败均保留 |
| 工作区关闭，补前置条件 | 关闭期间无 Finish，重开后 turn 6 完成 | 两边均能用一条条件修复 |
| 平分候选 | 32 个 seed 的选择逐一匹配，两种最大分动作都出现 | 确定性不意味着每个 seed 选择相同动作 |
| 原件 cancellation | 两个 visitor 候选是同一对象，都被改写为 Cancel | **不匹配**；普通权重下动作序列恰好相同 |
| 原件 cancellation，负权重 | native Wait=0 > Cancel=-1；原件仍选择 Cancel | **不匹配且公共动作序列不同**，不是活动组织收益 |
| 两个 explicit-binding workaround | 条件显式绑定 Status 后候选对象分开 | 均恢复匹配；上游源码没有修改 |

共 12 个案例，10 个逐回合 parity 通过，2 个保留为已诊断的上游差异。单独注入错误 action effect、actor role、workspace filter 的三个负控都能被检测；它们不是自然场景失败。早期真实失败目录与合成 CLI 故障测试目录分开保留，不重新命名为成功。

## 实际追加了什么

每个扩展保存两侧 `before.json / after.json / diff.json`，以及共同 seed、turn horizon、actor 顺序、事件与世界 contract；diff 重放必须恢复 after。以下是内容改动，不是人类工时估计。

| 变化 | 平面 utility | Praxish 活动内容 |
|---|---|---|
| 新的取消行为 | 加一个角色绑定动作及 visitor goal | request practice 加动作，visitor 加 goal |
| 负取消动机 | 改 Cancel 目标权重 | 改对应 goal utility |
| 第二对角色 | 增加实体绑定，不复制动作模板 | 新活动实例、角色和目标实例，不复制 practice 定义 |
| 同 worker 第二请求 | 增加 Visitor 实体；原服务模板/目标匹配复用 | 新请求实例；原 practice/泛化后的 Visitor goal 复用 |
| 关闭后禁止完成 | Finish 加 workspace-open 前置条件 | Finish 加同义 condition |
| 原件对象别名 workaround | 不改 baseline | 一条条件改为 Status 变量绑定，再加 pending 等值检查 |
| 平分情形 | 请求权重改为 4 | 同义目标 utility 改为 4 |

**调试记录**见 [DEVELOPMENT_LOG](DEVELOPMENT_LOG.md)：包括实际路径错误、角色顺序、比较器 key order、事件投影、误把总分 21 当服务贡献 20、8-turn horizon 不足及原件别名问题。原始进程 stderr 没有全部单独保存，因此不编造精确人工调试次数或时间。AI 修改量、JSON diff 数和人类作者成本不能互相替代。

## 第 4 步能判断什么

**可观察证据：**共同 timeline 只含 turn、actor、action。除原件负取消权重 bug 外，两侧公共动作序列相同；同样映射到展示动作时，没有由动作序列本身提供的方法差异。它不是完整游戏视听呈现，也不是玩家实验。

**研究判断：**在这个有限、全信息、一步绝对 goal-utility 的场景中，不支持以“活动组织产生更好行为”为理由立项；简单工作恢复、请求优先级与关闭条件不足以迫使我们提出新心理机制。不能由此否定活动组织在更复杂作者工作流中的价值。

**未获得的证据：**真实作者维护/迁移成本、玩家感受到的自主性/连贯性、真实 RPG 约束下的机制缺口。第 4 步的玩家意义和具体 gap 尚未验证，不能把 1—3 的运行通过写成全部研究目标完成。

下一研究检查点是“组合变化的维护瓶颈是否存在且玩家在意”，不是继续扩大这个 toy 的 seed 数或调参制造胜者。具体候选需对照 ScriptEase / 活动式方法与合格 utility 的已有能力；本次结果不授权新机制、训练或玩家招募。
