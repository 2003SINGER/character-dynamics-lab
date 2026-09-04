#include "world.h"

#include <sstream>

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
        return room.light_on && task_progress < task_target;
    case ActionType::TurnLightOn:
        return !room.light_on;
    case ActionType::TurnLightOff:
        return room.light_on;
    case ActionType::TurnOffAlarm:
        return room.alarm_ringing;
    case ActionType::OpenCurtain:
        return !room.curtain_open;
    case ActionType::CloseCurtain:
        return room.curtain_open;
    default:
        return true;
    }
}

const RoomObject* World::object_for(ActionType action) const {
    return room.object_for(action);
}

std::vector<ActionType> World::available_actions() const {
    std::vector<ActionType> actions = {ActionType::Idle};
    for (const RoomObject& object : room.objects) {
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
    room.current_activity = to_string(action);
    outcome.activity = room.current_activity;
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
        room.light_on = true;
        outcome.effects.push_back("room light turned on");
        break;
    case ActionType::TurnLightOff:
        room.light_on = false;
        outcome.effects.push_back("room light turned off");
        break;
    case ActionType::TurnOffAlarm:
        room.alarm_ringing = false;
        outcome.effects.push_back("alarm clock silenced");
        break;
    case ActionType::OpenCurtain:
        room.curtain_open = true;
        outcome.effects.push_back("curtains opened; outside weather becomes visible from the room");
        break;
    case ActionType::CloseCurtain:
        room.curtain_open = false;
        outcome.effects.push_back("curtains closed; outside weather is no longer directly visible");
        break;
    case ActionType::Idle:
        outcome.effects.push_back("character remains in the room without a focused activity");
        break;
    }

    outcome.elapsed_minutes = action_definition(action).default_duration_minutes;
    const int before = total_minutes(time);
    int after = before + outcome.elapsed_minutes;
    constexpr int kColdWakeMinute = 16 * 60;
    if (action == ActionType::SleepAtBed && before < kColdWakeMinute && after >= kColdWakeMinute) {
        after = kColdWakeMinute;
        outcome.elapsed_minutes = after - before;
        outcome.woke_early = true;
    }
    advance_minutes(time, outcome.elapsed_minutes);

    if (action == ActionType::SleepAtBed) {
        outcome.effects.push_back(outcome.woke_early
            ? "character wakes early because cold is sensed; the next decision point can refresh O from the room"
            : "character wakes; the next decision point can refresh O from the room");
    }

    const auto emit_if_crossed = [&](int at, const char* id, const char* description, const char* source) {
        if (before < at && after >= at) {
            WorldEvent event{id, description, source};
            outcome.events.push_back(event);
            outcome.effects.push_back("external event: " + event.description);
        }
    };
    if (before < alarm_minute_of_day && after >= alarm_minute_of_day && !room.alarm_ringing) {
        room.alarm_ringing = true;
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
    if (before < kColdWakeMinute && after >= kColdWakeMinute && room.temperature_celsius > 17.0) {
        room.temperature_celsius = 17.0;
        WorldEvent event{"room-cold", "room temperature falls to 17C", "room/temperature"};
        outcome.events.push_back(event);
        outcome.effects.push_back("world event: " + event.description);
        if (action == ActionType::SleepAtBed) {
            outcome.sleeping_sensory_events.push_back(event);
            outcome.effects.push_back("sleeping sensory update: cold is felt despite other O fields being frozen");
        }
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
    return ::time_summary(time);
}

std::string World::summary() const {
    std::ostringstream output;
    output << "W{time=" << time_summary()
           << ", location=" << location
           << ", light=" << (room.light_on ? "on" : "off")
           << ", alarm=" << (room.alarm_ringing ? "ringing" : "silent")
           << ", curtain=" << (room.curtain_open ? "open" : "closed")
           << ", weather=" << weather
           << ", temperature=" << room.temperature_celsius << "C"
           << ", task=" << task_progress << '/' << task_target
           << ", wallet=" << wallet
           << ", unread_messages=" << unread_messages
           << ", objects=[";
    for (std::size_t index = 0; index < room.objects.size(); ++index) {
        const RoomObject& object = room.objects[index];
        output << object.id << ':' << (object.usable ? "ready" : "unavailable");
        if (index + 1 < room.objects.size()) {
            output << ", ";
        }
    }
    output << "], activity=" << room.current_activity
           << ", counts=[phone:" << phone_uses
           << ", computer:" << computer_uses
           << ", study:" << study_sessions
           << ", rest:" << rest_sessions
           << ", bathroom:" << bathroom_visits
           << ", meal:" << meals_collected
           << ", orders:" << online_orders << "]}";
    return output.str();
}
