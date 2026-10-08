# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前验收与历史开发运行：见 [RESULTS](RESULTS.md)；只有带完整输入、预算、代码/协议 provenance 和原始 trace 的运行产物才支持状态更新。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

正式运行仍须按冻结预算 `10,000 expansions / 2 seconds`，保留失败与完整结果。不要将开发测试或 CI 运行重标为正式实验。
