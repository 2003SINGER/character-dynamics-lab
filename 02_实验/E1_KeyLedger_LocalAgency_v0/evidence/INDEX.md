# E1-1 开发证据索引

结果与边界只见[RESULTS](../RESULTS.md)。本包不是正式实验；原始运行不因打包而重跑。

- [完整 ZIP](E1_dev_f637743_20261009.zip)：**3,800,918 bytes，93 个成员**。
- ZIP SHA-256：`bbf09a913483ac89ad62a4f7281345e9c32c05ef8fea323256770e725d010ac4`。
- [成员 manifest](E1_dev_f637743_20261009.manifest.json)：逐成员路径、大小、SHA-256，来源目录，源码审计与后续文档 hash 区别；父级独立回读 93/93 成员及 4/4 compact 副本一致。
- 直接阅读：[audit.json](audit.json)、[E1 单测](unit-tests.log)、[TypedIR 回归](typed-ir-tests.log)、[本次 E0 云端失败日志](ci-e0.log)。E1 云端日志/原始 artifact 在 ZIP 内。

`sources/` 保留三次早期开发运行 `dev-20261009-e1-1{-r2,-r3}`，精确源码 primary/rerun，两次 budget 负控，以及父级审计目录。审计目录包含 `audit_parent.py`、`bundle_evidence.py`、本地测试/健康日志、E1 Ubuntu artifact 和原样保存的 `ci-e0-artifact.zip`；后者来自 GitHub artifact `11600699426`，保留此次 E0 失败的全部 14 格记录，不只有 H02。

f637743 上的原审计报告对应 **29 项当时源码/依赖/协议 hash**。最终交付仅追加证据和外围文档，并澄清协议 §8 的开发授权句；包源码与行为/预算规则未改。protocol SHA-256：原审计 `255a9418a72f5996d5cb57b141a8a88acbe1c0e4e58d49c98098feadce2b1d76`，后续文档 `dd2a017a35d6def5ac47c38eef635086ead1fd2446ec2c37522a56dc357b7042`。不能把后续文档 HEAD/hash 写成原运行的 HEAD/hash。

原审计脚本要求 f637743 checkout；若只复核归档，应从 ZIP 按 manifest 回读成员，而非在新 HEAD 下反复覆盖旧 `audit.json`。新开发回放命令见[代码 README](../../../tools/e1_keyledger_v0/README.md)，必须选择新的 run-id。

非压缩本地原件仍在项目 `runs/e1_keyledger_v0/dev/`，未移动或删除。公开包只含有限合成实验与 CI 记录，**不含私有对话原文或外部数据集**。
