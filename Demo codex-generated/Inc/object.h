#pragma once

#include "action.h"

#include <string>
#include <vector>

// Object is a concrete thing contained by a Room. It carries its stable
// affordances plus current usability inside that room.
struct Object {
    std::string id;
    std::string label;
    bool usable = true;
    std::vector<ActionType> affordances;
};

bool provides_action(const Object& object, ActionType action);
