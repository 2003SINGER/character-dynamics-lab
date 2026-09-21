# DemoLivingV1 baseline-freeze status

`DEMO_LIVING_V1_BASELINE_FREEZE = SUPERSEDED_BY_MECHANISM_REPAIR_R1`

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

The replacement same-seed `batch_48h_v1_mechanism_repair/` is generated only
after the implementation commit, with its generating revision recorded in its
manifest. Its result determines whether a new independent-review state is
appropriate; this document does not silently claim it in advance.

## Next boundary

No Laya or policy A/B milestone is authorized by this repair. A later policy
experiment may be proposed only after the repaired batch is independently
reviewed.
