# Open Adventure Native v0 — 原版游戏接入与机制缺口

日期：2026-10-14。状态：**DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止，未 CLOSED**。

## 本轮解决什么

不再把“在 Evennia 上手写了工具占用规则”当作成熟游戏已有机制。站点是项目内容；Evennia 是执行引擎。首个外部完整游戏采用 [Open Adventure 1.22](https://gitlab.com/esr/open-adventure/-/tags)，原玩法、原 NPC、地图和物品规则均未修改。只构建、接最薄命令回放并审查原生机制，不把 P5 策略迁移过来。

独立的代码债清理提交为 `2b0e5c8`：只删除两个被覆盖 helper 的旧定义，保留 Python 实际使用的最后定义。[维护记录与回归](../Mature_Methods_Integration_v1/MAINTENANCE_20261014.md)记录完整模块 AST 等价核对、P5 229 run / 228 pass / 1 skip、P3 56 pass。旧站点运行与 PARTIAL 不改写。

## 固定原件与实际接入

| 项目 | 实际证据与范围 |
|---|---|
| 上游版本 | tag `1.22`，tag object `a58e03033307122cd56cb2c60259c377b49230dd`，源码 commit `e6160529e70a8c7a06b9a5f190d69aa35c4c62f5` |
| 本地原件 | `_local_data/external_games/open_adventure/upstream`，项目隔离、Git 忽略；没有全球安装游戏或新依赖 |
| 许可证 | BSD-2-Clause，COPYING SHA256 `1736e44e3dd4fab08c3291434c45ccf7f6933704ed0648516afb056641fcf306`；有限回放再分发说明见 [NOTICE](THIRD_PARTY_NOTICE.md) |
| 构建 | 官方 Makefile，现有 macOS SDK / clang / libedit 和已存在 Python/PyYAML；没有手改生成源码。命令、环境、原始 stdout/stderr 见 [BUILD_AND_RUN](BUILD_AND_RUN.md) 和 [原始构建/测试记录](BUILD_TEST_LOGS.json) |
| 官方功能测试 | `make check`：115 tests / 0 failures，exit 0。父代理独立重跑也为 115 / 0。可选 pylint/cppcheck/spellcheck 缺失，被上游忽略；不能声称这些静态检查通过 |
| 游戏源码 | 256 个 tracked 文件快照 SHA256 `6eec67f3b0dffc072bb2b00d0e377335e6e9e13182bb4a8b2d72c6fa199b5b77`；构建/回放前后相同，父代理核对 tracked diff 为空 |
| 薄入口 | [runner.py](../../tools/open_adventure_v0/runner.py)：新进程重置、提交原生命令、记录完整玩家文字/错误/退出码、同输入回放；不解析隐藏状态、不替代执行器 |
| 接口缺项 | **整局回放**而非实时逐回合 Agent API；文本保留命令/回答顺序，但未生成动作级结构化世界回执。源码原生支持 save/resume，本轮未封装 checkpoint/fork，也不假称已提供 |

构建没有取得 catb 发布包（请求不可达）；实际来源是官方 GitLab 的固定 tag。`-o` 是上游原生 stdin 模式。runner 只移除 fixture 的注释/空行，必要时追加原生 `quit / yes`；`input.txt` 和 `execution_stdin.txt` 分别保留原始与实际发送内容。游戏可能在死亡时提前退出，末尾输入不一定被消费。

## 三个原生短场景的真实结果

这三条是**上游已知回归脚本**，不是规划器发现的解，不是未见测试集，也不是 NPC 自主性效果实验。

| 场景与原始输出 | 固定 seed | 实际机制及结果 | 不可声称 |
|---|---:|---|---|
| [鸟与玉](runs/native-bird-free-and-carry-20261014T010515Z-842eac/stdout.txt)，`tests/dropcagedbird.log` | 1495951709 | 持 rod 抓鸟失败；放下 rod 后成功；到合适地点释放鸟、挥 rod，鸟带回玉，`take jade` 返回 OK；另保留喂蛇失败。exit 0，26 turns，59/430 分 | 系统发明因果链或学到了新动作 |
| [海盗夺宝](runs/native-pirate-carry-20261014T010515Z-10819a/stdout.txt)，`tests/pirate_carry.log` | 1837473132 | 取得银器后，海盗遇到玩家并抢走宝物，之后正常退出；源码原生把宝物移向海盗宝箱位置。exit 0，44 turns，67/430 分 | 海盗有我们验证过的信任/敌意记忆；文本接口提供精确隐藏坐标 |
| [矮人过程](runs/native-dwarf-process-20261014T010515Z-012dc0/stdout.txt)，`tests/dwarf.log` | 1494912171 | 原生遭遇、投刀、挡路；后续玩家被刀击中并拒绝复活。exit 0，55 turns，81/430 分；**角色死亡是真实负面结果，不是目标成功** | exit 0 等于游戏通关，或追踪 flag 等于完整人物意图 |

每场保存原始输入、实际 stdin、完整 stdout/stderr、run.json 的版本、二进制/源码哈希及同二进制重复执行结果。原始三场用 binary SHA256 `9be0dea71ef185969f729f6c5544e8b9d67f1d59fa2221b61a4c1fc41c23f122`，三场 stdout/stderr 均逐字节重复一致。随后相同源码的重建二进制哈希不同，详见构建记录；不改写原始归属。父代理独立以中间重建 binary `0fa94664…91500b3` 复放**同三条输入**，退出码和输出亦相同，并核验记录中 stdin/stdout/stderr 的 SHA256。它支持本机这些回放的复现，不是跨平台二进制同一性或任意随机运行保证。

官方功能测试会按其自己的协议比较上游 `.chk`。本 runner 的 `-o` 输出在初始化/提示符格式上不同，故三场记录比较的是同模式直接执行输出，**没有把不同模式的 stdout 说成与 `.chk` 逐字节相同**。官方测试通过与 wrapper 透明性是两项不同证据。

## 原生状态到底做了什么

完整 producer→consumer、源码行链接与可见性只在 [MECHANISMS](MECHANISMS.md)维护。父代理核对了主循环：`do_move → dwarfmove（内部 guard）→ do_command`，玩家位置没有变化也可能更新 NPC；澄清输入和强制移动使“一行命令=一次 NPC tick”不成立。

| 游戏已有能力 | 在固定规则中可组合（本轮未接 Planner） | 缺失或未证实的作者语义 |
|---|---|---|
| 物品位置/属性、地图/通路、原生谜题、随机过程、矮人阶段及 `seen/loc/oldloc` 追踪、海盗夺宝 | 利用真实前提组合抓鸟/放鸟/挥杆/取物，选择路线，依据真实拒绝修订未来命令 | 丰富承诺、互惠、事件归因、关系恶化的判据、可控作者剧情接口和持续主观目标 |

`seen` 是真实被后续追踪/挡路规则消费的经历标记，是局部原生历史影响的例子；它不是完整经历日志或社会关系。已审查 NPC 路径没有证据支持丰富人物历史机制。不要给它补 `trust/loan_history/refuse_if_late` 再宣称原游戏具备这些能力。

审计可读内部 `game_t`，未来玩家/角色接口只能取合法输出；隐藏变量不能偷偷变成 observation。可复现未来需要完整状态、随机流游标、规则/数据版本与未来输入；只有相同可见文本不足以证明未来相同。fixture 的 `seed` 是实验控制，不是未来规划器可以为剧情随意选择的动作。

若下一题需要原生社会状态，报告列出有官方 producer/consumer 依据的 **Cataclysm-DDA 只读候选**：任务结果更新 opinion，后续互动读取它。其完整历史、接口、可复现版本均未核定；它也不是纯文本 IF。本轮没安装第二款游戏，不把候选当已准入环境。

## 接入测试、发布与停止

入口的离线契约测试及父代理验收记录见 [VALIDATION](VALIDATION.md)。CI 新增的 runner job 只跑 mock/临时假进程，不下载游戏，不证明 macOS 原版回放在 Ubuntu 上运行。exact-head CI 状态以 GitHub Actions 为准；旧 E0 H02 的 BUDGET/UNREACHABLE 波动独立保留，不改预算刷绿。

公开范围仅本轮适配代码、报告、三条原生短回放和测试/构建证据；不含私有讨论、凭证、上游完整源码、游戏资源包或二进制。原输入已私有归档并从附件入口移至废纸篓，可恢复。

**下一步需要选择研究对象，不继续施工：**固定规则的物品/世界因果候选可使用本游戏；丰富人物关系须先核查更合适的原生环境。未来 LLM 可以提合法候选，或单独提内容/语义扩展；后者须列出规则修改、权限、前提/效果与影响，获批并验证新游戏版本后才能执行。本轮无 LLM 调用、训练、新 Director、通用 DSL/世界模型或规则扩展。旧 C++、E0、历史 RESULTS 和 main 均不动。
