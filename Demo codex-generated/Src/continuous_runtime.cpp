#include "continuous_runtime.h"

ContinuousRuntime::ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation)
    : scheduler_(scheduler), world_runtime_(world, scheduler), observation_(observation) {}

bool ContinuousRuntime::schedule_next_world_boundary() {
    return world_runtime_.schedule_next_world_boundary(scheduler_);
}

WorldOutcome ContinuousRuntime::submit_action_intent(ActionType action, const std::string& target_object_id,
                                                     int duration_minutes, bool interruptible) {
    WorldOutcome validation = world_runtime_.validate_runtime_start(action, target_object_id);
    if (!validation.accepted) {
        scheduler_.reject_action(action, target_object_id);
        apply_self_action_feedback(observation_, validation, world_runtime_.time_summary());
        return validation;
    }
    scheduler_.start_action(action, target_object_id, duration_minutes, interruptible);
    return validation;
}

ContinuousRuntimeStep ContinuousRuntime::advance_next_boundary() {
    const RuntimeBoundary boundary = scheduler_.advance_to_next_boundary();
    const std::vector<WorldEvent> events = world_runtime_.advance_to_boundary(boundary, scheduler_);
    apply_world_events(observation_, events, world_runtime_.time_summary());
    schedule_next_world_boundary();
    return {boundary, events};
}
