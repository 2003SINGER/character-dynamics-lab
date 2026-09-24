#include "laya_augmented_dynamics_v1.h"

#include <algorithm>

namespace {
bool material_update(const Observation& observation) {
    if (observation.last_self_action.has_action) return true;
    return std::any_of(observation.updates_this_refresh.begin(),
        observation.updates_this_refresh.end(), [](const ObservationFact& fact) {
            return fact.key != "clock.total_minutes" && fact.key != "clock.time"
                && fact.key != FactKey::EveningPhase;
        });
}

bool new_task_episode(const Observation& observation) {
    return std::any_of(observation.updates_this_refresh.begin(),
        observation.updates_this_refresh.end(), [](const ObservationFact& fact) {
            return fact.key == "task.coursework.episode";
        });
}

double intensity(const LayaTypedScores& scores, const char* key) {
    return scores.values.at(key) / 4.0;
}
}

StateUpdate LayaAugmentedDynamicsV1::advance_continuous(
    CharacterState& state, const Observation& observation, const Personality& personality,
    const RunningAction* action, int elapsed) const {
    return base_.advance_continuous(state, observation, personality, action, elapsed);
}

Appraisal LayaAugmentedDynamicsV1::appraise(
    const Observation& observation, const CharacterState& state,
    const Personality& personality) const {
    Appraisal appraisal = base_.appraise(observation, state, personality);
    if (!typed_appraisal_) return appraisal;
    if (!material_update(observation)) return appraisal;
    const LayaTypedScores typed = client_.score_appraisal(observation, state, personality);
    std::vector<AppraisalSignal> canonical_completion;
    for (const AppraisalSignal& signal : appraisal.semantic_signals)
        if (signal.kind == AppraisalSignalKind::GoalCompletion)
            canonical_completion.push_back(signal);
    appraisal.semantic_signals = std::move(canonical_completion);
    appraisal.tags = {"laya_typed_appraisal"};
    const bool completed = !appraisal.semantic_signals.empty();
    if (completed) appraisal.tags.push_back("task_completed");
    // Keep bodily relief, environmental fatigue, screen strain, purchase
    // inventory and O-derived pressure geometry from deterministic Dynamics.
    // Laya replaces only subjective interpretation, never those channels.
    appraisal.boredom_delta = -0.18 * intensity(typed, "stimulation");
    appraisal.satisfaction_delta = 0.0;
    appraisal.anxiety_delta = 0.04 * intensity(typed, "uncertainty")
        * personality.task_anxiety_sensitivity;
    auto add = [&](AppraisalSignalKind kind, double value, const char* source) {
        appraisal.semantic_signals.push_back({kind, value, 1.0, 1.0, 0.0, source});
    };
    if (!completed) {
        add(AppraisalSignalKind::GoalProgress, intensity(typed, "goal_progress"), "laya:goal_progress");
        add(AppraisalSignalKind::ShortTermReward, intensity(typed, "positive_outcome"), "laya:positive_outcome");
    }
    add(AppraisalSignalKind::GoalObstruction,
        std::max(intensity(typed, "goal_obstruction"), intensity(typed, "negative_outcome")),
        "laya:obstruction_or_negative_outcome");
    add(AppraisalSignalKind::EnvironmentControl, intensity(typed, "control_restored"),
        "laya:control_restored");
    for (const auto& [name, value] : typed.values) appraisal.typed_scores.emplace_back(name, value);
    appraisal.typed_source = typed.provenance;
    return appraisal;
}

StateUpdate LayaAugmentedDynamicsV1::apply_impulse(
    CharacterState& state, const Appraisal& appraisal, const Personality& personality) const {
    return base_.apply_impulse(state, appraisal, personality);
}

void LayaAugmentedDynamicsV1::update_persistent_intention(
    CharacterState& state, const Observation& observation, int now) const {
    // Legacy callers retain deterministic semantics. Scheduler-native full
    // mode calls the typed RNG-aware hook below instead.
    base_.update_persistent_intention(state, observation, now);
}

std::optional<CommitmentDecisionTrace> LayaAugmentedDynamicsV1::update_persistent_intention_typed(
    CharacterState& state, const Observation& observation, const Personality& personality,
    int now, std::mt19937& rng) const {
    if (!typed_commitment_) {
        base_.update_persistent_intention(state, observation, now);
        return std::nullopt;
    }
    if (new_task_episode(observation)) state.commitment = {};
    const ObservedAction& action = observation.last_self_action;
    // A visible completed task or observed episode replacement is not a
    // subjective choice. Hidden World completion never reaches this path.
    if ((action.has_action && action.accepted && action.task_completed)
        || (state.commitment.status != CommitmentStatus::None
            && has_known_fact(observation, "task." + state.commitment.task_id + ".status", "completed"))) {
        state.commitment = {};
        return CommitmentDecisionTrace{"clear_visible_completion", {}, "observed_task_completion"};
    }
    if (!material_update(observation)) return std::nullopt;
    const std::string task_id = state.commitment.status != CommitmentStatus::None
        ? state.commitment.task_id : (action.has_action && action.accepted ? action.task_id : "");
    if (task_id.empty() || !has_known_fact(observation, "task." + task_id + ".status", "active"))
        return std::nullopt;
    std::vector<std::string> options;
    switch (state.commitment.status) {
    case CommitmentStatus::None: options = {"continue", "abandon"}; break;
    case CommitmentStatus::Active: options = {"continue", "suspend", "abandon"}; break;
    case CommitmentStatus::Suspended: options = {"resume", "suspend", "abandon"}; break;
    }
    const LayaTypedChoice choice = client_.choose_commitment(
        observation, state, personality, options, rng);
    if (choice.selected == "abandon") state.commitment = {};
    else if (choice.selected == "suspend") {
        state.commitment.status = CommitmentStatus::Suspended;
        state.commitment.task_id = task_id;
        state.commitment.reason = "laya typed choice: suspend";
        if (state.commitment.started_at_total_minutes < 0)
            state.commitment.started_at_total_minutes = now;
        ++state.commitment.suspended_decision_points;
    } else {
        const bool was_none = state.commitment.status == CommitmentStatus::None;
        state.commitment.status = CommitmentStatus::Active;
        state.commitment.task_id = task_id;
        state.commitment.reason = "laya typed choice: " + choice.selected;
        if (was_none || state.commitment.started_at_total_minutes < 0)
            state.commitment.started_at_total_minutes = now;
        state.commitment.suspended_decision_points = 0;
    }
    return CommitmentDecisionTrace{choice.selected, choice.probabilities, choice.provenance};
}

DecisionContext LayaAugmentedDynamicsV1::build_policy(
    const Observation& observation, const CharacterState& state,
    const Personality& personality) const {
    return base_.build_policy(observation, state, personality);
}

DynamicsReconsideration LayaAugmentedDynamicsV1::reconsider_running_action(
    const Observation& observation, const CharacterState& before, const CharacterState& after,
    const RunningAction& action, const Personality& personality) const {
    return base_.reconsider_running_action(observation, before, after, action, personality);
}
