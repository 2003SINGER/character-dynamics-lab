# Veloren Vertical Slice v0 — 阶段结果

日期：2026-10-16

官方 binary 来源：Veloren v0.18.0 GitLab macOS ARM64 build，commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`。旧 `source_audit/` 的 GitHub `b2f1060df37ba4eb2eb001ac1b115beaf404f656` 仅作历史源码线索，不代表与 binary 同版。

项目起点：`webgpt-sync@91ebd876cef823e8f8b69c07a0d1af941b6b5b56`，远端与本地一致。

当前状态：`ENVIRONMENT_PREPARED`；`INTERFACE_IMPLEMENTATION=UNCOMPILED / DEPENDENCY_FETCH_BLOCKED`；`NPC_PROGRAM_COLLECTION=NOT_ESTABLISHED`；`EXTERNAL_TARGET_LOOP=NOT_RUN`。本轮已交付有限 server 接口补丁与文件调用器，但服务器依赖获取失败，尚未进入 Rust 编译；不作原生运行通过或 CLOSED 声明。

## 当前结论

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

## 本轮程序接口实现与核验

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

## 本轮真实阻断：依赖获取，非 NPC 运行失败

完整记录见 [构建尝试索引](evidence/server_build_20261016/attempt_index.json)与同目录原始输出。早期数次在索引获取阶段被人工停止；不能称为 Cargo 超时、编译失败或游戏拒绝。

有界排查发现，即使选择 server package，原完整 workspace 仍解析客户端 `conrod_core` Git 依赖。为避免构建 GUI，在独立 `source_build_serveronly` 副本中只收窄 workspace members，保存 [构建范围差异](evidence/server_build_20261016/server-build-scope.patch)，原始源码树的 Cargo.toml 未动。两份 Cargo.lock 均保持 SHA-256 `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`；没有升级依赖、改游戏规则或取消校验。

同一官方 `cansi` 索引 GET：当前本地代理 SSL 超时，直连 HTTP 200（3,443 bytes，约 2.027 秒）。但随后 server-only 直连 Cargo 返回真实错误：获取 `https://index.crates.io/ru/sq/rusqlite` 时无法解析 `index.crates.io`（错误 6）。一次 curl 成功不等于 Cargo 整批依赖可取得；不能把它解释成已解决构建问题。未生成修改版 server binary，未运行程序化 NPC baseline、TalkToNpc、取消/恢复场景。

原单人 world 已复制到独立 userdata 并核对输入哈希，配置仅监听 loopback，固定原 seed/map；原存档不覆盖。游戏资产、数据库、地图、RTSim 数据及上游源码仍不入 Git；公开仅含限定日志、哈希和补丁。

## 当前授权与下一步

本轮停在 `DEPENDENCY_FETCH_BLOCKED`，不是等待用户试玩或再次允许打开游戏。下一步先恢复官方 Cargo 索引/依赖访问，再对现有补丁编译、运行真实只读 baseline，读取真实 NPC ID 后才提交请求。只有同一请求的 Brain、Controller、原生效果与结束后活动记录可支持闭环验收。

不继续盲重试，不启动 GUI、作者节点或 LLM，不改 F0/F1、冻结 Runtime 或 main，不回到选材。仍待完成的核心问题是：**外部程序能否让真实 NPC 尝试原生行为并取得实际反馈？本轮尚无运行答案。**
