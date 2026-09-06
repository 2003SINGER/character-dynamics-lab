#pragma once

#include "semantic_types.h"
#include "personality.h"
#include "state_types.h"

#include <string>
#include <vector>

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
