# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 28894.0 minutes
- leisure_minutes: 64253.0 minutes
- idle_minutes: 12020.0 minutes
- rest_minutes: 95242.0 minutes
- sleep_minutes: 90535.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_HIGH_SATURATION: 69 actors\n- BATHROOM_URGE_HIGH_SATURATION: 7 actors\n- BOREDOM_HIGH_SATURATION: 10 actors\n- BOREDOM_LOW_SATURATION: 1 actors\n- EXCESSIVE_SLEEP: 17 actors\n- FATIGUE_LOW_SATURATION: 31 actors\n- HUNGER_HIGH_SATURATION: 5 actors\n- MEAL_SPAM: 56 actors\n- REJECTION_LOOP: 1 actors\n- SATISFACTION_HIGH_SATURATION: 15 actors\n- SCREEN_STRAIN_LOW_SATURATION: 123 actors\n- TASK_PRESSURE_HIGH_SATURATION: 115 actors\n- TASK_PRESSURE_LOW_SATURATION: 10 actors\n- UNMET_BATHROOM: 37 actors\n- UNMET_HUNGER: 30 actors

## Switching distribution

- median: 37.25/day
- p90: 42.00/day
- p95: 42.50/day
- max: 45.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
