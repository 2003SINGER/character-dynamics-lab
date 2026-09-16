# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 53712.0 minutes
- leisure_minutes: 85274.0 minutes
- idle_minutes: 16840.0 minutes
- rest_minutes: 91549.0 minutes
- sleep_minutes: 106752.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 96 actors
- BATHROOM_URGE_HIGH_SATURATION: 1 actors
- BOREDOM_LOW_SATURATION: 76 actors
- EXCESSIVE_SLEEP: 43 actors
- FATIGUE_LOW_SATURATION: 110 actors
- HUNGER_HIGH_SATURATION: 10 actors
- NO_SLEEP_48H: 4 actors
- SATISFACTION_HIGH_SATURATION: 128 actors
- SCREEN_STRAIN_LOW_SATURATION: 100 actors
- TASK_PRESSURE_HIGH_SATURATION: 60 actors
- TASK_PRESSURE_LOW_SATURATION: 68 actors
- UNMET_BATHROOM: 55 actors
- UNMET_HUNGER: 55 actors

## Switching distribution

- median: 30.50/day
- p90: 35.50/day
- p95: 38.00/day
- max: 45.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
