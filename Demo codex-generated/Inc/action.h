#pragma once

#include <string>

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
    Idle
};

std::string to_string(ActionType action);
