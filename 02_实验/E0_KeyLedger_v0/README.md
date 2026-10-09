# E0-KeyLedger-v0

本目录是 [冻结协议](../../00_研究设计/E0_KeyLedger_Protocol_v0.md) 的实验入口与结果索引；不拥有第二份协议定义。

- 协议：`PROTOCOL_FROZEN / E0-KeyLedger-v0`，冻结提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`。
- 实现：`tools/e0_keyledger_v0/`；纯标准库。共享 Monitor bridge 复用 `tools/trajectory_constraints_v0`。
- 当前固定源码 commit `aba0ddfad08487b963a9fe0bad327e1f3fb54a4f` 已通过一次 Mac formal（14/14 fixtures）和一次 exact-source CI（六 jobs、38/38 unit、14/14 fixtures），`receipt.delta_w` 窄修复亦通过 bounded local regression 与 P01/P02 physical-effect parity。最终原始产物、hash、预算核验及证据边界见 [RESULTS](RESULTS.md#final-fixed-source-formal-and-ci-commit-aba0ddf)。V0 保留 10k/2s；保留历史 wall-time miss/pass，不声称跨运行稳定、不加跑追绿。当前状态 `E0_BOUNDED_ACCEPTANCE_PASS / READY_FOR_INDEPENDENT_REVIEW`；后续需独立审阅与用户决定才能 CLOSED 或授权 E1。非阻断存储/稳定性增强进入 backlog。
- 运行入口：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --output-root runs/e0_keyledger_v0/development`。可用 `--case E0-P01` 和 `--run-id <id>` 限定一次运行；已有目录不可覆盖。
- 该有限软件验收不构成 NPC 玩家效度、心理机制或冻结 Runtime 的证据；C01 的 fixture test PASS 与搜索求解成功严格分开。

历史检查点：`ebe3cbb` 的 Mac formal 与 CI run `37867775555` 的 13/14 预算失败保留，不能覆盖页首修复后结果。当前正式原始证据已以完整 ZIP 和逐文件哈希索引保存在 [RESULTS 的最终验收段](RESULTS.md#final-fixed-source-formal-and-ci-commit-aba0ddf)。这些有界结果仍不证明任意历史、任意平台的全面正确性或性能稳定。

2026-10-09 外部审阅建议 E0 收口，后续新授权仅限[E1-0 协议设计](../../00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md)，不是 E1 执行；E0 不继续非阻断优化，历史证据与冻结协议不改，正式 CLOSED 仍需用户明确确认。
