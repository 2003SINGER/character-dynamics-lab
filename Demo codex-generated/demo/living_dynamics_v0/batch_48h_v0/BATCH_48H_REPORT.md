# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 49901.0 minutes
- leisure_minutes: 69967.0 minutes
- idle_minutes: 13794.0 minutes
- rest_minutes: 99732.0 minutes
- sleep_minutes: 103957.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_LOW_SATURATION: 94 actors\n- BATHROOM_URGE_HIGH_SATURATION: 1 actors\n- BOREDOM_HIGH_SATURATION: 1 actors\n- BOREDOM_LOW_SATURATION: 49 actors\n- EXCESSIVE_SLEEP: 43 actors\n- FATIGUE_LOW_SATURATION: 101 actors\n- HUNGER_HIGH_SATURATION: 3 actors\n- REJECTION_LOOP: 3 actors\n- SATISFACTION_HIGH_SATURATION: 128 actors\n- SCREEN_STRAIN_LOW_SATURATION: 97 actors\n- TASK_PRESSURE_HIGH_SATURATION: 74 actors\n- TASK_PRESSURE_LOW_SATURATION: 51 actors\n- UNMET_BATHROOM: 15 actors\n- UNMET_HUNGER: 15 actors

## Switching distribution

- median: 32.50/day
- p90: 39.00/day
- p95: 39.50/day
- max: 44.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
