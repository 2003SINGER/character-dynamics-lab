#include "room_scene_projection.h"

#include "scene.h"

SceneSnapshot project_room_scene(const Scene& scene,
                                 const std::string& room_id,
                                 const std::string& actor_id) {
    SceneSnapshot snapshot;
    snapshot.dataset = "RoomDemo";
    snapshot.actor = actor_id;
    const Room* room = scene.room_by_id(room_id);
    if (!room) return snapshot;
    snapshot.place = room->label;
    snapshot.setting = room->label;
    for (const Object& object : room->objects) {
        snapshot.entities.push_back({object.id, object.label, "object", {}});
        for (ActionType action : object.affordances) {
            snapshot.affordance_evidence.push_back({
                object.id, to_string(action), "room_demo_projected", "RoomDemo:" + object.id
            });
        }
    }
    return snapshot;
}
