#pragma once

#include "action.h"

#include <string>
#include <vector>

// Objects own affordances. Adding an object to the room is therefore the
// single place where a new action can become possible in this small demo.
struct RoomObject {
    std::string id;
    std::string label;
    bool usable = true;
    std::vector<ActionType> affordances;
};

struct WorldOutcome {
    bool accepted = false;
    ActionType action = ActionType::Idle;
    std::string activity;
    std::string object_id;
    std::vector<std::string> effects;
    std::string provenance;
};

struct World {
    std::vector<RoomObject> room_objects = {
        {"phone", "phone", true, {ActionType::UsePhone}},
        {"computer", "computer", true, {ActionType::UseComputer}},
        {"desk", "desk with study materials", true, {ActionType::StudyAtDesk}},
        {"bed", "bed", true, {ActionType::RestAtBed}},
        {"door", "room door", true, {ActionType::GoToBathroom, ActionType::GetMeal}}
    };

    int phone_uses = 0;
    int computer_uses = 0;
    int study_sessions = 0;
    int rest_sessions = 0;
    int bathroom_visits = 0;
    int meals_collected = 0;
    std::string current_activity = "idle";
    ActionType last_action = ActionType::Idle;

    bool can_execute(ActionType action) const;
    std::vector<ActionType> available_actions() const;
    const RoomObject* object_for(ActionType action) const;
    WorldOutcome execute(ActionType action);
    std::string summary() const;
};
