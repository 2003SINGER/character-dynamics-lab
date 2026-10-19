# Multi-Actor Process v5 — 结果与边界

**状态：DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW；本轮停止扩展并提交独立审阅，完整过程未通过。** 2026-10-19 的单次有界运行证明了真实多角色计划、作者版本更新、两次跨角色报告交付及其后续协调派发；没有完成两处集结，也没有满足全部作者义务。运行原始记录、配置、快照与逐条证据均留在私有本地数据区，不在本报告公开。

## 本轮结果

- 单一 Veloren server 进程，实际 wall 725.44 秒（720 秒运行上限及关闭余量）；9 项请求（8 项 G1、1 项原生招募），结束时无 inflight。输出记录 1,406 条角色观察；G1 请求 8 accepted、4 settled、4 failed；出现 2 次原生 speech emission。
- 原生 G0 招募成功：头目 476 招募 NPC 442（game time 7.8166）。招募和 Hired/Following 仍走原生规则。
- G1 `recon-v1` 的两个地标巡察均真实结算；巡察员 433 将 A、B 记录分别交付给 476，结算距离分别为 5.772 m、5.714 m。A 的原生 speech emission 与接收侧知识写入均有确认，作者交接义务达到 SAT。
- 作者输入经 `RUNNER_DEMO` 生产器按独立控制周期写入：g1 作者目标、A 集结期限、再将未来集结地点编辑为 B。真实历史与版本前缀保留；不是人工 `LOCAL_AUTHOR` 交互测试。
- Director v2 的 B 集结请求于 game time 461.220 实际派发并被 G1 接受，晚于约 245.185 的绝对 deadline，随后 TTL 失败；A、B 集结均未结算。相应事件监测输出 UNKNOWN 是因为 coverage 不完整，不代表期限仍可能满足，也不能冒称 SAT/VIOLATED。
- 集结失败体现一个具体的原生执行生命周期断口，而非 HTN 算法能力结论：B 运行中 game time 470.73 的采样显示头目距地标约 2.91 m、随从约 47 m；TTL 到期时随从已距头目约 4.85 m，但头目已距地标约 29.6 m。到达后未保持位置以等待随从；原生 brain 显示 interrupted/idle，G1 lease 下控制活动停止。此结果说明当前“移动到点”不保证“保持到同伴到点”。
- 另有两次未产生 speech 的失败，当前分支 telemetry 不足以归因；旧闭包覆盖新 lease 是候选解释之一，但未证实。不得将其归为 NPC 固有拒绝、规划器限制或已查明的某一 bug。

## 迭代与真实失败边界

本轮之前的两次启动预检分别暴露了错误随从身份选择、以及终态 `report_id` 延迟生成与适配器校验不一致；均在正式迭代前修正。v3 诊断运行发现 UID 命名空间不匹配，导致真实 speech 已发出但 G1 请求过期；v4 有界运行发现缺少接收者局部接触前提，重复派发消耗了请求预算。v5 加入独立 dispatch 前提、只在前提变化后重试、受控接收者 inflight 保护，并在请求预算耗尽时停止新派发而排空实际 inflight。此前运行与失败均保留，不能用 v5 覆盖或改写。

## 解释边界

- 结果支持：同一在线 controller 中两个外部角色均有自身多步计划；G1 规则有真实终态；作者多版本未来约束、真实交接后知识变化、Director v2 的 B 目标派发及因果前缀保留可在同一进程中衔接。
- 结果不支持：完整多角色/作者剧情过程通过；A/B 两处 Rally 完成；期限要求实现；NPC 长期自主生活；全局最优联合规划；相对其他方法有优势；任意作者请求均可实现。期限监测与版本维护可工作，不等于规划器已搜索动作时长、期限可行性或所有状态义务的联合可实现性。
- 规划使用逐角色、逐目标的固定优先级 HTN 细化，不是多主体联合搜索器。作者事件约束和真实终态由有限 selector/事件族表达；其范围不等于通用剧情语言。失败原因中有尚未区分的原生 G1 生命周期因素，不能外推为 HTN 的内在限制。
- 两名应用角色的 quota=2 是本应用的角色任务，不是原版 Veloren 海盗四人 raid 目标。原生 G0 Hire/Follow 与新增版本化 G1 巡察、语音交接、集结规则分开报告；G1 “交付”基于原生 speech emission，不声称接收者消费了完整对话或具备原版社会认知。

## 可复现范围与隐私

本次可运行的规则、状态投影、地标/角色计划模型和作者 AST/schedule 均由开发者显式建模；没有由系统自动发现规则或推导游戏语义。建模与接线的人工工时未单独计量。HTN 与作者约束的能力边界应按该有限手工模型解释。

Python 离线测试依赖 `gtpyhop-core==2.0.2`；测试命令：

```sh
python -B -m unittest discover -s tools/character_dynamics_online_v0/tests -v
```

该冻结版本测试 52 项通过。在线 runner 需要用户自行准备全新、隔离的 userdata 副本和对应 freeze；已运行副本不能重用或覆盖。复现命令模板及输入边界见工作包 [README](README.md)，本次具体私有路径、配置、快照与日志不公开。

Veloren 源码基线为 `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。本轮为 GPL-3.0 许可下的派生构建；G1 是明确新增规则，不是原版 Veloren 能力。复建补丁顺序为 [Native Talk](../../tools/veloren_native_v0/veloren-native-talk.patch) → [Native Decision](../../tools/veloren_native_decision_v1/veloren-native-decision.patch) → [Loaded Msg Repair](../../tools/veloren_native_decision_v1/veloren-native-loaded-msg-repair.patch) → [G1 r2](../../tools/character_dynamics_online_v0/veloren-g1-recon-v1-r2.patch)（SHA-256 `93b69d74eb0a134b32b442926a379cf9594ef8461408d9507ed11ae1be4a70fc`）。[G1 r1](../../tools/character_dynamics_online_v0/veloren-g1-recon-v1.patch) 是保留的早期失败修订；r1 与 r2 是替代的累计 G1 补丁，不可互相叠加。公开代码和报告不包含运行世界、原始轨迹、配置、源快照或私有输入；外部读者无法仅凭公开材料重放本次原始过程。代码和报告是唯一公开范围，不授权发布 raw 或脱敏证据。

## 后续边界

本轮提交 DEVELOPMENT / PARTIAL 结果供独立审阅；不自动启动新运行，也不重用本次 userdata。若后续继续，需先在明确授权下处理 G1 集结的到达后位置保持/随从汇合生命周期，并单独诊断 speech 失败归因；不能借此宣称更广的时序可行性或方法优势。旧 [RESULTS](RESULTS.md) 与 [PROTOCOL](PROTOCOL.md) 继续分别记录先前 v0 三组结果与其固定条件，不由本报告替代。
