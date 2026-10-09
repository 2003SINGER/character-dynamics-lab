# NPC System Integration v0

2026-10-09 用户将“只维护外围”改为“可以改，按目标 TXT 来”。本目录是对此授权的**有限应用集成开发样机**，不是 E1-2 正式实验，不改冻结 C++ Kernel/E0/E1。状态与逐例证据唯一见 [RESULTS](../../02_实验/NPC_System_Integration_v0/RESULTS.md)。

## 跑起来

从仓库根目录，Windows PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/npc_system_v0/requirements.txt
$env:PYTHONPATH = "$PWD\tools"
.\.venv\Scripts\python.exe -B -m tools.npc_system_v0.runner --suite
.\.venv\Scripts\python.exe -B -m tools.npc_system_v0.runner --planner htn --author-json tools/npc_system_v0/examples/author.json
.\.venv\Scripts\python.exe -B -m tools.npc_system_v0.runner --no-director --policy PAY
.\.venv\Scripts\python.exe -B -m unittest discover -s tools/npc_system_v0/tests -v
```

已建立 `.venv` 时不必重复第一行。不启动模型服务、不下载模型、不调用外部 LLM。macOS/Linux 使用 `python3 -m venv .venv`、`.venv/bin/python` 和 `PYTHONPATH=tools`。产物默认在不可覆盖的新 `outputs/npc-system-v0/<timestamp>/`；显式 `--out` 若已经存在会报错。

## 真实执行链与 owner

```text
作者分层点/线/事件/顺序要求 → TypedIR 编译与监测
              ↓                        ↑ 实际封存证据
受限世界规划：NO_OP / 公开激励 → W 校验 → 单时钟结算
                                      ↓ 合法 O 传播
角色自己的 O/H/P → X → S → 目标/承诺 → GOAP 或 HTN
                                      ↓ 只提交下一步意图
                              W 校验 → RunningAction → 收据
```

| 责任 | 代码 | 输入/输出与权限 |
|---|---|---|
| 角色状态、语义与目标协调 | `model.py` | 自己的 O、S、固定 P、时钟/任务截止 → 可查 X → 新 S 与目标优先级；模型可替换 |
| A 局部规划 | `planners.py` | actor-local view → prediction-only 多步提案；GOAP/UCS 或真正 GTPyhop HTN；只执行首项 |
| B 自主选择 | E1 `policy.choose_b`，本应用 adapter | B 自己公开可见的机会与目标 → 接受/拒绝/交换；A 的 forecast 不执行 B |
| 世界干预规划与未来修复 | `System.world_proposal` | 当前已提交前缀、作者要求、合法机会 → 隔离预测的候选比较；每次边界重新规划未来 |
| 真实物理执行 | `executor.py` → E1 → E0 | start validation、唯一时钟、RunningAction、重新检查完成前提、收据及 seal |
| 作者监测 | `author.py` → 既有 TypedIR | 真实 snapshots + receipt-backed ledger → SATISFIED/VIOLATED/PENDING/INDETERMINATE；不是可达性求解器 |

这里只增加职责不同的接缝，不引入统一 AlgorithmPlugin、加载器/注册工厂或第二套世界执行器。替换 `ContextDriveV0`/`MonotoneAvoidanceV0` 改变 S 到目标优先级的响应；替换 GOAP/HTN 改变规划算法但继续服从同一 executor。高层 LLM、通用 inverse response、角色关系/ToM 和开放场景绑定仍未实现；不能把本次 HTN 搜索写成已接入 LLM。

## 有限域、权利与成本

沿用 E1 的 A/B、坏掉的 key0、B 的 key1、账本、支付品与借来的 toolB，绝对模拟分钟 **t=2..10**；沿用 E0/E1 一次一项控制的有限协议，不宣称通用并发多 NPC 世界。世界自然推进仅含原有时钟、动作进度、固定期限；角色 S 每个真实边界更新，日常 work/rest 保留。没有城市生态、经济或长时程生活验证。

- 作者可以提供全局、场景、片段多个 `levels`，其约束合取检查。分层元数据保存在每条 run 中；**层级不是 NPC 行为脚本或自动任务分解规则**。示例同时要求资源不为负的线、账本事件、同意先于取得的顺序，以及终点持有状态。不能只用最终持有替代取得事件。
- 世界导演只有 `publish_incentive(DIRECTOR, bonus=2)`：持续 1 分钟、消耗 2 个世界 credit、一次性公开预付的借钥匙激励。只能在尚未报价、钥匙完整且预算足够时发布。该预付机会令 B 原有收益计算增加 2，不改变 B 的基础成本/人格；原有支付品交换仍由 E0 结算。它不是新的现金支付系统。
- 玩家 `destroy_key1(PLAYER,item=key1)` 持续 1 分钟，经同一 token 验证/结算，令钥匙毁坏并公开投影。没有复活钥匙、撤销玩家、隐藏改 S、代替 B 接受、改 deadline 或改过去的算子。
- `rest` / `work` 是 A/B 自己的 1 分钟应用活动；只有取得控制槽的角色可发起。rest 的自己可知收据进入 X→S 恢复，work 产生个人 work_units。B 可以主动要求自己的工具；目标不可达、承诺暂停或已完成时不会让人物停止活动。
- start 不推进时间、不立即给效果。长 unlock 继续用 E0 的进度与控制 token；中途 checkpoint 恢复只继续剩余动作，不再记录一次 ACTION_START。世界/玩家动作不吞掉 B 尚未得到的首个控制槽。

W 的 `world_tasks.ledger.progress`、角色 `TaskCommitment` 和当前 RunningAction 是三个不同对象。只有自己收到合法完成证据才完成承诺；暂停/恢复不重写 started_at；已完成承诺不会因日常休息重新打开。

## 候选 dynamics 与可替换规划

`ContextDriveV0` 使用**人造开发规则** `drive(s)=4s(1-s)-0.5` 及 overload guard；弱/中/高压力可以分别选日常活动、任务推进、恢复。X 显式记录可见阻断/恢复事件及自己可知的截止压力，updater 实际消费这些字段。`MonotoneAvoidanceV0` 改为 `drive(s)=-s`，其余执行器、条件与参数不变，作为会改变行为的反例实现。**不是普遍倒 U 心理规律，也不是已训练 Theory-S。** S 字段仅存在于本应用版本，不扩充冻结 C++ schema。

GOAP 直接复用 E1 h=0 UCS。HTN 通过 [GTPyhop](https://github.com/dananau/GTPyhop) 的维护者 [gtpyhop-core 2.0.2](https://pypi.org/project/gtpyhop-core/) 执行 backtracking，而非手写固定动作列表或伪装的 UCS。局部 HTN methods 可以分解“直接借钥匙 / 先还工具再借 → 开门 → 取账本”，效果仍只是 A 对公开协议的假设。未披露的 LoanKey 只能作为未来变量，不能派发成真实动作。

依赖固定为 `gtpyhop-core==2.0.2` 与 `psutil==7.2.2`。GTPyhop 授权为 BSD-3-Clause-Clear；本目录只写领域 adapter，未复制上游 planner 源码。缺少依赖直接说明错误，不静默降级。上游 `max_expansions` 参数不执行限制，因此这里**不把它当预算**：adapter 对每次 method/action 调用实施 cooperative cap 和 wall check；库 session 另有 timeout。默认 UCS 1000 expansions / .5s、HTN 1000 method/action visits / .5s，二者计数单位不同，不作运行成本公平比较。

## 世界计划不是实际历史

每次只比较 NO_OP 和当前可校验机会；fork 从同一已提交 checkpoint 出发，运行同一演员链到 t=10，上限 16 个 actor steps。默认 lexicographic score 是硬约束 SATISFIED 数、负 VIOLATED 数；同分保持 NO_OP。soft 状态照样监测，但本版不参与选择，也没有通用作者优先级求解。

forecast 明确假设相同演员模型、固定公开 B utility、没有未预告的未来玩家输入。被选操作提交前再次验证真实 W；所有预测只在 director_proposals，不能作为 committed witness。预算不足输出 BUDGET_NO_INTERVENTION，不冒充不可达证明；全部试过不成功也只说明**当前有限候选/模型下无改善**。玩家扰动后重新计算未来，已提交前缀与绝对期限不变。不提供 `∃director ∀responses` 保证。

硬约束预测仍有 PENDING/INDETERMINATE 时该候选不进入数值选择，报告 UNKNOWN_NO_INTERVENTION；不能把欠缺的过去样本或超出有限 horizon 的要求当作零损失。只恢复 checkpoint 而没有过去 snapshots 时，角色执行可以继续，但过去状态线不补证。

monitor 复用既有编译器的 exact-time、typed owner、版本和 seal 语义。缺省资源线是 piecewise-constant `ALWAYS resources>=0`，不是伪造连续 NumericBand 证书。未知/缺失采样不补成 SAT；非注册量与未经定义的连续轨迹直接拒绝。这里的收据/历史检查是工程一致性校验，不是 cryptographic authenticity 或完整可达性证明。
