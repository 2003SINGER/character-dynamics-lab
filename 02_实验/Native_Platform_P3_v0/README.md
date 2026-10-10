# Native Platform P3 v0｜Evennia 原生人物实施

状态：**DEVELOPMENT_VERIFIED（限定场景）**。当前已授权范围 P3-A（一个真实自主 NPC）与 P3-B（原生 Ensemble 双 NPC 交互）已有实际 Evennia run、timer、MCP stdio 与 SQLite readback 证据；不代表生产就绪或全项目关闭。P4 未授权。本文是当前唯一状态入口；逐项实际结果只记于本目录 [RESULTS.md](RESULTS.md)。

真人亲自试玩是可选体验反馈，目前尚未确认；它不是 P3 技术 gate 或全局 blocker。P1/P2 的成功、失败、LIGHT `NO_GO_WITHIN_THIS_TIMEBOX` 及其原始证据保留于[历史结果](../Native_Platform_P1P2_v0/RESULTS.md)，不由本阶段重写。

## 授权范围与验收边界

- **P3-A：单个自主 NPC。** 在 Evennia 实际运行的世界中，用可重放证据证明一个 NPC 会基于游戏中的合法行动/状态持续采取行为并产生真实世界变化。只在实际入口、命令/运行日志及世界状态读回齐备后更新结果；计划、代码存在或自测不算通过。
- **P3-B：原生 Ensemble 双 NPC 交互。** 在 P3-A 基础上，由两个真实 NPC 经原生 Ensemble 机制形成交互，并验证世界动作/社会结算边界。必须记录实际运行输入、结果及独立状态读回；不把单元测试或桥接设计冒充现场交互。
- 真人试玩可作为体验反馈单独记录，不替代以上工程验收，也不是其前置条件。
- P4、完整村庄/Director、LLM 或新心理机制不在本次授权内。

本次 autonomous loop 是对一个作者给定配送目标的有限执行，不等于日常生活自治；手动 callback 数不等于经过的游戏内时间。B 的共享 Ensemble 记录包含三个符号人物，Evennia 中有两个实际 NPC；本次只验证了两种受支持 social action，不外推为全 Ensemble 动作覆盖。HTN 依赖与来源边界见[实现来源](README.md#实现与来源边界)；不主张原创 HTN 方法。

## 本地复核入口

以下是限定本地 Evennia 实例的操作示例，不是无需准备的一键安装。前提是已初始化本地 P1 Evennia game，且维护者可操作对应 P1 admin/game 目录。P3 hook 文件位于 ignored 的 `_local_data/native_platform_v0/evennia/nativep1/server/conf/`，普通 clone 不包含它们。先在 `server_services_plugins.py` 的 `start_plugin_services(server)` 中加入：

```python
from server.conf.p3_control_plugin import start_plugin_services as start_p3_control
start_p3_control(server)
```

并创建 `p3_control_plugin.py`，内容为：

```python
"""Local import bridge from Evennia's configured service hook to the repo."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[6]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.control_service import start_plugin_services
```

`install_headless_service.py --check` 仅只读核验上述两个 hook 文件，不会安装/改写它们。应用后可启动本地实例并执行单场景 runner：

```sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/install_headless_service.py --check
tools/native_platform_v0/evennia/start_loopback.sh
_local_data/native_platform_v0/evennia/venv/bin/python tools/native_platform_v0/p3/headless_runner.py --scenario Asteal-return --seed 20261010
_local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p3.mcp_stdio
```

MCP stdio 命令保持前台 JSON-RPC stdin/stdout；本地控制服务须已启动且仅监听 `127.0.0.1:14011`。精确七份复核输入（含历史 stale-target 负控）及 DB 导出路径列于 [P3 RESULTS](RESULTS.md#timer-mcp-与持久读回)；将七个 JSON 路径依次传给 `tools/native_platform_v0/p3/audit_evidence.py --runs`，再以该节的 SQLite JSON 传给 `--db`。审计器会在同一 runs 目录写入唯一 `p3-audit-*.json`，并打印该记录与输入哈希。

## 维护

保留实际命令、环境/版本、stdout/stderr、失败、世界前后状态和对应 run 路径。状态只在有可复核证据时变化；不要覆盖 P1/P2 历史产物。项目根 README、研究 TODO 与实验路由只保留当前入口指针。

## 实现与来源边界

P3 的 HTN planner 调用 GTPyhop 2.0.2（打包 fork：PCfVW/GTPyhop；BSD 清许可；作者 Dana Nau、Eric Jacopin），人物任务/方法配置及 Evennia 世界适配属于本项目的有限应用实现。算法调用不等于原创 HTN 研究或独立方法贡献；具体运行来源哈希保存在每个 run JSON。

P3-C0 的限定 DEVELOPMENT 已验证，当前等待独立审阅；其当前状态、范围与结果唯一见 [Native Platform P3-C0](../Native_Platform_P3_C0_v0/README.md) / [RESULTS](../Native_Platform_P3_C0_v0/RESULTS.md)。本页只维护 P3-A/B 历史结果，不复制 C0 结果。
