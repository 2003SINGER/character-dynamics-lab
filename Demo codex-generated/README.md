# Character Dynamics Reference Demo（Codex 生成参考实现）

这是一个**只供阅读、运行和拆解**的 C++17 控制台参考系统。它和用户亲自编写的 `E:\Character Dynamics Demo` 完全分离：不读取、复制、修改或替代后者。

它不证明任何研究结论。这里的状态、分数、规则和人格参数只是为了让你看见一条完整、可追踪的计算链：

```text
W → O → X → S → D → π(A) → A → W'
```

## 它会做什么

- 同一初始房间世界运行两次：拖延/低自控、较高自控/任务导向；
- 每次运行固定随机种子，连续 12 个离散决策点；每个动作直接结算并推进 1–60 分钟的模拟时间；
- W 维护时间、房间物品、灯光、闹钟、窗帘、天气、任务进度、钱包、未读消息和确定性世界事件；
- 房间以对象清单表示：手机、电脑、带学习材料的书桌、床、门、灯、闹钟、窗户。对象提供 affordance，再自然给出浏览、网购、学习、休息/睡觉、上厕所、买饭、开/关灯、关闭闹钟、开/关窗帘等候选；
- 角色并不按脚本轮流执行动作：每步由当前 `S + P` 算动作 activation；低于 threshold 的动作被抑制，其余动作按概率采样。床和门只让行动成为可能，不决定角色必定去睡或出门；
- `O` 是跨决策点保持的字段记录；每项有 `known/stale/unknown`、来源和观察时刻。当前房间对象通常来自 `direct_room_visual`，闹钟来自同场景的 `direct_room_auditory`；
- `A^W → A^O → π(A)` 已显式输出：W 给出合法动作，O 只暴露角色已知物品对应的动作。这个房间通常两者相同，但层没有被省掉；
- `X` 是 `(O, previous WorldOutcome) → Appraisal` 的可替换小函数；S 包含无聊、疲劳、任务压力、满意度、饥饿、如厕需求、焦虑、屏幕疲劳和购买欲，并有一个轻量的 persistent intention 占位；
- 打印动作前后 W、O、X 输入、X、StateDelta/S、D 的 activation/threshold/概率、世界结算、外部事件与来源；
- 不实现 LLM、UI、异步、玩家可见延迟、多角色、P 学习、真正的 O 信息差或回放评测。

## 阅读顺序

1. `Src/main.cpp`：程序入口；
2. `Src/simulation.cpp`：整条 W→O→X→S→D→A→W 链如何编排；
3. `Inc/simulation_time.h`、`Inc/object.h`、`Inc/scene.h`：时间、物品 affordance 与房间局部状态；
4. `Inc/*.h`：其余每个量的接口和所有权；
5. `Src/world.cpp`、`Src/decision.cpp`：世界结算与动作分布；
6. `Src/appraisal.cpp`、`Src/state.cpp`：语义解释与状态动力学怎样分开。

## 当前代码的边界

- `simulation_time` 只负责离散时间运算；它刻意不叫 `time.h`，避免遮蔽 C++ 标准库依赖的 C 头文件；
- `RoomObject` 只描述一个场景实例可提供什么动作、现在是否可用；`RoomScene` 承担房间内灯光、温度、窗帘、闹钟和物品集合；`World` 承担跨场景的时间、天气、任务、钱包和动作结算；
- `ActionDefinition` 是唯一的动作显示名/默认时长目录。动作是否可用仍由 `World::can_execute` 判断，动作对 W 的后果仍由 `World::execute` 判断；
- `ObservationFact` 是 O 中 room light、温度、时间、任务等信息的唯一存储，避免“同一事实既在 facts 又在几个 bool/int 字段”逐渐不同步；
- `Simulation` 仍故意保留为可读的编排层。不要把 W 结算、X 解释、S 更新和 D 选择硬塞进一个万能规则表：它们正是后续替换机制时需要各自独立的边界。

## 构建与运行（本机 MinGW）

本项目源码仍在本目录；但 MinGW `mingw32-make` 不能可靠处理其中的中文上级路径。因此本机创建了一个不复制文件的 ASCII junction：`D:\Tools\cpp-src\character-dynamics-reference`。从该 junction 配置，build 输出也位于 ASCII 路径：

```powershell
Set-Location D:\Tools\cpp-src\character-dynamics-reference
cmake --preset mingw-debug
cmake --build --preset build
D:\Tools\cpp-build\character-dynamics-reference\character_dynamics_reference.exe
ctest --preset test
```

VS Code 已提供 `CMake Tools` + `clangd` 本机配置。打开本目录后选择 preset `mingw-debug`，再运行 Configure / Build 即可。

## 重要边界

- `O` 是独立的角色视图；当前同房间可直接看见绝大多数对象，但字段级来源已经存在。窗帘关上时，`outside.weather` 不再刷新、保留旧值并标为 `stale`；未来场景、消息或记忆可复用同一记录接口。
- `X` 是受限的 appraisal 标签和数值变化，不是 LLM，也不是“真实心理学”。它现在只演示接口和简单函数关系。
- `P` 在每次 run 内固定，只在两次对照运行之间改变。当前实际使用拖延、自控、休息偏好、刺激寻求、任务焦虑敏感度、屏幕疲劳敏感度、需求响应与行动噪声。
- 人物级动作直接结算：例如 `go_to_bathroom` 会直接完成一次门外短途、推进 15 分钟，并在下一决策点经 X 降低如厕需求；它不模拟走路或中间动画。
- `sleep_at_bed` 最长为 8 小时：W 的时钟和排程事件继续运行，O 的普通视觉/时间字段在区间内冻结；但温度可经 `direct_room_thermal_while_asleep` 局部写入 O。固定场景中温度在 16:00 降到 17°C，会提前唤醒角色；醒来后下一决策点才用场景感知更新其余 O 字段。它演示的是暂时的 `W ≠ O`，不是完整睡眠模型。
- 这些字段和参数只是为了搭接口与观察轨迹；是否保留及其具体动力学仍须由后续机制阅读和实验决定。
- 规则化状态和策略的价值仍须靠后续文献、基线、干预和实验验证。
