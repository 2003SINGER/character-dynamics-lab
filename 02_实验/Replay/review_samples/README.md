# Adapter review fixtures v0

这些是从真实本地 raw asset 自动生成的 raw → transformed 对照夹具，专供 WebGPT/人工逐条审 adapter；不是新数据集，也不是 semantic annotation。

| 文件 | 条目 | SHA-256 | 生成器 |
|---|---:|---|---|
| `ClubFloyd_review_v0.jsonl` | 300 | `E8B711DF407DD67F244B89CD5BB9778901DBDE27550CA3400C49B453B47C7800` | `ClubFloyd/extract_full.py` (`27FC0F78D46BE7945E93171F1488943C051738FECD978DF14DECAE39C22C74D9`) |
| `LIGHT_review_v0.jsonl` | 303 | `112EB7031256DDAA110EE7F0F363BC91136F76E71578B4403919B49CA307A839` | `T0c_LIGHT/extract_full.py` (`548AC81CDC7A7127FEB31A235CDED96E841F404F738498023A16FA09892E5C86`) |
| `FarmQuest_review_v0.jsonl` | 250 | `AC6162960012A55BA0ECBEEF247787DF462227789984497AC532D1031B75632E` | `T0f_FarmQuest/export_replay.py` (`8916BF731779D8ED27321DDEA1AD8EC4050E851A512602250C659D13BCA9CB33`) |

每条包含 `raw`、`parsed`（FarmQuest）、`transformed`、`mapping_notes`、`source_record_ref` 和 `generator_sha256`。ClubFloyd 覆盖每条 trajectory 的首/中/尾及长 state/action；LIGHT 覆盖首/中/尾、长 context，并强制包含 3 条 `A*` 不在 `available_actions` 的样本；FarmQuest 覆盖 action proxy、nested QuestBoardState 和 source-order/timestamp 边界。所有原始文本均由 extractor 从本地 source 自动复制，未人工重抄或手修 transformed。
