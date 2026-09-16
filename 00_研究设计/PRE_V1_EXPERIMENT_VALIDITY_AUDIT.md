# Pre-V1 experiment validity audit

日期：2026-09-16

这份审计把旧工程、proxy 与即将开始的研究动力学分开。它不删除、不重算、不覆盖任何旧结果；旧结果的数值与 commit provenance 仍按原样保留。

## 身份分类

| 身份 | canonical id | 证据地位 | 允许的用法 |
|---|---|---|---|
| 旧 C++ 规则 | `LegacyReferenceRuleDynamicsV0` | 冻结工程/回归基线 | replay parity、机制 fixture、历史复现 |
| 旧 Python Theory-S | `ExpectedEffectEMAProxyV0`（历史显示名：Theory-S） | expected-possession-effect proxy | 仅历史 diagnostic；不得写成角色动力学验证 |
| 新研究对象 | `ResearchDynamicsV1` | 未冻结候选 | 只做机制 sanity 与受控 intervention，尚无正式训练/测试结论 |
| Demo living | `DemoLivingDynamicsV0/V1` | application sandbox | 只服务展示与生活感调试，不提供科研证据 |

T14/T20、LIGHT、AGAIN 与旧 Replay 输出均属于 development/history artifacts。它们的原始文件、结果、seed、manifest 与旧解释保留；本页只改变当前路由与主张边界，不追写历史结果。

## 依赖与主张边界

- Shared Runtime Kernel 只提供时间、W/O 边界、动作 settlement、gate 与 trace。
- dynamics model 显式拥有 `X`、`S` 更新和 `π` construction；replay adapter 不得隐式选择旧 reference。
- 旧结果不能证明 `ResearchDynamicsV1`、心理机制、自然性或泛化收益。
- 正式 Paper-0 test 仍被独立行为真值、候选集与 observation audit gate 阻塞。

当前状态：`RESEARCH_DYNAMICS_V1 = READY_FOR_INDEPENDENT_REVIEW`；未 CLOSED。
