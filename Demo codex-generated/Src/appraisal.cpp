#include "appraisal.h"

#include <sstream>

Appraisal appraise(const Observation& observation) {
    Appraisal appraisal;

    switch (observation.observed_last_action) {
    case ActionType::UsePhone:
        appraisal.boredom_delta = -0.22;
        appraisal.fatigue_delta = 0.14;
        appraisal.task_pressure_delta = 0.08;
        appraisal.satisfaction_delta = 0.05;
        appraisal.tags = {"device_stimulation", "device_strain", "task_deferred"};
        break;
    case ActionType::UseComputer:
        appraisal.boredom_delta = -0.16;
        appraisal.fatigue_delta = 0.12;
        appraisal.task_pressure_delta = 0.06;
        appraisal.satisfaction_delta = 0.04;
        appraisal.tags = {"screen_engagement", "screen_strain", "task_deferred"};
        break;
    case ActionType::StudyAtDesk:
        appraisal.boredom_delta = 0.03;
        appraisal.fatigue_delta = 0.10;
        appraisal.task_pressure_delta = -0.26;
        appraisal.satisfaction_delta = 0.12;
        appraisal.tags = {"task_progress", "mental_effort"};
        break;
    case ActionType::RestAtBed:
        appraisal.boredom_delta = 0.04;
        appraisal.fatigue_delta = -0.30;
        appraisal.task_pressure_delta = 0.02;
        appraisal.satisfaction_delta = 0.05;
        appraisal.tags = {"recovery", "task_still_pending"};
        break;
    case ActionType::GoToBathroom:
        appraisal.boredom_delta = 0.01;
        appraisal.satisfaction_delta = 0.07;
        appraisal.bathroom_urge_delta = -0.55;
        appraisal.tags = {"bodily_need_resolved", "brief_room_exit"};
        break;
    case ActionType::GetMeal:
        appraisal.boredom_delta = -0.04;
        appraisal.satisfaction_delta = 0.10;
        appraisal.hunger_delta = -0.48;
        appraisal.tags = {"hunger_resolved", "brief_room_exit"};
        break;
    case ActionType::Idle:
        appraisal.boredom_delta = 0.12;
        appraisal.fatigue_delta = -0.01;
        appraisal.task_pressure_delta = 0.09;
        appraisal.satisfaction_delta = -0.05;
        appraisal.tags = {"under_stimulation", "task_unattended"};
        break;
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
