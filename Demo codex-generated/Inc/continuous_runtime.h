#pragma once

#include "observation.h"
#include "runtime_scheduler.h"
#include "world_runtime_adapter.h"
#include "appraisal.h"
#include "decision.h"
#include "state.h"

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
    ContinuousRuntimeStep advance_next_boundary();
    RuntimeExecutionResult execute_next_boundary(CharacterState& state, const Personality& personality);

private:
    RuntimeScheduler& scheduler_;
    WorldRuntimeAdapter world_runtime_;
    Observation& observation_;
    InformationAccess access_;
};
