# P0 原始路线审计：LLM 引导 Sabre 搜索

阅读日期：2026-10-11
状态：论文方法 + 上游源码审计 + 五节点历史缓存回放完成；新模型准入未通过
论文原件：`90_原始材料/_private/2026-10-11_Planner_P0/farrell2024large.pdf` 与 `senanayake2025language.pdf`（私有原件）；[Farrell & Ware 作者 PDF](https://cs.uky.edu/~sgware/reading/papers/farrell2024large.pdf)，IEEE Transactions on Games 17(2), 419–428 (2025), DOI [10.1109/TG.2024.3487416](https://doi.org/10.1109/TG.2024.3487416)。对照论文：[Senanayake & Ware 作者 PDF](https://www.cs.uky.edu/~sgware/reading/papers/senanayake2025language.pdf), FDG 2025, DOI [10.1145/3723498.3723815](https://doi.org/10.1145/3723498.3723815)。此处称“对照”，不暗示它是前一方法的直接继承或必然时间后续。

## 结论先行

**论文证据：**Farrell & Ware 将 GPT 用作 Sabre Uniform Cost Search 的搜索引导。LLM 在每个弹出节点上读自然语言故事上下文并建议两个下一事件；合法 grounded action 与建议文本用 `text-embedding-ada-002` 向量作 cosine-distance 匹配，再将距离量化为动作边成本。Sabre 仍负责状态转移、合法前提、作者目标与角色 explainedness 的检查。

**项目决定：**这不是 LLM 生成完整故事后交给规划器验收，也不是 LLM 打分器/合法性 oracle。搜索优先级是软引导；它不剪去低相似动作，也不保证找到最短/最佳故事。计划被接受的边界仍由 Sabre 的硬语义判定。

**状态限制：**原仓库已检出于本机忽略目录 `_local_data/planner_p0_v0/planning-stories-neurally/`，HEAD `4a258be9e36bb4fedcee0f7eaec92652ed8e532f`（2025-06-23）。仓库未发现 `LICENSE`、`COPYING` 或 `NOTICE`；原件、完整源、CSV 向量、完整提示/响应 transcript 均留在本机忽略目录，不复制进公开项目。捆绑 Sabre JAR SHA-256 `b74d1f73cad5a68a077794a99d97a7b0348739dcf0958b5b3d42c88e8ac2d526`，class major 64；JDK 17 无法加载。JDK 21 运行原 jar 又因缺少 `ProgressionPlanner$Method$4` 失败。全量原源码在 JDK 21 编译原样失败于 `Precondition.java:82` 泛型推断；仅在忽略目录副本中将该行改为显式类型实参 `new Disjunction<Clause<Precondition>>(new Clause<Precondition>(this))` 后，全量统一编译通过。该构建标为 `SOURCE_COMPAT_BUILD`，不是原始 jar 原样通过；上游 checkout 未修改。

## 论文方法

### 输入与模型调用

论文把每个搜索节点表示为从初态开始的动作历史。提示上下文由初始状态、每个角色的目标、域动作名称、作者故事目标和已发生动作组成；各 benchmark 的动作/状态自然语言语法由作者手写。LLM 默认返回两条不同的下一事件短句，使用 `gpt-3.5-turbo` (May 2023)，temperature 0.3，最多 25 tokens，不微调；非根节点的历史格式构成少样本提示。

LLM **不**枚举/排序当前完整合法动作集，也不决定可执行性。论文称这是刻意限制模型任务：预测接下来可能发生什么，把复杂推理留给符号 planner。

### 匹配、评分与搜索

合法 grounded action 的自然语言描述和每条 LLM 建议都嵌入；原文使用 `text-embedding-ada-002` (May 2023)。对动作 `a` 和建议集合 `S`：

```text
d(a,S) = min_s [1 - (1 + cosine(EM(a.NL), EM(s))) / 2]
cost(a) = round(d(a,S) * z), 默认 z=100
```

Algorithm 1 的核心顺序：最小优先队列弹出累计边成本最低的计划；若到达 author goal 且计划 explained，则返回；若未超过深度界，向 LLM 请求下一步建议，枚举所有当前满足 precondition 的动作，为各动作计算边成本并把扩展计划压回队列。成本是边代价累加，所以长但贴近建议的轨迹可先于较短但不匹配的轨迹被访问。

| 职责 | 保证边界 |
|---|---|
| LLM completion | 提供软的后继事件提示；错误、不可执行、偏离角色目标的建议都可能出现 |
| embedding + cosine mapping | 只产生相似度诱导的边成本；不是语义等价或因果必要性的证明 |
| Sabre action precondition | 只把当前符号状态下可执行的 grounded actions 扩展进计划 |
| Sabre state transition / author utility | 状态更新及故事目标可达性仍由符号域和 planner 判断 |
| Sabre explainedness | 解必须通过人物动作解释约束；论文算法用先前搜索预计算的 explained-node lookup 检查 |
| depth / queue checks | 深度上限导致不再扩展；队列空则报告 failure。有限预算下 failure 不等于全域无解 |

原方法没有用相似度阈值剪枝。论文在讨论中把阈值剪枝列为可探索的未来改进；P0 若使用该策略即属于另一个算法变体，不能静默加入。

## 论文结果与限制

作者以 benchmark 搜索为初步评估；最多 5000 节点，且未对每个方法多次重复取平均。基线 UCS-1 与 UCS-GPT 被限于相同的“possible node”空间；Sabre 还要搜索 epistemic nodes 以验证错误信念下的解释，因此三者节点数不能直接视作同空间排名。论文报告多数域搜索节点与 visited explainedness 有改善，但有例外；词语改名/语义混淆可使性能显著恶化，且 embedding 字面相似不总等价于剧情语义相似。

作者明确指出没有将 LLM guidance 合入真正的搜索 heuristic；当前是统一成本搜索的优先级，不是 A* admissible/consistent heuristic，也不提供最优性保证。其他局限包括 completion/embedding API 延迟、手写自然语言语法和调用成本。输出可能给出当前不可行事件；Sabre 的合法动作前提负责挡住它们。

## 原始仓库源码核对

只使用文件/函数名和行号作为本机核查定位；原项目无许可证文件，故不复制源代码片段。阅读归属：本卡作者通读论文与上游方法链；主代理另行 spot-check 论文 Algorithm 1 和 `LLMSearch`/`OpenAIComponent` 核心。

| 搜索环节 | 上游实现位置（HEAD `4a258be`） | 可验证边界 |
|---|---|---|
| 选择队列节点 | `src/r7/llmsearch/LLMSearch.java:48-78,85-108`；继承 `ProgressionSearch.compare` `src/edu/uky/cs/nil/sabre/prog/ProgressionSearch.java:556-570` | `LLMSearch` 用 `CostTable` 且 heuristic 为 `ProgressionCost.ZERO`；队列按累计成本排序，平局再看 heuristic、epistemic depth 和空间次序。不是模型直接排序完整动作集。 |
| 获取候选动作 | `LLMSearch.java:147-165` | `problem.actions.getEvery(state)` 枚举当前状态合法 grounded actions；建议文本不能使不满足符号前提的 action 变合法。 |
| prompt 与建议 | `LLMSearch.java:175-209`；`OpenAIComponent.java:13-53,67-95` | 源码默认 system role 为 “You are helping the user outline a branching story.”，chat 默认 `gpt-3.5-turbo-1106`；25 tokens、temperature .3；embedding model 固定 `text-embedding-ada-002`。这与论文所记 May 2023 模型名/快照并不完全等同，属于仓库具体实现配置。 |
| action edge scoring | `LLMSearch.java:211-223,266-274,308-333` | 每个建议与每个候选动作自然语言先精确查本地 CSV；miss 才请求 OpenAI embedding。取最近余弦距离，clamp cosine 到 [-1,1] 后 round(100×(1−(cos+1)/2))。`CostTable.java:8-28` 将边成本累加；不是把不相似边剪除。 |
| 目标与 explainedness | `LLMSearch.java:91-108,124-143` | 作者目标满足后先查每个前缀是否在预计算 `explainedNodes`；成功通过抛出 `IllegalStateException("Solution found...")` 终止。注意源码在 goal 节点调用检查后无条件 `return`；若 explained lookup 未通过，不再扩展该节点。论文 Algorithm 1 的叙述是只有 goal 且 explained 才返回解、否则仍受深度条件控制；源码这个 return 是实现/论文表述差异，不能把失败节点当作继续扩展。
| 错误路径与预算 | `LLMSearch.java:24-29,91-108,147-165,277-292` | 固定 `SEARCH_NODE_LIMIT=5`，另有 5 秒请求等待；CLI `-atl 5` 是 temporal depth，不是节点数上限。异常被 `processChildren` 捕获后仍扩展子动作；缺失成本会在 `CostTable.getCost` 变成 “No cost has been set” 而失败。shim/replay 发现不匹配必须在结果层标失败，不可称有效搜索结果。 |

仓库根未发现 license 文件；在得到作者授权/明确许可前不公开复制上游代码、向量 CSV、完整 prompt/response transcript 或其长段内容。JAR 的缺失内部类和泛型编译错误属于分发/兼容准入障碍，不应与论文算法差异混为一谈。

## 后续论文：不同的接口与问题

Senanayake & Ware (FDG 2025) 研究的是 LLM 对**剩余故事长度和可达动作内容**的启发式预测：在已穷举并验证距离的状态上比较自然语言/ Sabre 语法 prompt 与 `h+`, `hmax`, `hrp`。原实验用 `GPT-4o mini`、temperature 0、token limit 3000；LLM 完整计划动作通过 `text-embedding-ada-002` 最近余弦映射到 Sabre action。作者报告结果跨域不稳定，传统 `hrp` 在多数域更好，部分 Space/Gramma/Treasure 例外；API 延迟当时阻碍在线搜索。它是 heuristic-prediction 研究，不是前文 UCS-GPT 源码实现的替代说明。两文正式出版时间不同；本卡不把“后续”解释成方法继承或前者已升级版本。

## P0 复现协议与风险边界

上游 README 声明需 Java、Sabre v0.7 与 `OPENAI_KEY`；本轮未配置/未授权新的付费云调用，未执行云 API。主代理提供的 loopback Qwen3-4B-Q4_K_M 仅做了两次 completion preflight（v1 响应在客户端读取 CSV 时解码崩溃，未留存；v2 已先保存原始响应后核验）。v2 模型 fingerprint `b10809-5266f24da`，prompt/completion/total tokens 为 296/17/313；两条新建议在原 Gramma embedding cache 精确查找均 miss，因此当场停止。该结果只标 `ADAPTED_COMPLETION_PREFLIGHT`，不是 P0 search run；没有请求任何 embedding endpoint，也没有运行 Qwen 搜索。精确命中是唯一允许的本地 cache 复用标准，禁止同义匹配、字符串规则或替代 embedding。

只允许小型共同域/固定搜索预算 sanity run。不得更改 budget 来改善单边结果，不跑大 benchmark。详细实验记录见 [`02_实验/Planner_P0_v0/llm_search_guide/REPLAY_AND_PREFLIGHT.md`](../../../02_实验/Planner_P0_v0/llm_search_guide/REPLAY_AND_PREFLIGHT.md)：官方 Gramma 历史 run 1 的五条 search trace 与五轮 prompt/suggestion/cost 通过本地精确提示 replay 后，`search.txt` 与 `transcript.txt` 都逐字节匹配原件 SHA；这是 `REPLAY`，不是 live。原始完整 transcript/CSV/JAR/源均留在 ignored 本机目录。当前尚缺一条可审计、与新 completion 建议逐字兼容的 embedding 供应路径；新建议 cache miss 后必须停止，故 live search 为 `NOT_LIVE`。后续若要 live，需要明确授权合适的 completion 和原法所需 embedding provider/预算；不能靠本地 chat endpoint冒充 ada embeddings。

## 当前项目对应

这是成熟规划中“神经模型引导搜索次序、符号 planner 保持合法性与目标/解释保证”的直接基线。对本项目可借鉴的只是软偏好与符号门控分离；不能据此断言新的组合收益、故事质量或本地模型等价。最小验收应先拿到原 checkout 与许可证、确认历史 API/cache，再在共用 Sabre 版本的小实例上记录请求和每个 expanded node/edge cost；若 embedding 资源不可取得，应停止 live run，保留原件审计与有标记 replay。
