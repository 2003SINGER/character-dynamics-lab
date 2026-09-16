# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 57774.0 minutes
- leisure_minutes: 64241.0 minutes
- idle_minutes: 28160.0 minutes
- rest_minutes: 117747.0 minutes
- sleep_minutes: 78779.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 119 actors
- BATHROOM_URGE_HIGH_SATURATION: 1 actors
- EXCESSIVE_SLEEP: 2 actors
- FATIGUE_LOW_SATURATION: 114 actors
- HUNGER_HIGH_SATURATION: 1 actors
- NO_SLEEP_48H: 1 actors
- SATISFACTION_HIGH_SATURATION: 107 actors
- SCREEN_STRAIN_LOW_SATURATION: 103 actors
- TASK_PRESSURE_HIGH_SATURATION: 48 actors
- TASK_PRESSURE_LOW_SATURATION: 79 actors
- UNMET_BATHROOM: 16 actors
- UNMET_HUNGER: 17 actors

## Switching distribution

- median: 33.00/day
- p90: 36.00/day
- p95: 37.00/day
- max: 39.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
