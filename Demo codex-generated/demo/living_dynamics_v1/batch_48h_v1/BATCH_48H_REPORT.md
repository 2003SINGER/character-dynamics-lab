# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 57219.0 minutes
- leisure_minutes: 62624.0 minutes
- idle_minutes: 31010.0 minutes
- rest_minutes: 118581.0 minutes
- sleep_minutes: 77127.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 117 actors
- EXCESSIVE_SLEEP: 2 actors
- FATIGUE_HIGH_SATURATION: 1 actors
- FATIGUE_LOW_SATURATION: 110 actors
- HUNGER_HIGH_SATURATION: 2 actors
- NO_SLEEP_48H: 1 actors
- SATISFACTION_HIGH_SATURATION: 107 actors
- SCREEN_STRAIN_LOW_SATURATION: 107 actors
- TASK_PRESSURE_HIGH_SATURATION: 47 actors
- TASK_PRESSURE_LOW_SATURATION: 80 actors
- UNMET_BATHROOM: 23 actors
- UNMET_HUNGER: 18 actors

## Switching distribution

- median: 33.00/day
- p90: 35.50/day
- p95: 36.50/day
- max: 38.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
