#include "action.h"

std::string to_string(ActionType action) {
    switch (action) {
    case ActionType::UsePhone:
        return "use_phone";
    case ActionType::UseComputer:
        return "use_computer";
    case ActionType::StudyAtDesk:
        return "study_at_desk";
    case ActionType::RestAtBed:
        return "rest_at_bed";
    case ActionType::Idle:
        return "idle";
    }
    return "unknown_action";
}
