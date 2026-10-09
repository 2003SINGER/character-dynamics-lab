# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前固定源码 commit `aba0ddfad08487b963a9fe0bad327e1f3fb54a4f` 已通过一次 Mac formal（14/14 fixtures）和一次 exact-source CI（六 jobs、38/38 unit、14/14 fixtures），`receipt.delta_w` 窄修复亦通过 bounded local regression 与 P01/P02 physical-effect parity。最终原始产物、hash、预算核验及证据边界见 [RESULTS](RESULTS.md#final-fixed-source-formal-and-ci-commit-aba0ddf)。V0 保留 10k/2s；保留历史 wall-time miss/pass，不声称跨运行稳定、不加跑追绿。当前状态 `E0_BOUNDED_ACCEPTANCE_PASS / READY_FOR_INDEPENDENT_REVIEW`；后续需独立审阅与用户决定才能 CLOSED 或授权 E1。非阻断存储/稳定性增强进入 backlog。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

当前 Mac formal 原始产物位于 `runs/e0_keyledger_v0/formal/20261009T005835Z_all_formal-ebe3cbb-20261009/`；逐 case parity、性能 audit 和 provenance 见 [RESULTS](RESULTS.md)。CI run `37867775555` 的完整结果为 13/14，未过固定预算 gate；E0 acceptance 也未证明所有历史回执 immutable/correct。
