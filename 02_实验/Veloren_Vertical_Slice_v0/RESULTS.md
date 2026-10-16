# Veloren Vertical Slice v0 — 阶段结果

日期：2026-10-16  
固定源码版本：Veloren `v0.18.0`，commit `b2f1060df37ba4eb2eb001ac1b115beaf404f656`  
项目起点：`webgpt-sync@91ebd876cef823e8f8b69c07a0d1af941b6b5b56`，远端与本地一致。  
当前状态：`BLOCKED_DOWNLOAD / READY_FOR_INDEPENDENT_REVIEW`；`NATIVE_RUN=NOT_RUN`，未 CLOSED。

## 当前结论

阶段1尚未通过：官方 macOS ARM64 原版包未完整取得，因而没有解压、启动或建立可复核的原版行为基线。当前下载结果不能用于判断游戏不兼容，也不能据此给出 `NO_GO`。

阶段2、阶段3均未启动；A 基线未建立，B/C 未运行。没有实现接入，没有目标控制、危险中断或退还路径的运行结果。当前也没有新的系统架构、协议或选材结论。

| 闸门/对象 | 当前记录 |
|---|---|
| 阶段1：原版完整包与原生运行 | `BLOCKED_DOWNLOAD` / `NOT_RUN` |
| A：无改行为 baseline | 未建立 |
| B/C：目标接入及原生处理路径 | 未启动 |
| NPC 世界、角色、存档、动作轨迹 | 本轮均无运行证据 |

这里的 `BLOCKED_DOWNLOAD` 描述交付物不完整，不是运行失败或平台兼容性结论。下载完成前，原版 binary 是否能启动、是否能单人连接、是否能观察到实际 NPC 变化，都保持未知。

## 下载与环境记录

- 目标资产：官方[Older versions → 0.18.0 → macOS ARM64](https://veloren.net/download-other/)指向的[GitLab 构建归档](https://gitlab.com/veloren/veloren/-/jobs/artifacts/v0.18.0/download?job=macos-aarch64)，不是 nightly/weekly。
- 官方 artifact 的预期大小为 `404,762,532` bytes；官方 HEAD 已核对该长度。
- 代理下载运行 240 秒后为 0 bytes，超时。
- 直连下载运行 240 秒后取得 19,279,413 bytes，仍超时且不完整。
- 之后作一次四段 Range 传输排查：三段各运行 300 秒后超时，仅取得 21,538,889 / 15,583,989 / 12,149,724 bytes；另一段 70.44 秒后连接重置，取得 161,077 bytes。后两次该段尝试另见下方证据，不把重叠数据累加为完整包进度。
- 一次续传将 `--continue-at` 与 `--range` 混用，服务端返回超出所需片段的范围，触发本地大小限制；这是下载工具使用错误，不是游戏拒绝或引擎失败。后一次精确范围重试仍只取得少量字节即连接重置，未继续循环。
- 保留的非重叠下载数据合计 **68,713,092 / 404,762,532 bytes（16.96%）**；该数字不是完整 ZIP，也不是一个已安装游戏。没有合并片段、解压或运行；所有本轮下载进程均已结束。
- 有限路径对照包括 HTTP 代理、直连和 SOCKS 代理；未改全局代理、安全设置或下载版本。HEAD 能返回长度，不代表完整 GET 可靠。内置浏览器加载官方页面也返回连接重置；没有绕过安全检查。
- 主机：Darwin arm64，macOS `27.0.1 (26A434)`，当时可用磁盘约 `14 GiB`。
- 下载断点、日志及选取的固定版本源码位于项目忽略目录 `_local_data/external_games/veloren_0_18_0/`；未产生 userdata/存档。游戏包、片段与上游源码不纳入 Git，仅发布本工作包限定证据。
- 未进行大型源码 clone、LFS 获取、Rust 构建或依赖安装。
- 公开限定证据见 [下载记录索引](evidence/download_attempts/attempt_index.json)及同目录 curl stderr/metrics；头文件、签名下载 URL、凭证与私人浏览器内容不公开。早期代理/直连结果只有工具输出转录，不伪称为独立保存的 raw 文件。

## 原版运行与数据边界

以下只用于恢复运行时定位观测入口，不替代基线。固定 server 源码有 Admin 聊天命令 `/rtsim_npc` 与 `/rtsim_info`：先查 NPC 名称和 UID，再查该 UID 的 RTSim 信息；发布 binary 是否按此构建、运行时权限与输出均未实测。

- `/rtsim_npc <query> [max]` 输出匹配 NPC 的名称与 UID；可按职业、角色、模式、UID、身体/物种关键词及 AI action backtrace 标签过滤。它不是逐 tick 状态导出。
- `/rtsim_info <uid>` 返回 seed、位置、role、home、faction、personality、current site、current mode、riding，以及 `brain.action.backtrace`。
- `/rtsim_info` 不输出当前时间、明确目标字段、controller activity、健康值或已实现的物理/动画动作。因此命令输出不能冒充完整的 NPC 状态轨迹。
- 这两项是客户端发往服务器的 Admin 聊天命令，不是服务器 CLI/TUI 子命令；服务器管理 TUI/argv 未见 NPC 查询命令。
- v0.18.0 server 启动时记录 userdata 根目录，并在其下使用服务器数据目录；数据库位于该目录下的 `saves`。源码允许以每进程 `VELOREN_USERDATA` 选择 userdata 根，可用于隔离原版运行数据。
- 本轮尚未确认 web 服务是否存在只读 NPC 状态端点，不对此作肯定或否定断言。

## 固定源码核验（非运行结果）

选取的源码文件来自固定 commit，仅保存在 ignored 的 `source_audit/`，不是完整源码克隆，也不进入 Git。tag 对象 `5de79bf45d4c0595d9136947165a6f2becb5762f` 的解引用提交由父级另行 `ls-remote` 核对。

- Admin 命令分派及信息字段：[`server/src/cmd.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/server/src/cmd.rs#L226-L227)；处理函数 `handle_rtsim_info` Rust 行 1942–2018、`handle_rtsim_npc` 行 2020–2099。固定文件 SHA-256：`aba623bbd99f6ddfef6980948a00b02ffb7633412aea1a4c46cd9813d4e65e68`。
- Admin 参数/命令关键词：[`common/src/cmd.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/common/src/cmd.rs#L1030-L1038)；关键词 Rust 行 1246–1247。SHA-256：`a0119dd532bdaee729009ca4f2697211762134799049074c9721e5cdcff630f1`。
- userdata 初始化及 server `saves` 路径：[`server-cli/src/main.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/server-cli/src/main.rs#L92-L98)；数据库目录 Rust 行 134–139。SHA-256：`36321f663e384b8918cdd6ec3d928015baa543fc4bd9445527c8e06cb4b4581f`。
- per-process userdata 环境变量：[`common/base/src/userdata_dir.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/common/base/src/userdata_dir.rs#L4-L5) 及 Rust 行 28–32。SHA-256：`71f35850b529c7dcb1adee4b071c1870ecce21fa20b33ccf5d31a8c29aefc84b`。
- 原生 RTSim controller 每次 brain tick 前重置 `activity`、`look_dir`，并恢复 job：[`rtsim/src/data/npc.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/rtsim/src/data/npc.rs#L73-L80)。AI tick 调用前的 reset 位于 [`rtsim/src/rule/npc_ai/mod.rs`](https://github.com/veloren/veloren/blob/b2f1060df37ba4eb2eb001ac1b115beaf404f656/rtsim/src/rule/npc_ai/mod.rs#L162-L186)。这说明“提前写 activity”可能被原生 reset 清除；并非目标接入已实现或已验证。

## 下一步与停止条件

本轮停止所有下载与实施。已向用户请求最小协助：切换可访问官方 CDN 的网络节点，或从上方官方页面下载固定 ARM64 包到 Downloads；没有要求购买、注册账号或亲自试玩。下载断点与失败原样保留，不在本轮结束后声称后台继续。

恢复后只从原授权的未改原版运行开始，确认 binary 版本、单人世界、隔离 userdata、具体 NPC 的时间/身份/行为/真实状态轨迹；加载与离屏分别记账。仅启动窗口或读到 Controller 意图都不足以通过阶段1。只有真实基线通过，才可推进最薄目标接入及作者节点，不需要先写一轮新架构协议。

阶段1通过之前不写适配、不改 NPC 行为、不启动模型调用或其他游戏，也不把源码审计替代为 baseline。当前不回到已冻结的 OpenXRay 或 RimWorld 选材，不新增架构协议。

提交检查仅覆盖限定日志的字节/哈希、范围及去重、文档链接、受保护文件未变和仓库 health；后者保留四项既有警告。没有原版游戏测试或 NPC 运行 PASS，仓库 CI 也不能替代这些缺失证据。
