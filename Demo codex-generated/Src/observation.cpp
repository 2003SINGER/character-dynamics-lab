#include "observation.h"

#include <sstream>

Observation refresh_observation(const World& world, const std::string& source) {
    Observation observation;
    for (const RoomObject& object : world.room_objects) {
        if (object.usable) {
            observation.visible_object_labels.push_back(object.label);
        }
    }
    observation.available_actions = world.available_actions();
    observation.observed_last_action = world.last_action;
    observation.source = source;
    return observation;
}

std::string observation_summary(const Observation& observation) {
    std::ostringstream output;
    output << "O{visible_objects=[";
    for (std::size_t index = 0; index < observation.visible_object_labels.size(); ++index) {
        output << observation.visible_object_labels[index];
        if (index + 1 < observation.visible_object_labels.size()) {
            output << ", ";
        }
    }
    output << "], affordances=[";
    for (std::size_t index = 0; index < observation.available_actions.size(); ++index) {
        output << to_string(observation.available_actions[index]);
        if (index + 1 < observation.available_actions.size()) {
            output << ", ";
        }
    }
    output << "], observed_last_action=" << to_string(observation.observed_last_action)
           << ", source=" << observation.source << "}";
    return output.str();
}
