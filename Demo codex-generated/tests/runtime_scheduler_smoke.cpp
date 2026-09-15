#include "runtime_scheduler.h"

#include <iostream>

namespace {
bool has_reason(const DecisionGate& gate, DecisionGateReason reason) {
    for (DecisionGateReason item : gate.reasons) if (item == reason) return true;
    return false;
}
}

int main() {
    RuntimeScheduler scheduler(9 * 60);
    scheduler.start_action(ActionType::StudyFocused, "desk", 35, true);
    scheduler.schedule({"message", 9 * 60 + 10, false, std::nullopt});
    scheduler.schedule({"temperature_drop", 9 * 60 + 20, false, std::nullopt});

    const RuntimeBoundary first = scheduler.advance_to_next_boundary();
    const RuntimeBoundary second = scheduler.advance_to_next_boundary();
    const RuntimeBoundary third = scheduler.advance_to_next_boundary();
    if (first.elapsed_minutes != 10 || first.decision_gate.open || first.events.size() != 1
        || second.elapsed_minutes != 10 || second.decision_gate.open || second.events.size() != 1
        || third.elapsed_minutes != 15 || !has_reason(third.decision_gate, DecisionGateReason::ActionCompleted)
        || !third.action_after_boundary.has_value()
        || third.action_after_boundary->status != RunningActionStatus::Completed
        || scheduler.running_action().has_value()) {
        std::cerr << "action progress / weak-event / completion scheduling failed\n";
        return 1;
    }

    RuntimeScheduler interruption(0);
    interruption.start_action(ActionType::StudyFocused, "desk", 35, true);
    interruption.schedule({"urgent_message", 5, true, std::nullopt, DecisionGateReason::StrongExternalEvent});
    const RuntimeBoundary interrupted = interruption.advance_to_next_boundary();
    if (interrupted.elapsed_minutes != 5
        || !has_reason(interrupted.decision_gate, DecisionGateReason::StrongExternalEvent)
        || !has_reason(interrupted.decision_gate, DecisionGateReason::ActionInterrupted)
        || !interrupted.action_after_boundary.has_value()
        || interrupted.action_after_boundary->status != RunningActionStatus::Interrupted) {
        std::cerr << "strong event interruption scheduling failed\n";
        return 1;
    }

    RuntimeScheduler same_timestamp(0);
    same_timestamp.start_action(ActionType::StudyFocused, "desk", 5, true);
    same_timestamp.schedule({"urgent_message", 5, true, std::nullopt, DecisionGateReason::StrongExternalEvent});
    const RuntimeBoundary preempted_completion = same_timestamp.advance_to_next_boundary();
    if (!has_reason(preempted_completion.decision_gate, DecisionGateReason::ActionInterrupted)
        || has_reason(preempted_completion.decision_gate, DecisionGateReason::ActionCompleted)
        || !preempted_completion.action_after_boundary.has_value()
        || preempted_completion.action_after_boundary->status != RunningActionStatus::Interrupted) {
        std::cerr << "same-timestamp interrupt priority must be explicit\n";
        return 1;
    }

    RuntimeScheduler rejection(100);
    rejection.reject_action(ActionType::ShopOnPhone, "phone");
    const RuntimeBoundary rejected = rejection.advance_to_next_boundary();
    if (rejected.elapsed_minutes != 1 || rejected.at_total_minutes != 101
        || !has_reason(rejected.decision_gate, DecisionGateReason::ActionRejected)) {
        std::cerr << "rejection must consume one runtime transition\n";
        return 1;
    }
    std::cout << "runtime scheduler smoke OK\n";
    return 0;
}
