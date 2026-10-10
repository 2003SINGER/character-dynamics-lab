# Native Platform P4-0

状态：**READY_FOR_INDEPENDENT_REVIEW**。16 个固定范围 native-server 场景均 COMPLETE，8 组配对及逐场景 DB 证据经独立审计；结果见[RESULTS](RESULTS.md)。这是有限 DEVELOPMENT 检查点，不是 CLOSED、生产就绪或研究效度结论。本轮至此停止，不进入 P4-1。

## 冻结范围

- `p4_story_v0`、手动驱动、两房间、courier/resident 两个物理 NPC 与一个测试玩家；保留双方原 delivery goal。
- 四个场景：`open`、`blocked-return`、`blocked-held`、`short-deadline`。开发矩阵为每场景×author on/off×seed `20261010`/`20261011`，共 16 次；这是配对开发复跑，不是随机样本。`short-deadline` 为 6 simulated minutes，其余 24。
- `blocked-return` 与 `short-deadline`：测试玩家在第 1 分钟真实取走 courier supply，并在第 6 分钟归还同一物品；`blocked-held` 只取走并持有到 deadline；`open` 不做玩家物品干预。各 arm 使用相同 schedule、actors、seed 与预算。
- 唯一 author action 为 `OPEN_PASSAGE` 或 `NO_OP`。最多一次开通初始封闭的 east passage；不直接控制 NPC、不改社交记录或玩家物品。
- 固定机会规则为 simulated minute ≥4、门仍关闭、机会未用且尚无目标 witness 时才允许开门；否则 `NO_OP`。不给 NPC 预设会合点或 rendezvous 脚本。
- `step_world` 每步推进服务器拥有的模拟时钟 1 分钟；每分钟两个 NPC 各执行 callback。它不是墙钟计时或连续物理模拟。
- 主约束：deadline 前恰有一个由 courier 发起、resident 实际结算的 note response。接受和拒绝都计为 interaction；接受另行报告。只认可完整封存的 server ledger、native response/commit receipt 与精确场景只读 DB 导出，不认可 proposal/text。

本探针使用 pinned Ensemble 原生源码，但只创建 hero/love 两个物理 NPC。原 `loversAndRivals` cast 中未在场的 rival 仍可能影响原生触发规则；它不是第三个 Evennia NPC，也不表示全量 social state 已镜像到世界中或完整实现独立私有 cognition。

范围固定为：原生互动链必须由 A courier 发起真实 note request，再由 B resident 的真实 callback 依据其原生 volition/action 选择接受或拒绝，且物理 note response 与 native commit 均结算。此处不预置接收者意愿，也不强制任何 arm 达成会合或成功 response。

该固定机会规则借用 DM action/refiner 与 null-action 的设计动机；不声称复现 DODM/SAS/RL，也不主张新算法。它是 bounded engineering feasibility check，不是心理效度或完整 DM。

## 运行与审计

需预先运行当前 branch 已初始化的 P1 Evennia 服务，保留场景所属管理员账户，并准备项目 Python venv、隔离 loopback RPC 与固定 Ensemble Node runner。普通 clone 不能仅靠 `--check` 自动安装 hook；依照 P3 owner 的 hook install 说明完成初始化。不要求管理员登录、浏览器客户端或人工输入命令。

原始运行、DB 证据及压缩副本校验索引见[完整证据清单](evidence_manifest.json)；逐例 outcome 与配对检查见[RESULTS](RESULTS.md)。CI 状态以本提交的 GitHub Actions 为准。

单场景（保存原始响应，不作 PASS 判定）：

```sh
PYTHONDONTWRITEBYTECODE=1 _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.p4_runner --case open --director on --seed 20261010
```

同一 case/seed 的 off/on 配对：

```sh
PYTHONDONTWRITEBYTECODE=1 _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.p4_runner --case blocked-return --director off --seed 20261010 --paired
```

一次 MCP stdio transport smoke 可用 `--mcp-stdio` 替代 direct RPC；仍调用同一认证 RPC handler，不是独立 transport implementation 或额外场景。MCP tool 不做全局注册。

导出精确 scene 的独立 query-only DB 证据并审计单 run：

```sh
PYTHONDONTWRITEBYTECODE=1 _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.export_evidence --p4 --scene-id SCENE_ID
PYTHONDONTWRITEBYTECODE=1 _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.p4_audit --run RUN.json --db DB.json
```

配对审计使用 `--paired-run OTHER_RUN.json --paired-db OTHER_DB.json`。原始 run、source hash manifest、query-only DB export 与唯一命名 audit 保存在本目录 `runs/`；失败和 INDETERMINATE 也保留。

## 边界

不改变 P3/C0/A/B 默认合同或旧结果，不覆盖旧原始证据；不触及 E0、用户 C++ 改动、P4+ 或心理学结论。本轮完成后停止，不自动扩展。
