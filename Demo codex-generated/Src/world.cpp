#include "world.h"

#include <sstream>

bool World::can_execute(ActionType action) const {
    switch (action) {
    case ActionType::UsePhone:
        return phone_available;
    case ActionType::UseComputer:
        return computer_available;
    case ActionType::StudyAtDesk:
        return desk_available;
    case ActionType::RestAtBed:
        return bed_available;
    case ActionType::Idle:
        return true;
    }
    return false;
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
    case ActionType::Idle:
        outcome.effects.push_back("character remains in the room without a focused activity");
        break;
    }
    return outcome;
}

std::string World::summary() const {
    std::ostringstream output;
    output << "room{phone=" << (phone_available ? "ready" : "unavailable")
           << ", computer=" << (computer_available ? "ready" : "unavailable")
           << ", desk=" << (desk_available ? "ready" : "unavailable")
           << ", bed=" << (bed_available ? "ready" : "unavailable")
           << ", activity=" << current_activity
           << ", counts=[phone:" << phone_uses
           << ", computer:" << computer_uses
           << ", study:" << study_sessions
           << ", rest:" << rest_sessions << "]}";
    return output.str();
}
