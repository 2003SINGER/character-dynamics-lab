#pragma once

#include "action.h"
#include "world.h"

#include <string>

// O: a separately stored character-side view, even though this one-room
// reference refreshes all visible fields deterministically.
struct Observation {
    bool phone_known_available = false;
    bool computer_known_available = false;
    bool desk_known_available = false;
    bool bed_known_available = false;
    ActionType observed_last_action = ActionType::Idle;
    std::string source;
};

Observation refresh_observation(const World& world, const std::string& source);
std::string observation_summary(const Observation& observation);
