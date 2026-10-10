# Native Platform P5 — RESULTS

状态：**READY_FOR_INDEPENDENT_REVIEW**，未 CLOSED。固定矩阵 12/12 场均 `COMPLETE` 且有 query-only DB 导出；11/12 结构审计 PASS，另 1 场保留为真实 shared-supply 约束失败。MCP 1 分钟控制链与旧阶段回归已核验；本状态表示证据包已就绪供独立审阅，不表示所有作者约束均 SAT。本页是唯一结果 owner；阶段入口见 [README](README.md)。

公开证据入口：[reviewer summary](public_evidence/p5-evidence-20261010T130007Z-d875ac/reviewer_summary.json) / [压缩 manifest](public_evidence/p5-evidence-20261010T130007Z-d875ac/manifest.json)。逐文件 SHA-256、raw/gzip 大小与解压校验见 manifest；已补入父级独立复核原件，早期 `INCOMPLETE` 失败原件也均保留、不覆盖。

## 运行记录

| 项目 | 状态 |
|---|---|
| 固定 development matrix | 已定义；见 [`bundles/dev-matrix-v1.json`](bundles/dev-matrix-v1.json) |
| 单元/合同测试 | 43/43 P5、53/53 P3、23/23 native bridge、30/30 TypedIR；记录的本地子进程均 exit 0；这是代码验证，不替代场景运行 |
| Native server 场景 runs | 固定开发矩阵 12/12 `COMPLETE` |
| 持久化世界 DB readback | 12 场均有 query-only DB 导出 |
| P5 逐场结构审计 | 11/12 PASS；1/12 shared-supply 真实约束失败，保留不改 expected |
| MCP / 旧 native 回归 | MCP reset/step/get_trace 1 分钟控制链 smoke PASS；unsupported 负控返回 `SEMANTIC_GAP` 且未建场景/新增 P5 场景标记。9 个 legacy cases（10 worlds）及 8 场 P4 worlds 共 18 worlds 完成回归；四组 P4 配对 integrity audit PASS |
| 最终阶段状态 | READY_FOR_INDEPENDENT_REVIEW；未 CLOSED |

首次 main smoke 原样保留（run ID `p5-main-reject-20261010T122314Z-f3377c`），记录为 `INCOMPLETE`，不能计作通过；随后针对嵌套 EvenniaSaver 容器读回的浅转换作了窄修。下表与审计统计指窄修后的 12 场运行。公开审阅使用上述 summary/manifest；逐例压缩文件按 manifest 索引，不把本地 raw 误作公共证据入口。

## 固定矩阵的实际观察

| 场景 | 实际观察 | 结构审计/判读 |
|---|---|---|
| Main / reject、accept | 两种原生社交预设下，4 项约束均 SAT；A/B 两次配送在 t6 完成，note response 在 t7 产生 | 两场均 PASS；run IDs：`p5-main-reject-20261010T123213Z-6058b4`、`p5-main-accept-20261010T123221Z-c6427a` |
| Side / reject、accept | 两种原生社交预设下，4 项约束均 SAT；A/B 配送在 t16，note response 在 t17 | 两场均 PASS；run IDs：`p5-side-reject-20261010T123154Z-866b07`、`p5-side-accept-20261010T123205Z-ea81f3` |
| Future edit + stale CAS | t2 接受 v2；新 side 目标 SAT，已有历史前缀与 pending identity 保持；NPC 实际仍走已开放 main。t3 用旧版本编辑得到 `VERSION_CONFLICT` | PASS；编辑更新约束/计划身份，不强迫路线重置；run ID `p5-future-edit-and-stale-cas-20261010T123250Z-d8966c` |
| Shared supply stolen/returned | 玩家 t1 真实 get、t4 真实 drop；两 NPC 任务绑定同一 courier_supply 实体。物品归还原点后，两 NPC 仍在 side room 与 destination 间巡查，不回 origin；0 delivery、0 note response | COMPLETE 但约束 VIOLATED，是固定开发基线中的唯一真实失败，不是运行/审计通过；玩家物品未被回滚/复制，任务未伪完成。具体原因是项目固定 patrol/恢复规则按出口排序循环（side east→destination→south→side），不重新观察 origin；这是项目接线/策略局限，不证明 GTPyhop 或 Ensemble 本身失效，也不是本轮自动修复项。保留原 SAT 预期未兑现。run ID `p5-shared-supply-stolen-returned-20261010T123233Z-60badf` |
| Director-off blocked | 没有 passage opportunity，目标按预期 VIOLATED | 负例审计 PASS；run ID `p5-director-off-blocked-20261010T123224Z-98e7a9` |
| Restricted opportunity denied | 请求越权 main 被拒绝，受限路线/既有 NPC 行为仍可运行 | PASS；run ID `p5-restricted-opportunity-denied-20261010T123258Z-d7c8e6` |
| Zero budget / deadline conflict / conflicting route goals | 预算为零、deadline=0 与互斥 route hard goals 均未被当作可满足；场景实际返回相应 VIOLATED 结果 | 三个负控审计 PASS；run IDs `p5-zero-budget-negative-20261010T123300Z-5c6bfe`、`p5-deadline-conflict-negative-20261010T123301Z-3cd437`、`p5-conflicting-route-goals-20261010T123307Z-d7b5bd` |
| Director-off open-world autonomy | main 已开放，NPC 自主行为满足约束，且没有作者机会调用 | 场景 SAT；修正后的 auditor 已通过，run ID `p5-director-off-open-world-autonomy-20261010T123315Z-885fa6` |

修正 auditor 后，12 场中 11 场结构审计 PASS，shared-supply 一场忠实记录为行为 VIOLATED。所有运行均 `COMPLETE` 只表示场景/证据生成流程完整，不等于作者约束 SAT。MCP reset/step/get_trace 1 分钟控制链 smoke 已通过；unsupported 负控纯加载失败闭合，返回 `SEMANTIC_GAP`、`scene_created=false`，只读 P5 场景标记计数保持 17→17（不是全 DB 对象数）。12 场矩阵对应源码提交 `2740923a95a8c8779cca3f31040351044a7e3334`；当前仅 `p5/audit.py` 的 off-open 计量修正与 `p3/control_service.py` 的 MCP await 修正不同，其他 manifest 所列 P5/world/agency/Ensemble/TypedIR 源文件哈希一致，因此没有将审计/MCP 窄修误称为重新运行 12 场。

旧回归为 9 个 legacy cases（10 个 worlds）加 8 个 P4 worlds，共 18 worlds；P4 四组配对的 integrity audit 全部 PASS。P4 结果状态分别为：open 两臂 SAT；blocked-return OFF VIOLATED / ON SAT；held 与 short 两臂均 VIOLATED。完整交付边界见 reviewer summary；本阶段仅达独立审阅，不是 `CLOSED`。

## CI

源码提交 `2740923a95a8` 的 [native-platform-p3 workflow](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38052291276) 成功；[runtime-regression workflow](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38052291272) 整体失败，失败项是既有 E0 `H02 BUDGET` contract，其余 5 个 job 成功。该固定预算问题未在 P5 中修改；不能将其描述为全仓 CI 绿。此为该历史提交的 CI 结果；后续 auditor/MCP 窄修的 exact-head CI 需以[当前分支 Actions](https://github.com/2003SINGER/character-dynamics-lab/actions)为准。本地 native-server runs/DB 与 workflow 的 host-contract 测试是不同证据边界。

## 判读边界

P5 使用有限、条件性的作者机会 AND/OR 候选枚举，并复用现有 TypedIR、GTPyhop HTN 与原生 Ensemble。它不是完整 DM：候选只涵盖注册的 passage 机会；符号下界不是 NPC 到达时间预测；NPC 原生决策可以不执行或拒绝。storylet 仅为内容文本。Bundle CAS 编辑的是计划版本与未来要求，不等于 NPC 持久目标进度，也不回写过去判定。

后续结果应按原始场景收据、TypedIR trace 和独立 DB readback 填写，并将完整成功、约束未满足、运行不完整和证据不确定分开；不以单测代替真实场景证据，也不据此声称玩家效度、心理机制或方法新颖性。
