# DemoLivingV1 baseline-freeze status

`DEMO_LIVING_V1_BASELINE_FREEZE = READY_FOR_INDEPENDENT_REVIEW`

This is a demo/application baseline, not a research result or a claim of psychological realism. Laya is deliberately not integrated in this milestone.

## Evidence

- Implementation/spec audit: `V1_IMPLEMENTATION_AUDIT.md`.
- Calibration rationale and old/new values: `CALIBRATION_LOG.md`.
- Exact frozen 128 actors × 48h batch: `batch_48h_v1_calibrated/`.
- Same seeds, profiles, scenario construction, policy construction, world and action set as `batch_48h_v1`; the batch runner byte-compares a second run of all 128 actors.
- Full CTest including V1 coupling, Runtime, architecture and legacy-parity checks passes on the calibration revision.

## Acceptance reading

The previous major same-extreme collapses are no longer above 80% of actors: fatigue-low 51/128, anxiety-low 77/128, satisfaction-high 0/128, task-pressure-high 48/128 and task-pressure-low 79/128. Meal/bathroom spam and rejection-loop flags are absent; task completion remains possible.

Remaining demo diagnostic: `EXCESSIVE_SLEEP` is 36/128 (up from 2/128), and unmet hunger/bathroom episodes are 21/128 and 26/128. These are not hidden or optimized away. A second pass would be justified only by a mechanism-level explanation, not by fitting a target daily schedule; this milestone therefore stops here as required.

## Next boundary

If independently accepted, the next isolated milestone is `DemoLayaPolicyV0`: replace policy only for an A/B run while preserving this world, Runtime, action surface, seeds and frozen demo dynamics baseline.
