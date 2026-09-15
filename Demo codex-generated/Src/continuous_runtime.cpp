#include "continuous_runtime.h"

namespace {
constexpr double kNeedReconsiderationThreshold = 0.40; // Runtime v1 engineering semantics.
}

ContinuousRuntime::ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation,
                                     InformationAccess access, unsigned int policy_seed)
    : scheduler_(scheduler), world_runtime_(world, scheduler), observation_(observation), access_(access),
      rng_(policy_seed), policy_seed_(policy_seed) {}

bool ContinuousRuntime::schedule_next_world_boundary() {
    return world_runtime_.schedule_next_world_boundary(scheduler_);
}

WorldOutcome ContinuousRuntime::submit_action_intent(ActionType action, const std::string& target_object_id,
                                                     int duration_minutes, bool interruptible) {
    WorldOutcome validation = world_runtime_.validate_runtime_start(action, target_object_id);
    if (!validation.accepted) {
        scheduler_.reject_action(action, target_object_id, RuntimeRejection{
            false, action, target_object_id, static_cast<int>(validation.failure_reason), 0, validation.provenance});
        return validation;
    }
    scheduler_.start_action(action, target_object_id, duration_minutes, interruptible);
    schedule_next_world_boundary();
    return validation;
}

void ContinuousRuntime::invalidate_running_action() {
    scheduler_.invalidate_running_action();
}

RuntimeExecutionResult ContinuousRuntime::execute_next_boundary(CharacterState& state, const Personality& personality) {
    RuntimeExecutionResult result;
    result.policy_seed = policy_seed_;
    const CharacterState before_continuous = state;
    result.runtime.boundary = scheduler_.advance_to_next_boundary();
    const auto& action = result.runtime.boundary.action_after_boundary;
    // Continuous dynamics is integrated before event projection at t.
    result.continuous_state = advance_continuous_state(state, personality,
        action.has_value() ? &*action : nullptr, result.runtime.boundary.elapsed_minutes);
    result.runtime.world_events = world_runtime_.advance_to_boundary(result.runtime.boundary, scheduler_);
    apply_world_events(observation_, result.runtime.world_events, world_runtime_.world(), access_, world_runtime_.time_summary());
    for (const ScheduledRuntimeEvent& event : result.runtime.boundary.events) {
        if (!event.rejection.has_value()) continue;
        WorldOutcome rejection;
        rejection.action = event.rejection->action;
        rejection.target_object_id = event.rejection->target_object_id;
        rejection.failure_reason = static_cast<RejectionReason>(event.rejection->failure_reason);
        rejection.provenance = event.rejection->provenance;
        apply_self_action_feedback(observation_, rejection, world_runtime_.time_summary(), true, false);
    }
    schedule_next_world_boundary();
    bool threshold_reconsideration = false;
    if ((before_continuous.hunger < kNeedReconsiderationThreshold
         && state.hunger >= kNeedReconsiderationThreshold)
        || (before_continuous.bathroom_urge < kNeedReconsiderationThreshold
            && state.bathroom_urge >= kNeedReconsiderationThreshold)) {
        result.runtime.boundary.decision_gate.open = true;
        result.runtime.boundary.decision_gate.reasons.push_back(DecisionGateReason::NeedThresholdCrossed);
        threshold_reconsideration = true;
    }
    if (action.has_value() && action->status == RunningActionStatus::Completed) {
        result.outcome = world_runtime_.world().settle_runtime_completion(
            action->action, action->target_object_id, action->elapsed_minutes);
        result.pre_policy_outcome = result.outcome;
        apply_self_action_feedback(observation_, *result.outcome, world_runtime_.time_summary(),
                                   access_.self_task_completion_observable, false);
    } else if (action.has_value() && action->status == RunningActionStatus::Interrupted) {
        WorldOutcome invalidation;
        invalidation.action = action->action;
        invalidation.target_object_id = action->target_object_id;
        invalidation.action_elapsed_minutes = action->elapsed_minutes;
        invalidation.provenance = "ContinuousRuntime::plan_invalidated";
        invalidation.plan_invalidated = true;
        result.outcome = invalidation;
        result.pre_policy_outcome = result.outcome;
        apply_self_action_feedback(observation_, *result.outcome, world_runtime_.time_summary(), true, false);
    }
    result.appraisal = appraise(observation_, state, personality);
    result.impulse_state = apply_appraisal_impulse(state, result.appraisal, personality);
    update_commitment(state, observation_, scheduler_.now_total_minutes());
    consume_appraisal_inputs(observation_);
    if (result.runtime.boundary.decision_gate.open
        && (result.outcome.has_value() || !action.has_value()
            || action->status != RunningActionStatus::Running || threshold_reconsideration)) {
        result.policy_evaluated = true;
        result.decision = decide(observation_, state, personality);
        const ActionType selected = test_action_selector_ ? test_action_selector_(result.decision)
                                                           : sample_action(result.decision, rng_);
        for (const CandidateAction& candidate : result.decision.candidates) {
            if (candidate.action == selected && candidate.probability > 0.0) {
                result.selected_action = selected;
                result.selected_target_object_id = candidate.target_object_id;
                // A threshold crossing is a subjective reconsideration point. Keep
                // the running action and its elapsed progress unless an explicit
                // physical interruption outcome was produced at this boundary.
                const bool same_intent = action.has_value()
                    && selected == action->action
                    && candidate.target_object_id == action->target_object_id;
                if (threshold_reconsideration && action.has_value()
                    && action->status == RunningActionStatus::Running
                    && !same_intent) {
                    const WorldOutcome validation = world_runtime_.validate_runtime_start(
                        candidate.action, candidate.target_object_id);
                    result.replacement_validation_performed = true;
                    result.replacement_validation_accepted = validation.accepted;
                    if (!validation.accepted) {
                        scheduler_.reject_action(candidate.action, candidate.target_object_id, RuntimeRejection{
                            false, candidate.action, candidate.target_object_id,
                            static_cast<int>(validation.failure_reason), 0, validation.provenance});
                        break;
                    }
                    WorldOutcome reconsideration;
                    reconsideration.action = action->action;
                    reconsideration.target_object_id = action->target_object_id;
                    reconsideration.action_elapsed_minutes = action->elapsed_minutes;
                    reconsideration.task_session_interrupted = true;
                    reconsideration.provenance = "ContinuousRuntime::policy_reconsideration";
                    result.outcome = reconsideration;
                    result.post_policy_outcome = reconsideration;
                    apply_self_action_feedback(observation_, reconsideration,
                                               world_runtime_.time_summary(), true, false);
                    scheduler_.replace_running_action(candidate.action, candidate.target_object_id,
                                                      action_definition(candidate.action).default_duration_minutes);
                } else if (!threshold_reconsideration || !action.has_value()
                           || action->status != RunningActionStatus::Running) {
                    submit_action_intent(candidate.action, candidate.target_object_id,
                                         action_definition(candidate.action).default_duration_minutes);
                }
                break;
            }
        }
    }
    return result;
}
