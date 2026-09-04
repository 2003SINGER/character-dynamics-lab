#include "object.h"

#include <algorithm>

bool provides_action(const Object& object, ActionType action) {
    return std::find(object.affordances.begin(), object.affordances.end(), action) != object.affordances.end();
}
