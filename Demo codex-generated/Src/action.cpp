#include "action.h"

#include <array>

namespace {
constexpr std::array<ActionDefinition, static_cast<std::size_t>(ActionType::Count)> kDefinitions = {{
    {"use_phone", 25},
    {"shop_on_phone", 20},
    {"use_computer", 30},
    {"study_at_computer", 35},
    {"study_at_desk", 35},
    {"rest_at_bed", 60},
    {"sleep_at_bed", 8 * 60},
    {"go_to_bathroom", 15},
    {"get_meal", 35},
    {"turn_light_on", 1},
    {"turn_light_off", 1},
    {"turn_off_alarm", 1},
    {"open_curtain", 1},
    {"close_curtain", 1},
    {"idle", 10},
}};
} // namespace

const ActionDefinition& action_definition(ActionType action) {
    // ActionType::Count is a sentinel, never a runtime action.
    return kDefinitions.at(static_cast<std::size_t>(action));
}

std::string to_string(ActionType action) {
    return std::string(action_definition(action).name);
}
