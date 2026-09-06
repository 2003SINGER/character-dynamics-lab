#pragma once

#include "personality.h"
#include "state.h"

#include <string>
#include <vector>

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

struct ExternalCandidate {
    std::string id;
    CandidateSemantics semantics;
    double bias = 0.0;
};

struct ExternalCandidateScore {
    std::string id;
    double activation = 0.0;
    double probability = 0.0;
};

inline constexpr const char* kExternalCandidateScorerVersion = "drive-linear-v0";

std::vector<ExternalCandidateScore> score_external_candidates(
    const std::vector<ExternalCandidate>& candidates,
    const CharacterState& state,
    const Personality& personality);
