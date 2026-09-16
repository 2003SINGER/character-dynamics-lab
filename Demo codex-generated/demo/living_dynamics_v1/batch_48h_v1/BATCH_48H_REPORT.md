# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 52261.0 minutes
- leisure_minutes: 68953.0 minutes
- idle_minutes: 17343.0 minutes
- rest_minutes: 110131.0 minutes
- sleep_minutes: 93723.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 100 actors
- BATHROOM_URGE_HIGH_SATURATION: 1 actors
- BOREDOM_LOW_SATURATION: 46 actors
- EXCESSIVE_SLEEP: 33 actors
- FATIGUE_LOW_SATURATION: 96 actors
- HUNGER_HIGH_SATURATION: 3 actors
- NO_SLEEP_48H: 5 actors
- REJECTION_LOOP: 2 actors
- SATISFACTION_HIGH_SATURATION: 128 actors
- SCREEN_STRAIN_LOW_SATURATION: 100 actors
- TASK_PRESSURE_HIGH_SATURATION: 64 actors
- TASK_PRESSURE_LOW_SATURATION: 60 actors
- UNMET_BATHROOM: 22 actors
- UNMET_HUNGER: 13 actors

## Switching distribution

- median: 32.50/day
- p90: 38.00/day
- p95: 40.00/day
- max: 47.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
