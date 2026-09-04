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
} // namespace

DecisionContext decide(const Observation& observation,
                       const CharacterState& state,
                       const Personality& personality) {
    DecisionContext decision;

    const double distraction = state.boredom * 0.75 + personality.procrastination * 0.30;
    const double task_drive = state.task_pressure * (0.75 + personality.self_control * 0.85);
    const double recovery_drive = state.fatigue * 0.95 + personality.rest_preference * 0.20;

    if (recovery_drive >= task_drive && recovery_drive >= distraction) {
        decision.dominant_need = "recover from fatigue";
    } else if (task_drive >= distraction) {
        decision.dominant_need = "reduce task pressure";
    } else {
        decision.dominant_need = "seek stimulation / defer task";
    }

    if (observation.phone_known_available) {
        decision.candidates.push_back(candidate(
            ActionType::UsePhone,
            0.12 + distraction - state.fatigue * 0.20,
            "boredom and procrastination make a quick device reward attractive"));
    }
    if (observation.computer_known_available) {
        decision.candidates.push_back(candidate(
            ActionType::UseComputer,
            0.10 + distraction * 0.78 - state.fatigue * 0.16,
            "screen activity offers engagement but is less immediate than phone use"));
    }
    if (observation.desk_known_available) {
        decision.candidates.push_back(candidate(
            ActionType::StudyAtDesk,
            0.08 + task_drive - state.fatigue * 0.35 - personality.procrastination * 0.22,
            "task pressure and self-control favor task progress"));
    }
    if (observation.bed_known_available) {
        decision.candidates.push_back(candidate(
            ActionType::RestAtBed,
            0.08 + recovery_drive - state.boredom * 0.10,
            "fatigue and rest preference favor recovery"));
    }
    decision.candidates.push_back(candidate(
        ActionType::Idle,
        0.05 + state.boredom * 0.12 - state.task_pressure * 0.08,
        "no focused action wins decisively"));

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
