# ParameterConfig v0 mapping

`Simulation` owns an immutable `ParameterConfig`; state and decision operators
receive it explicitly. Defaults are all `1.0`, preserving the pre-parameterized
formulas within floating-point tolerance.

| field | current operator controlled |
|---|---|
| `state_accumulation` | positive task-pressure accumulation term |
| `state_recovery_strength` | negative fatigue recovery term |
| `state_decay` | negative task-pressure relaxation term |
| `task_pressure_coupling` | appraisal + semantic task-pressure contribution |
| `study_fatigue_penalty` | focused/partial study fatigue penalty terms |
| `task_drive_coefficient` | decision task-drive scale |
| `distraction_weight` | decision distraction scale |
| `commitment_bonus` | existing commitment bonus |
| `recovery_drive_coefficient` | decision recovery-drive scale |

Observability, fixture schedules, split seeds, hard gates, and evaluator
thresholds are not parameters. Each listed field is active in the current
state/decision path; the end-to-end smoke records distinct Engine config
hashes and candidate-specific trajectories.
