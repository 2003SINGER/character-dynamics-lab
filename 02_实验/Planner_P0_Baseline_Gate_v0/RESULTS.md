# P0 Baseline Gate v0 — results

**状态：DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW。** 本结果仅覆盖冻结 `ad2e017` 的 direct fixture 与三个已授权场景；每格运行一次，共六次。三个场景的 A/B 同 seed `20261011`。不调参、不扩预算、不重跑；运行期间未作 correctness repair，也没有 retry。

## 结果

三场景中，单层 Sabre A 和 Sabre + GTPyhop B 均在原生世界达到同一目标：恰好一次交付、B 一次观察风暴、一次会议见证，且 delivery 与 storm observation 均先于 meeting（两者之间无先后要求）。独立复核对六个 run 的 `parent-readback.json` 全部 PASS；父级另行确认每例 5 项 TypedIR constraints 均 SAT、六例合计 30 项，初始快照在 ID 归一化后成对一致、seed 一致、12 个 source hashes 成对相同且匹配当前冻结源，Sabre per-call limits 相同，搜索指标重算相符。

父级逐项比对了每个 paired scene 的完整原生 story action signature（action dict、native code、pre/post clock），A/B 三场景均完全一致，包括 route-repair 的失败动作。因此观察到的差异在本切片中属于计划表示/调度与成本，不是不同的最终原生执行链或世界结果。

| 场景 | 共同原生结果（meeting 后 story clock / 原生 story actions / witness 前 clock） | A calls；visited/generated | B calls；visited/generated；HTN proposals / visits | 累计 episode wall A / B |
|---|---:|---:|---:|---:|
| `direct-clean` | 9 / 9 / 8 | 9；75 / 1,092 | 7；48 / 574；3 / 12 | 7,439 / 7,322 ms |
| `route-repair` | 12 / 12 / 11 | 12；114 / 1,534 | 8；59 / 624；5 / 22 | 8,778 / 7,799 ms |
| `high-causal-replan` | 10 / 10 / 9 | 10；84 / 1,190 | 8；57 / 672；3 / 12 | 8,204 / 7,769 ms |

三例都在 native clock 24 封窗，evaluation drain 分别为 15、12、14 个动作。这里报告的是故事目标完成时刻与封窗后的完整 run 两种口径，不把 drain/wait 当作 NPC 策略。B 使用较少的 Sabre calls，但本比较的搜索空间表示不同；调用数、节点数和墙钟不构成严格等总计算量优势证据。

route-repair 在 clock 2、A 持物时封闭主路；对已提议的主路移动，原生系统真实拒绝并消耗 1 分钟。task identity、持物状态、任务进度序号及 item progress 均保留，之后通过 side route 完成；这是修复质量相同的真实受扰运行，不是规划器未遇到失败。high-causal-replan 在 clock 6、seed 5 已生成且 due 7 时执行零 tick 的真实取消；已完成交付前缀保持不变，第二个唯一 seed 6 产生实际风暴，随后目标完成。两算法均完成这两个扰动场景。

## 成本与表示边界

`comparison.json` 汇总六个原始 run 的 ID、动作/时钟口径、搜索指标与分层墙钟。Sabre 每次调用均使用相同 v0.8.0 配置（200 visited、5,000 generated、5,000 ms native、12 s wrapper）；B 另有 HTN 上限 500 visits / 0.25 s per proposal。各层计时存在嵌套/重叠，不能相加：wrapper-minus-native-search 仅是 overhead proxy，不是纯 Java startup；HTN/refinement、native/RPC、evaluation drain 分开列示，但不得将 RPC wall 与其他 wall 相加成 episode total。两臂只有相同的 per-call Sabre budget，不是 equal-total-compute 比较。

Sabre `--cost t` 与 author limit 24 是 symbolic action temporal depth，不是 native simulation minutes。A 将 GET/MOVE/DROP 表为原子动作；B 使用手工定价的 delivery macro，再由现有 actor-local-view GTPyhop HTN 细化，二者粒度不同，因此 symbolic cost/depth 与 node count 不可视为同单位搜索效率，也不证明 native 最短完成时间最优。

B 的 exporter **不是字节级复用 frozen macro**：它复用宏结构，并新增与原生 DROP 对齐的 `!kit_held(A)` 效果；A 也清除 held 状态。两臂还共同加入 once-only storm-look / meeting guards。这些是本 gate 新 exporter 的投影校正；旧 P0-Integration renderer/runner/monitor 与 HTN 源码没有改动，且不据此声称复现旧 integration 域的字节级模型。

维护工作量只给代理量：每变体生成 8–9 个 Sabre action declarations；variant exporter 90 LOC、frozen exporter 196 LOC、既有 P3 planning 225 LOC。它们不是人时或难度测量，也没有量化 Java 安装/启动、模型设计、导出/RPC/封窗的作者工时。结果体现的是整个架构组合差异，不是只替换一个 solver。

## 结论与限制

在这三个固定 direct 场景内，单层 Sabre 已足够达到目标；多层方案没有表现新增可达性或更好的修复质量。B 少用了高层 Sabre calls，但宏表示、手工价格与 HTN 细化均不同；不能从节点或调用数推断方法优势。每格 `n=1` 的六次 DEVELOPMENT 运行是描述性检查，不是统计性能、成功率或泛化证据。

这是 joint author-authorized direct orchestration，不是独立 NPC agency；作者目标是固定 fixture，不是通用 AuthorBundle/TypedIR→Sabre 约束编译器。旧 P0 的 LLM/embedding/Qwen 路线仍暂停，P5 shared-supply 失败仍保留。此 gate 到此停止；任何新场景、预算/调参、通用编译器、后续比较或修复须另行讨论与授权，不自动实施，也不将本 checkpoint 标为 CLOSED。

## 可复核材料

- [冻结比较协议](README.md)；[机器可读比较摘要](comparison.json)。

| 场景 / arm | `run.json` | 独立 DB/ledger readback | 初始 DSL | 首次 raw Sabre stdout |
|---|---|---|---|---|
| direct-clean A | [run](runs/p0bg-direct-clean-A-20261011T115534Z-4f5c03/run.json) | [PASS](runs/p0bg-direct-clean-A-20261011T115534Z-4f5c03/parent-readback.json) | [DSL](runs/p0bg-direct-clean-A-20261011T115534Z-4f5c03/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-direct-clean-A-20261011T115534Z-4f5c03/p0bg-direct-clean-A-20261011T115534Z-4f5c03-a-01/stdout.log) |
| direct-clean B | [run](runs/p0bg-direct-clean-B-20261011T115555Z-5a94b4/run.json) | [PASS](runs/p0bg-direct-clean-B-20261011T115555Z-5a94b4/parent-readback.json) | [DSL](runs/p0bg-direct-clean-B-20261011T115555Z-5a94b4/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-direct-clean-B-20261011T115555Z-5a94b4/p0bg-direct-clean-B-20261011T115555Z-5a94b4-b-01/stdout.log) |
| route-repair A | [run](runs/p0bg-route-repair-A-20261011T115612Z-14caf8/run.json) | [PASS](runs/p0bg-route-repair-A-20261011T115612Z-14caf8/parent-readback.json) | [DSL](runs/p0bg-route-repair-A-20261011T115612Z-14caf8/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-route-repair-A-20261011T115612Z-14caf8/p0bg-route-repair-A-20261011T115612Z-14caf8-a-01/stdout.log) |
| route-repair B | [run](runs/p0bg-route-repair-B-20261011T115633Z-c85e0a/run.json) | [PASS](runs/p0bg-route-repair-B-20261011T115633Z-c85e0a/parent-readback.json) | [DSL](runs/p0bg-route-repair-B-20261011T115633Z-c85e0a/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-route-repair-B-20261011T115633Z-c85e0a/p0bg-route-repair-B-20261011T115633Z-c85e0a-b-01/stdout.log) |
| high-causal-replan A | [run](runs/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c/run.json) | [PASS](runs/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c/parent-readback.json) | [DSL](runs/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c-a-01/stdout.log) |
| high-causal-replan B | [run](runs/p0bg-high-causal-replan-B-20261011T115825Z-b779d4/run.json) | [PASS](runs/p0bg-high-causal-replan-B-20261011T115825Z-b779d4/parent-readback.json) | [DSL](runs/p0bg-high-causal-replan-B-20261011T115825Z-b779d4/problem-01.txt) | [stdout](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/p0bg-high-causal-replan-B-20261011T115825Z-b779d4/p0bg-high-causal-replan-B-20261011T115825Z-b779d4-b-01/stdout.log) |

Each gate run directory stores its DSL problem sequence and native run JSON/readback. Per-call Sabre `stdout.log`/`stderr.log` files are under the existing evidence root [`../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/`](../Planner_P0_v0/sabre_baseline/evidence/baseline-gate-v0/); exact paths are recorded in the corresponding `run.json`. Full native traces remain in each gate run directory.
- 新 exporter 与 runner 源哈希见各 `run.json` 的 `source_sha256`；全部 12 项在六例中相同并与冻结当前源一致。单次 A/B preflight 输出为 [A](preflight/baseline-gate-a-20261011.txt)（SHA-256 `2bec8381d8a32c2a34d6372cb5bab749e43f03beec586c87dbae4528dc006cae`）与 [B](preflight/baseline-gate-b-20261011.txt)（SHA-256 `0dc669f8a0bbfcceb2768cc58e40165de5f30e033d578e9b7a704c0061dff0c3`）；它们在 wrapper 执行后从 `02_实验/Planner_P0_v0/integration_v0/preflight/` 迁入此 owner，字节/SHA 保持一致，原始 wrapper config 的 problem path 可能仍指旧位置，不要据此寻找 live run 输入。六个 live `problem-*.txt` 则直接保存在本 owner 的 run 目录。
- readback 的 `counts.CLOUD_DISSIPATED=0` 只统计 `accepted=true` 的动作；取消 mutation 的 ledger event 为 `accepted=null`，因此该计数不是“没有取消”。应检查 high-causal run 的 raw ledger/mutation boundary。
- 本地验证：baseline gate projection tests 6/6、旧 integration projection tests 7/7、旧 native contract tests 9/9、shared-world tests 7/7、Sabre wrapper tests 5/5 均通过。wrapper 第一次 read-only sandbox 临时目录写入遇 PermissionError；以限定临时目录权限重跑后通过，非算法失败。repo health check exit 0，保留四个既有 warnings（3 个本地依赖大文件、1 个历史原文重复），未新增修复。
- 本页记录 local native evidence 与离线验证；离线 CI 不替代本报告中的 native run 与独立 readback。Exact-head workflow 状态以 GitHub Actions 为准。
