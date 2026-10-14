# Open Adventure B0：首次原生因果规划结果

2026-10-14。**DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW，本轮停止，未自行 CLOSED。**
完整三方法研究仍为 **PARTIAL**：用户本轮明确只完成传统基线，B1/B2为`DEFERRED_BY_USER`，没有实时模型调用、缓存代替或LLM增益结论。

## 这次实际证明了什么

经典前向 uniform-cost search（`h=0`）在一份源自原版规则的有限模型中，组合出行动过程，再逐条交给未修改的 Open Adventure 1.22 执行。开发目标、恢复负控、冻结过桥目标均得到原生最终地点/背包/状态证据。没有目标专用HTN方法、预存正确命令序列或规划器自行结算世界。

但是作者要求仍由开发者手工绑定成谓词；模型有14房间、3对象的公开地图/初始配置先验及保守安全条件。它不是盲探索、全游戏最优规划、通用自然语言绑定、长期NPC系统或原创算法。协议和信息权限见唯一[PROTOCOL](PROTOCOL.md)，源规则核对和适配失败见[VALIDATION](VALIDATION.md)。

## 固定结果与成本

任务输入包括行动、观察、已知原生问题的回答及显式负控注入；每段另外2条启动回答/seed输入。输入请求不等于游戏tick。耗时为本机单次搜索累计观测，不能作统计加速结论。

| 条件 / 分账 | 原生目标判定 | 任务输入 | 搜索调用 / 扩展 / 生成后继 | 累计搜索秒 | 原始入口 |
|---|---|---:|---|---:|---|
| D开发，最终代码 | PASS：BELOWGRATE、keys/lamp持有、灯亮、无死亡 | 10 | 8 / 1,163 / 15,491 | 0.111 | [结果](development_final.json) |
| D恢复负控，修正后 | PASS：真实拒绝后重新搜索恢复；同一目标最终成立 | 24 | 15 / 1,689 / 22,593 | 0.165 | [结果](development_feedback_final.json) |
| E冻结目标，仅一次 | PASS：原生晶桥、WESTBANK、keys/lamp、灯亮、无死亡 | 17 | 15 / 39,404 / 487,410 | 3.818 | [结果](evaluation_first.json) |
| G语义缺口 | UNSUPPORTED_SEMANTICS：未注册信任/受助归因/后续消费链 | 不运行游戏 | 不搜索 | 不适用 | [缺口结果](semantic_gap.json) |

E的39,404是15次搜索扩展的**累计数**，不是突破单次10,000上限。预算、seed、目标和动作规则没有因结果调整。每条原生段的源码/二进制前后核对均不变；P1最后close是进程清理，不是游戏通关，目标判定在清理前完整原生观察上作出。不能拿清理退出码证明成功。

### 真正的决策与反馈

- D/E的下一条输入均取自通用UCS的当前计划；完整预测计划、来源与成本写入`b0_trace.jsonl`，真正输入/字节/响应写入`events.jsonl`，预测从不充当真实证据。
- 恢复负控先由测试控制器用原生输入把钥匙放回building，故意延迟这些可见反馈。旧计划的`unlock grate`真实返回`You have no keys!`。这次原生拒绝是第14输入；随后回答已知hint问题、补交之前真实输入/响应、look/inventory刷新；**新搜索**产生后续`build → enter → take keys → …`，不是恢复程序写死的路线。
- 这是假定输入流滞后的显式开发负控，不是自然NPC扰动，也不证明普遍在线修复。未知问题、未建模NPC变化和无法辨认的反馈仍有停止边界。
- G是开发者核查的机制注册缺口与保守拒绝，不是模型自行发现了全部游戏语义。不能由有限模型缺一个字段，就证明任何游戏都没有该能力。

## 全部运行证据（不覆盖失败）

| 运行 | 原生输入/输出 | 搜索、候选、反馈 |
|---|---|---|
| 首次D，修hint前已成功 | [events](runs/oa-b0-D-clean-309b4a16b3-20261014T073230Z-b76a69/events.jsonl) | [trace](runs/oa-b0-D-clean-309b4a16b3-20261014T073230Z-b76a69/b0_trace.jsonl) |
| 首次恢复负控，失败保留 | [events](runs/oa-b0-D-feedback_negative_control-bf215f0af7-20261014T073359Z-17e3a7/events.jsonl) | [trace](runs/oa-b0-D-feedback_negative_control-bf215f0af7-20261014T073359Z-17e3a7/b0_trace.jsonl) |
| 修正后D | [events](runs/oa-b0-D-clean-b72659bde4-20261014T073838Z-5e9dde/events.jsonl) | [trace](runs/oa-b0-D-clean-b72659bde4-20261014T073838Z-5e9dde/b0_trace.jsonl) |
| 修正后恢复负控 | [events](runs/oa-b0-D-feedback_negative_control-84cb07d4ce-20261014T073838Z-9c8d29/events.jsonl) | [trace](runs/oa-b0-D-feedback_negative_control-84cb07d4ce-20261014T073838Z-9c8d29/b0_trace.jsonl) |
| 冻结E，仅一次 | [events](runs/oa-b0-E-clean-726b86305d-20261014T074046Z-8baf7e/events.jsonl) | [trace](runs/oa-b0-E-clean-726b86305d-20261014T074046Z-8baf7e/b0_trace.jsonl) |

首次负控状态`MODEL_MISMATCH`、14任务输入，独立目标判定`INDETERMINATE`：原版在解锁失败后提问`Are you trying to get into the cave?`，旧控制器未处理回答窗口，look/inventory被拒绝。只修正这一原生输入模式；不改Planner规则/预算/种子，不覆盖[失败摘要](development_feedback_first.json)。[首次D摘要](development_first.json)也保留。开发运行期间的源码差异以各trace开头记录的hash为准；最终三条成功段的协议和五个实施文件hash均与交付源码一致，base Git revision为`c852968`，不是尚未生成的交付commit。

## 传统基线与独立验收

- [代码](../../tools/open_adventure_planning_v0/README.md)：透明自实现的经典UCS，不宣称第三方完整GOAP/HTN复现。14房间、45移动行、174别名、326 grounded operator实例；模型、观察、搜索、独立验证、控制器共1,042行，连同初始化/9项测试共1,172行。代码规模不等于人工工时；本轮未记录可靠人时，不编造建模成本数字。
- 来源核对：逐一对照上游YAML词汇/移动目的地，174别名无不合法源边；前提、双向效果、HERE及灯光安全另核。先验/安全子域的额外知识必须同样给未来B1/B2，不能把B0称为仅凭玩家观察探索。
- [父级回归](parent_unit_tests_final.log)：**25/25**（9 B0 + 16 P1）。另做非D/E合取目标“携灯回START”的通用搜索核验，得到3步单位成本计划；不是评价题专用查表。
- 独立判据不导入搜索或预测模型，重读原生完整字节；历史目标前缀、后续位置/库存变化、坏字节/缺证据、死亡复活不能PASS。父级再次读回最终三条段均PASS。
- 这是Luna实现加父级AI源规则/执行核验，不冒称独立人类评价。CI只验证离线契约，不下载游戏，不替代这些macOS原生记录；exact-head结果由GitHub Actions核对。旧E0-H02失败与本轮无关，不改它的预算。

## 科研判断与停止

当前有限规则下，传统搜索已经解决两个不同目标及限定反馈修复；**尚未发现需要LLM才能补全的因果搜索缺口**。不应将加一层LLM或HTN预设为收益，也不能据一题单次成功推断传统方法足以覆盖开放游戏。

仍未回答：抽象作者要求的可靠绑定、域外/未知规则的建模成本、随机NPC扰动、丰富社会历史、多线作者控制。下一轮若用户重新授权模型，最值得对照的是在共同规则/先验/预算下，LLM究竟减少了绑定劳动还是增加了未经执行的叙述；本轮不实施、不自动扩题或调提示。

原文私有归档、原附件已移入可恢复废纸篓。公开限定代码、协议、摘要、短游戏文字与原始轨迹；许可证归属沿用[Open Adventure NOTICE](../OpenAdventure_Native_v0/THIRD_PARTY_NOTICE.md)，不推上游完整资源/二进制/私有对话。P1代码、原版游戏、旧Evennia、C++、E0和main未修改；无关原有dirty保持不动。
