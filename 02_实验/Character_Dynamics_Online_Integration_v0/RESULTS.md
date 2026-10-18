# Character Dynamics Online Integration v0 — RESULTS

**状态：DEVELOPMENT / PARTIAL / READY_FOR_INDEPENDENT_REVIEW；本轮停止。** 三组真实 headless 运行完成，Actor/Director 两组形成了有界的目标—请求—原生 Job—继续观察链；但三台服务最终均以 SIGTERM（exit `-15`）结束，没有正常退出，整包按 PARTIAL 记录。此结果验证的是本次有限连续链，不是完整 Character Dynamics 系统、算法优势、复杂自主性或长期活动证明。

## 范围与来源

本轮按固定 [PROTOCOL](PROTOCOL.md) 使用同一个当前完整 checkpoint 的三份独立 userdata，条件为 `NATIVE_ONLY`、`ACTOR / DIRECTOR_OFF`、`ACTOR / DIRECTOR_ON`。六个 world 文件在三组间一致；SQLite 三文件相对旧 freeze 的哈希漂移已记录，未混搭 checkpoint，也未改 world 内容。相同 seed 不代表严格随机配对；每条件仅 `n=1`。应用 `ACTOR party_quota=2` 是本集成给角色的显式自身任务，不是原生海盗“四人目标”；原生 `population > 3` 规则未改。

作者输入来自 `RUNNER_DEMO`，通过真实 `author-input.jsonl` 入口；`LOCAL_AUTHOR` 人工交互没有实测。作者目标仅表达结构化结果/对象/期限，不预写动作序列。Planner 复用 GTPyhop 2.0.2 的 one-step 规划和固定优先级，不是新算法。

复现定位：Veloren source commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`；沿用 Loaded Msg binary SHA-256 `93473c17e11556d9ed7080b6ed9007a879b0614a77c7e9341a6a6b557ebc3aeb`；本轮无 Rust 改动。离线测试可运行 `python -B -m unittest discover -s tools/character_dynamics_online_v0/tests -v`。runner 入口示例为 `python -B -m tools.character_dynamics_online_v0.runner --freeze <private-new-input-freeze.json> --run-id <new-id>`。这只是用法说明，不授权新运行；本轮已运行 userdata 不可原样复用，后续如另获授权须创建隔离副本、重新固定哈希并使用新 run ID，不能覆盖本次产物。实际 `author-input.jsonl` 不公开；输入格式以 `runner.parse_author_input` 为准。

## 三组结果

| 条件 | 观测结果 | 停止与结局 |
|---|---|---|
| `NATIVE_ONLY` | 677 条 native telemetry、67 条 recruit telemetry；0 条外部 request、0 个可信归因 Job。 | 60 秒 wall cap 后进入约 16 秒关闭宽限，实际 wall 约 76.12 秒；最终 SIGTERM（exit `-15`），`PARTIAL`。 |
| `ACTOR / DIRECTOR_OFF` | 2 个 ACTOR 请求；Job witness 分别为 NPC 475（game time 9.295502916）与 NPC 450（14.621104916），这些时间是 Job witness 时间，不是请求提交时间。17 个 controller decisions；`party_quota=2` 达成。运行记录为两个可归因的 native Job 效果，随后继续原生观察 15 秒。 | 达到“两项 native Job + continuation”停止条件；总 wall 54.093 秒，其中约 16.076 秒为关闭阶段，运行约 38.017 秒；服务以 SIGTERM（exit `-15`）结束。 |
| `ACTOR / DIRECTOR_ON` | 首个 ACTOR 请求提交于 game time 48.930；第二个请求所依据的 ActorView 时间为 51.965。NPC 442 的首个 Job witness 时间为 52.0420375。作者版本 v1（目标 NPC 469）编辑为 v2（目标 NPC 450）在 game time 49.941722208 的同一个 controller batch 应用，并非两个独立周期；deadline 保持 138.930144375。首个请求仍在途，未假称取消。第二个请求由 `DIRECTOR` 使用 author version 2 发往 NPC 450，native Job witness 时间为 59.923078791，v2 为 SAT。v1 为 `SUPERSEDED / UNKNOWN`：无完整全局覆盖，不能称其已完成。第二次 Job 后继续原生观察约 15 秒，最终共 26 个 controller decisions（game time 74.2926），`inflight=null`、violations 0。 | 达到“两项 native Job + continuation”停止条件；总 wall 99.445 秒，其中约 16.045 秒为关闭阶段，运行约 83.4 秒；服务以 SIGTERM（exit `-15`）结束。 |

OFF 与 ON 的 game-state 效果由原生 Job 记录作证；Planner 状态只用于解释目标/版本，不代替原生世界事实。运行结束状态不等同于服务器正常关闭。19、54、25 三组离线测试均通过；这些测试通过不改变真实运行的 PARTIAL 状态。

ON 的 continuation 原生观测不仅是 `MAY_CONTINUE` 标志：second Job witness（59.9231）至最后 controller decision（74.2926）期间，约15秒 wall observation 记录到150条 `native_npc_baseline`（10 UID × 15）；leader 476 与 recipients 442/450 各有15个位置样本，distinct positions 分别为11/10/13。leader brain backtrace 从 idle 转为沿 path 前往 pirate hideout；两个 recipients 在观察期内均保持原生 `Following` leader，没有独立 follow 事件或状态切换。这证明本次短窗有原生位置/brain 活动，但未开始新的 ACTOR 任务或长期目标，不能宣称长期角色生活。

## 原任务 8 项验收逐项对照

1. **Director OFF 时角色 Planner 仍实际运行：有界通过。** OFF 条件有 17 个 controller decisions、两条 ACTOR 请求，且 actor quota 达成；Director 关闭没有关闭 ACTOR。
2. **游戏开始后作者要求进入系统：有界通过。** ON 条件在运行中经 `RUNNER_DEMO` 的真实 author-input 文件入口加入结构化未来要求；未测试人工现场交互。
3. **在线修改影响后续决策或产生合法阻断：有界通过。** v2 被后续 DIRECTOR 请求实际消费并产生目标 450 的 native Job；v1 保留为 `SUPERSEDED / UNKNOWN`，不能据此说旧目标完成。首个 inflight 请求未被假取消，deadline 未被编辑顺延。
4. **至少一个原生多 NPC 状态变化，优先两个不同 NPC 连续效果：有界通过。** 两个 Actor 条件的运行记录均达到两项可归因 native Job 效果，并各继续原生观察 15 秒；这只是每条件一次的有限轨迹。
5. **原生世界状态是结果唯一权威：通过本次证据边界。** Job 效果取自原生记录；控制器的 SAT/UNKNOWN 是状态解释，不能替代原生结算。
6. **作者版本修改后已结算历史保留：本次运行未覆盖该时序，验收部分未证。** 本次编辑发生于 game time 49.941722208，早于首个 Job witness 52.0420375；实测能说明编辑没有取消仍在途的请求，随后出现的 Job witness 被保留为事实，但不能称为“先有已结算历史、再编辑并保留”。版本历史保留与已结算后编辑保护另有离线测试，不冒充本次在线实测。
7. **NPC 未被一次性控制成固定完整脚本：有界支持，长期自主性未证。** 输入指定未来结果而非动作序列，后续选择由运行中的 Planner/真实反馈产生；规划实现仍是 one-step GTPyhop 加固定优先级，不能外推复杂、长期自主行为。
8. **完整轨迹区分 ACTOR、AUTHOR、DIRECTOR、NATIVE 来源：有界通过。** 请求、版本、controller decisions 与 native Job 分别留存并带来源；单次轨迹不证明来源分类在更多场景下普遍正确。

## 实际链、限制与停止

本轮证明了一个有限纵向能力链：Director OFF 下角色按自身 quota 决策；ON 运行通过真实作者输入版本化并消费编辑；原生 Job 变化可由原生记录核验；版本未知状态与 inflight 边界没有被伪装成成功或取消；两 Actor 运行按预设条件继续观察。它不证明作者可任意深度/任意时刻介入，不证明 `LOCAL_AUTHOR` 交互、完整全局覆盖、普遍目标绑定、长期角色生活、方法优于成熟基线或算法创新。G0 保持固定；本轮没有授权或实施 G1。

本包结果标为 **PARTIAL**：三台服务均未正常退出，且“已结算后再编辑”的在线时序未覆盖；非零退出不能被“达到场景停止条件”覆盖。每条件 `n=1` 另限制了结果的研究解释力，不是算法比较。本轮停止：不自动修复 shutdown、不补跑、不换世界、不增加准入或预算。后续开发若继续，须由用户另行明确授权。

## 私有证据与复现边界

本轮公开范围仅包括代码和报告；raw 记录、脱敏运行证据、配置、存档与源码快照均不公开，留在本地：

- Run root：`_local_data/veloren_online_integration_v0/20261018T234250-online-v0/`
- 统一运行摘要定位：该目录下 `integration-manifest.json`
- `integration-manifest.json` SHA-256：`6f572faec652143a016516743aecf23a5907128b1644ad43653bc561261428ea`
- 输入冻结与源码快照私有定位：`_local_data/veloren_online_integration_v0/inputs-online-20261018-v0/`；源码清单 SHA-256：`ddcf8989fd924aea139ee7efa52bd691bab669cc1b5b7b4a3bf74043d0018e2a`

公开报告仅给出摘要和私有定位/哈希，不能单独重放这些本地原始运行。raw 记录、逐版本 dump、回执、运行配置、源码快照、脱敏运行证据及私有对话均不发布。
