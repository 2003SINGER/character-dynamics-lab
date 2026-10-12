# Planner Adapter Integration v1 — RESULTS

**结论：PARTIAL / READY_FOR_INDEPENDENT_REVIEW**（2026-10-12）。固定的 8 组匹配场景已产生 16 条完整的 24-round 轨迹，另有 1 条单 round 的 stale-control 诊断；17 个场景记录均有独立 DB readback。stale 场景仅封存到 minute 1（horizon 24，`run_status=INCOMPLETE`），不能计为完整 24-minute 运行。但 Sabre 在真实 P5 快照上未产生可执行候选，因此不能声称 Sabre→GTPyhop handoff、完整目标满足或成功后缀修复。`DEVELOPMENT_RUN_RECORDED` 仅表示轨迹采集完成。此报告是本实验唯一结果/状态入口；能力来源细节见[能力审计](CAPABILITY_AUDIT.md)，运行复现见[包 README](../../tools/planner_adapter_integration_v1/README.md)。

## M0：真实执行路径与边界

```text
固定 AuthorBundle + 原生封存前缀 / W capability projection / A、B 对称采样的 O
  → model.build_snapshot（物理世界 W 与角色局部观察 O 分离）
  → sabre.render_problem / invoke_sabre（r2 有界搜索）
  → projection_status 与首个注册世界机会的 freshness/权限/预算检查
  → runner（仅候选首步为注册的 route opportunity 时可请求 dispatch）
  → P5 step_world（Evennia 唯一真实时钟、世界状态与 receipt）
      → A、B 原有 GTPyhop / Ensemble callback 与 P5 TypedIR ledger
  → sealed feedback / independent DB readback / 下一边界重新投影
```

新增 P5 只读投影暴露既有世界对象、任务绑定、路线边与相应世界机会元数据；另在新建场景 reset 时补齐既有 A→courier / B→resident 控制角色标签，使认证的局部观察入口可以解析角色。不回填旧场景，不修改 owner 检查、NPC 策略或世界规则；投影本身不向 NPC 注入路径知识、不创建 NPC 新任务。P5 没有动态角色任务派发入口，所以 Sabre 计划中的人物步骤仍是条件性预测/等待，不是 NPC 接受指令的证据。即使候选可搜索，native receipts 才是事件事实，TypedIR verdict 才是目标结算。当前实验没有产生 Sabre 正候选，图中完整边链仍未得到实证贯通。

## M1–M5 与 A1–A8

| Gate | 结果 | 证据边界 |
|---|---|---|
| M1 | **PASS（source/capability mapping）** | [能力审计](CAPABILITY_AUDIT.md)及 versioned P5 read-only seam；不是 planner handoff 证明。 |
| M2 | **PARTIAL** | Sabre 确实对真实 P5 投影调用搜索；结果只有 `BUDGET_LIMIT`、`NATIVE_NO_SOLUTION` 或投影不确定，无正候选。前两者只说明有限投影/搜索结果，不能推断整个 P5 世界不可达。 |
| M3 | **NOT DEMONSTRATED** | 没有 Sabre 正候选进入 GTPyhop/native dispatch。Director 组的原生 callback 只证明旧 P5 执行链工作。 |
| M4 | **PARTIAL** | 已观察真实 minute prefix、玩家扰动、作者 CAS 编辑与版本变化；没有 Sabre 成功 suffix repair。stale-control 未实际提交候选，故不能算 stale 拒绝通过。 |
| M5 | **PASS（matched experiment recorded）** | 8 组相同输入的 Sabre / P5 Director 运行完成并有独立 DB readback。效能比较仅为描述性 n=1，不是方法优越性结论。 |

| Acceptance | 结果 | 实际判定 |
|---|---|---|
| A1 | **NOT DEMONSTRATED** | 无预选路线的结果目标在 Sabre 中未产生可执行候选；不能以 Director 的成功替代。 |
| A2 | **NOT DEMONSTRATED** | 12/24 分钟窗口已匹配运行，但 Sabre 没有候选可比较其完成时间。没有用观察到的 6/16 分钟完成时长硬编码。 |
| A3 | **PARTIAL** | 机会预算与世界权限负控均被执行；Sabre 没有满足目标。不能把正确拒绝/无解报成完成。 |
| A4 | **NOT DEMONSTRATED** | 没有可逐步关联到 native GTPyhop 动作及 receipt 的 Sabre actor-chain。 |
| A5 | **PARTIAL** | Director 原生运行记录到拒绝（默认 reject 场景）和接受（accept 场景），证明真实策略分支存在；Sabre 未形成预测→实际回应的闭环。NPC 是否合作仍非作者权限。 |
| A6 | **PARTIAL** | Director 的编辑保留历史前缀、待执行身份，之后由正常 callback 结算；Sabre 无成功重规划 suffix。 |
| A7 | **PASS（matched runs）** | 每个场景对的输入和采样时点匹配；结果见下表。 |
| A8 | **PASS（既有算法回归）** | [未修改 Sabre/GTPyhop 回归](validation/upstream-regression-20261012T011108Z/summary.md)通过；这不是新适配器集成通过。 |

## 固定运行结果

8 个匹配对共享各自的 AuthorBundle、场景初态、时限、seed、preset、权限/预算及干预日程。两组都在同一 sealed minute 以 A→B 顺序调用原生 `observe_actor`；该采样会更新 retained O/witness，因此下表只对这个共同协议有效。公开的[逐文件 hash index](public_evidence/index.json)来自最终 `evidence-index-20261012T032956Z-656a59.json`，SHA-256 `53fcd3b03a8b7e288e1bca34232eee0a8ca79e1578057f725d2345dcd3c9f579`。早期 032542 index 有 validation 路径漏收，不能作为完整索引。

[完整原始证据包](public_evidence/native-evidence.tar.gz)共 12,737,591 bytes，SHA-256 `b940a7028b636b7d13e75e10507dc1835e7dcfdcb8383c045866974041d9d065`。父级逐项验证了 854/854 原文件与包内文件的 hash/size，包括 17 个场景记录、159 个 validation/preflight 文件与代码/输入；另外包含原样 index 和重启 lifecycle，合计 856 个成员。包内 `evidence/` 下按项目相对路径重建，原始 ignored `runs/` 不另逐文件提交。旧开发包在本地 ignored `runs/development-packages/` 保留，没有覆盖实验历史。

| 固定场景 | P5 Director（原生） | Sabre adapter | 解释 |
|---|---|---|---|
| `outcome-wide24` | 4/4 hard goals SATISFIED；A、B 交付与 A→B 拒绝回应均有 receipt | 4/4 VIOLATED；22 次 BUDGET_LIMIT、2 次 bounded NATIVE_NO_SOLUTION；0 receipt | 基础宽时限配对。 |
| `outcome-tight12` | 4/4 SATISFIED | 4/4 VIOLATED；raw 为 13 BUDGET_LIMIT + 11 NATIVE_NO_SOLUTION；后 11 次另标 PROJECTION_INDETERMINATE | 紧时限；不是 Sabre 已证明世界不可达。 |
| `outcome-wide24-accept` | 4/4 SATISFIED；回应为接受 | 4/4 VIOLATED；22 BUDGET_LIMIT、2 NATIVE_NO_SOLUTION | 同 preset 下验证真实接受分支。 |
| `outcome-wide24-budget1` | 4/4 SATISFIED | 4/4 VIOLATED；18 BUDGET_LIMIT + 6 NATIVE_NO_SOLUTION | 机会预算变化的匹配对。 |
| `outcome-tight12-budget1` | 4/4 SATISFIED | 4/4 VIOLATED；raw 为 13 BUDGET_LIMIT + 11 NATIVE_NO_SOLUTION；后 11 次另标 PROJECTION_INDETERMINATE | 紧时限与机会预算约束。 |
| `outcome-no-opportunity-budget` | 3 个适用目标均 VIOLATED，0 receipt | 同为 3 个 VIOLATED，0 receipt；bounded NATIVE_NO_SOLUTION | 机会预算为零的负控。 |
| `outcome-no-world-permission` | 3 个适用目标均 VIOLATED，0 receipt | 同为 3 个 VIOLATED，0 receipt；bounded NATIVE_NO_SOLUTION | 无世界机会权限的负控。 |
| `outcome-player-interruption-cas-edit` | B delivery 与编辑后的 side-route 条件 SATISFIED；A delivery、note response、顺序目标 VIOLATED | 5 个目标均 VIOLATED；raw 为 2 BUDGET_LIMIT + 22 NATIVE_NO_SOLUTION；后 22 次另标 PROJECTION_INDETERMINATE；0 receipt | 包含玩家扰动及 minute-2 CAS 编辑。不是成功 repair。 |

`raw_search_status_counts` 与 `search_status_counts` 分别记录原求解结果和投影/派发资格标签。当前 runner 对 Sabre 每个 minute 都调用求解器，即使投影已不允许派发；`PROJECTION_INDETERMINATE` 不表示跳过了搜索。Director 控制组不调用 Sabre，不能把其零 Sabre 耗时写成规划成本为零。

Director 五个可行常规场景各自都在 minute 12 记录 A/B delivery；note response 在 minute 13，按场景 preset 真实记录接受或拒绝。该结果来自 P5 callback/策略，不是 Sabre 的预测。side delivery 在历史样例为 minute 16，而本批 Director 为 minute 12；两者差异与局部观察/探索有关，不用于声称方法加速。搜索时间及请求开销为单场景单次的描述数据，受不同状态和投影分支影响，不报告排名或效率优势。r2 的实际限额固定为 `bf`（best-first）、`t`、`h+`、10,000 visited、100,000 generated、5,000 ms 原生搜索、30s 外部进程保护、author 24 / character 16；不因本次失败继续调大。旧 r1 与所有错误、负控均保留在 evidence pack。`BUDGET_LIMIT` 是资源护栏触发，不是不可达证据；`NATIVE_NO_SOLUTION` 也仅针对该有界渲染域。

### 扰动、CAS 与 stale control

minute-2 作者编辑在 Director 场景被接受，原生 edit receipt 的 `historical_prefix_preserved=true`。编辑前后，A pending operation `p5:…:5829:1` 与 B `p5:…:5830:1` 身份相同；随后两个 callback 正常结算它们。不能把跨整个 step 的 pending identity 变化误判为 reset，也不能据此声称 Sabre 保留了 pending：Sabre 编辑前后均无 pending，因此其 retention 证据是空洞的。玩家 get@2、drop@6 都有真实 SETTLED 回执；v2 新增 side-route 的未来窗口 [2,4]，原配送/便条的绝对 deadline 24 没有重置。Director 最终只有 B delivery 与新 side-route 条件满足；A delivery、note/order 目标仍失败。

stale-control 的 v2 编辑已被 native 接受，未打开 route，但没有可提交的精确 Sabre 候选，`native_intervention_status=null`。状态是 `STALE_CONTROL_NOT_EXERCISED`，不算 stale guard 拒绝通过。完整对照见 evidence pack 中 `outcome-player-interruption-cas-edit-*` 与 `stale-edit-negative-*` 目录。

## 九项交付对照

| 交付项 | 状态与位置 |
|---|---|
| 1. 真实架构与数据流 | 本页 M0 flow；实现入口见 [README](../../tools/planner_adapter_integration_v1/README.md)。 |
| 2. 原生/适配器能力边界 | [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md)。 |
| 3. adapter 实现与复现入口 | [tools/planner_adapter_integration_v1](../../tools/planner_adapter_integration_v1)；限定的离线与 native 复现命令见 README。 |
| 4. 作者结果目标→Sabre 计划候选→native receipt | **未交付成功链**；本轮没有 Sabre 正候选，原始 bounded outputs 保留在压缩包/index。 |
| 5. 高层角色步骤→角色本地 GTPyhop 执行 | **未证明集成**；旧方法能力回归不等于新 adapter handoff。 |
| 6. 扰动/编辑后的后缀修复 | **部分证据**：native prefix/CAS 与 Director 后续 callback 记录；无 Sabre successful suffix repair。 |
| 7. 与 P5 Director 匹配对照 | 8 对固定输入与双边 readback 见 evidence index/压缩包。 |
| 8. pass/partial/fail/unknown 判定 | 本页 M/A 表；不把失败场景的 `run_status=COMPLETE` 等同目标通过。 |
| 9. 后续方法建议 | 先用已观察到的 native 成功路径校准并消融检查 domain/heuristic 与受限投影的一致性；之后再决定是否改方法。当前不自动启用 LLM、新框架或 P6。 |

## 成本与建模劳动

以下是各一次开发运行中 24 个边界的累计计时，单位秒；不是端到端总墙钟（未计所有观察、读 trace 和 DB 导出），也不是等搜索空间/等计算预算的性能比较。Director 的规划和角色 callback 包含在服务器 step RPC 中；Sabre 列只含外部 adapter/render/search。

| 场景 | Sabre adapter/search | Sabre 组 step RPC | Director 组 step RPC |
|---|---:|---:|---:|
| wide24 | 22.005 | 6.013 | 7.023 |
| tight12 | 15.431 | 5.872 | 6.543 |
| wide24 accept | 21.643 | 5.879 | 7.255 |
| wide24 budget1 | 23.389 | 5.881 | 6.792 |
| tight12 budget1 | 18.253 | 6.132 | 7.010 |
| opportunity budget0 | 6.640 | 5.747 | 5.635 |
| no world permission | 6.397 | 5.700 | 5.838 |
| player interruption + CAS | 8.546 | 6.965 | 8.503 |

两组游戏动作、权限、机会成本和角色方法相同，但高层求解表示、节点护栏与计时边界不同。没有统计显著性、普遍成功率或速度优势结论。建模仍需要人工编写 P5 专用 `model.py` / `sabre.py`，来源在能力审计中逐项列出；没有测量作者人时、维护劳动或自然语言绑定成本，不能宣称减少创作成本。

## 独立验证与来源

- Planner Adapter Integration v1：20/20；P5 正确 Evennia venv：44/44；P3 venv：53/53；System Baseline v0 venv：25/25。此前全局 Python 缺 Twisted 的结果已由正确环境复核，不用其 skip 结果代替。
- 13 个保护源文件 hash 未变化。第三方 Sabre pinned source 与 Main class 保持不变；运行时 search limits 未超出已授权 r2。更早的解析/投影错误和失败 attempt 均留在验证历史，不被成功采集状态覆盖。
- 原始完整轨迹、问题文件、native receipt、independent DB readback 和历史诊断一并保存在上述哈希索引所列归档中。归档采用显式文件 allowlist，无原始对话、`_private`、认证文件、AppleDouble 或缓存成员；索引保留已公开的本机项目绝对路径以便复现，不称其为全面隐私审计。源对话只保存在本地私有归档，未纳入 Git publication。

## 下一步

READY_FOR_INDEPENDENT_REVIEW 是审阅就绪，不是系统完成。下一项只应针对已见差异做 domain/heuristic 与已见 native 成功路径的一致性诊断及消融；在这之前，不扩充搜索预算、不重跑刷绿、不将 bounded no-solution 外推为整个世界不可达。M5 后本轮停止，等待独立审阅决定是否继续。
