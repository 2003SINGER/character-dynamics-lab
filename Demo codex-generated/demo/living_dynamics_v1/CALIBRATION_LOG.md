# DemoLivingV1 calibration log

Milestone: `DEMO_LIVING_V1_BASELINE_FREEZE`  
Pass: 1 of at most 2  
Date: 2026-09-21

This is application/demo calibration. It does not optimize against a human
schedule, change the world/runtime/action interface, or provide research
evidence.

| Parameter / response owner | Old | New | Causal reason | Expected qualitative effect |
|---|---:|---:|---|---|
| recovery-drive rest-preference contribution | `0.18 * P.rest_preference` at every fatigue level | `0.06 * P.rest_preference * smoothstep(.35,.55,fatigue)` | non-gated preference selected Rest while fresh | Rest becomes relevant after fatigue activates; fatigue can use its normal range |
| Rest continuous fatigue recovery / 30 min | `-0.050` | `-0.028` | continuous plus settlement recovery doubled the effective recovery | Rest lowers fatigue without instantly resetting it |
| Sleep continuous fatigue recovery / 30 min | `-0.110` | `-0.060` | same duplicated recovery path, amplified by long sleep | Sleep remains strongest recovery but does not pin fatigue low |
| Rest/Sleep continuous anxiety recovery | `-0.018/-0.025 × (1+overload)` | `-0.008/-0.012 × (1+overload)` | repeated recovery plus zero-target decay suppressed anxiety | recovery reduces acute strain but preserves mild/moderate range |
| anxiety neutral return / 30 min | `-0.006 * anxiety` | `0.003 * (.20-anxiety)` | prior path had a permanent zero attractor | calm intervals return to declared mild neutral, not zero |
| pressure-to-anxiety activation | `max(0,pressure-.55)*.035` | `.018 * pressure_motivation(pressure)` | onset was too late/weak for ordinary task pressure | moderate pressure can produce mild vigilance; extreme impairment remains separate |
| Study / halfhearted pressure relief | `-.14/-.08 × pressure_motivation` | `-.10/-.06 × pressure_motivation` | fast progress relief contributed to low-pressure attractor | real progress still relieves, with slower return |
| Study / halfhearted anxiety reduction | `-.04/-.02 × facilitation` | `-.02/-.01 × facilitation` | task engagement directly erased the remaining mild anxiety | engaged work can regulate anxiety without forcing it low |
| Rest/Sleep settlement fatigue recovery | `-.10/-.20 × recovery_drive` | `-.065/-.13 × recovery_drive` | settlement duplicated continuous recovery | preserve recovery semantics at a calibrated timescale |
| Rest/Sleep pending-task pressure | `+.02/.03 * current pressure` | `0` | contradicts the spec: recovery retains pending pressure; it does not create it | removes artificial high-pressure recovery loop |
| positive satisfaction headroom | no scaling | `positive_delta × (.35 + .65 × (1-satisfaction))` | repeated varied positive settlements pinned satisfaction high | positive outcomes diminish near the high zone without action-specific treatment |
| satisfaction neutral return / 30 min | `.006 × (.50-satisfaction)` | `.014 × (.50-satisfaction)` | normalization could not counter normal positive settlement | quiet periods return more visibly toward neutral |
| generic need-resolution satisfaction bonus | `+.04 * P.need_response` | removed | meal/bathroom already have state-dependent satisfaction effects | removes a duplicated positive path |

No seed, profile, action type, world settlement, state field or
ResearchDynamics component changed in this calibration pass.

## Mechanism repair R1 — 2026-09-21

This is not a coefficient pass. It follows explicit authorization to modify
the model/Runtime interface and O-clock projection after the calibration batch
revealed an ownership defect.

| Mechanism | Before | Repair | Boundary preserved |
|---|---|---|---|
| recovery fatigue / screen strain | continuous action, appraisal and semantic paths could all mutate the same load | physical loads are continuous-action-owned; events retain typed meaning only | no World/action schema change |
| long-action reconsideration | only Kernel `.40` need crossings could open a gate | model can request a typed subjective reconsideration; same-action continuation retains elapsed progress | Kernel does not name V1 states or thresholds |
| runtime time for model dynamics | V1 could not honestly derive deadline urgency from O | Kernel writes `clock.total_minutes` to O before model integration | model reads O, not hidden World time |
| task pressure | event-density-dependent appraisal impulse stock | continuous relaxation toward an O-derived workload/deadline/commitment target | Reference model retains no-op hook |
| anxiety | generic baseline/pump could sustain an artificial channel | target is driven by pressure motivation plus typed impulses | no profile or action-set change |

## Mechanism repair R2 — 2026-09-21

R2 is a focused closure pass after the R1 same-seed audit. It changes no World
schema, action surface, profile seed, Reference dynamics, ResearchDynamics or
Laya behavior.

| Defect | Repair | Executable boundary |
|---|---|---|
| rejected replacement resumed old action without re-planning | `ActionRejected` always opens the next Runtime policy gate, while the existing action remains intact until a valid replacement is chosen | closure smoke asserts feedback, gate, informed policy and retained action continuity |
| urgent policy and runtime gate were not one law | V1 centralizes a perceived-need threshold used by its gate hook and hard eligibility constraint | reconsideration smoke crosses the model boundary during a running sleep |
| fragmented screen exposure never affected behavior | preserve one continuous owner; rebalance device build, short-rest recovery and sleep reset timescales | coupling smoke reaches the screen-aversion zone through continuous device exposure |
| recovery could push anxiety beneath its contextual target | continuous Rest/Sleep recovery is capped at the pressure-derived target | coupling smoke forbids a low-attractor overshoot |
| extreme fatigue could repeatedly admit work/device candidates | extreme fatigue makes only recovery/safety candidates eligible | coupling smoke validates the feasibility boundary |
| saturation audit over-counted end-of-boundary state | split threshold-crossing Δt rather than assigning end state to the entire interval | batch analyzer regression path |

## Final pressure ownership repair — 2026-09-21

This is a state-owner correction, not a policy or profile-coefficient pass.
It follows review of the R2 trace semantics; it changes no World schema,
action surface, profile seed, Reference dynamics, ResearchDynamics or Laya.

| Defect | Repair | Executable boundary |
|---|---|---|
| pressure moved at every appraisal boundary | `update_state` / impulses no longer mutate task pressure; elapsed continuous integration is its sole writer | coupling smoke proves target appraisal is zero-duration pressure-neutral |
| deadline target depended on scheduler split density | integrate the linearly changing O-clock deadline target exactly over each interval | same 300-minute O trajectory split across 2/20 irrelevant boundaries has equal final pressure |
| High/Extreme/overload pressure range was unreachable | O-derived incomplete-work/deadline target now spans ordinary through overdue urgency | smoke reaches Extreme pressure and overload from active overdue task O facts, not an injected high pressure value |
