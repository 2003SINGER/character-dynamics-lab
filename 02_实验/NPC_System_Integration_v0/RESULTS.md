# NPC System Integration v0｜唯一开发结果 owner

日期：2026-10-09。状态：**DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW**；没有独立 closure，不自行 CLOSED。

授权依据：用户在提交 19:16–19:45 目标讨论 TXT 后，先限定外围维护，随后明确改为“现在不只是外围维护了，可以改了！按照目标文本贴出的txt来”。本次限于基于 E1 的有限整合开发，不自动恢复旧 formal test、训练、Optimizer 或重构 C++ Kernel。

## 实现与来源

源码入口：[应用 README](../../tools/npc_system_v0/README.md)、[runner](../../tools/npc_system_v0/runner.py)、[测试](../../tools/npc_system_v0/tests/test_system.py)。语义 owner 仍是[F0/F1](../../00_研究设计/CharacterDynamics_FormalProblem_v0.md)与[完整机制](../../00_研究设计/完整机制说明_v0.md)，不新增并列系统总纲。原讨论仅在本地私有原始材料保存，SHA256 `12ef1420e1db6b580e69c149601357cc4d20a17c50e5103933add12f690b783f`。

构建源基线 `webgpt-sync@8f4fb7b` + 本次 source hashes；manifest 会明确记录工作树是否 dirty。证据包保留实际源码 SHA、Python/依赖版本、条件、完整 snapshots、动作收据、X/S/承诺及 director 预测。正式验证数据不存在，所有来源均为 synthetic_diagnostic / DEVELOPMENT。

## 目标文本的落实边界

| 用户要求 / 讨论要点 | 本次具体落实 | 仍未实现 / 不能声称 |
|---|---|---|
| 原有角色动力不能被抽象掉 | O/H/P→X→S→个人目标/承诺→planner→W 结算；状态恢复、阻断、压力实际消费 | 不等于旧完整心理机制已训练或识别 |
| 机制可替换算法或放在算法之间协调 | 两种 response model 可替换；goal arbitration 位于模型与 planner 之间；GOAP 与真正 HTN 使用同一执行器 | 无泛用插件加载器；未接入高层 LLM |
| 多层稀疏点/线要求而非逐分支剧情 | 可执行 global/scene/beat JSON；事件、顺序、资源线、终点状态分别检查 | 非可视化 author UI；分层不自动规划；锁定/分支/关系等完整 author language 未实现 |
| 世界也是可规划参与者 | NO_OP/有成本公开机会的隔离预测与选择；再次 W validation | 有限 1 种世界干预；不是开放世界导演 |
| NPC 自己生活，不围绕导演才动作 | director-off 仍有 B 请求、A/B work/rest；PAY 不靠导演可完成任务 | 仅两个角色、八分钟有限域；不证明长时程活人感 |
| 玩家改变条件后修未来 | 独立玩家毁钥匙收据；重新预测未来；绝对 deadline 与旧 ledger 不变 | 毁坏后缺少替代资源会失败；无稳健必胜保证 |
| 世界任务/角色承诺/动作不同 | W-derived progress、actor-visible completion、RunningAction 分开；反馈缺失不关闭承诺 | 不是通用多任务活动库 |

## 本机开发验证

- 新应用 unit contracts：**32 项**。覆盖独立后端、非单调响应、模型替换、完成反馈、承诺时间、日常活动、隔离预测、世界/角色权限、收据篡改、资源记账、玩家不可回滚、缺失证据 UNKNOWN、硬约束未知不优化为零损失、长动作每个边界与中途恢复不重复开始。
- 未改动的 E1：**30 项**；E0：**38 项**；TypedIR：**30 项**。此为对应 Python 回归，不是本次重跑 C++ CTest 或旧正式实验。
- 开发矩阵：**10 个条件**；另跑 HTN + 外部多层 JSON 入口 **1 个**。实际时刻/完整 verdict 以下方证据为准。

| 条件 | 账本事件 | 解释 |
|---|---|---|
| KEEP + director + GOAP | SATISFIED | 有成本公开激励→B 自己请求→A 报价→B 自己接受/交换→A 开门取账本 |
| KEEP + director + HTN | SATISFIED | 换后端；不调用 UCS；同一 executor |
| KEEP + director off | VIOLATED | 无愿意借钥匙的条件，人物继续自己的 work |
| PAY + director off | SATISFIED | 本身可行动，不依赖导演 |
| 玩家 t=3 起毁钥匙 | VIOLATED | 已发布激励也不能撤销玩家毁坏；代价/历史保留 |
| 世界资源 0 | VIOLATED | 无权透支/无免费增益 |
| 作者 deadline=8 | VIOLATED | 不平移 deadline；候选激励也来不及满足 |
| forecast budget=0 | VIOLATED | BUDGET，不伪称证明不可达 |
| monotone response model | VIOLATED | 参数/执行器不变，换 response law 实际改变目标行为 |
| 初始 overload，PAY/director off | SATISFIED | 自主 rest 后恢复，再完成；不是一直逃避 |

## 证据与错误留存

版本化完整开发包：[development_20261009](development_20261009/manifest.json)；多层外部输入运行：[author_json_20261009](author_json_20261009/manifest.json)。未来运行另起路径，不覆盖此检查点。运行中出现的 registry 缺项、piecewise NumericBand 不支持、编辑缩进、示例 Compare enum 大小写、Windows Git 输出解码，以及显式 owner qualifier 没有解析到 canonical 采样导致的 UNKNOWN 均修复并重验；后者先验证 owner 再在本应用 adapter 解析，不改冻结 reference。原失败及尚未冻结的早期证据副本保留在本地 `outputs/npc-system-v0/`，不把失败抹成始终成功。

## 接下来与停止条件

### 推送后的 CI（代码 checkpoint `e5eeedd`）

[npc-system-development run 37934365423](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37934365423) 的 job log 已核对：**新应用 32/32、E1 30/30 均通过**，10 条开发矩阵运行成功且各条件 verdict 与本机一致，artifact 上传成功。合并 unit step 随后在未改动的冻结 E0 `test_h02_keeps_state_and_event_outcomes_distinct` 失败：期望 UNREACHABLE 而固定预算返回 BUDGET。因此该 workflow 的 overall 仍为 **FAILURE**，不能称“全 CI 绿”。冻结 E0 的失败只在其[唯一结果 owner](../E0_KeyLedger_v0/RESULTS.md)记录，不放宽 cap、删测试或重跑追绿。

同 source 的 [runtime-regression run 37934365282](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37934365282) 中 C++ build/CTest/reference、TypedIR 等其余五个 jobs 成功，E0 job 失败。CI 属软件回归，不是独立用户 closure 或玩家有效性验证。最后的报告提交只维护这些实际观测，不改代码与运行条件。

已经达到本次有限 vertical slice 的开发交付点，等待独立检查原需求映射、权限边界、真实 trace 与可替换后端。下一次功能扩展应围绕一个可玩场景和具体作者要求选择；不是把该 synthetic trace 当论文成果或直接扩大城市/长期/LLM 批次。

这版仍不是完整 Character Dynamics 产品：没有 C++ native 集成、开放多 NPC 并发、长时程世界、LLM 高层规划、作者 UI、独立玩家评估、心理训练或科研方法收益。GTPyhop/GOAP 能跑、director 能达成一个有限目标，是实现证据而非上述结论。
