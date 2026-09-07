# Mechanism Sanity v1.2：trajectory sanity

本轮只验证受控轨迹中的 `X_t → U → S_{t+1} → π_t` 接口，不是正式 NLL、Experiment B、心理学验证或 persistent-S 预测实验。它使用固定 canonical scene、固定 `A^O`、固定 P 和当前 candidate mechanism；不读取 `A*`，不修改 Terra strict-v2。

## 四条受控轨迹

| trajectory | X 输入 | 预期状态变化 | 行为检查 |
|---|---|---|---|
| `effort_build_up_recovery` | 先连续高 `effort_load`，再连续 `recovery_cue` | fatigue 先累积再回落 | build 阶段检查 stimulation 下降；recovery 阶段检查 posture mass 如何随当前 coupling 回归，并记录 cross-effect |
| `positive_progress` | 高 `positive_conduciveness` + `social_opportunity`（避免把 goal relevance 偷渡成 tension） | engagement 上升 | social participation 质量上升；所有其他 S 字段也逐步报告 |
| `obstruction_build_up_decay` | 先连续 `negative_conduciveness`，再移除事件 | tension 先累积再衰减 | conflict 质量与 fatigue cross-effect 同时报告，不把结果归因给单一字段 |
| `rest_recovery` | 高 `recovery_cue`、低 effort/negative | fatigue/tension 回落 | recovery/posture 质量上升（若存在） |

每一步都保存 `X_t`、S 的全部字段（`S_t`、`S_{t+1}`）、完整 `π_t`、semantic-family mass、top action、逐阶段 relaxation、残留衰减、cross-effect 和检查结果。这里的方向是当前工程假设，不是外部行为真值。`4/4` 只有在代码实际列出的全部检查通过时才成立；未通过或可疑 coupling 不会被隐藏在总分里。

## 结果边界

本轮若通过，只能说明状态更新接口有可见的一阶 relaxation、build-up→recovery/decay 和行为传导。它不证明 X 的语义正确、不证明字段是心理真实状态，也不证明任何数据集适合 persistent-S identification。特别要检查 residual persistence/half-life、overshoot 和可疑 cross-effect；下一步若进入真实轨迹，必须先独立审核 `ΔO → X`，再冻结输入、时间尺度和对照。

运行：

```text
py -m unittest discover -s 02_实验/Mechanism_Sanity_v1_2 -p "test_*.py" -v
py 02_实验/Mechanism_Sanity_v1_2/run_trajectory_sanity_v1_2.py
```
