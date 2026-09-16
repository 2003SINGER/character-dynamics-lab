# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 48524.0 minutes
- leisure_minutes: 58029.0 minutes
- idle_minutes: 12300.0 minutes
- rest_minutes: 83532.0 minutes
- sleep_minutes: 134608.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_HIGH_SATURATION: 47 actors\n- ANXIETY_LOW_SATURATION: 6 actors\n- BATHROOM_URGE_HIGH_SATURATION: 1 actors\n- BOREDOM_HIGH_SATURATION: 3 actors\n- BOREDOM_LOW_SATURATION: 58 actors\n- EXCESSIVE_SLEEP: 78 actors\n- FATIGUE_LOW_SATURATION: 114 actors\n- REJECTION_LOOP: 3 actors\n- SATISFACTION_HIGH_SATURATION: 50 actors\n- SCREEN_STRAIN_LOW_SATURATION: 103 actors\n- TASK_PRESSURE_HIGH_SATURATION: 88 actors\n- TASK_PRESSURE_LOW_SATURATION: 49 actors\n- UNMET_BATHROOM: 12 actors\n- UNMET_HUNGER: 5 actors

## Switching distribution

- median: 29.50/day
- p90: 36.50/day
- p95: 37.50/day
- max: 41.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
