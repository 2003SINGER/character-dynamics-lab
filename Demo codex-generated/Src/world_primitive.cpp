#include "world_primitive.h"

#include <sstream>
#include <type_traits>

namespace {
const char* to_string(WorldCounter counter) {
    switch (counter) {
    case WorldCounter::PhoneUses: return "phone_uses";
    case WorldCounter::ComputerUses: return "computer_uses";
    case WorldCounter::StudySessions: return "study_sessions";
    case WorldCounter::RestSessions: return "rest_sessions";
    case WorldCounter::BathroomVisits: return "bathroom_visits";
    case WorldCounter::MealsCollected: return "meals_collected";
    case WorldCounter::OnlineOrders: return "online_orders";
    }
    return "unknown_counter";
}

const char* to_string(WorldValue value) {
    switch (value) {
    case WorldValue::Wallet: return "wallet";
    case WorldValue::TaskProgress: return "task_progress";
    }
    return "unknown_value";
}

const char* to_string(RoomFlag flag) {
    switch (flag) {
    case RoomFlag::LightOn: return "room.light_on";
    case RoomFlag::AlarmRinging: return "room.alarm_ringing";
    case RoomFlag::CurtainOpen: return "room.curtain_open";
    }
    return "unknown_room_flag";
}
} // namespace

std::string world_primitive_summary(const WorldPrimitive& primitive) {
    std::ostringstream output;
    output << primitive.id << ':';
    std::visit([&output](const auto& payload) {
        using Payload = std::decay_t<decltype(payload)>;
        if constexpr (std::is_same_v<Payload, SetCurrentActivity>) {
            output << "set_activity(" << to_string(payload.action) << ')';
        } else if constexpr (std::is_same_v<Payload, IncrementWorldCounter>) {
            output << "increment(" << to_string(payload.counter) << ',' << payload.amount << ')';
        } else if constexpr (std::is_same_v<Payload, AdjustWorldValue>) {
            output << "adjust(" << to_string(payload.value) << ',' << payload.amount << ')';
        } else if constexpr (std::is_same_v<Payload, SetRoomFlag>) {
            output << "set(" << to_string(payload.flag) << ',' << (payload.value ? "true" : "false") << ')';
        } else if constexpr (std::is_same_v<Payload, AdvanceSimulationTime>) {
            output << "advance_time(" << payload.minutes << "m)";
        }
    }, primitive.payload);
    return output.str();
}

std::string world_primitives_summary(const std::vector<WorldPrimitive>& primitives) {
    std::ostringstream output;
    output << "[";
    for (std::size_t index = 0; index < primitives.size(); ++index) {
        output << world_primitive_summary(primitives[index]);
        if (index + 1 < primitives.size()) {
            output << ", ";
        }
    }
    output << "]";
    return output.str();
}
