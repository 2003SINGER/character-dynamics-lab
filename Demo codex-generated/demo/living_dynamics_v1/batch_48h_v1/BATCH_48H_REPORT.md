# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 57547.0 minutes
- leisure_minutes: 79472.0 minutes
- idle_minutes: 15980.0 minutes
- rest_minutes: 83652.0 minutes
- sleep_minutes: 116842.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 105 actors
- BOREDOM_LOW_SATURATION: 31 actors
- EXCESSIVE_SLEEP: 46 actors
- FATIGUE_LOW_SATURATION: 117 actors
- HUNGER_HIGH_SATURATION: 2 actors
- SATISFACTION_HIGH_SATURATION: 91 actors
- SCREEN_STRAIN_LOW_SATURATION: 86 actors
- TASK_PRESSURE_HIGH_SATURATION: 48 actors
- TASK_PRESSURE_LOW_SATURATION: 79 actors
- UNMET_BATHROOM: 53 actors
- UNMET_HUNGER: 56 actors

## Switching distribution

- median: 30.00/day
- p90: 34.00/day
- p95: 34.50/day
- max: 39.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
