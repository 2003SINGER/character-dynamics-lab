# 父代理验收：前两步开发检查点

日期：2026-10-06。范围：Praxish 原件运行/机制解释、共同小场景。状态保留 `READY_FOR_INDEPENDENT_REVIEW`；不是 `CLOSED`，没有完成完整 goal 的基线挑战及玩家意义判断。

## 观察到的实际差异

| 条件 | turn 0 | turn 2 | turn 4 |
|---|---|---|---|
| 没有请求 | 开始备货 | 完成备货（5） | 工作已完成，无候选 |
| 有请求，默认请求权重 10 | 开始备货 | 回应请求（11），备货仍 working | 完成备货（15） |
| 同一请求，作者将请求权重设为 1 | 开始备货 | 完成备货（5 > 回应的 2） | 回应请求（6） |

请求在 turn 1 创建 pending 实例，不直接选响应。默认 turn 2 的答复分数为保留 working 的 1 + served 的 10；完成备货得 5。后续完成的 15 包括已经满足的 served=10，**不是又获得十五点进展**。这些权重是作者设置，不是学出的参数，也不是最优心理机制。

## 父代理独立检查

1. 全读 noninteractive 三个源文件及包内 README；读九页论文并视觉核对活动定义。正式版本和执行机制见[论文/源码报告](../../01_文献/精读_Praxish论文与原始实现_2026-10-06.md)。
2. 用独立 Node VM 按原顺序执行原文件，固定同 seed 两次日志及最终 DB 相同；实际包含四阶段与 83 条日志。再用最终 runner 的 `original` 命令复跑；不是只读代码或依赖 Luna 的汇报。
3. 不调用 harness 的评分函数，直接用原 API 重建场景，逐候选执行后果、查询目标，核对候选数、分数与实际 post-facts；另用**无 observer 的原 tick**与 harness 轨迹比较，两个条件的选择和后果一致。
4. 单独降低请求权重，实测先完成备货、后回应；没有事件强制响应。visitor 的角色条件没有给它 worker 的动作。
5. 最终 snapshot `test`：11 项全部通过。覆盖原件字节、原示例复跑、事件、角色、最大分选择、工作保留/完成、偏好敏感性、重复轨迹、公开摘录与 CLI 缺源/不覆盖。它们是 fixture 测试，不是独立玩家实验。
6. 最终 paired CLI 两次输出 trace **字节相同**；成功 run ID 再调用明确报 `EEXIST`，既有 manifest 不变；manifest 的 scenario/runner SHA 与当时磁盘字节一致。
7. 隔离副本缺少上游 source 的 CLI 负控报失败，并保留 failed manifest/error。验收中真实失败的 paired02 同样保留，没有将其删掉冒充从未失败。

## 运行证据位置

均位于本机忽略目录 `outputs/praxish_activity_pilot_v0/runs/`，不宣称远端能取得这些完整本机结果：

- 最终原件复跑：`parent-original-review-20261006-03/original_demo/`。
- 最终 paired 复跑：`parent-paired-review-20261006-03/`、`parent-paired-review-20261006-04/`。
- 中途失败：`parent-paired-review-20261006-02/error.json` 与 failed manifest；当时新增 roles 记录误读 `sandbox.practiceDefs`，修正为 `state.practiceDefs` 后用新 run ID 重跑。
- 最早 CLI 负控暴露 macOS 临时路径别名使 main-module 判断失效；已使用 realpath 比较并测试实际缺源退出码。仅清理父代理生成的临时 PNG/隔离副本，不删除实验原件或正式 run。

完整本机产物可通过[README 命令](README.md#run)重新生成；远端审阅的[生成摘录](examples/paired_choice_excerpt.json)由测试与新 trace 对照。上游源码仍只在忽略缓存，不 vendor。

## 能判什么，不能判什么

**前两步的开发证据已具备：**能解释原件为何选择动作；共同场景可重跑、可观察条件差异，有自己的工作、外来请求及明确后果。

**没有完成：**传统 utility/BT/GOAP 的匹配比较、新增情境的真实作者劳动记录、玩家感知意义判断。也没有验证浏览器 UI、连续 Runtime 集成、长时生活合理性或 RPG 泛化。终态无动作只反映有限任务结束，不计作行为崩坏，也不因此声称生活合理。

下一动作只有一个：与用户讨论这个小场景是否足以承载后续匹配基线挑战；不先新增机制或扩大模拟。
