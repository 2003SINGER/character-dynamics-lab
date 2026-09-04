#include "appraisal.h"

#include "personality.h"
#include "state.h"

#include <sstream>

Appraisal appraise(const Observation& observation,
                   const CharacterState& old_state,
                   const Personality& personality) {
    Appraisal appraisal;

    // This is intentionally a small replaceable X function. It reads only O,
    // Delta-O, old S, and P: raw WorldOutcome must first pass through O.
    switch (observation.last_self_action.action) {
    case ActionType::UsePhone:
        appraisal.boredom_delta = -0.22;
        appraisal.fatigue_delta = 0.08;
        appraisal.task_pressure_delta = 0.07;
        appraisal.satisfaction_delta = 0.04;
        appraisal.screen_strain_delta = 0.12;
        appraisal.purchase_urge_delta = 0.10;
        appraisal.tags = {"device_stimulation", "screen_strain", "task_deferred"};
        break;
    case ActionType::ShopOnPhone:
        appraisal.satisfaction_delta = 0.10;
        appraisal.task_pressure_delta = 0.03;
        appraisal.screen_strain_delta = 0.08;
        appraisal.purchase_urge_delta = -0.55;
        appraisal.tags = {"purchase_completed", "short_term_reward"};
        break;
    case ActionType::UseComputer:
        appraisal.boredom_delta = -0.16;
        appraisal.fatigue_delta = 0.10;
        appraisal.task_pressure_delta = 0.05;
        appraisal.screen_strain_delta = 0.11;
        appraisal.tags = {"screen_engagement", "task_deferred"};
        break;
    case ActionType::StudyAtComputer:
    case ActionType::StudyAtDesk:
        appraisal.boredom_delta = 0.02;
        appraisal.fatigue_delta = 0.11;
        appraisal.task_pressure_delta = -0.25;
        appraisal.satisfaction_delta = 0.13;
        appraisal.anxiety_delta = -0.08;
        appraisal.screen_strain_delta = observation.last_self_action.action == ActionType::StudyAtComputer ? 0.08 : 0.0;
        appraisal.tags = {"task_progress", "mental_effort"};
        break;
    case ActionType::RestAtBed:
        appraisal.boredom_delta = 0.04;
        appraisal.fatigue_delta = -0.32;
        appraisal.screen_strain_delta = -0.14;
        appraisal.task_pressure_delta = 0.03;
        appraisal.satisfaction_delta = 0.05;
        appraisal.tags = {"recovery", "task_still_pending"};
        break;
    case ActionType::SleepAtBed:
        appraisal.boredom_delta = -0.08;
        appraisal.fatigue_delta = -0.58;
        appraisal.screen_strain_delta = -0.30;
        appraisal.task_pressure_delta = 0.06;
        appraisal.satisfaction_delta = 0.08;
        appraisal.tags = {"sleep_recovery", "long_unobserved_interval", "task_still_pending"};
        break;
    case ActionType::GoToBathroom:
        appraisal.satisfaction_delta = 0.07;
        appraisal.bathroom_urge_delta = -0.62;
        appraisal.tags = {"bodily_need_resolved", "brief_room_exit"};
        break;
    case ActionType::GetMeal:
        appraisal.boredom_delta = -0.04;
        appraisal.satisfaction_delta = 0.11;
        appraisal.hunger_delta = -0.55;
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
    case ActionType::Idle:
        appraisal.boredom_delta = 0.12;
        appraisal.task_pressure_delta = 0.08;
        appraisal.satisfaction_delta = -0.05;
        appraisal.tags = {"under_stimulation", "task_unattended"};
        break;
    }

    const auto apply_observation_update = [&](const ObservationFact& update) {
        if (update.key == "room.alarm" && update.value == "ringing"
            && update.status == KnowledgeStatus::Known) {
            appraisal.boredom_delta += 0.03;
            appraisal.anxiety_delta += 0.02 + 0.04 * personality.task_anxiety_sensitivity;
            appraisal.tags.push_back("alarm_interrupts_room");
        } else if (update.key == "room.temperature" && update.value == "17.0C"
                   && update.status == KnowledgeStatus::Known) {
            appraisal.fatigue_delta += 0.04;
            appraisal.satisfaction_delta -= 0.06;
            appraisal.tags.push_back("cold_interrupts_sleep");
        } else if (update.key == "message.unread_count" && update.value != "0"
                   && update.status == KnowledgeStatus::Known) {
            appraisal.task_pressure_delta += 0.08;
            appraisal.anxiety_delta += 0.05;
            appraisal.tags.push_back("social_task_reminder");
        } else if (update.key == "calendar.task_due" && update.value == "today"
                   && update.status == KnowledgeStatus::Known) {
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
    output << "X{tags=[";
    for (std::size_t index = 0; index < appraisal.tags.size(); ++index) {
        output << appraisal.tags[index];
        if (index + 1 < appraisal.tags.size()) {
            output << ", ";
        }
    }
    output << "]}";
    return output.str();
}
