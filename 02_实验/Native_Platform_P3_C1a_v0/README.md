# Native Platform P3-C1a｜临时不可观察与配送恢复

状态：**READY_FOR_INDEPENDENT_REVIEW**（有限 native-server DEVELOPMENT 与独立 DB 核验已完成；尚未 CLOSED）。本阶段是 C0 之后获授权的有限开发切片：在真实 Evennia 本地 server 的 headless 场景中，复用固定目标优先级和 GTPyhop/HTN，区分“当前未观察到目标物品”与“无计划、预算耗尽或全局不可达”，并检查暂时受阻后的切换/恢复。唯一状态与结果入口为本页及 [RESULTS](RESULTS.md)。

## 范围与场景

- activity profile：`delivery_patrol_recovery_v0`。
- `C1a-blocked-switch`：以固定规则测试配送目标暂时无法由当前合法观察支持时的受阻/切换处理；不得把一次缺失观察直接等同于 `NO_PLAN`、`BUDGET` 或全局 `UNREACHABLE`。
- `C1a-observed-resume`：仅当后续本地观察重新支持配送行动时，验证目标恢复与 HTN 继续执行；包含 hidden-return 负控，避免凭隐藏世界状态推断物品返回。
- 使用有限的原生 server headless callbacks，保留局部观察、候选/目标选择、HTN 输出、真实命令结算及世界状态读回。
- 当前只验证这两个场景与负控，不扩成通用恢复框架或生活自治。

## 保护边界

- 不改变 P3-C0、P3-A/B 的默认行为与合同，不覆盖既有结果或 raw runs；E0 协议/结果及冻结 C++ Runtime 保持不变。
- 不新增心理状态、LLM、额外地图/NPC/动作或第二套时钟/执行器；本轮完成后停止，不自动扩展 P3-C1/C2 或进入 P4。
- C0 的有限 DEVELOPMENT 验收已获外审认可，但其 README 仍保留 `READY_FOR_INDEPENDENT_REVIEW`，不据此宣称 `CLOSED`。

## 验收状态

两场景及 hidden-return 负控的真实证据、失败与限制只记于 [RESULTS](RESULTS.md)。

## 本地复核入口

复跑需要已初始化的本地 Evennia server、既有 loopback hook 与 `_local_data/native_platform_v0/evennia/venv`；不需要游戏客户端。按 [P3-A/B 本地复核说明](../Native_Platform_P3_v0/README.md#本地复核入口) 准备并启动服务，然后分别运行：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c1a_runner.py --scenario C1a-blocked-switch --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c1a_runner.py --scenario C1a-observed-resume --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/export_evidence.py --c1a --scene-id CASE_A_SCENE_ID
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c1a_audit.py --run CASE_A_RUN_JSON --db CASE_A_DB_EVIDENCE_JSON
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/export_evidence.py --c1a --scene-id CASE_B_SCENE_ID
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c1a_audit.py --run CASE_B_RUN_JSON --db CASE_B_DB_EVIDENCE_JSON
```

分别从两个 run 的 `response.scene_ids[]` 取对应 scene ID；C1a 导出和 audit 均按单个场景执行，不能合并两个 ID 后再逐 run 审计。
