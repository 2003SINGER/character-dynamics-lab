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

struct SimTime {
    int day = 1;
    int minute_of_day = 8 * 60;
};

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
    std::vector<WorldEvent> events;
    std::vector<WorldEvent> sleeping_sensory_events;
    std::vector<std::string> effects;
    std::string provenance;
};

struct World {
    std::vector<RoomObject> room_objects = {
        {"phone", "phone", true, {ActionType::UsePhone, ActionType::ShopOnPhone}},
        {"computer", "computer", true, {ActionType::UseComputer, ActionType::StudyAtComputer}},
        {"desk", "desk with study materials", true, {ActionType::StudyAtDesk}},
        {"bed", "bed", true, {ActionType::RestAtBed, ActionType::SleepAtBed}},
        {"door", "room door", true, {ActionType::GoToBathroom, ActionType::GetMeal}},
        {"light", "room light", true, {ActionType::TurnLightOn, ActionType::TurnLightOff}},
        {"alarm", "alarm clock", true, {ActionType::TurnOffAlarm}},
        {"window", "window with curtains", true, {ActionType::OpenCurtain, ActionType::CloseCurtain}}
    };

    SimTime time;
    bool light_on = true;
    bool alarm_ringing = false;
    int alarm_minute_of_day = 9 * 60;
    bool curtain_open = true;
    std::string weather = "clear";
    double room_temperature_celsius = 23.0;
    int task_progress = 0;
    int task_target = 5;
    int wallet = 120;
    int unread_messages = 0;
    std::string location = "room";
    int phone_uses = 0;
    int computer_uses = 0;
    int study_sessions = 0;
    int rest_sessions = 0;
    int bathroom_visits = 0;
    int meals_collected = 0;
    int online_orders = 0;
    bool character_asleep = false;
    std::string current_activity = "idle";
    ActionType last_action = ActionType::Idle;

    bool can_execute(ActionType action) const;
    std::vector<ActionType> available_actions() const;
    const RoomObject* object_for(ActionType action) const;
    WorldOutcome execute(ActionType action);
    std::string time_summary() const;
    std::string summary() const;
};
