#pragma once

#include "action.h"
#include "world.h"

#include <string>
#include <vector>

namespace FactKey {
inline constexpr const char* WalletBalance = "wallet.balance";
inline constexpr const char* RoomLight = "room.light";
inline constexpr const char* RoomCurtain = "room.curtain";
inline constexpr const char* RoomAlarm = "room.alarm";
inline constexpr const char* RoomTemperature = "room.temperature_celsius";
inline constexpr const char* ClockTime = "clock.time";
inline constexpr const char* MessageUnreadCount = "message.unread_count";
}

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
    std::string task_id;
    bool task_completed = false;
    std::string outcome_reason;
    std::string source = "self_action_feedback";
    std::string observed_at;
};

// Scenario-level information policy. False means the fact remains a hidden W
// condition and can only be learned through an observed feedback path.
struct InformationAccess {
    bool self_task_completion_observable = true;
    bool wallet_balance_observable = false;
    bool object_usability_observable = false;
    bool phone_presence_observable = true;
    bool task_deadline_observable = true;
};

// Stable affordance knowledge belongs to O. It is deliberately separate from
// current W object presence/usability, which may change before discovery.
struct KnownObjectAffordance {
    std::string id;
    std::vector<ActionType> affordances;
};
struct ActionTargetBinding { ActionType action = ActionType::Idle; std::string target_object_id; };

// A failed direct attempt is evidence available to the actor, but it must not
// reveal the hidden W value that caused the rejection.  This is intentionally
// separate from ordinary facts: it records a bounded "do not retry this yet"
// belief, keyed by the attempted action and target, until an appropriate O
// update can invalidate it.
enum class ActionConstraintType {
    TargetAbsent,
    TargetUnusable,
    ResourceRequirement,
    Precondition
};

struct ActionConstraintBelief {
    ActionType action = ActionType::Idle;
    std::string target_object_id;
    ActionConstraintType constraint = ActionConstraintType::Precondition;
    bool satisfied = false;
    std::string source;
    std::string observed_at;
};

// O: a separately stored character-side view, even though this one-room
// reference refreshes all visible fields deterministically.
struct Observation {
    std::vector<std::string> visible_object_labels;
    std::vector<std::string> known_object_ids;
    std::vector<KnownObjectAffordance> known_object_affordances;
    std::vector<ActionTargetBinding> action_target_bindings;
    std::vector<ActionType> known_actions; // A^O, not W's full action set.
    std::vector<ActionConstraintBelief> action_constraints;
    std::vector<ObservationFact> facts;
    std::vector<ObservationFact> updates_this_refresh;
    // A sensory update can occur during a long action after the current
    // decision has already been made. Keep it until the next X update.
    std::vector<ObservationFact> pending_appraisal_updates;
    ObservedAction last_self_action;
};

const ObservationFact* find_fact(const Observation& observation, const std::string& key);
bool has_known_fact(const Observation& observation, const std::string& key, const std::string& value);
bool known_bool(const Observation& observation, const std::string& key, bool& value);
bool known_int(const Observation& observation, const std::string& key, int& value);
bool known_double(const Observation& observation, const std::string& key, double& value);
Observation refresh_observation(Observation previous,
                                const World& world,
                                const WorldOutcome& previous_outcome,
                                const InformationAccess& access = {});
// This is the only W-outcome -> O bridge for a character's own completed
// action. Callers may deliberately withhold completion confirmation to model
// a task whose actual settlement is not yet observable to the character.
void apply_self_action_feedback(Observation& observation,
                                const WorldOutcome& outcome,
                                const std::string& observed_at,
                                bool completion_is_observable = true);
// Project an already-authorized observable runtime event into O. The caller
// supplies only the event payload the actor can perceive; this function never
// reads W. The scheduler-native caller appraises the resulting Delta-O at the
// same runtime boundary.
void apply_observable_runtime_event(Observation& observation,
                                    std::string key,
                                    std::string value,
                                    std::string source,
                                    const std::string& observed_at);
bool observation_knows_action(const Observation& observation, ActionType action);
Observation apply_sleep_sensory_update(Observation previous,
                                       const WorldOutcome& outcome,
                                       const World& world);
void clear_pending_appraisal_updates(Observation& observation);
std::string observation_updates_summary(const Observation& observation);
std::string observation_summary(const Observation& observation);
