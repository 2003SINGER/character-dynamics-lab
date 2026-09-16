#include "appraisal.h"

#include "personality.h"
#include "state.h"
#include "living_dynamics.h"

#include <sstream>
#include <cstdlib>

namespace {
bool parse_int_fact(const Observation& observation, const std::string& key, int& value) {
    const ObservationFact* fact = find_fact(observation, key);
    if (fact == nullptr || fact->status != KnowledgeStatus::Known) return false;
    char* end = nullptr;
    const long parsed = std::strtol(fact->value.c_str(), &end, 10);
    if (end == fact->value.c_str() || *end != '\0') return false;
    value = static_cast<int>(parsed);
    return true;
}
}

namespace DemoLivingV0 {
Appraisal appraise(const Observation& observation,
                   const CharacterState& old_state,
                   const Personality& personality) {
    Appraisal appraisal;
    const bool coursework_pending = has_known_fact(observation, "task.coursework.status", "active")
        || old_state.commitment.task_id == "coursework";

    if (observation.last_self_action.has_action && !observation.last_self_action.accepted) {
        appraisal.satisfaction_delta = -0.03;
        appraisal.anxiety_delta = 0.03;
        appraisal.tags = {"action_rejected", "goal_obstructed"};
    } else if (observation.last_self_action.has_action) {
        switch (observation.last_self_action.action) {
        case ActionType::UsePhone:
            appraisal.boredom_delta = -0.08 - 0.20 * old_state.boredom;
            appraisal.fatigue_delta = 0.03 + 0.08 * old_state.screen_strain;
            appraisal.task_pressure_delta = coursework_pending ? 0.07 : 0.0;
            appraisal.satisfaction_delta = 0.02 + 0.04 * old_state.boredom;
            appraisal.screen_strain_delta = 0.04 + 0.08 * (1.0 - old_state.screen_strain);
            appraisal.purchase_urge_delta = 0.04 + 0.06 * old_state.boredom;
            appraisal.tags = coursework_pending
                ? std::vector<std::string>{"device_stimulation", "screen_strain", "task_deferred"}
                : std::vector<std::string>{"device_stimulation", "screen_strain"};
            break;
        case ActionType::ShopOnPhone:
            appraisal.satisfaction_delta = 0.10;
            appraisal.task_pressure_delta = coursework_pending ? 0.03 : 0.0;
            appraisal.screen_strain_delta = 0.08;
            appraisal.purchase_urge_delta = -0.55;
            appraisal.tags = {"purchase_completed", "short_term_reward"};
            break;
        case ActionType::UseComputer:
            appraisal.boredom_delta = -0.06 - 0.14 * old_state.boredom;
            appraisal.fatigue_delta = 0.04 + 0.07 * old_state.screen_strain;
            appraisal.task_pressure_delta = coursework_pending ? 0.05 : 0.0;
            appraisal.screen_strain_delta = 0.04 + 0.07 * (1.0 - old_state.screen_strain);
            appraisal.tags = coursework_pending
                ? std::vector<std::string>{"screen_engagement", "task_deferred"}
                : std::vector<std::string>{"screen_engagement"};
            break;
        case ActionType::StudyAtComputer:
        case ActionType::StudyFocused:
            appraisal.boredom_delta = 0.02;
            appraisal.fatigue_delta = 0.11;
            appraisal.task_pressure_delta = -0.04 - 0.12 * old_state.task_pressure;
            appraisal.satisfaction_delta = 0.03 + 0.07 * old_state.task_pressure;
            appraisal.anxiety_delta = -0.02 - 0.04 * old_state.anxiety;
            appraisal.screen_strain_delta =
                observation.last_self_action.action == ActionType::StudyAtComputer ? 0.08 : 0.0;
            appraisal.tags = {"task_effort_session", "mental_effort"};
            break;
        case ActionType::StudyHalfhearted:
            appraisal.boredom_delta = 0.05;
            appraisal.fatigue_delta = 0.08;
            appraisal.task_pressure_delta = -0.02 - 0.06 * old_state.task_pressure;
            appraisal.satisfaction_delta = 0.01 + 0.03 * old_state.task_pressure;
            appraisal.anxiety_delta = -0.01 - 0.02 * old_state.anxiety;
            appraisal.tags = {"task_effort_session", "distracted_effort"};
            break;
        case ActionType::RestAtBed:
            appraisal.boredom_delta = 0.04;
            appraisal.fatigue_delta = -0.06 * LivingDynamics::rest_recovery_efficiency(old_state);
            appraisal.screen_strain_delta = -0.14;
            appraisal.task_pressure_delta = coursework_pending ? 0.02 * old_state.task_pressure : 0.0;
            appraisal.satisfaction_delta = 0.05;
            appraisal.tags = coursework_pending
                ? std::vector<std::string>{"recovery", "task_still_pending"}
                : std::vector<std::string>{"recovery"};
            break;
        case ActionType::SleepAtBed:
            appraisal.boredom_delta = -0.08;
            appraisal.fatigue_delta = -0.10 * LivingDynamics::rest_recovery_efficiency(old_state);
            appraisal.screen_strain_delta = -0.30;
            appraisal.task_pressure_delta = coursework_pending ? 0.03 * old_state.task_pressure : 0.0;
            appraisal.satisfaction_delta = 0.08;
            appraisal.tags = coursework_pending
                ? std::vector<std::string>{"sleep_recovery", "long_unobserved_interval", "task_still_pending"}
                : std::vector<std::string>{"sleep_recovery", "long_unobserved_interval"};
            break;
        case ActionType::GoToBathroom:
            appraisal.satisfaction_delta = 0.07;
            appraisal.bathroom_urge_delta = -LivingDynamics::bathroom_relief(old_state);
            appraisal.tags = {"bodily_need_resolved", "brief_room_exit"};
            break;
        case ActionType::GetMeal:
            appraisal.boredom_delta = -0.04;
            appraisal.satisfaction_delta = LivingDynamics::meal_satisfaction_gain(old_state, personality);
            appraisal.hunger_delta = -LivingDynamics::meal_hunger_relief(old_state);
            appraisal.tags = {"hunger_resolved", "brief_room_exit"};
            break;
        case ActionType::TurnLightOn:
            appraisal.satisfaction_delta = 0.02;
            appraisal.tags = {"room_prepared_for_activity"};
            break;
        case ActionType::TurnLightOff:
            appraisal.satisfaction_delta = 0.02;
            appraisal.tags = {"room_prepared_for_rest"};
            break;
        case ActionType::TurnOffAlarm:
            appraisal.satisfaction_delta = 0.03;
            appraisal.anxiety_delta = -0.02;
            appraisal.tags = {"alarm_silenced", "interruption_resolved"};
            break;
        case ActionType::OpenCurtain:
            appraisal.satisfaction_delta = 0.01;
            appraisal.tags = {"outside_visibility_restored"};
            break;
        case ActionType::CloseCurtain:
            appraisal.satisfaction_delta = 0.01;
            appraisal.tags = {"room_stimulation_reduced"};
            break;
        case ActionType::Idle:
            appraisal.boredom_delta = 0.12;
            appraisal.task_pressure_delta = 0.0;
            appraisal.satisfaction_delta = 0.0;
            appraisal.tags = coursework_pending
                ? std::vector<std::string>{"under_stimulation", "task_unattended"}
                : std::vector<std::string>{"under_stimulation"};
            break;
        case ActionType::Count:
            break;
        }
    }

    const auto apply_observation_update = [&](const ObservationFact& update) {
        if (update.key == "task.coursework.status" && update.value == "completed"
            && update.status == KnowledgeStatus::Known) {
            appraisal.semantic_signals.push_back({
                AppraisalSignalKind::GoalCompletion, 1.0, 1.0, 1.0, 1.0,
                "task.coursework.status=completed"
            });
            appraisal.tags.push_back("task_completed");
        } else if (update.key == "task.coursework.deadline_at_total_minutes"
                   && update.source != "initial_calendar" && update.status == KnowledgeStatus::Known
                   && coursework_pending) {
            int deadline = 0, now = 0;
            if (parse_int_fact(observation, update.key, deadline)
                && parse_int_fact(observation, "clock.total_minutes", now)) {
                const int remaining = deadline - now;
                const double urgency = remaining <= 0 ? 1.0
                    : remaining >= 720 ? 0.0 : 1.0 - static_cast<double>(remaining) / 720.0;
                appraisal.deadline_pressure_contribution = 0.20 * urgency;
                appraisal.task_pressure_delta += appraisal.deadline_pressure_contribution;
                appraisal.anxiety_delta += 0.08 * urgency * personality.task_anxiety_sensitivity;
                appraisal.tags.push_back("deadline_urgency");
            }
        } else if (update.key == FactKey::TaskDeadlinePassed && update.value == "1"
                   && update.status == KnowledgeStatus::Known && coursework_pending) {
            appraisal.task_pressure_delta += 0.20;
            appraisal.anxiety_delta += 0.08 * personality.task_anxiety_sensitivity;
            appraisal.tags.push_back("deadline_passed");
        } else if (update.key == "room.alarm" && update.value == "ringing"
                   && update.status == KnowledgeStatus::Known) {
            appraisal.boredom_delta += 0.03;
            appraisal.anxiety_delta += 0.02 + 0.04 * personality.task_anxiety_sensitivity;
            appraisal.tags.push_back("alarm_interrupts_room");
        } else if (update.key == "room.temperature_celsius" && update.status == KnowledgeStatus::Known) {
            double temperature = 0.0;
            if (known_double(observation, update.key, temperature) && temperature <= 17.0) {
                appraisal.fatigue_delta += 0.04;
                appraisal.satisfaction_delta -= 0.06;
                appraisal.tags.push_back("cold_interrupts_sleep");
            }
        } else if (update.key == "message.unread_count" && update.value != "0"
                   && update.status == KnowledgeStatus::Known && coursework_pending) {
            appraisal.task_pressure_delta += 0.08;
            appraisal.anxiety_delta += 0.05;
            appraisal.tags.push_back("social_task_reminder");
        } else if (((update.key == "calendar.task_due" && update.value == "today")
                    || (update.key == FactKey::TaskReminder && update.value == "1"))
                   && update.status == KnowledgeStatus::Known && coursework_pending) {
            appraisal.task_pressure_delta += 0.14;
            appraisal.anxiety_delta += 0.06 + 0.08 * personality.task_anxiety_sensitivity;
            appraisal.tags.push_back("deadline_salience");
        } else if (update.key == "outside.weather" && update.value == "rain"
                   && update.status == KnowledgeStatus::Known && old_state.boredom > 0.40) {
            appraisal.boredom_delta += 0.03;
            appraisal.tags.push_back("rain_observed_through_window");
        }
    };
    for (const ObservationFact& update : observation.updates_this_refresh) {
        apply_observation_update(update);
    }
    for (const ObservationFact& update : observation.pending_appraisal_updates) {
        apply_observation_update(update);
    }
    if (has_known_fact(observation, "room.light", "off")) {
        appraisal.tags.push_back("room_is_dark");
    }
    return appraisal;
}

std::string appraisal_summary(const Appraisal& appraisal) {
    std::ostringstream output;
    output << "X{signals=[";
    for (std::size_t i = 0; i < appraisal.semantic_signals.size(); ++i) {
        const auto& s = appraisal.semantic_signals[i];
        output << appraisal_signal_name(s.kind)
               << "{intensity=" << s.intensity
               << ", relevance=" << s.goal_relevance
               << ", congruence=" << s.goal_congruence
               << ", controllability=" << s.controllability
               << ", source=" << s.source << '}';
        if (i + 1 < appraisal.semantic_signals.size()) output << ", ";
    }
    output << "], tags=[";
    for (std::size_t index = 0; index < appraisal.tags.size(); ++index) {
        output << appraisal.tags[index];
        if (index + 1 < appraisal.tags.size()) output << ", ";
    }
    output << "]}";
    return output.str();
}

const char* appraisal_signal_name(AppraisalSignalKind kind) {
    switch (kind) {
    case AppraisalSignalKind::GoalProgress: return "goal_progress";
    case AppraisalSignalKind::GoalCompletion: return "goal_completion";
    case AppraisalSignalKind::GoalObstruction: return "goal_obstruction";
    case AppraisalSignalKind::Stimulation: return "stimulation";
    case AppraisalSignalKind::Recovery: return "recovery";
    case AppraisalSignalKind::ShortTermReward: return "short_term_reward";
    case AppraisalSignalKind::EnvironmentControl: return "environment_control";
    }
    return "unknown";
}

}
