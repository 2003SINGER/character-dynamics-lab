# DEMO LIVING V0 → V1 COMPARISON

Application engineering diagnostics only; this does not establish psychological realism.

| Metric | V0 mean across profiles | V1 mean across profiles |
|---|---:|---:|
| meals_day_mean | 6.113 | 1.473 |
| bathroom_day_mean | 5.703 | 1.387 |
| study_hours_day_mean | 1.881 | 3.730 |
| leisure_hours_day_mean | 4.183 | 4.131 |
| sleep_hours_day_mean | 5.894 | 4.995 |
| task_completion_rate | 0.109 | 0.625 |
| task_completion_time_p10 | 1843.333 | 1195.125 |
| task_completion_time_p90 | 2271.333 | 1626.375 |
| switches_day_mean | 37.230 | 32.879 |

## V0 diagnostics

```json
{
  "ANXIETY_HIGH_SATURATION": 69,
  "SCREEN_STRAIN_LOW_SATURATION": 123,
  "MEAL_SPAM": 56,
  "TASK_PRESSURE_HIGH_SATURATION": 115,
  "UNMET_BATHROOM": 37,
  "EXCESSIVE_SLEEP": 17,
  "BATHROOM_URGE_HIGH_SATURATION": 7,
  "FATIGUE_LOW_SATURATION": 31,
  "UNMET_HUNGER": 30,
  "HUNGER_HIGH_SATURATION": 5,
  "SATISFACTION_HIGH_SATURATION": 15,
  "TASK_PRESSURE_LOW_SATURATION": 10,
  "BOREDOM_HIGH_SATURATION": 10,
  "REJECTION_LOOP": 1,
  "BOREDOM_LOW_SATURATION": 1
}
```

Switching: {"median": 37.25, "p90": 42.0, "p95": 42.5, "max": 45.0}

## V1 diagnostics

```json
{
  "FATIGUE_LOW_SATURATION": 112,
  "SATISFACTION_HIGH_SATURATION": 106,
  "SCREEN_STRAIN_LOW_SATURATION": 106,
  "TASK_PRESSURE_HIGH_SATURATION": 47,
  "ANXIETY_LOW_SATURATION": 118,
  "TASK_PRESSURE_LOW_SATURATION": 80,
  "UNMET_BATHROOM": 23,
  "EXCESSIVE_SLEEP": 3,
  "UNMET_HUNGER": 18,
  "FATIGUE_HIGH_SATURATION": 1,
  "HUNGER_HIGH_SATURATION": 2,
  "NO_SLEEP_48H": 1
}
```

Switching: {"median": 33.0, "p90": 36.5, "p95": 37.0, "max": 39.0}
