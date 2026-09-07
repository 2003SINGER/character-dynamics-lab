# Paper-0 问题卡（冻结锚点，2026-09-05）

## 研究问题

在局部可观测、可回放的单角色 Forward 环境中，持久状态 `S` 是否保留历史后果并近似充分地预测下一动作；相对等容量朴素状态、强摘要和置换状态，它是否具有可测的必要性？`P` 固定，`D` 由当前输入导出。

## 变量与数据边界

- `W`：权威世界；角色不能直接读取或写入。
- `O`：角色在当前时刻拥有的局部观察，允许 stale/unknown。
- `H^obs`：截至预测时刻的完整、合法观察历史；不得包含未来信息。
- `X`：由 `ΔO`、旧 `S`、`P` 产生的结构化 appraisal。
- `S`：跨决策点保存、按字段更新的角色状态。
- `A^O`：角色依据 O 知道/能设想的有限候选动作；`A^W` 由世界最终校验。
- `π(A)`：在真实下一动作揭晓前输出的候选分布。
- 独立真值 `A*`：来自外部人类轨迹或明确独立的 replay；E0 自生成动作不构成 `A*`。

## 三条可证伪主张

1. **Information boundary**：在 hidden-W paired fixture 中，`W_hidden` 不应改变行为相关 `O/X/S/A^O/π`；在 visible-W fixture 中，合法观察变化可以改变它们。E0 只证明 instrumentation validity。
2. **Approximate sufficiency**：在同一信息权限与模型条件下，`p(A | S,O,P)` 与 `p(A | H^obs,O,P)` 的 held-out NLL 差异落入预注册非劣效/等价界 `ε`，或明确显示 residual gain。
3. **Necessity**：保持容量与支持集不变，`NLL(S)` 相对 `NLL(permute(S))` 显著更低；paired ΔNLL 按 session/user 聚类，不能把动作当独立样本。

## 首轮比较与报告

`persona-only`、raw history、结构化 history、strong summary、`no-S`、rank-matched 1D `Activity-S`/`ActionSupport-S`/`Theory-S`、permuted-S；统一 finite candidate set 与 O 权限。T14/T20 的 1D 条件统一使用同一 conditional linear probe，不为 theory-S 手写专用 action head；正式训练前冻结协议见 [rank-matched probe](../02_实验/T14_T20_rank_matched_probe_v0.md)。主指标为 held-out action NLL（同时报告 Δbits、按候选集分层的原始 NLL 与预注册分母归一化值），辅以 ranking、support 命中和成本/延迟。报告 session/user split，禁止未来泄漏、身份泄漏与叙事 framing 泄漏。

## 失败条件与 no-go

候选集无法冻结、观察无法按角色重建、split 存在未来泄漏、或外部 `A*` 不独立，则停止正式 baseline。首轮不做 inverse、多角色/ToM、P 漂移、Scene Manager、Q01 高级曲线、心理机制成立或广泛新颖性宣称。

## 路线顺序

E0 回归验收 → T0d OPeRA 30–50 session 准入审计 → 选择 OPeRA/LIGHT pilot → 最小 X→S slice → state/history/summary/naive-S/theory-S/permuted-S 表。
