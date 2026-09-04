#pragma once

#include "action.h"
#include "appraisal.h"
#include "personality.h"

#include <string>

// Placeholder for a future goal/intention module. It is deliberately small:
// it can bias repeated study choices, but does not claim to model planning.
struct PersistentIntention {
    bool active = false;
    ActionType action = ActionType::Idle;
    std::string reason;
    int remaining_decision_points = 0;
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
    PersistentIntention intention;
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

StateDelta update_state(CharacterState& state,
                        const Appraisal& appraisal,
                        const Personality& personality,
                        int elapsed_minutes);
std::string state_summary(const CharacterState& state);
std::string state_delta_summary(const StateDelta& delta);
