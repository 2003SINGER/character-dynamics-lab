# Character Dynamics Reference Demo（Codex 生成参考实现）

这是一个**只供阅读、运行和拆解**的 C++17 控制台参考系统。它和用户亲自编写的 `E:\Character Dynamics Demo` 完全分离：不读取、复制、修改或替代后者。

它不证明任何研究结论。这里的状态、分数、规则和人格参数只是为了让你看见一条完整、可追踪的计算链：

```text
W → O → X → S → D → π(A^char) → CharacterActionPlan[a^world...] → W'
```

## 它会做什么

- 同一初始房间世界运行两次：拖延/低自控、较高自控/任务导向；
- 默认展示每次使用固定随机种子、连续 12 个离散决策点；每个动作直接结算并推进 1–480 分钟的模拟时间；
- `--batch` 会生成 32 个固定可复现、每个字段均位于 `[0,1)` 的合成人格，针对 8 个世界情景种子各运行 256 步，共保存 65,536 个决策点；每次运行在所给根目录下创建唯一 `run_<timestamp>_<suffix>/`，不会覆盖旧结果；人格参数、世界事件时间、天气、温度和任务 effort 配置均可由输出文件审计；
- W 维护时间、Scene、角色所在 Room、天气、通用 `WorldTask`、钱包、未读消息和确定性世界事件；Room 自己维护灯光、闹钟、窗帘、温度和室内对象；
- `Scene(home) → Room(student room) → Object` 是当前世界层级。手机、电脑、书桌、床、门、灯、闹钟、窗户都是 Room 的 Object；Object 提供 affordance，再自然给出浏览、网购、学习、休息/睡觉、上厕所、买饭、开/关灯、关闭闹钟、开/关窗帘等候选；
- 角色并不按脚本轮流执行动作：每步由当前 `S + P` 算动作 activation；低于 threshold 的动作被抑制，其余动作按概率采样。床和门只让行动成为可能，不决定角色必定去睡或出门；
- `O` 是跨决策点保持的字段记录；每项有 `known/stale/unknown`、来源和观察时刻。当前房间对象通常来自 `direct_room_visual`，闹钟来自同场景的 `direct_room_auditory`；
- `A^W → A^O → π(A)` 已显式输出：W 给出合法动作，O 只暴露角色已知物品对应的动作。这个房间通常两者相同，但层没有被省掉；
- 每次选择的 `A^char` 由 W 自行展开为 typed `CharacterActionPlan`，其中含 `set activity / increment counter / adjust value / set room flag / advance time` 等 `a^world`；调用方不能提交 primitive 让 W 执行。日志会并列打印 W 生成的计划 primitive 与实际结算 primitive，例如睡眠被冷醒后时间 primitive 会缩短；
- `X` 是 `(ΔO, O, old S, P) → Appraisal` 的可替换小函数；它不直接读取原始 `WorldOutcome`。S 包含无聊、疲劳、任务压力、满意度、饥饿、如厕需求、焦虑、屏幕疲劳、购买欲与任务绑定的 `TaskCommitment`；学习 action 仅代表一次 session，W 以连续 effort、时长与可复现的小幅种子扰动结算任务推进。截止时间先由 W 产生事件、再经 O 的任务字段进入 X；
- 打印动作前后 W、O、X 输入、X、requested/applied StateDelta 与 S、D 的 activation/threshold/概率、世界结算、外部事件与来源；
- 不实现 LLM、UI、异步、玩家可见延迟、多角色、P 学习或研究用回放评测。已有睡眠/温感/窗帘的局部 O 信息差演示，但尚无正式信息干预实验。

## 阅读顺序

1. `Src/main.cpp`：程序入口；
2. `Src/simulation.cpp`：整条 W→O→X→S→D→A→W 链如何编排；
3. `Inc/simulation_time.h`、`Inc/object.h`、`Inc/scene.h`：时间、物品 affordance 与房间局部状态；
4. `Inc/*.h`：其余每个量的接口和所有权；
5. `Src/world.cpp`、`Src/decision.cpp`：世界结算与动作分布；
6. `Src/appraisal.cpp`、`Src/state.cpp`：当前规则 Appraisal 与状态更新的调用边界；Appraisal 仍携带直接 delta，并非已实现完整语义 X。

完整机制与本实现的差距统一见[当前实现进度](../00_研究设计/当前实现进度.md)和[未决问题](../00_研究设计/未决问题与机制候选.md)。本页维护构建、运行和源码导航，不另列研究 TODO。

## 当前代码的边界

- `simulation_time` 只负责离散时间运算；它刻意不叫 `time.h`，避免遮蔽 C++ 标准库依赖的 C 头文件；
- `Scene` 是局部 W 边界，持有一个或多个 `Room`；`Room` 是 Scene 内的场所对象，持有室内 `Object` 容器与局部物理状态；`Object` 才是手机、床、门等具体可交互物。`World` 持有 Scene、角色位置、跨场景时间/天气/任务/钱包，以及动作的最终结算；
- `ActionDefinition` 是唯一的动作显示名/默认时长目录。`World::expand_action` 只供解释/trace；`World::settle(A^char)` 在 W 内部重新生成 primitive、复核当前 W 并结算其后果；`World::execute` 是同一条受限路径的便捷包装；
- `CharacterActionPlan` / `WorldPrimitive` 是人物动作与 W 写入之间的 typed 边界。policy 只选择 `A^char`，不能直接改 W，也不能提交伪造 primitive；W 结算后才确认 actual primitive。新的场景效果应新增明确 primitive 类型及其 W executor，而不是把字段名塞进字符串；
- `ObservationFact` 是 O 中 room light、温度、时间、任务等信息的唯一存储，避免“同一事实既在 facts 又在几个 bool/int 字段”逐渐不同步；
- `X` 只读取 O/ΔO、旧 S 和 P；`D` 只读取 O、S、P 和已经由上游形成的 A^O。W 只在上游给出 A^W、在下游校验/结算；这样 policy 不会绕过 O 偷看 W；
- `TaskCommitment` 只在 W 接受所选动作后写回 S；学习 session 建立或恢复对未完成 task 的承诺，吃饭、如厕和恢复动作使其暂停，task 完成时关闭。暂停中的承诺只有在任务状态和学习 affordance 仍被 O 已知、且疲劳/饥饿/如厕需求低于 v0 门槛时，才会重新提高学习动作 activation；这不是规划器。被拒绝或未来因异步失效的计划不应被错误记成角色已承诺的行为。睡眠提前醒来是当前明确的已结算中断语义，其实际时间 primitive 会被记录；
- `Simulation` 仍故意保留为可读的编排层。不要把 W 结算、X 解释、S 更新和 D 选择硬塞进一个万能规则表：它们正是后续替换机制时需要各自独立的边界。

## 构建与运行（本机 MinGW）

本项目源码仍在本目录；但 MinGW `mingw32-make` 不能可靠处理其中的中文上级路径。因此本机创建了一个不复制文件的 ASCII junction：`D:\Tools\cpp-src\character-dynamics-reference`。从该 junction 配置，build 输出也位于 ASCII 路径：

```powershell
Set-Location D:\Tools\cpp-src\character-dynamics-reference
cmake --preset mingw-debug
cmake --build --preset build
D:\Tools\cpp-build\character-dynamics-reference\character_dynamics_reference.exe
D:\Tools\cpp-build\character-dynamics-reference\character_dynamics_reference.exe --batch D:\Tools\character-dynamics-batch
ctest --preset test
```

批量目录包含 `metadata.txt`（配置版本与构建时 Git revision）、`personalities.csv`、`trajectories.csv` 和 `runs.csv`。`trajectories.csv` 明确区分 `pre_*` 决策时状态、`outcome_*` 结算事实与 `post_*` 结算后世界/承诺，避免把同一行误当作同一时刻的快照。

VS Code 已提供 `CMake Tools` + `clangd` 本机配置。打开本目录后选择 preset `mingw-debug`，再运行 Configure / Build 即可。

## 重要边界

- `O` 是独立的角色视图；当前同房间可直接看见绝大多数对象，但字段级来源已经存在。窗帘关上时，`outside.weather` 不再刷新、保留旧值并标为 `stale`；未来场景、消息或记忆可复用同一记录接口。
- `X` 是受限的 appraisal 标签和数值变化，不是 LLM，也不是“真实心理学”。它现在只演示接口和简单函数关系。
- `P` 在每次 run 内固定，只在两次对照运行之间改变。当前实际使用拖延、自控、休息偏好、刺激寻求、任务焦虑敏感度、屏幕疲劳敏感度、需求响应与行动噪声。
- 人物级动作直接结算：例如 `go_to_bathroom` 会直接完成一次门外短途、推进 15 分钟，并在下一决策点经 X 降低如厕需求；它不模拟走路或中间动画。
- `sleep_at_bed` 最长为 8 小时：W 的时钟和排程事件继续运行，O 的普通视觉/时间字段在区间内冻结；但温度可经 `direct_room_thermal_while_asleep` 局部写入 O。固定场景中温度在 16:00 降到 17°C，会提前唤醒角色；醒来后下一决策点才用场景感知更新其余 O 字段。它演示的是暂时的 `W ≠ O`，不是完整睡眠模型。
- 这些字段和参数只是为了搭接口与观察轨迹；是否保留及其具体动力学仍须由后续机制阅读和实验决定。
- 规则化状态和策略的价值仍须靠后续文献、基线、干预和实验验证。
