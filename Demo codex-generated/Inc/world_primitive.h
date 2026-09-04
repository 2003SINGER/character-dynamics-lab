#pragma once

#include "action.h"

#include <string>
#include <variant>
#include <vector>

// These are the small, typed world operations that a character-level action
// can expand into. New scenarios may add their own primitive kind without
// giving policy permission to mutate W directly.
enum class WorldCounter {
    PhoneUses,
    ComputerUses,
    StudySessions,
    RestSessions,
    BathroomVisits,
    MealsCollected,
    OnlineOrders
};

enum class WorldValue {
    Wallet,
    TaskProgress
};

enum class RoomFlag {
    LightOn,
    AlarmRinging,
    CurtainOpen
};

struct SetCurrentActivity {
    ActionType action = ActionType::Idle;
};

struct IncrementWorldCounter {
    WorldCounter counter = WorldCounter::PhoneUses;
    int amount = 1;
};

struct AdjustWorldValue {
    WorldValue value = WorldValue::Wallet;
    int amount = 0;
};

struct SetRoomFlag {
    RoomFlag flag = RoomFlag::LightOn;
    bool value = false;
};

struct AdvanceSimulationTime {
    int minutes = 0;
};

using WorldPrimitivePayload = std::variant<SetCurrentActivity,
                                           IncrementWorldCounter,
                                           AdjustWorldValue,
                                           SetRoomFlag,
                                           AdvanceSimulationTime>;

struct WorldPrimitive {
    std::string id;
    std::string description;
    WorldPrimitivePayload payload;
};

// The boundary between a chosen A^char and W settlement. A plan is only a
// proposal; World::settle revalidates it against the current W.
struct CharacterActionPlan {
    ActionType action = ActionType::Idle;
    std::vector<WorldPrimitive> world_primitives;
};

std::string world_primitive_summary(const WorldPrimitive& primitive);
std::string world_primitives_summary(const std::vector<WorldPrimitive>& primitives);
