# DEMO LIVING V0 → V1 COMPARISON

Application engineering diagnostics only; this does not establish psychological realism.

| Metric | V0 mean across profiles | V1 mean across profiles |
|---|---:|---:|
| meals_day_mean | 1.898 | 1.148 |
| bathroom_day_mean | 2.371 | 1.156 |
| study_hours_day_mean | 3.402 | 3.728 |
| leisure_hours_day_mean | 4.493 | 5.191 |
| sleep_hours_day_mean | 6.056 | 7.553 |
| task_completion_rate | 0.477 | 0.609 |
| task_completion_time_p10 | 1369.375 | 1281.250 |
| task_completion_time_p90 | 2122.375 | 1762.625 |
| switches_day_mean | 32.973 | 29.770 |

## V0 diagnostics

```json
{
  "TASK_PRESSURE_HIGH_SATURATION": 64,
  "SATISFACTION_HIGH_SATURATION": 128,
  "FATIGUE_LOW_SATURATION": 96,
  "ANXIETY_LOW_SATURATION": 100,
  "SCREEN_STRAIN_LOW_SATURATION": 100,
  "TASK_PRESSURE_LOW_SATURATION": 60,
  "BOREDOM_LOW_SATURATION": 45,
  "UNMET_HUNGER": 13,
  "HUNGER_HIGH_SATURATION": 3,
  "EXCESSIVE_SLEEP": 31,
  "UNMET_BATHROOM": 22,
  "BATHROOM_URGE_HIGH_SATURATION": 1,
  "NO_SLEEP_48H": 5,
  "REJECTION_LOOP": 2
}
```

Switching: {"median": 32.5, "p90": 38.0, "p95": 40.0, "max": 47.0}

## V1 diagnostics

```json
{
  "TASK_PRESSURE_HIGH_SATURATION": 49,
  "SATISFACTION_HIGH_SATURATION": 102,
  "FATIGUE_LOW_SATURATION": 118,
  "ANXIETY_LOW_SATURATION": 104,
  "TASK_PRESSURE_LOW_SATURATION": 78,
  "UNMET_BATHROOM": 56,
  "SCREEN_STRAIN_LOW_SATURATION": 84,
  "UNMET_HUNGER": 54,
  "EXCESSIVE_SLEEP": 47,
  "BOREDOM_LOW_SATURATION": 34,
  "HUNGER_HIGH_SATURATION": 1
}
```

Switching: {"median": 29.5, "p90": 34.0, "p95": 34.5, "max": 37.5}
