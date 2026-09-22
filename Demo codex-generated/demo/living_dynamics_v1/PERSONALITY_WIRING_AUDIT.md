# Personality wiring audit — 2026-09-22

Status: `PERSONALITY_WIRING = IMPLEMENTED`; long horizon evaluation is still
`IMPLEMENTING`.

The historical `batch_48h.py` assigned a profile label from `actor_id % 8`.
The C++ executable independently inferred the same index from the scenario
seed and did pass the resulting eight-number `Personality` into
`DemoLivingDynamicsV1`. Thus the old runs did use eight P vectors. The defect
was hidden seed-to-P coupling and missing P provenance in the trace. Each
profile also had different World and policy seeds, so the historical 48h
profile summary cannot isolate personality effects.

`character_dynamics_free_run` now accepts an explicit fourth positional
argument naming a profile. The batch runner passes it, verifies the returned
`profile_id` and complete P vector, and retains the old three-argument
six-hour route for legacy regression. New boundary traces record both fields.
The dedicated `personality_wiring_smoke` checks identical scenario and policy
seeds, identical initial task brief, two different explicit P vectors, a
different initial π, and deterministic replay for the same P.

Historical 48h artifacts remain snapshots of their original revision. They
must not be retroactively described as paired personality evidence.
