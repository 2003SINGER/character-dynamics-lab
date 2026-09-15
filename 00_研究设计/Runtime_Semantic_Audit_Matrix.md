# Runtime v1 semantic audit matrix

本表是 `RUNTIME_V1_CLOSURE_AND_PROJECT_STABILIZATION` 的独立复核输入，不把 telemetry 当成心理机制证据。

| 来源 | W/runtime 输出 | O/ΔO | X/S consumer | gate/状态 | 结论 |
|---|---|---|---|---|---|
| message | `message-study-group` | `message.unread_count` | social-task appraisal | weak event，gate closed | consumed |
| alarm | alarm event | alarm fact | alarm appraisal | policy relevance | consumed |
| weather | weather event | `outside.weather`（受 curtain/access 控制） | weather appraisal | hidden 时不开放 | consumed |
| temperature | temperature event | temperature fact | comfort appraisal | policy relevance | consumed |
| task reminder | reminder event | task reminder fact | task-pressure appraisal | gate by relevance | consumed |
| task deadline | deadline event | deadline fact | deadline appraisal | gate by relevance | consumed |
| evening | evening event | time/evening fact | rest/sleep appraisal | policy relevance | consumed |
| completion | typed `WorldOutcome` | task status ΔO | GoalCompletion signal → S impulse | completion gate | consumed exactly once |
| rejection | typed `RuntimeRejection` | constraint/target ΔO | rejection appraisal → S impulse | rejection gate | consumed exactly once |
| interruption | typed runtime outcome | interruption feedback | plan/reconsideration appraisal | policy gate | consumed |

Key naming is centralized in `FactKey`; no generic ontology framework is introduced. Commitment update runs in the canonical scheduler-native boundary before self-action feedback is consumed, and reads actor-local feedback only.
