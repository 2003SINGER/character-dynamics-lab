#include "decision.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <sstream>

namespace {
CandidateAction candidate(ActionType action, double score, std::string reason) {
    CandidateAction result;
    result.action = action;
    result.score = score;
    result.reason = std::move(reason);
    return result;
}

bool is_available(const Observation& observation, ActionType action) {
    return std::find(observation.available_actions.begin(),
                     observation.available_actions.end(),
                     action) != observation.available_actions.end();
}
} // namespace

DecisionContext decide(const Observation& observation,
                       const CharacterState& state,
                       const Personality& personality) {
    DecisionContext decision;

    const double distraction = state.boredom * 0.75 + personality.procrastination * 0.30;
    const double task_drive = state.task_pressure * (0.75 + personality.self_control * 0.85);
    const double recovery_drive = state.fatigue * 0.95 + personality.rest_preference * 0.20;
    const double hunger_drive = state.hunger * 1.05;
    const double bathroom_drive = state.bathroom_urge * 1.10;

    if (bathroom_drive >= recovery_drive && bathroom_drive >= task_drive && bathroom_drive >= distraction && bathroom_drive >= hunger_drive) {
        decision.dominant_need = "resolve bathroom need";
    } else if (hunger_drive >= recovery_drive && hunger_drive >= task_drive && hunger_drive >= distraction) {
        decision.dominant_need = "eat a meal";
    } else if (recovery_drive >= task_drive && recovery_drive >= distraction) {
        decision.dominant_need = "recover from fatigue";
    } else if (task_drive >= distraction) {
        decision.dominant_need = "reduce task pressure";
    } else {
        decision.dominant_need = "seek stimulation / defer task";
    }

    if (is_available(observation, ActionType::UsePhone)) {
        decision.candidates.push_back(candidate(
            ActionType::UsePhone,
            0.12 + distraction - state.fatigue * 0.20,
            "boredom and procrastination make a quick device reward attractive"));
    }
    if (is_available(observation, ActionType::UseComputer)) {
        decision.candidates.push_back(candidate(
            ActionType::UseComputer,
            0.10 + distraction * 0.78 - state.fatigue * 0.16,
            "screen activity offers engagement but is less immediate than phone use"));
    }
    if (is_available(observation, ActionType::StudyAtDesk)) {
        decision.candidates.push_back(candidate(
            ActionType::StudyAtDesk,
            0.08 + task_drive - state.fatigue * 0.35 - personality.procrastination * 0.22,
            "task pressure and self-control favor task progress"));
    }
    if (is_available(observation, ActionType::RestAtBed)) {
        decision.candidates.push_back(candidate(
            ActionType::RestAtBed,
            0.08 + recovery_drive - state.boredom * 0.10,
            "fatigue and rest preference favor recovery"));
    }
    if (is_available(observation, ActionType::GoToBathroom)) {
        decision.candidates.push_back(candidate(
            ActionType::GoToBathroom,
            0.04 + bathroom_drive - state.fatigue * 0.04,
            "the door makes a bathroom visit available when bodily urgency grows"));
    }
    if (is_available(observation, ActionType::GetMeal)) {
        decision.candidates.push_back(candidate(
            ActionType::GetMeal,
            0.03 + hunger_drive - state.fatigue * 0.03,
            "the door makes getting food available when hunger grows"));
    }
    if (is_available(observation, ActionType::Idle)) {
        decision.candidates.push_back(candidate(
            ActionType::Idle,
            0.05 + state.boredom * 0.12 - state.task_pressure * 0.08,
            "no focused action wins decisively"));
    }

    double normalizer = 0.0;
    for (CandidateAction& item : decision.candidates) {
        item.probability = std::exp(item.score);
        normalizer += item.probability;
    }
    for (CandidateAction& item : decision.candidates) {
        item.probability /= normalizer;
    }
    return decision;
}

ActionType sample_action(const DecisionContext& decision, std::mt19937& rng) {
    std::vector<double> weights;
    weights.reserve(decision.candidates.size());
    for (const CandidateAction& item : decision.candidates) {
        weights.push_back(item.probability);
    }
    std::discrete_distribution<std::size_t> distribution(weights.begin(), weights.end());
    return decision.candidates[distribution(rng)].action;
}

std::string decision_summary(const DecisionContext& decision) {
    std::ostringstream output;
    output << "D{dominant_need=" << decision.dominant_need << "}\n";
    for (const CandidateAction& item : decision.candidates) {
        output << "    pi(" << to_string(item.action) << ")="
               << std::fixed << std::setprecision(3) << item.probability
               << " score=" << item.score << " | " << item.reason << '\n';
    }
    return output.str();
}
