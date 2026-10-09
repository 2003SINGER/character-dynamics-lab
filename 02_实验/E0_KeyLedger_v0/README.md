# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前已提交 Mac formal `20261009T005835Z_all_formal-ebe3cbb-20261009` 为 14/14 fixture PASS，C01 仍未解决。exact source `904cc6a3ce275fcd19ef3ac0500f09313839ef7c` 的 CI run `37869124267` 六项 job 全部成功（37/37 unit、14/14 fixture）；原始 ZIP、审计及逐项结果见 [RESULTS](RESULTS.md#successful-ci-checkpoint-exact-source-904cc6a)。其后 `receipt.delta_w` 快照修复通过本地 bounded regression：E0 38/38、TypedIR 30/30、focused executor 9/9，P01/P02 物理效果对照见 [RESULTS](RESULTS.md#receipt-delta-repair-and-bounded-regression)。V0 预算仍为 10k/2s；成功的单次 CI 不证明跨运行 wall-time 稳定。待提交固定源码上的一次 Mac formal 和一次 CI；当前状态 `RECEIPT_FIX_LOCAL_REGRESSION_PASS / FIXED_SOURCE_FORMAL_CI_PENDING`，E0 不视为 CLOSED。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

当前 Mac formal 原始产物位于 `runs/e0_keyledger_v0/formal/20261009T005835Z_all_formal-ebe3cbb-20261009/`；逐 case parity、性能 audit 和 provenance 见 [RESULTS](RESULTS.md)。CI run `37867775555` 的完整结果为 13/14，未过固定预算 gate；E0 acceptance 也未证明所有历史回执 immutable/correct。
