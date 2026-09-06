# Adapter review fixtures v0

这些是从真实本地 raw asset 自动生成的 raw → transformed 对照夹具，专供 WebGPT/人工逐条审 adapter；不是新数据集，也不是 semantic annotation。

| 文件 | 条目 | SHA-256 | 生成器 |
|---|---:|---|---|
| `ClubFloyd_review_v0.jsonl` | 375 | `84F6C2C72E15425C1A573D7550BA44746DB1934968D865444A3F1545DCA8AC9F` | `ClubFloyd/extract_full.py` (`D0EE6C39702554D096C0DE59FA6757A1F9585E068218DF75D8BD02F672EB4445`) |
| `LIGHT_review_v0.jsonl` | 303 | `F23599B64DF9CD16082FB500CA0E321A3F769F403D5E8A54A68EF1B0102EC7AD` | `T0c_LIGHT/extract_full.py` (`500B628011AACEC4419A2D637330A8574073317008C42CC7BDC8F300737C31FC`) |
| `FarmQuest_review_v0.jsonl` | 250 | `AC6162960012A55BA0ECBEEF247787DF462227789984497AC532D1031B75632E` | `T0f_FarmQuest/export_replay.py` (`8916BF731779D8ED27321DDEA1AD8EC4050E851A512602250C659D13BCA9CB33`) |
| `PowerWash_review_v0.jsonl` | 312 | `9EAD5F8AFC8177ADE8B7708C096B511DF6A8A9F878A9AE4B673758D04D17D448` | `T0g_PowerWash/pilot_bucket_pipeline.py` (`0655BD657E317759C6BC1513B6E165689496776AA305DEA8FD3FDE65AB16A43C`) |

每条包含 `raw`、`parsed`（FarmQuest）、`transformed`、`mapping_notes`、`source_record_ref` 和 `generator_sha256`。ClubFloyd 覆盖每条 trajectory 的首/中/尾及长 state/action，并强制包含全部 47 条 chat/commentary-like 与 42 条 meta-command，再补充分层 command-like/ambiguous 样本；LIGHT 覆盖首/中/尾、长 context，并包含异常样本；FarmQuest 覆盖 action proxy、nested QuestBoardState 和 source-order/timestamp 边界；PowerWash 强制覆盖 8 条 `post_exit_orphan` 边界 fixture（该 pilot 未观察到 `pre_login_orphan`）。所有原始文本均由 extractor 从本地 source 自动复制，未人工重抄或手修 transformed。
