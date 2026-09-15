# Runtime Scheduler v1｜统一时间骨架

状态：**Continuous Runtime v1 closure 进行中；尚未迁移既有 reference fixtures。**

当前 checkpoint：`TEMPORAL_KERNEL_PASS`；`FIRST_VERTICAL_SLICE_PASS`；
`WORLD_RUNTIME_CLOCK_ADAPTER_PASS`（受控 slice）；完整 canonical owner、typed
outcome flow 与 scheduler-native fixtures 仍未完成。

## 边界

现有 C++ `Simulation` 是 **Action-Step Reference Engine v0**：一次决策直接
结算完整动作，并以动作持续时间跨越世界时间。这仍是 W/O 边界、typed
settlement、commitment 与 rejection feedback 的有效机制对照，但不是持续
runtime，也不应再被描述为逐 tick 的动态系统。

Runtime Scheduler v1 与旧引擎并存，不修改其 batch、evaluator 或优化器。
本阶段只建立“何时运行”的可验证骨架；不新增状态字段、不改变 X/S 内容、
不重新解释已有 fixture，也不冻结任何研究结论。

## Runtime contract

```text
SimulationClock + EventScheduler + RunningAction
        |
        v  advance to the next meaningful boundary by exact Delta-t
W continuous dynamics / action progress / S continuous dynamics
        |
        v
events and settlement outcome -> O -> X -> S impulse
        |
        v
DecisionGate open? -- no --> continue RunningAction
        |
       yes
        v
A^O -> policy -> start / replace RunningAction
```

`SimulationClock` is event-driven here: it jumps to the next scheduled event
or action-completion boundary rather than iterating arbitrary empty minutes.
It still exposes an exact elapsed minute duration, so a later W/S integrator
can use the same timeline for continuous dynamics. A fixed-tick adapter can be
added later without changing the ownership contract.

### Shared-timestamp contract

At a shared timestamp `t`, the scheduler deterministically: (1) integrates
the open interval `[previous, t)`; (2) advances the running action to `t`;
(3) handles exogenous events at `t`; (4) lets an event explicitly marked
interrupting preempt completion of an interruptible action; then (5) settles
completion only if the action is still running. Thus a 10:35 interrupting
event and a 10:35 action completion yield `Interrupted`, not a result that
depends on container iteration order. The scheduler smoke locks this rule.

`RunningAction` is first-class state: action, target, start time, planned and
elapsed duration, interruptibility, and terminal status. Policy is **not**
called once per clock minute. `DecisionGate` only opens for an action
completion, rejection, a strong external event, interruption, a need
threshold, commitment reconsideration, or plan invalidation.

`ContinuousRuntime` now owns action-intent submission and automatically renews
the next W boundary after every step. `WorldRuntimeAdapter::schedule_next_world_boundary` queries W's authoritative
event source and registers the next event; fixtures no longer copy known W
timestamps into the scheduler. `World::validate_runtime_start` is the scheduler-native start gate: policy's
intent must be accepted by W before a `RunningAction` is created. A later
`World::settle_runtime_completion` applies action effects,
counters, task effort and typed `WorldOutcome`, but never advances `World.time`
or scans interval events. Its outcome records both `action_elapsed_minutes`
and `time_advanced_by_settlement`, so provenance does not confuse runtime
duration with settlement clock movement. The scheduler owns elapsed time; W
owns completion effects.

## v1 executable evidence

`RuntimeScheduler` lives in
`Demo codex-generated/Inc/runtime_scheduler.h` and is intentionally world-
agnostic. Its smoke test demonstrates:

1. a 35-minute study action remains running through weak events at +10 and
   +20 minutes without reopening policy;
2. action completion at +35 opens the decision gate;
3. a strong interrupting event at +5 both opens the gate and marks an
   interruptible action interrupted;
4. a rejected action is delivered through a one-minute runtime transition and
   opens the next decision gate, so there cannot be a second decision at the
   same clock instant.

The runtime bridge now provides `World::validate_runtime_start`, typed
rejection payloads, and a perception-aware `apply_world_events` projector;
fixtures must use these APIs rather than duplicating W's event meaning in
key/value writes. Remaining closure work is tracked in the acceptance matrix:
give the rejection event its typed `WorldOutcome` payload and then project it
to O, where the existing `ActionConstraintBelief` can remain the persistent
actor-local consequence. It must not make `W -> S` a shortcut or copy hidden
W values into O.

## First scheduler-native vertical slice

`runtime_vertical_slice_smoke` is the first real W/O/X/S/pi path on the new
clock, while keeping all existing batch machinery on Reference v0:

1. At 09:00 it starts a 35-minute `StudyFocused` `RunningAction`.
2. At 09:10 a weak message event occurs. The 10-minute interval updates S via
   `advance_continuous_state(S, P, RunningAction, Delta-t)`; the permitted
   message payload then enters O, existing X yields `social_task_reminder`,
   and its S impulse is applied with `Delta-t=0`. The gate remains closed.
3. At 09:35 another 25-minute action interval is integrated. The actual W
   study settlement writes its existing self-feedback into O; X/S run, the
   completion gate opens, and existing `decide` produces a next action which
   starts a new `RunningAction`.

The continuous-action coefficients in this adapter are explicitly engineering
placeholders. They prove that elapsed time and `RunningAction` are separate
inputs to S; they do not preserve old action-step magnitudes, claim a
psychological model, or authorize a batch/evaluator migration.

## Migration order and acceptance

1. Complete the canonical runtime owner and typed WorldEvent/ActionOutcome → O
   incremental projection; do not hand-write event payloads in fixtures.
2. Recreate the Deadline fixture natively, proving that a deadline can become
   observable during a long action rather than only after it completes.
3. Recreate Phone and Commitment as scheduler-native fixtures with
   equivalent information-boundary evidence.
4. Only then consider replacing any action-step batch or evaluator path.

Future scheduler boundaries must include state-threshold crossings (or a
bounded numerical step when they cannot be predicted), in addition to world
events, physical preemption, action completion and external input.
The v1 fallback is `RuntimeScheduler::max_runtime_step_minutes` (default 60):
long actions receive bounded integration opportunities even when no event source
can predict a threshold crossing.

At every stage, old and new outputs must have distinct provenance and run
directories. `optimizer_train`, `internal_holdout`, Objective v0 and optimizer
selection remain out of scope.
`ContinuousRuntime::execute_next_boundary` is the canonical orchestration API:
it advances continuous S, settles a completed RunningAction, projects outcome
and events into O, applies X→S impulse, evaluates the gate, and submits the
next policy intent through W validation. The older lower-level calls remain
available for unit tests and are not the fixture-level contract.
