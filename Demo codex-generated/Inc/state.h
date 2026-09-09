#pragma once

#include "appraisal.h"
#include "personality.h"
#include "state_types.h"
#include "parameter_config.h"

#include <string>

// A persistent task-level commitment. It preserves the direction of an
// unfinished task across individual actions without turning actions into a
// multi-step script.
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

// semantic_contribution is the explicit U(X,P) contribution. requested then
// adds legacy/demo direct deltas and time dynamics; applied is post-clamp.
struct StateUpdate {
    StateDelta semantic_contribution;
    StateDelta requested;
    StateDelta applied;
};

StateUpdate update_state(CharacterState& state,
                         const Appraisal& appraisal,
                         const Personality& personality,
                         int elapsed_minutes,
                         const ParameterConfig& config = ParameterConfig::defaults());
std::string state_summary(const CharacterState& state);
std::string state_delta_summary(const StateDelta& delta);
std::string state_update_summary(const StateUpdate& update);
