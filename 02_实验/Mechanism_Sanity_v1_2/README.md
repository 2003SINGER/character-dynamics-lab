# Mechanism Sanity v1.2：trajectory sanity

本轮只验证受控轨迹中的 `X_t → U → S_{t+1} → π_t` 接口，不是正式 NLL、Experiment B、心理学验证或 persistent-S 预测实验。它使用固定 canonical scene、固定 `A^O`、固定 P 和当前 candidate mechanism；不读取 `A*`，不修改 Terra strict-v2。

## 四条受控轨迹

| trajectory | X 输入 | 预期状态变化 | 行为检查 |
|---|---|---|---|
| `continuous_effort` | 连续高 `effort_load` | fatigue 累积 | stimulation/conflict 质量下降，posture/recovery 质量上升（若存在） |
| `positive_progress` | 高 `goal_relevance` + `positive_conduciveness` | engagement 上升 | stimulation/social participation 质量上升 |
| `repeated_obstruction` | 高 `goal_relevance` + `negative_conduciveness` | tension 累积 | conflict 质量上升；不把它解释成普遍“更坏” |
| `rest_recovery` | 高 `recovery_cue`、低 effort/negative | fatigue/tension 回落 | recovery/posture 质量上升（若存在） |

每一步都保存 `X_t`、`S_t`、`S_{t+1}`、完整 `π_t`、semantic-family mass、top action 和检查结果。这里的方向是当前工程假设，不是外部行为真值。

## 结果边界

本轮若通过，只能说明状态更新接口有可见的惯性、累积/恢复和行为传导。它不证明 X 的语义正确、不证明字段是心理真实状态，也不证明任何数据集适合 persistent-S identification。下一步若进入真实轨迹，必须先独立审核 `ΔO → X`，再冻结输入、时间尺度和对照。

运行：

```text
py -m unittest discover -s 02_实验/Mechanism_Sanity_v1_2 -p "test_*.py" -v
py 02_实验/Mechanism_Sanity_v1_2/run_trajectory_sanity_v1_2.py
```
