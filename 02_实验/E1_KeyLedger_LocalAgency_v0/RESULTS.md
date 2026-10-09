# E1-1｜局部 GOAP 与独立 B 的开发验证

日期：2026-10-09。状态：**DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW**，不是正式实验或 `CLOSED`。本页是唯一结果 owner；[协议 v0.r1](../../00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md)定义语义，[代码与复现](../../tools/e1_keyledger_v0/README.md)定义实现。

## 交付与版本

用户明确授权“E1-1 最小实现与开发验证；暂不正式实验”。完成了独立 E1 adapter、真实 B chooser、A-local `h=0` UCS、独立手写 oracle 模块（world / fixed-B 两种搜索模式，共享模块内转移）、Monitor、完整 checkpoint 与开发运行器。**没有训练 policy**：B 的 utility/优先级是公开手写契约；A 使用成熟搜索算法，不读取 W 或真实 O_B。E0 源码/冻结协议与 C++ Runtime 未修改。

源码提交：[`f637743a8af9faacbb908e8b4bae4b8f4661b193`](https://github.com/2003SINGER/character-dynamics-lab/commit/f637743a8af9faacbb908e8b4bae4b8f4661b193)。父级精确源码运行 `parent-f637743-20261009`；重复运行后缀 `-rerun`。环境 Python 3.12.14 / macOS 27.0.1 arm64，`PYTHONHASHSEED=0`。每 solver/episode 开发 cap=10,000；候选 watchdog=2.0s，A 的所有 replan 共用一个 budget ledger；**正式实验预算未冻结**。后续交付提交仅含证据/外围文档，以及协议 §8 一句开发授权澄清；v0.r1 行为、时间、预算规则和包源码均不变，原运行的 protocol hash 保留，不能伪称其为后来文档 hash。

完整原始运行、输入、逐步状态、回执、事件、seal、策略输入、预测、预算、错误、CI artifact 和审计脚本保存于[证据 ZIP](evidence/E1_dev_f637743_20261009.zip)，成员与归档 hash 见[索引](evidence/INDEX.md)。可直接审阅[父级审计 JSON](evidence/audit.json)、[E1 单测日志](evidence/unit-tests.log)和[TypedIR 日志](evidence/typed-ir-tests.log)。本地非压缩原件仍在 `runs/e1_keyledger_v0/dev/`，未覆盖或删除。

## 12 格结果：匹配预期不等于全部取得账本

世界 joint oracle 在每格均 **SOLVED @8**（97 次扩展）。下表 fixed-B 无解均为完整穷尽；实际失败均在 T 封口后由 Monitor 判 `VIOLATED`，不是 planner 预测。实际取得账本为 **6/12**；正确性对照为 **12/12**，另有 **24/24 oracle 对照**。

| K | B | T | fixed-B oracle：结果 / 扩展 | 实际 Monitor / witness | A 全部 replan 累计扩展 |
|---|---|---:|---|---|---:|
| known | PAY | 8 | SOLVED @8 / 72 | SATISFIED @8 | 27 |
| known | PAY | 10 | SOLVED @8 / 72 | SATISFIED @8 | 29 |
| known | TOOL | 8 | UNREACHABLE / 93 | VIOLATED，无 witness | 55 |
| known | TOOL | 10 | SOLVED @9 / 94 | SATISFIED @9 | 38 |
| known | KEEP | 8 | UNREACHABLE / 79 | VIOLATED，无 witness | 51 |
| known | KEEP | 10 | UNREACHABLE / 139 | VIOLATED，无 witness | 99 |
| unknown | PAY | 8 | SOLVED @8 / 72 | SATISFIED @8 | 27 |
| unknown | PAY | 10 | SOLVED @8 / 72 | SATISFIED @8 | 29 |
| unknown | TOOL | 8 | UNREACHABLE / 93 | VIOLATED，无 witness | 55 |
| unknown | TOOL | 10 | SOLVED @9 / 94 | SATISFIED @9 | 38 |
| unknown | KEEP | 8 | UNREACHABLE / 79 | VIOLATED，无 witness | 51 |
| unknown | KEEP | 10 | UNREACHABLE / 139 | VIOLATED，无 witness | 99 |

这里的 UNREACHABLE 是 `PROVEN_UNREACHABLE_IN_FINITE_DOMAIN`；完整性、termination、frontier、耗时和真实 witness ID 在原始数据中分别保存。主运行无预算停止或 Executor 错误。A episode watchdog 观测约 0.0076–0.0148s（含该 episode 内结算/重规划，不是纯搜索 CPU 时间）；两 oracle 各次约 0.0017–0.0044s。这些是本次开发观测，不是统计性能结论。

### 实际轨迹与决策机制

- **PAY：**B request `2→3`；A offer `3→4`；B 自选 ACCEPT `4→5`、真实 exchange `5→6`；A unlock `6→7`、take `7→8`。B 收到 payment、保留 key beneficial ownership，但 tool 未归还。
- **TOOL / T10：**request 后，A 的规划自己选择 return `3→4`，再 offer `4→5`；B ACCEPT `5→6`、exchange `6→7`；A unlock `7→8`、take `8→9`。B tool/payment 分别达成。A 归还是完成 A 目标的规划手段，不是 B 请求自动控制 A。
- **TOOL / T8 与 KEEP：**A 完整搜索无目标计划后 no_control/idle 到期限，主轨迹不强迫报价，也没有伪造 B 的拒绝事件。B 在真实 OFFERED 状态的 TOOL-before/after-return、KEEP 拒绝由专项 consumer 测试验证。

B 根据自身 O 计算 `V=2−c−p·I(tool未归还)`：PAY 为 +1；TOOL 从 −3 变 +1；KEEP 为 −1。它不是全知心理模型。B 的 `request_sent` 从自己的成功 request receipt/event @3 投影，start/拒绝不能设置；World 的 request bit 只用于物理验证。

Known/Unknown 对照的首个 A 动作、真实动作序列和最早结果相同，是**有效零效果负控**：通用 offer 不要求知道 key ID，B 接受后才披露。Unknown 计划中的 `LoanKey(offer_id)` 仅为非 dispatchable 预测变量；真正 unlock 由后来合法披露的 key1 grounding。不能据零差异宣称信息普遍不重要。

## 有界验收

- 父级 E1 单测 **30/30**；复用 TypedIR **30/30**。覆盖请求成功/拒绝、非法 key grounding、A 越权交易、DECLINE 后不发生部分交易、伪造/未封口事件、历史回执、fork 与预算恢复，以及两个 oracle 的合法路径在真实 Executor 回放。
- 在源码提交 f637743 上，primary/rerun 的 29 项 E1/依赖/协议 hash 与当时实际文件一致；逐步 after-state hash 重算 **84/84**。角色动作、时钟、W/O、事件/回执 IDs、goal、参数及扩展数语义相同。比较只排除 `run_id/created_utc/elapsed_seconds` 和包含计时的派生 `before_hash/after_hash`，不是 byte-identical 文件声明；完整排除计数见 audit JSON。重跑归档中的原审计脚本应使用该源码 checkout，而非假定后续文档 HEAD 等于原 HEAD。
- 同一 B view、不同隐藏 `W.request_used`：B proposal 相同，World start 接受/拒绝不同；两者均不提前写 B 的成功请求历史。该负控区分“角色知道什么”和“世界允许什么”。
- cap=1 与显式极短 watchdog=1e-9 的独立诊断中，世界 oracle、fixed-B oracle、A planner 均为 `BUDGET/complete=false`，case 标 `INCOMPLETE_BUDGET`；没有变成不可达或 PASS。正常开发配置仍是 10k/2s，没有失败后加预算。
- 三次未提交阶段开发运行原件也保留。其 manifest 标旧 HEAD+各自源码 hash，不能冒充精确源码提交运行；早期“recorded”不构成当前版本验收。父级正式交付使用 f637743 的开发运行和上述独立检查。

## CI：f637743 版本快照与后续运行

精确源码 E1 [run 37898921437](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37898921437) **SUCCESS**：30 项单测和 12 格开发回放均通过；原始 Ubuntu artifact 已下载并随 ZIP 保留。Python 3.12.15 / Linux x86_64，同 10k/2s、同源码 revision/hash。

该版本快照的总体 [runtime-regression run 37898921385](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37898921385) **FAILURE**，唯一失败作业为既有 E0；其他五项（含 C++ Configure/Build/CTest/Reference verification）成功。E0 单测 38/38，但固定 fixture H02 触发墙钟上限，具体记录由[E0 结果 owner](../E0_KeyLedger_v0/RESULTS.md)维护；失败日志与原始压缩 artifact 同样保留。该历史失败不代表最新运行状态。

后续交付 [`48412e4`](https://github.com/2003SINGER/character-dynamics-lab/commit/48412e4) 的 E1 development [run 37901728095](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37901728095) 与总体 runtime-regression [run 37901728081](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37901728081) 均 **SUCCESS**。

## 停止与下一步

本轮最小实现和开发验证已完成，**到此停止**。外部定向审阅已收到：未发现 E1-1 开发阻断，建议停止扩修；成熟 GOAP 已能解公开 deterministic B 合作域，Known/Unknown 零差异是该有限实例的负控，不证明一般认知能力。此为外部 AI 审阅，不是独立人工验证，也不自动将状态改为 `CLOSED`；状态仍为 `DEVELOPMENT_VERIFIED / READY_FOR_INDEPENDENT_REVIEW`。正式 E1 实验、formal budget/environment 冻结、E1-2 AND/OR、Director、训练或更大世界均未启动。

本次说明成熟 GOAP 能正确解该有限、公开 deterministic B contract 的合作域，且装置能分开世界上界、固定策略上界、实际行为与预算不足。它**没有暴露一个需要原创方法的性能瓶颈**，不证明 NPC 自主性、一般认知能力、作者成本、心理规律或玩家生命感。下一步是否研究更强的信息/策略不确定性，应由后续明确问题与授权决定，不靠继续完善 E1-1 自动推进。
