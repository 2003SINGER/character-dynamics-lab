# P0 原始规划路线：方法入口

2026-10-11。此处维护原件与计算机制；运行结果、预算、失败和未完成项唯一见 [P0 RESULTS](../../../02_实验/Planner_P0_v0/RESULTS.md)。前轮 [05 审计](../05_游戏世界规划近邻审计_2026-10-11/全量近邻精读总表_2026-10-11.md)保留，不将它的比较候选当成已验证方法。

| 原始资产 | 具体计算作用 | 本轮使用边界 |
|---|---|---|
| [Sabre 官方代码与基准](https://github.com/sgware/sabre) / [基准集合](https://github.com/sgware/sabre-benchmarks) | grounded actions、角色信念与 consenting explanations、作者 utility；原生搜索返回解与解释 | 先运行官方小问题；再对接同一 Evennia 状态和真实回执。不是从零造替代 planner |
| [Farrell & Ware 的原始 LLM 搜索](LLM_Sabre_Search.md) | 节点故事上下文 → 两条下一事件建议 → 原 ada embedding 与合法动作描述的余弦距离 → 累计边成本引导 UCS；预计算 explained lookup | 历史缓存重放、新模型适配、原模型 live 分账；不能用另一 embedding 空间补原缓存，也不能跨 Sabre 版本直接宣称效率优势 |
| [Senanayake & Ware 的启发式研究](LLM_Sabre_Search.md#后续论文不同的接口与问题) | 比较 LLM 估计的剩余长度／动作内容与经典规划启发式 | 核读接口与限制；不是 Farrell 代码的升级运行结果 |
| [Fisher & Ware 2024 抽象](Abstraction_and_MultiCharacter.md) | 划分低层事实 → 外部可用转移签名 → region 等价类 → 抽象状态和算子 | 核读可复用输入输出；本轮未实现该抽象算法，不把论文压缩结果说成任意高层计划都能精化执行 |
| [de Lima 等人 2023 系统级近邻](Abstraction_and_MultiCharacter.md#2023-system-identity-identified-mechanism-not-audited-here) | 多角色规划＋按叙事结构组织的 Drama Management＋图形作者工具 | 已明确是哪篇，作者页面摘要已核。全文分工、POPF、偏离检测、世界干预及执行反馈仍待定向核读；完整源码可得性未确认。不是 Generative Agents / There and Back Again，不阻断当前原始搜索复现 |

de Lima 论文 DOI：[10.1016/j.entcom.2023.100590](https://doi.org/10.1016/j.entcom.2023.100590)，[作者介绍](https://edirlei.com/component/content/article/entertainment-computing-journal-2023-managing-the-plot-structure-of-character-based-interactive-narratives-in-games?catid=8)。原 PDF 与完整上游 checkout 留在本机 ignored 路径；公开报告须区分已读原文、源码实测、用户指出的待核线索。

这轮不实现候选 C 的跨层新规划器，不调整旧 Dynamics，不以作者目标 SAT／符号 explainedness 替代玩家可信度判断。
