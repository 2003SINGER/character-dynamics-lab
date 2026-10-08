# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前 macOS 正式运行与历史开发运行分列于 [RESULTS](RESULTS.md)：formal run `20261008T123731Z_all_formal-4caa088-20261008` 为 14/14 fixture PASS；C01 仍未解决。Ubuntu CI 在 H02 的固定 2 秒 Planner cap 下未通过，而独立 Oracle 已穷尽。当前状态：`E0_LOCAL_ACCEPTANCE_PASS / CI_NOT_PASS_BUDGET / READY_FOR_REVIEW`。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

正式原始产物位于 `runs/e0_keyledger_v0/formal/20261008T123731Z_all_formal-4caa088-20261008/`；逐 case 结果、provenance 和分支证据见 [RESULTS](RESULTS.md)。CI 失败后取证已调整为保留 unit log 并始终运行完整 fixture batch，等待下一 head 的 CI 产物；不改变 10,000 / 2 秒预算或 gate。
