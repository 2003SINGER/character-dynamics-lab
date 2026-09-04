# Character Dynamics Reference Demo（Codex 生成参考实现）

这是一个**只供阅读、运行和拆解**的 C++17 控制台参考系统。它和用户亲自编写的 `E:\Character Dynamics Demo` 完全分离：不读取、复制、修改或替代后者。

它不证明任何研究结论。这里的状态、分数、规则和人格参数只是为了让你看见一条完整、可追踪的计算链：

```text
W → O → X → S → D → π(A) → A → W'
```

## 它会做什么

- 同一初始房间世界运行两次：拖延/低自控、较高自控/任务导向；
- 每次运行固定随机种子，连续 12 个离散 step；
- 房间以对象清单表示：手机、电脑、带学习材料的书桌、床、门；对象各自提供可供性（affordance）；
- `SceneFilter` 只把看得见且可用的对象及其可供性写进 `O`。决策层再从中提出 `use_phone`、`study_at_desk`、`go_to_bathroom`、`get_meal` 等候选；
- 角色并不按脚本轮流执行动作：每步由当前 `S + P` 对这些候选评分并采样。床和门只让行动成为可能，不决定角色必定去睡或出门；
- 打印 `W`、`O`、`X`、`StateDelta/S`、`D/π(A)`、动作与 `W` 结算来源；
- 不实现模拟时钟、LLM、UI、异步、玩家可见延迟、多角色、P 学习或回放评测。

## 阅读顺序

1. `Src/main.cpp`：程序入口；
2. `Src/simulation.cpp`：整条 W→O→X→S→D→A→W 链如何编排；
3. `Inc/*.h`：每个量的接口和所有权；
4. `Src/world.cpp`、`Src/decision.cpp`：世界结算与动作分布；
5. `Src/appraisal.cpp`、`Src/state.cpp`：语义解释与状态动力学怎样分开。

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

- `O` 是独立的角色视图；这个单房间例子只做确定性直接刷新，尚未演示 `stale/unknown` 或复杂信息遮挡。
- `X` 是受限的 appraisal 标签和数值变化，不是 LLM，也不是“真实心理学”。
- `P` 在每次 run 内固定，只在两次对照运行之间改变；它调制状态更新和决策分数，不写死某个动作。当前已经实际使用 `procrastination`、`self_control`、`rest_preference` 三个参数。
- 新加入的 `hunger`、`bathroom_urge` 只是演示“门的动作自然带来新的状态后果”；它们不是一套心理需求理论。
- 规则化状态和策略的价值仍须靠后续文献、基线、干预和实验验证。
