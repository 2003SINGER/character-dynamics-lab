#pragma once

#include <string>
#include <string_view>

enum class ActionType {
    UsePhone,
    ShopOnPhone,
    UseComputer,
    StudyAtComputer,
    StudyAtDesk,
    RestAtBed,
    SleepAtBed,
    GoToBathroom,
    GetMeal,
    TurnLightOn,
    TurnLightOff,
    TurnOffAlarm,
    OpenCurtain,
    CloseCurtain,
    Idle,
    Count
};

struct ActionDefinition {
    std::string_view name;
    int default_duration_minutes = 0;
};

const ActionDefinition& action_definition(ActionType action);
std::string to_string(ActionType action);
