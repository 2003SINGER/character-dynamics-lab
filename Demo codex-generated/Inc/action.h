#pragma once

#include <string>

enum class ActionType {
    UsePhone,
    UseComputer,
    StudyAtDesk,
    RestAtBed,
    Idle
};

std::string to_string(ActionType action);
