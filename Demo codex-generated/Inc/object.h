#pragma once

#include "action.h"

#include <string>
#include <vector>

// A room-object instance carries its stable affordances plus its current
// usability inside the containing scene. The scene owns the collection.
struct RoomObject {
    std::string id;
    std::string label;
    bool usable = true;
    std::vector<ActionType> affordances;
};

bool provides_action(const RoomObject& object, ActionType action);
