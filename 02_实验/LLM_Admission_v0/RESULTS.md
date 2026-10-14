# LLM-Admission v0｜真实调用成立，E 绑定未通过

基准 `webgpt-sync@90ee524ec6f908acc2ee4663b05ca4d70cdbd357`；2026-10-14 单轮开发准入。**DEVELOPMENT / AGENT_CONFOUNDED / READY_FOR_INDEPENDENT_REVIEW，停止，不自行 CLOSED。**

本轮实际调用 native `gpt-6-luna`：1次极简准入 + E/G各1次语义推理，0重试。Luna是被测对象，不是代码助手；主控准备、校验和保留证据。E的原样候选不满足冻结契约，故 **UCS未运行、原版任务执行0次**。只有准备信息包时的原版新会话 `n` / `seed 20261014` 两条启动输入，不能算模型任务运行。

## G1–G6

| Gate | 实际结果 | 证据/边界 |
|---|---|---|
| G1 共同规则 | 有限规则完整；文本与后台明文等同性非独立可核 | [structured packet](shared_rules.json)反向展开逐实例等同326操作；14房间、3物品、45行/174别名及全部动作族。转录文本的地图行核对与族计数见[fairness](requests/fairness.json)；其余文字前提/效果手工核对，不称自然语言等价证明 |
| G2 Luna身份 | 真实调用 PASS；隔离不是 PASS | 三份runtime `turn_context`均为gpt-6-luna/medium；fork_turns=none请求参数有记录，实际工具调用均0，但工具权限和自动注入指令未关闭 |
| G3 E绑定 | **FAIL / INTERFACE_SEMANTIC_MISMATCH** | [原样输出](calls/e/response.raw.txt)，[固定验收](e_validation.json)：实际Goal4原子，缺最终bridge；同时保留no-death硬监测义务及硬残留；没有主控补全 |
| G4 G缺口 | 有用的定性分析，格式部分偏离 | [原样输出](calls/g/response.raw.txt)、[父级审閱](g_review.json)：明确生产/归因、持续更新、后续消费和证据边界；missing_capabilities返回字符串，而非请求的objects。不是独立全文源码发现 |
| G5 UCS/原生 | **NOT_RUN_BINDING_REJECTED** | 不把拒绝候选替换成GOALS["E"]。薄注入接口的mock测试确实捕获同一个external Goal进入UCS，但不是模型执行成功 |
| G6 保存/停止 | 已交付待独立复核 | 请求、原样输出、模型/工具/用量、共享规则、启动原始账本、失败及测试保存；没有扩题、调提示、换模型或改变游戏 |

## 实际输入与环境

完整主控请求转录：[probe](requests/tested_luna_admission_probe.txt)、[E](requests/tested_luna_semantic_e.txt)、[G](requests/tested_luna_semantic_g.txt)。同一共同前缀保留在[common_request](common_request.txt)，目标段不同。实际调用参数/时间/ID见同目录JSON；原始共享导出哈希见[manifest](packet_manifest.json)。静态先验与实际玩家观察分开；[visible_start](visible_start.json)保留完整合法启动文字与未知事实；[启动原始账本](runs/7f03a137938b4e94a8f2f33997c6a63d-20261014T092930Z-2ad9b6/events.jsonl)只有两条setup输入。

主控没有给GOALS、人工谓词答案、旧搜索计划、成功回放或walkthrough；所有有限地图边、HERE变体、可逆晶桥操作、钥匙/灯/杆先验和非原生保守灯光限制均提供，不只给正确路线。海盗生产/消费审计也是共享的已知线索，故G回答不能当独立发现未知机制的证据。当前NPC位置/flags、随机游标、灯能量/closing等隐藏值未提供；模型不享有全游戏状态。

**本地runtime把子任务正文及父spawn的message加密保存。**不能从日志独立恢复后台实际plaintext，不能伪造解密结果。公开全文是主控对本轮实际调用文本的转录；调用参数、密文SHA与原样最终输出有独立runtime来源。文本一致性检查只核对这份转录，**不声称它与后台plaintext密码学验同**。首次提取过程与完整会话留私有；公开只保留必要指令指纹，不发布个人AGENTS内容。

`fork_turns=none`没有传主控长对话，但同workspace、工具、Codex developer与个人AGENTS/环境仍被自动注入，且有不可观测部分。无工具调用不等于无工具权限，更不能排除预训练已知Adventure答案。E本来就是公开开发题，不是新题泛化。可见自动指令只做角色/长度/hash指纹；后台完整隐藏系统提示、模型权重和服务端预处理 **NOT_OBSERVABLE**。

### 模型与用量（runtime报告，不是计费单）

| 调用 | 子session ID | input / output tokens | cached input | observed tools |
|---|---|---|---|---|
| probe | 01a139b5-f8ce-7583-9775-cd2148945916 | 43850 / 17 | 17152 | 0 |
| E | 01a139f1-bf26-7902-8816-bd90f44000ad | 46187 / 751 | 17152 | 0 |
| G | 01a139f2-9ac3-71b2-a580-13e4bc497ec4 | 46249 / 814 | 42752 | 0 |

三次均openai provider、CodexDesktop `0.162.0-alpha.17.2`、实际reasoning medium。E/G reported reasoning分别240/231，未将其再加进total而重复计数。合计input136286/output1582，reported total137868；高input包含明显的Agent/harness上下文，不能当作纯实验信息包token量或裸模型推理成本。缓存并不是使用旧模型回答，本轮有新的实际生成；美元成本不可取得，不编造。

完整限定审计：[probe](calls/probe_verified/audit.json)、[E](calls/e/audit.json)、[G](calls/g/audit.json)。模型标识来自runtime而非模型自报；后台权重身份仍未知。

## E究竟哪里没通过？

模型实际生成：`at(player,WESTBANK)`、`carrying(keys)`、`carrying(lamp)`、`lamp_on`；`bridge`出现在bindings和解释中，**没有进入实际Goal.required**。它解释“建立桥”是中间过程，原句未要求最终桥仍在。另将`no_death_ever`同时写成hard trajectory obligation和hard residual。冻结检查要求最终bridge且不含未落实hard residual，所以拒绝；不补原子、不删残留、不重试、不修改gate刷PASS。

**不能把这直接解释为模型不懂晶桥或漏读生存。**原文“建立”与人工最终状态gold的时间语义不完全相同；已可监测但尚未运行验证的义务，与缺少游戏能力的未绑定义务，也尚未在最小输出契约中充分分开。这是语言解释与验收接口的真实分歧。既保持本轮FAIL，又将这个测量局限置于前台；不事后改判，也不从一次失败推断一般规划能力。

若以后继续，优先由独立审阅决定：作者要“曾经建成桥”还是“最后桥仍存在”；no-death应是可执行待验证义务还是不可绑定残留。下一协议可以明确区分，但不可回写本轮提示、原样输出和失败。**本轮不发起下一模型调用。**

## G究竟贡献了什么？

它没有编造`trust(pirate)`或声称真实帮助已经发生；将要求拆成帮助事件与施助/受益归因、跨经历持续更新、后续行为读取与改变、以及“逐渐/持续”的可检验语义。明确已审计海盗逻辑消费的是宝藏、灯和进度，reset seen不自动等于信任；也承认有限字段缺失不能证明全游戏绝对不存在。这是**基于给定审计的有用需求分析**，不是新社会算法、完整原版机制考古或人工质量盲评。

## 工程/测试与保留范围

- 本轮新增独立目录下packet、审计、严格解析、绑定与限定证据工具；只给B0控制器添加external Goal/text/output-root注入。默认D/E/G、domain/search/observe/verify、P1、原版游戏、C++、E0及历史结果不改。
- 注入接缝测试传不同于人工E的Goal并截获UCS实际对象；拒绝候选测试确保不会调用原生执行器。mock测试不算真实episode。
- 最终离线检查：**36/36**（11新准入 + 9 B0 + 16 P1）；[原始测试日志](parent_unit_tests_final.log)。冻结4个核心文件SHA从90ee524读取后固化断言，CI无需旧Git历史。
- 初次证据抽取漏识别`phase=final_answer`、本地任务正文加密和测试替身不完整曾导致工具检查失败；均属于父级记录工具/测试问题，**没有产生新的模型调用**。排查原记录保留私有，不用其替代最终证据。
- CI只验证离线契约，不重新调用Luna、不下载游戏、不证明任务执行成功。exact-head流水线以[Actions](https://github.com/2003SINGER/character-dynamics-lab/actions/workflows/runtime-regression.yml)为准，提交时不预先声称全绿。
- 全部完整对话私有归档，原附件核验后放可恢复废纸篓。原版源码/资源/二进制不推送，沿用[Open Adventure NOTICE](../OpenAdventure_Native_v0/THIRD_PARTY_NOTICE.md)。原有无关dirty不入本提交。

## 回答本轮八个问题及科研判断

1. 真调用Luna：是，有3个独立子session/实际model标识和原样输出；非主控mock回答。
2. 指令影响：Codex工具/环境/个人AGENTS等已知自动注入，不公开内容；后台不可见指令未知。
3. 仓库/工具权限：存在、不能关闭；实际3次均0工具调用。
4. 知识公平：完整冻结有限规则/先验与安全限制均提供，海盗审计也提供；实际隐藏值不提供。文本核对及后台加密明文局限如上。
5. 独立谓词：4个最终原子；bridge降为中间，no-death保留但硬残留阻止准入。
6. 是否不补答案进入UCS：否，本轮候选拒绝；代码接缝mock验证成立，不混成模型成功。
7. 原版执行与预期：任务执行未开始，只有2条准备输入；不虚构成功/失败动作。
8. 能力缺口：G给出具体producer/attribution/update/consumer要求，保留硬性与证据范围；格式偏离和非独立发现如实保留。

**结论：真实Luna-in-Codex准入成立，首次语义绑定未通过，G缺口分析有用；没有模型优于B0的证据。**本轮完成交付并停止。下一步是审阅时间语义与残留义务契约，而不是扩大游戏、调模型、改传统搜索或立即做排名。

模型调用边界参照官方[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)与[API多Agent文档](https://developers.openai.com/api/docs/guides/responses-multi-agent)：上下文/模型/工具/系统指令是不同控制面。API能力不能冒称本机spawn工具可用参数；本机是否可禁工具以实际schema为准。本轮使用OpenAI Docs skill核对这一区分，具体身份以本地runtime证据为准。
