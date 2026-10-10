# Native Platform P3-C0｜基础日常活动与固定优先目标选择

状态：**READY_FOR_INDEPENDENT_REVIEW**（有限 DEVELOPMENT 已实测；尚未 CLOSED）。本阶段在 P3-A/B 已验证的 Evennia 执行基座上，增加一个 opt-in 的 patrol 活动，并用最小固定规则协调两个目标：`deliver_supply > patrol`。本页是 C0 当前状态入口，实际运行证据只记于 [RESULTS](RESULTS.md)。不自动开始 P3-C1、P3-C2 或 P4。

## 当前授权与范围

- 有有效配送任务时始终优先配送，继续使用既有 GTPyhop/HTN 规划和 Evennia 原生命令验证；依据该角色持久化的自有 settled drop receipt 判定“已完成”（不新增独立 latch 字段），不得因巡逻再次领取或重复投递。
- 无配送目标的场景才选择 `patrol`；完成配送后可在同一世界继续巡查。巡查只根据当前合法局部观察中的出口/位置决定下一次移动，使用真实 Evennia move 命令及其执行回执。
- patrol 必须 opt-in，既有 P3-A/B 场景默认保留原行为和验收语义。不要把本轮的任务切换扩展成配送阻断时转去巡逻、待条件恢复后再回来。
- 目标选择、候选目标、固定优先级、选择原因、局部观察、规划/直接行为、命令结果、世界前后位置与基于自有 receipt 的完成判定均进入 trace。继续复用现有 P3AutonomyScript/Headless Runner/MCP 控制面；不另造 clock、scheduler、World 或 executor。
- 可在两个现有房间间巡查。负控包含两房间间 `traverse:false` 的锁门出口；若当前出口无效或移动被拒绝，记录并安全等待/停止，不循环重试。薄适配规则应标为本项目的有限 priority/FSM，不宣称复现 Evennia 完整 FSM/roaming。

## 三组有限 DEVELOPMENT 验收

1. **无配送任务：** actor 在没有作者配送合同的场景中由有限后台 callback 选择巡查，至少一次真实合法移动；以行动记录和独立 Evennia DB 读回核实位置一致、无全知地图输入与无无界重试，并验证两房间锁门出口被拒后安全等待且不会重复提交该无效移动。
2. **有配送任务：** 配送优先，HTN 仍执行真实 get/move/drop；原 Aclean 与 Asteal-return 回归保持。patrol opt-in 不能重置、跳过或覆盖既有配送合同。
3. **完成后续巡查：** 同一 NPC 先由自身配送 receipt 判定任务完成，再切换 patrol；配送不会重启或创建重复完成 receipt，且无需新作者指令。

三组已在有限场景实测，逐例证据及解释边界见 [RESULTS](RESULTS.md)。这些证据不等于生产就绪或完整 NPC 自治。输出隔离于 `runs/` 的 C0 独立子目录；不得覆盖 P3-A/B 原始证据。

## 本地复核入口

复跑前提：已按 [P3 本地复核入口](../Native_Platform_P3_v0/README.md#本地复核入口)初始化本地 P1 Evennia game、应用两处 ignored hook，并准备好 `_local_data/native_platform_v0/evennia/venv`。`install_headless_service.py --check` 只是只读核验，不会替普通 clone 安装 hook。服务仅应由 `start_loopback.sh` 在 `127.0.0.1:14011` 启动。每个命令单独运行并保留其返回的 JSON 路径：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/install_headless_service.py --check
tools/native_platform_v0/evennia/start_loopback.sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c0_runner.py --scenario C0-no-delivery --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c0_runner.py --scenario C0-delivery-priority --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c0_runner.py --scenario C0-after-delivery --seed 20261010
```

从 run JSON 取精确场景 ID：`C0-no-delivery` 使用 `response.scenes[].trace.scene_id`；`C0-delivery-priority` 与 `C0-after-delivery` 使用 `response.trace.scene_id`。再将四个 scene ID 显式用于只读 DB export（每个 `--scene-id` 重复一次）：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/export_evidence.py --c0 --scene-id SCENE_ID_1 --scene-id SCENE_ID_2 --scene-id SCENE_ID_3 --scene-id SCENE_ID_4
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/c0_audit.py --run RUN_JSON --db DB_EVIDENCE_JSON
```

按三组分别以对应 run 与其场景 ID 的 DB export 调用 `c0_audit.py`。`c0_runner.py` 通过本地服务调用同一个经过认证的 RPC handler，不是经 MCP stdio 传输。另有实际 MCP stdio transport 核验：11 个工具可列出，`run_c0_scenario` 存在但未全局注册，记录见 [MCP stdio transport evidence](runs/p3-headless-MCPstdio-C0-transport-seed20261010-20261010T035534Z-33130c.json)。callback 驱动次数不是现实或游戏内经过时间。

## 明确不做

不做 needs/情绪/人格学习、S/P/X 公式、关系学习、长期记忆、多目标 utility 学习、额外 Ensemble 动作、地图/职业/NPC 扩张、LLM/训练、通用插件框架、浏览器控制、P3-C1/C2 或 P4/DODM/Mimesis/Director。保持冻结的 C++ Runtime、E0/E1 和既有实验资产不变。

## 来源与主张边界

当前选择是成熟传统游戏 AI 的极小应用策略：固定优先级加 patrol 行为适配；其价值是验证有限连续活动，不是新心理模型、完整 NPC 生活或科研创新。P3-A/B 实证由[旧阶段 owner](../Native_Platform_P3_v0/README.md)维护，不在本阶段改写。
