# A-Closure 原生证据读回

## 本轮边界

独立读回冻结的原始事件、输入和运行日志；不操作游戏/GUI，不重跑。原始输入与事件 JSONL 在本目录保留；原生用户数据目录中的地图、存档数据库、资产、二进制及源码未公开。旧 A = PARTIAL 记录保留；B 未启动。

协议冻结依据：原始冻结记录 SHA-256 `7a460c4444e1e0a7f175014b25ee065de76739afb3667bc89fdff62a531234f4`；RESULTS hash-matched reconstruction SHA-256 `7cf6f1eaf9c59a5bd7b7e07da9b544bfaa806289bb12889dd028e6747fb5ba5b`（这是对当前导航调整逆变换后的重构视图，不是当时另存的原件；仅用于核对运行前冻结协议）。原始独立索引 SHA-256 `e4e798bcd01bc81b45749fbb042a0ef9894215921b5270ab86b87aa0c5dee5f3`；索引本身因嵌有本机路径不公开，其安全摘录见 `run_index_readback.json`。共享世界输入哈希公开于 `run_config.json`，供核对输入身份；哈希不等于可完整复现。

运行输入摘要：Veloren 官方 GitLab 源码 commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`；世界 seed `130626853`、day length `30 min`；TCP/web 绑定 loopback ephemeral，query disabled。原存档数据库、地图、rtsim 数据和资产未发布；seed 本身不足以复现该历史存档。

## 请求逐项读回

| ID | 输入/状态 | 可核验事件 | 判定 |
|---|---|---|---|
| `cd-a-closure-cancel-20261017-1249` | 唯一写入的负控请求，随后同一原子 append 写入对应 cancel；输入文件共 198 B、两行 | 候选对 445→465 在 game time `5.195206791` 通过 harness 的 5 秒稳定与新鲜 ECS 3D 资格检查，距离 `7.419992818 m`。其后服务端记录 `request_rejected`，原因为 `pair_not_live_loaded_civilised_nearby`；`not_found` 时间 `6.194890416`。无 `cancelled_before_native_action` 终态 | 负控未成立；不能当作成功取消 |
| `cd-a-closure-positive-20261017-1249` | 只出现在 harness 的计划配置，未追加到 request 文件 | 无对应输入行、无事件 | 未提交，不评价 Agent、随机分支、Say 或 handoff |

提交资格与服务端拒绝之间的采样显示：拒绝后的同一采样时点，双方仍为 Loaded、alive、SPEAK allowed；记录 ECS 坐标计算的 3D 距离约 `8.67 m`。复合拒绝事件无独立时间戳，也没有失败子条件，故这与距离在检查间跨过 8 m 相容，但不能证明具体拒绝原因或精确处理时刻。该事件属于新请求入口的服务端资格 guard，不是 NPC/Agent 的行为选择；不得归因于 Agent、RNG 或某个单独 guard。

## 运行与验收

- baseline：server exit 0；742 行（9 catalog、733 baseline），game time `0.033333333 → 82.579435291`，增量 `82.546101958 s`；目标窗口为 60 s。首条 stdout 时间 `12:51:18.553 +0800`，最后日志/事件写入约 `12:52:49 +0800`，约 91 s 的观测跨度不等同于精确采样窗；SIGUSR1 信号时间未记录，故准确墙钟采样时长未知。完整原始轨迹保留；不截尾、不重跑。baseline 为无请求观察，包含 native pirate travel/原生活动，不是项目任务成果。
- request run：server exit 0；673 行（9 catalog、662 baseline、1 rejection、1 not_found），game time `0.033333333 → 80.206367916`。server 在 gate 失败后由精确 PID 的 SIGUSR1 停止并 exit 0。controller 在父级要求于拒绝后停止时被 Ctrl-C，exit 130 / `KeyboardInterrupt`；这不是 helper 自动 abort、成功取消或预算自然完成。该 run 有一个 cancel 负控、零个 positive submission；不得描述成“做了六次正向试验”。两次 server stdout 均保留一条缺少 plugins 目录的非致命 ERROR，server 继续运行且正常 exit 0。
- 两次 server launch 预算均已用完。无成功取消终态；无正向请求；无请求接受、native speech、Agent emission/blocked、handoff、或 positive 后 20 秒原生延续证据。观测未发现 telemetry cap 命中；但这些事实不能替代未执行的请求闭环。
- 编译与测试：冻结 patch `19caffe6962c6b5e094fd1344c2b84b8eb5a737943a8d0ac865d9c0b39708cf8`、官方 GitLab 源码 commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`、锁文件 SHA-256 `cc0d0eb5561e6463aeac5bc7a1ed50a3256a3a041210bf1e2cec9a0c9ae5348f`、binary SHA-256 `c578dfb4b72347e64025969b0c42753e68402d883e5e23941d970712aadd877d`。server CLI build exit 0；Python 15/15；Rust focused tests 14/14。详见相邻 `build_test_summary.md` 及其所列原始构建/测试日志 SHA。

## 结论

有限原生活动基线成立：无请求基线，以及请求未获准入后的原生轨迹，均记录到 native NPC 持续状态/行动。但这不支持完整控制接口 PASS、Agent 成功/失败或研究收益。本轮 A-Closure = **BLOCKED at cancellation-control gate**；整体 A 仍是 **PARTIAL**，B 未启动。候选在 harness 的 3D/稳定/新鲜资格检查通过，但服务端复合 guard 拒绝了唯一负控，导致正向请求按协议未提交；不据此归因原生 NPC/Agent 选择或随机分支。
