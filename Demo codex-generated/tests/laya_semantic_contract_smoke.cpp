#include "laya_augmented_dynamics_v1.h"

#include <cmath>
#include <random>

namespace {
ObservedAction feedback(ActionType action, std::string task_id = {}) {
    ObservedAction result;
    result.has_action = true;
    result.action = action;
    result.accepted = true;
    result.task_id = std::move(task_id);
    return result;
}
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const int port = std::stoi(argv[1]);
    LayaAugmentedDynamicsV1 typed(port, true, true);
    DemoLivingDynamicsV1 base;
    CharacterState state;
    Personality personality;
    std::mt19937 rng(123);
    Observation observation;
    observation.facts.push_back({"clock.total_minutes", "190", KnowledgeStatus::Known,
                                 "runtime_clock", "test"});
    observation.facts.push_back({"task.coursework.status", "active", KnowledgeStatus::Known,
                                 "observed_task", "test"});
    ActorHistory actor_history;
    ActorEpisode prior_episode;
    prior_episode.action = ActionType::StudyFocused;
    prior_episode.target = "desk";
    prior_episode.start_total_minutes = 100;
    prior_episode.end_total_minutes = 130;
    prior_episode.actual_minutes = 30;
    prior_episode.planned_minutes = 45;
    prior_episode.task_id = "coursework";
    actor_history.episodes.push_back(prior_episode);
    actor_history.events.push_back({180, "task.coursework.status", "active"});
    observation.last_self_action = feedback(ActionType::StudyFocused, "coursework");
    auto decision = typed.update_persistent_intention_typed_with_history(state, observation, personality, 100, rng, actor_history);
    if (!decision || decision->choice != "continue"
        || state.commitment.status != CommitmentStatus::Active
        || state.commitment.task_id != "coursework"
        || state.commitment.started_at_total_minutes != 100) return 3;

    observation.last_self_action = feedback(ActionType::RestAtBed);
    decision = typed.update_persistent_intention_typed_with_history(state, observation, personality, 130, rng, actor_history);
    if (!decision || decision->choice != "suspend"
        || state.commitment.status != CommitmentStatus::Suspended
        || state.commitment.started_at_total_minutes != 100) return 4;

    observation.last_self_action = feedback(ActionType::StudyFocused, "coursework");
    decision = typed.update_persistent_intention_typed_with_history(state, observation, personality, 160, rng, actor_history);
    if (!decision || decision->choice != "resume"
        || state.commitment.status != CommitmentStatus::Active
        || state.commitment.started_at_total_minutes != 100) return 5;

    // Hidden W completion is not available to this O-side hook.
    observation.last_self_action = {};
    observation.updates_this_refresh.clear();
    decision = typed.update_persistent_intention_typed_with_history(state, observation, personality, 180, rng, actor_history);
    if (decision || state.commitment.status != CommitmentStatus::Active) return 6;

    observation.facts[1].value = "completed";
    observation.updates_this_refresh.push_back(observation.facts[1]);
    decision = typed.update_persistent_intention_typed_with_history(state, observation, personality, 190, rng, actor_history);
    if (!decision || decision->choice != "clear_visible_completion"
        || state.commitment.status != CommitmentStatus::None) return 7;

    observation.facts[1].value = "active";
    observation.updates_this_refresh.clear();
    observation.last_self_action = feedback(ActionType::GetMeal);
    state.hunger = 0.70;
    const Appraisal rule_appraisal = base.appraise(observation, state, personality);
    const Appraisal typed_appraisal = typed.appraise_with_history(observation, state, personality, actor_history);
    if (typed_appraisal.typed_scores.size() != 7 || typed_appraisal.typed_source.empty()
        || !typed_appraisal.has_task_pressure_target
        || std::abs(typed_appraisal.hunger_delta - rule_appraisal.hunger_delta) > 1e-12
        || std::abs(typed_appraisal.fatigue_delta - rule_appraisal.fatigue_delta) > 1e-12)
        return 8;
    CharacterState rule_state = state;
    CharacterState typed_state = state;
    base.apply_impulse(rule_state, rule_appraisal, personality);
    typed.apply_impulse(typed_state, typed_appraisal, personality);
    if (std::abs(rule_state.hunger - typed_state.hunger) > 1e-12
        || std::abs(rule_state.bathroom_urge - typed_state.bathroom_urge) > 1e-12
        || std::abs(rule_state.fatigue - typed_state.fatigue) > 1e-12)
        return 9;
    return 0;
}
