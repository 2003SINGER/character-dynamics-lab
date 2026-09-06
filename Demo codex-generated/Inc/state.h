#pragma once

#include "action.h"
#include "appraisal.h"
#include "personality.h"

#include <string>

// A persistent task-level commitment. It preserves the direction of an
// unfinished task across individual actions without turning actions into a
// multi-step script.
enum class CommitmentStatus {
    None,
    Active,
    Suspended
};

struct TaskCommitment {
    CommitmentStatus status = CommitmentStatus::None;
    std::string task_id;
    std::string reason;
    int started_at_total_minutes = -1;
    int suspended_decision_points = 0;
};

struct CharacterState {
    double boredom = 0.55;
    double fatigue = 0.15;
    double task_pressure = 0.55;
    double satisfaction = 0.45;
    double hunger = 0.25;
    double bathroom_urge = 0.15;
    double anxiety = 0.20;
    double screen_strain = 0.05;
    double purchase_urge = 0.10;
    TaskCommitment commitment;
};

struct StateDelta {
    double boredom = 0.0;
    double fatigue = 0.0;
    double task_pressure = 0.0;
    double satisfaction = 0.0;
    double hunger = 0.0;
    double bathroom_urge = 0.0;
    double anxiety = 0.0;
    double screen_strain = 0.0;
    double purchase_urge = 0.0;
    int elapsed_minutes = 0;
};

// Requested is the model's unconstrained update; applied is the actual
// before/after difference after W-independent range constraints.  Logging
// both prevents provenance from claiming an impossible state transition.
struct StateUpdate {
    StateDelta semantic_contribution;
    StateDelta requested;
    StateDelta applied;
};

StateUpdate update_state(CharacterState& state,
                        const Appraisal& appraisal,
                        const Personality& personality,
                        int elapsed_minutes);
std::string state_summary(const CharacterState& state);
std::string state_delta_summary(const StateDelta& delta);
std::string state_update_summary(const StateUpdate& update);
