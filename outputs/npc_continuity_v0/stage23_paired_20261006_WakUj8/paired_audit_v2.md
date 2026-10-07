# Paired NPC continuity trace audit

Scope: protocol/input consistency and recorded Runtime outcomes only. This is not a player evaluation, behavior-quality score, or policy-preference judgement.

| Case | Policy | End | Min | Horizon | Policy calls | Starts | Action completions | Interruptions | Continuation intervals | Replacement validation (performed/rejected) | Typed rejections | Task completed | HTTP calls | API ms | Tokens P/C |
|---|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alarm_active | utility | horizon | 90 | True | 4 | 4 | 3 | 1 | 2 | 1/0 | 0 | 0 | 0 | unknown (no HTTP timing) | unknown |
| alarm_active | history-llm | horizon | 90 | True | 3 | 3 | 2 | 1 | 2 | 1/0 | 0 | 0 | 3 | 18883 | 4963/24 |
| quiet_active | utility | horizon | 90 | True | 2 | 2 | 2 | 0 | 2 | 0/0 | 0 | 0 | 0 | unknown (no HTTP timing) | unknown |
| quiet_active | history-llm | horizon | 90 | True | 2 | 2 | 2 | 0 | 2 | 0/0 | 0 | 0 | 2 | 11337 | 3182/16 |
| near_completion_alarm | utility | horizon | 90 | True | 6 | 6 | 5 | 1 | 2 | 1/0 | 0 | 1 | 0 | unknown (no HTTP timing) | unknown |
| near_completion_alarm | history-llm | horizon | 90 | True | 6 | 6 | 5 | 1 | 1 | 1/0 | 0 | 0 | 6 | 33472 | 10410/48 |

## Pair integrity

| Case | Same setup/O/running | Same first O/clock/history/candidates | Both full horizon |
|---|:---:|:---:|:---:|
| alarm_active | True | True | True |
| quiet_active | True | True | True |
| near_completion_alarm | True | True | True |

Action duration is attributed to a running `running_before` over each `[from, at)` interval. Starts counted here are Runtime transitions after the initial scenario action (which is excluded); same-running-action intervals also include boundaries with a closed policy gate. Action completion, interruption, task completion, and typed rejection are separate counts. Replacement validation counts include only `performed=true`; unperformed replacements are not rejections. `selected_action` is not treated as execution. Task completion is counted only from accepted typed Runtime outcomes and cross-checked with final World task status.

Utility has no HTTP request; its model-call latency/tokens are not applicable, and CPU execution latency is unavailable rather than zero. HTTP elapsed time is transport/API timing from the journal, not inference-only timing. A call-limit/error stop is not reported as a full-horizon run.

## Near-completion case: recorded task state and decision inputs

The table reports raw debug task progress and policy-selected intent at policy boundaries; selection is not execution, and no reason is inferred from the policy choice.

| Policy | Minute | Task status | Effort / target | Remaining | Selected intent | StudyFocused candidate present |
|---|---:|---|---:|---:|---|:---:|
| utility | 540 | active | 7.7 / 8 | 0.2999999999999998 | turn_off_alarm | True |
| utility | 541 | active | 7.7 / 8 | 0.2999999999999998 | study_at_computer | True |
| utility | 576 | completed | 8 / 8 | 0.0 | idle | False |
| utility | 586 | completed | 8 / 8 | 0.0 | idle | False |
| utility | 596 | completed | 8 / 8 | 0.0 | idle | False |
| utility | 606 | completed | 8 / 8 | 0.0 | idle | False |
| history-llm | 540 | active | 7.7 / 8 | 0.2999999999999998 | study_halfhearted | True |
| history-llm | 575 | active | 7.962369218455723 / 8 | 0.03763078154427735 | idle | True |
| history-llm | 585 | active | 7.962369218455723 / 8 | 0.03763078154427735 | idle | True |
| history-llm | 595 | active | 7.962369218455723 / 8 | 0.03763078154427735 | idle | True |
| history-llm | 605 | active | 7.962369218455723 / 8 | 0.03763078154427735 | idle | True |
| history-llm | 615 | active | 7.962369218455723 / 8 | 0.03763078154427735 | idle | True |

An active task near its target is not a completed task. Completion counts above require `task_completed=true` in a typed Runtime outcome and agreement with the final World task status.
