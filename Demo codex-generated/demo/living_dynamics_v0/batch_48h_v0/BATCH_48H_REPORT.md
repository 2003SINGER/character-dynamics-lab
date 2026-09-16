# DEMO_LIVING_BATCH_48H_V0

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 48053.0 minutes
- leisure_minutes: 62154.0 minutes
- idle_minutes: 13209.0 minutes
- rest_minutes: 94520.0 minutes
- sleep_minutes: 115880.0 minutes\n\n## Stability diagnostics\n\n- ANXIETY_HIGH_SATURATION: 1 actors\n- ANXIETY_LOW_SATURATION: 61 actors\n- BATHROOM_URGE_HIGH_SATURATION: 1 actors\n- BOREDOM_HIGH_SATURATION: 2 actors\n- BOREDOM_LOW_SATURATION: 66 actors\n- EXCESSIVE_SLEEP: 59 actors\n- FATIGUE_LOW_SATURATION: 108 actors\n- HUNGER_HIGH_SATURATION: 2 actors\n- NO_SLEEP_48H: 1 actors\n- REJECTION_LOOP: 4 actors\n- SATISFACTION_HIGH_SATURATION: 116 actors\n- SCREEN_STRAIN_LOW_SATURATION: 91 actors\n- TASK_PRESSURE_HIGH_SATURATION: 75 actors\n- TASK_PRESSURE_LOW_SATURATION: 57 actors\n- UNMET_BATHROOM: 21 actors\n- UNMET_HUNGER: 18 actors

## Switching distribution

- median: 31.50/day
- p90: 38.50/day
- p95: 41.00/day
- max: 46.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
