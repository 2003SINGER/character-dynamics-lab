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

// Self-action feedback is part of O too. It stays typed rather than being
// encoded as a string fact, but carries the same provenance boundary.
struct ObservedAction {
    bool has_action = false;
    ActionType action = ActionType::Idle;
    bool accepted = false;
    std::string outcome_reason;
    std::string source = "self_action_feedback";
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
    // A sensory update can occur during a long action after the current
    // decision has already been made. Keep it until the next X update.
    std::vector<ObservationFact> pending_appraisal_updates;
    ObservedAction last_self_action;
};

const ObservationFact* find_fact(const Observation& observation, const std::string& key);
bool has_known_fact(const Observation& observation, const std::string& key, const std::string& value);
Observation refresh_observation(Observation previous,
                                const World& world,
                                const WorldOutcome& previous_outcome);
bool observation_knows_action(const Observation& observation, ActionType action);
Observation apply_sleep_sensory_update(Observation previous,
                                       const WorldOutcome& outcome,
                                       const World& world);
void clear_pending_appraisal_updates(Observation& observation);
std::string observation_updates_summary(const Observation& observation);
std::string observation_summary(const Observation& observation);
