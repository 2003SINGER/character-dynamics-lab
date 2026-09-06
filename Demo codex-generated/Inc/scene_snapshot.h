#pragma once

#include <string>
#include <vector>

// Minimal canonical scene boundary. It stores source/projection evidence and
// deliberately does not prescribe dataset-specific action enums or world rules.
struct SceneEntity {
    std::string id;
    std::string label;
    std::string kind;
    std::string description;
};

struct SceneAffordanceEvidence {
    std::string entity_id;
    std::string action_id;
    std::string status = "not_projected";
    std::string source_ref;
};

struct SceneSnapshot {
    std::string schema_version = "canonical_scene_snapshot_v0";
    std::string dataset;
    std::string trajectory_id;
    int t = 0;
    std::string place;
    std::string actor_id;
    std::vector<SceneEntity> entities;
    std::vector<std::string> actor_inventory;
    std::vector<SceneAffordanceEvidence> affordance_evidence;
    std::string actor_observation;
    std::vector<std::string> source_candidates;
    std::string provenance_ref;
};

struct Scene;
SceneSnapshot project_room_scene(const Scene& scene,
                                 const std::string& room_id,
                                 const std::string& actor_id);
