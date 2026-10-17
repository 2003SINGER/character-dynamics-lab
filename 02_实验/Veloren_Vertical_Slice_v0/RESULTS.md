# Veloren Vertical Slice v0 — 阶段结果

记录范围：2026-10-16—17；本轮结果日期：2026-10-17。

官方 binary 来源：Veloren v0.18.0 GitLab macOS ARM64 build，commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。旧 `source_audit/` 的 GitHub `b2f1060df37ba4eb2eb001ac1b115beaf404f656` 仅作历史源码线索，不代表与 binary 同版。

10-16 环境阶段起点：`webgpt-sync@91ebd876cef823e8f8b69c07a0d1af941b6b5b56`，当时远端与本地一致。本轮从 `72a37c9` 继续。

当前状态：**`READY_FOR_INDEPENDENT_REVIEW / A=PARTIAL / A-Closure=BLOCKED_CANCEL_ADMISSION / B=NOT_STARTED_A_GATE`**。本轮诊断补丁已构建并测试，两个真实服务器均正常退出；取消负控请求被权威服务器拒绝，因此没有提交任何正向请求，Agent 边界仍未证明。已达到本轮停止条件，不继续修补、重启或进入 B，不自行 CLOSED。`3a82cd0` 的历史部分通过及无发言结果不改写。

## 2026-10-17 A-Closure：运行前固定边界

起点 `webgpt-sync@3a82cd0`；官方源码 `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`，旧补丁 SHA-256 `1ccf5c1db8d164743838b1bcb67a73adea88dd7a180f64c45b4c204c48097936`。审查原文仅私有归档于 `_local_data/source_archive/2026-10-17_veloren_a_closure_review/`，SHA-256 `6a4a2d75cfd292961e55c554be8800b1c5a9bb3d8ba5c9f41f5869ae6ee3116a`。本节在新原生运行前确定；最终补丁、脚本及配置哈希在编译、聚焦测试和静态审阅通过后记录，运行中不修改代码。

| 维度 | 本轮固定规定 |
|---|---|
| 允许修改 | request-scoped 原生 Talk 路线/已有 RNG 结果、Say 实际交接或原生过滤的只读观测；有界资格采样和文件 harness。无请求的行为分支、RNG 消耗、动作处理次序不变 |
| 源码/构建 | 原 nightly、Cargo.lock、官方完整 workspace；只构建 server-cli，`worldgen,persistent_world,plugins`，jobs=2；不开 GUI，不放松原生检查 |
| 世界与启动上限 | 同一原始保存世界、seed=130626853，两个独立新副本；**最多启动 2 次**：无请求基线一次、请求序列一次。重启不冒充连续轨迹，不增开第三次刷随机结果 |
| 基线 | 服务器 ready 后采样 60 秒；不配置请求输入，使用相同原生 persister 加载设置，观察原有 NPC 行为 |
| 启动/资格窗口 | 每次启动最多等待 ready/首有效样本 120 秒；每次候选资格等待最多 60 秒，耗尽即停止。不移动、生成或重置 NPC |
| 候选 | 优先真实 445→465；否则从原生 catalog 的已公布 Loaded 候选中，按新鲜 ECS **三维距离、sender UID、target UID** 排序，sender 取较小 UID。并非扫描所有 NPC 的统计抽样 |
| 资格 | 真实存活、双方 Loaded 且 Agent SPEAK 可用、3D≤8m、连续满足 5 秒、采样墙钟/游戏时钟年龄≤2秒；提交前重查。sender 无未完成 lease；只读追加采样最多覆盖既有 catalog 的8组候选所涉UID |
| 负控 | **1 次**请求与取消两行原子追加，确认 accepted→cancel_requested→cancelled_before_native_action，且无关联 Say/交接/Agent 效果；不成立立即停，不提交正向 |
| 正向预算 | **最多 6 次实际提交总计**；拒绝、无发言及提前结束均计数；独一 request ID，核对全部输入前缀，一次只保留一个未结束正请求 |
| 单次观察 | TTL=60秒；反馈最多80秒，随后20秒原生续行观察。未完成 lease 不提交下一次。没有完整链则在有资格且仍有预算时进入下一次 |
| 提前停止 | 首次同 ID 的真实 Brain→Say→Agent入队→emitted/blocked 完整链及续行证据成立，立即停止后续提交；或提交/资格/启动/资源预算耗尽后停止 |
| 遥测/资源 | 通过已有环境配置固定 `MAX_RECORDS=50000`、`MAX_BYTES=67108864`（64MiB）、`MAX_SECONDS=1800`；完整变量前缀为 `VELOREN_NATIVE_`。只提高观测预算，不改游戏事件。运行后核对未触顶；限额耗尽不以事件缺失作否定结论。磁盘保留≥6GiB，不删除历史世界/证据 |
| 结论 | 一次有界接口覆盖检查，不估计发言概率；全部提交与失败均保留。形成 PASS/PARTIAL/FAIL/BLOCKED 后本轮停止，**无论 A 是否 PASS 均不进入 B**，不自行 CLOSED |

本轮运行前冻结了完整9文件补丁 SHA-256 `19caffe6962c6b5e094fd1344c2b84b8eb5a737943a8d0ac865d9c0b39708cf8`，以及文件 harness SHA-256 `6a0f07a3934baf6899030deb305aec4e3063087477f0e172a62da93bd1f9416b`。原位随机条件、过滤谓词/次序、普通发言归因与 Agent 行为体由父代理及独立 Luna 静审；Python 文件测试15/15通过，父代理独立复跑15/15通过，不是原生运行结果。构建时曾漏设 `CARGO_TARGET_DIR`，人工中止默认目录重编后保留日志与缓存，改回原绝对 `source-target-serveronly` 路径；该失误发生时尚未启动新服务器，没有改变依赖、锁文件或游戏逻辑。

原生运行准入检查：canonical target 构建 exit 0（2m42s），binary SHA-256 `c578dfb4b72347e64025969b0c42753e68402d883e5e23941d970712aadd877d`；聚焦 Rust 14/14（common 1、rtsim 8、server 5）通过。父代理独立读回构建/测试输出，并核对 build copy 完整差异哈希等于上述补丁，两份 Cargo.lock 均仍为 `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`。代码、脚本与上表协议在第一轮新服务器启动前固定；之后不修改，缺证据则按固定边界停止。

## A-Closure 实际结果与停止裁决

两个新世界副本均来自同一原始保存世界，初始六项输入哈希一致；没有改种子、移动/生成 NPC、启动 GUI 或提交 LLM/Planner 请求。完整限定记录见[本轮证据目录](evidence/a_closure_20261017/)，与下节旧 B/C/D 运行分开。

| 请求 / 检查 | 实际结果 | 本轮判定 |
|---|---|---|
| 无请求基线（服务器 #1） | 742 条：733 条 NPC 样本、9 条目录；445/465 保持原有旅行与实际位置变化，0 关联请求；正常退出 0 | 有限基线 PASS，不代表长期人物动力学 |
| `cd-a-closure-cancel-20261017-1249`（服务器 #2） | 445→465 的 Talk 与 cancel 两行一次写入，随后 `request_rejected: pair_not_live_loaded_civilised_nearby` → `not_found`；没有 accepted、Brain 终态、Say、交接或 Agent 效果 | **取消负控未成立**，不是成功取消，也不是 Agent 拒绝 |
| 正向请求 | **0 / 最多6次**；负控前置失败后不提交 | NOT_RUN；不能写成六次无发言 |
| 原生交谈分支 / Agent 处理 | 新补丁已静审、构建及聚焦测试，但本轮请求未进入 Brain | 原生分支和 Agent 证据仍未补齐；不能解释旧 D 的 RNG 原因 |
| 上限与退出 | 2 / 2 次服务器启动已用；两个服务器均 SIGUSR1 正常退出 0。纯文件 harness 因明确负控失败被人工中止，退出 130 / KeyboardInterrupt | 本轮停止；不是 harness 自动失败出口，更不是流程成功 |

**资格与权威世界检查并非同一时刻。**原始样本和 harness 记录显示，提交前 t=5.195206791，双方 alive、Loaded、原生 SPEAK 可用，ECS 三维距离约 **7.41999m**，已通过5秒持续资格窗。之后的 t=6.194890416 样本显示约 **8.67m**。拒绝事件本身只有综合 guard 原因、没有时间戳或逐条件诊断，所以不能断言距离就是已证实的唯一拒绝原因；现象与采样至实际处理之间资格失效相容。新鲜观察不等于原子地锁定世界资格，最终接受仍由服务器检查决定。本轮不缩短等待、放宽距离或补交第二个负控来追成功。

请求世界完整事件为673条（662样本、9目录、1拒绝、1 not_found），619,866 bytes，仿真 t=0.033333333→80.206367916；最大单条4,216 bytes，远低于50,000条 / 64MiB / 1,800墙钟秒 / 64KiB单条预算。基线为688,685 bytes、最大单条4,188 bytes。这里没有把遥测耗尽当作无效果。请求后继续采得的原生活动不是正向请求后的恢复证据，因为本轮根本没有正向请求。

拒绝位于**本项目补丁新增的服务端请求入口校验**，不是 NPC 自身的社交拒绝，也不是原生 Talk/Agent 执行失败；请求没有越过该入口。它只能说明本次输入未被入口接受，不能据此裁决 Veloren 的原生交谈能力或新诊断链有缺陷。

**执行偏差原样记录：**基线目标为首有效样本后60墙钟秒；人工轮询/关闭使采集多保留了一段，完整仿真跨度约82.546秒，未截尾。精确首样本墙钟与停止信号时间没有完整捕获：服务端首日志为12:51:18.553，末端记录/文件写入约12:52:49，对应约91秒的进程观测跨度，**不是精确采样时长**。不采用早期口头估计的74/14秒，也不把mtime当精确退出时间。负控拒绝后，harness 没有自动识别该组合拒绝并立即退出，而是等待终态；父级按停止条件中止纯文件控制器，随后正常关闭服务器，未追加任何输入。这是现有脚本的失败反馈局限，本轮不在运行中修改。

冻结记录保存了启动前 RESULTS 整文件哈希 `7cf6f1ea…fb5ba5b`；随后仅移动一行历史引导、明确旧标题归属，实验参数未变。对这两项导航编辑逆变换得到的 hash-matched 视图与原哈希一致；这是可核对的重建视图，不伪称当时另存的快照。构建前误目录重编、临时目录权限失败及全部正常/失败输出也分别保留。

**裁决：A 总体仍为 PARTIAL；本次 A-Closure 阻断于取消负控准入。**已经证实的最远正向边界仍来自 `3a82cd0`：请求进入 Brain，尚无 Agent 结果。本轮没有证明接口行为错误、普通发言误归因或绕过原生规则，也没有补到 Agent 链。**B 仍无新准入证据，不开始。**后续是否修改资格/反馈协议，应由独立审阅后另行决定，不在本轮继续。

## 2026-10-17 3a82cd0 历史授权与实际结果

本轮从 `72a37c940f09d3983a5747be33d8509f958b588f` 继续。完整审查已存 ignored `_local_data/source_archive/2026-10-17_veloren_review/`，原文 SHA-256 为 `b34a84c4f73ff7d419dd911be85b340c1b2f6df170272ef685962ad128391077`，不公开原文。A 先完成三项风险修正与原生运行；B 只在 A 关键能力实际证明后开始，不预写世界成功结果。

已核实：原 server-only workspace 缩减会要求 Cargo 更新锁文件，因此放弃该构建范围适配；在独立构建副本恢复官方完整 workspace 清单，仍只编译 server-cli package，不启动或编译客户端。采用隔离可信 crates.io 镜像解析依赖，原 Cargo.lock 不变，真实编译错误已修；这与 10-16 的依赖 DNS 失败是不同结果。

最终补丁的第一次 server build 实际 exit 0，但无 `plugins` 的调试构建在首 tick 因 `RequestPluginsEvent` 缺少已注册处理器而 exit 134。原生事件总线检查没有关闭，也没有添加空处理器；仅启用原版已有的 `plugins` feature 重建，实际 exit 0，binary SHA-256 `2760baacf42ad8b403f9ee94c721503ff0e7521f40f20d865e9a8b331ea7ab28`。两次构建和首轮崩溃均保留，不把后一次结果覆盖到前一次。

无请求基线已正常结束：454 条真实 NPC 采样及 24 条 catalog，覆盖仿真时钟约 230.44 秒。UID 434 / 465 从 simulated 转为 Loaded，原生 Brain 为 `walk to pirate hideout`，Controller 为 `Goto`，ECS 位置连续变化，之后重新进入离屏模拟；不把 simulated hints 当成 Loaded 交谈对象。原样轨迹和短读回见 [baseline readback](evidence/server_build_20261017/native_baseline_readback.md)。stdout 中缺少可选 plugins assets 目录的错误原样保留，服务器随后继续运行。仿真时长不冒充精确墙钟时长。

随后零请求发现运行暴露了人工轮询延迟：445 / 465 曾处于约 2.29 米近距，提交前已相距约 29.1 米，因此未发出请求，不记为 NPC 拒绝。正向试验改用实时文件 harness，在同进程无请求前缀及新鲜三维距离门限成立后提交一次取消负控及唯一正向请求；不改 NPC、种子、原生随机分支或游戏能力。

最终自动控制运行 D 的原始 JSONL 共 348 条：17 条 catalog、326 条 NPC 采样、2 条 `request_accepted`、1 条 `cancel_requested`、2 条 Brain 终态。两个 ID 均只接受和结算一次，没有 `native_speech_emitted`、`speech_blocked` 或活动请求的持续采样。轨迹约 258 KB、165.27 秒仿真时间，低于默认遥测预算；不能把缺少 Agent 事件解释成日志限额耗尽。

| A 的固定验收项 | 本次证据与裁决 |
|---|---|
| 修改版服务器真实编译运行 | PASS；最终 patch `1ccf5c1…`、原锁不变、plugins build exit 0 |
| 无请求的程序化原生基线 | PASS；434/465 的 native Brain、Controller、ECS 轨迹及加载/离屏转换 |
| 请求进入原生行为选择 | PASS；445→465，正请求 `cd-native-positive-20261017-1105` 于 t=11.47195075 接受并由原生 Talk 返回无发言终态，不仅是文件写入 |
| Agent 实际处理结果或明确拒绝 | **未证明**；无 Say 排队/发言/阻止记录。不能把无发言终态改写成 Agent 拒绝，也未记录具体 RNG 抽样 |
| 外控结束后的原生行为 | PASS（有限观察）；两个 NPC 继续原有藏身处旅行/等待与位置变化，未重写历史或设置完成状态；不是长期稳定性证明 |
| 有效负控，不伪造成功/归因 | PASS（本次取消范围）；`cd-native-cancel-20261017-1105` 于 t=6.257583541 接受、取消并终止为 `cancelled_before_native_action`，同 ID 无动作或 Agent 效果。普通/外部 Say 交错另有 Rust 测试，不冒充本次实机并发社交证据 |

完整限定证据见[逐文件清单](evidence/server_build_20261017/manifest.json)；最终 D 的[独立读回](evidence/server_build_20261017/native_run_D_readback.md)、[原样服务器事件](evidence/server_build_20261017/native-events-auto-d-20261017T110500+0800.jsonl)、[原样请求输入](evidence/server_build_20261017/native-requests-auto-d-20261017T110500+0800.jsonl)与[配置/源码版本](evidence/server_build_20261017/native_run_D_config.json)均可直接复查。Cargo 大型 HTTP trace 只公开标明来源哈希的有限诊断摘录；真实服务器 JSONL 不删减，游戏资产、DB 二进制和私人原文不公开。

执行脚本 `run_talk_probe.py` 只追加真实请求、读取服务器事件；负控两行由一次 OS write 提交，终态确认后再提交唯一正请求。它固定等待 TTL+20 秒及额外 20 秒后续观察，`exit 0` 只表示流程结束，不代表游戏成功。两名原 NPC 均保留自身任务；正请求之后，445 后续到达原生等待活动，465 仍有原生旅行轨迹。后续插件版 B/C/D 服务器均通过 SIGUSR1 正常退出，首轮无插件启动的 exit 134 另行保留；未继续 GUI、作者节点、LLM 或工作包 B。

**B 的回答：本轮没有开始规划新行动过程或验证作者约束。**A 的 Agent 边界尚未通过，因此不提前运行 B，也不把 B 判为平台 `UNSUPPORTED`。若后续继续验证 Agent，须先固定有限重复采样或分支观测方案，保留本次无发言结果；不将“重试到说话”为隐含验收策略。

聚焦测试实际执行：common 动作队列 1/1、rtsim 请求/归因/取消/过期 6/6、server 去重/筛选/终态 5/5 均通过。最终补丁 SHA-256 为 `1ccf5c1db8d164743838b1bcb67a73adea88dd7a180f64c45b4c204c48097936`（9 个 Rust 文件）。`mismatched_request_id_is_not_attached_to_say` 只测归因隔离，不宣称测试了完整 Agent 发言拒绝。初次广测未指定资源目录，common 52 pass / 48 资源缺失 fail；指定现有官方 assets 后广测 exit 0，另行保留其结果，不用它代替聚焦测试。为保留磁盘安全空间，已仅清除本轮 target 下约 3.44 GiB 可再生成的 incremental cache，依赖、测试产物、日志、存档均保留；后续 build 使用过程内 `CARGO_INCREMENTAL=0`，不修改原生玩法规则或锁文件。

## 2026-10-16 环境与接口检查点（历史）

官方 macOS ARM64 ZIP 已完整取得并校验（404,762,532 bytes；SHA-256 `4fbd5cf1794e149ec9bad38dcbf34d1a9b4e1eda428e8be0a28f12eacec29afc`）；binary SHA-256 为 `70572f61dbde6395f3bb737d0031ebb5c1907e0567cf82b2a33d77481b24ec28`。官方 client 已启动并由单人 server 生成 world，故当前仅记 `ENVIRONMENT_PREPARED`。`.app` 是官方 binary 的逐字节本地包装并链接 assets；签名与 quarantine 未更改。

GUI baseline 路径已由用户撤销，本轮没有继续操作玩家、菜单或城镇。NPC 程序采集仍为 `NOT_ESTABLISHED`；外部目标闭环为 `NOT_RUN`。源码静态审阅和 Python 文件测试不能替代 NPC 的真实运行证据。

| 闸门/对象 | 当前记录 |
|---|---|
| 环境准备：官方原版 client 与单人 world | `ENVIRONMENT_PREPARED` |
| NPC 程序采集 | `NOT_ESTABLISHED` |
| 外部目标 typedgoal 程序闭环 | `NOT_RUN`；有限源码补丁尚未编译/运行 |
| Python 文件调用器 | 5/5 测试通过，父代理独立复跑通过；不涉及游戏 |
| Rust server 构建 | 依赖获取受阻，未进入编译；不称为 Rust 编译错误 |
| GUI baseline / 作者节点 / LLM | GUI 路径已撤销；作者节点与 LLM 禁止且未使用 |

以上环境证据不构成 NPC baseline 或控制闭环结果。当前 client 和 singleplayer world 的启动只支持环境已准备；NPC 状态采集、外部目标执行及其反馈尚未证明。

## 历史：下载受阻阶段与环境记录

以下下载失败记录描述早先阶段；之后官方 ZIP 已完整取得并校验。原始下载材料仍保留，不覆盖、不作为当前状态。

- 目标资产：官方[Older versions → 0.18.0 → macOS ARM64](https://veloren.net/download-other/)指向的[GitLab 构建归档](https://gitlab.com/veloren/veloren/-/jobs/artifacts/v0.18.0/download?job=macos-aarch64)，不是 nightly/weekly。
- 官方 artifact 的预期大小为 `404,762,532` bytes；官方 HEAD 已核对该长度。
- 代理下载运行 240 秒后为 0 bytes，超时。
- 直连下载运行 240 秒后取得 19,279,413 bytes，仍超时且不完整。
- 之后作一次四段 Range 传输排查：三段各运行 300 秒后超时，仅取得 21,538,889 / 15,583,989 / 12,149,724 bytes；另一段 70.44 秒后连接重置，取得 161,077 bytes。后两次该段尝试另见下方证据，不把重叠数据累加为完整包进度。
- 一次续传将 `--continue-at` 与 `--range` 混用，服务端返回超出所需片段的范围，触发本地大小限制；这是下载工具使用错误，不是游戏拒绝或引擎失败。后一次精确范围重试仍只取得少量字节即连接重置，未继续循环。
- 当时保留的非重叠下载数据合计 **68,713,092 / 404,762,532 bytes（16.96%）**；该历史数字不包括之后取得并校验的完整官方 ZIP。
- 有限路径对照包括 HTTP 代理、直连和 SOCKS 代理；未改全局代理、安全设置或下载版本。HEAD 能返回长度，不代表完整 GET 可靠。内置浏览器加载官方页面也返回连接重置；没有绕过安全检查。
- 主机：Darwin arm64，macOS `27.0.1 (26A434)`，当时可用磁盘约 `14 GiB`。
- 下载断点、日志及游戏文件仍位于项目忽略目录 `_local_data/external_games/veloren_0_18_0/`。后续环境准备已生成单人 world；公开的脱敏环境证据见 [native environment manifest](evidence/native_environment_20261016/manifest.json)。游戏包、assets、userdata 数据库与上游源码不纳入 Git。
- 早期下载阶段未进行大型源码 clone、Rust 构建或依赖安装；本轮另行取得的干净官方源码与 nightly 环境准备进度属于当前实现工作，尚未构建运行。
- 公开限定证据见 [下载记录索引](evidence/download_attempts/attempt_index.json)及同目录 curl stderr/metrics；头文件、签名下载 URL、凭证与私人浏览器内容不公开。早期代理/直连结果只有工具输出转录，不伪称为独立保存的 raw 文件。

## 原版运行与数据边界

以下 GitHub `b2f1060` 源码审计只作历史定位线索，不是官方 GitLab binary 的同版源码证据。官方 client 与单人 world 已启动，但 NPC 程序观测及 Admin 命令权限/输出仍未实测。

- `/rtsim_npc <query> [max]` 输出匹配 NPC 的名称与 UID；可按职业、角色、模式、UID、身体/物种关键词及 AI action backtrace 标签过滤。它不是逐 tick 状态导出。
- `/rtsim_info <uid>` 返回 seed、位置、role、home、faction、personality、current site、current mode、riding，以及 `brain.action.backtrace`。
- `/rtsim_info` 不输出当前时间、明确目标字段、controller activity、健康值或已实现的物理/动画动作。因此命令输出不能冒充完整的 NPC 状态轨迹。
- 这两项是客户端发往服务器的 Admin 聊天命令，不是服务器 CLI/TUI 子命令；服务器管理 TUI/argv 未见 NPC 查询命令。
- v0.18.0 server 启动时记录 userdata 根目录，并在其下使用服务器数据目录；数据库位于该目录下的 `saves`。源码允许以每进程 `VELOREN_USERDATA` 选择 userdata 根，可用于隔离原版运行数据。
- 本轮尚未确认 web 服务是否存在只读 NPC 状态端点，不对此作肯定或否定断言。

## 历史 GitHub 源码审计（非运行结果；不对应官方 binary 版本）

旧选取文件来自 GitHub commit `b2f1060df37ba4eb2eb001ac1b115beaf404f656`，仅保存在 ignored 的 `source_audit/`；它们不是官方 GitLab binary 对应源码，不能用于同版断言。官方 GitLab build commit 为 `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。

- Admin 命令分派及信息字段：[`server/src/cmd.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/server/src/cmd.rs#L226-L227)；处理函数 `handle_rtsim_info` Rust 行 1942–2018、`handle_rtsim_npc` 行 2020–2099。固定文件 SHA-256：`aba623bbd99f6ddfef6980948a00b02ffb7633412aea1a4c46cd9813d4e65e68`。
- Admin 参数/命令关键词：[`common/src/cmd.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/common/src/cmd.rs#L1030-L1038)；关键词 Rust 行 1246–1247。SHA-256：`a0119dd532bdaee729009ca4f2697211762134799049074c9721e5cdcff630f1`。
- userdata 初始化及 server `saves` 路径：[`server-cli/src/main.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/server-cli/src/main.rs#L92-L98)；数据库目录 Rust 行 134–139。SHA-256：`36321f663e384b8918cdd6ec3d928015baa543fc4bd9445527c8e06cb4b4581f`。
- per-process userdata 环境变量：[`common/base/src/userdata_dir.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/common/base/src/userdata_dir.rs#L4-L5) 及 Rust 行 28–32。SHA-256：`71f35850b529c7dcb1adee4b071c1870ecce21fa20b33ccf5d31a8c29aefc84b`。
- 原生 RTSim controller 每次 brain tick 前重置 `activity`、`look_dir`，并恢复 job：[`rtsim/src/data/npc.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/rtsim/src/data/npc.rs#L73-L80)。AI tick 调用前的 reset 位于 [`rtsim/src/rule/npc_ai/mod.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/rtsim/src/rule/npc_ai/mod.rs#L162-L186)。这说明“提前写 activity”可能被原生 reset 清除；并非目标接入已实现或已验证。

## 2026-10-16 程序接口实现与核验（历史）

本轮项目基线为 `b44a26895f15cca0d79b942ab9f3058ead3984eb`。取得官方同版稀疏源码（约 24 MiB，不下载 LFS/assets），在项目 ignored 目录安装固定 `nightly-2025-09-08`：`rustc 1.91.0-nightly (12eb345e5 2025-09-07)`。没有安装虚拟机，也没有更改全局 Rust、Git、代理或安全设置。

实现见 [补丁与调用入口](../../tools/veloren_native_v0/README.md)，补丁固定到上述 GitLab commit，覆盖 8 个 Rust 文件。当前补丁 SHA-256 为 `b9edac2224a558ef9e681be873a00bc23faa2623aa173c5b72fdc8499b802b57`。父代理已核对文件范围及反向应用检查，另有 Luna 静态审阅；这些均非编译或运行验收。

| 接口位置 | 补丁中的实际职责；尚未实机验证 |
|---|---|
| `server/src/rtsim/tick.rs` | 消费本地 append-only JSONL；校验请求身份、TTL、真实 NPC/target、加载状态和距离；输出原生状态目录及选定 NPC 的 Brain/controller 采样 |
| `rtsim/src/rule/npc_ai/mod.rs` | 在原生 inbox、敌人及任务超时反应之后接入有限 `TalkToNpc`；调用已有 `talk_to`，不以写一次 activity 绕过 Brain；保留原生打断及取消路径 |
| `rtsim/src/data/npc.rs`、`common/src/rtsim.rs` | 保存运行期请求 lease，并把 request ID 与具体 Say action 同位关联；避免旧的自然对话被错误算作外部效果 |
| `server/src/sys/agent/behavior_tree/mod.rs` | 在原生语音许可检查和 ChatEvent 实际发出点记录 `native_speech_emitted` 或 `speech_blocked`，不把意图排队算作完成 |
| `server/src/rtsim/mod.rs` | 默认关闭的内部观测与有界事件输出；未设置请求路径时不轮询请求 |
| `server/src/lib.rs`、`server-cli/src/main.rs` | 可选调用原生 persister 加载真实 NPC 现有位置附近的区块；不创建或传送角色。该选项会改变加载条件，未来实测须单独记录 |

选择原有对话而非采集：同版 Agent 的 Gather 路径仍是 TODO/占位，不能将其当成已实现资源结算。对话保留原生内容、随机性和发言限制，不新增“必定成功”动作。`request_accepted`、`native_intent_queued` 与 `native_speech_emitted` 是三个不同边界；即便后者将来出现，也不证明对方收到、接受或完成了对话。

取消与 TTL 只约束 Brain 侧尚未排队的意图，不能撤销已交给 Agent 的动作，也不保证外部请求即时打断原生长活动。请求状态是进程内临时数据，不宣称读档或崩溃恢复。

已运行的 [5 项 Python CLI 测试](../../tools/veloren_native_v0/offline_evidence/python_cli_unittest.txt)仅覆盖参数拒绝、request/cancel 追加、按 ID 读事件及分段 JSONL 尾行。父代理独立复跑 5/5，通过；没有启动游戏或制造游戏结果。新增 Rust 测试尚未运行。

## 2026-10-16 阻断：依赖获取，非 NPC 运行失败（历史）

完整记录见 [构建尝试索引](evidence/server_build_20261016/attempt_index.json)与同目录原始输出。早期数次在索引获取阶段被人工停止；不能称为 Cargo 超时、编译失败或游戏拒绝。

有界排查发现，即使选择 server package，原完整 workspace 仍解析客户端 `conrod_core` Git 依赖。为避免构建 GUI，在独立 `source_build_serveronly` 副本中只收窄 workspace members，保存 [构建范围差异](evidence/server_build_20261016/server-build-scope.patch)，原始源码树的 Cargo.toml 未动。两份 Cargo.lock 均保持 SHA-256 `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`；没有升级依赖、改游戏规则或取消校验。

同一官方 `cansi` 索引 GET：当前本地代理 SSL 超时，直连 HTTP 200（3,443 bytes，约 2.027 秒）。但随后 server-only 直连 Cargo 返回真实错误：获取 `https://index.crates.io/ru/sq/rusqlite` 时无法解析 `index.crates.io`（错误 6）。一次 curl 成功不等于 Cargo 整批依赖可取得；不能把它解释成已解决构建问题。未生成修改版 server binary，未运行程序化 NPC baseline、TalkToNpc、取消/恢复场景。

原单人 world 已复制到独立 userdata 并核对输入哈希，配置仅监听 loopback，固定原 seed/map；原存档不覆盖。游戏资产、数据库、地图、RTSim 数据及上游源码仍不入 Git；公开仅含限定日志、哈希和补丁。

## 2026-10-16 停止状态与当时的下一步（历史）

本轮停在 `DEPENDENCY_FETCH_BLOCKED`，不是等待用户试玩或再次允许打开游戏。下一步先恢复官方 Cargo 索引/依赖访问，再对现有补丁编译、运行真实只读 baseline，读取真实 NPC ID 后才提交请求。只有同一请求的 Brain、Controller、原生效果与结束后活动记录可支持闭环验收。

不继续盲重试，不启动 GUI、作者节点或 LLM，不改 F0/F1、冻结 Runtime 或 main，不回到选材。仍待完成的核心问题是：**外部程序能否让真实 NPC 尝试原生行为并取得实际反馈？本轮尚无运行答案。**
