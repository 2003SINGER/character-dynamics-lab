# DEMO_LIVING_BATCH_48H_V1

Demo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.

- Artifact: `demo-living-v1-final-pressure-repair`.
- 128 independent actors, 8 demo engineering profiles × 16 seeds.
- 48 simulated hours each; total 6144 actor-hours.
- Dynamics model: `demo-living-v1`.
- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).
- Full raw traces remain local-only; compact audit trace contains every boundary.

See `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.

## Behavior distribution

- study_minutes: 55044.0 minutes
- leisure_minutes: 71859.0 minutes
- idle_minutes: 35428.0 minutes
- rest_minutes: 101905.0 minutes
- sleep_minutes: 78567.0 minutes

## Stability diagnostics

- SATISFACTION_HIGH_SATURATION: 1 actors
- UNMET_BATHROOM: 1 actors

## Switching distribution

- median: 34.75/day
- p90: 38.00/day
- p95: 38.50/day
- max: 40.50/day


## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
