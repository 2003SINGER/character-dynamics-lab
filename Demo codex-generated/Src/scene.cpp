#include "scene.h"

#include <algorithm>

Scene make_default_scene() {
    Scene scene;
    scene.id = "home";
    scene.label = "home";
    scene.rooms.push_back({"room", "student room",
        {{"phone", "phone", true, {ActionType::UsePhone, ActionType::ShopOnPhone}},
         {"computer", "computer", true, {ActionType::UseComputer, ActionType::StudyAtComputer}},
         {"desk", "desk with study materials", true, {ActionType::StudyFocused, ActionType::StudyHalfhearted}},
         {"bed", "bed", true, {ActionType::RestAtBed, ActionType::SleepAtBed}},
         {"door", "room door", true, {ActionType::GoToBathroom, ActionType::GetMeal}},
         {"light", "room light", true, {ActionType::TurnLightOn, ActionType::TurnLightOff}},
         {"alarm", "alarm clock", true, {ActionType::TurnOffAlarm}},
         {"window", "window with curtains", true, {ActionType::OpenCurtain, ActionType::CloseCurtain}}}});
    return scene;
}

const Object* Room::object_for(ActionType action) const {
    for (const Object& object : objects) {
        if (object.usable && provides_action(object, action)) {
            return &object;
        }
    }
    return nullptr;
}

Room* Scene::room_by_id(const std::string& room_id) {
    const auto found = std::find_if(rooms.begin(), rooms.end(),
        [&room_id](const Room& room) { return room.id == room_id; });
    return found == rooms.end() ? nullptr : &*found;
}

const Room* Scene::room_by_id(const std::string& room_id) const {
    const auto found = std::find_if(rooms.begin(), rooms.end(),
        [&room_id](const Room& room) { return room.id == room_id; });
    return found == rooms.end() ? nullptr : &*found;
}
