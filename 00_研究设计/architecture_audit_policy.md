# Architecture audit policy

人工结构审计采用 milestone trigger，不按固定日历周期。`webgpt-sync@685c319` 是本轮 anti-patch-debt baseline。

## 触发点

1. 第一个新 dataset adapter 完成后；
2. 第二种不同数据域接入后；
3. 第一次因外部 dev 数据修改 `S`/`U_k`/utility/timing 后；
4. mechanism v1 freeze 前；
5. 合并 `main` 前；
6. 距上次审计累计 5–10 个实质 commit 后。

## 审计清单

检查重复 pipeline、职责膨胀、dataset schema 漂移、实验/runtime 分叉、hidden side-channel、字符串 ontology 漂移、provenance 丢失、dev/test 污染、无意义抽象、dead helper/dead field、语义阶段被折叠以及文档重复。

日常小 bug 不触发完整审计。机器 guard 只做廉价预警；人工记录应写明基线 commit、发现、风险、决定和后续动作。
