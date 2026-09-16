# ResearchDynamicsV1

最小研究动力学候选，当前仅用于 mechanism sanity 与 intervention dry-run。它不替代 `LegacyReferenceRuleDynamicsV0`、`ExpectedEffectEMAProxyV0` 历史 proxy 或 Demo Living，也未进入正式训练。`artifacts/manifest.json` 明确记录 model id、seed 与 zero/correct/permuted/stale/frozen/wrong-field 六类干预。

运行：`python3 -m unittest discover -s 02_实验/ResearchDynamicsV1 -p 'test_*.py'`。
