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
