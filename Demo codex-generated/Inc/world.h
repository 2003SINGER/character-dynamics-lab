#pragma once

#include "action.h"

#include <string>
#include <vector>

struct WorldOutcome {
    bool accepted = false;
    ActionType action = ActionType::Idle;
    std::string activity;
    std::vector<std::string> effects;
    std::string provenance;
};

struct World {
    bool phone_available = true;
    bool computer_available = true;
    bool desk_available = true;
    bool bed_available = true;

    int phone_uses = 0;
    int computer_uses = 0;
    int study_sessions = 0;
    int rest_sessions = 0;
    std::string current_activity = "idle";
    ActionType last_action = ActionType::Idle;

    bool can_execute(ActionType action) const;
    WorldOutcome execute(ActionType action);
    std::string summary() const;
};
