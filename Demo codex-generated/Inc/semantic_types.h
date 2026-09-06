#pragma once

#include <string>

// Dataset-neutral semantic input. This header intentionally has no dependency
// on ActionType, Observation, World, or the Room demo.
struct CandidateSemantics {
    double goal_progress = 0.0;
    double stimulation = 0.0;
    double recovery = 0.0;
    double hunger_relief = 0.0;
    double bathroom_relief = 0.0;
    double short_term_reward = 0.0;
    double environment_control = 0.0;
    double context_relevance = 0.0;
};

struct AppraisalSignalInput {
    std::string kind;
    double intensity = 0.0;
    double goal_relevance = 0.0;
    double goal_congruence = 0.0;
    double controllability = 0.0;
    std::string source;
};
