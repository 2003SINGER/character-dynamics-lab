# Native Platform P1/P2 v0｜Evennia + Ensemble

历史范围：本页记录 P1/P2 验收截面，不代表当前实施状态。该截面的技术交付及当时未实施 P3/P4 按记录时间理解；随后用户授权 P3-A 单自主 NPC、P3-B 原生 Ensemble 双 NPC 交互。当前状态仅见 [Native Platform P3](../Native_Platform_P3_v0/README.md)。真人试玩是可选体验反馈、尚未确认，不是技术 gate 或全局 blocker；P4 未授权。原验收内容和证据不覆盖。

先读[唯一结果与 GO/NO-GO](RESULTS.md)、[父级真实浏览器验收](BROWSER_AUDIT.md)，
再查[源码级复用矩阵 / P3 接缝参考](REUSE_AND_P3.md)。
Evennia 原样漫游失败，最小兼容后 ADAPTED_PASS；Ensemble 原件测试及真实世界桥接通过；
LIGHT 本轮 NO_GO。代理交互不替代用户亲自试玩，不宣称完整人物系统/科研收益。

## 本轮要求与验收证据

| Gate | 要证明的事实 | 需要的权威证据 |
|---|---|---|
| P1-env | 项目隔离环境、固定 Evennia/Python/依赖 | 版本、lock/freeze、安装命令及原始失败；不是全局安装 |
| P1-native | 官方基础游戏与 EvAdventure NPC/FSM 运行 | 原入口/源码版本、真实服务器日志、NPC 状态/动作，不以自写 FSM 替代 |
| P1-player | 浏览器玩家进入、动作与世界变化 | 实际 web client 登录/命令/状态前后；代理验收与用户亲自试玩分别记账 |
| P2-native | Ensemble 原例的社会记录、volition、动作选择/效果 | 固定原例资产与原 JS engine 的输入输出、原 tests 结果及不启用的测试 |
| Bridge | 实际 Evennia 事件→合法 Ensemble 输入→提案→Evennia 验证/结算→社会投影 | 成功/真实拒绝/重复反馈的记录；提案阶段不改变 W，不双重提交 effects |
| LIGHT | 独立无模型限时准入 | 固定源码、命令、依赖/入口失败或实际行动；NO_GO 不阻塞主线，不大修原依赖 |
| Reuse | 旧 Python 资产可复用/不能直接复用的接缝 | 当前源码接口审查与矩阵；不调用旧 Executor 再结算新世界 |
| Handoff | 可复现环境、最小交互演示、P3 清单、风险及 GO/NO-GO | 本目录唯一 RESULTS；运行目录不可覆盖，私密账号/db 不公开 |

## 归属与操作边界

- `tools/native_platform_v0/`：窄安装/复现/互通工具，不是新的插件框架。
- `_local_data/native_platform_v0/`：原件缓存、venv 与本地游戏 db/测试账号；Git 忽略。
- `outputs/native_platform_p1p2_v0/`：本轮原始安装/运行日志和未删减开发产物，子 run 互不覆盖；公开证据只挑无凭据的明确文件。
- 本目录：可公开的版本/重放指针、脱敏事实证据与唯一结果，不提交大源码缓存、数据库或账号秘密。
- Evennia 拥有实际游戏 W；Ensemble 为共享社会记录算法，不声称 actor-private O。节点提案必须经过游戏权限/位置/真实前提检查，失败不 commit 社会 effects。
- 只监听 loopback；QQ 已使用 4001，本轮选 14000/14001/14002/14005 等未冲突本地端口，不重启其他服务、不开放公网。
- 明确区分工程技术 GO、独立复核状态、用户亲自试玩和研究收益；没有玩家可置信性或新方法结论。

复现入口：[Evennia](../../tools/native_platform_v0/evennia/README.md)、
[原 Ensemble](../../tools/native_platform_v0/ensemble/README.md)、
[最窄桥接](../../tools/native_platform_v0/bridge/README.md)。
原始产物保留在 ignored outputs，供远端审阅的小型证据及哈希见 [evidence](evidence/README.md)。
不自动扩开发完整村庄、Director、心理 law、训练或 LLM，也不自行 CLOSED。
