#pragma once

#include "action.h"
#include "world.h"

#include <string>

// O: a separately stored character-side view, even though this one-room
// reference refreshes all visible fields deterministically.
struct Observation {
    std::vector<std::string> visible_object_labels;
    std::vector<ActionType> available_actions;
    bool light_known_on = true;
    int known_task_progress = 0;
    int known_unread_messages = 0;
    std::string observed_time;
    ActionType observed_last_action = ActionType::Idle;
    std::string source;
};

Observation refresh_observation(const World& world, const std::string& source);
std::string observation_summary(const Observation& observation);
