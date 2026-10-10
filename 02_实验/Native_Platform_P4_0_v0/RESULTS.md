# P4-0 Results

状态：**READY_FOR_INDEPENDENT_REVIEW**，有限开发结果已完成；不标记 CLOSED。16/16 native-server 场景 `COMPLETE`；8 个 author-off/on 配对审计与精确场景 query-only DB readback 均 PASS。父级独立复核清单见 [verification audit](runs/p4-audit-20261010T083131Z-0e8e3e.json)。本轮后停止，不进入 P4-1。

## 配对结果

| 场景 | Author OFF | Author ON | 观察 |
|---|---|---|---|
| `open` | 2/2 SATISFIED，B 于模拟分钟 7 拒绝 | 2/2 SATISFIED，B 于分钟 7 拒绝 | 两臂都完成唯一 note response；开门机会未使用。 |
| `blocked-return` | 2/2 VIOLATED，无 response | 2/2 SATISFIED，B 于分钟 14 拒绝 | ON 于分钟 4 结算开门；玩家归还后出现实际互动。拒绝仍满足 response 约束。 |
| `blocked-held` | 2/2 VIOLATED，无 response | 2/2 VIOLATED，无 response | ON 虽于分钟 4 开门，玩家仍持有 courier supply；没有 response。 |
| `short-deadline` | 2/2 VIOLATED，无 response | 2/2 VIOLATED，无 response | 截止分钟 6；ON 于分钟 4 开门，但截止前无 response。 |

共观察到 6 个实际 `SOCIAL_RESPONSE`，全部由原生 Ensemble 选择 `writeLoveNoteReject`；没有观察到 accept。`SATISFIED` 只表示封存账本内有且仅有一次 A courier 发起、B resident 原生结算的真实 note response，拒绝也计为 interaction。这个有限 author opportunity 在 `blocked-return` 配对中伴随较晚的真实互动；不能外推成普遍效果或成功率估计。held 与短时限负例保留。

## 失败机制与复用边界

失败类型不是同一种：author-off 的封门场景缺少合法 east 路线；`blocked-held` 中 courier supply 持续被玩家持有，NPC 的局部观察也没有该物品，故恢复路径未出现；`short-deadline` 的有限窗口结束前没有 response。账本/轨迹没有显示 GTPyhop 或原生 Ensemble intrinsic failure；不应把这些负例归因成 planner budget。`blocked-return` 的 author-on 成功发生在路由开放、玩家按固定 schedule 归还后，实际 A/B 行为与互动仍由各自 native callback 决定，没有脚本化会合。

组件归属：上游 Ensemble 负责原生 volition 与 response action 选择；既有 GTPyhop 负责有限 delivery/patrol 规划。项目新增 glue 负责场景/profile 到原生角色的映射、手动 server clock、固定 one-shot passage rule、settlement receipt、append-only ledger 与审计封口。它们不是新规划算法或完整社交世界。

本地回归记录：P3 tests 53/53、旧 bridge 9/9、P4 bridge 6/6、TypedIR 30/30、上游 Ensemble 45/45、wrapper 28/28；旧 native A/B/C0/C1 九个回归案例及独立 DB audit 见 [`legacy_regression_audit.json`](legacy_regression_audit.json) / [regression evidence manifest](regression_evidence_manifest.json)，runner 输出见 [`ensemble-regression-20261010.json`](runs/ensemble-regression-20261010.json)。旧 A/B 四例是本轮选取的回归子集，不冒充原阶段全部七例。

`blocked-return` ON 的可读机制链：t1 玩家取走同一物品 → t2 A 的取物被原生世界拒绝 → t4 作者开通路线 → t6 玩家归还时 A 不在场、没有立刻恢复 → t8 A 重新观察到物品 → t9 取物、t11 移动、t13 实际交付 → t14 A 在当地看到 B 后提出 note，B 在自己的 callback 拒绝并结算。同一 seed 的 OFF 臂保留真实拒绝与归还历史，但路线未开放，没有发生互动。逐事件字段见 [trajectory excerpt](trajectory_excerpt.json)，完整证据由下述压缩索引定位。

READY_FOR_INDEPENDENT_REVIEW 后的研究检查点是读取这些真实 trajectories，挑选一个值得比较的困难维度；这不是自动开工或进入 P4-1 的授权。

时钟是服务端 simulated-minute，每步推进 1 分钟，不是墙钟或连续物理模拟。两 seed 是配对开发复跑标签，不是随机抽样；没有预设 NPC 会合/response。Monitor 依据 sealed native ledger/receipt 与独立 DB，不将 proposal 当 witness。

## 配对 audit

- `open`: seed 20261010 [audit b5e262](runs/p4-audit-20261010T082545Z-b5e262.json)，seed 20261011 [audit eda56e](runs/p4-audit-20261010T082803Z-eda56e.json)；[初次联合基线 audit](runs/p4-audit-20261010T082803Z-8b157a.json)。
- `blocked-return`: [seed 20261010](runs/p4-audit-20261010T082803Z-458260.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-7abded.json)。
- `blocked-held`: [seed 20261010](runs/p4-audit-20261010T082803Z-d1c6d6.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-0d93d1.json)。
- `short-deadline`: [seed 20261010](runs/p4-audit-20261010T082803Z-0fdcf7.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-f7a616.json)。

逐例 raw run/DB 共 34 份的无损压缩副本、原始与压缩 SHA-256、文件名对应关系见[证据清单](evidence_manifest.json)；精简可读事件摘录见 [`trajectory_excerpt.json`](trajectory_excerpt.json)。清单记录原始共 75,584,138 bytes，压缩副本共 2,885,322 bytes；原始单场景 JSON 留存本地，audit JSON 的 inputs 记录精确文件名和 SHA-256。

CI 状态以本提交的 [GitHub Actions](https://github.com/2003SINGER/character-dynamics-lab/actions?query=branch%3Awebgpt-sync) 为准：`native-platform-p3` 与总体 `runtime-regression` 分别核对，不把专项成功写成全仓成功；本机测试与本组 server audits 不能代替 exact-head CI。P4-0 复用 pinned Ensemble 原生人物响应机制；固定 author opportunity 是有限项目规则，不声称复现 DODM/SAS/RL，也不主张新算法。原始 `loversAndRivals` cast 中 offstage `rival` 仍可能影响 Ensemble trigger，但不是第三个物理 NPC；不表示全量 social state 镜像、完整 DM 或独立 cognition。没有玩家体验或心理效度证据。
