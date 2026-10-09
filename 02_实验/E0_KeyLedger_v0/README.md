# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前 macOS formal run `20261009T005835Z_all_formal-ebe3cbb-20261009` 为 14/14 fixture PASS，C01 仍未解决。Exact source `ebe3cbb` 的 Ubuntu CI 已完成但 13/14，唯一失败 H02 因固定 2 秒 wall cap 返回 `BUDGET`；CI_NOT_PASS_BUDGET。性能检查和已知 receipt-history limitation 见 [RESULTS](RESULTS.md)。当前状态：`E0_LOCAL_ACCEPTANCE_PASS / CI_NOT_PASS_BUDGET / READY_FOR_REVIEW`。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

当前 Mac formal 原始产物位于 `runs/e0_keyledger_v0/formal/20261009T005835Z_all_formal-ebe3cbb-20261009/`；逐 case parity、性能 audit 和 provenance 见 [RESULTS](RESULTS.md)。CI run `37867775555` 的完整结果为 13/14，未过固定预算 gate；E0 acceptance 也未证明所有历史回执 immutable/correct。
