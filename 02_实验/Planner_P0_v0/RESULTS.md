# P0：原始规划器复现与共同游戏实例

2026-10-11；DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW（有界检查点）。**共同域 A/B/C 方法比较仍 NOT_READY**，不自行 CLOSED，不声称科研优势、作者劳动减少或玩家可信度成立。

本轮从 `08373231fc197af11474e99b5c1a9e5726962aad` 开始；工作树源文件哈希写入每个原生运行记录。原算法由 Luna 复现，主代理另行执行官方例子、原生 clean 案例、源码边界检查、历史回放字节比较与只读数据库核验。以下均为小型开发复现，不是正式 benchmark。

## 实际完成与准入边界

| 工作 | 结果 | 实际证据 |
|---|---|---|
| A：官方 Sabre 小问题 | PASS | MacGuffin：`walk`→`buy`，utility=1，10 visited / 57 generated；两次原运行与主代理独立复跑一致。[原始 stdout/config](sabre_baseline/README.md)；[主代理复跑](sabre_baseline/evidence/runs/parent-macguffin-20261011-01/) |
| A：共同世界原生执行 | PASS（有限实例） | Sabre 从真实快照生成计划，Evennia 执行、结算，再只读 DB 确认位置；见下表 |
| B：Farrell 原始代码准入 | SOURCE_COMPAT_BUILD | 原 JAR 缺类；原源码 Java 21 泛型推断失败。仅忽略目录副本的一行显式泛型参数兼容修改，全量编译；原 checkout 未改 |
| B：原始输入重放 | REPLAY PASS | 五轮 prompt 严格匹配；输出 search/transcript 与上游历史 run-1 **逐字节一致**。这是到五节点上限的历史输入重放，不是找到新解或论文整体实验复现 |
| B：本地 Qwen 新模型 | NOT_LIVE | 两次短 completion；第一次客户端失败未保存响应，第二次 313 tokens、两条建议均缓存 miss。没有 embedding 请求或新模型搜索 |
| C：LLM 多层规划候选 | NOT_IMPLEMENTED | 不为赶比较而临时另造算法，也不以手工控制轨迹充当 C |

原始 B 的新建议需要原 `text-embedding-ada-002` 向量空间；没有可用凭据/本轮新的付费调用授权。换本地向量模型或字符串距离会改变方法，不能静默替代。Gramma 缓存也不能用作天气共同域的向量缓存。因此本轮**没有可解释的 A/B/C 性能对照，不能回答 LLM 增量是否存在**。[B 运行及失败账本](llm_search_guide/REPLAY_AND_PREFLIGHT.md)保留版本、两次调用、哈希、成本和先前一次错误预算诊断。

## 共同 Evennia 世界：同规则规划—执行—修复

3 个房间、A/B/测试玩家；离散小时 0–48，H2 暴雨由世界触发。移动只受实际 Exit/通行条件约束；天气不偷偷禁止人物出行。`look` 后的房间属性读回才建立天气观察。会面是原生自定义命令结算的事件；只有暴雨且 B 事前已观察暴雨的会面满足作者目标。

这是明确授权的联合编排模式，**不是两个自主 NPC 的策略实验**。人物 utility 是显式 fixture 偏好；`known_storm` 是回执派生的窄谓词，不声称完整信念模型。天气、观察、会面的物理合法性与作者目标条件分开。[场景规则与命令](shared_world/README.md)。

所有共同域搜索使用同一原生 Sabre v0.8.0、`bf/t/h+`、epistemic limit=1、200 visited / 5000 generated / 5000 ms、author-limit=48、目标 utility=1、Java `-Xss8m`；每次进程 watchdog=12s，外层调用 timeout=20s。配置、problem、完整 stdout/stderr 与预算状态逐次保存。**不是 h=0 UCS**；B 的 v0.7/LLM 成本也不能与 A 的 v0.8 节点数直接排名。

| 原生运行 | 原始 planner 结果 | 真实世界结果 |
|---|---|---|
| [clean](shared_world/runs/p0-sabre-clean-20261011T060145Z-f58e8a/run.json) | 18 visited / 264 generated，utility=1 | A 到旅馆→A 等待至 H2→B 观察→B 到旅馆→会面，H5 完成 |
| [clean 主代理独立复跑](shared_world/runs/p0-sabre-clean-20261011T060159Z-297200/run.json) | 同一五步计划，18 / 264 | H5 完成；20 个顺序事件，真实 DB 位置一致 |
| [封主路后重规划](shared_world/runs/p0-sabre-mainblockedrepair-20261011T060203Z-bb72ed/run.json) | 先执行 clean 原计划前两步；封路至 H3 后 10 / 71，utility=1 | A 已到旅馆及 H2 sealed prefix 保留；B H3 观察、走侧路；H7 完成 |
| [封全部路负控](shared_world/runs/p0-sabre-allblockednegative-20261011T060229Z-3709cf/run.json) | 同一真实前缀；重规划原生 `No solution exists`，0 / 0 | H3 停止，没有执行空计划、没有会面、没有伪造成功。标签 `REPLAN_NATIVE_NO_SOLUTION`，不是预算超时或任意游戏不可达证明 |

主代理逐项核验：grounded tokens 与实际提交逐步一致；所有计划动作 accepted/settled/prediction_matches；时间和事件序号单调；B 观察先于 qualifying meet；H2 天气事件不创造观察；封路未改 deadline、A 已到达位置或 sealed prefix；三组最终位置与独立只读 SQLite 查询一致。恢复场景最终 A/B 对应 DB location #3565，负控 A=#3575/B=#3573；独立 clean A/B=#3555。数据库核验只读，不从另一进程改世界。

另有三组明确标记 `SCRIPTED_CONTROL_NOT_PLANNER_OUTPUT` 的手工动作对照，不能用于宣称 Sabre 规划结果。合成文本 fixtures 同样不是实际历史前缀；只有上表真实 snapshot→plan→execute 的记录证明接缝。

## 失败、环境与回归

- Sabre 默认 1 MiB 栈编译共同域时 `Error: null`；独立异常诊断为 `StackOverflowError`。保留[失败与 stack trace](sabre_baseline/evidence/shared-clean-default-stack-failure-01/)，各共同域统一显式 8 MiB 栈；未改 Sabre 算法。
- 早期手工封路运行发生 Exit 属性适配错误；修复后重载服务。保留[恢复的失败部分账本](shared_world/runs/p0-handtrace-mainblockedrepair-failure-recovered-20261011T060107Z.json)，不把适配缺陷当成熟方法失败。
- 原始 B 的 JAR/源码失败、shim 调试失败、历史缓存重放与 Qwen 新响应分账；完整上游源、模型、JDK、向量和长 transcript 留本机 ignored 路径。Sabre 官方 GPL-3.0；B 仓库未发现许可证，公开仅自有薄适配、派生元数据和审计，未复制整套源/JAR/向量。
- 主代理本机回归：Sabre wrapper **5/5**；共同域投影 **7/7**；已有 P3 **53/53**。新增 CI 仅跑两组离线 Python 契约，不冒充下载 Java、原生 Evennia 或 live LLM 的远端复现。exact-head CI 状态以 GitHub 对应 run 为准。
- 附加[时间／观察边界记录](shared_world/runs/p0-boundary-clock-observation-20261011T060439Z.json)：H1 观察 clear 后世界 H2 变 storm，角色不自动获知；48 次有效等待后拒绝 deadline 上继续等待。保持原规则，不为该负控增加规划能力。
- 现有 `repo_health_check.py --top 5` 正常退出、有 6 个 warning（忽略目录第三方包大小、旧原文重复）；不是文档或算法语义验收。
- 未修改冻结 C++ Runtime/Dynamics、旧 E0 固定预算或 P5 结果；开始时已有的 CMake/paired continuity 脏工作原样保留且不随本轮提交。Java 与模型依赖都项目/本机局部，未安装 VM 或全局 JDK；Evennia 保持原数据库、后台运行。
- 本地 Qwen 服务本轮临时启动后已停止，恢复开始前状态。方法 preflight 两次调用之外有一次独立 transport readiness probe（16 prompt / 3 completion tokens）；它不是算法输入，不混入两次方法调用的结果。无云端 API 或 embedding 请求。

## 本轮收口与下一步

原始基线 A 与真实游戏接缝、历史 B 回放已达到可独立审阅的小检查点；**B 的实时向量资源准入、共同版本/目标/预算公平对照、C 的方法选择仍未完成**。不继续扩游戏、人物心理模型或完整 Director。若继续，先决定取得原 embedding 资源或明确标记重新嵌入变体，再以很小的同域试验验证，不能直接扩大 benchmark。

de Lima 等人 2023 已按用户确认加入[系统级强近邻](../../01_文献/算法积木/06_P0原始规划路线_2026-10-11/Abstraction_and_MultiCharacter.md#2023-system-identity-identified-mechanism-not-audited-here)：身份/作者摘要已核；POPF 分工、剧情偏离检测、世界干预、反馈与作者工具仍待全文定向核对。尚未确认完整开源实现，不阻断本轮 Sabre 实跑。[Fisher 抽象机制与 B 源码机制](../../01_文献/算法积木/06_P0原始规划路线_2026-10-11/README.md)分别记录，不凭这些准备材料宣称新多层规划器已成立。

复跑入口：[Sabre 原始 CLI 薄适配](../../tools/planner_p0_v0/sabre_baseline/README.md)、[B 离线 replay shim](../../tools/planner_p0_v0/llm_search_guide/README.md)、`python tools/planner_p0_v0/shared_world/planner_runner.py --case clean|mainblockedrepair|allblockednegative`（先启动已有 Evennia；三个 case 分别执行，不把 `|` 当 shell 命令）。
