# 公开审阅材料索引（2026-10-07）

本次只改变材料的远端可见性，不重跑、挑选最佳 seed、修改模型或提升研究结论。审阅分支是 **`webgpt-sync`，不是 `main`**。历史失败、被停止的运行、合成测试与真实开发运行按原 run ID 分开保留；“已上传”不等于“结果有效”。

## 先读什么

| 问题 / 证据组 | 报告与解释边界 | 支撑结果路径（仓库内） |
|---|---|---|
| 当前研究方向、有哪些事还没证明 | [研究重建审计](../00_研究设计/研究重建审计_2026-10-06.md)、[TODO](../00_研究设计/TODO.md) | 不以工程闭环或自有评分器替代方法 / 玩家证据 |
| 世界中心 NPC、作者成本、已有方法的算法层 | [文献总入口](../01_文献/README.md)、[算法拆解](../01_文献/算法拆解_NPC方法与生产系统_2026-10-07.md)、[外围调研](../01_文献/专题调研_世界中心NPC的制作障碍与活人感_2026-10-07.md) | 文献审计正文已跟踪；论文原件不是本次结果上传对象 |
| 第一阶段算法地基（2026-10-08） | [算法积木总表](../01_文献/算法积木/README.md)及其三份17字段卡 | 具体运算、权限/代码接缝、手推与本人待补栏；无新实验结果；两份完整新原文仅本地，论文PDF不上传 |
| 多粒度作者约束、旧规划算法与 NCP-Bench | [技术考古总报告](../01_文献/专题调研_多粒度剧情连接与LLM重组_2026-10-07.md)、[NCP 协议卡](../01_文献/精读_NCPBench_协议与接入边界_2026-10-07.md)、[来源清单](../01_文献/来源清单_叙事技术考古_2026-10-07.json) | 新增的是原件/源码审计与纸面例，不是实验；完整新对话私有、不上传；本地论文/失败缓存不混为公开结果 |
| 多层状态轨迹与可执行世界（当前续审） | [算法级续审与下一动作](../01_文献/专题调研_多层状态轨迹约束与可执行世界_2026-10-07.md)、[阅读/版本/未核账本](../01_文献/来源清单_多层状态轨迹_2026-10-07.json) | 状态约束、地标修复、语义编译、执行 canon 的文献审计；无新模拟/玩家结果；两份新原文仅本地，不上传 |
| Praxish 原件及共同小场景 | [Activity Pilot](Praxish_Activity_Pilot_v0/README.md) | `outputs/praxish_activity_pilot_v0/` 的自有运行记录；下载的作者原代码包不上传 |
| Praxish / utility 匹配比较与真实失败 | [RESULTS](Praxish_Utility_Comparison_v0/RESULTS.md) | `outputs/praxish_utility_comparison_v0/`：case results、typed timeline、debug / failure evidence、manifest、匿名 viewer；test-only 子目录不冒充真实比较 |
| 已训练开发预测基线与复现 | [PredictionBaseline RESULTS](PredictionBaselineV1/RESULTS.md) | `outputs/prediction_baseline_v1_20261006/`：逐行 loss、epochs、split / config / manifests、代码快照、小型训练 checkpoint |
| 九来源条件排名开发比较 | [SourceRanking INPUT_REVIEW](LIGHT_SourceRankingV1/INPUT_REVIEW.md) | `outputs/light_source_ranking_v1_20261006/`：逐行 predictions、epochs、训练产物、审计脚本及协议 / 代码快照；输入 JSONL 不上传 |
| 旧 LIGHT / T14–T20 / Theory-S proxy 与失败分解 | [实验路由](README.md)及各分支协议 | `outputs/experiments/`；夹带源文本的 LIGHT 结果另有公开投影，见下节。旧 split / proxy 结论降级不因上传而撤销 |
| split、来源语义和训练准入审计 | [LIGHT 准入精读](../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md) | `outputs/research_reset_audit_20261006/`、`outputs/light_prediction_admission_20261006/`、`outputs/light_source_contract_20261006/`；输入 / 原文 review 排除 |
| Laya 历史 / no-history、typed 模式及未通过 gate 的运行 | [Laya README](../Demo%20codex-generated/demo/laya_typed_policy_v0/README.md) | `outputs/laya_runs/`：合成 trace / cassette、结果 / 审计 / 配置；v1 输入截断、v2 stale clock / choice surface、v4.3 gate 失败仍保留，不能混成可解释的正式行为实验 |
| 短窗 utility / history-LLM 的连续运行与回放 | [阶段 1—3 检查点](../Demo%20codex-generated/applications/npc_continuity_v0/STAGE3_CHECKPOINT.md) | `outputs/npc_continuity_v0/`：六条 stage23 trace、11 次调用 journals、paired audits、哈希与匿名 player；另有旧 smoke，不混用 |
| 旧行为 audit / event-relaxation / 来源表示比较 | 对应历史报告与 provenance | `outputs/behavior_audit_casebook_v0/`、`outputs/again_dynamics_audit_20260908/`、`outputs/clubfloyd_representation_baseline_structured_v0/`、`outputs/T0c_LIGHT_batch4/`；旧失效解释不能复活 |
| 参数敏感度、optimizer、self-evaluation、holdout | [实验路由](README.md)与历史协议 | `outputs/parameter_sensitivity_v0*`、`outputs/optimizer_v0*`、`outputs/self_evaluation_v0*`、`outputs/sensitivity_*`、`outputs/development_split_v1/`、`outputs/holdout_v1/`；小型报告 / 结果全保留，大轨迹 CSV 按大小排除，不因此宣称 objective 有效或选出了 candidate |

这张表是阅读路由，不是独立实验计数。所有实际上传与排除项以机器清单为准；未关联来源的 `_candidate_*.json` 仅作为 legacy artifact 保留，不能凭文件名归属为一项已验收实验。

## 精确范围与核验

本次白名单覆盖 **2,817 文件 / 647,489,863 bytes（约 617.49 MiB）**，其中包括少量原已跟踪材料，不是 2,817 个独立实验。新增结果文件为 2,758 个。26 份来源结果已生成公开投影；文件级清单的 `public_projection` 将原件直接连到副本及其 hash。上传前通过 20 项发布 / 投影合同单测、25 项现有配对分析 / 展示单测，并核对全部白名单文件的字节数及 SHA。

- [文件级发布 / 排除清单](public_review_inventory_20261007.json)：路径、大小、SHA-256（发布文件）、分类和理由。扫描 `outputs/` 及指定历史结果目录；文献审计、进度正文和已跟踪 Demo 结果由普通 Git 历史提供，不重复复制。
- [确定性盘点工具](../tools/public_review_inventory.py)：生成白名单并逐文件核对已发布字节。`outputs/` 仍默认忽略，只对清单中的文件显式加入 Git，防止今后的输入 / 缓存自动泄漏。
- [源文本剥离结果](../outputs/public_result_projections_20261007_v2/)及[投影工具](../tools/project_public_result_evidence.py)：保留已有分析数值 / 源 ID 的可审阅副本，不更改原文件，不执行实验，不算新结果。

完整数据集输入（含 `_local_data/`）、外部源码 / 原文下载、预训练大模型、构建 / 缓存、环境服务日志、迁移 Git 备份不上传。**单文件达到 20 MiB** 本次作为大文件排除，包括若干本项目生成的大轨迹 CSV；这是发布预算，不是删样本或重新分析。大文件留在本地，原实验 manifest 内的引用 / hash 保留。已在仓库中的历史材料不由本次批量移除。

夹带数据集原文的 LIGHT trace / review 与 OPeRA candidate artifact 不原样上传。公开副本保留逐行数值输出、来源 ID、自己计算的语义特征 / 分类等明确字段，去除源观察、动作原文、候选 prose 和嵌套场景文字；投影 manifest 记录来源与输出 hash、行数和信息剥离规则。它不是完整 raw trace，无法在缺少本地数据集时单独复现输入构造或做原文语义复核。未决的人类判断仍是未决，不被投影或上传变成 PASS。

合成 NPC 的 prompt / response / cassette 是实验输入输出，不是人的私聊；本次检查凭据和异常私密字段后保留。SHA 与路径 provenance 表达“哪些字节被运行 / 留存”，不等于源码版本已经通过独立审查。

## 特别容易误读的代码状态

stage23 paired harness 的 C++ 源码和 CMake 本机仍有尚未提交的开发改动。本次发布检查点、协议、结果及通过单测的分析 / 回放导出工具，不顺手提交未验收的 Runtime / harness 修改。运行源码 / 二进制 hash 存在，但不能把这些运行说成来自干净提交；fresh clone 可审结果，未必可直接重建那一次 harness。SourceRanking / PredictionBaseline 的已冻结代码快照及对应实验清单则保留各自 provenance。

上传不取消原定“到开发检查点停、先讨论”的边界，也不启动新训练、长批次、玩家研究或心理机制开发。
