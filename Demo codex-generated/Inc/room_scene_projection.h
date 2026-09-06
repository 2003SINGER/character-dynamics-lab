#pragma once

#include "scene_snapshot.h"

#include <string>

struct Scene;
SceneSnapshot project_room_scene(const Scene& scene,
                                 const std::string& room_id,
                                 const std::string& actor_id);
