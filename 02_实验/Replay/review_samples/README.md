# Adapter review fixtures v0

这些是从真实本地 raw asset 自动生成的 raw → transformed 对照夹具，专供 WebGPT/人工逐条审 adapter；不是新数据集，也不是 semantic annotation。

| 文件 | 条目 | SHA-256 | 生成器 |
|---|---:|---|---|
| `ClubFloyd_review_v0.jsonl` | 300 | `A8533BF5840D1B95969291C70F64F3AAEEC372F267216921D44F0C744E777C4E` | `ClubFloyd/extract_full.py` (`D2E1E50A297B9C65541230695470834DB0D9D5EEABFDCC1A0F8ABFB21FF57F8B7`) |
| `LIGHT_review_v0.jsonl` | 303 | `1AC98DD664476318E397057FE193F3E9EC139D1A7B0717D8E36CB136E3276053` | `T0c_LIGHT/extract_full.py` (`494150E1EC9A6A84AA18886050DD48DB0D9D5EEABFDCC1A0F8ABFB21FF57F8B7`) |
| `FarmQuest_review_v0.jsonl` | 250 | `1E612B2C9CB62E8D9CFE3CEA6A8E491117CDB6BDE9C0559E992C1028F85A14F2` | `T0f_FarmQuest/export_replay.py` (`ADB26B2BEDC275AE0A5A1A79897A861D7B134A586BF73D0B9ECBEA44D58972CB`) |

每条包含 `raw`、`parsed`（FarmQuest）、`transformed`、`mapping_notes`、`source_record_ref` 和 `generator_sha256`。ClubFloyd 覆盖每条 trajectory 的首/中/尾及长 state/action；LIGHT 覆盖首/中/尾、长 context，并强制包含 3 条 `A*` 不在 `available_actions` 的样本；FarmQuest 覆盖 action proxy、nested QuestBoardState 和 source-order/timestamp 边界。所有原始文本均由 extractor 从本地 source 自动复制，未人工重抄或手修 transformed。
