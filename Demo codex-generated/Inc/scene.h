#pragma once

#include "object.h"

#include <string>
#include <vector>

// A Room is a scene-contained location object. Its object container holds the
// concrete things inside it (phone, bed, desk, ...), while its other fields
// are local physical conditions rather than character psychology.
struct Room {
    std::string id;
    std::string label;
    std::vector<Object> objects;
    bool light_on = true;
    bool alarm_ringing = false;
    bool curtain_open = true;
    double temperature_celsius = 23.0;

    const Object* object_for(ActionType action) const;
};

// Scene is the local W boundary for observation candidates and A^W. A Scene
// contains location objects such as Room; a Room in turn contains Objects.
struct Scene {
    std::string id;
    std::string label;
    std::vector<Room> rooms;

    Room* room_by_id(const std::string& room_id);
    const Room* room_by_id(const std::string& room_id) const;
};

Scene make_default_scene();
