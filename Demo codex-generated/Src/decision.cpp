#include "decision.h"
#include "living_dynamics.h"

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

bool commitment_can_bias_study(const Observation& observation, const CharacterState& state) {
    if (state.commitment.status == CommitmentStatus::None) return false;
    if (!has_known_fact(observation, "task." + state.commitment.task_id + ".status", "active")) return false;
    const bool study_is_known = observation_knows_action(observation, ActionType::StudyFocused)
        || observation_knows_action(observation, ActionType::StudyHalfhearted)
        || observation_knows_action(observation, ActionType::StudyAtComputer);
    if (!study_is_known) return false;
    if (state.commitment.status == CommitmentStatus::Active) return true;

    // A suspended commitment may shape a return to work only after immediate
    // bodily/recovery demands have eased. This is a v0 reconsideration gate,
    // not a planner or an automatic multi-step script.
    return state.fatigue < 0.65 && state.hunger < 0.60 && state.bathroom_urge < 0.60;
}
} // namespace

DecisionContext decide(const Observation& observation,
                       const CharacterState& state,
                       const Personality& personality,
                       const ParameterConfig& config) {
    DecisionContext decision;
    decision.known_actions = observation.known_actions;
    switch (state.commitment.status) {
    case CommitmentStatus::None:
        decision.intention_status = "none";
        break;
    case CommitmentStatus::Active:
        decision.intention_status = "active task: " + state.commitment.task_id;
        break;
    case CommitmentStatus::Suspended:
        decision.intention_status = "suspended task: " + state.commitment.task_id
                                  + " for " + std::to_string(state.commitment.suspended_decision_points)
                                  + " decision point(s); reconsideration "
                                  + (commitment_can_bias_study(observation, state) ? "permits return" : "defers return");
        break;
    }
    const double distraction = config.distraction_weight * (state.boredom * 0.65 + personality.procrastination * 0.25
                             + personality.stimulation_seeking * 0.20);
    const double overload = LivingDynamics::overload(state, personality);
    const double task_drive = config.task_drive_coefficient * (state.task_pressure * (0.70 + personality.self_control * 0.80)
                            + state.anxiety * 0.20) * (1.0 - 0.45 * overload);
    const double recovery_drive = config.recovery_drive_coefficient * (state.fatigue * 0.75 + state.screen_strain * 0.50
                                + personality.rest_preference * 0.18);
    const double hunger_drive = LivingDynamics::perceived_hunger(state, personality) * (0.85 + personality.need_response * 0.25);
    const double bathroom_drive = LivingDynamics::perceived_bathroom(state, personality) * (0.90 + personality.need_response * 0.20);
    // Above a moderate bodily-need level, leisure and task candidates lose
    // probability smoothly rather than relying on a hard scripted interrupt.
    const double urgent_bodily_need = std::max(0.0, std::max(hunger_drive, bathroom_drive) - 0.65);

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
        const bool advances_committed_task = (action == ActionType::StudyFocused
            || action == ActionType::StudyHalfhearted
            || action == ActionType::StudyAtComputer)
            && commitment_can_bias_study(observation, state);
        const double commitment_bonus = advances_committed_task ? 0.16 * config.commitment_bonus : 0.0;
        switch (action) {
        case ActionType::UsePhone:
            decision.candidates.push_back(candidate(action, 0.06 + distraction - state.screen_strain * 0.30 - state.fatigue * 0.12
                - 0.34 * (hunger_drive + bathroom_drive) - 0.90 * urgent_bodily_need + commitment_bonus, 0.12, "phone offers immediate stimulation but yields to urgent bodily needs"));
            break;
        case ActionType::ShopOnPhone:
            decision.candidates.push_back(candidate(action, 0.03 + state.purchase_urge * 0.95 + distraction * 0.10 + commitment_bonus, 0.18, "phone supports online shopping when purchase urge activates"));
            break;
        case ActionType::UseComputer:
            decision.candidates.push_back(candidate(action, 0.04 + distraction * 0.72 - state.screen_strain * 0.28 - 0.80 * urgent_bodily_need + commitment_bonus, 0.13, "computer offers longer-form stimulation"));
            break;
        case ActionType::StudyAtComputer:
            decision.candidates.push_back(candidate(action, 0.04 + task_drive - state.fatigue * 0.25 * config.study_fatigue_penalty - personality.procrastination * 0.16 + commitment_bonus, 0.18, "computer can be used for task progress"));
            break;
        case ActionType::StudyFocused:
            decision.candidates.push_back(candidate(action,
                0.05 + task_drive + state.satisfaction * 0.10
                - state.fatigue * 0.25 * config.study_fatigue_penalty
                - 0.38 * (hunger_drive + bathroom_drive) - 0.90 * urgent_bodily_need - personality.procrastination * 0.18
                + commitment_bonus,
                0.18,
                "lit desk supports sustained focused study"));
            break;
        case ActionType::StudyHalfhearted:
            decision.candidates.push_back(candidate(action,
                0.06 + task_drive * 0.55 + state.boredom * 0.36
                - 0.26 * (hunger_drive + bathroom_drive) - 0.75 * urgent_bodily_need
                + 0.03 * static_cast<double>(state.commitment.suspended_decision_points)
                - state.fatigue * 0.12 * config.study_fatigue_penalty - personality.self_control * 0.18
                + commitment_bonus,
                0.16,
                "lit desk permits partial study when task pressure coexists with distraction"));
            break;
        case ActionType::RestAtBed:
            decision.candidates.push_back(candidate(action, 0.05 + recovery_drive - state.anxiety * 0.10 + overload * 0.10 + commitment_bonus, 0.16, "bed supports recovery from fatigue and screen strain"));
            break;
        case ActionType::SleepAtBed:
            decision.candidates.push_back(candidate(action, -0.10 + recovery_drive * 1.15 + LivingDynamics::sleep_readiness(observation,state,personality) + commitment_bonus, 0.58, "bed supports a long sleep interval when fatigue becomes high"));
            break;
        case ActionType::GoToBathroom:
            decision.candidates.push_back(candidate(action, 0.03 + 1.55 * bathroom_drive + commitment_bonus, 0.16, "door supports resolving a bodily need"));
            break;
        case ActionType::GetMeal:
            decision.candidates.push_back(candidate(action, 0.03 + 1.45 * hunger_drive + commitment_bonus, 0.16, "door supports getting a meal"));
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

    // A genuinely urgent bodily need is a contextual constraint, not a
    // scripted action: at the extreme end, ordinary leisure/work options are
    // no longer admissible, while eating and bathroom relief remain competing
    // choices. This keeps free-runs from repeatedly ignoring a saturated need.
    if (LivingDynamics::perceived_bathroom(state, personality) >= 0.92
        || LivingDynamics::perceived_hunger(state, personality) >= 0.92) {
        const bool bathroom_urgent = LivingDynamics::perceived_bathroom(state, personality) >= 0.92;
        const bool hunger_urgent = LivingDynamics::perceived_hunger(state, personality) >= 0.92;
        for (CandidateAction& item : decision.candidates) {
            const bool bodily = item.action == ActionType::GoToBathroom || item.action == ActionType::GetMeal;
            if (bodily) {
                if ((item.action == ActionType::GoToBathroom && bathroom_urgent)
                    || (item.action == ActionType::GetMeal && hunger_urgent)) continue;
                item.eligible = false;
            } else {
                item.eligible = false;
            }
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
    for (CandidateAction& item : decision.candidates) {
        for (const ActionTargetBinding& binding : observation.action_target_bindings) {
            if (binding.action == item.action) {
                item.target_object_id = binding.target_object_id;
                break;
            }
        }
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

void update_commitment(CharacterState& state,
                       const Observation& observation,
                       int settled_at_total_minutes) {
    const ObservedAction& action = observation.last_self_action;
    if (!action.has_action || !action.accepted) return;

    if (action.task_completed) {
        state.commitment = {};
        return;
    }
    if (!action.task_id.empty()) {
        state.commitment = {CommitmentStatus::Active, action.task_id,
                            "continue advancing unfinished task", settled_at_total_minutes, 0};
        return;
    }

    const bool bodily_or_recovery_action = action.action == ActionType::RestAtBed
        || action.action == ActionType::SleepAtBed
        || action.action == ActionType::GetMeal
        || action.action == ActionType::GoToBathroom;
    if (state.commitment.status == CommitmentStatus::Active && bodily_or_recovery_action) {
        state.commitment.status = CommitmentStatus::Suspended;
        state.commitment.reason = "temporarily yield to bodily or recovery need";
        state.commitment.suspended_decision_points = 0;
        return;
    }
    if (state.commitment.status == CommitmentStatus::Suspended) {
        ++state.commitment.suspended_decision_points;
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
