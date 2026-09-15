#pragma once

#include "observation.h"
#include "runtime_scheduler.h"
#include "world_runtime_adapter.h"
#include "appraisal.h"
#include "decision.h"
#include "state.h"
#include <random>
#include <functional>

struct ContinuousRuntimeStep {
    RuntimeBoundary boundary;
    std::vector<WorldEvent> world_events;
};

struct RuntimeExecutionResult {
    ContinuousRuntimeStep runtime;
    StateUpdate continuous_state;
    StateUpdate impulse_state;
    Appraisal appraisal;
    DecisionContext decision;
    // Pre-policy inputs (completion, physical interruption, delivered rejection).
    std::optional<WorldOutcome> pre_policy_outcome;
    // Policy-generated transition result; consumed on the next boundary.
    std::optional<WorldOutcome> post_policy_outcome;
    // Deprecated compatibility alias for callers being migrated.
    std::optional<WorldOutcome> outcome;
    std::optional<ActionType> selected_action;
    std::string selected_target_object_id;
    bool replacement_validation_performed = false;
    bool replacement_validation_accepted = false;
    unsigned int policy_seed = 0;
    bool policy_evaluated = false;
};

// Canonical owner for Continuous Runtime v1: it advances time, integrates
// continuous S, projects W/events into O, appraises X/S, gates policy, and
// submits every new ActionIntent through W validation.
class ContinuousRuntime {
public:
    ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation,
                      InformationAccess access = {}, unsigned int policy_seed = 0x43445257U);
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

private:
    RuntimeScheduler& scheduler_;
    WorldRuntimeAdapter world_runtime_;
    Observation& observation_;
    InformationAccess access_;
    std::mt19937 rng_;
    unsigned int policy_seed_ = 0;
    std::function<ActionType(const DecisionContext&)> test_action_selector_;
};
