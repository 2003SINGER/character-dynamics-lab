#pragma once

#include "action.h"
#include "scene.h"
#include "simulation_time.h"
#include "world_primitive.h"

#include <string>
#include <vector>

struct WorldEvent {
    std::string id;
    std::string description;
    std::string source;
};

struct WorldOutcome {
    bool accepted = false;
    ActionType action = ActionType::Idle;
    std::string activity;
    std::string object_id;
    int elapsed_minutes = 0;
    bool observation_frozen_during_action = false;
    bool woke_early = false;
    std::vector<WorldPrimitive> settled_primitives;
    std::vector<WorldEvent> events;
    std::vector<WorldEvent> sleeping_sensory_events;
    std::vector<std::string> effects;
    std::string provenance;
};

struct World {
    SimTime time;
    Scene scene = make_default_scene();
    int alarm_minute_of_day = 9 * 60;
    std::string weather = "clear";
    int task_progress = 0;
    int task_target = 5;
    int wallet = 120;
    int unread_messages = 0;
    std::string location = "room";
    std::string current_activity = "idle";
    int phone_uses = 0;
    int computer_uses = 0;
    int study_sessions = 0;
    int rest_sessions = 0;
    int bathroom_visits = 0;
    int meals_collected = 0;
    int online_orders = 0;
    ActionType last_action = ActionType::Idle;

    bool can_execute(ActionType action) const;
    std::vector<ActionType> available_actions() const;
    Room& current_room();
    const Room& current_room() const;
    const Object* object_for(ActionType action) const;
    CharacterActionPlan expand_action(ActionType action) const;
    WorldOutcome settle(const CharacterActionPlan& plan);
    WorldOutcome execute(ActionType action);
    std::string time_summary() const;
    std::string summary() const;
};
