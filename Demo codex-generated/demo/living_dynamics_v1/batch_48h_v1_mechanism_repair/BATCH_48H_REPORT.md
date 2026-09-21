# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- Artifact: `demo-living-v1-mechanism-repair`.
- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 52007.0 minutes
- leisure_minutes: 82358.0 minutes
- idle_minutes: 41748.0 minutes
- rest_minutes: 99185.0 minutes
- sleep_minutes: 65128.0 minutes

## Stability diagnostics

- ANXIETY_LOW_SATURATION: 9 actors
- FATIGUE_HIGH_SATURATION: 1 actors
- FATIGUE_LOW_SATURATION: 7 actors
- SCREEN_STRAIN_UNRESPONSIVE: 77 actors
- UNMET_BATHROOM: 11 actors
- UNMET_HUNGER: 11 actors

## Switching distribution

- median: 36.00/day
- p90: 40.00/day
- p95: 40.50/day
- max: 42.00/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
