# 有限作者义务规划

本包把冻结 B0 的世界投影与有限事件进度组成 UCS 的 product state。终态相同而作者过程不同，会是不同的搜索问题；未指定条件不补成作者硬要求。没有新增游戏规则、原生命令攻略、LLM Judge 或通用时序语言。

- `tasks.py`：28 个静态作者任务、4 个在线编辑/反馈场景的人工参考，不包含行动序列。
- `contracts.py`：严格 JSON 绑定；非法能力/事件拒绝，不静默丢条件。
- `search.py`：UCS × 有界监测器；原生历史按任务版本重新编译。FOUND 仅是有限模型中存在预测计划。
- `conflicts.py`：带证书的有限模型矛盾检查；NO_CONFLICT_PROVED 不等于可达。不会把预算失败改名为无解。
- `native.py`：复用原 P1 Session、B0 算子/可见观察，在实际回执后推进义务；H1–H3 只变更作者版本，H4 是明确标记的反馈延迟负控。
- `verify.py`：只从原生字节、已登记词表与完整日志检查作者终态/过程，不导入搜索进度。
- `run.py`：先保存输入和源快照，再分别执行人工参考、Luna 候选搜索及预选原生任务；文件存在即拒绝覆盖，不自动重试。
- `audit.py`：只读复核来源哈希、作者版本、已提交历史前缀；不重跑游戏。

真实运行、失败与修复验收只由[本轮 RESULTS](../../02_实验/Author_Obligation_Planning_v0/RESULTS.md)维护。源模型依然是原来的有限手工 B0，不是完整游戏状态推演。

离线契约：`python -B -m unittest discover -s tools/author_obligation_planning_v0/tests -v`。

复现需要另一个未存在的 pack 路径：先 `python -B -m tools.author_obligation_planning_v0.run prepare --pack <new-path>`；默认只产生人工参考输入，不会调用模型。模型候选须另行获取、原样保存后以 `offline --pack <new-path> --bindings <candidate.json>` 验收。`native --pack <new-path>` 只使用已验收候选，不会回退到人工答案；不得指向本轮已保存的目录重跑。原生依赖本机已固定的 Open Adventure 构建；CI 只运行离线契约，不下载游戏、不调用模型。
