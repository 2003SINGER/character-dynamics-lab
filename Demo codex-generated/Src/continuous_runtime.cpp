#include "continuous_runtime.h"
#include "simulation_time.h"

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
    const auto capture_episode = [&](const RunningAction& episode, int end, bool interrupted,
                                     const std::string& outcome, bool accepted, const std::string& task_id,
                                     const std::string& identity_suffix) {
        const std::string key = std::to_string(episode.started_at_total_minutes) + ":" +
            std::to_string(static_cast<int>(episode.action)) + ":" + episode.target_object_id + ":" + identity_suffix;
        if (key == last_captured_action_key_) return;
        actor_history_.episodes.push_back({episode.action, episode.target_object_id,
            episode.started_at_total_minutes, end, episode.planned_duration_minutes,
            std::max(0, end - episode.started_at_total_minutes), accepted, interrupted,
            outcome, task_id});
        last_captured_action_key_ = key;
        while (!actor_history_.episodes.empty()
               && end - actor_history_.episodes.front().end_total_minutes > 48 * 60)
            actor_history_.episodes.pop_front();
    };
    // The scheduler is the canonical time owner.  Its clock is an internally
    // observable cue, so Dynamics never has to read hidden W time or operate
    // against a stale O-side deadline.
    const int scheduler_minutes = result.runtime.boundary.at_total_minutes;
    const SimTime scheduler_time{scheduler_minutes / (24 * 60) + 1,
                                 scheduler_minutes % (24 * 60)};
    const std::string scheduler_time_text = time_summary(scheduler_time);
    apply_observable_runtime_event(observation_, FactKey::ClockTime,
                                   scheduler_time_text, "runtime_internal_clock", scheduler_time_text);
    apply_observable_runtime_event(observation_, "clock.total_minutes",
                                   std::to_string(scheduler_minutes),
                                   "runtime_internal_clock", scheduler_time_text);
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
        RunningAction rejected_attempt;
        rejected_attempt.action = event.rejection->action;
        rejected_attempt.target_object_id = event.rejection->target_object_id;
        rejected_attempt.started_at_total_minutes = scheduler_minutes;
        rejected_attempt.planned_duration_minutes = action_definition(rejected_attempt.action).default_duration_minutes;
        capture_episode(rejected_attempt, scheduler_minutes, false, "rejected", false, "",
                        "rejection:" + event.id);
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
        if (!result.runtime.boundary.decision_gate.open) {
            result.model_soft_reconsideration = policy_->soft_reconsider_with_history(
                observation_, state, personality, *action, actor_history_, rng_);
            if (result.model_soft_reconsideration.has_value()
                && result.model_soft_reconsideration->requested) {
                result.runtime.boundary.decision_gate.open = true;
                result.runtime.boundary.decision_gate.reasons.push_back(
                    DecisionGateReason::ModelSoftReconsideration);
            }
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
    if (result.running_action_before && action.has_value()
        && (action->status == RunningActionStatus::Completed || action->status == RunningActionStatus::Interrupted)) {
        const WorldOutcome* feedback = result.pre_policy_outcome ? &*result.pre_policy_outcome : nullptr;
        const ObservedAction& observed = observation_.last_self_action;
        capture_episode(*result.running_action_before, scheduler_minutes,
            action->status == RunningActionStatus::Interrupted || (feedback && feedback->task_session_interrupted),
            observed.has_action ? (observed.accepted ? (observed.task_completed ? "task_completed" : "settled") : "rejected") : "settled",
            observed.has_action ? observed.accepted : true,
            observed.has_action ? observed.task_id : std::string{}, "terminal");
    }
    for (const ObservationFact& fact : observation_.updates_this_refresh) {
        if (fact.status != KnowledgeStatus::Known && fact.status != KnowledgeStatus::Stale) continue;
        if (fact.key == "clock.total_minutes" || fact.key == FactKey::ClockTime || fact.key == FactKey::EveningPhase) continue;
        actor_history_.events.push_back({scheduler_minutes, fact.key, fact.value});
    }
    while (!actor_history_.events.empty() && scheduler_minutes - actor_history_.events.front().total_minutes > 48 * 60)
        actor_history_.events.pop_front();
    result.appraisal = model_.appraise_with_history(observation_, state, personality, actor_history_);
    result.impulse_state = model_.apply_impulse(state, result.appraisal, personality);
    result.observation_deltas = observation_.updates_this_refresh;
    result.typed_commitment_decision = model_.update_persistent_intention_typed_with_history(
        state, observation_, personality, scheduler_.now_total_minutes(), rng_, actor_history_);
    consume_appraisal_inputs(observation_);
    const bool rejection_reconsideration = std::find(
        result.runtime.boundary.decision_gate.reasons.begin(),
        result.runtime.boundary.decision_gate.reasons.end(),
        DecisionGateReason::ActionRejected) != result.runtime.boundary.decision_gate.reasons.end();
    // Feedback for a rejected replacement is itself a decision opportunity.
    // It preserves the old action unless the informed next policy sample
    // explicitly replaces it, just like a subjective need/recovery gate.
    const bool subjective_reconsideration = threshold_reconsideration
        || dynamics_reconsideration.requested || rejection_reconsideration
        || (result.model_soft_reconsideration.has_value()
            && result.model_soft_reconsideration->requested);
    if (result.runtime.boundary.decision_gate.open
        && (result.pre_policy_outcome.has_value() || !action.has_value()
            || action->status != RunningActionStatus::Running || subjective_reconsideration)) {
        result.policy_evaluated = true;
        result.decision = model_.build_policy(observation_, state, personality);
        const PolicySelection selection = test_action_selector_
            ? PolicySelection{test_action_selector_(result.decision), "test-selector", "test-only override", {}}
            : policy_->select_with_history(result.decision, observation_, state, personality,
                                           actor_history_, action ? &*action : nullptr, rng_);
        result.policy_id = selection.policy_id;
        result.policy_selection_provenance = selection.provenance;
        result.sampled_policy_probabilities = selection.probabilities;
        // Trace the policy distribution actually sampled. RulePolicy leaves
        // its soft-filtered surface unchanged; typed Laya uses every O-known,
        // hard-admissible candidate while retaining the Rule eligibility cue.
        if (!selection.probabilities.empty()) {
            for (CandidateAction& candidate : result.decision.candidates) {
                candidate.probability = 0.0;
                for (const auto& [action, probability] : selection.probabilities)
                    if (candidate.action == action) candidate.probability = probability;
                if (selection.policy_id == "laya-typed-policy-v0")
                    candidate.eligible = candidate.hard_admissible;
            }
        }
        const ActionType selected = selection.action;
        for (const CandidateAction& candidate : result.decision.candidates) {
            if (candidate.action == selected && candidate.hard_admissible && candidate.probability > 0.0) {
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
                    capture_episode(*action, scheduler_minutes, true, "policy_replaced", true,
                                    observation_.last_self_action.task_id, "replacement");
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
