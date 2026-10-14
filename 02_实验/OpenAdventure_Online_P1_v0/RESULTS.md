# Open Adventure P1 — 原版在线交互闭环

日期：2026-10-14。状态：**DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止，未 CLOSED**。

## 实际交付与 G1–G8 验收

父代理核读代码并独立运行，最终[程序 smoke 结果](current_policy_smoke.json)为同一原版进程 **18 次输入 / 12 次非启动、seed 或退出回答的游戏输入**，其中包含一次原生语法拒绝；不把这些计数称为 resolved actions 或游戏 ticks。初始观察及全部 18 段原始字节均与重新执行相同输入的 replay 一致。[离线回归日志](unit_tests.log)：新 session 8 项 + 旧 runner 8 项，共 **16/16**。CI 仅跑离线契约；exact-head 状态见 GitHub Actions，不替代本地原版证据。

| Gate | 实际依据 | 结论 |
|---|---|---|
| G1 逐次交互 | 每次 `step` 只写一行，返回原生提示符或真实终止；未预先提交整局 stdin。支持 reset/observe/step/close/replay | 开发验收通过 |
| G2 同世界持续 | 同一进程取灯→库存有 `Brass lantern`→重复拿取被拒→放下→库存为空→取回→库存恢复；父级另验 `take`→`Take what?`→`lamp` 的澄清 | 开发验收通过 |
| G3 反馈决策 | `choose_recovery` 只接收刚返回的可见文字；实际“already carrying”选择 `drop lamp`，反例文字选择 `inventory`。调用发生在收到响应之后 | 接口程序分支通过；非规划能力证据 |
| G4 原生变化/失败后继续 | 原版拒绝、物品状态变化、退出确认选择 `no` 后继续 `look` 均实际发生；未新增 NPC/世界行为 | 开发验收通过；未声称触发新 NPC 场景 |
| G5 信息边界 | controller 输入仅为可见字符串；没有隐藏地图、game_t、NPC/RNG 游标 API。源码/二进制校验只做接入审计，不传给选择函数 | 当前接缝通过；不是恶意 Python 调用者的安全沙箱 |
| G6 回放 | 固定正常终端模式、源码/二进制和 seed 设置时机；实际初始/每步字节一致，完整消费输入，无超时/错误才能报 replay complete | 当前两个有限序列通过，不保证所有随机初始化 |
| G7 保护边界 | 上游源码/数据和 binary 在每段 close 时核对不变；未改 P5、C++、E0、时钟或执行器 | 通过 |
| G8 证据/异常 | 每次记录 prior observation、controller/source、intended/actual bytes、raw output、边界/终止/错误；假进程测试涵盖超时部分输出、短写、非零退出、超时但 exit 0 仍不得完成 | 有限契约通过，早期失败保留见下 |

最终程序首次/重复运行：

- [首次逐步记录](runs/66f9b188877c4f8ba2b880b4ac684c40-20261014T023846Z-4e46e0/events.jsonl)
- [明确标为 replay 的记录](runs/1e37aa06e2844f56bf45505052abdfe9-20261014T023846Z-fc0f3c/events.jsonl)
- 父级独立的澄清/恢复核验：[18 次输入](runs/parent-clarification-recovery-20261014T023728Z-1f1d4d/events.jsonl)与[精确重放](runs/4cece48d595944ebb676dcd9182f9677-20261014T023728Z-85b048/events.jsonl)。两条是同一物品/输入边界切片的不同核验，不是更多规划场景。

`reset` 创建新进程；单个 Session 实例只启动一次，新 episode/replay 使用新实例。`observe` 只取缓存，不读进程或推进世界，结束后也保留最后完整输出。超时部分字节保存在日志，不被升级为新的完整观察。PTY 合并 stdout/stderr 为玩家终端流，本接口不假称分别识别两者。POSIX PTY 路径已在本机 macOS 验证，Windows 原生路径未验证。

## 失败、版本差异与修正

1. [早期探针](runs/pty-feasibility-probe-initial/record.json)记录原生提示符与退出确认；第一段退出码未采到，不能补猜。父级之后未发现存活 advent；第二段实际 quit/yes exit 0。
2. worker 的[最初 17 输入](runs/c1b9277a484b4541af8b31d35b61dc7b-20261014T022458Z-d02795/events.jsonl)及[旧 replay](runs/f647c7ac0111409e9f27cdad4525b1d7-20261014T022458Z-aff450/events.jsonl)保留。它们早于最终源码 SHA 元数据、进程隔离和正向库存断言，也没有单列 intended/actual 输入字段；旧 replay 复制了原 controller 标签，仅代表历史输入，不代表重新决策。最终验收以本页上方新版记录为准，不回填旧日志。
3. [父级失败尝试](runs/ec3db2d94da6424a9bf9fda8bc907248-20261014T023224Z-f41530/events.jsonl)停在第6输入：库存显示 `Brass lantern`，父级脚本错误检查 `lamp` 导致断言失败，这是核验脚本的别名错误，不是物品没拿到。随后调用 close 时整个执行入口返回 143，末尾 close 未写出；不能把这段说成完整成功。与共享进程组中的原生终端信号处理有关的具体机制未完整跟踪。
4. 修正为子进程 `start_new_session=True`，只隔离进程/信号生命周期，不改原游戏。原生[仍等待输入时的关闭探针](runs/19f63f816c444d9482a3ec108bb2cf65-20261014T023607Z-aaedc9/events.jsonl)已返回调用方并回收子进程，exit -15、source/binary 不变；-15 是 Adapter 清理，不是正常通关。离线 SID/回收断言及上方新版真实 episode 均通过。

最终 reset 记录 Adapter 源码 SHA、配置版本与基础 Git revision；程序首段另记录 policy 源码 SHA。实验在提交前运行，base revision 是 `354d7ba`，不是交付 commit；以实际代码 hash 对应交付源码，不能把旧 base revision 当新代码未修改。未保存早期单测失败的完整 stdout：实现过程曾有临时目录权限错误及退出状态竞态（已修）；这是保留的诊断描述，不冒充原始日志。

## 边界与职责

固定原版 Open Adventure 1.22，源码 commit `e6160529e70a8c7a06b9a5f190d69aa35c4c62f5`。此前官方测试/三个整局回放继续由[原 Native v0 RESULTS](../OpenAdventure_Native_v0/RESULTS.md)拥有；本页只记录新在线接缝，不改写旧运行。地图、物品效果、NPC 与随机过程属于原游戏；PTY、单行收发、日志与回放属于新增 Adapter；简单反馈分支属于 **interface smoke policy**，不是成熟规划器或新算法。

正常模式使用上游 `advent.h:85` 的 `PROMPT = "> "`；`misc.c:get_input()` 先打印换行，再进入 `main.c:myreadline()` / libedit，普通输入、yes/no 和澄清共享这一通道。旧 `-o` 关闭提示符，不用于在线入口。PTY / `TERM=dumb` 提供原生终端条件；只有精确的行尾提示符或实际进程终止才形成返回边界，不靠 sleep、静默时长或任意剧情单词猜测。

**输入请求边界不等于动作成功、任务完成或一个世界 tick。**一条 `take` 可以只触发澄清，一条 `quit` 可以只触发确认；世界/NPC 更新仍由上游循环决定。适配层不维护第二套游戏时钟、动作结算器或 TypedIR 回执。

父代理独立核查固定 `adventure.yaml` 的字符串，未发现与换行加 `> ` 完全相同的文本行。这个边界准入仅适用于此版本与此终端模式，不是通用终端协议保证。初始随机种子来自游戏初始化，实验通过原生 seed 输入控制其后的随机流；须记录 seed 的设置时机，不能主张任意初始化都受它控制。

## 后续研究所需的最小输入/输出（仅登记，不实施 P2）

1. **共同输入：**作者目标、硬条件、截止/停止判据；玩家合法文字、自己已提交的输入与真实响应。传统基线若需要动作模型，应核验其公开规则来源，并明确所有方法可取得什么，不用隐藏世界状态给某一方法额外信息。
2. **单次输出：**一条原生输入；可另附因果假设、候选子目标与未落实义务。文字假设不修改世界、不注册新动作，也不是成功证据。
3. **实际反馈：**原始游戏字节与可见文字、是否再次请求输入、真实终止/错误及退出码。动作或作者目标是否满足，需要另外预先定义可核验依据；退出码 0 和到达提示符都不等于目标完成。
4. **共同控制：**固定游戏/终端版本、随机控制时机、输入/调用/计算预算和超时处理；重放已提交序列，不把它称为未见任务的重新决策。
5. **准入缺项：**可信目标识别、明确的动作/规则输入、认真实现的传统基线、开发/评价区分、成本与失败分析尚未建成。本轮没有 LLM、搜索规划、快照分叉或作者自然语言编译。游戏的社会历史缺项也没有补齐；它不阻塞固定规则的物品因果研究，但不能被本接口解决。

## 发布与停止

公开限定适配代码、测试、真实交互/重复回放和本轮失败尝试的文本证据；[原版权归属说明](../OpenAdventure_Native_v0/THIRD_PARTY_NOTICE.md)适用于新的短游戏输出。私有讨论、上游完整源码/资源/二进制不公开。原附件已核验复制到私有原始材料，再移至废纸篓，可恢复。

本轮只验 P1，不部署 Jericho/第二款游戏，不接 Sabre/GTPyhop/LLM，不新增剧情/关系机制，不修改冻结 C++、E0、main 或旧实验。无关的 E0-H02 搜索预算失败继续按原 CI 证据记录，不修改其预算或断言。
