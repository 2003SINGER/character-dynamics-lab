# P3 CI 与 runtime-regression 快照

- 源码提交：[`a2148170262181c7238f7b573229b37cd8854b7b`](https://github.com/2003SINGER/character-dynamics-lab/commit/a2148170262181c7238f7b573229b37cd8854b7b)
- P3 专项 workflow：[run 38018330610](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38018330610) — **SUCCESS**。
- runtime regression：[run 38018330609](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38018330609) — **FAILURE**，仅 `e0-keyledger-contract` 失败；另外 5 个 jobs 成功（含 regression build、CTest、reference、health）。
- 已核对的 E0 GitHub Ubuntu CI 日志：37/38 unit tests、13/14 fixtures 通过。唯一失败为 H02：实际 planner status `BUDGET`，断言预期 `UNREACHABLE`。
- 边界：这是既有 E0 fixed-budget/expected-status 不一致；保留失败事实，本轮未改 E0，也未重跑/修补该 workflow。P3 专项 CI 通过不等于全仓 runtime regression 通过。
