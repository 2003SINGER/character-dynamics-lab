#include "continuous_runtime.h"

#include <algorithm>

namespace {
}

ContinuousRuntime::ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation,
                                     CharacterDynamicsModel& model, InformationAccess access, unsigned int policy_seed,
                                     CharacterPolicy* policy)
    : scheduler_(scheduler), world_runtime_(world, scheduler), observation_(observation), model_(model),
      policy_(policy ? policy : &default_policy_), access_(access), rng_(policy_seed), policy_seed_(policy_seed) {}

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
    result.policy_id = policy_->identity();
    result.running_action_before = scheduler_.running_action();
    const CharacterState before_continuous = state;
    result.runtime.boundary = scheduler_.advance_to_next_boundary();
    const auto& action = result.runtime.boundary.action_after_boundary;
    result.running_action_after = action;
    // The scheduler is the canonical time owner.  Its clock is an internally
    // observable cue, so Dynamics never has to read hidden W time or operate
    // against a stale O-side deadline.
    apply_observable_runtime_event(observation_, "clock.total_minutes",
                                   std::to_string(result.runtime.boundary.at_total_minutes),
                                   "runtime_internal_clock", world_runtime_.time_summary());
    // Continuous dynamics is integrated before event projection at t.
    result.continuous_state = model_.advance_continuous(state, observation_, personality,
        action.has_value() ? &*action : nullptr, result.runtime.boundary.elapsed_minutes);
    result.runtime.world_events = world_runtime_.advance_to_boundary(result.runtime.boundary, scheduler_);
    apply_world_events(observation_, result.runtime.world_events, world_runtime_.world(), access_, world_runtime_.time_summary());
    if (std::any_of(result.runtime.world_events.begin(), result.runtime.world_events.end(),
                    [](const WorldEvent& event) { return event.id=="task-assigned"; })) {
        rebuild_known_actions_from_observation(observation_);
    }
    for (const ScheduledRuntimeEvent& event : result.runtime.boundary.events) {
        if (!event.rejection.has_value()) continue;
        WorldOutcome rejection;
        rejection.action = event.rejection->action;
        rejection.target_object_id = event.rejection->target_object_id;
        rejection.failure_reason = static_cast<RejectionReason>(event.rejection->failure_reason);
        rejection.provenance = event.rejection->provenance;
        apply_self_action_feedback(observation_, rejection, world_runtime_.time_summary(), true, false);
        rebuild_known_actions_from_observation(observation_);
    }
    schedule_next_world_boundary();
    bool threshold_reconsideration = false;
    if ((before_continuous.hunger < RuntimeConfig::NeedReconsiderationThreshold
         && state.hunger >= RuntimeConfig::NeedReconsiderationThreshold)
        || (before_continuous.bathroom_urge < RuntimeConfig::NeedReconsiderationThreshold
            && state.bathroom_urge >= RuntimeConfig::NeedReconsiderationThreshold)) {
        result.runtime.boundary.decision_gate.open = true;
        result.runtime.boundary.decision_gate.reasons.push_back(DecisionGateReason::NeedThresholdCrossed);
        threshold_reconsideration = true;
    }
    DynamicsReconsideration dynamics_reconsideration;
    if (action.has_value() && action->status == RunningActionStatus::Running) {
        dynamics_reconsideration = model_.reconsider_running_action(
            observation_, before_continuous, state, *action, personality);
        if (dynamics_reconsideration.requested) {
            result.runtime.boundary.decision_gate.open = true;
            result.runtime.boundary.decision_gate.reasons.push_back(
                DecisionGateReason::DynamicsReconsideration);
            result.dynamics_reconsideration_reason = dynamics_reconsideration.reason;
        }
    }
    if (action.has_value() && action->status == RunningActionStatus::Completed) {
        result.pre_policy_outcome = world_runtime_.world().settle_runtime_completion(
            action->action, action->target_object_id, action->elapsed_minutes);
        apply_self_action_feedback(observation_, *result.pre_policy_outcome, world_runtime_.time_summary(),
                                   access_.self_task_completion_observable, false);
        rebuild_known_actions_from_observation(observation_);
    } else if (action.has_value() && action->status == RunningActionStatus::Interrupted) {
        WorldOutcome invalidation;
        invalidation.action = action->action;
        invalidation.target_object_id = action->target_object_id;
        invalidation.action_elapsed_minutes = action->elapsed_minutes;
        invalidation.provenance = "ContinuousRuntime::plan_invalidated";
        invalidation.plan_invalidated = true;
        result.pre_policy_outcome = invalidation;
        apply_self_action_feedback(observation_, *result.pre_policy_outcome, world_runtime_.time_summary(), true, false);
        rebuild_known_actions_from_observation(observation_);
    }
    result.appraisal = model_.appraise(observation_, state, personality);
    result.impulse_state = model_.apply_impulse(state, result.appraisal, personality);
    result.observation_deltas = observation_.updates_this_refresh;
    model_.update_persistent_intention(state, observation_, scheduler_.now_total_minutes());
    consume_appraisal_inputs(observation_);
    const bool rejection_reconsideration = std::find(
        result.runtime.boundary.decision_gate.reasons.begin(),
        result.runtime.boundary.decision_gate.reasons.end(),
        DecisionGateReason::ActionRejected) != result.runtime.boundary.decision_gate.reasons.end();
    // Feedback for a rejected replacement is itself a decision opportunity.
    // It preserves the old action unless the informed next policy sample
    // explicitly replaces it, just like a subjective need/recovery gate.
    const bool subjective_reconsideration = threshold_reconsideration
        || dynamics_reconsideration.requested || rejection_reconsideration;
    if (result.runtime.boundary.decision_gate.open
        && (result.pre_policy_outcome.has_value() || !action.has_value()
            || action->status != RunningActionStatus::Running || subjective_reconsideration)) {
        result.policy_evaluated = true;
        result.decision = model_.build_policy(observation_, state, personality);
        const PolicySelection selection = test_action_selector_
            ? PolicySelection{test_action_selector_(result.decision), "test-selector", "test-only override"}
            : policy_->select(result.decision, observation_, state, personality, rng_);
        result.policy_id = selection.policy_id;
        result.policy_selection_provenance = selection.provenance;
        const ActionType selected = selection.action;
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
                if (subjective_reconsideration && action.has_value()
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
                    result.post_policy_outcome = reconsideration;
                    apply_self_action_feedback(observation_, reconsideration,
                                               world_runtime_.time_summary(), true, false);
                    scheduler_.replace_running_action(candidate.action, candidate.target_object_id,
                                                      action_definition(candidate.action).default_duration_minutes);
                } else if (!subjective_reconsideration || !action.has_value()
                           || action->status != RunningActionStatus::Running) {
                    submit_action_intent(candidate.action, candidate.target_object_id,
                                         action_definition(candidate.action).default_duration_minutes);
                }
                break;
            }
        }
    }
    result.running_action_after = scheduler_.running_action();
    return result;
}
