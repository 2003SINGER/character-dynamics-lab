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
    std::optional<WorldOutcome> outcome;
    std::optional<ActionType> selected_action;
    bool policy_evaluated = false;
};

// Canonical owner for the scheduler-native W -> O incremental handoff.
// State integration and policy remain explicit callers at this stage.
class ContinuousRuntime {
public:
    ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation,
                      InformationAccess access = {});
    bool schedule_next_world_boundary();
    WorldOutcome submit_action_intent(ActionType action, const std::string& target_object_id,
                                      int duration_minutes, bool interruptible = true);
    void invalidate_running_action();
    RuntimeExecutionResult execute_next_boundary(CharacterState& state, const Personality& personality);
    // Test-only deterministic policy override; production keeps seeded sampling.
    void set_test_action_selector(std::function<ActionType(const DecisionContext&)> selector) {
        test_action_selector_ = std::move(selector);
    }

private:
    RuntimeScheduler& scheduler_;
    WorldRuntimeAdapter world_runtime_;
    Observation& observation_;
    InformationAccess access_;
    std::mt19937 rng_{0x43445257U};
    std::function<ActionType(const DecisionContext&)> test_action_selector_;
};
