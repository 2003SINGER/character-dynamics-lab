# E0-KeyLedger-v0 results

状态：开发全 fixture 检查完成；`FORMAL_RUN_NOT_STARTED`。本文不把开发单测或 CI 等同正式实验结论。

正式验收预算固定为 10,000 expansions / 2 seconds；若正式 Oracle 未完整耗尽，则对应搜索 fixture 保持 `NOT_PASS`。

## Development diagnostics

- 2026-10-08，E0 单测命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m unittest discover -s tools/e0_keyledger_v0/tests -v`：后续验收 **33/33 PASS**。开发过程中一次中间检查为 30/31，原因是空 no_control observation delta 表示不一致；失败原因在本节留档并修复后复测。
- 全 14 fixture 的实际开发运行：`runs/e0_keyledger_v0/development/20261008T123337Z_all_dev-20261008-a/`，运行输入、每边界快照、搜索/回放结果、异常列表见 [result.json](../../runs/e0_keyledger_v0/development/20261008T123337Z_all_dev-20261008-a/result.json)。总 `fixture_test_result=PASS`，14/14 PASS；其中 C01 的测试 PASS 仅表示正确报告 `BUDGET / incomplete / not exhausted`，不表示求解成功。Planner/Oracle 正式搜索 applicable 的各例 Oracle 均完整耗尽，细节见原始 JSON。

该开发运行基于冻结协议提交 `e411ff45f67855e58d047fd37332b6896db5b8fe`，运行时 E0 scope 仍有未提交实现/路由文件（`e0_scoped_dirty=true`），所以它不是可作为正式版本证据的干净代码提交。硬件、Python、单线程预算与源码/协议 hashes 以该运行 JSON 的 `provenance` 为准。代码提交后仍须由父代理另行放行正式批次；不得将此开发运行重标为正式运行。

| Fixture | Search/oracle result | Fixture test |
|---|---|---|
| P01 / B01 / B03 / H01 / P02 | 可达；Oracle 完整穷尽，真实 Executor replay 与 Monitor witness 匹配 | PASS |
| N01 / N02 / B02 / H02 | 有限域不可达；Oracle 完整穷尽 | PASS |
| X01 / X02 / U01 / F01 | 定向绑定/预测、原子失败、证据缺口与 fork 隔离检查 | PASS |
| C01 | Planner 与 Oracle 均 `BUDGET`, `complete=false`, `exhausted=false` | PASS（预算诊断断言，不是求解 PASS）|

已完成的开发验证只记录在会话/CI 的开发产物中；正式报告须引用真实 `code_revision`、协议冻结提交与 hash、源码 hash、Python/platform/hardware 和单线程配置。正式运行目录：暂无。
