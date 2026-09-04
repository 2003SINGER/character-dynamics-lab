#include "object.h"

#include <algorithm>

bool provides_action(const RoomObject& object, ActionType action) {
    return std::find(object.affordances.begin(), object.affordances.end(), action) != object.affordances.end();
}
