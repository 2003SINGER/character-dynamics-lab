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

失败类型不是同一种：author-off 的封门场景缺少合法 east 路线；`blocked-held` 中 courier supply 持续被玩家持有、A 的局部观察没有该物品，也没有自己的 delivery drop receipt，因而不触发 note request；`short-deadline` 在 t6 截止，A 当时已离开 pickup，只有 west move intent、还没有 settlement。后者是当前有限 horizon/callback 粒度下未及时完成，不是物理不可达证明。账本/轨迹没有显示 GTPyhop 或原生 Ensemble intrinsic failure，也没有证据可把失败归因成 planner budget。`blocked-return` 的 author-on response 发生在路线开放、玩家按固定 schedule 归还后；自然行动时序形成了相遇，未脚本 rendezvous。

组件归属：`plan_next` 的有限 delivery HTN 使用 GTPyhop；`plan_patrol` 则是项目自己的稳定排序可见出口规则，不是 GTPyhop（[planning.py](../../tools/native_platform_v0/p3/planning.py#L55)、[patrol adapter](../../tools/native_platform_v0/p3/planning.py#L196)）。项目胶水另负责 profile/场景映射、手动 server clock、固定 one-shot passage、receipt 与 append-only ledger。互动分两段：A 自己的 drop 与本地可见 B 触发 A→B note request、note 实物送入 B 库存；随后 B callback 持有该 note，原生接受门按匹配的 Love→Hero `(category,type,intentType)` volition 判断（权重 `<0` 拒绝、`>=0` 接受、无匹配默认接受），再由 B 结算同一 note。runner 从最高权重并列 native 候选中选择受支持的 `WRITELOVENOTE` lineage；正式轨迹的 `writeLoveNoteReject` 与 `kissFail` 均为 20，种子选择了前者。这不是 B 自主规划社交目标或完整 BDI，也不是上游唯一指定拒绝动作。拒绝仍给 Hero→Love closeness 加 10 并写入 `romantic-failure`，不表示关系恶化或无副作用。胶水见 [p4_social.py](../../tools/native_platform_v0/p3/p4_social.py#L221)，候选/投影见 [runner.mjs](../../tools/native_platform_v0/ensemble/runner.mjs#L166)、[runner selection](../../tools/native_platform_v0/ensemble/runner.mjs#L173)、[bridge regression](../../tools/native_platform_v0/bridge/test_p4_social.py#L28)。

本地回归记录：P3 tests 53/53、旧 bridge 9/9、P4 bridge 6/6、TypedIR 30/30、上游 Ensemble 45/45、wrapper 28/28；旧 native A/B/C0/C1 九个回归案例及独立 DB audit 见 [`legacy_regression_audit.json`](legacy_regression_audit.json) / [regression evidence manifest](regression_evidence_manifest.json)，runner 输出见 [`ensemble-regression-20261010.json`](runs/ensemble-regression-20261010.json)。旧 A/B 四例是本轮选取的回归子集，不冒充原阶段全部七例。

`blocked-return` 的事件顺序按 server callbacks 与 player commands 记录；意图与 W 结算分开：

| 时间 | Author OFF | Author ON | 游戏/因果语义 |
|---|---|---|---|
| t1 | A delivery `ACTIVE`，`NO_PLAN`、无 intent；之后玩家成功 get supply | 相同；玩家 get 发生在 NPC callbacks 后 | 不是 NPC get 被 W 拒绝。seed10：`/runs/1/decision_rows/0`、`/runs/1/world_interventions/0`。 |
| t2 | A 转 patrol，`SUSPENDED_LOCAL_ITEM_UNAVAILABLE`，patrol `WAIT`、无 intent | 同样尚无 courier get dispatch | OFF `/runs/0/t2_courier_check`、ON `/runs/1/t2_courier_check`：无 get rejection 或 settlement。 |
| t4–t5 | 门仍关闭，无 east route | `OPEN_PASSAGE` 是唯一 author W 改动；t4 A east、B get 只有 intent，t5 才结算 | 不是 author 直接命令 NPC：`/runs/1/world_interventions/1`、`/runs/1/decision_rows/4`、`/runs/1/decision_rows/5`、`/runs/1/all_primitive_settlements/0`、`/runs/1/all_primitive_settlements/1`。 |
| t6–t9 | 玩家归还后 A 已重见 item，但封闭路线下仍 `NO_PLAN` | t6 玩家归还时 A 在外；t7 回 pickup、t8 看见 item 并形成 get intent、t9 才结算 | `/runs/1/world_interventions/2`、`/runs/1/all_primitive_settlements/2`、`/runs/1/decision_rows/8`、`/runs/1/all_primitive_settlements/4`。OFF 相应 t6 状态见 `/runs/0/decision_rows/6`。 |
| t9–t13 | 无 note response | B t9 完成自己的 delivery；t10 west intent/t11 settle、t12 east intent/t13 settle，两 NPC 在 destination 自然相遇 | B delivery drop `/runs/1/all_primitive_settlements/5`；patrol 选择 `/runs/1/decision_rows/11`、`/runs/1/decision_rows/13`；settlement `/runs/1/all_primitive_settlements/7`、`/runs/1/all_primitive_settlements/8`、`/runs/1/all_primitive_settlements/9`。非脚本 rendezvous。 |
| t14 | 无互动 | A 请求实际 note；B 持有同一 note 时在自己的 callback 响应并 commit 拒绝 | `/runs/1/social_events/0` 为 request，`/runs/1/social_events/1` 为 response，`/runs/1/social_events/2` 为 native commit。不是 accept，也不是 B 独立生成社交目标。 |

父级只读因果审计 [causal_audit.json](causal_audit.json) 由 12 份已存 raw run 确定性抽取、没有新 run；文件 SHA-256：`0b39362220da699a723e42d5d47ddba77a5914637cd916cb2dc22b6de13a0f68`。正文中的 RFC 6901 pointers 指向该文件，并链接到解压后 run JSON 对应记录；`/runs/0`、`/runs/1` 是 seed10 return OFF/ON，`/runs/2`、`/runs/3` 是 seed11，`/runs/4..7` 为 held、`/runs/8..11` 为 short；`/assertions` 含通过断言。Raw/archive SHA-256 与对应关系见[证据 manifest](evidence_manifest.json)，事件摘录见 [trajectory excerpt](trajectory_excerpt.json)。

本轮因果诊断已完成：现有配对只比较固定 minute-4 开门机会与关闭门，没有改变开门时机，也没有测量干预成本，因而没有证据判断“更早开门更优”或存在可识别的时机权衡。后续只有在另行选出可区分的条件/协议后，才考虑用成熟方法比较；不重跑“4 分钟开门”命题，不自动进入 P4-1 或造新算法。

时钟是服务端 simulated-minute，每步推进 1 分钟，不是墙钟或连续物理模拟。两 seed 是配对开发复跑标签，不是随机抽样；没有预设 NPC 会合/response。Monitor 依据 sealed native ledger/receipt 与独立 DB，不将 proposal 当 witness。观察中的出口 `traversable` 是对当前可见 exit 的 actor-specific `traverse` 权限检查结果（[agency.py](../../tools/native_platform_v0/p3/agency.py#L63)），不是 NPC 看到了“锁门”标识或理解了障碍语义；本地图没有该可见标识。解释仅是本地通行 affordance 假设：可见阻挡或明示规则可直接知道，隐锁需要另一种观察契约，本轮不强制失败探测。每分钟 callback 与细日志是实现观察粒度，不证明高层活动必须频繁决策或对应现实行走效率。

## 配对 audit

- `open`: seed 20261010 [audit b5e262](runs/p4-audit-20261010T082545Z-b5e262.json)，seed 20261011 [audit eda56e](runs/p4-audit-20261010T082803Z-eda56e.json)；[初次联合基线 audit](runs/p4-audit-20261010T082803Z-8b157a.json)。
- `blocked-return`: [seed 20261010](runs/p4-audit-20261010T082803Z-458260.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-7abded.json)。
- `blocked-held`: [seed 20261010](runs/p4-audit-20261010T082803Z-d1c6d6.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-0d93d1.json)。
- `short-deadline`: [seed 20261010](runs/p4-audit-20261010T082803Z-0fdcf7.json)，[seed 20261011](runs/p4-audit-20261010T082803Z-f7a616.json)。

逐例 raw run/DB 共 34 份的无损压缩副本、原始与压缩 SHA-256、文件名对应关系见[证据清单](evidence_manifest.json)；精简可读事件摘录见 [`trajectory_excerpt.json`](trajectory_excerpt.json)。清单记录原始共 75,584,138 bytes，压缩副本共 2,885,322 bytes；原始单场景 JSON 留存本地，audit JSON 的 inputs 记录精确文件名和 SHA-256。

CI 状态以本提交的 [GitHub Actions](https://github.com/2003SINGER/character-dynamics-lab/actions?query=branch%3Awebgpt-sync) 为准：`native-platform-p3` 与总体 `runtime-regression` 分别核对，不把专项成功写成全仓成功；本机测试与本组 server audits 不能代替 exact-head CI。P4-0 复用 pinned Ensemble 原生人物响应机制；固定 author opportunity 是有限项目规则，不声称复现 DODM/SAS/RL，也不主张新算法。原始 `loversAndRivals` cast 中 offstage `rival` 仍可能影响 Ensemble trigger，但不是第三个物理 NPC；不表示全量 social state 镜像、完整 DM 或独立 cognition。没有玩家体验或心理效度证据。
