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
- sleep_minutes: 90535.0 minutes

## Stability diagnostics

- NO_SLEEP_48H: 0 actors
- EXCESSIVE_SLEEP: 17 actors
- MEAL_SPAM: 61 actors
- BATHROOM_SPAM: 0 actors
- ACTION_COLLAPSE: 0 actors
- STUDY_LOCK: 0 actors
- LEISURE_LOCK: 0 actors
- STATE_HIGH_SATURATION: 0 actors
- STATE_LOW_SATURATION: 0 actors
- UNMET_HUNGER: 33 actors
- UNMET_BATHROOM: 37 actors
- RAPID_SWITCHING: 126 actors
- REJECTION_LOOP: 1 actors

## Representative timelines

Selection is automatic; see the 16 JSON traces for full records.
