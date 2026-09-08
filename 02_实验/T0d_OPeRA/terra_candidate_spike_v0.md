# T0d｜OPeRA Terra candidate spike v0

核查日期：2026-09-08  
范围：30-step deterministic blind fixture；只验证 `raw interactables → Terra semantic candidates`，不训练、不修改冻结 OPeRA protocol、Theory-S 或 canonical 13D readout。

## Verdict

**CANDIDATE RECONSTRUCTION：NO-GO（当前 spike）；OPeRA 总体仍 LIMITED-GO。**

这次不是 deterministic HTML grounding smoke，而是实际调用 `gpt-5.6-terra` 的 gold-blind 语义候选生成。结果显示 Terra 能把页面元素压缩成小候选集，但 target identity 保留和歧义控制不足，不能把当前结果升级成可用的 `Ahat^O` support。

## Frozen protocol and artifact boundary

流程固定为：

```text
pre-action simplified_html + URL + legal past history
  → deterministic raw interactive elements
  → Terra semantic filtering/grouping/normalization
  → frozen candidate artifact
  → evaluator reveal of current gold action
```

Fixture 由 session SHA-256 排序后固定抽取 10 个 session、每条 3 个 step，共 30 records；没有按当前 action、semantic_id 或预测难度选样。Terra generator 只声明并读取 `url`、`history`、`raw_elements`，artifact 标注 `gold_access=false`。每个候选保留 raw source-index provenance、ambiguity 标记和 generator metadata。

机器产物均在 Git ignored 的 `outputs` 下：

- generator：[candidate_artifact.json](../../outputs/opera_t0d_2026-09-08/terra_candidate_spike_v0/candidate_artifact.json)
- evaluator：[evaluator_report.json](../../outputs/opera_t0d_2026-09-08/terra_candidate_spike_v0/evaluator_report.json)
- blind input：[blind_input.json](../../outputs/opera_t0d_2026-09-06/terra_candidate_spike_v0/blind_input.json)
- evaluator-only gold：[gold_evaluator_only.json](../../outputs/opera_t0d_2026-09-06/terra_candidate_spike_v0/gold_evaluator_only.json)

Generator metadata：`gpt-5.6-terra`、temperature `0.2`、protocol `T0d-terra-candidate-v0`、30 unique fixtures、157 candidates。candidate artifact SHA-256：`2D6388D9D45DB391B35711F3B627D959437FD06E11530DAF5EE71CC7ADB313DD`。

## Evaluator rule and results

Evaluator 在 artifact 固化后才读取 gold。matching 使用 gold 的 `semantic_id` / structured `element_meta` 与候选的 controlled intent family；不使用 target-description lexical overlap、fixture suffix 或 raw provenance 作为 support。`semantic` 表示非歧义候选命中 intent family 但抽象掉 exact target；`ambiguous` 表示只有 ambiguity=true 的候选支持；`exact` 要求非歧义且保留 target identity。

| metric | result |
|---|---:|
| records | 30 |
| total candidates | 157 |
| candidates per record (mean / median / p25 / p75 / p90) | 5.23 / 5 / 5 / 5.75 / 6.1 |
| strict support recall `(exact + semantic) / 30` | **7/30 = 0.2333** |
| exact | 0/30 |
| semantic | 7/30 |
| ambiguous gold matches | 17/30 = 0.5667 |
| misses | 6/30 = 0.2000 |
| candidate ambiguity rate | 114/157 = 0.7261 |
| duplicate candidate IDs | 0 |
| no-candidate records | 0/30 |

The diagnostic support rate including ambiguous matches is 24/30 = 0.8, but it is **not** strict support recall and cannot be used as a GO result. Every record contains at least one ambiguous candidate; exact support is zero. The evaluator verified prohibited current-gold keys were absent from generator input/artifact and the frozen artifact hash was stable across reads. It did not rerun Terra, so reproducibility is artifact-hash stability, not regeneration equivalence.

## Decision boundary

This spike answers the narrow question “can Terra reduce raw page elements to a compact semantic candidate list?”—yes, structurally. It does **not** establish that the list preserves the user's exact target support. The current 23.3% strict recall, zero exact matches, and 72.6% candidate ambiguity are insufficient for candidate-set training or canonical `A^O` claims.

Therefore:

- keep OPeRA at **LIMITED-GO** for a coarse click-type/history auxiliary only;
- do not start `α, β, b, W` training;
- do not modify Theory-S, action features, or the frozen OPeRA protocol;
- if reopening this branch, first redesign target-identity preservation and ambiguity handling, then rerun a fresh blind fixture with a new protocol version.
