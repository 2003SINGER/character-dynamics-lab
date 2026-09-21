# DemoLivingV1 baseline-freeze status

`DEMO_LIVING_V1_MECHANISM_REPAIR_R2 = READY_FOR_INDEPENDENT_REVIEW`

This is a demo/application baseline, not a research result or a claim of psychological realism. Laya is deliberately not integrated in this milestone.

## Evidence

- Implementation/spec audit: `V1_IMPLEMENTATION_AUDIT.md`.
- Calibration rationale and old/new values: `CALIBRATION_LOG.md`.
- Mechanism-repair scope and ownership: `MECHANISM_REPAIR_AUDIT.md`.
- Historical calibrated 128 actors × 48h batch: `batch_48h_v1_calibrated/`.
- Same seeds, profiles, scenario construction, policy construction, world and action set as `batch_48h_v1`; the batch runner byte-compares a second run of all 128 actors.
- Full CTest including V1 coupling, Runtime, architecture and legacy-parity checks passes on the calibration revision.

## Acceptance reading

The calibrated batch remains a historical comparison artifact. It was produced
before the authorized Runtime/O projection and pressure-target repair, so it
cannot be used as the freeze evidence for the current implementation.

The replacement same-seed `batch_48h_v1_mechanism_repair/` was generated from
`685ec6a` and records 128×48h (6144 actor-hours), with a byte-for-byte
deterministic rerun of all 128 actors. It no longer reports excessive sleep or
task-pressure high/low saturation. It does report `SCREEN_STRAIN_UNRESPONSIVE`
for 77 actors with at least two hours of screen exposure, 11 unmet-hunger and
11 unmet-bathroom episodes, plus sparse fatigue/anxiety saturation. Those are
visible Demo-model follow-ups, not hidden by the acceptance state.

The historical calibrated artifact and this repair artifact are compared in
`V1_CALIBRATED_VS_MECHANISM_REPAIR.md`. Because the audit semantics were
corrected along the way, changed diagnostic definitions are labelled there as
context rather than treated as fitted improvement scores.

R2 repairs the remaining rejection-replanning, perceived-need gate, screen
response, contextual anxiety recovery and extreme-fatigue feasibility paths.
`batch_48h_v1_mechanism_repair_r2/` is generated from `f829d57`, runs 128×48h
(6144 actor-hours), and byte-compares all 128 deterministic reruns. The
systemic R1 flags are now absent: `SCREEN_STRAIN_UNRESPONSIVE`, unmet hunger,
unmet bathroom, anxiety-low, fatigue-high and fatigue-low saturation are each
0/128. One excessive-sleep and one satisfaction-high trace remain exposed for
review; they are not folded into a false claim of behavioral realism.

`V1_MECHANISM_REPAIR_R1_VS_R2.md` records the exact artifact comparison. The
R1/R2 episode semantics differ where the R2 analyzer corrects boundary-time
attribution, so diagnostic deltas are evidence of repair direction, not a
fitted quality score.

## Next boundary

No Laya or policy A/B milestone is authorized by this repair. This state is
not `CLOSED` or a psychology claim; an independent review must decide whether
the two remaining sparse traces warrant a separate, explicitly scoped
Demo-dynamics follow-up.
