#include "world.h"

#include <algorithm>
#include <sstream>

bool World::can_execute(ActionType action) const {
    return action == ActionType::Idle || object_for(action) != nullptr;
}

const RoomObject* World::object_for(ActionType action) const {
    for (const RoomObject& object : room_objects) {
        const bool provides_action = std::find(object.affordances.begin(),
                                               object.affordances.end(),
                                               action) != object.affordances.end();
        if (object.usable && provides_action) {
            return &object;
        }
    }
    return nullptr;
}

std::vector<ActionType> World::available_actions() const {
    std::vector<ActionType> actions = {ActionType::Idle};
    for (const RoomObject& object : room_objects) {
        if (object.usable) {
            actions.insert(actions.end(), object.affordances.begin(), object.affordances.end());
        }
    }
    return actions;
}

WorldOutcome World::execute(ActionType action) {
    WorldOutcome outcome;
    outcome.action = action;
    outcome.provenance = "World::execute(" + to_string(action) + ")";

    if (!can_execute(action)) {
        outcome.effects.push_back("rejected: required room affordance is unavailable");
        return outcome;
    }

    outcome.accepted = true;
    last_action = action;
    current_activity = to_string(action);
    outcome.activity = current_activity;
    if (const RoomObject* object = object_for(action)) {
        outcome.object_id = object->id;
        outcome.provenance += " via object:" + object->id;
    }

    switch (action) {
    case ActionType::UsePhone:
        ++phone_uses;
        outcome.effects.push_back("phone use count increased");
        break;
    case ActionType::UseComputer:
        ++computer_uses;
        outcome.effects.push_back("computer use count increased");
        break;
    case ActionType::StudyAtDesk:
        ++study_sessions;
        outcome.effects.push_back("study session recorded at desk");
        break;
    case ActionType::RestAtBed:
        ++rest_sessions;
        outcome.effects.push_back("rest session recorded at bed");
        break;
    case ActionType::GoToBathroom:
        ++bathroom_visits;
        outcome.effects.push_back("left through door and returned after using bathroom");
        break;
    case ActionType::GetMeal:
        ++meals_collected;
        outcome.effects.push_back("left through door and returned with a simple meal");
        break;
    case ActionType::Idle:
        outcome.effects.push_back("character remains in the room without a focused activity");
        break;
    }
    return outcome;
}

std::string World::summary() const {
    std::ostringstream output;
    output << "room{objects=[";
    for (std::size_t index = 0; index < room_objects.size(); ++index) {
        const RoomObject& object = room_objects[index];
        output << object.id << ':' << (object.usable ? "ready" : "unavailable");
        if (index + 1 < room_objects.size()) {
            output << ", ";
        }
    }
    output << "], activity=" << current_activity
           << ", counts=[phone:" << phone_uses
           << ", computer:" << computer_uses
           << ", study:" << study_sessions
           << ", rest:" << rest_sessions
           << ", bathroom:" << bathroom_visits
           << ", meal:" << meals_collected << "]}";
    return output.str();
}
