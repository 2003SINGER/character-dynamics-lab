#pragma once

#include "observation.h"
#include "runtime_scheduler.h"
#include "world_runtime_adapter.h"
#include "appraisal.h"
#include "decision.h"
#include "state.h"
#include "runtime_config.h"
#include "character_dynamics_model.h"
#include "character_policy.h"
#include <random>
#include <functional>

struct ContinuousRuntimeStep {
    RuntimeBoundary boundary;
    std::vector<WorldEvent> world_events;
};

struct RuntimeExecutionResult {
    ContinuousRuntimeStep runtime;
    std::optional<RunningAction> running_action_before;
    std::optional<RunningAction> running_action_after;
    StateUpdate continuous_state;
    StateUpdate impulse_state;
    Appraisal appraisal;
    DecisionContext decision;
    // Pre-policy inputs (completion, physical interruption, delivered rejection).
    std::optional<WorldOutcome> pre_policy_outcome;
    // Policy-generated transition result; consumed on the next boundary.
    std::optional<WorldOutcome> post_policy_outcome;
    std::optional<ActionType> selected_action;
    std::string selected_target_object_id;
    bool replacement_validation_performed = false;
    bool replacement_validation_accepted = false;
    std::string dynamics_reconsideration_reason;
    unsigned int policy_seed = 0;
    std::vector<ObservationFact> observation_deltas;
    bool policy_evaluated = false;
    std::string policy_id;
    std::string policy_selection_provenance;
    std::vector<std::pair<ActionType, double>> sampled_policy_probabilities;
};

// Canonical owner for Continuous Runtime v1: it advances time, integrates
// continuous S, projects W/events into O, appraises X/S, gates policy, and
// submits every new ActionIntent through W validation.
class ContinuousRuntime {
public:
    ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation,
                      CharacterDynamicsModel& model, InformationAccess access = {},
                      unsigned int policy_seed = RuntimeConfig::DefaultPolicySeed,
                      CharacterPolicy* policy = nullptr);
    bool schedule_next_world_boundary();
    WorldOutcome submit_action_intent(ActionType action, const std::string& target_object_id,
                                      int duration_minutes, bool interruptible = true);
    void invalidate_running_action();
    RuntimeExecutionResult execute_next_boundary(CharacterState& state, const Personality& personality);
    // Test-only deterministic policy override; production keeps seeded sampling.
    void set_test_action_selector(std::function<ActionType(const DecisionContext&)> selector) {
        test_action_selector_ = std::move(selector);
    }
    unsigned int policy_seed() const { return policy_seed_; }
    // Experiment fork support: preserve the exact policy RNG position when
    // cloning a Runtime checkpoint; no policy law or production path changes.
    std::mt19937 policy_rng_state() const { return rng_; }
    void restore_policy_rng_state(const std::mt19937& state) { rng_=state; }

private:
    RuntimeScheduler& scheduler_;
    WorldRuntimeAdapter world_runtime_;
    Observation& observation_;
    CharacterDynamicsModel& model_;
    RulePolicyV0 default_policy_;
    CharacterPolicy* policy_ = nullptr;
    InformationAccess access_;
    std::mt19937 rng_;
    unsigned int policy_seed_ = 0;
    std::function<ActionType(const DecisionContext&)> test_action_selector_;
};
