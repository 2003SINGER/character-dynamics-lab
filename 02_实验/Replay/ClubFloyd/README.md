# ClubFloyd Replay adapter

这是 ClubFloyd 的独立 adapter 资产，不属于 runtime，也不与其他数据集共享原始文件。

## 当前切片

- 原始包：`outputs/external_assets_2026-09-06/ClubFloyd/lm_data.zip`（本地忽略目录）
- 原始解压目录：`.../raw/cleaned_corpora/`
- 开发切片：`outputs/external_assets_2026-09-06/ClubFloyd/clubfloyd_dev_30.replay.json`（本地忽略目录）
- 生成器：`../clubfloyd_adapter.py`
- 结果：30 条 trajectory、30,388 个 observed steps；已通过 ReplayRecord v0 validator。
- 全量无损抽取：425 条 trajectory、438,188 steps；统计见 [full extraction QA](full_extraction_report_v0.md)，全量 JSONL 仅保存在 ignored external-assets。

## 映射边界

源文件是 `[STATE] ... [ACTION] ...` 的回放文本。每一对只复制为 `source_O` 与 `source_action_A_star`；`W`、persona、state label、candidate sets、event 和 timestamp 保留为 `null`。没有加入 LLM 推断，也没有把游戏响应重写成角色内部状态。`source_step_context` 保留同一对原文，便于审计。

## 复现

```powershell
py -3 02_实验/Replay/clubfloyd_adapter.py `
  outputs/external_assets_2026-09-06/ClubFloyd/raw/cleaned_corpora `
  outputs/external_assets_2026-09-06/ClubFloyd/clubfloyd_dev_30.replay.json --limit 30
py -3 tools/validate_replay_record.py outputs/external_assets_2026-09-06/ClubFloyd/clubfloyd_dev_30.replay.json
```

这只是结构切片，不是语义准入或机制实验。下一步是逐条审计 W/O/X/S 归属、动作语义损失和 future leakage；审核前不得扩大批量或进入 mechanism loop。

Stage-A source-command 入口已冻结于 [source-command protocol v0](source_command_protocol_v0.md)。当前 30-trajectory smoke 仅验证 `verified_command_like_v0`、canonical `verb/target/modifier`、trajectory-disjoint split 与 future-boundary；尚未开始模型训练或 Theory-S representation comparison。

## Corrected action boundary (v1)

Read [command admission definition v1](command_admission_definition_v1.md) before using any Stage-A action. ClubFloyd `[ACTION]` is observed chosen action `A*`, not an objectively legal world action `A^W`, and not the character's subjective candidate set `A^O`. Failed, rejected, mistaken-belief, unreachable-target, and parser-rejected in-world attempts remain `A*` when the player's in-world choice is clear. World settlement/outcome is a separate later layer.

`command_admission_audit_semantic_v0.jsonl` and `command_admission_review_independent_v0.jsonl` are historical model-assisted review provenance, not human gold. The corrected 60-row challenge set was independently reviewed by three fresh LLM sessions and aggregated under [the frozen rule](llm_adjudication_aggregation_rule_v1.md): 51 `MODEL_CONSENSUS`, 9 `MODEL_MAJORITY`, 0 human-required. These are frozen multi-LLM adjudicated development labels, not human gold.

The first v0 canary is retained but marked `STAGE0_V0_INCONCLUSIVE_PROBE_SANITY_FAILED`; its former `NO_CLEAR_HISTORY_SIGNAL` interpretation is invalidated. Stage 0b passes the low-order probe sanity check, but [duplicate sensitivity](stage0b_duplicate_sensitivity.md) and the frozen [Stage 0c non-duplicate view](stage0c_nonduplicate_protocol.md) show no positive history increment for the current verb-family estimand after exact pair repeats are excluded. This establishes a repaired measurement interface, not a Theory-S result; the ClubFloyd persistent-compression bridge is paused.

全量抽取与分层 review slice：

```powershell
py -3 02_实验/Replay/ClubFloyd/extract_full.py outputs/external_assets_2026-09-06/ClubFloyd/raw/cleaned_corpora outputs/external_assets_2026-09-06/ClubFloyd
```
