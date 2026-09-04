#pragma once

#include <string>

enum class ActionType {
    UsePhone,
    ShopOnPhone,
    UseComputer,
    StudyAtComputer,
    StudyAtDesk,
    RestAtBed,
    GoToBathroom,
    GetMeal,
    TurnLightOn,
    TurnLightOff,
    Idle
};

std::string to_string(ActionType action);
