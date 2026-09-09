# Self-Evaluation v0：首轮 scorecard

运行对象：RoomDemo C++ reference batch；32 personalities × 8 world seeds × 256 decision points = 65,536 trajectory rows / 256 runs。

结果 JSON：`outputs/self_evaluation_v0/self_evaluation_scorecard_v0.json`（本地生成物；原始 batch 保存在同目录）。

## Score vector

| 维度 | v0 score | 读法 |
|---|---:|---|
| WorldValidity | 1.0000 | 轨迹解析完整，accepted 字段合法 |
| InformationIntegrity | 未评分 | 没有隐藏信息 intervention 标签 |
| CausalResponsiveness | 0.9301 | 事件后动作变化诊断，不是因果估计 |
| Persistence / Commitment | 0.9795 | commitment 连续性诊断 |
| Recovery | 0.0000 | 当前 batch 的 interruption 后五步恢复指标没有命中；需要检查 demo 语义/窗口，不应直接优化分数 |
| Adaptivity | 0.9301 | 与事件后动作变化同源的诊断 |
| CharacterDifferentiation | 0.0111 | personality chosen-action 分布的 pairwise JS divergence，差异不等于自然性 |
| BehavioralDiversity | 0.0566 | 每 run unique actions / decision points |
| Believability | 未评分 | 尚无盲 judge 或人类 pairwise |
| Efficiency | 0 LLM calls | token/latency/GPU telemetry 尚未接入 |

基础检查：65,536 rows、256 runs、8 seeds，全部 accepted 值可解析；概率列最大和误差约 `3.0e-6`，需要在后续 evaluator 中决定是否改为 tolerance-aware warning。

## 当前结论

这份 scorecard 证明了 evaluator 能从现有合成轨迹稳定产出多维、可审计的开发指标；它没有证明 NPC 自然、没有证明心理机制、没有证明 Theory-S，也没有提供 paired causal intervention 证据。

特别需要修正/复核的开发信号是 Recovery=0：这更像当前 interruption 语义与五步窗口的接口问题，而不是“系统恢复能力为零”的科学结论。下一步应先冻结 evaluator 与指标定义，再增加同初态 paired intervention scenarios；不要先调参数追分。
