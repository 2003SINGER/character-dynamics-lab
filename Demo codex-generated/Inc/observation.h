#pragma once

#include "action.h"
#include "world.h"

#include <string>
#include <vector>

enum class KnowledgeStatus {
    Known,
    Stale,
    Unknown
};

// A field in persistent O. Future scenes/messages/memory can write the same
// record shape with a different source without changing the policy interface.
struct ObservationFact {
    std::string key;
    std::string value;
    KnowledgeStatus status = KnowledgeStatus::Unknown;
    std::string source;
    std::string observed_at;
};

// O: a separately stored character-side view, even though this one-room
// reference refreshes all visible fields deterministically.
struct Observation {
    std::vector<std::string> visible_object_labels;
    std::vector<std::string> known_object_ids;
    std::vector<ActionType> known_actions; // A^O, not W's full action set.
    std::vector<ObservationFact> facts;
    std::vector<ObservationFact> updates_this_refresh;
    bool light_known_on = true;
    int known_task_progress = 0;
    int known_unread_messages = 0;
    std::string observed_time;
    ActionType observed_last_action = ActionType::Idle;
};

Observation refresh_observation(Observation previous,
                                const World& world,
                                const WorldOutcome& previous_outcome);
bool observation_knows_action(const Observation& observation, ActionType action);
std::string observation_summary(const Observation& observation);
