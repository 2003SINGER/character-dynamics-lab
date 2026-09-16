# ResearchDynamicsV1 protocol（候选，未冻结）

这是一个最小、可干预、可审计的研究动力学候选，不是心理学结论，也不是对旧 Theory-S 的改名。所有运行必须写出 `dynamics_model_id=ResearchDynamicsV1`、seed、初始状态与 intervention。

## 统一接口

```text
X_t = A(O_t, ΔO_t, outcome_t, goal_context)
S_{t+1} = F(S_t, X_t, Δt, running_action, P)
π_t = G(O_t, S_t, P, A^O_t)
```

`W` 只能由 world owner 读取/结算；`O` 是带 stale/unknown 的局部投影；`A^O` 先由 O 生成；`A*` 只能在评估边界揭示。禁止读取未来 outcome、source candidate list 或 hidden W。

## 最小状态字段

| 字段 | 操作性语义 | 累积/恢复 | 可观测证据 |
|---|---|---|---|
| `fatigue` | 当前持续负荷与恢复缺口 | effort/屏幕负荷上升；rest/sleep 衰减 | action duration、rest/sleep outcome |
| `task_pressure` | 未完成目标的紧迫度 | deadline 接近、阻塞上升；progress/completion 缓解 | task facts、deadline delta、completion |
| `boredom` | 刺激不足的短时状态 | 单调/低刺激上升；新颖/社会刺激缓解 | visible event/action family |
| `satisfaction` | 最近结果的短时正负反馈 | progress/reward 上升；obstruction/成本下降 | typed outcome 与 appraisal delta |

所有字段均 `[0,1]`、显式初始化、按 `Δt` 更新；阈值是 candidate engineering controls，不能直接解释为临床或人格界线。`P` 只调更新速率/偏好权重，不改变 W 合法性。

## 受控证据包

必须至少通过：零输入衰减、正确字段 intervention、字段置换、stale-O、未来信息泄漏与 deterministic rerun。每个 artifact 都保留 raw trace、compact summary、model id 和 config hash。未完成这些 gate 前，不启动 LIGHT 全量或正式 Paper-0 test。
