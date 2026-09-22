#pragma once

#include "decision.h"

#include <random>
#include <string>

// Policy selection is distinct from the Runtime and Dynamics model. A policy
// only receives O/S/P and the model-generated, O-legal candidate surface.
// It cannot inspect World or submit a primitive.
struct PolicySelection {
    ActionType action = ActionType::Idle;
    std::string policy_id;
    std::string provenance;
};

class CharacterPolicy {
public:
    virtual ~CharacterPolicy() = default;
    virtual PolicySelection select(const DecisionContext& decision,
                                   const Observation& observation,
                                   const CharacterState& state,
                                   const Personality& personality,
                                   std::mt19937& rng) = 0;
    virtual const char* identity() const = 0;
};

class RulePolicyV0 final : public CharacterPolicy {
public:
    PolicySelection select(const DecisionContext& decision, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937& rng) override {
        return {sample_action(decision, rng), identity(), "seeded_sample_from_model_decision"};
    }
    const char* identity() const override { return "rule-policy-v0"; }
};
