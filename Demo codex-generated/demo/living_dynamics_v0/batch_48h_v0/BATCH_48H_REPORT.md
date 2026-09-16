# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 50665.0 minutes
- leisure_minutes: 67260.0 minutes
- idle_minutes: 14807.0 minutes
- rest_minutes: 103521.0 minutes
- sleep_minutes: 101488.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_LOW_SATURATION: 98 actors\n- BOREDOM_HIGH_SATURATION: 1 actors\n- BOREDOM_LOW_SATURATION: 60 actors\n- EXCESSIVE_SLEEP: 36 actors\n- FATIGUE_LOW_SATURATION: 106 actors\n- HUNGER_HIGH_SATURATION: 3 actors\n- REJECTION_LOOP: 3 actors\n- SATISFACTION_HIGH_SATURATION: 128 actors\n- SCREEN_STRAIN_LOW_SATURATION: 104 actors\n- TASK_PRESSURE_HIGH_SATURATION: 70 actors\n- TASK_PRESSURE_LOW_SATURATION: 55 actors\n- UNMET_BATHROOM: 12 actors\n- UNMET_HUNGER: 17 actors

## Switching distribution

- median: 33.00/day
- p90: 38.50/day
- p95: 39.50/day
- max: 45.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
