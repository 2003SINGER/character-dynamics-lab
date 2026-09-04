#include "decision.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {
CandidateAction candidate(ActionType action, double activation, double threshold, std::string reason) {
    CandidateAction result;
    result.action = action;
    result.activation = activation;
    result.threshold = threshold;
    result.eligible = activation >= threshold || action == ActionType::Idle;
    result.reason = std::move(reason);
    return result;
}
} // namespace

DecisionContext decide(const Observation& observation,
                       const CharacterState& state,
                       const Personality& personality) {
    DecisionContext decision;
    decision.known_actions = observation.known_actions;
    if (state.intention.active && state.intention.remaining_decision_points > 0) {
        decision.intention_status = "active: " + to_string(state.intention.action)
                                  + " for " + std::to_string(state.intention.remaining_decision_points)
                                  + " more decision point(s)";
    } else {
        decision.intention_status = "none";
    }
    const double distraction = state.boredom * 0.65 + personality.procrastination * 0.25
                             + personality.stimulation_seeking * 0.20;
    const double task_drive = state.task_pressure * (0.70 + personality.self_control * 0.80)
                            + state.anxiety * 0.20;
    const double recovery_drive = state.fatigue * 0.75 + state.screen_strain * 0.50
                                + personality.rest_preference * 0.18;
    const double hunger_drive = state.hunger * (0.85 + personality.need_response * 0.25);
    const double bathroom_drive = state.bathroom_urge * (0.90 + personality.need_response * 0.20);

    const double dominant = std::max({distraction, task_drive, recovery_drive, hunger_drive, bathroom_drive});
    if (dominant == bathroom_drive) {
        decision.dominant_need = "resolve bathroom need";
        decision.intention_hint = "briefly leave through the door";
    } else if (dominant == hunger_drive) {
        decision.dominant_need = "eat a meal";
        decision.intention_hint = "briefly leave through the door";
    } else if (dominant == recovery_drive) {
        decision.dominant_need = "recover from fatigue / strain";
        decision.intention_hint = "prepare room for rest or use bed";
    } else if (dominant == task_drive) {
        decision.dominant_need = "reduce task pressure";
        decision.intention_hint = "prepare light if needed, then study";
    } else {
        decision.dominant_need = "seek stimulation / defer task";
        decision.intention_hint = "use an available device";
    }

    // A^W -> A^O -> pi(A): W declares what is legal; persistent O exposes
    // only the actions afforded by things the character currently knows.
    for (ActionType action : observation.known_actions) {
        const double commitment_bonus = state.intention.active
                                     && state.intention.remaining_decision_points > 0
                                     && state.intention.action == action ? 0.16 : 0.0;
        switch (action) {
        case ActionType::UsePhone:
            decision.candidates.push_back(candidate(action, 0.06 + distraction - state.screen_strain * 0.30 - state.fatigue * 0.12 + commitment_bonus, 0.12, "phone offers immediate stimulation but raises strain"));
            break;
        case ActionType::ShopOnPhone:
            decision.candidates.push_back(candidate(action, 0.03 + state.purchase_urge * 0.95 + distraction * 0.10 + commitment_bonus, 0.18, "phone supports online shopping when purchase urge activates"));
            break;
        case ActionType::UseComputer:
            decision.candidates.push_back(candidate(action, 0.04 + distraction * 0.72 - state.screen_strain * 0.28 + commitment_bonus, 0.13, "computer offers longer-form stimulation"));
            break;
        case ActionType::StudyAtComputer:
            decision.candidates.push_back(candidate(action, 0.04 + task_drive - state.fatigue * 0.25 - personality.procrastination * 0.16 + commitment_bonus, 0.18, "computer can be used for task progress"));
            break;
        case ActionType::StudyAtDesk:
            decision.candidates.push_back(candidate(action, 0.07 + task_drive - state.fatigue * 0.22 - personality.procrastination * 0.14 + commitment_bonus, 0.18, "lit desk and materials support studying"));
            break;
        case ActionType::RestAtBed:
            decision.candidates.push_back(candidate(action, 0.05 + recovery_drive - state.anxiety * 0.10 + commitment_bonus, 0.16, "bed supports recovery from fatigue and screen strain"));
            break;
        case ActionType::SleepAtBed:
            decision.candidates.push_back(candidate(action, -0.10 + recovery_drive * 1.15 + state.fatigue * 0.25 + commitment_bonus, 0.58, "bed supports a long sleep interval when fatigue becomes high"));
            break;
        case ActionType::GoToBathroom:
            decision.candidates.push_back(candidate(action, 0.03 + bathroom_drive + commitment_bonus, 0.16, "door supports resolving a bodily need"));
            break;
        case ActionType::GetMeal:
            decision.candidates.push_back(candidate(action, 0.03 + hunger_drive + commitment_bonus, 0.16, "door supports getting a meal"));
            break;
        case ActionType::TurnLightOn:
            decision.candidates.push_back(candidate(action, 0.02 + task_drive * 0.55 + commitment_bonus, 0.20, "light enables currently blocked study actions"));
            break;
        case ActionType::TurnLightOff:
            decision.candidates.push_back(candidate(action, 0.02 + recovery_drive * 0.45 + commitment_bonus, 0.20, "darkening the room prepares a rest-oriented context"));
            break;
        case ActionType::TurnOffAlarm:
            decision.candidates.push_back(candidate(action, 0.45 + state.anxiety * 0.25 + commitment_bonus, 0.12, "ringing alarm is immediately available to silence"));
            break;
        case ActionType::OpenCurtain:
            decision.candidates.push_back(candidate(action, 0.04 + state.boredom * 0.22 + commitment_bonus, 0.18, "opening curtains restores direct access to outside conditions"));
            break;
        case ActionType::CloseCurtain:
            decision.candidates.push_back(candidate(action, 0.03 + recovery_drive * 0.22 + commitment_bonus, 0.19, "closing curtains can reduce environmental stimulation before rest"));
            break;
        case ActionType::Idle:
            decision.candidates.push_back(candidate(action, 0.05 + state.boredom * 0.10 - state.task_pressure * 0.06 + commitment_bonus, 0.0, "no focused action wins decisively"));
            break;
        case ActionType::Count:
            break;
        }
    }

    const double temperature = std::max(0.05, 0.45 + personality.action_noise);
    double max_logit = -std::numeric_limits<double>::infinity();
    for (const CandidateAction& item : decision.candidates) {
        if (item.eligible && std::isfinite(item.activation)) {
            max_logit = std::max(max_logit, item.activation / temperature);
        }
    }
    double normalizer = 0.0;
    for (CandidateAction& item : decision.candidates) {
        if (item.eligible && std::isfinite(item.activation)) {
            item.probability = std::exp(item.activation / temperature - max_logit);
            normalizer += item.probability;
        } else {
            item.eligible = false;
            item.probability = 0.0;
        }
    }
    if (!std::isfinite(normalizer) || normalizer <= 0.0) {
        throw std::logic_error("Decision has no finite eligible action probability");
    }
    for (CandidateAction& item : decision.candidates) {
        item.probability = item.eligible ? item.probability / normalizer : 0.0;
    }
    return decision;
}

ActionType sample_action(const DecisionContext& decision, std::mt19937& rng) {
    std::vector<double> weights;
    std::vector<ActionType> actions;
    for (const CandidateAction& item : decision.candidates) {
        if (item.eligible) {
            weights.push_back(item.probability);
            actions.push_back(item.action);
        }
    }
    if (actions.empty()) {
        throw std::logic_error("Cannot sample an empty action distribution");
    }
    std::discrete_distribution<std::size_t> distribution(weights.begin(), weights.end());
    return actions[distribution(rng)];
}

void update_intention(CharacterState& state,
                      ActionType chosen_action) {
    const bool study_choice = chosen_action == ActionType::StudyAtDesk
                           || chosen_action == ActionType::StudyAtComputer;
    if (study_choice) {
        state.intention = {true, chosen_action, "continue reducing task pressure", 2};
        return;
    }
    if (!state.intention.active) {
        return;
    }
    --state.intention.remaining_decision_points;
    if (state.intention.remaining_decision_points <= 0 || chosen_action == ActionType::RestAtBed
        || chosen_action == ActionType::SleepAtBed
        || chosen_action == ActionType::GetMeal || chosen_action == ActionType::GoToBathroom) {
        state.intention = {};
    }
}

std::string decision_summary(const DecisionContext& decision) {
    std::ostringstream output;
    output << "D{dominant_need=" << decision.dominant_need
           << ", intention_hint=" << decision.intention_hint
           << ", persistent_intention=" << decision.intention_status << "}\n"
           << "    A^O=";
    for (ActionType action : decision.known_actions) output << to_string(action) << ' ';
    output << '\n';
    for (const CandidateAction& item : decision.candidates) {
        output << "    " << (item.eligible ? "eligible " : "suppressed")
               << " | pi(" << to_string(item.action) << ")="
               << std::fixed << std::setprecision(3) << item.probability
               << " activation=" << item.activation
               << " threshold=" << item.threshold
               << " | " << item.reason << '\n';
    }
    return output.str();
}
