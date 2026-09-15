#include "continuous_runtime.h"

#include <iostream>

int main() {
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    RuntimeScheduler scheduler(9 * 60 + 20);
    Observation observation = refresh_observation({}, world, {});
    ContinuousRuntime runtime(scheduler, world, observation, {}, 12345U);
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 1;
    CharacterState state;
    Personality personality;
    const RuntimeExecutionResult tick = runtime.execute_next_boundary(state, personality);
    if (tick.policy_seed != 12345U || tick.runtime.boundary.at_total_minutes <= tick.runtime.boundary.from_total_minutes
        || !tick.runtime.boundary.action_after_boundary.has_value()
        || tick.continuous_state.applied.elapsed_minutes <= 0
        || scheduler.now_total_minutes() != total_minutes(world.time)) return 2;
    std::cout << "trace seed=" << tick.policy_seed
              << " boundary=" << tick.runtime.boundary.from_total_minutes << "->"
              << tick.runtime.boundary.at_total_minutes
              << " action=" << to_string(tick.runtime.boundary.action_after_boundary->action) << "\n";
    return 0;
}
