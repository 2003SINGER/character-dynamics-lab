# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 48453.0 minutes
- leisure_minutes: 59534.0 minutes
- idle_minutes: 13321.0 minutes
- rest_minutes: 90917.0 minutes
- sleep_minutes: 125921.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_HIGH_SATURATION: 1 actors\n- ANXIETY_LOW_SATURATION: 70 actors\n- BATHROOM_URGE_HIGH_SATURATION: 2 actors\n- BOREDOM_LOW_SATURATION: 90 actors\n- EXCESSIVE_SLEEP: 73 actors\n- FATIGUE_LOW_SATURATION: 110 actors\n- REJECTION_LOOP: 1 actors\n- SATISFACTION_HIGH_SATURATION: 64 actors\n- SCREEN_STRAIN_LOW_SATURATION: 101 actors\n- TASK_PRESSURE_HIGH_SATURATION: 81 actors\n- TASK_PRESSURE_LOW_SATURATION: 54 actors\n- UNMET_BATHROOM: 19 actors\n- UNMET_HUNGER: 17 actors

## Switching distribution

- median: 30.00/day
- p90: 37.50/day
- p95: 39.50/day
- max: 44.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
