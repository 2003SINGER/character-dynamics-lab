# Character Dynamics Online Integration v0

**当前状态：DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW — 2026-10-22 在线作者干预迭代已停止。** 本轮运行、限制与 Judge 摘要归 [ONLINE_PLAYTEST_V1.md](ONLINE_PLAYTEST_V1.md)：Judge 认为表现有一定效果但不完整，未见作者编辑驱动实际目标行为的证据；事实勘误已纳入该 owner，Judge 私有原文不公开。未实现目标不升级为通过，不另建 Controller 或新增 G1 技能。此前多角色过程仍为 PARTIAL，其计划与原始结论分别见 [MULTI_ACTOR_PROCESS.md](MULTI_ACTOR_PROCESS.md)、[MULTI_ACTOR_RESULTS.md](MULTI_ACTOR_RESULTS.md)；三组更早运行仍由 [RESULTS.md](RESULTS.md) 记录，旧运行条件只见 [PROTOCOL.md](PROTOCOL.md)。历史结果不覆盖，成熟方法继续作为复用基础。

## 目标与边界

贯通角色自身目标与规划、作者在线加入/编辑未来要求、协调后续计划、Veloren 执行、真实反馈、未完成义务更新及角色继续活动。旧 v0 三组运行固定 G0；当前新授权明确允许为多角色过程增加版本化 G1 内容，条件与归属见 [MULTI_ACTOR_PROCESS.md](MULTI_ACTOR_PROCESS.md)。两条合法路径是某些算法对照的实验条件，不是系统开发的普遍准入门槛。

本包复用 F0/F1、Author Obligation Planning、HTN/GTPyhop 角色目标选择，以及 Veloren 已验证的原生招募/受雇/跟随能力。G0 原生规则、冻结 C++ Runtime、旧实验结果和历史事实均不改写；新增 G1 必须独立版本化并按实际执行结果归因，不得把 Planner 预测当成约束已满足。

决策来源始终分开：`NATIVE` 为游戏原生行为，`ACTOR` 为角色自身职业任务/目标驱动，`AUTHOR` 为作者要求及权限，`DIRECTOR` 为协调作者未来要求的计划选择。Director OFF 只关闭作者介入，不能关闭 ACTOR。角色决策只用合法局部观察；作者全局监测单独记录。已发生事实与作者版本历史保留。无取消能力时如实记录 inflight，不伪造取消或回滚。

## 维护、计划与结果

- 当前授权目标与实施范围见 [MULTI_ACTOR_PROCESS.md](MULTI_ACTOR_PROCESS.md)；旧 v0 运行条件与预算见 [PROTOCOL.md](PROTOCOL.md)。
- 状态 owner：本 README；2026-10-22 在线作者干预运行与 Judge 摘要 owner：[ONLINE_PLAYTEST_V1.md](ONLINE_PLAYTEST_V1.md)；此前多角色结果 owner：[MULTI_ACTOR_RESULTS.md](MULTI_ACTOR_RESULTS.md)；先前三组结果 owner：[RESULTS.md](RESULTS.md)。
- 2026-10-22 在线 playtest 独立 Judge 初评与勘误摘要见 [ONLINE_PLAYTEST_V1.md](ONLINE_PLAYTEST_V1.md)；不等于人类体验评价，也不改变 PARTIAL 状态。
- 旧运行结果以 RESULTS 的证据边界为准；不把单次轨迹提升为算法优势或新里程碑完成。
- 本轮公开范围仅为代码和报告；raw 与脱敏运行证据、私有原文均不公开。

## 可复用入口（不构成新运行授权）

离线测试依赖 `gtpyhop-core==2.0.2`：`python -B -m unittest discover -s tools/character_dynamics_online_v0/tests -v`。当前 runner 入口示例：`python -B -m tools.character_dynamics_online_v0.process_runner --freeze <private-new-freeze.json> --run-id <new-id> [--author-input <private-author-input.jsonl>]`；省略 `--author-input` 时使用 `RUNNER_DEMO`，不是人工 `LOCAL_AUTHOR`。占位符须换成新隔离输入与新 run ID；已运行 userdata 不可原样复用，须重新隔离复制并重新固定哈希，不能覆盖既有产物。此命令仅说明可复用接口，不构成新运行授权。
