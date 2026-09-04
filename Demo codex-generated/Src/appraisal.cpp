#include "appraisal.h"

#include <sstream>

Appraisal appraise(const Observation& observation, const WorldOutcome& previous_outcome) {
    Appraisal appraisal;

    // This is intentionally a small replaceable X function. Its input is an
    // observation plus the last settled world outcome, not direct writes to S.
    switch (previous_outcome.action) {
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
        appraisal.screen_strain_delta = previous_outcome.action == ActionType::StudyAtComputer ? 0.08 : 0.0;
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

    for (const WorldEvent& event : previous_outcome.events) {
        if (event.id == "alarm-rings") {
            appraisal.boredom_delta += 0.03;
            appraisal.anxiety_delta += 0.04;
            appraisal.tags.push_back("alarm_interrupts_room");
        } else if (event.id == "message-study-group") {
            appraisal.task_pressure_delta += 0.08;
            appraisal.anxiety_delta += 0.05;
            appraisal.tags.push_back("social_task_reminder");
        } else if (event.id == "task-reminder") {
            appraisal.task_pressure_delta += 0.14;
            appraisal.anxiety_delta += 0.12;
            appraisal.tags.push_back("deadline_salience");
        } else if (event.id == "evening") {
            appraisal.fatigue_delta += 0.04;
            appraisal.tags.push_back("evening_fatigue_cue");
        }
    }
    if (!observation.light_known_on) {
        appraisal.tags.push_back("room_is_dark");
    }
    for (const ObservationFact& update : observation.updates_this_refresh) {
        if (update.key == "outside.weather" && update.value == "rain"
            && update.status == KnowledgeStatus::Known) {
            appraisal.boredom_delta += 0.03;
            appraisal.tags.push_back("rain_observed_through_window");
        }
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
