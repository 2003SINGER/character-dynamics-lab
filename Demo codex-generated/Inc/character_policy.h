#pragma once

#include "decision.h"
#include "actor_history.h"

#include <random>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// Policy selection is distinct from the Runtime and Dynamics model. A policy
// only receives O/S/P and the model-generated, O-legal candidate surface.
// It cannot inspect World or submit a primitive.
struct PolicySelection {
    ActionType action = ActionType::Idle;
    std::string policy_id;
    std::string provenance;
    std::vector<std::pair<ActionType, double>> probabilities;
};

struct SoftReconsideration {
    double probability = 0.0;
    bool requested = false;
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
    virtual PolicySelection select_with_history(const DecisionContext& decision,
                                   const Observation& observation, const CharacterState& state,
                                   const Personality& personality, const ActorHistory&,
                                   const RunningAction*, std::mt19937& rng) {
        return select(decision, observation, state, personality, rng);
    }
    virtual const char* identity() const = 0;
    // Optional subjective gate. This can only add a reconsideration; hard
    // Runtime gates remain authoritative and cannot be closed by a policy.
    virtual std::optional<SoftReconsideration> soft_reconsider(
        const Observation&, const CharacterState&, const Personality&,
        const RunningAction&, std::mt19937&) { return std::nullopt; }
    virtual std::optional<SoftReconsideration> soft_reconsider_with_history(
        const Observation& observation, const CharacterState& state, const Personality& personality,
        const RunningAction& action, const ActorHistory&, std::mt19937& rng) {
        return soft_reconsider(observation, state, personality, action, rng);
    }
};

class RulePolicyV0 final : public CharacterPolicy {
public:
    PolicySelection select(const DecisionContext& decision, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937& rng) override {
        PolicySelection selection{sample_action(decision, rng), identity(), "seeded_sample_from_model_decision", {}};
        for (const CandidateAction& candidate : decision.candidates)
            if (candidate.eligible)
                selection.probabilities.emplace_back(candidate.action, candidate.probability);
        return selection;
    }
    const char* identity() const override { return "rule-policy-v0"; }
};
