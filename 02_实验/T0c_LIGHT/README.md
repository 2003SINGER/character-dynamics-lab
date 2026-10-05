# LIGHT T0c｜准入审计与 Replay slice

当前解释以[2026-10-06 研究重建审计](../../00_研究设计/研究重建审计_2026-10-06.md)和[LIGHT 任务准入审计](../../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)为准。下面保留原批次记录；H0b/compression 的旧 actor-unit split 有 episode overlap，不作为已证实泛化。新的 episode-disjoint development fit 也只使用环境快照/physical history，不等于完整角色观察。

原始资产位于被 Git 忽略的 `outputs/external_assets_2026-09-06/LIGHT/`，与 ClubFloyd 和 runtime 分离。来源为 ParlAI LIGHT 的 `light-dialog-processed-small7.pkl`，文件 SHA-256 记录在 manifest 中。

## 已完成

- 审计前 50 个 episode：41 个含至少一个非空 physical action，共 140 个 physical action turns；606 个 turn 提供 `available_actions`。
- 导出 41 条 eligible trajectory / 140 steps，已通过 ReplayRecord v0 validator。
- 全量无损抽取已完成：7,258 条 trajectory / 25,001 physical-action steps；统计见 [full extraction QA](full_extraction_report_v0.md)，全量 JSONL 仅保存在 ignored external-assets。
- 每步只把 processed record 的 actor-specific `context` 作为 `source_O`；setting、room objects、room agents 保留在 episode/step source context，不把整个 world graph 复制进 `W` 或 `O`。
- `action`、persona、候选列表和 turn actor 原样保留；dialogue-only turns 不冒充 `A*`。

## 当前准入判断

**受限 dev 资产，不能作为已通过研究准入的真人行为 benchmark。** 数据结构能支持字段映射，但 actor、角色可见信息和环境 world state 的时间对齐仍需人工 semantic audit；当前 `W`、state label、timestamp 保持 unknown。候选列表仅按 source 的 `available_actions` 记录为 observed，不等同于角色实际可知集合 `A^O`。

### Actor-local history eligibility gate v0（2026-09-09）

严格同 trajectory、同 actor、non-quarantine 的 gate 已完成：13,463 targets / 6,869 actor-trajectory units。原 H0 equality-bit probe 被标记为 `LIGHT_H0_INCONCLUSIVE_HISTORY_FEATURE_TOO_NARROW`；它没有表示上一动作的通用语义。H0b 已用 generic Replay action interactions 加 capacity-matched permutation control 重跑，且 L2 保存并使用 `previous2_source_O`；aligned history 优于 O-only 与 permuted history。首版 compression runner 曾漏掉每个 actor-unit 的第一条 prior，并错误构造 permutation，现已修复并完成 depth × nontrivial closure：在排除 exact-repeat shortcut 后，depth≥2 的 26D cumulative-mean persistent 略优于 raw-prev 但 CI 跨 0，且显著优于相同 depth-bin 的 within-split permutation；depth≥3/4 样本较少、置换区间跨 0。当前为 `COMPRESSION_DEPTH2_ALIGNED_SIGNAL_PRESENT; COMPARATIVE_SUFFICIENCY_INCONCLUSIVE`，不作 formal non-inferiority claim。详见 [H0b report](LIGHT_H0b_transition_probe_v0.md) 与 [compression benchmark](LIGHT_compression_benchmark_v0.md)。

### Blind semantic admission 50（2026-09-07）

已生成固定、model-blind 的 50 条跨 trajectory source package：
`outputs/external_assets_2026-09-06/LIGHT/light_semantic_admission_blind50_20260907.csv`，以及可直接交给独立 LLM 填写的
`light_semantic_admission_blind50_20260907_for_external_llm.md`。
此前的 `*.reviewed.csv` / `*.readout.md` 只是 AI source-only diagnostic，不是人工 semantic admission，不能作为准入证据，也不应提供给独立 reviewer 作为输入。候选集仍只被定义为 observed-source candidate set，未据此宣称 `A^O` 已验证。

### Full semantic annotation shards（2026-09-07）

全量 mechanism-dev cohort 已按 source-only 当前步证据切成 **24,999 rows / 500 shards × 50**；协议见 `full_semantic_annotation_20260907_v1/protocol.md`，输入位于同目录 `shards/`。输入不包含 previous/future step、Run1–4 结果或其他 reviewer 输出；reviewer 只返回紧凑 JSONL 标签，逐 shard 校验后追加落盘，便于断点续跑。3×20 smoke 也已生成并通过结构检查。

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

`run_compiled_semantics_v0.py --scene-aware` 现在先调用 `compile_light_step()` 生成 canonical `SceneSnapshot`，再将 candidate target 与 snapshot 的 entities、actor observation 和 possessions 做最小绑定，并对不在 scene/不可见/已携带的 target 调整 candidate semantics/bias。当前 neutral replay scorer 下，verb-only v0 的 stateful/no-history NLL 均为 **1.444400**，scene-aware v1 的 stateful/no-history NLL 均为 **1.438298**；scene-aware frontend 的平均 gold probability 校准（NLL）相对改善约 0.00610，但 top-1 与 MRR 反而下降，因此不能笼统称为 ranking 更好；各自 stateful 与 no-history 相同，该差异不能归因于 persistent S，且仍只是 dev diagnostic。

### Transition theory-S diagnostic

`run_transition_theory_s_v0.py` 在同一 140 steps 上执行 `SceneSnapshot(t-1,t) → transition → appraisal X → AppraisalTraceStateV0 → candidate scorer`，并输出 zero-S、theory-S、trajectory-permuted-S 三组 trace。固定 `eta=0.35`、离散 replay boundary `Δt=1`；replay scorer 现在只接收候选语义和显式 `ReplayPolicyConfig`，不读取 RoomDemo `CharacterState/Personality`。neutral scorer 的冻结结果见 `LIGHT_transition_theory_s_replay_neutral_v0.summary.json` 与同名 manifest；旧 `drive-linear-v0` 结果保留为带版本名的历史 smoke。运行 trace 位于 `outputs/experiments/LIGHT_transition_theory_s_replay_neutral_v0/`。本轮只作机制 smoke，不调 eta 或 scorer。

neutral scorer 重跑后（按 decision-index 分层 permutation）结果为：zero-S `1.438298`、theory-S `1.436894`、permuted-S `1.441893`、uniform `1.412648`。正确历史现已优于 permutation，但三组 mean rank 均为 `2.3`，因此当前差异主要体现为 probability calibration 而非 action ordering；仍输给 uniform。negative channel 本轮非零率为 0，expected effect 41 条中 15 条 confirmed、26 条 unconfirmed。
