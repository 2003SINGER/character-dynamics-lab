#include "scene.h"

RoomScene make_default_room() {
    return {{{"phone", "phone", true, {ActionType::UsePhone, ActionType::ShopOnPhone}},
             {"computer", "computer", true, {ActionType::UseComputer, ActionType::StudyAtComputer}},
             {"desk", "desk with study materials", true, {ActionType::StudyAtDesk}},
             {"bed", "bed", true, {ActionType::RestAtBed, ActionType::SleepAtBed}},
             {"door", "room door", true, {ActionType::GoToBathroom, ActionType::GetMeal}},
             {"light", "room light", true, {ActionType::TurnLightOn, ActionType::TurnLightOff}},
             {"alarm", "alarm clock", true, {ActionType::TurnOffAlarm}},
             {"window", "window with curtains", true, {ActionType::OpenCurtain, ActionType::CloseCurtain}}}};
}

const RoomObject* RoomScene::object_for(ActionType action) const {
    for (const RoomObject& object : objects) {
        if (object.usable && provides_action(object, action)) {
            return &object;
        }
    }
    return nullptr;
}
