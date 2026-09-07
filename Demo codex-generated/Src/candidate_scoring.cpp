#include "candidate_scoring.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

std::vector<ExternalCandidateScore> score_replay_candidates(
    const std::vector<ExternalCandidate>& candidates,
    const ReplayPolicyConfig& config) {
    if (candidates.empty()) throw std::invalid_argument("external candidate set is empty");
    const double temperature = std::max(0.05, config.temperature);
    std::vector<ExternalCandidateScore> out;
    out.reserve(candidates.size());
    double max_logit = -std::numeric_limits<double>::infinity();
    for (const auto& candidate : candidates) {
        const auto& f = candidate.semantics;
        const double activation = candidate.bias
            + f.goal_progress * config.task_drive
            + f.stimulation * config.distraction_drive
            + f.recovery * config.recovery_drive
            + f.hunger_relief * config.hunger_drive
            + f.bathroom_relief * config.bathroom_drive
            + f.short_term_reward * config.reward_drive
            + f.environment_control * config.environment_drive
            + f.context_relevance * config.context_drive;
        out.push_back({candidate.id, activation, 0.0});
        max_logit = std::max(max_logit, activation / temperature);
    }
    double normalizer = 0.0;
    for (auto& item : out) {
        item.probability = std::exp(item.activation / temperature - max_logit);
        normalizer += item.probability;
    }
    if (!std::isfinite(normalizer) || normalizer <= 0.0)
        throw std::logic_error("replay scorer produced invalid normalizer");
    for (auto& item : out) item.probability /= normalizer;
    return out;
}

std::vector<ExternalCandidateScore> score_external_candidates(
    const std::vector<ExternalCandidate>& candidates,
    const CharacterState& state,
    const Personality& personality) {
    if (candidates.empty()) {
        throw std::invalid_argument("external candidate set is empty");
    }

    const double task_drive = state.task_pressure
                            * (0.70 + 0.80 * personality.self_control)
                            + 0.20 * state.anxiety;
    const double distraction = 0.65 * state.boredom
                             + 0.25 * personality.procrastination
                             + 0.20 * personality.stimulation_seeking;
    const double recovery_drive = 0.75 * state.fatigue
                                + 0.50 * state.screen_strain
                                + 0.18 * personality.rest_preference;
    const double hunger_drive = state.hunger * (0.85 + 0.25 * personality.need_response);
    const double bathroom_drive =
        state.bathroom_urge * (0.90 + 0.20 * personality.need_response);
    const double temperature = std::max(0.05, 0.45 + personality.action_noise);

    std::vector<ExternalCandidateScore> out;
    out.reserve(candidates.size());
    double max_logit = -std::numeric_limits<double>::infinity();

    for (const auto& candidate : candidates) {
        const auto& f = candidate.semantics;
        const double activation =
            candidate.bias
            + f.goal_progress * task_drive
            + f.stimulation * distraction
            + f.recovery * recovery_drive
            + f.hunger_relief * hunger_drive
            + f.bathroom_relief * bathroom_drive
            + f.short_term_reward * (0.35 + 0.65 * state.purchase_urge)
            + f.environment_control * (0.15 * task_drive + 0.10 * recovery_drive)
            + f.context_relevance * 0.25;
        out.push_back({candidate.id, activation, 0.0});
        max_logit = std::max(max_logit, activation / temperature);
    }

    double normalizer = 0.0;
    for (auto& item : out) {
        item.probability = std::exp(item.activation / temperature - max_logit);
        normalizer += item.probability;
    }
    if (!std::isfinite(normalizer) || normalizer <= 0.0) {
        throw std::logic_error("external candidate scorer produced invalid normalizer");
    }
    for (auto& item : out) item.probability /= normalizer;
    return out;
}
