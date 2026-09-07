# Mechanism Sanity v1.1（development engineering slice）

本切片保留 v1 的目标，但修正了候选编译、持有关系、逐字段干预和结论边界。它只使用 LIGHT review projection 的 canonical `SceneSnapshot`，不触碰 Terra strict-v2 的 protocol/validator/shards/annotations/status/results，不启动 Run1–4、正式 test、Experiment B、新数据采集或新模型调用，也不新增 Theory-S 字段。

## 1. 证据边界

`fatigue`、`engagement`、`tension` 在本轮是 candidate mechanism / engineering hypotheses，不是已工程冻结的 Theory-S v1。文献只约束可搬的形式（有界连续量、一阶松弛/恢复、trait 调 ramp/decay 或 salience 的可能接口）；本项目选择的字段语义、系数和阈值均不是文献估计。参数是 hand-set engineering parameters，尚未用行为真值拟合。LIGHT 的 `scene_appraisal` 大部分输入是 0/unknown，因此本轮只检查固定 `A^O` 下的 `S→π`；不宣称 `ΔO→X→U→S` 已验证，X→U→S 留给 v1.2 / Gate 1。

本轮结果是可复现的 plumbing sanity，不是心理学正确性、预测收益、persistent-S 识别或 formal experiment 证据。

## 2. Canonical SceneSnapshot → ontology → generated `A^O`

`run_sanity_v1.py` 从 LIGHT 的 `room_objects`、`room_agents`、`actor`、`carrying`、`wearing`、`wielding`、`source_O` 与 `field_provenance` 构造 snapshot。对象和代理的 `type`、`description`、`facts`、source provenance 原样保留；持有物不再被清空，并成为带有 `possession_relation` 的 canonical entities。

生成器 `candidate_generation_v1.py` 只读 snapshot 的实体、可见性、显式 facts 和 possessions。它绝不读取 `source_action_A_star`、`candidate_set_factual` 或 `source_candidates`。生成结束后，`support_diagnostic` 才把 source `available_actions` 与生成结果比较；miss 永远不注入 gold action，原因保留为：`object extraction`、`ontology`、`insufficient O`、`entity binding`、`hidden/unknown fact` 或 `other`。

| family / action | 生成条件（只写可审计事实） | 未声称的条件 |
|---|---|---|
| `inspect` | 可见 room object | inspection success |
| `take/get` | `facts.portable == true` | ownership、成功；缺 portable 不生成 |
| `drop` | canonical possession 中确有 actor holds | destination、成功 |
| `give` | possession + visible agent | ownership、consent、成功 |
| `wear/wield` | possession + `wearable/wieldable == true` | fit、appropriateness、成功 |
| `talk` | visible agent | language、conversation success |
| `hug/hit` | visible agent 的 generic contact affordance | 合适性、permission、成功；不代表应该做 |
| `sit` | type/description/label 有 chair/stool/seat 证据 | permission、成功 |
| `use` | `usable == true` 或小型显式 type/description ontology（如 lantern/horn/door） | use success、permission |

重复实体按 canonical 输入顺序保留，以 entity id 绑定；相同 label 不合并。缺 id 时按 kind 与稳定输入索引补 id，重复 id 加稳定后缀。aliases 只用于后验 target binding，不用于凭空生成对象。

## 3. Development fixtures

fixture 只按 canonical scene 的对象、代理、持有关系和生成候选数选择，不按 `A*` 覆盖率选取。当前 5 个 LIGHT fixtures 的 generated `A^O` 大小为 5–10；均包含 inspect、social communication、social contact、physical conflict，另有 carrying、seat 或 use 的场景。fixture 原始 snapshot 与 generated records 在 [`fixtures.jsonl`](fixtures.jsonl)，每条候选包含 `action_id`、human-readable action、targets、semantic family、rule id、required facts、supporting evidence/provenance 和 unknown preconditions。

## 4. S intervention

每个 fixture 固定 Scene/O/P/generated `A^O`，每次只把一个字段从 0.15 改到 0.85，其他 S 字段保持 baseline `(fatigue=.35, engagement=.55, tension=.25)`。每格报告 full π、Δprob、rank/top-action、semantic-family mass、TV、预先写定的 expected direction、support invariant、direction check 与 PASS/FAIL/NOT_TESTABLE。`joint_extreme_stress_test` 单独保留，不能拿来归因单个字段。

当前重跑结果（详见 [`intervention_results.json`](intervention_results.json)）：

| 单字段 | TV 范围（5 fixtures） | direction / support | rank/top-action |
|---|---:|---|---|
| fatigue | 0.021–0.036 | 5/5 PASS；support 不变 | 无 top-action flip；是较弱但可见 coupling |
| engagement | 0.043–0.060 | 5/5 PASS；support 不变 | 5/5 top-action flip |
| tension | 0.066–0.095 | 5/5 PASS；support 不变 | 5/5 top-action flip |

TV 不是唯一成功标准：本轮同时要求方向检查和非微小变化（`TV > .005`）；如果只有小抖动，必须记为 coupling 偏弱，不能仅以低 TV 阈值宣布成功。这里的结果只说明当前手工 operator 存在可见 S→π 耦合。

## 5. P/S orthogonality

固定 S 改 `recovery_preference`、`stimulation_seeking`、`threat_sensitivity`，固定 P 改每个 S 字段。两类干预都重新使用同一个 generated `A^O`，并检查 action ids、required facts、对象存在/可见性和 legality 不变；结果也记录每个 `P×S` 的 difference-in-differences interaction。stimulation/threat 在有相应 family 的 fixture 上产生稳定偏好变化；recovery 只有 posture family 存在时才可测试。此处可区分的是“P 调 operator、S 调 transient preference”的工程接口，不是 personality model。

## 6. LIGHT 当前边界

LIGHT 当前的 projection、可验证字段和 ontology 还不足以支持 persistent-S 识别，最终适用性未决。原因不是一句“LIGHT 不适合”：possessions、ontology、trajectory history/event consequence 仍未完整审计，且 source `available_actions` 不等于 generated `A^O`。因此本轮只能做 interface / support / controlled intervention sanity；不把 source action 当作 A^O 或心理标签。

## 7. 运行与验收

在仓库根目录执行：

```text
py -m unittest discover -s 02_实验/Mechanism_Sanity_v1 -p "test_*.py" -v
py 02_实验/Mechanism_Sanity_v1/run_sanity_v1.py
```

测试覆盖 generator 不读 A*/source candidates、possessions、P/S 不改 `A^O`、单字段 semantic-family 方向、irrelevant S 不无差别改变所有动作、provenance/rule id、缺事实不生成、support miss 不 gold injection、duplicate/alias deterministic。输出仅覆盖本目录的 fixtures/results；不覆盖 Terra strict-v2 或 Run1–4。

留给 v1.2 / Gate 1 的问题是：如何从有充分时序后果的 `ΔO` 构造并验证 `X→U→S`，以及在独立行为真值与强 baseline 下检验 persistent-S 是否带来可泛化预测增益。
