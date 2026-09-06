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

struct ScenePossession {
    std::string actor;
    std::string entity;
    std::string relation;
};

struct SceneSnapshot {
    std::string schema_version = "canonical_scene_snapshot_v0";
    std::string dataset;
    std::string trajectory_id;
    int t = 0;
    std::string place;
    std::string setting;
    std::string actor;
    std::vector<SceneEntity> entities;
    std::vector<ScenePossession> possessions;
    std::vector<SceneAffordanceEvidence> affordance_evidence;
    std::string actor_observation;
    std::vector<std::string> source_candidates;
    std::string provenance_ref;
};
