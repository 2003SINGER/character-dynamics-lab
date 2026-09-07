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
inline constexpr const char* kReplayCandidateScorerVersion = "replay-neutral-v0";

// Dataset-neutral replay scorer.  It consumes only candidate semantics and an
// explicit policy configuration; it must not depend on RoomDemo state types.
struct ReplayPolicyConfig {
    double task_drive = 0.70;
    double distraction_drive = 0.25;
    double recovery_drive = 0.50;
    double hunger_drive = 0.0;
    double bathroom_drive = 0.0;
    double reward_drive = 0.35;
    double environment_drive = 0.15;
    double context_drive = 0.25;
    double temperature = 0.45;
};

std::vector<ExternalCandidateScore> score_replay_candidates(
    const std::vector<ExternalCandidate>& candidates,
    const ReplayPolicyConfig& config = {});

std::vector<ExternalCandidateScore> score_external_candidates(
    const std::vector<ExternalCandidate>& candidates,
    const CharacterState& state,
    const Personality& personality);
