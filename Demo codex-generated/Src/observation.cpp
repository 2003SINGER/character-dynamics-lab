#include "observation.h"

#include <sstream>

Observation refresh_observation(const World& world, const std::string& source) {
    Observation observation;
    observation.phone_known_available = world.phone_available;
    observation.computer_known_available = world.computer_available;
    observation.desk_known_available = world.desk_available;
    observation.bed_known_available = world.bed_available;
    observation.observed_last_action = world.last_action;
    observation.source = source;
    return observation;
}

std::string observation_summary(const Observation& observation) {
    std::ostringstream output;
    output << "O{phone=" << (observation.phone_known_available ? "known-ready" : "known-unavailable")
           << ", computer=" << (observation.computer_known_available ? "known-ready" : "known-unavailable")
           << ", desk=" << (observation.desk_known_available ? "known-ready" : "known-unavailable")
           << ", bed=" << (observation.bed_known_available ? "known-ready" : "known-unavailable")
           << ", observed_last_action=" << to_string(observation.observed_last_action)
           << ", source=" << observation.source << "}";
    return output.str();
}
