# Runtime / Dynamics / Demo 架构边界 v1

## 项目定位

Character Dynamics 不是一条已经被证明的心理公式，而是一个共享、可审计、持续运行的角色执行 Runtime，加上可替换的 Character Dynamics Model，再加 Evaluator、Optimizer 与 Applications。

共享的是执行机制；尚未验证的行为假设必须通过 model 插槽隔离。

## 四类 ownership

1. **Shared Runtime Kernel**：权威 W、Scene/Room/Object、W→O 信息边界、时钟与 Scheduler、RunningAction、WorldEvent/Outcome、DecisionGate、ActionIntent、W validation/settlement、trace/replay，以及对已有 π 的 RNG sampling。
2. **Dynamics Model**：X/appraisal、U 与 S 演化、commitment transition、候选集与 π 构造。这里的系数和规则是候选行为假设，不是 Kernel invariant。
3. **Research Track**：比较 Reference、Theory-S、ablation 等 dynamics candidate，保留 protocol、数据隔离和证据边界。
4. **Application/Demo**：使用明确选择的 model 做 mechanism fixture 或 living sandbox；Demo naturalness 没有科研证据权。

```text
                 ContinuousRuntime (one shared execution kernel)
                         │ explicit CharacterDynamicsModel
                 ┌───────┴────────┐
        ReferenceRuleDynamicsV0   DemoLivingDynamicsV0
          mechanism/reference       living sandbox/free-run
                 │
          research fixtures / replay
```

Engine 是产品组合词：`Engine = Runtime Kernel + explicitly selected Dynamics Model`，不是唯一的 state/policy 实现。

## 变更分类

- W 拒绝手机后，O 已知道不可用但 A^O 仍保留 UsePhone：Runtime information/ownership invariant，可修 Kernel。
- free-run 中角色饿到 0.8 仍刷手机：behavior/naturalness issue，只能改 DemoLivingDynamics 或另开 research candidate。
- 实验显示新的 S decay law 更好：research dynamics proposal，建立新 candidate + protocol，不覆盖 Reference V0。

## Promotion rules

Demo heuristic 不因“看起来更自然”进入 Reference/Research；Research candidate 也不因单次结果自动成为 Demo 默认。两者都必须显式版本化、记录 protocol 和证据边界。

共享 `CharacterState` schema 不代表字段语义或 update law 已被科学验证。Demo 轨迹、分数、视觉展示和用户印象默认 `demo_only=true`、`research_evidence=false`。
