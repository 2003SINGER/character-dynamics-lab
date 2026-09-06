#pragma once
#include "personality.h"
#include "state.h"
#include <string>
#include <vector>
struct CandidateSemantics { double goal_progress=0, stimulation=0, recovery=0, hunger_relief=0, bathroom_relief=0, short_term_reward=0, environment_control=0; };
struct ExternalCandidate { std::string id; CandidateSemantics semantics; double bias=0; };
struct ExternalCandidateScore { std::string id; double activation=0, probability=0; };
std::vector<ExternalCandidateScore> score_external_candidates(const std::vector<ExternalCandidate>&, const CharacterState&, const Personality&);
