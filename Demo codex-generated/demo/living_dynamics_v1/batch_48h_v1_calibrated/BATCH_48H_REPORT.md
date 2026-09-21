# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- Artifact: `demo-living-v1-calibrated`.
- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 56202.0 minutes
- leisure_minutes: 57079.0 minutes
- idle_minutes: 47540.0 minutes
- rest_minutes: 71529.0 minutes
- sleep_minutes: 110323.0 minutes

## Stability diagnostics

- ANXIETY_HIGH_SATURATION: 2 actors
- ANXIETY_LOW_SATURATION: 77 actors
- EXCESSIVE_SLEEP: 36 actors
- FATIGUE_LOW_SATURATION: 51 actors
- HUNGER_HIGH_SATURATION: 1 actors
- SCREEN_STRAIN_LOW_SATURATION: 116 actors
- TASK_PRESSURE_HIGH_SATURATION: 48 actors
- TASK_PRESSURE_LOW_SATURATION: 79 actors
- UNMET_BATHROOM: 26 actors
- UNMET_HUNGER: 21 actors

## Switching distribution

- median: 31.50/day
- p90: 37.50/day
- p95: 38.00/day
- max: 40.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
