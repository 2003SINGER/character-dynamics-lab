# DEMO LIVING V0 → V1 COMPARISON

Application engineering diagnostics only; this does not establish psychological realism.

| Metric | V0 mean across profiles | V1 mean across profiles |
|---|---:|---:|
| meals_day_mean | 6.113 | 1.480 |
| bathroom_day_mean | 5.703 | 1.414 |
| study_hours_day_mean | 1.881 | 3.975 |
| leisure_hours_day_mean | 4.183 | 4.186 |
| sleep_hours_day_mean | 5.894 | 4.662 |
| task_completion_rate | 0.109 | 0.672 |
| task_completion_time_p10 | 1843.333 | 1177.875 |
| task_completion_time_p90 | 2271.333 | 1591.500 |
| switches_day_mean | 37.230 | 33.309 |

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
  "SATISFACTION_HIGH_SATURATION": 110,
  "TASK_PRESSURE_HIGH_SATURATION": 41,
  "FATIGUE_LOW_SATURATION": 115,
  "SCREEN_STRAIN_LOW_SATURATION": 110,
  "ANXIETY_LOW_SATURATION": 122,
  "TASK_PRESSURE_LOW_SATURATION": 86,
  "EXCESSIVE_SLEEP": 5,
  "UNMET_BATHROOM": 23,
  "UNMET_HUNGER": 12,
  "HUNGER_HIGH_SATURATION": 1,
  "NO_SLEEP_48H": 1,
  "BATHROOM_URGE_HIGH_SATURATION": 1
}
```

Switching: {"median": 33.0, "p90": 37.0, "p95": 38.0, "max": 40.0}
