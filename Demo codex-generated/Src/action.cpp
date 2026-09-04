#include "action.h"

std::string to_string(ActionType action) {
    switch (action) {
    case ActionType::UsePhone:
        return "use_phone";
    case ActionType::ShopOnPhone:
        return "shop_on_phone";
    case ActionType::UseComputer:
        return "use_computer";
    case ActionType::StudyAtComputer:
        return "study_at_computer";
    case ActionType::StudyAtDesk:
        return "study_at_desk";
    case ActionType::RestAtBed:
        return "rest_at_bed";
    case ActionType::SleepAtBed:
        return "sleep_at_bed";
    case ActionType::GoToBathroom:
        return "go_to_bathroom";
    case ActionType::GetMeal:
        return "get_meal";
    case ActionType::TurnLightOn:
        return "turn_light_on";
    case ActionType::TurnLightOff:
        return "turn_light_off";
    case ActionType::TurnOffAlarm:
        return "turn_off_alarm";
    case ActionType::OpenCurtain:
        return "open_curtain";
    case ActionType::CloseCurtain:
        return "close_curtain";
    case ActionType::Idle:
        return "idle";
    }
    return "unknown_action";
}
