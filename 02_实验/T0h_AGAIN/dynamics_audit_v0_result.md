# AGAIN dynamics development audit v0

状态：**完成；development-only；不进入 formal test**  
执行日期：2026-09-08  
协议：[`dynamics_protocol_v0.md`](dynamics_protocol_v0.md)

## 执行与 provenance

使用冻结的本地 replay、manifest 和 QA 运行：

```powershell
py -3 outputs/again_dynamics_audit_20260908/run_again_dynamics_audit_v0.py
```

原始 replay 保持在 `_local_data/AGAIN/again_dev_20_v4/`；逐步结果、run record、执行脚本和详细 fold artifact 保持在被 Git 忽略的：

`outputs/again_dynamics_audit_20260908/`

已验证：

- replay SHA-256 与冻结 manifest 一致：`bb2707c1fac1a6f8b5c265953ccf49147d7bfda9c6c237a2a29a0fd6aaef870c`
- 20 trajectories / 9,302 steps / 9 games
- future annotation guard、`source_O` / `source_action_A_star` / `state_label` null checks 通过
- trajectory boundary 与 timestamp 顺序检查通过
- participant-held-out：18 folds；game-held-out：9 folds
- 没有训练 `alpha`、`beta`、`b`、`W`，没有修改 Theory-S 或协议

## Frozen comparators

执行了：

- training-part median no-state baseline；
- fixed `phi ∈ {0.0, 0.5, 0.8, 0.95}` 的 AR(1) carry-forward sensitivity；
- per-channel binary-onset event envelope；fixed `tau ∈ {0.5, 1.0, 2.0, 5.0}` seconds 的 first-order relaxation comparator。

事件通道逐一保留 raw provenance，不构造综合 arousal score。详细预注册字段、窗口、容差、fold 和软件 hash 见 `outputs/again_dynamics_audit_20260908/run_record.json`。

## 核心结果

### Persistence

两组 hold-out 的轨迹级结果一致呈现短期 persistence：

| native lag | proxy correlation median |
|---:|---:|
| 0.25 s | 0.9856 |
| 0.50 s | 0.9697 |
| 1.00 s | 0.9411 |
| 2.00 s | 0.8967 |
| 4.00 s | 0.7901 |

AR(1) 只是描述性 comparator；`phi=0.95` 的 held-out MAE median 为 `0.696`，不能解释为 Theory-S state transition 或已估计参数。

### Event-driven relaxation

该 family **不判 stable**：事件支持稀疏且明显依赖 channel/game，lag、decay、recovery 在大量 fold 中为 undefined 或 censored。例如：

- `player_damaged`：participant-held-out 12/18 folds、game-held-out 6/9 folds 有事件；
- `player_shooting`：participant-held-out 10/18 folds、game-held-out 5/9 folds 有事件；
- 其余多数 channel 的 game-held-out 支持仅 1–3/9 folds。

因此目前只能报告：AGAIN dev slice 有可重复的 annotation-proxy persistence；没有足够稳定的 event-to-proxy relaxation 形状可升级为主数据、Theory-S 验证或心理因果结论。

## 停止结论

`AGAIN dynamics audit v0` **完成但不升级**。下一步若继续，只能另写带明确输入语义的开发协议；本轮不训练、不调参、不把 proxy 改名为 `source_O`、fatigue、engagement、tension 或 character state。

