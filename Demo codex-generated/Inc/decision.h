#pragma once

#include "action.h"
#include "observation.h"
#include "personality.h"
#include "state.h"
#include "world.h"

#include <random>
#include <string>
#include <vector>

struct CandidateAction {
    ActionType action = ActionType::Idle;
    double activation = 0.0;
    double threshold = 0.0;
    double probability = 0.0;
    bool eligible = false;
    std::string reason;
};

// D: transient decision context. It is recalculated every step and is not
// written back into CharacterState.
struct DecisionContext {
    std::string dominant_need;
    std::string intention_hint;
    std::string intention_status;
    std::vector<ActionType> world_actions; // A^W
    std::vector<ActionType> known_actions; // A^O
    std::vector<CandidateAction> candidates;
};

DecisionContext decide(const Observation& observation,
                       const World& world,
                       const CharacterState& state,
                       const Personality& personality);
ActionType sample_action(const DecisionContext& decision, std::mt19937& rng);
void update_intention(CharacterState& state,
                      ActionType chosen_action);
std::string decision_summary(const DecisionContext& decision);
