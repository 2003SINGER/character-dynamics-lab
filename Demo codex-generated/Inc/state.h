#pragma once

#include "appraisal.h"
#include "personality.h"

#include <string>

struct CharacterState {
    double boredom = 0.55;
    double fatigue = 0.15;
    double task_pressure = 0.55;
    double satisfaction = 0.45;
};

struct StateDelta {
    double boredom = 0.0;
    double fatigue = 0.0;
    double task_pressure = 0.0;
    double satisfaction = 0.0;
};

StateDelta update_state(CharacterState& state,
                        const Appraisal& appraisal,
                        const Personality& personality);
std::string state_summary(const CharacterState& state);
std::string state_delta_summary(const StateDelta& delta);
