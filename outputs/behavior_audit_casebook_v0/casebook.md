# Behavior audit casebook v0

Scope: development-only failure mining. This is not a pre-registered objective,
not a candidate ranking, and not evidence of naturalness or psychological validity.

- source: `/Users/2003singer/Workspace/Research/character-dynamics-lab/outputs/development_split_v1/baseline_train_final/run_1788968585206_0/trajectories.csv`
- split: `optimizer_train` only; holdout was not read
- screeners: need >= 0.8; task pressure >= 0.8; study probability < 0.12
- `deadline_remaining` is absent from this batch: no deadline-response screener is produced.

## Cases

| id | personality / seed | screening tags | score | highlighted span | trace |
| --- | --- | --- | ---: | --- | --- |
| case-001 | 2 / 1128 | active_task_stagnation, commitment_suspension, high_pressure_low_study | 41 | 40–85 | `traces/case-001_p2_s1128.csv` |
| case-002 | 4 / 1113 | active_task_stagnation, commitment_suspension, high_pressure_low_study | 34 | 46–79 | `traces/case-002_p4_s1113.csv` |
| case-003 | 32 / 1120 | high_bathroom_nonvisit, high_hunger_nonmeal | 35 | 20–148 | `traces/case-003_p32_s1120.csv` |
| case-004 | 32 / 1123 | active_task_stagnation, commitment_suspension | 34 | 28–61 | `traces/case-004_p32_s1123.csv` |
| case-005 | 8 / 1117 | active_task_stagnation, commitment_suspension | 31 | 57–87 | `traces/case-005_p8_s1117.csv` |
| case-006 | 8 / 1125 | active_task_stagnation, commitment_suspension | 30 | 20–49 | `traces/case-006_p8_s1125.csv` |
| case-007 | 31 / 1114 | active_task_stagnation, commitment_suspension | 28 | 28–55 | `traces/case-007_p31_s1114.csv` |
| case-008 | 10 / 1111 | active_task_stagnation, commitment_suspension | 26 | 45–70 | `traces/case-008_p10_s1111.csv` |
| case-009 | 2 / 1106 | active_task_stagnation, commitment_suspension | 26 | 17–42 | `traces/case-009_p2_s1106.csv` |
| case-010 | 15 / 1116 | same_action_run, zero_time_loop | 7 | 227–233 | `traces/case-010_p15_s1116.csv` |
| case-011 | 15 / 1121 | same_action_run, zero_time_loop | 7 | 227–233 | `traces/case-011_p15_s1121.csv` |
| case-012 | 15 / 1122 | same_action_run, zero_time_loop | 7 | 248–254 | `traces/case-012_p15_s1122.csv` |
| case-013 | 16 / 1112 | same_action_run, zero_time_loop | 7 | 201–207 | `traces/case-013_p16_s1112.csv` |
| case-014 | 16 / 1113 | same_action_run, zero_time_loop | 7 | 211–217 | `traces/case-014_p16_s1113.csv` |
| case-015 | 8 / 1107 | same_action_run, zero_time_loop | 7 | 223–229 | `traces/case-015_p8_s1107.csv` |
| case-016 | 11 / 1120 | same_action_run, zero_time_loop | 6 | 231–236 | `traces/case-016_p11_s1120.csv` |
| case-017 | 31 / 1103 | high_hunger_nonmeal | 53 | 8–214 | `traces/case-017_p31_s1103.csv` |
| case-018 | 18 / 1124 | high_hunger_nonmeal | 50 | 8–235 | `traces/case-018_p18_s1124.csv` |
| case-019 | 7 / 1128 | high_hunger_nonmeal | 48 | 24–115 | `traces/case-019_p7_s1128.csv` |
| case-020 | 23 / 1124 | high_bathroom_nonvisit | 44 | 26–242 | `traces/case-020_p23_s1124.csv` |
| case-021 | 20 / 1111 | high_hunger_nonmeal | 40 | 9–204 | `traces/case-021_p20_s1111.csv` |
| case-022 | 2 / 1123 | high_hunger_nonmeal | 39 | 32–70 | `traces/case-022_p2_s1123.csv` |
| case-023 | 2 / 1122 | high_hunger_nonmeal | 38 | 20–256 | `traces/case-023_p2_s1122.csv` |
| case-024 | 20 / 1102 | high_pressure_low_study | 38 | 15–80 | `traces/case-024_p20_s1102.csv` |
| case-025 | 7 / 1123 | high_hunger_nonmeal | 38 | 19–140 | `traces/case-025_p7_s1123.csv` |
| case-026 | 22 / 1107 | high_hunger_nonmeal | 37 | 26–216 | `traces/case-026_p22_s1107.csv` |
| case-027 | 21 / 1106 | high_pressure_low_study | 36 | 16–79 | `traces/case-027_p21_s1106.csv` |
| case-028 | 23 / 1116 | high_pressure_low_study | 36 | 26–79 | `traces/case-028_p23_s1116.csv` |
| case-029 | 3 / 1103 | high_pressure_low_study | 35 | 8–66 | `traces/case-029_p3_s1103.csv` |
| case-030 | 31 / 1124 | high_hunger_nonmeal | 35 | 8–58 | `traces/case-030_p31_s1124.csv` |
| case-031 | 6 / 1122 | high_pressure_low_study | 35 | 27–70 | `traces/case-031_p6_s1122.csv` |
| case-032 | 7 / 1106 | high_pressure_low_study | 35 | 25–91 | `traces/case-032_p7_s1106.csv` |
| case-033 | 8 / 1106 | high_pressure_low_study | 34 | 18–69 | `traces/case-033_p8_s1106.csv` |
| case-034 | 2 / 1104 | high_pressure_low_study | 32 | 11–71 | `traces/case-034_p2_s1104.csv` |
| case-035 | 8 / 1124 | high_bathroom_nonvisit | 30 | 24–75 | `traces/case-035_p8_s1124.csv` |
| case-036 | 22 / 1103 | high_bathroom_nonvisit | 29 | 23–51 | `traces/case-036_p22_s1103.csv` |
| case-037 | 12 / 1124 | high_bathroom_nonvisit | 28 | 26–102 | `traces/case-037_p12_s1124.csv` |
| case-038 | 2 / 1112 | active_task_stagnation | 28 | 30–57 | `traces/case-038_p2_s1112.csv` |
| case-039 | 24 / 1106 | high_bathroom_nonvisit | 28 | 28–61 | `traces/case-039_p24_s1106.csv` |
| case-040 | 8 / 1128 | high_bathroom_nonvisit | 28 | 33–60 | `traces/case-040_p8_s1128.csv` |
| case-041 | 20 / 1101 | active_task_stagnation | 27 | 7–33 | `traces/case-041_p20_s1101.csv` |
| case-042 | 21 / 1101 | high_bathroom_nonvisit | 27 | 28–61 | `traces/case-042_p21_s1101.csv` |
| case-043 | 22 / 1112 | high_bathroom_nonvisit | 27 | 18–87 | `traces/case-043_p22_s1112.csv` |
| case-044 | 8 / 1103 | high_bathroom_nonvisit | 27 | 45–71 | `traces/case-044_p8_s1103.csv` |
| case-045 | 20 / 1103 | commitment_suspension | 26 | 12–37 | `traces/case-045_p20_s1103.csv` |
| case-046 | 11 / 1106 | commitment_suspension | 25 | 15–39 | `traces/case-046_p11_s1106.csv` |
| case-047 | 8 / 1102 | same_action_run | 8 | 176–183 | `traces/case-047_p8_s1102.csv` |
| case-048 | 1 / 1109 | same_action_run | 6 | 115–120 | `traces/case-048_p1_s1109.csv` |
| case-049 | 13 / 1103 | same_action_run | 6 | 80–85 | `traces/case-049_p13_s1103.csv` |
| case-050 | 13 / 1120 | zero_time_loop | 6 | 239–244 | `traces/case-050_p13_s1120.csv` |
| case-051 | 16 / 1107 | zero_time_loop | 6 | 215–220 | `traces/case-051_p16_s1107.csv` |
| case-052 | 17 / 1127 | zero_time_loop | 6 | 213–218 | `traces/case-052_p17_s1127.csv` |

## Reviewer rule

A screening tag is not a pathology label. For every case, record whether it is a true positive, true negative, false positive, or false negative before proposing a candidate metric.
