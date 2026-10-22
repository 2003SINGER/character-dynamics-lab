# Online Playtest v1 — 在线作者干预

2026-10-22；基线 `39f90e6`；状态 **DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW**；本轮停止，提交独立审阅。继续现有多角色 Controller，不另立平台或研究准入阶段。旧多角色结果与 Judge 评价保留，不回写。

本轮只推进一个完整迭代：修复已证实的原生交互/持续活动问题，将作者期限用于未来派发协调，提供复用 JSONL/现有 AST 的交互 CLI；同一持续世界中由操作员查看实际状态后临场加入并编辑未来要求，再由新上下文 Judge 盲审真实行为。主级代理担任 `AGENT_OPERATOR`，不冒充真人作者或玩家体验实验；不打开游戏客户端，不调用 LLM 规划服务。

保留角色 433/476、原生随从 442 及既有 G0/G1 `recon-v1` 能力。不得新增剧情技能、放宽距离与驻留规则、瞬移或伪造效果。过去作者期限明确阻止相应 DIRECTOR 新派发；合法 ACTOR 活动、实际历史和在途动作不因编辑重置。未过期但耗时不确定的义务保持不确定，不把导航/HTN heuristic 当作游戏秒数。

并行分工：A 原生执行与交互修复；B 作者协调与 CLI；C 只读旧轨迹的时间消耗和行为优先级。使用全新 Source-A 副本与输入快照完成两次真实运行：首轮在 68.07 秒、提交 5 个请求后因 CLI→runner 命令 schema 接缝错误退出；修复后完成一次有界验证。第二次运行结果如下；本轮停止，不继续补跑。既有 720 秒运行、30 请求、20,000 记录、64 MiB 输出与 6 GiB 可用空间保护保持不变，没有放宽规则或反复刷通过。

## 实现与操作

原生修复有两处：交谈结束回调按捕获的 `request_id` 核对当前 lease，防止旧动作把替代请求误写为失败；会合的原生 goto→hold 在漂出原到达半径后重新进入 goto，而不是永久 idle。原有 TTL、危险响应、半径与驻留规则保留；这不保证每次交谈都有 speech，本轮仍保存了一次无 speech 失败。

在线操作由 `process_runner` 读取预先存在的空 operator JSONL；存在 `--author-input` 时禁用 `RUNNER_DEMO`，不预置作者命令或触发时刻。操作员顺序提交命令；编辑需等上一条命令已应用并产生 checkpoint。同一批中先 append v1 再 edit v2 时，v2 会因按尚未应用 v1 的 session 校验而被拒；接口不是批量事务，也不支持并发写入。每个 controller cycle 最多应用一条命令，编辑只影响未来要求，不撤销已结算历史或取消原生在途动作。`show` 读取最近已写入的 decision/view，可能滞后一轮，也不显示尚待应用的输入队列。已知局限：计划 `plan.status` 还可能落后于最新 decision 摘要；核对状态应同时看最新已写入 decision，当前不修此展示差异。CLI 的退出不是服务器关闭操作。

复用入口（下列路径与 run ID 是占位符，不指向本轮私有产物）：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -B -m tools.character_dynamics_online_v0.process_runner \
  --freeze <private-freeze.json> --run-id <new-run-id> \
  --author-input <precreated-empty-author-input.jsonl>

_local_data/native_platform_v0/evennia/venv/bin/python -B -m tools.character_dynamics_online_v0.author_cli \
  --run-dir _local_data/veloren_online_integration_v0/<new-run-id> \
  --author-input <same-author-input.jsonl> show --section all

_local_data/native_platform_v0/evennia/venv/bin/python -B -m tools.character_dynamics_online_v0.author_cli \
  --run-dir _local_data/veloren_online_integration_v0/<new-run-id> \
  --author-input <same-author-input.jsonl> append-rally \
  --goal-id live-rally --actor-uid 476 --marker B --follower-uid 442 --deadline 270

# 确认 goals 中上一版本已应用，再用同样前缀调用：
# edit-rally --goal-id live-rally --actor-uid 476 --marker A --follower-uid 442 --deadline 270
```

离线测试使用既有 Evennia venv（依赖 `gtpyhop-core==2.0.2`）：`_local_data/native_platform_v0/evennia/venv/bin/python -B -m unittest discover -s tools/character_dynamics_online_v0/tests -v`。不需另装依赖。

## 首轮集成失败与修复

首次 freeze 前，patch 导出期间的哈希不匹配被启动前校验拦下，未创建 run 目录或启动 server；随后用最终 patch 与新 freeze 重新核验。第一次实际运行在 CLI 输入触发后 68.07 秒终止：CLI 的标准化 `source=AUTHOR` 字段混入 core 要求的精确五字段 command，形成六字段并触发 `ContractError`。这次真实运行与其输入保留，native code 0 不代表任务通过。修复后，CLI→parse→`step_process` 跨接口测试通过，整套包测试为 67/67；重试改用全新 Source-A userdata 副本，不复用已运行副本。原生 G1 r3 是交互修复实现，规则、距离/驻留阈值及技能范围未改变。该失败与其修复和下面第二次运行结果分别记录。

公开范围仅代码与报告；原始轨迹、作者输入、配置、快照、存档和 Judge 原文仍留本地。本报告概述独立 Judge 初评及事实勘误，不复述私有原文；既有 C++ Runtime、F0/F1、历史实验和 main 不改。

## 第二次真实运行与停止

第二次运行正常按主级 SIGUSR1 监督流程停止：515.682 秒、7 个请求、0 个在途请求；停止不表示所有目标完成。7 个请求中，原生 hire 1 次，G1 有 5 次结算、1 次失败。442 受雇于 8.826469；433 对 A、B 的 survey 分别于 5.042493、15.831303 结算。首次 A delivery 于 107.605 接受、183.662 以 `native_talk_completed_without_speech` 失败；B delivery 于 185.371967 结算。ACTOR 来源的 Rally-B 在 185.811 请求、185.997 被原生接受，并于 197.414856 结算；A delivery 重试于 345.406188 结算。失败原因按原生终态记录，不推广成所有交互均已修复。

在线 CLI 在 game time 29.800 应用 expired-probe（deadline 0），没有产生对应 DIRECTOR 原生请求。live-rally B/v1 于 76.8515 应用，随后在 135.1157 编辑为 A/v2；deadline 270 保持不变。编辑保留既有历史和在途 A delivery、未失效的 B delivery 节点。最终 A 未产生会合请求，目标没有得到满足；监测保留 `UNKNOWN` / `EXPIRED`，不写成 `SAT` 或 `VIOLATED`。B 的实际 delivery/Rally 成功路径来自 ACTOR，不是作者命令。全程没有 DIRECTOR 原生请求，因此本轮只证明在线输入、版本编辑与期限拦截/保留行为，不证明作者修改改变了世界行为。

本轮 Python 测试 67/67、旧 decision 测试 54/54、旧 Talk 测试 25/25 通过；Rust 检查/构建完成，2 项聚焦测试通过。这是一条新运行轨迹（n=1），不是匹配性能对照。首次真实运行的失败保留，不能由此次运行概括为“所有交互失败均已修复”。

Judge 初评摘要：认为表现有一定效果但不完整，认可巡察、报告、招募与会合链；但没有证据表明作者编辑驱动了实际目标行为，优先建议用目标版本到实际动作建立因果证据。这不是人类体验或画面评价。勘误：Judge 自行撤回了对 hire 发生过晚的初始判断；核对原生行后，hire effect 为 8.788、job/terminal 为 8.826、下一观察为 9.207，早段已 Following，因此不采纳“迟聘”结论。初评与勘误原文仅私有封存。

开发者对照：现有请求已记录 ACTOR/DIRECTOR 与作者版本，断口并非仅缺日志标签，而是本次作者 A 约束没有在期限内促成相应执行安排。后续应先审阅这一协调失败及交谈延迟，不以补一个成功事件或继续刷跑代替问题解决；本轮到此停止。

工作包以 `DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW` 停止；Judge 初评及勘误已摘要记录，不标 CLOSED。r3 是按三项基础补丁顺序之后应用的累积 G1 修复补丁，替代旧 r1/r2、不可与其叠加；它没有新增 G1 技能或改变规则、半径/驻留阈值。复核锚点：Veloren source `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`；[r3 patch](../../tools/character_dynamics_online_v0/veloren-g1-recon-v1-r3.patch) SHA-256 `4ca3fc31252f96be0e7d5bb328a28cb25707c6e6d29f4074c8170b74d541a01a`；native binary SHA-256 `ea7437da769c95f2e7532bf4cdd9f35979ba4b20f8be832d5dcf622b7fc9c474`。原始输入、轨迹、配置、快照、存档和 Judge 原文均仅本地保存，公开范围仅代码与本报告。
