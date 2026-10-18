# Character Dynamics Online Integration v0

**状态：DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW；本轮停止。** 三组 headless 运行已完成；有限的 ACTOR/AUTHOR/DIRECTOR→原生 Job→后续观察链有证据，但三台服务均以 SIGTERM（exit `-15`）结束，整包不标完整通过。结果与限制只见本包唯一 [RESULTS.md](RESULTS.md)。本包仍是 Character Dynamics 持续系统的首个纵向集成；成熟规划方法作为复用基础，历史 C1/C2 `NO_GO` 不作当前开发停点。

## 目标与边界

贯通角色自身目标与规划、作者在线加入/编辑未来要求、协调后续计划、Veloren 原生执行、真实反馈、未完成义务更新及角色继续活动。G0 固定为既有游戏规则；G1 是未来可明确扩展并研究的域，本包不授权新增游戏规则。两条合法路径是某些算法对照的实验条件，不是系统开发的普遍准入门槛。

本包复用 F0/F1、Author Obligation Planning、HTN/GTPyhop 角色目标选择，以及 Veloren 已验证的原生招募/受雇/跟随能力。不得改写原生规则、冻结 C++ Runtime、旧实验结果或历史事实；不得把 Planner 预测当成约束已满足。

决策来源始终分开：`NATIVE` 为游戏原生行为，`ACTOR` 为角色自身职业任务/目标驱动，`AUTHOR` 为作者要求及权限，`DIRECTOR` 为协调作者未来要求的计划选择。Director OFF 只关闭作者介入，不能关闭 ACTOR。角色决策只用合法局部观察；作者全局监测单独记录。已发生事实与作者版本历史保留。无取消能力时如实记录 inflight，不伪造取消或回滚。

## 维护与结果

- 固定范围、条件和预算边界见 [PROTOCOL.md](PROTOCOL.md)。
- 状态 owner：本 README；运行与限制的唯一结果 owner：[RESULTS.md](RESULTS.md)。主级已完成本轮验收；当前交付等待独立审阅，不自动补跑或扩建。
- 真实状态/原生结果以 RESULTS 的证据边界为准，不把单次轨迹提升为算法优势或完整系统完成。
- 本轮公开范围仅为代码和报告；raw 与脱敏运行证据、私有原文均不公开。

## 可复用入口（不构成新运行授权）

离线契约测试：`python -B -m unittest discover -s tools/character_dynamics_online_v0/tests -v`。runner 入口示例：`python -B -m tools.character_dynamics_online_v0.runner --freeze <private-new-input-freeze.json> --run-id <new-id>`。占位符须换成新隔离输入的 freeze 与新 run ID；已运行 userdata 不可原样复用，须重新隔离复制并重新固定哈希，不能覆盖本次产物。
