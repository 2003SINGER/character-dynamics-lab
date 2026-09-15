#pragma once

#include "action.h"

#include <optional>
#include <string>
#include <vector>

// Runtime Scheduler v1 is deliberately independent of the action-step
// reference engine. It provides the temporal backbone for a future continuous
// runtime; it does not yet replace World settlement, O, X, S, or policy.
enum class RunningActionStatus { Running, Completed, Interrupted, Rejected };

struct RunningAction {
    ActionType action = ActionType::Idle;
    std::string target_object_id;
    int started_at_total_minutes = 0;
    int planned_duration_minutes = 0;
    int elapsed_minutes = 0;
    bool interruptible = true;
    RunningActionStatus status = RunningActionStatus::Running;
};

struct RuntimeRejection {
    ActionType action = ActionType::Idle;
    std::string target_object_id;
    int failure_reason = 0;
    std::string provenance;
};

struct ScheduledRuntimeEvent {
    std::string id;
    int occurs_at_total_minutes = 0;
    bool opens_decision_gate = false;
    bool interrupts_running_action = false;
    std::optional<RuntimeRejection> rejection;
};

enum class DecisionGateReason {
    None,
    Initial,
    ActionCompleted,
    ActionRejected,
    StrongExternalEvent,
    ActionInterrupted,
    NeedThresholdCrossed,
    CommitmentReconsideration,
    PlanInvalidated
};

struct DecisionGate {
    bool open = false;
    std::vector<DecisionGateReason> reasons;
};

struct RuntimeBoundary {
    int from_total_minutes = 0;
    int at_total_minutes = 0;
    int elapsed_minutes = 0;
    std::vector<ScheduledRuntimeEvent> events;
    std::optional<RunningAction> action_after_boundary;
    DecisionGate decision_gate;
};

// Event-driven clock. `advance_to_next_boundary` jumps to the next scheduled
// event or action completion and reports the exact elapsed duration. A caller
// integrates W and continuous S dynamics over that duration, then routes the
// returned events through O -> X -> S. Policy is only consulted when the gate
// is open; ordinary weak events need not reopen a decision. At one shared
// timestamp the contract is deterministic: first integrate [previous,t), then
// process exogenous events at t; an interrupting event preempts completion of
// an otherwise completed interruptible action. Only then is completion settled.
class RuntimeScheduler {
public:
    explicit RuntimeScheduler(int start_total_minutes = 0, int max_runtime_step_minutes = 60)
        : now_total_minutes_(start_total_minutes), max_runtime_step_minutes_(max_runtime_step_minutes) {}

    int now_total_minutes() const { return now_total_minutes_; }
    int max_runtime_step_minutes() const { return max_runtime_step_minutes_; }
    const std::optional<RunningAction>& running_action() const { return running_action_; }

    void schedule(ScheduledRuntimeEvent event);
    void start_action(ActionType action, std::string target_object_id,
                      int duration_minutes, bool interruptible = true);
    void invalidate_running_action();
    // Settlement failures are emitted into the next one-minute transition,
    // rather than allowing another decision at the same simulation instant.
    void reject_action(ActionType action, std::string target_object_id,
                       std::optional<RuntimeRejection> rejection = std::nullopt);
    RuntimeBoundary advance_to_next_boundary();

private:
    int now_total_minutes_ = 0;
    int max_runtime_step_minutes_ = 60;
    std::optional<RunningAction> running_action_;
    std::vector<ScheduledRuntimeEvent> scheduled_events_;
};

const char* to_string(RunningActionStatus status);
const char* to_string(DecisionGateReason reason);
