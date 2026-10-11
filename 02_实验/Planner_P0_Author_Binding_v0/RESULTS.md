# P0 Author Binding v0 — results

**当前状态：DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW（仅固定域离线原型）；未 CLOSED。** 22 项新增离线契约测试通过，三个固定输入在本地 Sabre parser/solver 预检中均成功。此状态仅供独立审阅有限原型与其证据，不代表原生游戏执行、live dispatch/replanning、完整系统或研究有效性。本页是本工作的唯一实现与证据 owner。

## 范围与问题

在固定 P0 域内，检验一个已确认的作者要求能否同时投影为 Sabre 条件和 Pilot TypedIR 监测条件，并保留来源/版本、权限、时间与绝对 deadline、依赖假设、固定证据输入及 residual obligations。当前批准的 v0 子集只覆盖 `0 ≤ deadline ≤ 24`、exact-once 与两类事件顺序；其他语义须显式保留为 residual/unsupported，不得静默丢弃或软化 hard 要求。此范围由本 owner 维护，不代表通用作者语言编译器。

## 既有回归证据（不是新接口验收）

父级报告在新代码实现期间保存了以下旧契约套件：

| 套件 | 结果 | 证据 |
|---|---|---|
| P0 regression | 29 PASS | [日志](verification/p0_regression.txt) |
| TypedIR regression | 30 PASS | [日志](verification/typedir_regression.txt) |
| Sabre wrapper filesystem/parser regression | 5 PASS | [日志](verification/sabre_regression.txt)；不是 author-binding 原生预检 |
| P5 regression | 42 PASS，另有 1 项因缺少 Twisted 跳过 | [日志](verification/p5_regression.txt)；不是 43/43 PASS |
| TypedIR 首次导入尝试 | 初次因缺 `PYTHONPATH=tools` 报 `ModuleNotFoundError`；修正导入路径后的结果见上方 30 PASS | [首次错误日志](verification/typedir_regression_initial_import_error.txt) |

这些结果说明相关既有套件在记载的运行环境下的表现；不能替代 author-binding 新增单测、投影契约测试、反例、原生 P0 receipt 验证或独立审阅。

## 新接口离线单测

父级保存的 `verification/author_binding_tests.txt` 记录新增测试 **22/22 PASS**。其中 16 项覆盖编译、投影、hard residual、期限传递、未知/不可信 receipt 以及六个 pin 的 TypedIR 检查；独立语义审计另有 6 项，覆盖缺少暴雨观察时 delivery receipt 不足以满足全约束、deadline 分钟边界、clause ID 改名不改语义、相同版本内容变化使 plan digest 失效、unsupported hard 阻止 SAT、未 pin fixture 不作为证据。该日志证明的是固定 fixture 上的离线契约测试，不等于 live dispatch、midtask recompilation 或端到端运行时支持。

## Sabre parser/solver 离线预检

三个新 renderer 导出的固定问题文件通过本地 Sabre v0.8.0 parser/solver；沿用既有 search、space、time 和 character limits，具体命令、逐例计划/goal 与输入哈希见[预检记录](verification/sabre_preflight/README.md)，原始 stdout 为 `verification/sabre_preflight/parent-default.txt`、`parent-deadline-8.txt`、`parent-delivery-only.txt`。结果均为 `Result: Success!`, utility=1：default 13 visited / 230 generated；deadline-8 为 11 / 212，meeting 在 pre-action minute 8 结算，符合闭区间 `[0,8]`；delivery-only 为 4 / 39，仅有 delivery goal，没有被加强为 storm observation 或 meeting。前两例的 cloud-seed 是 fixture 的环境可行性动作，不是新增作者要求。

该预检只证明有限导出候选域可以解析并找到计划，不是原生游戏执行、dispatch、真实 receipt 或性能评估。本次预检源代码哈希：author-binding compiler `ddd9caa68fb3c6eb0779fb0db5f2a0917dce145cb6d2ff58ee8fcdac4f826f4d`；复用的 Baseline Gate Sabre exporter `8845bf57d70f11ae03f2c38d894f47d235404d5e20bfd678ec81474cc417261e`；复用的 Integration monitor `d0df705ae69e7faf6831b99508303c8c15cd1ec421e088d5d905408c8b81f260`。预检输入哈希列于对应 README；输入或源码变化后本结论不自动适用。

## 已验收契约与剩余边界

审计已逐项对照 descriptor、来源/版本、hardness、绝对期限、fixture entity IDs、Sabre/TypedIR projection map 与 hard residual 处理。当前投影仅包括：

| 已确认的作者条款 | Sabre 候选投影 | TypedIR 监测投影 |
|---|---|---|
| 三个注册事件各发生一次，闭区间 `[0,T]` | 对应计数器 exact-once guard/goal，并将 deadline 编入动作前置条件 | 每个事件 `EventCount(min=1,max=1, Window[0,T])` |
| delivery before meeting；B storm observation before meeting | 事件时间 guard：`delivery_time < meeting_time`、`observation_time(B) < meeting_time` | `EventOrder(EXISTS_DISTINCT_PAIR, EVENT_KEY, Window[0,T])` |
| unsupported hard clause | 不产生 planner projection，不得以计划满足 | 保留 hard residual；整体状态为 `PARTIAL_UNRESOLVED` / evidence `INDETERMINATE`，不得声称 SATISFIED |

具体来源字段、fixture ID/SHA、entity IDs、renderer/monitor source SHA 及逐 clause 映射随编译记录保存；见[原型 README](../../tools/planner_p0_v0/author_binding_v0/README.md)和编译器。测试涵盖 supported 正例、unsupported hard、字段/权限/来源错误、版本或内容变化、未知/非 allowlisted receipt 与 SAT 防护；完整逐例见 `verification/author_binding_tests.txt`。任何 unsupported hard 仍须显式保留为 unresolved，不能用“防伪”表述替代本地 pin 的有限完整性保证。

仍待独立审阅的条件与范围限制：
- 当前 preflight 仅接受六个固定 direct case 的清洁初态 SHA-256 pins；不支持 live 或 midtask recompilation。pin 校验固定 fixture 字节完整性，不鉴权原生生产者身份，也不建立通用 provenance 真实性证明。
- 计划版本/digest guard 目前是独立 primitive，未接入真实 native dispatch；不能宣称 stale-plan dispatch 已被拦截或在线版本变化会自动重新编译。
- 旧 P0 运行中已读回 sealed prefix/progress 的证据不代表新 adapter 支持 failure-prefix 延续；新工作仅作固定初态离线投影，不验证运行时修复、在线失败恢复或 dispatch 行为。
- 独立审阅仍须检查语义覆盖、renderer 与 monitor 的共同缺陷风险、unsupported/residual 处理及上述范围限制；之后由用户决定是否 CLOSED 或另行授权研究。

## 独立结果边界

- [P0 Baseline Gate RESULTS](../Planner_P0_Baseline_Gate_v0/RESULTS.md)拥有三场景单层 Sabre vs Sabre+HTN 结果：固定切片里单层已足够；六个 n=1 开发运行不证明普遍的分层无效或性能优势。本工作不回写或重开该 Gate。
- 旧 E0-H02 的 `planner status BUDGET != UNREACHABLE` CI 失败与后续有界修复状态由 [E0 RESULTS](../E0_KeyLedger_v0/RESULTS.md) 维护。预算耗尽与穷尽证明不可达必须分开；本工作不改变其历史预算、预期或结果。
- P5 shared-supply 失败仍只由 [P5 RESULTS](../Native_Platform_P5_v0/RESULTS.md) 维护。本工作不修改 P5、冻结 C++ Runtime 或原始 P0 结果。

## 收口条件

`READY_FOR_INDEPENDENT_REVIEW` 仅表示当前离线原型 checkpoint 已具备可审阅的测试、预检及明确失败/范围边界。外部独立审阅与用户关闭仍是不同状态；不得自行标记 CLOSED。后续 LLM 比较、扩大 domain/约束子集或新实验都不是本工作自动授权的下一步。
