#include "appraisal.h"

#include "personality.h"
#include "state.h"

#include <sstream>

Appraisal appraise(const Observation& observation,
                   const CharacterState& old_state,
                   const Personality& personality) {
    Appraisal appraisal;
    // Unknown task status is not silently treated as "known unfinished".
    // A currently maintained commitment remains a character-side reason to
    // experience unfinished-task pressure while confirmation is unavailable.
    const bool coursework_pending = has_known_fact(observation, "task.coursework.status", "active")
        || old_state.commitment.task_id == "coursework";

    // This is intentionally a small replaceable X function. It reads only O,
    // Delta-O, old S, and P: raw WorldOutcome must first pass through O.
    if (observation.last_self_action.has_action && !observation.last_self_action.accepted) {
        // A rejected A^char is still a character-side observation, but it
        // must not be mistaken for a successful W transition.
        appraisal.satisfaction_delta = -0.03;
        appraisal.anxiety_delta = 0.03;
        appraisal.tags = {"action_rejected", "goal_obstructed"};
    } else if (observation.last_self_action.has_action) {
    switch (observation.last_self_action.action) {
    case ActionType::UsePhone:
        appraisal.boredom_delta = -0.22;
        appraisal.fatigue_delta = 0.08;
        appraisal.task_pressure_delta = coursework_pending ? 0.07 : 0.0;
        appraisal.satisfaction_delta = 0.04;
        appraisal.screen_strain_delta = 0.12;
        appraisal.purchase_urge_delta = 0.10;
        appraisal.tags = coursework_pending ? std::vector<std::string>{"device_stimulation", "screen_strain", "task_deferred"}
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
        appraisal.boredom_delta = -0.16;
        appraisal.fatigue_delta = 0.10;
        appraisal.task_pressure_delta = coursework_pending ? 0.05 : 0.0;
        appraisal.screen_strain_delta = 0.11;
        appraisal.tags = coursework_pending ? std::vector<std::string>{"screen_engagement", "task_deferred"}
                                           : std::vector<std::string>{"screen_engagement"};
        break;
    case ActionType::StudyAtComputer:
    case ActionType::StudyAtDesk:
        appraisal.boredom_delta = 0.02;
        appraisal.fatigue_delta = 0.11;
        appraisal.task_pressure_delta = -0.15;
        appraisal.satisfaction_delta = 0.08;
        appraisal.anxiety_delta = -0.05;
        appraisal.screen_strain_delta = observation.last_self_action.action == ActionType::StudyAtComputer ? 0.08 : 0.0;
        appraisal.tags = {"task_effort_session", "mental_effort"};
        break;
    case ActionType::RestAtBed:
        appraisal.boredom_delta = 0.04;
        appraisal.fatigue_delta = -0.32;
        appraisal.screen_strain_delta = -0.14;
        appraisal.task_pressure_delta = coursework_pending ? 0.03 : 0.0;
        appraisal.satisfaction_delta = 0.05;
        appraisal.tags = coursework_pending ? std::vector<std::string>{"recovery", "task_still_pending"}
                                           : std::vector<std::string>{"recovery"};
        break;
    case ActionType::SleepAtBed:
        appraisal.boredom_delta = -0.08;
        appraisal.fatigue_delta = -0.58;
        appraisal.screen_strain_delta = -0.30;
        appraisal.task_pressure_delta = coursework_pending ? 0.06 : 0.0;
        appraisal.satisfaction_delta = 0.08;
        appraisal.tags = coursework_pending ? std::vector<std::string>{"sleep_recovery", "long_unobserved_interval", "task_still_pending"}
                                           : std::vector<std::string>{"sleep_recovery", "long_unobserved_interval"};
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
        appraisal.task_pressure_delta = coursework_pending ? 0.08 : 0.0;
        appraisal.satisfaction_delta = -0.05;
        appraisal.tags = coursework_pending ? std::vector<std::string>{"under_stimulation", "task_unattended"}
                                           : std::vector<std::string>{"under_stimulation"};
        break;
    case ActionType::Count:
        break;
    }
    }

    const auto apply_observation_update = [&](const ObservationFact& update) {
        if (update.key == "task.coursework.status" && update.value == "completed"
            && update.status == KnowledgeStatus::Known) {
            appraisal.task_pressure_delta -= 0.85;
            appraisal.anxiety_delta -= 0.55;
            appraisal.satisfaction_delta += 0.32;
            appraisal.tags.push_back("task_completed");
        } else if (update.key == "task.coursework.deadline" && update.value == "passed"
                   && update.status == KnowledgeStatus::Known && coursework_pending) {
            appraisal.task_pressure_delta += 0.18;
            appraisal.anxiety_delta += 0.10 + 0.10 * personality.task_anxiety_sensitivity;
            appraisal.tags.push_back("deadline_passed");
        } else if (update.key == "room.alarm" && update.value == "ringing"
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
                   && update.status == KnowledgeStatus::Known && coursework_pending) {
            appraisal.task_pressure_delta += 0.08;
            appraisal.anxiety_delta += 0.05;
            appraisal.tags.push_back("social_task_reminder");
        } else if (update.key == "calendar.task_due" && update.value == "today"
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
