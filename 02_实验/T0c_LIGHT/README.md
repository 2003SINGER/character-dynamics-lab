# LIGHT T0c｜准入审计与 Replay slice

原始资产位于被 Git 忽略的 `outputs/external_assets_2026-09-06/LIGHT/`，与 ClubFloyd 和 runtime 分离。来源为 ParlAI LIGHT 的 `light-dialog-processed-small7.pkl`，文件 SHA-256 记录在 manifest 中。

## 已完成

- 审计前 50 个 episode：41 个含至少一个非空 physical action，共 140 个 physical action turns；606 个 turn 提供 `available_actions`。
- 导出 41 条 eligible trajectory / 140 steps，已通过 ReplayRecord v0 validator。
- 全量无损抽取已完成：7,258 条 trajectory / 25,001 physical-action steps；统计见 [full extraction QA](full_extraction_report_v0.md)，全量 JSONL 仅保存在 ignored external-assets。
- 每步只把 processed record 的 actor-specific `context` 作为 `source_O`；setting、room objects、room agents 保留在 episode/step source context，不把整个 world graph 复制进 `W` 或 `O`。
- `action`、persona、候选列表和 turn actor 原样保留；dialogue-only turns 不冒充 `A*`。

## 当前准入判断

**受限 dev 资产，不能作为已通过研究准入的真人行为 benchmark。** 数据结构能支持字段映射，但 actor、角色可见信息和环境 world state 的时间对齐仍需人工 semantic audit；当前 `W`、state label、timestamp 保持 unknown。候选列表仅按 source 的 `available_actions` 记录为 observed，不等同于角色实际可知集合 `A^O`。

复现：

```powershell
py -3 02_实验/T0c_LIGHT/audit_slice.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT/light_audit_50.json --limit 50
py -3 02_实验/T0c_LIGHT/export_replay.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT/light_dev_50.replay.json --limit 50
py -3 tools/validate_replay_record.py outputs/external_assets_2026-09-06/LIGHT/light_dev_50.replay.json
py -3 02_实验/T0c_LIGHT/extract_full.py outputs/external_assets_2026-09-06/LIGHT/light_data.pkl outputs/external_assets_2026-09-06/LIGHT
```

全量 QA 已标记两个 source alignment anomaly episode（486、778：actor 不在 source agents，且 A* 在 case-normalized 后不在 candidates）；这两个 episode quarantine，不进入 mechanism loop。候选统计同时报告 exact miss=3、casefold miss=2（24,999/25,001 casefold 命中）。

机制开发视图必须用 `py -3 02_实验/Replay/build_mechanism_dev_view.py <full.replay.jsonl> <mechanism_dev.replay.jsonl>` 生成；脚本会硬排除 `source_episode_context.quarantine == true` 的 trajectory。

## Batch 4–5 dev diagnostic (2026-09-06)

已用 41 条非 quarantine trajectory / 140 steps 跑通 fixed compiled semantics → replay core → candidate scorer → held-out `A*` 链，并生成 semantic-update remove diagnostic（20 条 trajectory、52 对）。结果位于 `outputs/experiments/LIGHT_compiled_semantics_v0/`；该结果仍是 dev diagnostic，不构成 Scene counterfactual、semantic admission 或 Paper-0 结论。

本轮补上的桥接层是 `02_实验/Replay/scene_snapshot_v0.py`：它把 LIGHT 每个 ReplayRecord step 投影为 source-preserving `canonical_scene_snapshot_v0`（setting、objects、agents、actor inventory、actor observation、source candidates、provenance）。当前明确保持 `world_projection_status=deferred`、`candidate_status=observed_source_only_not_A_O`；因此旧 Batch 4–5 scorer 仍只是 smoke，尚未宣称 scene-aware semantics。

C++ 框架侧同步新增 `Demo codex-generated/Inc/scene_snapshot.h` 与 `Src/scene_snapshot.cpp`。它定义不依赖数据集动作枚举的最小快照，并提供 RoomDemo → SceneSnapshot 投影；`CandidateSemantics` 已抽到 `Inc/semantic_types.h`，external scorer 不再从该类型头文件引入 demo `ActionType`。

### Scene-aware v1 paired diagnostic (same 41 trajectories / 140 steps)

`run_compiled_semantics_v0.py --scene-aware` 现在先调用 `compile_light_step()` 生成 canonical `SceneSnapshot`，再将 candidate target 与 snapshot 的 entities、actor observation 和 possessions 做最小绑定，并对不在 scene/不可见/已携带的 target 调整 candidate semantics/bias。结果与 verb-only v0 保存在 `LIGHT_v0_v1_paired_comparison.json`：canonical-snapshot v1 stateful NLL **1.419149**（v0 1.422254），但 v1 no-history NLL **1.419183**；stateful 仅比 no-history 好 **0.000034**，因此当前不能归因于 persistent S，且仍只是 dev diagnostic。

### Transition theory-S diagnostic

`run_transition_theory_s_v0.py` 在同一 140 steps 上执行 `SceneSnapshot(t-1,t) → transition → appraisal X → AppraisalTraceStateV0 → candidate scorer`，并输出 zero-S、theory-S、trajectory-permuted-S 三组 trace。固定 `eta=0.35`、离散 replay boundary `Δt=1`，不消费 RoomDemo Personality；结果与 transition audit 位于 `outputs/experiments/LIGHT_transition_theory_s_v0/`。本轮只作机制 smoke，不调 eta 或 scorer。
