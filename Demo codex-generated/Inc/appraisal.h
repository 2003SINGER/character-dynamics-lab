#pragma once

#include "observation.h"

#include <string>
#include <vector>

enum class AppraisalSignalKind { GoalCompletion };
struct AppraisalSignal {
    AppraisalSignalKind kind = AppraisalSignalKind::GoalCompletion;
    double intensity = 0.0;
    double goal_relevance = 0.0;
    double goal_congruence = 0.0;
    double controllability = 0.0;
    std::string source;
};

// X: structured meaning of the observed world change. These values are
// illustrative rules, not claims about real psychology.
struct Appraisal {
    double boredom_delta = 0.0;
    double fatigue_delta = 0.0;
    double task_pressure_delta = 0.0;
    double satisfaction_delta = 0.0;
    double hunger_delta = 0.0;
    double bathroom_urge_delta = 0.0;
    double anxiety_delta = 0.0;
    double screen_strain_delta = 0.0;
    double purchase_urge_delta = 0.0;
    std::vector<AppraisalSignal> semantic_signals;
    std::vector<std::string> tags;
};

struct CharacterState;
struct Personality;

Appraisal appraise(const Observation& observation,
                   const CharacterState& old_state,
                   const Personality& personality);
std::string appraisal_summary(const Appraisal& appraisal);
const char* appraisal_signal_name(AppraisalSignalKind kind);
