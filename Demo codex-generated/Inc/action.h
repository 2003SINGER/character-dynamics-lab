#pragma once

#include <string>

enum class ActionType {
    UsePhone,
    UseComputer,
    StudyAtDesk,
    RestAtBed,
    GoToBathroom,
    GetMeal,
    Idle
};

std::string to_string(ActionType action);
