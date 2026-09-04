#include "observation.h"

#include <algorithm>
#include <iomanip>
#include <sstream>

namespace {
const char* to_string(KnowledgeStatus status) {
    switch (status) {
    case KnowledgeStatus::Known: return "known";
    case KnowledgeStatus::Stale: return "stale";
    case KnowledgeStatus::Unknown: return "unknown";
    }
    return "unknown";
}

void write_fact(Observation& observation,
                std::string key,
                std::string value,
                std::string source,
                std::string observed_at) {
    const auto existing = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& fact) { return fact.key == key; });
    const ObservationFact next{std::move(key), std::move(value), KnowledgeStatus::Known,
                               std::move(source), std::move(observed_at)};
    if (existing == observation.facts.end()) {
        observation.facts.push_back(next);
        observation.updates_this_refresh.push_back(next);
    } else {
        const bool changed = existing->value != next.value || existing->status != next.status
                          || existing->source != next.source;
        *existing = next;
        if (changed) {
            observation.updates_this_refresh.push_back(next);
        }
    }
}

void mark_stale(Observation& observation, const std::string& key) {
    const auto existing = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& fact) { return fact.key == key; });
    if (existing != observation.facts.end() && existing->status == KnowledgeStatus::Known) {
        existing->status = KnowledgeStatus::Stale;
        observation.updates_this_refresh.push_back(*existing);
    }
}

bool contains_id(const std::vector<std::string>& ids, const std::string& id) {
    return std::find(ids.begin(), ids.end(), id) != ids.end();
}

std::string format_temperature(double temperature) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(1) << temperature << "C";
    return output.str();
}

std::string fact_value(const Observation& observation, const std::string& key) {
    if (const ObservationFact* fact = find_fact(observation, key)) {
        return fact->value;
    }
    return "unknown";
}
} // namespace

const ObservationFact* find_fact(const Observation& observation, const std::string& key) {
    const auto fact = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& item) { return item.key == key; });
    return fact == observation.facts.end() ? nullptr : &*fact;
}

bool has_known_fact(const Observation& observation, const std::string& key, const std::string& value) {
    const ObservationFact* fact = find_fact(observation, key);
    return fact != nullptr && fact->status == KnowledgeStatus::Known && fact->value == value;
}

Observation refresh_observation(Observation observation,
                                const World& world,
                                const WorldOutcome& previous_outcome) {
    observation.updates_this_refresh.clear();
    observation.visible_object_labels.clear();
    observation.known_object_ids.clear();
    observation.known_actions.clear();
    const std::string now = world.time_summary();

    // Current room rule: every usable room object is directly observable.
    // Other scenes can later omit objects here while still retaining facts from
    // message, memory, sound, or stale prior observation.
    for (const RoomObject& object : world.room.objects) {
        if (object.usable) {
            observation.known_object_ids.push_back(object.id);
            observation.visible_object_labels.push_back(object.label);
            write_fact(observation, "object." + object.id, "present", "direct_room_visual", now);
        }
    }
    observation.observed_last_action = world.last_action;
    write_fact(observation, "room.light", world.room.light_on ? "on" : "off", "direct_room_visual", now);
    const bool alarm_rang = std::any_of(previous_outcome.events.begin(), previous_outcome.events.end(),
        [](const WorldEvent& event) { return event.id == "alarm-rings"; });
    write_fact(observation, "room.alarm", world.room.alarm_ringing ? "ringing" : "silent",
               alarm_rang ? "direct_room_auditory" : "direct_room_visual", now);
    write_fact(observation, "task.progress", std::to_string(world.task_progress), "direct_room_visual", now);
    write_fact(observation, "message.unread_count", std::to_string(world.unread_messages), "phone_notification_state", now);
    write_fact(observation, "clock.time", now, "internal_clock", now);
    write_fact(observation, "room.temperature", format_temperature(world.room.temperature_celsius), "direct_room_thermal", now);
    if (world.room.curtain_open) {
        write_fact(observation, "outside.weather", world.weather, "direct_window_visual", now);
    } else {
        mark_stale(observation, "outside.weather");
    }

    // The alarm is a room-local event. Its auditory source wins over the
    // ordinary visual refresh when it rang during the preceding action.

    // Explicit A^W -> A^O: an action is known only when W says it is currently
    // legal and O contains the object that affords it. In this room all objects
    // are visible, so the sets will usually match; the layer is still separate.
    for (ActionType action : world.available_actions()) {
        if (action == ActionType::Idle) {
            observation.known_actions.push_back(action);
        } else if (const RoomObject* object = world.object_for(action);
                   object != nullptr && contains_id(observation.known_object_ids, object->id)) {
            observation.known_actions.push_back(action);
        }
    }
    return observation;
}

bool observation_knows_action(const Observation& observation, ActionType action) {
    return std::find(observation.known_actions.begin(), observation.known_actions.end(), action)
        != observation.known_actions.end();
}

Observation apply_sleep_sensory_update(Observation observation,
                                       const WorldOutcome& outcome,
                                       const World& world) {
    observation.updates_this_refresh.clear();
    for (const WorldEvent& event : outcome.sleeping_sensory_events) {
        if (event.id == "room-cold") {
            write_fact(observation, "room.temperature", format_temperature(world.room.temperature_celsius),
                       "direct_room_thermal_while_asleep", world.time_summary());
        }
    }
    return observation;
}

std::string observation_updates_summary(const Observation& observation) {
    std::ostringstream output;
    output << "updates=[";
    for (std::size_t index = 0; index < observation.updates_this_refresh.size(); ++index) {
        const ObservationFact& fact = observation.updates_this_refresh[index];
        output << fact.key << '=' << fact.value << "{" << to_string(fact.status)
               << ", " << fact.source << '}';
        if (index + 1 < observation.updates_this_refresh.size()) output << ", ";
    }
    output << ']';
    return output.str();
}

std::string observation_summary(const Observation& observation) {
    std::ostringstream output;
    output << "O{visible_objects=[";
    for (std::size_t index = 0; index < observation.visible_object_labels.size(); ++index) {
        output << observation.visible_object_labels[index];
        if (index + 1 < observation.visible_object_labels.size()) output << ", ";
    }
    output << "], A^O=[";
    for (std::size_t index = 0; index < observation.known_actions.size(); ++index) {
        output << to_string(observation.known_actions[index]);
        if (index + 1 < observation.known_actions.size()) output << ", ";
    }
    output << "], " << observation_updates_summary(observation)
           << ", temperature=" << fact_value(observation, "room.temperature")
           << ", time=" << fact_value(observation, "clock.time")
           << ", light=" << fact_value(observation, "room.light")
           << ", task_progress=" << fact_value(observation, "task.progress")
           << ", unread_messages=" << fact_value(observation, "message.unread_count")
           << ", observed_last_action=" << to_string(observation.observed_last_action) << '}';
    return output.str();
}
