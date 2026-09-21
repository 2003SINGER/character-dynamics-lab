# DemoLivingDynamicsV1 implementation audit

Date: 2026-09-21  
Scope: `DemoLivingDynamicsV1` only. This audit does not modify Runtime,
ResearchDynamicsV1, legacy/reference dynamics, the action surface, or V0
artifacts.

## Audit method

Reviewed the V1 model boundary (`demo_living_dynamics_v1.cpp`), continuous
update (`state_v1.cpp`), appraisal (`appraisal_v1.cpp`), policy response
functions (`living_dynamics_v1.cpp`, `decision_v1.cpp`), the V1 coupling
smoke, and the frozen `batch_48h_v1` compact/representative traces.

The frozen diagnostic has 128 actors × 48 hours. Its relevant saturation
counts are fatigue-low 114, anxiety-low 119, satisfaction-high 107,
task-pressure-high 48, and task-pressure-low 79. These are diagnostics, not
psychological claims.

## Field ownership and conformance

| Field | Continuous owner | Event/action owner | Neutral/recovery owner | Threshold/response | P modulation | Audit finding |
|---|---|---|---|---|---|---|
| hunger | `metabolism_rate` in `advance_continuous_state` | meal settlement | n/a | `hunger_zone`, smooth drive | `need_response` shifts perception | one physical accumulation owner; conformant |
| bathroom_urge | `bathroom_accumulation_rate` | bathroom settlement | n/a | `bathroom_zone`, smooth drive | `need_response` | one physical accumulation owner; conformant |
| fatigue | running-action load/recovery | study/device/rest/sleep appraisal | rest/sleep | `fatigue_zone`, recovery drive | rest preference, self control, strain sensitivity | recovery is delivered both continuously and on settlement; calibration required |
| task_pressure | no wall-clock owner | study progress, device avoidance, deadline/obstruction | progress/completion | `pressure_motivation`, overload interaction | procrastination, anxiety sensitivity | Rest/Sleep additionally add pressure despite spec saying pressure is retained; mismatch |
| anxiety | pressure/discomfort coupling | deadline, obstruction, reminders, recovery | homeostatic and rest/sleep recovery | facilitation/impairment zones | anxiety sensitivity, self control | unconditional decay plus repeated recovery suppresses the channel; calibration required |
| boredom | idle/repetition and activity context | stimulation outcome | engaging activity | boredom zone/drive | stimulation seeking | no generic wall-clock drift; conformant |
| satisfaction | discomfort cost | progress, recovery, need resolution, reward | neutral return to .50 | satisfaction zone only | none direct | several positive routes are not headroom-scaled; neutral return too weak; calibration required |
| screen_strain | screen exposure | device/study outcome | non-screen/rest/sleep | strain zone/aversion | strain sensitivity | exposure/recovery owned and contextual; conformant |
| purchase_urge | none | device cue/purchase relief | active-episode decay | urge zone | stimulation seeking via policy | no uncued accumulation; conformant |

`state_v1.cpp` uses the inherited V1-local `DemoLivingV0` namespace as a
linkage compatibility name, compiled as `DemoLivingV1`; it is not linked to
the historical V0 living target. The generic state router still carries typed
semantic signals, so this is documented as a compatibility surface rather
than an unreported second continuous owner.

## Direct raw-state coefficients and paths

All currently material raw-state coefficients are listed here before any
calibration change:

- fatigue: Study/device load; Rest/Sleep continuous recovery; Rest/Sleep
  appraisal recovery; screen-strain coupling.
- anxiety: pressure coupling, homeostatic decay, Rest/Sleep recovery,
  deadline/reminder/obstruction impulses, bodily discomfort.
- satisfaction: direct positive action outcomes, GoalProgress/Completion
  semantic signals, need-resolution generic feedback, neutral return.
- pressure: progress relief, deadline/obstruction/device avoidance impulses,
  and Rest/Sleep pending-task increments.

No duplicate hunger or bathroom continuous accumulation path was found. No
new persistent state field is needed for the calibration.

## Trace-based diagnosis before calibration

### Fatigue low saturation

The frozen traces show long Rest/Sleep occupancy while fatigue is already in
fresh/normal zones. The policy has a non-zone-gated `0.18 * rest_preference`
recovery component; each Rest/Sleep then reduces fatigue both during the
running interval and at action settlement. This double recovery is the main
cause, not weak study/device load alone.

### Anxiety low saturation

Anxiety is continuously reduced by `-0.006 * anxiety` each half-hour,
reduced again by Rest/Sleep and task-engagement outcomes, while ordinary
activation is mostly reserved for deadline/reminder/obstruction boundaries.
The resulting traces spend long ordinary periods below .02. This is an
activation/recovery timescale imbalance, not evidence that profiles lack
anxiety.

### Satisfaction high saturation

Study, recovery, need resolution, reward, environment actions and typed
GoalProgress/Completion all add positive satisfaction. The positive aggregate
does not shrink with remaining headroom, while the neutral return is only
`0.006` per half-hour. Repeated ordinary positive settlement therefore wins
over normalization and pins many traces above .98.

### Task-pressure polarization

Study sessions release pressure proportionally when it is already high,
whereas Rest/Sleep with a pending task add pressure repeatedly. The former
creates a low attractor after progress; the latter creates a high attractor
when recovery repeats. Deadline impulses strengthen the high branch. The
Rest/Sleep increment conflicts with the specification's “pressure retains”
rule and is removed as a conformance repair in the first calibration pass.

## Calibration constraint

Only existing V1 timescales, thresholds and response curves may change. No
action-specific outcome bonus is introduced; every change is recorded in
`CALIBRATION_LOG.md` with its prior value, semantic owner and expected
qualitative effect.
