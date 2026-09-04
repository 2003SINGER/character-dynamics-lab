# Character Dynamics Reference Demo（Codex 生成参考实现）

这是一个**只供阅读、运行和拆解**的 C++17 控制台参考系统。它和用户亲自编写的 `E:\Character Dynamics Demo` 完全分离：不读取、复制、修改或替代后者。

它不证明任何研究结论。这里的状态、分数、规则和人格参数只是为了让你看见一条完整、可追踪的计算链：

```text
W → O → X → S → D → π(A) → A → W'
```

## 它会做什么

- 同一初始房间世界运行两次：拖延/低自控、较高自控/任务导向；
- 每次运行固定随机种子，连续 12 个离散决策点；每个动作直接结算并推进 1–60 分钟的模拟时间；
- W 维护时间、房间物品、灯光、任务进度、钱包、未读消息和确定性外部事件；
- 房间以对象清单表示：手机、电脑、带学习材料的书桌、床、门、灯。对象提供 affordance，再自然给出浏览、网购、学习、休息、上厕所、买饭、开/关灯等候选；
- 角色并不按脚本轮流执行动作：每步由当前 `S + P` 算动作 activation；低于 threshold 的动作被抑制，其余动作按概率采样。床和门只让行动成为可能，不决定角色必定去睡或出门；
- `X` 是 `(O, previous WorldOutcome) → Appraisal` 的可替换小函数；S 包含无聊、疲劳、任务压力、满意度、饥饿、如厕需求、焦虑、屏幕疲劳和购买欲；
- 打印动作前后 W、O、X 输入、X、StateDelta/S、D 的 activation/threshold/概率、世界结算、外部事件与来源；
- 不实现 LLM、UI、异步、玩家可见延迟、多角色、P 学习、真正的 O 信息差或回放评测。

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

- `O` 是独立的角色视图；但这个房间版目前直接刷新，且为方便 vibe coding，`D` 直接从 W 的合法 affordance 取动作。它故意没有实现研究版的 `A^O`、`stale`、`unknown` 或信息遮挡。
- `X` 是受限的 appraisal 标签和数值变化，不是 LLM，也不是“真实心理学”。它现在只演示接口和简单函数关系。
- `P` 在每次 run 内固定，只在两次对照运行之间改变。当前实际使用拖延、自控、休息偏好、刺激寻求、任务焦虑敏感度、屏幕疲劳敏感度、需求响应与行动噪声。
- 人物级动作直接结算：例如 `go_to_bathroom` 会直接完成一次门外短途、推进 15 分钟，并在下一决策点经 X 降低如厕需求；它不模拟走路或中间动画。
- 这些字段和参数只是为了搭接口与观察轨迹；是否保留及其具体动力学仍须由后续机制阅读和实验决定。
- 规则化状态和策略的价值仍须靠后续文献、基线、干预和实验验证。
