#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"

#include <algorithm>

namespace {
bool has_reason(const RuntimeExecutionResult& result, DecisionGateReason reason) {
    return std::find(result.runtime.boundary.decision_gate.reasons.begin(),
                     result.runtime.boundary.decision_gate.reasons.end(), reason)
        != result.runtime.boundary.decision_gate.reasons.end();
}
}

int main() {
    Personality personality;
    DemoLivingDynamicsV1 dynamics;

    // A long sleep is reconsidered as soon as fatigue crosses its V1
    // satiation boundary; selecting the same action preserves elapsed work.
    World sleep_world;
    Observation sleep_o = refresh_observation({}, sleep_world, {});
    RuntimeScheduler sleep_scheduler(total_minutes(sleep_world.time), 60);
    ContinuousRuntime sleep_runtime(sleep_scheduler, sleep_world, sleep_o, dynamics);
    CharacterState sleep_state;
    sleep_state.fatigue = .60;
    sleep_runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::SleepAtBed; });
    if (!sleep_runtime.submit_action_intent(ActionType::SleepAtBed, "bed", 480).accepted) return 1;
    const RuntimeExecutionResult first = sleep_runtime.execute_next_boundary(sleep_state, personality);
    const RuntimeExecutionResult second = sleep_runtime.execute_next_boundary(sleep_state, personality);
    if (!has_reason(second, DecisionGateReason::DynamicsReconsideration)
        || second.dynamics_reconsideration_reason != "sleep_recovery_satisfied"
        || !second.policy_evaluated || !second.running_action_after.has_value()
        || second.running_action_after->action != ActionType::SleepAtBed
        || second.running_action_after->elapsed_minutes <= first.running_action_after->elapsed_minutes) return 2;
    int observed_clock = -1;
    if (!known_int(sleep_o, "clock.total_minutes", observed_clock)
        || observed_clock != sleep_scheduler.now_total_minutes()) return 3;

    // A later urgent crossing is not swallowed after the older .40 gate: it
    // causes another policy opportunity and can replace the long action.
    World urgent_world;
    Observation urgent_o = refresh_observation({}, urgent_world, {});
    RuntimeScheduler urgent_scheduler(total_minutes(urgent_world.time), 60);
    ContinuousRuntime urgent_runtime(urgent_scheduler, urgent_world, urgent_o, dynamics);
    CharacterState urgent_state;
    urgent_state.hunger = .91;
    urgent_runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::GetMeal; });
    if (!urgent_runtime.submit_action_intent(ActionType::SleepAtBed, "bed", 480).accepted) return 4;
    const RuntimeExecutionResult urgent = urgent_runtime.execute_next_boundary(urgent_state, personality);
    if (!has_reason(urgent, DecisionGateReason::DynamicsReconsideration)
        || urgent.dynamics_reconsideration_reason != "urgent_hunger"
        || !urgent.policy_evaluated || !urgent.post_policy_outcome.has_value()
        || !urgent.running_action_after.has_value()
        || urgent.running_action_after->action != ActionType::GetMeal) return 5;
    return 0;
}
