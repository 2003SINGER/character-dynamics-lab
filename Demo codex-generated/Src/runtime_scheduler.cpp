#include "runtime_scheduler.h"

#include <algorithm>
#include <stdexcept>

namespace {
void add_reason(DecisionGate& gate, DecisionGateReason reason) {
    gate.open = true;
    if (std::find(gate.reasons.begin(), gate.reasons.end(), reason) == gate.reasons.end()) {
        gate.reasons.push_back(reason);
    }
}
} // namespace

const char* to_string(RunningActionStatus status) {
    switch (status) {
    case RunningActionStatus::Running: return "running";
    case RunningActionStatus::Completed: return "completed";
    case RunningActionStatus::Interrupted: return "interrupted";
    case RunningActionStatus::Rejected: return "rejected";
    }
    return "unknown";
}

const char* to_string(DecisionGateReason reason) {
    switch (reason) {
    case DecisionGateReason::None: return "none";
    case DecisionGateReason::Initial: return "initial";
    case DecisionGateReason::ActionCompleted: return "action_completed";
    case DecisionGateReason::ActionRejected: return "action_rejected";
    case DecisionGateReason::StrongExternalEvent: return "strong_external_event";
    case DecisionGateReason::ActionInterrupted: return "action_interrupted";
    case DecisionGateReason::NeedThresholdCrossed: return "need_threshold_crossed";
    case DecisionGateReason::CommitmentReconsideration: return "commitment_reconsideration";
    case DecisionGateReason::PlanInvalidated: return "plan_invalidated";
    }
    return "unknown";
}

void RuntimeScheduler::schedule(ScheduledRuntimeEvent event) {
    if (event.occurs_at_total_minutes <= now_total_minutes_) {
        throw std::invalid_argument("Scheduled runtime event must occur after the current clock time");
    }
    const auto duplicate = std::find_if(scheduled_events_.begin(), scheduled_events_.end(),
        [&event](const ScheduledRuntimeEvent& existing) {
            return existing.id == event.id && existing.occurs_at_total_minutes == event.occurs_at_total_minutes;
        });
    if (duplicate == scheduled_events_.end()) scheduled_events_.push_back(std::move(event));
}

void RuntimeScheduler::start_action(ActionType action, std::string target_object_id,
                                    int duration_minutes, bool interruptible) {
    if (running_action_.has_value()) {
        throw std::logic_error("Cannot start an action while another action is running");
    }
    if (duration_minutes <= 0) {
        throw std::invalid_argument("Running action duration must be positive");
    }
    running_action_ = {action, std::move(target_object_id), now_total_minutes_, duration_minutes,
                       0, interruptible, RunningActionStatus::Running};
}

void RuntimeScheduler::invalidate_running_action() {
    if (!running_action_.has_value()) throw std::logic_error("Cannot invalidate without a running action");
    schedule({"action_invalidated", now_total_minutes_ + 1, true, std::nullopt,
              DecisionGateReason::PlanInvalidated});
}

void RuntimeScheduler::replace_running_action(ActionType action, std::string target_object_id,
                                               int duration_minutes, bool interruptible) {
    if (!running_action_.has_value()) throw std::logic_error("Cannot replace without a running action");
    if (duration_minutes <= 0) throw std::invalid_argument("Running action duration must be positive");
    running_action_ = {action, std::move(target_object_id), now_total_minutes_, duration_minutes,
                       0, interruptible, RunningActionStatus::Running};
}

void RuntimeScheduler::reject_action(ActionType action, std::string target_object_id,
                                     std::optional<RuntimeRejection> rejection) {
    // A rejection is feedback for a proposed intent. It does not modify an
    // unrelated running action; the actor receives it at the next transition.
    schedule({"action_rejected:" + to_string(action) + ":" + target_object_id,
              now_total_minutes_ + 1, false, std::move(rejection),
              running_action_.has_value() ? std::optional<DecisionGateReason>{}
                                           : std::optional<DecisionGateReason>{DecisionGateReason::ActionRejected}});
}

RuntimeBoundary RuntimeScheduler::advance_to_next_boundary() {
    int next = -1;
    if (running_action_.has_value()) {
        next = running_action_->started_at_total_minutes + running_action_->planned_duration_minutes;
    }
    for (const ScheduledRuntimeEvent& event : scheduled_events_) {
        if (next < 0 || event.occurs_at_total_minutes < next) next = event.occurs_at_total_minutes;
    }
    if (max_runtime_step_minutes_ > 0) {
        const int bounded = now_total_minutes_ + max_runtime_step_minutes_;
        if (next < 0 || bounded < next) next = bounded;
    }
    if (next < 0) throw std::logic_error("RuntimeScheduler has no next boundary");

    RuntimeBoundary boundary;
    boundary.from_total_minutes = now_total_minutes_;
    boundary.at_total_minutes = next;
    boundary.elapsed_minutes = next - now_total_minutes_;
    now_total_minutes_ = next;

    if (running_action_.has_value()) {
        running_action_->elapsed_minutes += boundary.elapsed_minutes;
    }
    for (auto it = scheduled_events_.begin(); it != scheduled_events_.end();) {
        if (it->occurs_at_total_minutes != now_total_minutes_) {
            ++it;
            continue;
        }
        boundary.events.push_back(*it);
        if (it->gate_reason.has_value()) add_reason(boundary.decision_gate, *it->gate_reason);
        if (it->interrupts_running_action && running_action_.has_value() && running_action_->interruptible) {
            running_action_->status = RunningActionStatus::Interrupted;
            add_reason(boundary.decision_gate, DecisionGateReason::ActionInterrupted);
        }
        it = scheduled_events_.erase(it);
    }

    if (running_action_.has_value()
        && running_action_->status == RunningActionStatus::Running
        && running_action_->elapsed_minutes == running_action_->planned_duration_minutes) {
        running_action_->status = RunningActionStatus::Completed;
        add_reason(boundary.decision_gate, DecisionGateReason::ActionCompleted);
    }
    boundary.action_after_boundary = running_action_;
    if (running_action_.has_value() && running_action_->status != RunningActionStatus::Running) {
        running_action_.reset();
    }
    return boundary;
}
