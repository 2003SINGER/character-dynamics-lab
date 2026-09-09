# Self-Play / Self-Evaluation v0

## 运行对象

现阶段直接使用 `Demo codex-generated` 的规则化 C++ reference batch：32 个合成人格 × 8 个世界 seed × 256 个 decision points，共 65,536 条 trajectory rows。该 batch 是系统开发材料，不是外部行为验证。

## 固定输入与输出

- 输入：`personalities.csv`、`trajectories.csv`、`runs.csv`、`metadata.txt`；可选的 `--paired paired_phone_intervention.csv`。
- 评分器：`tools/self_evaluation_v0.py`。
- 输出：`outputs/self_evaluation_v0/` 下的 JSON scorecard 与原始 batch run。
- 评分必须保留维度、分母、未评分原因和 provenance；不把多个维度压成单一自然度分数。

## 当前 v0 维度

| 维度 | v0 做法 | 边界 |
|---|---|---|
| WorldValidity | accepted 字段合法性与 CSV 完整性 | 仍需更细的 primitive/world invariant 计数 |
| InformationIntegrity | paired hidden/visible phone intervention | 只验证信息边界与观测中介，不是心理学有效性 |
| ObservationMediation | paired 后观察差异率 | 观测差异不等于行为因果 |
| StatePersistence / BehavioralPersistence | paired 状态距离 / 动作分歧 | 当前 phone fixture 可能只产生信息差异 |
| CausalResponsiveness | 事件后动作变化诊断 | 不是 paired intervention 的因果估计 |
| Persistence / Commitment | commitment task 连续性 | 不是心理状态验证 |
| Recovery | interruption 后五步内恢复承诺 | 依赖当前 demo 的 commitment 语义 |
| Adaptivity | 事件后动作变化诊断 | 需与不变事件对照 |
| CharacterDifferentiation | 人格间 chosen-action 分布 JS divergence | 差异不等于自然性 |
| BehavioralDiversity | 每 run unique actions / steps | 不是质量指标 |
| Believability | 未评分 | 后续盲 judge / human pairwise |
| Efficiency | 当前 batch 记录 0 LLM calls | 尚未有 token/latency/GPU telemetry |

## 结论边界

v0 只回答“当前规则引擎能否稳定产生可审计轨迹，以及哪些维度明显坏掉”。它不能宣布 NPC 自然、不能证明 Theory-S、不能替代外部评测。

paired harness 运行入口为 `character_dynamics_reference --paired-phone <csv>`；它固定人格、初态与 action RNG，step 1 后移除 phone，hidden 分支保留旧 O 事实，visible 分支立即标 stale。评分器用 `--paired` 读取该 CSV。该 fixture 仍是机制诊断，优化 run 与 frozen evaluation run 必须分开。

Deadline state-dynamics fixture 运行入口为 `--paired-deadline <csv>`。它使用
绝对 `deadline_at_total_minutes` 与 `clock.total_minutes`，并以 shared-action
replay 对齐三分支的时间和外部事件；CSV 同时记录 deadline discovery、derived
remaining/urgency、appraisal pressure、state pressure 与 policy distance。
