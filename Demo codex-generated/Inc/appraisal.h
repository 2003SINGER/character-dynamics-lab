#pragma once

#include "observation.h"

#include <string>
#include <vector>

// X vocabulary. A field may legitimately be present but have no effect in a
// particular scene. That is an explicit no-op, not a missing mechanism slot.
enum class AppraisalSignalKind {
    GoalProgress,
    GoalCompletion,
    GoalObstruction,
    Stimulation,
    Recovery,
    ShortTermReward,
    EnvironmentControl
};

struct AppraisalSignal {
    AppraisalSignalKind kind = AppraisalSignalKind::GoalProgress;
    double intensity = 0.0;
    double goal_relevance = 0.0;
    double goal_congruence = 0.0;
    double controllability = 0.0; // intentionally a no-op in updater v0
    std::string source;
};

// X: structured meaning of observed change. Numeric *_delta fields remain as
// legacy/demo channels while semantic slices are migrated incrementally.
struct Appraisal {
    double boredom_delta = 0.0;
    double fatigue_delta = 0.0;
    double task_pressure_delta = 0.0;
    double deadline_pressure_contribution = 0.0;
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
