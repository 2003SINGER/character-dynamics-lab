# Paired deadline state-dynamics v0

- source revision: `253db91`
- runner: `character_dynamics_reference --paired-deadline`
- branches: control / hidden / visible
- seeds: 8
- decision points: 12 per branch and seed
- action control: shared action sampled from control policy and replayed to all branches
- intervention: after common step 1; treatment deadline = intervention time + 180 minutes
- hidden discovery: first observation at intervention time + 60 minutes

Observed seed-1 trace:

- Before intervention, all three branches had deadline `1124` and identical policy distance `0`.
- At step 2, visible observed deadline `685`, urgency `0.75`, and appraisal pressure contribution `0.22`; hidden/control retained `1124` and policy distance `0`.
- At step 4, hidden observed `685`, discovery event became `1`, urgency `0.847222`, and appraisal pressure contribution `0.169444`.
- Shared action replay kept branch simulation times aligned.

This is mechanism evidence for deadline information entering O/X/S/policy. It is not psychological validation or external evidence.
