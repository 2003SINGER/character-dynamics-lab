# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 57289.0 minutes
- leisure_minutes: 63449.0 minutes
- idle_minutes: 30680.0 minutes
- rest_minutes: 119363.0 minutes
- sleep_minutes: 76721.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 118 actors
- EXCESSIVE_SLEEP: 3 actors
- FATIGUE_HIGH_SATURATION: 1 actors
- FATIGUE_LOW_SATURATION: 112 actors
- HUNGER_HIGH_SATURATION: 2 actors
- NO_SLEEP_48H: 1 actors
- SATISFACTION_HIGH_SATURATION: 106 actors
- SCREEN_STRAIN_LOW_SATURATION: 106 actors
- TASK_PRESSURE_HIGH_SATURATION: 47 actors
- TASK_PRESSURE_LOW_SATURATION: 80 actors
- UNMET_BATHROOM: 23 actors
- UNMET_HUNGER: 18 actors

## Switching distribution

- median: 33.00/day
- p90: 36.50/day
- p95: 37.00/day
- max: 39.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
