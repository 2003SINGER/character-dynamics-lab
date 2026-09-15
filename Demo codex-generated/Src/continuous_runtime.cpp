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

void ContinuousRuntime::invalidate_running_action() {
    scheduler_.invalidate_running_action();
}

ContinuousRuntimeStep ContinuousRuntime::advance_next_boundary() {
    const RuntimeBoundary boundary = scheduler_.advance_to_next_boundary();
    const std::vector<WorldEvent> events = world_runtime_.advance_to_boundary(boundary, scheduler_);
    apply_world_events(observation_, events, world_runtime_.world(), {}, world_runtime_.time_summary());
    schedule_next_world_boundary();
    return {boundary, events};
}

RuntimeExecutionResult ContinuousRuntime::execute_next_boundary(CharacterState& state, const Personality& personality) {
    RuntimeExecutionResult result;
    result.runtime = advance_next_boundary();
    const auto& action = result.runtime.boundary.action_after_boundary;
    result.continuous_state = advance_continuous_state(state, personality,
        action.has_value() ? &*action : nullptr, result.runtime.boundary.elapsed_minutes);
    if (action.has_value() && action->status == RunningActionStatus::Completed) {
        result.outcome = world_runtime_.world().settle_runtime_completion(
            action->action, action->target_object_id, action->elapsed_minutes);
        apply_self_action_feedback(observation_, *result.outcome, world_runtime_.time_summary());
    } else if (action.has_value() && action->status == RunningActionStatus::Interrupted) {
        WorldOutcome invalidation;
        invalidation.action = action->action;
        invalidation.target_object_id = action->target_object_id;
        invalidation.action_elapsed_minutes = action->elapsed_minutes;
        invalidation.provenance = "ContinuousRuntime::plan_invalidated";
        invalidation.plan_invalidated = true;
        result.outcome = invalidation;
        apply_self_action_feedback(observation_, *result.outcome, world_runtime_.time_summary());
    }
    result.appraisal = appraise(observation_, state, personality);
    result.impulse_state = apply_appraisal_impulse(state, result.appraisal, personality);
    if (result.runtime.boundary.decision_gate.open) {
        result.decision = decide(observation_, state, personality);
        for (const CandidateAction& candidate : result.decision.candidates) {
            if (candidate.probability > 0.0) {
                submit_action_intent(candidate.action, candidate.target_object_id,
                                     action_definition(candidate.action).default_duration_minutes);
                break;
            }
        }
    }
    return result;
}
