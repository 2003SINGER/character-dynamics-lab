#include "world.h"

#include <algorithm>
#include <iomanip>
#include <sstream>

namespace {
int action_duration(ActionType action) {
    switch (action) {
    case ActionType::UsePhone: return 25;
    case ActionType::ShopOnPhone: return 20;
    case ActionType::UseComputer: return 30;
    case ActionType::StudyAtComputer: return 35;
    case ActionType::StudyAtDesk: return 35;
    case ActionType::RestAtBed: return 60;
    case ActionType::SleepAtBed: return 8 * 60;
    case ActionType::GoToBathroom: return 15;
    case ActionType::GetMeal: return 35;
    case ActionType::TurnLightOn: return 1;
    case ActionType::TurnLightOff: return 1;
    case ActionType::TurnOffAlarm: return 1;
    case ActionType::OpenCurtain: return 1;
    case ActionType::CloseCurtain: return 1;
    case ActionType::Idle: return 10;
    }
    return 0;
}

int total_minutes(const SimTime& time) {
    return (time.day - 1) * 24 * 60 + time.minute_of_day;
}
} // namespace

bool World::can_execute(ActionType action) const {
    if (action == ActionType::Idle) {
        return true;
    }
    if (object_for(action) == nullptr) {
        return false;
    }
    switch (action) {
    case ActionType::ShopOnPhone:
        return wallet >= 30;
    case ActionType::StudyAtDesk:
    case ActionType::StudyAtComputer:
        return light_on && task_progress < task_target;
    case ActionType::TurnLightOn:
        return !light_on;
    case ActionType::TurnLightOff:
        return light_on;
    case ActionType::TurnOffAlarm:
        return alarm_ringing;
    case ActionType::OpenCurtain:
        return !curtain_open;
    case ActionType::CloseCurtain:
        return curtain_open;
    default:
        return true;
    }
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
        for (ActionType action : object.affordances) {
            if (object.usable && can_execute(action)) {
                actions.push_back(action);
            }
        }
    }
    return actions;
}

WorldOutcome World::execute(ActionType action) {
    WorldOutcome outcome;
    outcome.action = action;
    outcome.provenance = "World::execute(" + to_string(action) + ")";

    if (!can_execute(action)) {
        outcome.effects.push_back("rejected: object unavailable or action precondition failed");
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
        outcome.effects.push_back("phone browsing completed");
        break;
    case ActionType::ShopOnPhone:
        wallet -= 30;
        ++online_orders;
        outcome.effects.push_back("online order placed; wallet decreased by 30");
        break;
    case ActionType::UseComputer:
        ++computer_uses;
        outcome.effects.push_back("computer browsing completed");
        break;
    case ActionType::StudyAtComputer:
    case ActionType::StudyAtDesk:
        ++study_sessions;
        ++task_progress;
        outcome.effects.push_back("study session completed; task progress increased by 1");
        break;
    case ActionType::RestAtBed:
        ++rest_sessions;
        outcome.effects.push_back("rest session completed in bed");
        break;
    case ActionType::SleepAtBed:
        ++rest_sessions;
        character_asleep = true;
        outcome.observation_frozen_during_action = true;
        outcome.effects.push_back("character falls asleep; O is not refreshed during the sleep interval");
        break;
    case ActionType::GoToBathroom:
        ++bathroom_visits;
        outcome.effects.push_back("brief excursion through door: bathroom visit completed");
        break;
    case ActionType::GetMeal:
        ++meals_collected;
        outcome.effects.push_back("brief excursion through door: meal collected and eaten");
        break;
    case ActionType::TurnLightOn:
        light_on = true;
        outcome.effects.push_back("room light turned on");
        break;
    case ActionType::TurnLightOff:
        light_on = false;
        outcome.effects.push_back("room light turned off");
        break;
    case ActionType::TurnOffAlarm:
        alarm_ringing = false;
        outcome.effects.push_back("alarm clock silenced");
        break;
    case ActionType::OpenCurtain:
        curtain_open = true;
        outcome.effects.push_back("curtains opened; outside weather becomes visible from the room");
        break;
    case ActionType::CloseCurtain:
        curtain_open = false;
        outcome.effects.push_back("curtains closed; outside weather is no longer directly visible");
        break;
    case ActionType::Idle:
        outcome.effects.push_back("character remains in the room without a focused activity");
        break;
    }

    outcome.elapsed_minutes = action_duration(action);
    const int before = total_minutes(time);
    const int after = before + outcome.elapsed_minutes;
    time.day = after / (24 * 60) + 1;
    time.minute_of_day = after % (24 * 60);

    if (action == ActionType::SleepAtBed) {
        character_asleep = false;
        outcome.effects.push_back("character wakes; the next decision point can refresh O from the room");
    }

    const auto emit_if_crossed = [&](int at, const char* id, const char* description, const char* source) {
        if (before < at && after >= at) {
            WorldEvent event{id, description, source};
            outcome.events.push_back(event);
            outcome.effects.push_back("external event: " + event.description);
        }
    };
    if (before < alarm_minute_of_day && after >= alarm_minute_of_day && !alarm_ringing) {
        alarm_ringing = true;
        WorldEvent event{"alarm-rings", "the alarm clock rings in the room", "room/alarm-clock"};
        outcome.events.push_back(event);
        outcome.effects.push_back("scene event: " + event.description);
    }
    emit_if_crossed(9 * 60 + 30, "message-study-group", "a study-group message arrives", "phone notification");
    if (before < 11 * 60 && after >= 11 * 60 && weather == "clear") {
        weather = "rain";
        WorldEvent event{"weather-rain", "rain begins outside", "world/weather"};
        outcome.events.push_back(event);
        outcome.effects.push_back("world event: " + event.description);
    }
    emit_if_crossed(12 * 60, "task-reminder", "calendar reminder: task remains due today", "calendar");
    emit_if_crossed(18 * 60, "evening", "evening begins; the room becomes quieter", "world clock");
    for (const WorldEvent& event : outcome.events) {
        if (event.id == "message-study-group") {
            ++unread_messages;
        }
    }
    return outcome;
}

std::string World::time_summary() const {
    std::ostringstream output;
    output << "Day " << time.day << ' ' << std::setw(2) << std::setfill('0') << time.minute_of_day / 60
           << ':' << std::setw(2) << std::setfill('0') << time.minute_of_day % 60;
    return output.str();
}

std::string World::summary() const {
    std::ostringstream output;
    output << "W{time=" << time_summary()
           << ", location=" << location
           << ", light=" << (light_on ? "on" : "off")
           << ", alarm=" << (alarm_ringing ? "ringing" : "silent")
           << ", curtain=" << (curtain_open ? "open" : "closed")
           << ", weather=" << weather
           << ", task=" << task_progress << '/' << task_target
           << ", wallet=" << wallet
           << ", unread_messages=" << unread_messages
           << ", objects=[";
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
           << ", meal:" << meals_collected
           << ", orders:" << online_orders << "]}";
    return output.str();
}
