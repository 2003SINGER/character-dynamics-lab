# DemoLivingDynamicsV1 Coupling Specification

状态：`DESIGN SPECIFICATION / DEMO-ONLY`

本文件是 `DemoLivingDynamicsV1` 的唯一机制设计入口。它规定状态区间、自然更新 owner、跨状态耦合、动作影响、人格阈值偏移与需要验证的非单调关系。它不是心理学验证，也不是对 ReferenceRuleDynamicsV0、Theory-S 或 Paper-0 的修改。

## 不可越过的边界

- 只属于 Application/Demo；Reference dynamics、Shared Runtime Kernel、W/O/S schema、Personality 字段和 ActionType 不变。
- 生理库存 `hunger`、`bathroom_urge` 各只有一个 continuous owner：`metabolism_rate` 与 `bathroom_accumulation_rate`。不得再叠加旧固定 drift。
- 所有心理量必须由有语义的情境、动作结果或状态耦合更新；禁止“时间过去所以固定增减”。
- 先按本 spec 实现，再跑同一 frozen 128×48h batch；不得先看结果反调系数。

## 通用区间语义

实现提供 `ActivationZone` helper。阈值进入关系函数，而不只是 action eligibility：区间变化必须改变更新、耦合或动作 family relevance。跨阈值采用平滑过渡；需要防抖的关系使用已有 trace/context 实现 hysteresis 或 cooldown，不新增共享 state 字段。

| Zone | 默认含义 |
|---|---|
| low | 资源充足/几乎不驱动行为 |
| normal | 可感知但不主导 |
| activated | 开始改变注意与行为倾向 |
| high | 明显影响持续行为与恢复需求 |
| extreme | 强约束、失调风险或特殊动作相关性 |

## State coupling table

| State | Meaning / natural owner | Zones (thresholds) | Cross-state and action semantics | Personality effect |
|---|---|---|---|---|
| `hunger` | 生理库存；`metabolism_rate` 唯一积累 owner | 0–.25 satiated；.25–.50 neutral；.50–.70 hungry；.70–.88 very hungry；≥.88 urgent | 低区几乎不驱动 eating；activated 后 meal relevance 平滑上升；urgent 才显著压制普通动作。成功 meal 按当前区间产生饱腹 relief，不超过合理上限 | `need_response` 小幅移动 noticeable/urgent 阈值；不是乘整个 drive |
| `bathroom_urge` | 生理库存；`bathroom_accumulation_rate` 唯一积累 owner | 0–.25 comfortable；.25–.50 noticeable；.50–.75 pressing；.75–.90 high；≥.90 urgent | 只有 high/urgent 才强压制动作；成功 bathroom 按区间 relief | `need_response` 移动 pressing/urgent 阈值 |
| `fatigue` | 清醒与体力负荷库存；由 activity/rest/sleep context 更新 | 0–.25 fresh；.25–.55 normal；.55–.80 tired；≥.80 very tired；≥.92 exhausted | fresh/normal 几乎无 study penalty；tired 后 endurance cost；very tired 提升 rest；exhausted 强推 sleep。白天 fatigue 不直接等于 sleep，夜间 circadian 才增强 sleep relevance | `rest_preference` 移动 rest threshold；`self_control` 改变 tired 区的持续能力 |
| `task_pressure` | 未完成目标的 urgency；由 progress、obstruction、avoidance outcome 更新 | 0–.25 low；.25–.55 moderate；.55–.80 high；≥.80 extreme | low urgency 弱；moderate 促进 engagement；high 强 urgency；extreme 只有与 high anxiety/fatigue 交互才进入 overload。完成/进展按比例 relief，不固定盲减 | `procrastination` 改变 avoidance recovery，不直接加 pressure；`task_anxiety_sensitivity` 改变 pressure→anxiety 阈值 |
| `anxiety` | 对不确定/失败/压力的暂态反应；由 pressure、obstruction、recovery 更新 | 0–.20 very low；.20–.45 mild；.45–.70 moderate；.70–.88 high；≥.88 extreme | very low salience weak；mild/moderate 提升 vigilance 与 task engagement；high 开始 performance cost；extreme 才产生 impairment/avoidance。必须显式倒 U，不以两条线性项偶然相消 | `task_anxiety_sensitivity` 移动 high/extreme onset；`self_control` 减少 extreme 下 avoidance |
| `boredom` | 刺激不足与重复暴露；由 activity/context 更新 | 0–.25 engaged；.25–.55 neutral；.55–.80 activated；≥.80 extreme | engaging/non-repetitive activity 降低；idle/repetition 才上升；activated 提升 leisure/exploration relevance；low 不线性推 phone | `stimulation_seeking` 移动 activated threshold与 leisure gain |
| `satisfaction` | 目标进展、需要解决和阻碍的综合结果；向 neutral setpoint normalization | 0–.20 low；.20–.50 neutral；.50–.80 positive；≥.80 high | 不因时间单向下降；progress/completion/need resolution/reward 上升；discomfort/obstruction 下降；normalization 只向 neutral setpoint | 不直接由 personality 乘法决定 |
| `screen_strain` | 屏幕暴露负荷；screen action 增加，non-screen/rest/sleep 恢复 | 0–.25 low；.25–.55 activated；.55–.80 high；≥.80 extreme | low 对决策无影响；activated 降低 screen attractiveness；high 提升 recovery；sleep fastest recovery。禁止统一快速线性归零 | `screen_strain_sensitivity` 移动 high threshold |
| `purchase_urge` | phone/shop/reward cue 触发的 episodic urge | 0–.25 low；.25–.60 activated；.60–.85 high；≥.85 urgent | 只在 cue 激活后衰减；成功 purchase 强 relief；无 cue 不凭空增长或永恒线性滑落 | `stimulation_seeking` 改 cue response，不改库存 owner |

## 核心 coupling functions

实现必须提供并单测：

- `hunger_drive` / `bathroom_drive`：zone + smoothstep；低区接近零，urgent 区才 dominant。
- `pressure_motivation`：low→moderate 上升，high 保持 urgency，不能把 pressure 本身当 overload。
- `anxiety_facilitation`：mild/moderate 为正，极高趋零。
- `anxiety_impairment`：只在 high/extreme 上升。
- `overload_risk`：必须是 pressure × anxiety × fatigue 的 interaction；high pressure + low anxiety 不得自动 overload。
- `recovery_drive`：fatigue/screen strain/temporary overload 的 zone response；有效 rest/sleep 必须降低 fatigue、screen strain，并在 extreme anxiety 下缓慢降低 anxiety。

## Action effects

动作完成 impulse 必须读取当前 zone、动作 family、实际 outcome 与 context：

- Study：按实际 effort/progress 与投入状态改变 pressure/satisfaction/anxiety；不得固定盲减同一数值。
- Rest：恢复 fatigue/screen strain，短期降低 overload；未完成 task 的 pressure 保留。
- Sleep：强恢复 fatigue/screen strain，受 circadian 与 urgent bodily needs 约束；不是普通减压按钮。
- Meal/Bathroom：按当前需求区间 relief；每个需求只有一个库存 owner。
- Phone/Computer：按 screen exposure 增加 strain；engaging activity 才降低 boredom，重复/阻塞可降低 satisfaction。
- Idle：只有在 under-stimulation/repetition 情境下增加 boredom；不得固定增加 pressure 或固定降低 satisfaction。

## Hysteresis / cooldown

- urgent bodily need 进入和退出阈值分离，避免边界抖动。
- overload avoidance 只在 high→normal recovery 后退出；一次 Rest 不得永久锁死，也不得同一 boundary 反复切换。
- screen strain recovery 依 activity family 分层：sleep > rest > ordinary non-screen。
- purchase urge 只有 cue/成功结算触发 active episode；无 cue 不自动激活。

## Personality threshold use

只使用既有八字段：`procrastination`、`self_control`、`rest_preference`、`stimulation_seeking`、`task_anxiety_sensitivity`、`screen_strain_sensitivity`、`need_response`、`action_noise`。人格主要移动阈值、恢复速度和 zone transition，而不是对每个 activation 做无条件加法。所有 profile 仍是 demo engineering profiles，不是人格心理学定义。

## Acceptance probes before batch

在重跑 128×48h 前，必须有 deterministic unit probes 证明：

1. hunger/bathroom 每个 continuous interval 只有一个增长 owner；
2. pressure→task motivation 在 low→moderate 上升、extreme/high-anxiety 才受抑制；
3. anxiety moderate facilitation、extreme impairment 明确成立；
4. high pressure + low anxiety 不等于 overload；
5. rest/sleep 会降低 fatigue/strain/temporary overload，并允许 commitment 恢复；
6. idle 不再产生无条件 satisfaction/pressure 漂移；screen strain 与 purchase urge 为 exposure/cue-driven；
7. action completion impulse 随 zone/context 改变，不是固定常数。

## Status

本 spec 冻结后，下一 commit 才允许修改 DemoLivingV1 实现。任何与本文件不一致的结果先记为 diagnostic，不通过改系数掩盖。
