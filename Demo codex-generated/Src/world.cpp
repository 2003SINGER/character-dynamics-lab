#include "world.h"

#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <type_traits>

namespace {
Room& require_room(Scene& scene, const std::string& room_id) {
    if (Room* room = scene.room_by_id(room_id)) {
        return *room;
    }
    throw std::logic_error("World location does not resolve to a Room in its Scene");
}

const Room& require_room(const Scene& scene, const std::string& room_id) {
    if (const Room* room = scene.room_by_id(room_id)) {
        return *room;
    }
    throw std::logic_error("World location does not resolve to a Room in its Scene");
}
} // namespace

Room& World::current_room() {
    return require_room(scene, location);
}

const Room& World::current_room() const {
    return require_room(scene, location);
}

bool World::can_execute(ActionType action) const {
    if (action == ActionType::Idle) {
        return true;
    }
    const Room& room = current_room();
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

const Object* World::object_for(ActionType action) const {
    return current_room().object_for(action);
}

CharacterActionPlan World::expand_action(ActionType action) const {
    CharacterActionPlan plan;
    plan.action = action;
    if (const Object* object = object_for(action)) {
        plan.object_id = object->id;
    }
    const auto add = [&plan](std::string id, std::string description, WorldPrimitivePayload payload) {
        plan.world_primitives.push_back({std::move(id), std::move(description), std::move(payload)});
    };

    add("record-action", action == ActionType::Idle
            ? "character remains in the room without a focused activity"
            : "character begins " + to_string(action),
        SetCurrentActivity{action});
    switch (action) {
    case ActionType::UsePhone:
        add("count-phone-use", "phone browsing completed", IncrementWorldCounter{WorldCounter::PhoneUses});
        break;
    case ActionType::ShopOnPhone:
        add("spend-wallet", "online order placed; wallet decreased by 30", AdjustWorldValue{WorldValue::Wallet, -30});
        add("count-order", "online order recorded", IncrementWorldCounter{WorldCounter::OnlineOrders});
        break;
    case ActionType::UseComputer:
        add("count-computer-use", "computer browsing completed", IncrementWorldCounter{WorldCounter::ComputerUses});
        break;
    case ActionType::StudyAtComputer:
    case ActionType::StudyAtDesk:
        add("count-study-session", "study session completed", IncrementWorldCounter{WorldCounter::StudySessions});
        add("advance-task", "task progress increased by 1", AdjustWorldValue{WorldValue::TaskProgress, 1});
        break;
    case ActionType::RestAtBed:
        add("count-rest-session", "rest session completed in bed", IncrementWorldCounter{WorldCounter::RestSessions});
        break;
    case ActionType::SleepAtBed:
        add("count-sleep-session", "sleep session begins; ordinary O refresh is frozen during the interval",
            IncrementWorldCounter{WorldCounter::RestSessions});
        break;
    case ActionType::GoToBathroom:
        add("count-bathroom-visit", "brief excursion through door: bathroom visit completed",
            IncrementWorldCounter{WorldCounter::BathroomVisits});
        break;
    case ActionType::GetMeal:
        add("count-meal", "brief excursion through door: meal collected and eaten",
            IncrementWorldCounter{WorldCounter::MealsCollected});
        break;
    case ActionType::TurnLightOn:
        add("light-on", "room light turned on", SetRoomFlag{RoomFlag::LightOn, true});
        break;
    case ActionType::TurnLightOff:
        add("light-off", "room light turned off", SetRoomFlag{RoomFlag::LightOn, false});
        break;
    case ActionType::TurnOffAlarm:
        add("alarm-off", "alarm clock silenced", SetRoomFlag{RoomFlag::AlarmRinging, false});
        break;
    case ActionType::OpenCurtain:
        add("curtain-open", "curtains opened; outside weather becomes visible from the room",
            SetRoomFlag{RoomFlag::CurtainOpen, true});
        break;
    case ActionType::CloseCurtain:
        add("curtain-close", "curtains closed; outside weather is no longer directly visible",
            SetRoomFlag{RoomFlag::CurtainOpen, false});
        break;
    case ActionType::Idle:
        break;
    case ActionType::Count:
        throw std::logic_error("ActionType::Count cannot be expanded");
    }
    add("advance-time", "advance simulated time", AdvanceSimulationTime{action_definition(action).default_duration_minutes});
    return plan;
}

std::vector<ActionType> World::available_actions() const {
    std::vector<ActionType> actions = {ActionType::Idle};
    const Room& room = current_room();
    for (const Object& object : room.objects) {
        for (ActionType action : object.affordances) {
            if (object.usable && can_execute(action)) {
                if (std::find(actions.begin(), actions.end(), action) == actions.end()) {
                    actions.push_back(action);
                }
            }
        }
    }
    return actions;
}

WorldOutcome World::settle(ActionType action) {
    // Re-expand inside W immediately before settlement.  This deliberately
    // makes CharacterActionPlan a trace/provenance object rather than a
    // capability that another module can forge to mutate W.
    CharacterActionPlan plan = expand_action(action);
    WorldOutcome outcome;
    outcome.action = plan.action;
    outcome.provenance = "World::settle(" + to_string(plan.action) + ")";

    if (!can_execute(plan.action)) {
        outcome.effects.push_back("rejected: object unavailable or action precondition failed");
        return outcome;
    }

    outcome.accepted = true;
    if (!plan.object_id.empty()) {
        outcome.object_id = plan.object_id;
        outcome.provenance += " via object:" + plan.object_id;
    }

    outcome.planned_primitives = plan.world_primitives;
    outcome.settled_primitives = outcome.planned_primitives;
    const int before = total_minutes(time);
    auto time_primitive = std::find_if(outcome.settled_primitives.begin(), outcome.settled_primitives.end(),
        [](const WorldPrimitive& primitive) {
            return std::holds_alternative<AdvanceSimulationTime>(primitive.payload);
        });
    if (time_primitive == outcome.settled_primitives.end()) {
        throw std::logic_error("CharacterActionPlan has no AdvanceSimulationTime primitive");
    }
    auto& advance = std::get<AdvanceSimulationTime>(time_primitive->payload);
    int after = before + advance.minutes;
    constexpr int kColdWakeMinute = 16 * 60;
    if (plan.action == ActionType::SleepAtBed && before < kColdWakeMinute && after >= kColdWakeMinute) {
        after = kColdWakeMinute;
        advance.minutes = after - before;
        outcome.woke_early = true;
    }

    Room& room = current_room();
    for (const WorldPrimitive& primitive : outcome.settled_primitives) {
        std::visit([&](const auto& payload) {
            using Payload = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<Payload, SetCurrentActivity>) {
                last_action = payload.action;
                current_activity = to_string(payload.action);
                outcome.activity = current_activity;
            } else if constexpr (std::is_same_v<Payload, IncrementWorldCounter>) {
                switch (payload.counter) {
                case WorldCounter::PhoneUses: phone_uses += payload.amount; break;
                case WorldCounter::ComputerUses: computer_uses += payload.amount; break;
                case WorldCounter::StudySessions: study_sessions += payload.amount; break;
                case WorldCounter::RestSessions: rest_sessions += payload.amount; break;
                case WorldCounter::BathroomVisits: bathroom_visits += payload.amount; break;
                case WorldCounter::MealsCollected: meals_collected += payload.amount; break;
                case WorldCounter::OnlineOrders: online_orders += payload.amount; break;
                }
            } else if constexpr (std::is_same_v<Payload, AdjustWorldValue>) {
                switch (payload.value) {
                case WorldValue::Wallet: wallet += payload.amount; break;
                case WorldValue::TaskProgress: task_progress += payload.amount; break;
                }
            } else if constexpr (std::is_same_v<Payload, SetRoomFlag>) {
                switch (payload.flag) {
                case RoomFlag::LightOn: room.light_on = payload.value; break;
                case RoomFlag::AlarmRinging: room.alarm_ringing = payload.value; break;
                case RoomFlag::CurtainOpen: room.curtain_open = payload.value; break;
                }
            } else if constexpr (std::is_same_v<Payload, AdvanceSimulationTime>) {
                outcome.elapsed_minutes = payload.minutes;
                advance_minutes(time, payload.minutes);
            }
        }, primitive.payload);
        outcome.effects.push_back(primitive.description);
    }

    if (plan.action == ActionType::SleepAtBed) {
        outcome.observation_frozen_during_action = true;
        outcome.effects.push_back(outcome.woke_early
            ? "character wakes early because cold is sensed; the next decision point can refresh O from the room"
            : "character wakes; the next decision point can refresh O from the room");
    }

    const auto emit_daily_if_crossed = [&](int minute_of_day, const char* id, const char* description, const char* source) {
        constexpr int kMinutesPerDay = 24 * 60;
        const int first_day_index = before / kMinutesPerDay;
        const int last_day_index = after / kMinutesPerDay;
        for (int day_index = first_day_index; day_index <= last_day_index; ++day_index) {
            const int event_minute = day_index * kMinutesPerDay + minute_of_day;
            if (before < event_minute && after >= event_minute) {
                WorldEvent event{id, description, source};
                outcome.events.push_back(event);
                outcome.effects.push_back("external event: " + event.description);
            }
        }
    };
    if (before < alarm_minute_of_day && after >= alarm_minute_of_day && !room.alarm_ringing) {
        room.alarm_ringing = true;
        WorldEvent event{"alarm-rings", "the alarm clock rings in the room", "room/alarm-clock"};
        outcome.events.push_back(event);
        outcome.effects.push_back("scene event: " + event.description);
    }
    emit_daily_if_crossed(9 * 60 + 30, "message-study-group", "a study-group message arrives", "phone notification");
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
        if (plan.action == ActionType::SleepAtBed) {
            outcome.sleeping_sensory_events.push_back(event);
            outcome.effects.push_back("sleeping sensory update: cold is felt despite other O fields being frozen");
        }
    }
    if (task_progress < task_target) {
        emit_daily_if_crossed(12 * 60, "task-reminder", "calendar reminder: task remains due today", "calendar");
    }
    emit_daily_if_crossed(18 * 60, "evening", "evening begins; the room becomes quieter", "world clock");
    for (const WorldEvent& event : outcome.events) {
        if (event.id == "message-study-group") {
            ++unread_messages;
        }
    }
    return outcome;
}

WorldOutcome World::execute(ActionType action) {
    return settle(action);
}

std::string World::time_summary() const {
    return ::time_summary(time);
}

std::string World::summary() const {
    const Room& room = current_room();
    std::ostringstream output;
    output << "W{time=" << time_summary()
           << ", scene=" << scene.id
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
        const Object& object = room.objects[index];
        output << object.id << ':' << (object.usable ? "ready" : "unavailable");
        if (index + 1 < room.objects.size()) {
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
