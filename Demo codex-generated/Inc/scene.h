#pragma once

#include "object.h"

#include <string>
#include <vector>

// Local room state: it owns room objects and local physical conditions, not
// global schedule, task, wallet, or character psychology.
struct RoomScene {
    std::vector<RoomObject> objects;
    bool light_on = true;
    bool alarm_ringing = false;
    bool curtain_open = true;
    double temperature_celsius = 23.0;
    std::string current_activity = "idle";

    const RoomObject* object_for(ActionType action) const;
};

RoomScene make_default_room();
